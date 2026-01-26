# [Day 7] 클래스(Class)를 활용한 테스트 매니저 설계

class TestCaseManager:
    # 1. 초기화 메서드 : 클래스가 생성될 때 기본 정보를 설정합니다.
    def __init__(self, tester_name):
        self.tester = tester_name
        self.total_count = 0
        print(f"[{self.tester}]님의 테스트 매니저가 활성화되었습니다.")

    # 2. 테스트 실행 메서드 : 기능을 정의합니다.
    def run_test(self, case_name, is_success):
        self.total_count += 1
        result = "PASS" if is_success else "FAIL"
        print(f"테스트 {self.total_count} : {case_name} -> {result}")

# --- 실제 사용 (인스턴스 생성) ---
# 나만의 테스트 로봇(manager)을 만듭니다.
manager = TestCaseManager("석희")

# 로봇에게 일을 시킵니다.
manager.run_test("아이템 강화 클릭", True)
manager.run_test("상점 페이지 이동", False)
manager.run_test("채팅 입력 확인", True)

print(f"\n최종 결과 : 총 {manager.total_count}건의 테스트를 수행했습니다.")
