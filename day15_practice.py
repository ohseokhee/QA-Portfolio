from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

# [중요] 암묵적 대기 설정 (최대 10초까지 요소가 나타나길 기다림)
# 요소가 1초 만에 나타나면 바로 다음 코드를 실행하므로 효율적임
driver.implicitly_wait(10)

try:
    # 1. 테스트용 사이트 접속 (캡차가 적은 네이버로 연습)
    driver.get("https://www.naver.com")
    print("페이지 접속 완료")

    # 2. 검색창 탐색 및 클릭 (네이버 검색창 ID는 'query')
    search_input = driver.find_element(By.ID, "query")
    search_input.send_keys("QA 자동화")

    # 3. 검색 버튼 클릭
    search_button = driver.find_element(By.CLASS_NAME, "btn_search")
    search_button.click()
    print("검색 버튼 클릭 완료")

    # 4. 결과 확인을 위한 최종 대기
    time.sleep(5)

finally:
    driver.quit()
    print("브라우저 종료 및 테스트 완료")