import sqlite3
import time
import os

# 환경 분석 반영: 프로젝트 폴더 내 기존 DB 연결
db_path = os.path.join(os.getcwd(), "test_automation.db")


def run_join_practice():
    # 1. DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 성공: {db_path}")
    time.sleep(5)

    # 2. 주문(orders) 테이블 생성 (사용자 테이블과 ID로 연결됨)
    # user_id는 users 테이블의 id를 참조하는 외래키(Foreign Key) 역할
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("""
                   CREATE TABLE orders
                   (
                       order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id      INTEGER,
                       product_name TEXT,
                       price        INTEGER
                   )
                   """)
    print("2. 'orders' 테이블 생성 완료")
    time.sleep(5)

    # 3. 주문 테스트 데이터 삽입
    # ID 1번(석희)과 2번(Gemini) 사용자의 주문 데이터라고 가정
    order_data = [
        (1, '파이썬 자동화 강의', 50000),
        (1, '무선 마우스', 35000),
        (2, '고성능 키보드', 120000)
    ]
    cursor.executemany("INSERT INTO orders (user_id, product_name, price) VALUES (?, ?, ?)", order_data)
    conn.commit()
    print("3. 주문 테스트 데이터 삽입 완료")
    time.sleep(5)

    # 4. [핵심] JOIN을 사용해 사용자 이름과 주문 상품 정보 합쳐서 조회
    print("4. JOIN 쿼리 실행 (사용자 이름 + 주문 내역):")
    query = """
            SELECT users.name, orders.product_name, orders.price
            FROM users
                     INNER JOIN orders ON users.id = orders.user_id \
            """
    cursor.execute(query)
    results = cursor.fetchall()

    for row in results:
        print(f"   [결과] 구매자: {row[0]} | 상품: {row[1]} | 가격: {row[2]}원")
    time.sleep(5)

    # 5. 연결 종료
    conn.close()
    print("5. JOIN 실습을 마치고 DB 연결 종료")


if __name__ == "__main__":
    run_join_practice()