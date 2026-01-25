from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()

try:
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)

    # 1. 실습용 페이지 접속 (iframe이 포함된 연습용 사이트)
    driver.get("https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_iframe")
    print("1. 연습 페이지 접속 완료")

    # 2. [핵심] Iframe 내부로 제어권 전환
    # Iframe 요소가 로드될 때까지 대기 후, 해당 프레임으로 스위칭
    # iframe의 ID나 Name, 혹은 요소 자체를 인자로 넣을 수 있습니다.
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeResult")))
    print("2. 메인 페이지 -> Iframe 내부로 제어권 전환 성공")

    # 3. Iframe 내부의 요소 조작
    # 이 예제 사이트 안에는 또 다른 iframe이 있을 수 있으므로 내부 h1 태그 등을 확인
    inner_text = driver.find_element(By.TAG_NAME, "h1").text
    print(f"3. Iframe 내부 텍스트 추출: {inner_text}")

    # 4. [중요] 다시 메인 페이지(상위 레벨)로 빠져나오기
    # 이걸 안 하면 다음 단계에서 메인 메뉴를 클릭할 수 없음
    driver.switch_to.default_content()
    print("4. Iframe -> 메인 페이지로 복귀 완료")

    time.sleep(2)

finally:
    driver.quit()
    print("테스트 종료")