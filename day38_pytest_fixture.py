import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# conftest.py 역할을 이 파일에서 함께 수행 (단일 파일 실습용)
# 실제 프로젝트에서는 conftest.py를 별도 파일로 분리
# ============================================================

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 픽스처 정의
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver():
    """Chrome RemoteWebDriver 픽스처 - 테스트마다 생성/종료"""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def firefox_driver():
    """Firefox RemoteWebDriver 픽스처 - 테스트마다 생성/종료"""
    options = webdriver.FirefoxOptions()
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def wait(chrome_driver):
    """WebDriverWait 픽스처 - chrome_driver에 의존"""
    return WebDriverWait(chrome_driver, 15)


# ============================================================
# 테스트 클래스
# ============================================================

class TestGoogleSearch:
    """구글 검색 테스트 - Chrome"""

    def test_google_title(self, chrome_driver):
        """구글 홈 타이틀 확인"""
        chrome_driver.get("https://www.google.com")
        assert "Google" in chrome_driver.title
        print(f"\n  → 타이틀 확인: {chrome_driver.title}")

    def test_google_search_bar_exists(self, chrome_driver, wait):
        """검색창 존재 여부 확인"""
        chrome_driver.get("https://www.google.com")
        search_bar = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        assert search_bar.is_displayed()
        print("\n  → 검색창 존재 확인 완료")

    @pytest.mark.parametrize("keyword,expected", [
        ("python", "Python"),
        ("selenium", "Selenium"),
        ("pytest", "pytest"),
    ])
    def test_search_result_title(self, chrome_driver, wait, keyword, expected):
        """파라미터화된 검색 결과 타이틀 검증"""
        chrome_driver.get("https://www.google.com")
        search_bar = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        search_bar.send_keys(keyword)
        search_bar.submit()
        time.sleep(2)
        assert expected.lower() in chrome_driver.title.lower()
        print(f"\n  → '{keyword}' 검색 결과 타이틀: {chrome_driver.title}")


class TestNaverSearch:
    """네이버 검색 테스트 - Firefox"""

    def test_naver_title(self, firefox_driver):
        """네이버 홈 타이틀 확인"""
        firefox_driver.get("https://www.naver.com")
        assert "NAVER" in firefox_driver.title
        print(f"\n  → 타이틀 확인: {firefox_driver.title}")

    def test_naver_search_bar_exists(self, firefox_driver):
        """네이버 검색창 존재 여부 확인"""
        firefox_driver.get("https://www.naver.com")
        search_bar = firefox_driver.find_element(By.ID, "query")
        assert search_bar.is_displayed()
        print("\n  → 네이버 검색창 존재 확인 완료")

    @pytest.mark.parametrize("keyword", ["파이썬", "셀레니움", "도커"])
    def test_naver_search_keyword(self, firefox_driver, keyword):
        """네이버 키워드 검색 실행"""
        firefox_driver.get("https://www.naver.com")
        search_bar = firefox_driver.find_element(By.ID, "query")
        search_bar.send_keys(keyword)
        search_bar.submit()
        time.sleep(2)
        assert keyword in firefox_driver.current_url or firefox_driver.title
        print(f"\n  → '{keyword}' 검색 완료: {firefox_driver.title[:30]}")


# ============================================================
# 직접 실행 시 pytest 자동 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 38: Pytest 픽스처 기반 테스트 리팩토링")
    print("=" * 60)
    print("\n[안내] 아래 명령어로 실행하세요:")
    print("  pytest day38_pytest_fixture.py -v")
    print("  pytest day38_pytest_fixture.py -v -s  # print 출력 포함")
    print("  pytest day38_pytest_fixture.py -v -s --tb=short  # 간략한 오류 출력")

    pytest.main([__file__, "-v", "-s"])