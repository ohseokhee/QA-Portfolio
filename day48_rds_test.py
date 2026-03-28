"""
Day 48 : AWS RDS MariaDB 연결 테스트 및 데이터 검증
EC2 안에서 실행하는 스크립트
의존성: pip install pymysql
"""

import pymysql
import os
import sys

# ── RDS 연결 설정 (환경변수 또는 직접 입력) ───────────────────────────────
RDS_HOST     = os.environ.get("RDS_HOST", "YOUR_RDS_ENDPOINT")
RDS_PORT     = int(os.environ.get("RDS_PORT", 3306))
RDS_USER     = os.environ.get("RDS_USER", "admin")
RDS_PASSWORD = os.environ.get("RDS_PASSWORD", "YOUR_PASSWORD")
RDS_DB       = os.environ.get("RDS_DB", "qa_db")
# ──────────────────────────────────────────────────────────────────────────

STEPS = []


def log(step, msg):
    STEPS.append((step, msg))
    print(f"[{step}] {msg}")


def run():
    log("1", f"RDS 연결 시도: {RDS_HOST}:{RDS_PORT}")

    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB,
            connect_timeout=10,
        )
        log("2", "RDS 연결 성공")
    except Exception as e:
        log("2", f"RDS 연결 실패: {e}")
        sys.exit(1)

    with conn.cursor() as cursor:
        # 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rds_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        log("3", "테이블 생성 완료 (rds_test)")

        # 데이터 삽입
        cursor.execute(
            "INSERT INTO rds_test (message) VALUES (%s)",
            ("Day 48 RDS 연결 테스트 성공",)
        )
        conn.commit()
        log("4", "데이터 삽입 완료")

        # 데이터 조회
        cursor.execute("SELECT id, message, created_at FROM rds_test ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        log("5", f"조회 결과 ({len(rows)}건):")
        for row in rows:
            print(f"       id={row[0]} | message={row[1]} | created_at={row[2]}")

        # MariaDB 버전 확인
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        log("6", f"MariaDB 버전: {version}")

    conn.close()
    log("7", "연결 종료 및 검증 완료")


if __name__ == "__main__":
    run()