import pytest
import time
from selenium.webdriver.common.by import By


# ============================================================
# conftest.py의 픽스처를 자동으로 사용 (import 불필요)
# ============================================================

@pytest.mark.smoke
class TestConfigUsage:
    """conftest.py의 픽스처 활용 테스트"""

    def test_using_test_config(self, chrome_driver, test_config):
        """test_config 픽스처 활용"""
        chrome_driver.get(test_config["base_url"])
        assert "Google" in chrome_driver.title
        print(f"\n  → config 활용: {test_config['base_url']} 접속 성공")

    def test_chrome_fixture_from_conftest(self, chrome_driver):
        """conftest.py의 chrome_driver 픽스처 활용"""
        chrome_driver.get("https://www.google.com")
        search_bar = chrome_driver.find_element(By.NAME, "q")
        assert search_bar.is_displayed()
        print(f"\n  → conftest 픽스처: Chrome 드라이버 정상 동작")


@pytest.mark.regression
class TestFirefoxFromConftest:
    """Firefox 픽스처 활용 테스트"""

    def test_firefox_fixture(self, firefox_driver):
        """conftest.py의 firefox_driver 픽스처 활용"""
        firefox_driver.get("https://www.naver.com")
        assert "NAVER" in firefox_driver.title
        print(f"\n  → conftest 픽스처: Firefox 드라이버 정상 동작")


@pytest.mark.sanity
class TestMultipleFixtures:
    """여러 픽스처 동시 활용"""

    def test_combined_fixtures(self, chrome_driver, test_config):
        """chrome_driver + test_config 동시 활용"""
        timeout = test_config["timeout"]
        chrome_driver.get("https://www.google.com")
        chrome_driver.implicitly_wait(timeout)
        print(f"\n  → 복합 픽스처: timeout {timeout}초 설정 완료")
        assert True


# ============================================================
# 직접 실행 시 pytest 자동 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 40: conftest.py 분리 + pytest.ini 설정")
    print("=" * 60)
    print("\n[안내] 실행 방법:")
    print("  pytest day40_test_conftest.py -v -s")
    print("  pytest day40_test_conftest.py -v -s -m smoke")
    print("  pytest day40_test_conftest.py -v -s --html=day40_report.html --self-contained-html")
    print("\n[중요] conftest.py와 pytest.ini가 같은 디렉토리에 있어야 합니다.")

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--html=day40_report.html",
        "--self-contained-html"
    ])