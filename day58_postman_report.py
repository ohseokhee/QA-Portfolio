"""
Day 58 : Newman CLI 실행 + 리포트 생성 (자동화 연계 준비)
의존성: npm install -g newman newman-reporter-htmlextra
Day 57 컬렉션/데이터/환경변수를 그대로 재사용해 CLI + HTML 리포트 실행까지 자동화
"""

import subprocess
import sys

COLLECTION_FILE = "day57_postman_collection.json"
ENVIRONMENT_FILE = "day56_postman_environment.json"
DATA_FILE = "day57_data.json"
REPORT_DIR = "day58-report"


def run():
    print("=" * 55)
    print("  Day 58 Newman CLI 실행 + HTML 리포트 생성")
    print("=" * 55 + "\n")

    result = subprocess.run(
        [
            "newman", "run", COLLECTION_FILE,
            "-e", ENVIRONMENT_FILE,
            "-d", DATA_FILE,
            "-r", "cli,htmlextra",
            "--reporter-htmlextra-export", f"{REPORT_DIR}/index.html",
        ],
        capture_output=True, text=True, shell=True,
        encoding="utf-8", errors="replace",
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("[실패] Newman 실행 중 검증 실패 또는 오류 발생")
        sys.exit(1)

    print("=" * 55)
    print(f"  Day 58 실행 완료 - 리포트: {REPORT_DIR}/index.html")
    print("=" * 55)


if __name__ == "__main__":
    run()
