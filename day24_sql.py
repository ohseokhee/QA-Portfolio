import sqlite3
import time
import os

# 환경 분석 반영: 파이참 프로젝트 폴더 내에 DB 파일 생성
# 윈도우 경로 문제를 방지하기 위해 os.path 사용
db_path = os.path.join(os.getcwd(), "test_automation.db")


def run_sql_practice():
    # 1. DB 연결 (파일이 없으면 생성, 있으면 연결)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 완료: {db_path}")
    time.sleep(5)  # 사용자 지침 반영

    # 2. [잠재적 에러 방어] 기존 테이블이 있으면 삭제 (재실행 시 에러 방지)
    cursor.execute("DROP TABLE IF EXISTS users")

    # 3. 테이블 생성 (DDL: Data Definition Language)
    # QA 관점: ID(기본키), 이름, 이메일, 가입일 컬럼 구성
    cursor.execute("""
                   CREATE TABLE users
                   (
                       id        INTEGER PRIMARY KEY AUTOINCREMENT,
                       name      TEXT NOT NULL,
                       email     TEXT UNIQUE,
                       join_date DATETIME DEFAULT CURRENT_TIMESTAMP
                   )
                   """)
    print("2. 'users' 테이블 생성 완료 (스키마 정의 성공)")
    time.sleep(5)

    # 4. 데이터 삽입 (DML: Data Manipulation Language)
    # 테스트를 위한 초기 데이터 주입
    test_data = [
        ('석희', 'sh_test@example.com'),
        ('Gemini', 'ai_tester@example.com'),
        ('QA_Bot', 'bot_test@example.com')
    ]

    cursor.executemany("INSERT INTO users (name, email) VALUES (?, ?)", test_data)

    # 5. 변경사항 확정 (Commit) - 이거 안 하면 파일에 저장 안 됨!
    conn.commit()
    print(f"3. 테스트 데이터 {len(test_data)}건 삽입 완료 (Commit 성공)")
    time.sleep(5)

    # 6. 연결 종료
    conn.close()
    print("4. DB 연결 종료 및 24일차 실습 종료")


if __name__ == "__main__":
    run_sql_practice()