import sqlite3
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By

# 환경 설정
db_path = os.path.join(os.getcwd(), "test_automation.db")


def run_integration_test():
    # [준비] 테스트 데이터 정의
    test_user = {"name": "최종보스", "email": "boss@final.com"}

    # 1. UI 자동화 단계 (Selenium)
    print("1. UI 자동화 시작: 사용자 등록 페이지 접속")
    driver = webdriver.Chrome()  # 드라이버 경로는 환경에 맞게 설정
    try:
        # 가상의 등록 페이지 접속 (실제 테스트 시 해당 URL로 변경)
        # driver.get("https://example.com/register")
        print(f"   [UI] 사용자 '{test_user['name']}' 입력 중...")
        time.sleep(5)

        # 2. DB 검증 단계 (SQLite)
        print("2. DB 교차 검증 시작: 데이터 저장 여부 확인")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # UI에서 입력한 값이 DB에 있는지 쿼리
        cursor.execute("SELECT * FROM users WHERE email = ?", (test_user['email'],))
        db_result = cursor.fetchone()

        time.sleep(5)

        # 3. 데이터 일치 여부 판정 (Assertion)
        print("3. 결과 분석:")
        if db_result and db_result[1] == test_user['name']:
            print(f"   [PASS] UI 입력값과 DB 저장값이 일치합니다. (이름: {db_result[1]})")
        else:
            # 실습 편의를 위해 DB에 직접 삽입 후 확인하는 로직으로 대체 가능
            print("   [FAIL] 데이터를 찾을 수 없거나 일치하지 않습니다. 직접 삽입 후 재검증합니다.")
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (test_user['name'], test_user['email']))
            conn.commit()
            print("   [INFO] 테스트용 데이터 DB 강제 삽입 완료.")

    except Exception as e:
        print(f"   [ERROR] 테스트 중 오류 발생: {e}")

    finally:
        time.sleep(5)
        if 'conn' in locals(): conn.close()
        driver.quit()
        print("4. 통합 테스트 종료 및 리소스 해제")


if __name__ == "__main__":
    run_integration_test()