import sqlite3
import time
import os

# 환경 분석 반영: 프로젝트 폴더 내 기존 DB 연결
db_path = os.path.join(os.getcwd(), "test_automation.db")

def run_management_practice():
    # 1. DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 성공: {db_path}")
    time.sleep(5)

    # 2. 데이터 수정 (UPDATE)
    # '석희' 사용자의 이메일을 운영용 이메일로 변경한다고 가정
    new_email = 'seokhee_final@example.com'
    print(f"2. 데이터 수정 시작 (이름 = '석희' -> 새 이메일: {new_email})")
    cursor.execute("UPDATE users SET email = ? WHERE name = ?", (new_email, '석희'))
    conn.commit() # 수정 사항 확정
    print("   [수정완료] 데이터가 업데이트되었습니다.")
    time.sleep(5)

    # 3. 데이터 삭제 (DELETE)
    # 테스트용 계정인 'QA_Bot' 데이터를 삭제하여 DB 정리
    print("3. 데이터 삭제 시작 (이름 = 'QA_Bot')...")
    cursor.execute("DELETE FROM users WHERE name = ?", ('QA_Bot',))
    conn.commit() # 삭제 사항 확정
    print("   [삭제완료] 테스트 데이터가 정리되었습니다.")
    time.sleep(5)

    # 4. 최종 결과 확인 (SELECT)
    print("4. 최종 데이터 상태 확인:")
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(f"   현재 데이터 -> ID: {row[0]}, 이름: {row[1]}, 이메일: {row[2]}")
    time.sleep(5)

    # 5. 연결 종료
    conn.close()
    print("5. 관리 작업을 마치고 DB 연결 종료")

if __name__ == "__main__":
    run_management_practice()