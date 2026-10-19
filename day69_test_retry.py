"""
Day 69 : 네트워크 조건별 구매 재시도 테스트 - 타임아웃 후 재시도 시 중복 구매가 생기는지 확인
- 조건 5종(지연·요청 손실·응답 손실·순서 뒤바뀜·일시 끊김) x 클라이언트 재시도 방식 2종
	- new-id : 재시도마다 request_id를 새로 만듦 (흔한 클라이언트 실수)
	- same-id: 처음 request_id를 재시도에도 그대로 사용 (명세 R7 의도)
- 실행마다 DB 시드 초기화 → 로그인 → 구매(타임아웃 1초, 최대 3회) → 잠시 대기 → 구매 이력·FC·인벤토리 확인
- 기대: 사용자는 101 x1을 한 번 사려 했으므로 구매 이력 1건, FC -1000, 인벤토리 +1
- 결과는 콘솔 매트릭스 + day69_network_matrix.md(또는 --out)로 저장
실행: py day69_test_retry.py [--server day68_server_v2.py] [--label v2] [--out day69_network_matrix.md]
"""

import argparse
import contextlib
import io
import json
import os
import socket
import sys
import time
import uuid

import pymysql
import requests

from day59_apply_schema import APP_PASSWORD, APP_USER, DB_HOST, DB_NAME, DB_PORT, apply_schema
from day66_make_certs import CA_CERT, make_certs
from day66_proxy_lab import BASE_DIR, MITM_CA, PROXY_PORT, new_session, start_mitm, start_server, stop

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://127.0.0.1:8443"
PROXY = f"http://127.0.0.1:{PROXY_PORT}"
COND_FILE = os.path.join(BASE_DIR, "handoff", "day69_cond.json")
TIMEOUT_S, MAX_ATTEMPTS, BACKOFF_S = 1.0, 3, 0.2

CONDITIONS = [
    ("latency", "지연 (응답 1.5초 지연 > 타임아웃 1초)", {"latency_ms": 1500}),
    ("loss_request", "패킷 손실 - 첫 요청 유실", {}),
    ("loss_response", "패킷 손실 - 첫 응답 유실 (서버는 처리)", {}),
    ("reorder", "순서 뒤바뀜 (원 요청·재시도 3개가 역순 동시 도착)", {"hold_count": 3}),
    ("flaky", "일시 끊김 (처음 2개 응답 끊김 후 복구)", {"flaky_count": 2}),
]
POLICIES = ["new-id", "same-id"]


def assert_ports_free(*ports):
    for port in ports:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"[중단] 127.0.0.1:{port}에 이미 실행 중인 프로세스가 있습니다. 종료 후 다시 실행하세요.")


def reset_db():
    with contextlib.redirect_stdout(io.StringIO()):
        apply_schema()


def db_state():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER, password=APP_PASSWORD, database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM account_currency WHERE account_id = 1 AND currency_type = 'FC'")
            fc = int(cur.fetchone()["balance"])
            cur.execute("SELECT COUNT(*) AS n FROM purchase_history WHERE account_id = 1")
            purchases = cur.fetchone()["n"]
            cur.execute("SELECT COALESCE(SUM(quantity), 0) AS q FROM inventory WHERE account_id = 1 AND item_id = 101")
            inv = int(cur.fetchone()["q"])
        return fc, purchases, inv
    finally:
        conn.close()


def purchase_with_retry(token, policy):
    """클라이언트 재시도 로직. 시도별 결과(응답 코드 또는 예외 이름) 목록과 최종 성공 여부를 반환"""
    session = new_session(proxy=PROXY, verify=MITM_CA)
    request_id = f"d69-{uuid.uuid4().hex[:12]}"
    attempts = []
    for n in range(1, MAX_ATTEMPTS + 1):
        if policy == "new-id" and n > 1:
            request_id = f"d69-{uuid.uuid4().hex[:12]}"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": request_id}
        try:
            res = session.post(BASE_URL + "/shop/purchase", headers=headers, timeout=TIMEOUT_S,
                               json={"item_id": 101, "quantity": 1, "request_id": request_id})
            attempts.append(str(res.status_code))
            if res.status_code == 200:
                return attempts, True
            if res.status_code < 500 and res.status_code != 409:
                return attempts, False
        except requests.exceptions.Timeout:
            attempts.append("Timeout")
        except requests.exceptions.ConnectionError:
            attempts.append("ConnErr")
        time.sleep(BACKOFF_S)
    return attempts, False


def run_one(run_id, cond, extra, policy):
    reset_db()
    with open(COND_FILE, "w", encoding="utf-8") as f:
        json.dump({"run": run_id, "cond": cond, **extra}, f)
    token = new_session(verify=CA_CERT).post(BASE_URL + "/auth/login", timeout=5,
                                             json={"username": "qa_user1", "password": "Test1234!"}).json()["access_token"]
    fc0, p0, inv0 = db_state()
    attempts, ok = purchase_with_retry(token, policy)
    time.sleep(2.5)  # 붙잡힌 요청이 서버에 도달할 시간
    fc1, p1, inv1 = db_state()
    fc_change, purchases, inv_change = fc1 - fc0, p1 - p0, inv1 - inv0
    verdict = purchases == 1 and fc_change == -1000 and inv_change == 1
    return {"cond": cond, "policy": policy, "attempts": attempts, "client_ok": ok, "purchases": purchases,
            "fc": fc_change, "inv": inv_change, "pass": verdict}


def write_md(path, rows, label):
    names = {c: d for c, d, _ in CONDITIONS}
    lines = [
        f"# Day 69 네트워크 조건 매트릭스 ({label})",
        "",
        f"> 클라이언트: 타임아웃 {TIMEOUT_S}초, 최대 {MAX_ATTEMPTS}회 시도, 재시도 간격 {BACKOFF_S}초. "
        "기대값: 구매 이력 1건 / FC -1000 / 인벤토리 +1 (사용자는 101 x1을 한 번 구매)",
        "",
        "| 조건 | 재시도 방식 | 시도 결과 | 클라이언트 최종 | 구매 이력 | FC 변화 | 인벤토리 | 판정 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {names[r['cond']]} | {r['policy']} | {' → '.join(r['attempts'])} | "
                     f"{'성공' if r['client_ok'] else '실패'} | {r['purchases']} | {r['fc']:+d} | {r['inv']:+d} | "
                     f"{'PASS' if r['pass'] else '**FAIL**'} |")
    failed = [r for r in rows if not r["pass"]]
    lines += ["", f"- 결과: {len(rows) - len(failed)}/{len(rows)} PASS"]
    mismatch = [r for r in rows if r["client_ok"] != (r["purchases"] >= 1)]
    if mismatch:
        lines.append(f"- 클라이언트 결과와 서버 처리 불일치 {len(mismatch)}건 (실패로 보였지만 실제 구매됨 등)")
    with open(os.path.join(BASE_DIR, path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="day68_server_v2.py")
    parser.add_argument("--label", default="서버 v2")
    parser.add_argument("--out", default="day69_network_matrix.md")
    args = parser.parse_args()

    assert_ports_free(8443, PROXY_PORT)
    make_certs()
    os.makedirs(os.path.dirname(COND_FILE), exist_ok=True)
    reset_db()
    print(f"[1] 서버 기동: py {args.server} --no-reset (https://127.0.0.1:8443)")
    server = start_server([args.server, "--no-reset"], BASE_URL + "/openapi.json", verify=CA_CERT)
    print(f"[2] 네트워크 조건 프록시 기동: mitmdump -s day69_netem_addon.py (127.0.0.1:{PROXY_PORT})")
    mitm = start_mitm("day69_netem_addon.py", {"cond_file": COND_FILE}, upstream_ca=CA_CERT)
    print(f"[3] 클라이언트: 타임아웃 {TIMEOUT_S}초, 최대 {MAX_ATTEMPTS}회, 간격 {BACKOFF_S}초\n")
    rows = []
    try:
        run_no = 0
        for cond, desc, extra in CONDITIONS:
            for policy in POLICIES:
                run_no += 1
                r = run_one(f"{cond}-{policy}-{time.time_ns()}", cond, extra, policy)
                rows.append(r)
                print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {desc} / {policy}: 시도 {' → '.join(r['attempts'])}, "
                      f"클라이언트 {'성공' if r['client_ok'] else '실패'} | 구매 이력 {r['purchases']}건, "
                      f"FC {r['fc']:+d}, 인벤토리 {r['inv']:+d}")
    finally:
        stop(mitm)
        stop(server)
        reset_db()

    write_md(args.out, rows, args.label)
    failed = sum(not r["pass"] for r in rows)
    dup = sum(r["purchases"] > 1 or r["inv"] > 1 for r in rows)
    print(f"\n[결과] {len(rows) - failed}/{len(rows)} PASS, 중복 구매·중복 지급 {dup}건 → {args.out}")


if __name__ == "__main__":
    main()
