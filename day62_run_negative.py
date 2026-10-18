"""
Day 62 : 모의 게임 서버 부정 케이스 컬렉션 Newman 데이터 주도 실행
의존성: npm install -g newman (Day 56에 설치)
DB 초기화 → 서버 기동 → 만료 토큰·경계값 상태 준비 → CSV로 컬렉션 반복 실행 → 서버 종료 → DB 재초기화
"""

import os
import subprocess
import sys

import pymysql

from day59_apply_schema import APP_PASSWORD, APP_USER, DB_HOST, DB_NAME, DB_PORT, apply_schema
from day60_smoke_check import call, wait_for_server

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTION_FILE = "day62_negative_collection.json"
ENVIRONMENT_FILE = "day61_environment.json"
DATA_FILE = "day62_negative_cases.csv"


def login_user1():
    status, body = call("POST", "/auth/login", {"username": "qa_user1", "password": "Test1234!"})
    if status != 200:
        raise RuntimeError(f"준비용 로그인 실패: {status} {body}")
    return body["access_token"]


def prepare_state():
    """Postman으로 만들 수 없는 상태를 DB에서 직접 준비한다 (명세 3장 auth_tokens.expires_at 조작)."""
    expired_token = login_user1()
    expiring_token = login_user1()

    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER,
                           password=APP_PASSWORD, database=DB_NAME, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            # 발급 시각 기준으로 만료 시각을 당겨 서버 시계·DB 시간대 차이와 무관하게 만든다
            cur.execute("UPDATE auth_tokens SET expires_at = DATE_SUB(issued_at, INTERVAL 1 SECOND) "
                        "WHERE token = %s", (expired_token,))
            cur.execute("UPDATE auth_tokens SET expires_at = DATE_ADD(issued_at, INTERVAL 60 SECOND) "
                        "WHERE token = %s", (expiring_token,))
            # TC-GRANT-08: qa_admin BP 98,999,999 (1,000,000 지급 시 정확히 상한)
            cur.execute("UPDATE account_currency SET balance = 98999999 "
                        "WHERE account_id = 3 AND currency_type = 'BP'")
            # BVA-OWN: qa_admin 101 보유 990개 (보유 상한 999 경계)
            cur.execute("INSERT INTO inventory (account_id, item_id, quantity) VALUES (3, 101, 990)")
        conn.commit()
    finally:
        conn.close()

    print("  만료 토큰: expires_at = issued_at - 1초 (만료 1초 후)")
    print("  만료 직전 토큰: expires_at = issued_at + 60초")
    print("  qa_admin BP 98,999,999, 101 보유 990개")
    return expired_token, expiring_token


def run():
    print("[1] fc_qa_lab 시드 상태로 초기화")
    apply_schema()

    print("\n[2] 서버 기동: py -m uvicorn day60_server_v1:app --port 8000")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "day60_server_v1:app",
                               "--host", "127.0.0.1", "--port", "8000"],
                              cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_server()
        print("  기동 확인")

        print("\n[3] 테스트 상태 준비")
        expired_token, expiring_token = prepare_state()

        print(f"\n[4] newman run {COLLECTION_FILE} -e {ENVIRONMENT_FILE} -d {DATA_FILE}")
        result = subprocess.run(
            ["newman", "run", COLLECTION_FILE, "-e", ENVIRONMENT_FILE, "-d", DATA_FILE,
             "--env-var", f"expired_token={expired_token}",
             "--env-var", f"expiring_token={expiring_token}",
             "--color", "off"],
            cwd=BASE_DIR, capture_output=True, text=True, shell=True,
            encoding="utf-8", errors="replace",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    finally:
        server.terminate()
        server.wait(timeout=10)
        print("[5] 서버 종료")

    print("\n[6] fc_qa_lab 시드 상태로 재초기화")
    apply_schema()

    print(f"\n[결과] newman 종료 코드 {result.returncode} ({'전체 통과' if result.returncode == 0 else '실패 있음'})")
    sys.exit(result.returncode)


if __name__ == "__main__":
    run()
