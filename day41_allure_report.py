import pytest
import allure
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 픽스처 (allure 리포트에 자동 기록)
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver():
    """Chrome RemoteWebDriver 픽스처"""
    allure.dynamic.parameter("Browser", "Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    yield driver

    # 테스트 실패 시 스크린샷 자동 첨부
    if hasattr(driver, 'get_screenshot_as_png'):
        allure.attach(
            driver.get_screenshot_as_png(),
            name="Final Screenshot",
            attachment_type=allure.attachment_type.PNG
        )
    driver.quit()


# ============================================================
# Allure Feature/Story/Severity 활용 테스트
# ============================================================

@allure.feature("구글 검색 기능")
@allure.story("기본 검색")
class TestGoogleSearch:
    """구글 검색 테스트 - Allure 리포트에 Feature/Story로 분류"""

    @allure.title("구글 홈페이지 로딩 테스트")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("구글 메인 페이지가 정상적으로 로딩되는지 확인")
    def test_google_home(self, chrome_driver):
        """구글 홈 페이지 로딩"""
        with allure.step("구글 홈페이지 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("페이지 타이틀 확인"):
            assert "Google" in chrome_driver.title
            allure.attach(chrome_driver.title, name="Page Title", attachment_type=allure.attachment_type.TEXT)

        print(f"\n  → 구글 홈 로딩 성공")

    @allure.title("검색창 존재 확인")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_bar_exists(self, chrome_driver):
        """검색창 표시 확인"""
        with allure.step("구글 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("검색창 요소 찾기"):
            search_bar = chrome_driver.find_element(By.NAME, "q")

        with allure.step("검색창 표시 여부 검증"):
            assert search_bar.is_displayed()
            allure.attach("검색창 정상 표시됨", name="Validation Result", attachment_type=allure.attachment_type.TEXT)

        print(f"\n  → 검색창 존재 확인 완료")

    @allure.title("키워드 검색 기능 테스트")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("keyword,expected", [
        ("python", "Python"),
        ("docker", "Docker"),
    ])
    def test_search_keyword(self, chrome_driver, keyword, expected):
        """키워드 검색 기능"""
        with allure.step(f"'{keyword}' 검색 실행"):
            chrome_driver.get("https://www.google.com")
            search_bar = chrome_driver.find_element(By.NAME, "q")
            search_bar.send_keys(keyword)
            search_bar.submit()
            time.sleep(2)

        with allure.step("검색 결과 타이틀 검증"):
            assert expected.lower() in chrome_driver.title.lower()
            allure.attach(chrome_driver.title, name=f"Search Result for '{keyword}'",
                          attachment_type=allure.attachment_type.TEXT)

        print(f"\n  → '{keyword}' 검색 성공")


@allure.feature("네이버 검색 기능")
@allure.story("한글 검색")
class TestNaverSearch:
    """네이버 검색 테스트"""

    @allure.title("네이버 홈페이지 로딩")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_naver_home(self, chrome_driver):
        """네이버 홈 로딩"""
        with allure.step("네이버 접속"):
            chrome_driver.get("https://www.naver.com")

        with allure.step("타이틀 확인"):
            assert "NAVER" in chrome_driver.title

        print(f"\n  → 네이버 홈 로딩 성공")


@allure.feature("의도적 실패 테스트")
@allure.story("스크린샷 자동 첨부 검증")
class TestFailureWithScreenshot:
    """실패 시 스크린샷 자동 첨부 테스트"""

    @allure.title("의도적 실패 테스트 (스크린샷 확인용)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.skip(reason="실패 테스트용 - 필요 시 skip 제거")
    def test_intentional_failure(self, chrome_driver):
        """의도적으로 실패시켜 스크린샷 첨부 확인"""
        with allure.step("구글 접속"):
            chrome_driver.get("https://www.google.com")

        with allure.step("의도적 실패 (스크린샷 자동 첨부됨)"):
            assert False, "스크린샷 자동 첨부 테스트용 실패"


# ============================================================
# 직접 실행 시 allure 결과 생성
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 41: Allure Report 통합 및 결과 시각화")
    print("=" * 60)
    print("\n[안내] 실행 방법:")
    print("  pytest day41_allure_report.py -v -s --alluredir=./allure-results")
    print("  allure serve ./allure-results  # 리포트 확인 (Allure 설치 필요)")
    print("\n[중요] Allure 설치:")
    print("  Windows: scoop install allure")
    print("  Mac: brew install allure")

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=./allure-results"
    ])