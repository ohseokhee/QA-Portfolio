# [Day 6] 함수(Function)를 활용한 로직 재사용

# 1. 함수 정의 : 'def' 키워드를 사용합니다.
def check_test_result(test_name, actual_value, expected_value):
    print(f"[{test_name}] 검증 시작...")

    if actual_value == expected_value:
        print(f"결과 : Pass (실제값 '{actual_value}'이(가) 예상값과 일치합니다.)")
    else:
        print(f"결과 : Fail (예상값은 '{expected_value}'이지만 실제값은 '{actual_value}'입니다.)")
    print("-" * 30)


# 2. 함수 호출 : 정의한 함수를 실제로 사용해 봅니다.
# 케이스 1 : 로그인 테스트 (성공 시나리오)
check_test_result("로그인 성공 테스트", "Success", "Success")

# 케이스 2 : 레벨 업 테스트 (실패 시나리오 가정)
check_test_result("레벨 업 데이터 검증", 15, 20)