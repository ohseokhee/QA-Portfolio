# [Day 9] 예외 처리(try-except)를 활용한 중단 없는 테스트

def safe_test_execution():
    test_list = ["로그인", "결제"]

    try:
        print("--- 테스트 실행 시작 ---")

        # 1. 의도적인 에러 발생 : 리스트에 없는 3번째 항목 호출
        print(f"실행 중인 테스트 : {test_list[2]}")

    except IndexError as e:
        # 에러가 발생했을 때 실행되는 구간
        print(f"[경고] 에러 발생! 사유: {e}")
        print("조치 : 에러를 로그에 기록하고 다음 시나리오로 넘어감")

    finally:
        # 에러 발생 여부와 상관없이 무조건 실행되는 구간
        print("--- 테스트 프로세스 종료 (자원 정리) ---")


# 실행
safe_test_execution()

print("\n[알림] 예외 처리를 했기 때문에 프로그램이 강제 종료되지 않고 여기까지 도달함!")