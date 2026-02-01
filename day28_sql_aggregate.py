import sqlite3
import time
import os

# 환경 분석 반영: 프로젝트 폴더 내 기존 DB 연결
db_path = os.path.join(os.getcwd(), "test_automation.db")


def run_aggregate_practice():
    # 1. DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"1. 데이터베이스 연결 성공: {db_path}")
    time.sleep(5)

    # 2. 전체 주문 건수 및 총 매출액 계산 (COUNT, SUM)
    print("2. 전체 주문 통계 계산 시작...")
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders")
    total_count, total_sum = cursor.fetchone()
    print(f"   [통계] 총 주문 건수: {total_count}건 / 총 매출액: {total_sum}원")
    time.sleep(5)

    # 3. [QA 실무 포인트] 사용자별 주문 건수 및 평균 구매액 (GROUP BY, AVG)
    # 특정 사용자의 활동 로그가 정상적으로 집계되는지 확인
    print("3. 사용자별 구매 통계 조회 (GROUP BY)...")
    query = """
            SELECT users.name, COUNT(orders.order_id), AVG(orders.price)
            FROM users
                     LEFT JOIN orders ON users.id = orders.user_id
            GROUP BY users.name \
            """
    cursor.execute(query)
    results = cursor.fetchall()

    for row in results:
        # row[2]가 None일 경우(주문 없는 사용자)를 대비한 예외 처리
        avg_price = row[2] if row[2] is not None else 0
        print(f"   [결과] 사용자: {row[0]} | 주문건수: {row[1]}건 | 평균금액: {avg_price:.0f}원")
    time.sleep(5)

    # 4. 연결 종료
    conn.close()
    print("4. 집계 실습을 마치고 DB 연결 종료")


if __name__ == "__main__":
    run_aggregate_practice()