import pytest
from selenium import webdriver

GRID_URL = "http://localhost:4444/wd/hub"


# ============================================================
# 공통 픽스처 (모든 테스트 파일에서 자동으로 사용 가능)
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


@pytest.fixture(scope="session")
def test_config():
    """테스트 설정값 - session scope로 전체 테스트 세션 동안 1번만 생성"""
    return {
        "base_url": "https://www.google.com",
        "timeout": 10,
        "browser": "chrome"
    }


# ============================================================
# pytest hook - HTML 리포트 커스터마이징
# ============================================================

def pytest_html_report_title(report):
    """HTML 리포트 타이틀 설정"""
    report.title = "QA Portfolio - Day 40 Test Report"


def pytest_configure(config):
    """pytest 실행 전 초기 설정"""
    config._metadata = {
        "Tester": "QA Engineer",
        "Project": "QA-DevOps Portfolio",
        "Environment": "Grid (Selenium Hub)",
    }
