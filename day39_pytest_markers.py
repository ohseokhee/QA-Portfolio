import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# conftest.py 역할 (단일 파일 실습용)
# ============================================================

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 픽스처 정의
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver():
    """Chrome RemoteWebDriver 픽스처"""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def firefox_driver():
    """Firefox RemoteWebDriver 픽스처"""
    options = webdriver.FirefoxOptions()
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


# ============================================================
# 테스트 클래스 - Marker 적용
# ============================================================

@pytest.mark.smoke
class TestGoogleSmoke:
    """구글 스모크 테스트 - 핵심 기능만 빠르게 검증"""

    def test_google_homepage_loads(self, chrome_driver):
        """구글 홈페이지 로딩 확인"""
        chrome_driver.get("https://www.google.com")
        assert "Google" in chrome_driver.title
        print(f"\n  → 스모크 테스트: 구글 홈 로딩 성공")

    def test_search_bar_visible(self, chrome_driver):
        """검색창 표시 확인"""
        chrome_driver.get("https://www.google.com")
        search_bar = chrome_driver.find_element(By.NAME, "q")
        assert search_bar.is_displayed()
        print(f"\n  → 스모크 테스트: 검색창 존재 확인")


@pytest.mark.regression
class TestGoogleRegression:
    """구글 회귀 테스트 - 전체 기능 검증"""

    @pytest.mark.parametrize("keyword,expected", [
        ("python", "Python"),
        ("selenium", "Selenium"),
        ("docker", "Docker"),
    ])
    def test_search_functionality(self, chrome_driver, keyword, expected):
        """검색 기능 회귀 테스트"""
        chrome_driver.get("https://www.google.com")
        search_bar = chrome_driver.find_element(By.NAME, "q")
        search_bar.send_keys(keyword)
        search_bar.submit()
        time.sleep(2)
        assert expected.lower() in chrome_driver.title.lower()
        print(f"\n  → 회귀 테스트: '{keyword}' 검색 성공")


@pytest.mark.sanity
class TestNaverSanity:
    """네이버 정합성 테스트 - 기본 동작 확인"""

    def test_naver_homepage(self, firefox_driver):
        """네이버 홈 접속 확인"""
        firefox_driver.get("https://www.naver.com")
        assert "NAVER" in firefox_driver.title
        print(f"\n  → 정합성 테스트: 네이버 홈 로딩 성공")

    @pytest.mark.slow
    def test_naver_search(self, firefox_driver):
        """네이버 검색 기능 확인 (느린 테스트)"""
        firefox_driver.get("https://www.naver.com")
        search_bar = firefox_driver.find_element(By.ID, "query")
        search_bar.send_keys("pytest")
        search_bar.submit()
        time.sleep(3)  # 의도적으로 느리게 설정
        assert "pytest" in firefox_driver.title or firefox_driver.current_url
        print(f"\n  → 정합성 테스트: 네이버 검색 완료 (느림)")


@pytest.mark.skip(reason="외부 API 의존성으로 임시 스킵")
class TestExternalAPI:
    """외부 API 테스트 - 현재 스킵"""

    def test_api_call(self):
        """API 호출 테스트 (스킵됨)"""
        pass


# ============================================================
# 직접 실행 시 pytest 자동 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 39: Pytest 마커 + HTML 리포트 생성")
    print("=" * 60)
    print("\n[안내] 실행 방법:")
    print("  pytest day39_pytest_markers.py -v -s")
    print("  pytest day39_pytest_markers.py -v -s -m smoke  # 스모크 테스트만")
    print("  pytest day39_pytest_markers.py -v -s -m 'not slow'  # 느린 테스트 제외")
    print("  pytest day39_pytest_markers.py -v -s --html=report.html --self-contained-html")

    # HTML 리포트 생성 실행
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--html=day39_report.html",
        "--self-contained-html",
        "-m", "smoke or sanity"  # 스모크 + 정합성만 실행
    ])