# [Day 8] 시나리오 기반 자동화 테스트 설계 실습

class ShopTestSuite:
    def __init__(self):
        self.results = [] # 테스트 결과를 담을 리스트
        print("--- 상점 시스템 자동화 테스트를 시작합니다 ---")

    # 공통 검증 메서드
    def assert_equal(self, test_name, actual, expected):
        is_pass = (actual == expected)
        status = "PASS" if is_pass else "FAIL"
        self.results.append(f"{test_name} : {status}")
        print(f"[{test_name}] 결과: {status} (실제: {actual} / 예상: {expected})")

    # 리포트 출력 메서드
    def show_report(self):
        print("\n" + "="*30)
        print("최종 테스트 결과 리포트")
        for res in self.results:
            print(f"- {res}")
        print("="*30)

# --- 테스트 시나리오 실행 ---
test_bot = ShopTestSuite()

# 시나리오 1: 기본 아이템 구매 가격 검증
item_price = 500
user_money = 1000
test_bot.assert_equal("아이템 가격 검증", item_price, 500)

# 시나리오 2: 구매 후 잔액 계산 검증 (의도적 에러 발생 가정)
remaining_money = user_money - item_price
test_bot.assert_equal("구매 후 잔액 검증", remaining_money, 400) # 예상값을 400으로 틀리게 설정해봄

# 최종 결과 리포트 확인
test_bot.show_report()