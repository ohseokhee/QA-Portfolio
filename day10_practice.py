# [Day 10] 모듈(import) 활용 및 외부 라이브러리 기초

import time  # 시간 관련 모듈
import random  # 난수 발생 관련 모듈


def automated_random_test():
    print("--- 랜덤 데이터 기반 테스트 시작 ---")

    # 1. 랜덤 값 생성 (1~100 사이의 레벨 테스트 데이터)
    random_level = random.randint(1, 100)
    print(f"생성된 테스트 데이터(레벨) : {random_level}")

    # 2. 대기 시간 적용 (실제 웹 로딩을 기다리는 상황 가정)
    print("데이터 분석 중... (2초 대기)")
    time.sleep(2)

    # 3. 결과 판별
    if random_level >= 50:
        print("결과 : 고레벨 유저 시나리오 테스트 진행")
    else:
        print("결과 : 저레벨 유저 시나리오 테스트 진행")


# 실행
automated_random_test()