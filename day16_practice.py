from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()

try:
    # 0. 브라우저 창 최대화 및 기본 대기 설정
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)

    # 1. 네이버 메인 접속
    driver.get("https://www.naver.com")
    print("1. 네이버 메인 접속 완료")

    # 2. '지도' 메뉴 버튼 탐색 및 클릭 (XPath 활용)
    map_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., '지도')]")))
    map_menu.click()
    print("2. 지도 메뉴 클릭 완료 (새 탭 생성)")

    # 3. [핵심] 새 탭으로 드라이버 제어권 전환
    # 새 창이 열릴 때까지 잠시 대기 후 마지막에 열린 탭으로 이동
    time.sleep(1)
    driver.switch_to.window(driver.window_handles[-1])
    print(f"3. 제어권 전환 완료 (현재 창: {driver.title})")

    # 4. 지도 페이지 내 검색창 로딩 검증
    # 제어권이 전환되었으므로 이제 새 페이지의 요소를 찾을 수 있음
    print("4. 지도 페이지 요소 로딩 대기 중...")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "input_search")))
    print("5. 네이버 지도 서비스 로드 완료 확인 (성공)")

    time.sleep(3)

finally:
    driver.quit()
    print("테스트 종료 및 리소스 해제")