import os
import sys

import pymysql
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE = os.path.join(BASE_DIR, "day59_schema.sql")

load_dotenv(os.path.join(BASE_DIR, ".env"))
DB_HOST = "127.0.0.1"
DB_PORT = int(os.getenv("MYSQL_PORT", "3307"))
DB_NAME = os.getenv("FC_DB_NAME")
ROOT_PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD")
APP_USER = os.getenv("MARIADB_USER") or os.getenv("MYSQL_USER")
APP_PASSWORD = os.getenv("MARIADB_PASSWORD") or os.getenv("MYSQL_PASSWORD")


def load_statements(path):
    """주석 줄을 빼고 ';' 기준으로 SQL 문을 나눈다."""
    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("--")]
    return [stmt.strip() for stmt in "".join(lines).split(";") if stmt.strip()]


def apply_schema():
    statements = load_statements(SCHEMA_FILE)
    print(f"[1] 스키마 파일 읽기: {os.path.basename(SCHEMA_FILE)} (SQL {len(statements)}개)")

    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user="root",
                           password=ROOT_PASSWORD, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
            # 앱 계정(.env)에 fc_qa_lab 권한 부여 → Day 60 서버는 앱 계정으로 접속
            cur.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO %s@'%%'", (APP_USER,))
            cur.execute("FLUSH PRIVILEGES")
        conn.commit()
    finally:
        conn.close()
    print(f"[2] root로 {DB_NAME} 생성·초기화 및 앱 계정 권한 부여 완료")


def verify():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER,
                           password=APP_PASSWORD, database=DB_NAME, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            print(f"[3] 앱 계정으로 {DB_NAME} 접속 확인")
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            print(f"\n[테이블 {len(tables)}개]")
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                print(f"  {table:<24} rows={cur.fetchone()[0]}")

            print("\n[계정별 잔액]")
            cur.execute("""
                SELECT a.account_id, a.username, a.role, a.status,
                       SUM(CASE WHEN c.currency_type = 'FC' THEN c.balance END) AS fc,
                       SUM(CASE WHEN c.currency_type = 'BP' THEN c.balance END) AS bp
                FROM accounts a JOIN account_currency c ON a.account_id = c.account_id
                GROUP BY a.account_id ORDER BY a.account_id
            """)
            for row in cur.fetchall():
                print(f"  id={row[0]} {row[1]:<10} {row[2]:<5} {row[3]:<6} FC={row[4]:>6} BP={row[5]:>7}")

            print("\n[상점 아이템]")
            cur.execute("SELECT item_id, name, currency_type, price, max_per_purchase, max_owned, is_on_sale "
                        "FROM shop_items ORDER BY item_id")
            for row in cur.fetchall():
                print(f"  {row[0]} {row[1]} {row[2]} {row[3]} 1회최대={row[4]} 보유상한={row[5]} 판매중={row[6]}")

            print("\n[CHECK 제약 확인] 잔액을 -1로 수정 시도")
            try:
                cur.execute("UPDATE account_currency SET balance = -1 WHERE account_id = 2 AND currency_type = 'FC'")
                print("  결과: 수정됨 (제약 없음)")
            except pymysql.err.OperationalError as e:
                print(f"  결과: 거부됨 → {e.args[1]}")
            conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    apply_schema()
    verify()
