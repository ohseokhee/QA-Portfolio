import sqlite3
import time
import os

# 환경 분석 반영: 프로젝트 폴더 내 기존 생성된 DB 파일 연결
db_path = os.path.join(os.getcwd(), "test_automation.db")


def run_select_practice():
    # 1. DB 연결 (이미 존재하므로 연결만 수행)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 성공: {db_path}")
    time.sleep(5)

    # 2. 전체 데이터 조회 (SELECT *)
    print("2. 전체 사용자 목록 조회 시작...")
    cursor.execute("SELECT * FROM users")
    all_users = cursor.fetchall()  # 모든 행을 리스트로 가져옴

    for user in all_users:
        print(f"   [전체조회] ID: {user[0]}, 이름: {user[1]}, 이메일: {user[2]}")
    time.sleep(5)

    # 3. [QA 실무 포인트] 특정 데이터 필터링 (WHERE)
    # 이름이 '석희'인 데이터만 정확히 들어있는지 확인
    target_name = '석희'
    print(f"3. 특정 조건 조회 시작 (이름 = '{target_name}')...")
    cursor.execute("SELECT * FROM users WHERE name = ?", (target_name,))
    filtered_user = cursor.fetchone()  # 조건에 맞는 첫 번째 행만 가져옴

    if filtered_user:
        print(f"   [필터조회] 결과 발견 -> 이메일: {filtered_user[2]}")
    else:
        print("   [필터조회] 결과를 찾을 수 없습니다.")
    time.sleep(5)

    # 4. 연결 종료
    conn.close()
    print("4. 조회를 마치고 DB 연결 종료")


if __name__ == "__main__":
    run_select_practice()