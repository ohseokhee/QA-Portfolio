from selenium import webdriver
from selenium.webdriver.chrome.options import Options  # 옵션 추가
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# 1. 브라우저 옵션 설정
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])  # "제어되고 있음" 메시지 숨기기
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)

try:
    # 2. 구글 접속
    driver.get("https://www.google.com")
    print("페이지 접속 완료")

    # 보안 인증(캡차)이 뜰 경우를 대비해 여기서 충분히 기다려줍니다.
    # 사람이 직접 인증을 풀거나 창을 확인할 시간을 줍니다.
    time.sleep(5)

    # 3. 검색창 찾기
    search_box = driver.find_element(By.NAME, "q")

    # 4. 검색어 입력 (조금 더 천천히 입력하는 효과를 위해 검색어 설정)
    search_keyword = "QA 자동화 테스트"
    search_box.send_keys(search_keyword)
    print(f"검색어 입력 완료: {search_keyword}")

    search_box.send_keys(Keys.RETURN)
    print("검색 결과 페이지 이동 완료")

    # 5. 결과 확인 대기 시간 대폭 연장 (3초 -> 30초)
    # 이 시간 동안 검색된 페이지를 충분히 구경하세요!
    print("30초 동안 결과를 유지합니다. 확인 후 종료하세요.")
    time.sleep(30)

finally:
    driver.quit()
    print("테스트 종료")