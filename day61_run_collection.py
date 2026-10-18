"""
Day 61 : 모의 게임 서버 정상 흐름 컬렉션 Newman 실행
의존성: npm install -g newman (Day 56에 설치)
DB 초기화 → 서버 기동 → 컬렉션 실행 → 서버 종료 → DB 재초기화
"""

import os
import subprocess
import sys

from day59_apply_schema import apply_schema
from day60_smoke_check import wait_for_server

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTION_FILE = "day61_collection.json"
ENVIRONMENT_FILE = "day61_environment.json"


def run():
    print("[1] fc_qa_lab 시드 상태로 초기화")
    apply_schema()

    print("\n[2] 서버 기동: py -m uvicorn day60_server_v1:app --port 8000")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "day60_server_v1:app",
                               "--host", "127.0.0.1", "--port", "8000"],
                              cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_server()
        print("  기동 확인\n")

        print(f"[3] newman run {COLLECTION_FILE} -e {ENVIRONMENT_FILE}")
        result = subprocess.run(
            ["newman", "run", COLLECTION_FILE, "-e", ENVIRONMENT_FILE, "--color", "off"],
            cwd=BASE_DIR, capture_output=True, text=True, shell=True,
            encoding="utf-8", errors="replace",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    finally:
        server.terminate()
        server.wait(timeout=10)
        print("[4] 서버 종료")

    print("\n[5] fc_qa_lab 시드 상태로 재초기화")
    apply_schema()

    print(f"\n[결과] newman 종료 코드 {result.returncode} ({'전체 통과' if result.returncode == 0 else '실패 있음'})")
    sys.exit(result.returncode)


if __name__ == "__main__":
    run()
