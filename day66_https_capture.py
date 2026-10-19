"""
Day 66 : HTTPS 전환 + 프록시 복호화 검증
1) HTTPS 서버 직접 접속: 시스템 기본 신뢰 저장소 → 실패 / 로컬 CA 지정 → 성공
2) 프록시(mitmproxy) 경유: 프록시 CA를 신뢰하지 않으면 실패 (인증서 설치 전)
3) 프록시 CA를 verify에 지정하면 성공 → 프록시가 복호화한 요청·응답 원문 확인 (인증서 설치 후)
실행: py day66_https_capture.py
"""

import json
import os
import re
import sys
import time

import requests

from day59_apply_schema import apply_schema
from day66_make_certs import CA_CERT, make_certs
from day66_proxy_lab import BASE_DIR, MITM_CA, PROXY_PORT, new_session, start_mitm, start_server, stop

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://127.0.0.1:8443"
PROXY = f"http://127.0.0.1:{PROXY_PORT}"
CAPTURE_FILE = os.path.join(BASE_DIR, "handoff", "day66_capture.jsonl")


def check(label, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} → {detail}")
    return ok


def try_get(session, path):
    try:
        res = session.get(BASE_URL + path, timeout=5)
        return f"{res.status_code}", None
    except requests.exceptions.SSLError as e:
        reason = re.search(r"certificate verify failed: ([^'\"(]+)", str(e))
        return None, "SSLError: certificate verify failed: " + (reason.group(1).strip() if reason else str(e)[:80])


def shop_flow(session):
    """상점 페이지와 같은 순서: 로그인 → 재화 조회 → 101 x1 구매"""
    res = session.post(BASE_URL + "/auth/login", json={"username": "qa_user1", "password": "Test1234!"}, timeout=5)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session.get(BASE_URL + "/accounts/1/currency", headers=headers, timeout=5)
    res = session.post(BASE_URL + "/shop/purchase", headers=headers, timeout=5,
                       json={"item_id": 101, "quantity": 1, "request_id": f"d66-{time.time_ns()}"})
    return res


def main():
    results = []
    make_certs()
    print("[1] fc_qa_lab 시드 상태로 초기화")
    apply_schema()
    os.makedirs(os.path.dirname(CAPTURE_FILE), exist_ok=True)
    if os.path.exists(CAPTURE_FILE):
        os.remove(CAPTURE_FILE)

    print("\n[2] HTTPS 서버 기동: py day66_https_server.py --no-reset (127.0.0.1:8443)")
    server = start_server(["day66_https_server.py", "--no-reset"], BASE_URL + "/openapi.json", verify=CA_CERT)
    mitm = None
    try:
        print("\n[3] 직접 접속")
        status, err = try_get(new_session(verify=True), "/shop")
        results.append(check("기본 신뢰 저장소로 접속 → 인증서 검증 실패", err is not None, err or status))
        status, err = try_get(new_session(verify=CA_CERT), "/shop")
        results.append(check("verify=day66_certs/ca.pem → 성공", status == "200", status or err))

        print(f"\n[4] mitmproxy 기동: 127.0.0.1:{PROXY_PORT}, 서버 인증서는 로컬 CA로 검증")
        mitm = start_mitm("day66_capture_addon.py", {"capture_file": CAPTURE_FILE}, upstream_ca=CA_CERT)

        print("\n[5] 프록시 경유 - 프록시 인증서 설치 전 (verify=서버 CA)")
        status, err = try_get(new_session(proxy=PROXY, verify=CA_CERT), "/shop")
        results.append(check("프록시가 발급한 인증서를 신뢰하지 않음 → 실패", err is not None, err or status))

        print("\n[6] 프록시 경유 - 프록시 인증서 설치 후 (verify=day66_mitm/mitmproxy-ca-cert.pem)")
        session = new_session(proxy=PROXY, verify=MITM_CA)
        status, err = try_get(session, "/shop")
        results.append(check("GET /shop → 성공", status == "200", status or err))
        res = shop_flow(session)
        results.append(check("로그인 → 재화 조회 → 구매", res.status_code == 200, f"{res.status_code} {res.json()}"))
    finally:
        stop(mitm)
        stop(server)
        print("\n[7] 서버·프록시 종료")

    print("\n[8] 프록시 복호화 기록 (handoff/day66_capture.jsonl)")
    with open(CAPTURE_FILE, encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    for i, r in enumerate(records, 1):
        print(f"  #{i} {r['scheme'].upper()} {r['method']} {r['url']} → {r['status']} (서버 인증서 CN={r['server_cert_cn']})")
    purchase = next(r for r in records if r["url"].endswith("/shop/purchase"))
    print("\n  [POST /shop/purchase 복호화 원문]")
    print(f"  요청 헤더 Authorization: {purchase['request_headers'].get('authorization', '')[:20]}...")
    print(f"  요청 본문: {purchase['request_body']}")
    print(f"  응답 본문: {purchase['response_body']}")
    results.append(check("HTTPS 구매 요청 본문이 프록시에서 평문으로 보임",
                         '"item_id": 101' in purchase["request_body"] and purchase["scheme"] == "https",
                         f"{len(records)}건 기록"))

    print("\n[9] fc_qa_lab 시드 상태로 재초기화")
    apply_schema()

    passed = sum(results)
    print(f"\n[결과] {passed}/{len(results)} PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
