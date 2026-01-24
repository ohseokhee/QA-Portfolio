from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()

try:
    # 1. 테스트용 사이트 접속 (경고창 연습을 위해 JS Alert가 있는 페이지로 가정)
    # 실습을 위해 간단한 자바스크립트 경고창을 직접 실행해 보겠습니다.
    driver.get("https://www.google.com")
    driver.maximize_window()

    # 2. 브라우저에 강제로 경고창(Alert) 띄우기 (연습용)
    driver.execute_script("alert('QA 테스트: 경고창을 확인하세요!');")
    print("1. 브라우저 경고창 발생")
    time.sleep(2)


    # 3. [핵심] 경고창으로 제어권 이동 및 확인 클릭
    # alert_is_present 조건으로 경고창이 뜰 때까지 대기
    wait = WebDriverWait(driver, 10)
    wait.until(EC.alert_is_present())

    alert = driver.switch_to.alert
    print(f"2. 경고창 메시지 내용: {alert.text}")

    # 확인(OK) 버튼 클릭
    alert.accept()
    print("3. 경고창 '확인' 클릭 완료")

    time.sleep(2)

finally:
    driver.quit()
    print("테스트 종료")