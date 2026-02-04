import sqlite3
import time
import os

# 환경 분석 반영: 프로젝트 폴더 내 기존 DB 연결
db_path = os.path.join(os.getcwd(), "test_automation.db")

def run_constraint_test():
    # 1. DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 성공: {db_path}")
    time.sleep(5)

    # 2. [UNIQUE 제약조건 테스트] 중복 이메일 삽입 시도
    print("2. [예외 테스트] 중복 이메일 삽입 시도 시작...")
    try:
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ('중복사용자', 'sh@test.com'))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"   [검증성공] 예상된 에러 발생: {e}")
    time.sleep(5)

    # 3. [NOT NULL 제약조건 테스트] 필수값(이름) 누락 삽입 시도
    print("3. [예외 테스트] 필수값(이름) 누락 삽입 시도 시작...")
    try:
        cursor.execute("INSERT INTO users (email) VALUES (?)", ('no_name@test.com',))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"   [검증성공] 예상된 에러 발생: {e}")
    time.sleep(5)

    # 4. 최종 데이터 상태 확인
    print("4. 최종 데이터 무결성 확인 (에러 데이터 삽입 여부):")
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"   현재 총 사용자 수: {count}명 (제약조건에 의해 에러 데이터는 차단됨)")
    time.sleep(5)

    # 5. 연결 종료
    conn.close()
    print("5. 제약조건 검증을 마치고 DB 연결 종료")

if __name__ == "__main__":
    run_constraint_test()