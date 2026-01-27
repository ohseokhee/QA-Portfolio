from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import time

driver = webdriver.Chrome()

try:
    driver.maximize_window()
    wait = WebDriverWait(driver, 15)
    actions = ActionChains(driver)

    # 1. 네이버 메인 접속
    driver.get("https://www.naver.com")

    # '지도' 메뉴 탐색 (가장 확실한 링크 텍스트 사용)
    map_menu = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "지도")))

    # [보강] 마우스 오버가 안 될 경우를 대비해 click_and_hold 후 pause 처리
    # 실제로 마우스가 올라가서 메뉴 색상이 변하거나 밑줄이 생기는지 확인하기 위함
    actions.move_to_element(map_menu).pause(1).perform()
    print("1. 지도 메뉴 마우스 오버(Hover) 수행 완료")

    # 눈으로 확인할 시간 5초 부여
    time.sleep(5)

    # 2. 키보드 복합 입력 실습
    search_input = wait.until(EC.element_to_be_clickable((By.ID, "query")))

    # 검색창 클릭 후 Shift 조합 입력
    actions.click(search_input) \
        .key_down(Keys.SHIFT) \
        .send_keys("selenium") \
        .key_up(Keys.SHIFT) \
        .send_keys(Keys.ENTER) \
        .perform()
    print("2. 키보드 복합 제어 및 검색 수행 완료")

    # 검색 결과 화면 확인 시간 5초
    time.sleep(5)

except Exception as e:
    print(f"에러 발생 상세: {type(e).__name__} - {e}")

finally:
    driver.quit()
    print("테스트 종료")