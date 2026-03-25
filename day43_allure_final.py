import pytest
import allure
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 픽스처
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver(request):
    """Chrome RemoteWebDriver 픽스처"""
    allure.dynamic.parameter("Browser", "Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)

    yield driver

    # 실패 시 스크린샷
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        try:
            allure.attach(
                driver.get_screenshot_as_png(),
                name="Failure Screenshot",
                attachment_type=allure.attachment_type.PNG
            )
        except:
            pass

    driver.quit()


@pytest.fixture(scope="function")
def firefox_driver(request):
    """Firefox RemoteWebDriver 픽스처"""
    allure.dynamic.parameter("Browser", "Firefox")
    options = webdriver.FirefoxOptions()
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)

    yield driver

    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        try:
            allure.attach(
                driver.get_screenshot_as_png(),
                name="Failure Screenshot",
                attachment_type=allure.attachment_type.PNG
            )
        except:
            pass

    driver.quit()


# ============================================================
# pytest hook
# ============================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ============================================================
# 구글 검색 테스트 (Chrome)
# ============================================================

@allure.epic("QA Portfolio Phase 3")
@allure.feature("구글 검색")
@allure.story("기본 검색 시나리오")
class TestGoogleSearchChrome:
    """구글 검색 - Chrome"""

    @allure.title("구글 홈페이지 로딩")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.tag("smoke", "critical")
    def test_google_home(self, chrome_driver):
        with allure.step("구글 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("타이틀 검증"):
            assert "Google" in chrome_driver.title
            allure.attach(chrome_driver.title, "Page Title", allure.attachment_type.TEXT)

        print("\n  → Chrome: 구글 홈 로딩 성공")

    @allure.title("검색 기능 동작 확인")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "functional")
    @pytest.mark.parametrize("keyword,expected", [
        ("python", "Python"),
        ("docker", "Docker"),
    ])
    def test_search(self, chrome_driver, keyword, expected):
        with allure.step(f"'{keyword}' 검색"):
            chrome_driver.get("https://www.google.com")
            search_bar = chrome_driver.find_element(By.NAME, "q")
            search_bar.send_keys(keyword)
            search_bar.submit()
            time.sleep(2)

        with allure.step("결과 확인"):
            assert expected.lower() in chrome_driver.title.lower()

        print(f"\n  → Chrome: '{keyword}' 검색 성공")


# ============================================================
# 네이버 검색 테스트 (Firefox)
# ============================================================

@allure.epic("QA Portfolio Phase 3")
@allure.feature("네이버 검색")
@allure.story("한글 검색 시나리오")
class TestNaverSearchFirefox:
    """네이버 검색 - Firefox"""

    @allure.title("네이버 홈페이지 로딩")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.tag("smoke")
    def test_naver_home(self, firefox_driver):
        with allure.step("네이버 접속"):
            firefox_driver.get("https://www.naver.com")

        with allure.step("타이틀 검증"):
            assert "NAVER" in firefox_driver.title

        print("\n  → Firefox: 네이버 홈 로딩 성공")

    @allure.title("한글 검색 기능")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("functional")
    def test_korean_search(self, firefox_driver):
        with allure.step("네이버 접속"):
            firefox_driver.get("https://www.naver.com")

        with allure.step("'파이썬' 검색"):
            search_bar = firefox_driver.find_element(By.ID, "query")
            search_bar.send_keys("파이썬")
            search_bar.submit()
            time.sleep(2)

        with allure.step("결과 확인"):
            assert "파이썬" in firefox_driver.title

        print("\n  → Firefox: 한글 검색 성공")


# ============================================================
# 크로스 브라우저 테스트
# ============================================================

@allure.epic("QA Portfolio Phase 3")
@allure.feature("크로스 브라우저 테스트")
@allure.story("동일 시나리오 멀티 브라우저 검증")
class TestCrossBrowser:
    """크로스 브라우저 테스트"""

    @allure.title("Chrome에서 검색창 확인")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_bar_chrome(self, chrome_driver):
        chrome_driver.get("https://www.google.com")
        search_bar = chrome_driver.find_element(By.NAME, "q")
        assert search_bar.is_displayed()
        print("\n  → Chrome: 검색창 확인 완료")

    @allure.title("Firefox에서 검색창 확인")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_bar_firefox(self, firefox_driver):
        firefox_driver.get("https://www.google.com")
        search_bar = firefox_driver.find_element(By.NAME, "q")
        assert search_bar.is_displayed()
        print("\n  → Firefox: 검색창 확인 완료")


# ============================================================
# 성능 측정 (간단)
# ============================================================

@allure.epic("QA Portfolio Phase 3")
@allure.feature("성능 테스트")
@allure.story("페이지 로딩 시간 측정")
class TestPerformance:
    """간단한 성능 측정"""

    @allure.title("구글 페이지 로딩 시간")
    @allure.severity(allure.severity_level.MINOR)
    def test_loading_time(self, chrome_driver):
        with allure.step("로딩 시간 측정 시작"):
            start = time.time()
            chrome_driver.get("https://www.google.com")
            load_time = time.time() - start

        with allure.step(f"로딩 시간: {load_time:.2f}초"):
            allure.attach(f"{load_time:.2f}s", "Load Time", allure.attachment_type.TEXT)
            assert load_time < 5, f"로딩 시간 초과: {load_time:.2f}초"

        print(f"\n  → 로딩 시간: {load_time:.2f}초")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 43: Allure 리포트 종합 테스트 통합")
    print("=" * 60)
    print("\n[실행 방법]")
    print("  py -m pytest day43_allure_final.py -v -s --alluredir=./allure-results")
    print("  allure serve ./allure-results")
    print("\n[주요 구성]")
    print("  - Epic/Feature/Story로 계층 구조 분류")
    print("  - Tag로 smoke/functional 테스트 구분")
    print("  - Chrome/Firefox 크로스 브라우저")
    print("  - 성능 측정 포함")

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=./allure-results"
    ])