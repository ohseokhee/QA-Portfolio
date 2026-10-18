import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from day59_apply_schema import apply_schema

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "http://127.0.0.1:8000"


def call(method, path, body=None, token=None):
    """HTTP 요청을 보내고 (상태 코드, JSON 본문)을 반환한다."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def wait_for_server(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/openapi.json", timeout=1) as res:
                return json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.5)
    raise RuntimeError("서버가 기동되지 않았습니다.")


def check(label, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} → {detail}")
    return ok


def smoke():
    results = []
    status, body = call("POST", "/auth/login", {"username": "qa_user1", "password": "Test1234!"})
    user_token = body.get("access_token", "")
    results.append(check("POST /auth/login (qa_user1)", status == 200 and len(user_token) == 64,
                         f"{status}, token {len(user_token)}자, expires_in={body.get('expires_in')}"))

    status, body = call("POST", "/auth/login", {"username": "qa_admin", "password": "Admin1234!"})
    admin_token = body.get("access_token", "")
    results.append(check("POST /auth/login (qa_admin)", status == 200, f"{status}, account_id={body.get('account_id')}"))

    status, body = call("GET", "/accounts/1/currency", token=user_token)
    results.append(check("GET /accounts/1/currency", status == 200, f"{status}, {body}"))

    status, body = call("POST", "/admin/currency/grant",
                        {"account_id": 2, "currency_type": "FC", "amount": 10000, "memo": "기동 점검"},
                        token=admin_token)
    results.append(check("POST /admin/currency/grant", status == 200, f"{status}, {body}"))

    status, body = call("POST", "/shop/purchase",
                        {"item_id": 101, "quantity": 2, "request_id": "smoke-0001"}, token=user_token)
    results.append(check("POST /shop/purchase (101 x 2)", status == 200, f"{status}, {body}"))

    status, body = call("GET", "/accounts/1/inventory", token=user_token)
    results.append(check("GET /accounts/1/inventory", status == 200, f"{status}, {body}"))

    status, body = call("POST", "/auth/login", {"username": "qa_user1"})
    results.append(check("오류 형식 (password 누락)", status == 400 and "error_code" in body, f"{status}, {body}"))
    return results


def main():
    print("[1] fc_qa_lab 시드 상태로 초기화")
    apply_schema()

    print("\n[2] 서버 기동: py -m uvicorn day60_server_v1:app --port 8000")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "day60_server_v1:app",
                               "--host", "127.0.0.1", "--port", "8000"],
                              cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        spec = wait_for_server()
        paths = [f"{m.upper()} {p}" for p, ops in spec["paths"].items() for m in ops]
        print(f"  OpenAPI 등록 엔드포인트 {len(paths)}개")
        for p in paths:
            print(f"    {p}")

        print("\n[3] 정상 흐름 기동 점검")
        results = smoke()
        print(f"\n[결과] {sum(results)}/{len(results)} PASS")
    finally:
        server.terminate()
        server.wait(timeout=10)
        print("\n[4] 서버 종료")

    print("\n[5] fc_qa_lab 시드 상태로 재초기화 (Day 61 테스트 대비)")
    apply_schema()


if __name__ == "__main__":
    main()
