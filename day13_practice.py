# [Day 13] Selenium을 활용한 웹 브라우저 자동화 기초
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time

# 1. 크롬 드라이버 및 브라우저 실행
# 최근 Selenium 4 버전은 별도의 드라이버 다운로드 없이 자동 관리됨
driver = webdriver.Chrome()

try:
    # 2. 특정 URL로 이동
    print("웹 페이지 접속 시도 중...")
    driver.get("https://www.google.com")

    # 3. 브라우저 제목 확인 (검증)
    page_title = driver.title
    print(f"현재 페이지 제목 : {page_title}")

    # 4. 잠시 대기 (눈으로 확인하기 위함)
    time.sleep(3)

finally:
    # 5. 브라우저 종료 (안전하게 리소스 해제)
    driver.quit()
    print("브라우저 종료 및 테스트 완료")