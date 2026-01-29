from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# 환경 분석 반영: 파일 저장 경로를 절대 경로로 취급하여 권한 에러 방지
current_path = os.getcwd()

driver = webdriver.Chrome()

try:
    driver.maximize_window()
    wait = WebDriverWait(driver, 15)

    # 1. 대상 페이지 접속 (21일차와 동일한 페이지로 데이터 추출 실습)
    driver.get("https://www.selenium.dev/selenium/web/inputs.html")
    print("1. 실습 페이지 접속 완료")
    time.sleep(5)

    # 2. [잠재적 문제 해결] 요소가 화면 밖에 있을 경우를 대비한 텍스트 추출
    # 'Testing Inputs' 헤더 텍스트 수집
    header_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    collected_text = header_element.text
    print(f"2. 수집된 헤더 텍스트: {collected_text}")
    time.sleep(5)

    # 3. [증거 수집 1] 전체 화면 스크린샷
    # 파일명에 타임스탬프를 넣지 않아 덮어쓰기 방식으로 관리 편의성 증대
    full_screenshot_name = "full_evidence.png"
    driver.save_screenshot(full_screenshot_name)
    print(f"3. 전체 화면 캡처 완료: {current_path}\\{full_screenshot_name}")
    time.sleep(5)

    # 4. [증거 수집 2] 특정 요소(이메일 입력란) 부분 캡처
    # 환경 분석 반영: 요소가 가려져 있으면 캡처가 깨지므로 스크롤 후 캡처
    target_element = driver.find_element(By.NAME, "email_input")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
    time.sleep(2)  # 스크롤 안정을 위한 짧은 대기

    element_screenshot_name = "email_field_evidence.png"
    target_element.screenshot(element_screenshot_name)
    print(f"4. 이메일 필드 부분 캡처 완료: {element_screenshot_name}")
    time.sleep(5)

except Exception as e:
    # 환경 분석 반영: 에러 발생 시 발생 지점의 스크린샷을 남기는 QA 관습 적용
    driver.save_screenshot("error_log.png")
    print(f"에러 발생: {type(e).__name__} - {e}")

finally:
    driver.quit()
    print("테스트 종료")