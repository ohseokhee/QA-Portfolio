"""
Day 65 : 상점 페이지 제공 서버 점검
DB 초기화 → day65_serve_client 기동 → /shop 페이지 확인 → 페이지가 보내는 요청 순서대로 API 호출
→ 서버 종료 → DB 재초기화
--proxy http://127.0.0.1:8888 을 주면 같은 요청을 Fiddler를 거쳐 보낸다 (PC 단독 캡처 확인용)
"""

import argparse
import os
import subprocess
import sys
import time

import requests

from day59_apply_schema import apply_schema

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "http://127.0.0.1:8000"


def wait_for_server(timeout=15):
    """Fiddler가 켜져 있으면 Windows 시스템 프록시로 등록되므로 trust_env=False로 직접 접속해 기동을 확인한다."""
    session = requests.Session()
    session.trust_env = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if session.get(BASE_URL + "/openapi.json", timeout=1).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("서버가 기동되지 않았습니다.")


def check(label, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} → {detail}")
    return ok


def run_checks(session):
    results = []

    res = session.get(BASE_URL + "/shop", timeout=5)
    results.append(check("GET /shop 페이지", res.status_code == 200 and "text/html" in res.headers["content-type"],
                         f"{res.status_code} {res.headers['content-type']} {len(res.content)} bytes"))
    results.append(check("페이지에 로그인·구매 스크립트 포함",
                         "/auth/login" in res.text and "/shop/purchase" in res.text, "fetch 경로 2개 확인"))

    # 페이지의 [로그인] → 재화 조회 → [구매] 101 x1 → 재화·인벤토리 갱신 순서 그대로
    res = session.post(BASE_URL + "/auth/login", json={"username": "qa_user1", "password": "Test1234!"}, timeout=5)
    token = res.json().get("access_token", "")
    results.append(check("POST /auth/login", res.status_code == 200 and len(token) == 64,
                         f"{res.status_code} account_id={res.json().get('account_id')}"))
    headers = {"Authorization": f"Bearer {token}"}

    res = session.get(BASE_URL + "/accounts/1/currency", headers=headers, timeout=5)
    results.append(check("GET /accounts/1/currency", res.status_code == 200 and res.json()["balances"]["FC"] == 5000,
                         f"{res.status_code} {res.json()}"))

    request_id = f"web-{int(time.time() * 1000)}-check"
    res = session.post(BASE_URL + "/shop/purchase", headers=headers,
                       json={"item_id": 101, "quantity": 1, "request_id": request_id}, timeout=5)
    results.append(check("POST /shop/purchase 101 x1", res.status_code == 200 and res.json()["balance_after"] == 4000,
                         f"{res.status_code} {res.json()}"))

    res = session.get(BASE_URL + "/accounts/1/currency", headers=headers, timeout=5)
    results.append(check("구매 후 재화 조회", res.status_code == 200 and res.json()["balances"]["FC"] == 4000,
                         f"{res.status_code} {res.json()}"))

    res = session.get(BASE_URL + "/accounts/1/inventory", headers=headers, timeout=5)
    results.append(check("구매 후 인벤토리 조회", res.status_code == 200 and {"item_id": 101, "name": "프리미엄 선수팩",
                                                                     "quantity": 1} in res.json()["items"],
                         f"{res.status_code} {res.json()}"))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", default=None, help="예: http://127.0.0.1:8888 (Fiddler)")
    args = parser.parse_args()

    print("[1] fc_qa_lab 시드 상태로 초기화")
    apply_schema()

    print("\n[2] 서버 기동: py day65_serve_client.py --no-reset")
    server = subprocess.Popen([sys.executable, "day65_serve_client.py", "--no-reset"],
                              cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_server()
        print("  기동 확인\n")

        session = requests.Session()
        session.trust_env = False  # 시스템 프록시 무시, --proxy로 준 값만 사용
        if args.proxy:
            session.proxies = {"http": args.proxy}
        print(f"[3] 페이지·API 점검 (프록시: {args.proxy or '없음'})")
        results = run_checks(session)
    finally:
        server.terminate()
        server.wait(timeout=10)
        print("\n[4] 서버 종료")

    print("\n[5] fc_qa_lab 시드 상태로 재초기화")
    apply_schema()

    passed = sum(results)
    print(f"\n[결과] {passed}/{len(results)} PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
