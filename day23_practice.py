from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()

try:
    driver.maximize_window()
    wait = WebDriverWait(driver, 15)

    # 1. 실습 페이지 접속
    driver.get("https://www.selenium.dev/selenium/web/inputs.html")
    print("1. 실습 페이지 접속 완료")
    time.sleep(5)

    # 2. 페이지 하단으로 전체 스크롤 (요소 로드 유도)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    print("2. 페이지 하단으로 전체 스크롤 수행")
    time.sleep(5)

    # 3. [개선] 제출 버튼 정밀 탐색
    # ID에 의존하지 않고 버튼의 속성(type='submit')으로 확실하게 탐색
    submit_btn = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], #submit")))

    # 버튼을 화면 중앙으로 정밀 정렬
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
    print("3. 제출 버튼을 화면 중앙으로 정밀 정렬 완료")
    time.sleep(5)

    # 4. 최종 데이터 입력
    email_input = driver.find_element(By.NAME, "email_input")
    email_input.clear()
    email_input.send_keys("final_graduation@test.com")
    print("4. 최종 데이터 입력 완료")
    time.sleep(5)

    # 5. [개선] 상호작용 가능할 때까지 기다린 후 클릭
    wait.until(EC.element_to_be_clickable(submit_btn))
    submit_btn.click()
    print("5. 최종 제출 버튼 클릭 성공")

    time.sleep(5)

except Exception as e:
    print(f"에러 발생 상세: {type(e).__name__} - {e}")

finally:
    driver.quit()
    print("셀레니움 기초 과정 최종 종료")