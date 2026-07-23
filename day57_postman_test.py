"""
Day 57 : 검증 스크립트 (Tests 탭, Chai assertion) + 데이터 주도 테스트
의존성: npm install -g newman (Day 56에서 설치 완료)
Day 56 컬렉션에 pm.test() 검증 스크립트를 추가하고, day57_data.json으로 post_id를 3회 반복 치환
"""

import subprocess
import sys

COLLECTION_FILE = "day57_postman_collection.json"
ENVIRONMENT_FILE = "day56_postman_environment.json"
DATA_FILE = "day57_data.json"


def run():
    print("=" * 55)
    print("  Day 57 Postman 검증 스크립트 + 데이터 주도 테스트 (Newman)")
    print("=" * 55 + "\n")

    result = subprocess.run(
        ["newman", "run", COLLECTION_FILE, "-e", ENVIRONMENT_FILE, "-d", DATA_FILE],
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
    print("  Day 57 실행 완료")
    print("=" * 55)


if __name__ == "__main__":
    run()
