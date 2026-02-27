import pytest
import allure
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
import platform

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 픽스처 - 실패 시 스크린샷 자동 첨부
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver(request):
    """Chrome RemoteWebDriver 픽스처 - 실패 시 스크린샷 자동 첨부"""
    allure.dynamic.parameter("Browser", "Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)

    yield driver

    # 테스트 실패 시 스크린샷 자동 첨부
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        try:
            allure.attach(
                driver.get_screenshot_as_png(),
                name="Failure Screenshot",
                attachment_type=allure.attachment_type.PNG
            )
            allure.attach(
                driver.current_url,
                name="Failure URL",
                attachment_type=allure.attachment_type.TEXT
            )
            allure.attach(
                driver.page_source,
                name="Page Source (HTML)",
                attachment_type=allure.attachment_type.HTML
            )
        except Exception as e:
            print(f"\n  → 스크린샷 첨부 실패: {e}")

    driver.quit()


# ============================================================
# pytest hook - 테스트 결과 캡처
# ============================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """테스트 결과를 픽스처에서 사용 가능하도록 저장"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ============================================================
# 환경 정보 자동 첨부
# ============================================================

def pytest_configure(config):
    """Allure 환경 정보 설정"""
    allure_dir = config.getoption("--alluredir")
    if allure_dir:
        env_properties = os.path.join(allure_dir, "environment.properties")
        with open(env_properties, "w", encoding="utf-8") as f:
            f.write(f"Browser=Chrome (via Selenium Grid)\n")
            f.write(f"Grid.URL={GRID_URL}\n")
            f.write(f"OS={platform.system()} {platform.release()}\n")
            f.write(f"Python.Version={platform.python_version()}\n")
            f.write(f"Test.Framework=Pytest + Allure\n")


# ============================================================
# 테스트 케이스
# ============================================================

@allure.feature("구글 검색")
@allure.story("정상 시나리오")
class TestGoogleSuccess:
    """성공 테스트 - 스크린샷 미첨부"""

    @allure.title("구글 검색 성공 케이스")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_google_search_success(self, chrome_driver):
        """정상 검색 (스크린샷 첨부 안 됨)"""
        with allure.step("구글 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("'python' 검색"):
            search_bar = chrome_driver.find_element(By.NAME, "q")
            search_bar.send_keys("python")
            search_bar.submit()
            time.sleep(2)

        with allure.step("결과 확인"):
            assert "python" in chrome_driver.title.lower()
            # 성공 시에도 스크린샷 수동 첨부 가능
            allure.attach(
                chrome_driver.get_screenshot_as_png(),
                name="Success Screenshot",
                attachment_type=allure.attachment_type.PNG
            )

        print(f"\n  → 검색 성공")


@allure.feature("구글 검색")
@allure.story("실패 시나리오")
class TestGoogleFailure:
    """실패 테스트 - 스크린샷 자동 첨부"""

    @allure.title("잘못된 검색 결과 검증 (의도적 실패)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.xfail(reason="스크린샷 자동 첨부 데모용")
    def test_google_search_failure(self, chrome_driver):
        """실패 시 스크린샷 자동 첨부 확인"""
        with allure.step("구글 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("'docker' 검색"):
            search_bar = chrome_driver.find_element(By.NAME, "q")
            search_bar.send_keys("docker")
            search_bar.submit()
            time.sleep(2)

        with allure.step("잘못된 결과 검증 (의도적 실패)"):
            # 의도적으로 실패 → 자동으로 스크린샷 첨부됨
            assert "python" in chrome_driver.title.lower(), "검색 결과가 예상과 다름 (스크린샷 자동 첨부됨)"

        print(f"\n  → 의도적 실패 완료")


@allure.feature("네이버 검색")
@allure.story("타임아웃 테스트")
class TestNaverTimeout:
    """타임아웃 실패 - 스크린샷 자동 첨부"""

    @allure.title("존재하지 않는 요소 찾기 (타임아웃)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.xfail(reason="타임아웃 실패 데모용")
    def test_element_not_found(self, chrome_driver):
        """요소 못 찾아서 실패 시 스크린샷 자동 첨부"""
        with allure.step("네이버 접속"):
            chrome_driver.get("https://www.naver.com")

        with allure.step("존재하지 않는 요소 찾기"):
            chrome_driver.implicitly_wait(3)
            # 의도적으로 없는 요소 → NoSuchElementException → 스크린샷 첨부
            chrome_driver.find_element(By.ID, "this_element_does_not_exist")

        print(f"\n  → 타임아웃 실패 완료")


@allure.feature("환경 정보")
@allure.story("메타데이터 첨부")
class TestEnvironmentInfo:
    """환경 정보 확인"""

    @allure.title("환경 정보 리포트 확인")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_environment_metadata(self, chrome_driver):
        """environment.properties 파일 생성 확인"""
        with allure.step("간단한 동작 수행"):
            chrome_driver.get("https://www.google.com")
            assert "Google" in chrome_driver.title

        with allure.step("환경 정보 첨부"):
            env_info = f"""
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}
Browser: Chrome (Grid)
Grid URL: {GRID_URL}
            """
            allure.attach(env_info, name="Test Environment", attachment_type=allure.attachment_type.TEXT)

        print(f"\n  → 환경 정보 첨부 완료")


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 42: Allure 스크린샷 자동화 + 환경 정보 첨부")
    print("=" * 60)
    print("\n[안내] 실행 방법:")
    print("  pytest day42_allure_advanced.py -v -s --alluredir=./allure-results")
    print("  allure serve ./allure-results")
    print("\n[주요 기능]")
    print("  1. 실패 시 자동으로 스크린샷, URL, HTML 소스 첨부")
    print("  2. environment.properties로 테스트 환경 정보 리포트에 표시")
    print("  3. @pytest.mark.xfail로 예상된 실패 케이스 관리")

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=./allure-results"
    ])