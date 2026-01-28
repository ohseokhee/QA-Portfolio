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

    # 1. 실습 페이지 접속
    driver.get("https://www.selenium.dev/selenium/web/inputs.html")
    print("1. 실습 페이지 접속 완료")
    time.sleep(5)

    # 2. 첫 번째 입력란 기존 내용 삭제 후 새 텍스트 입력
    text_input = wait.until(EC.element_to_be_clickable((By.NAME, "no_type")))
    text_input.clear()
    print("2. 기존 텍스트 삭제(Clear) 완료")
    time.sleep(5)

    text_input.send_keys("QA Automation New Text")
    print("3. 새 텍스트 입력 완료")
    time.sleep(5)

    # 3. 체크박스 로직: 선택되어 있으면 해제 후 다시 선택
    checkbox = driver.find_element(By.NAME, "checkbox_input")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)

    if checkbox.is_selected():
        print("4-1. 체크박스가 이미 선택되어 있어 해제 시도")
        checkbox.click()  # 해제
        time.sleep(5)
        checkbox.click()  # 다시 선택
        print("4-2. 체크박스 해제 후 다시 선택 완료")
    else:
        checkbox.click()
        print("4. 체크박스 선택 완료")
    time.sleep(5)

    # 4. [개선] 라디오 버튼(토글) 선택 변경 - 인덱스 방식
    # name="radio_input"인 요소를 모두 찾아 두 번째(인덱스 1) 요소를 클릭
    radio_buttons = driver.find_elements(By.NAME, "radio_input")
    if len(radio_buttons) > 1:
        radio_buttons[1].click()
        print("5. 라디오 버튼 선택 변경 완료 (인덱스 기반)")
    else:
        # 만약 name이 다를 경우 XPath 속성으로 직접 타겟팅
        alt_radio = driver.find_element(By.XPATH, "(//input[@type='radio'])[2]")
        alt_radio.click()
        print("5. 라디오 버튼 선택 변경 완료 (XPath 기반)")
    time.sleep(5)

    # 5. 이메일 입력란 안정화 (강제 삭제 후 입력)
    email_input = wait.until(EC.element_to_be_clickable((By.NAME, "email_input")))
    email_input.click()

    # 전체 선택 후 삭제
    email_input.send_keys(Keys.CONTROL + "a")
    email_input.send_keys(Keys.BACKSPACE)
    time.sleep(2)

    email_input.send_keys("final_perfect_test@example.com")
    email_input.send_keys(Keys.ENTER)
    print("6. 이메일 입력 및 엔터 완료")
    time.sleep(5)

except Exception as e:
    print(f"에러 발생 상세: {type(e).__name__} - {e}")

finally:
    driver.quit()
    print("테스트 종료")