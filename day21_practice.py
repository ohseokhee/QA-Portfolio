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

    # 1. 종합 실습 페이지 접속
    driver.get("https://www.selenium.dev/selenium/web/inputs.html")
    print("1. 실습 페이지 접속 완료")
    time.sleep(5)

    # 2. [개선] 기존 내용이 있는 입력란 타겟팅 (name="no_type")
    # 해당 칸은 페이지 로드 시 기본값이 들어있을 수 있음
    text_input = wait.until(EC.element_to_be_clickable((By.NAME, "no_type")))

    # 로직: 기존 내용 지우기 -> 5초 대기 -> 새 내용 입력
    text_input.clear()
    print("2. 기존 텍스트 삭제(Clear) 완료")
    time.sleep(5)

    text_input.send_keys("QA Automation New Text")
    print("3. 새 텍스트 입력 완료")
    time.sleep(5)

    # 3. 체크박스 제어 (화면 스크롤 포함)
    checkbox = driver.find_element(By.NAME, "checkbox_input")
    actions.move_to_element(checkbox).perform()

    if not checkbox.is_selected():
        checkbox.click()
        print("4. 체크박스 선택 완료")
    time.sleep(5)

    # 4. 복합 제어: 이메일 입력란도 기존 내용 삭제 후 입력
    email_input = driver.find_element(By.NAME, "email_input")
    email_input.clear()  # 안전을 위해 이메일 칸도 초기화

    actions.click(email_input) \
        .send_keys("improved_test@example.com") \
        .send_keys(Keys.ENTER) \
        .perform()
    print("5. 이메일 입력 및 엔터 액션 완료")
    time.sleep(5)

except Exception as e:
    print(f"에러 발생 상세: {type(e).__name__} - {e}")

finally:
    driver.quit()
    print("테스트 종료")