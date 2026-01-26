from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains  # ActionChains 임포트
import time

driver = webdriver.Chrome()

try:
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)  # ActionChains 객체 생성

    # 1. 드래그 앤 드롭 실습 페이지 접속
    driver.get("https://jqueryui.com/droppable/")
    print("1. 실습 페이지 접속 완료")

    # 2. Iframe 전환 (드래그 요소가 iframe 안에 있음)
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.CLASS_NAME, "demo-frame")))

    # 3. 드래그할 요소와 타겟 요소 찾기
    source = driver.find_element(By.ID, "draggable")
    target = driver.find_element(By.ID, "droppable")

    # 4. [핵심] 드래그 앤 드롭 수행
    # perform()을 반드시 호출해야 동작이 실행됨
    actions.drag_and_drop(source, target).perform()
    print("2. 드래그 앤 드롭 동작 수행 완료")

    # 5. 결과 확인
    if "Dropped!" in target.text:
        print("3. 드래그 앤 드롭 성공 확인")

    time.sleep(2)

finally:
    driver.quit()
    print("테스트 종료")