import pytest
import allure
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pymysql
import time

GRID_URL = "http://localhost:4444/wd/hub"
DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "testuser",
    "password": "testpass",
    "database": "testdb"
}


# ============================================================
# 픽스처
# ============================================================

@pytest.fixture(scope="function")
def chrome_driver(request):
    """Chrome RemoteWebDriver 픽스처"""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(command_executor=GRID_URL, options=options)
    driver.implicitly_wait(10)
    driver.maximize_window()

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


@pytest.fixture(scope="session")
def db_connection():
    """MariaDB 연결 픽스처"""
    conn = pymysql.connect(**DB_CONFIG)
    yield conn
    conn.close()


# ============================================================
# pytest hook
# ============================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def pytest_configure(config):
    """환경 정보 설정"""
    allure_dir = config.getoption("--alluredir")
    if allure_dir:
        import os
        import platform
        env_properties = os.path.join(allure_dir, "environment.properties")
        with open(env_properties, "w", encoding="utf-8") as f:
            f.write(f"Project=QA Portfolio Phase 3 통합\n")
            f.write(f"Grid.URL={GRID_URL}\n")
            f.write(f"Database=MariaDB 10.6\n")
            f.write(f"OS={platform.system()} {platform.release()}\n")
            f.write(f"Python={platform.python_version()}\n")


# ============================================================
# E2E 테스트 시나리오
# ============================================================

@allure.epic("Phase 3 통합 프로젝트")
@allure.feature("구글 검색 E2E")
@allure.story("검색 후 DB 기록 검증")
class TestGoogleSearchE2E:
    """구글 검색 E2E 테스트"""

    @allure.title("구글 검색 전체 플로우")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_and_db_verify(self, chrome_driver, db_connection):
        """검색 → 결과 확인 → DB 기록 → 검증"""

        search_keyword = "Docker"

        with allure.step("1. 구글 홈페이지 접속"):
            chrome_driver.get("https://www.google.com")
            assert "Google" in chrome_driver.title
            allure.attach(chrome_driver.current_url, "URL", allure.attachment_type.TEXT)

        with allure.step(f"2. '{search_keyword}' 검색"):
            search_bar = chrome_driver.find_element(By.NAME, "q")
            search_bar.send_keys(search_keyword)
            search_bar.submit()
            time.sleep(2)

        with allure.step("3. 검색 결과 확인"):
            assert search_keyword.lower() in chrome_driver.title.lower()
            result_title = chrome_driver.title
            allure.attach(result_title, "Search Result Title", allure.attachment_type.TEXT)

        with allure.step("4. DB에 검색 기록 저장"):
            cursor = db_connection.cursor()
            # 테이블 생성 (없으면)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    keyword VARCHAR(255),
                    result_title VARCHAR(255),
                    search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 검색 기록 삽입
            cursor.execute(
                "INSERT INTO search_history (keyword, result_title) VALUES (%s, %s)",
                (search_keyword, result_title)
            )
            db_connection.commit()
            allure.attach(f"Keyword: {search_keyword}", "DB Insert", allure.attachment_type.TEXT)

        with allure.step("5. DB에서 검색 기록 확인"):
            cursor.execute("SELECT * FROM search_history ORDER BY id DESC LIMIT 1")
            record = cursor.fetchone()
            assert record is not None, "DB에 기록이 없습니다"
            assert record[1] == search_keyword, "키워드가 일치하지 않습니다"
            allure.attach(str(record), "DB Record", allure.attachment_type.TEXT)

        cursor.close()
        print(f"\n  → E2E 테스트 완료: {search_keyword} 검색 및 DB 검증 성공")


@allure.epic("Phase 3 통합 프로젝트")
@allure.feature("네이버 검색 E2E")
@allure.story("한글 검색 및 DB 기록")
class TestNaverSearchE2E:
    """네이버 검색 E2E 테스트"""

    @allure.title("네이버 한글 검색 플로우")
    @allure.severity(allure.severity_level.NORMAL)
    def test_naver_search_e2e(self, chrome_driver, db_connection):
        """네이버 검색 → DB 기록"""

        search_keyword = "파이썬"

        with allure.step("1. 네이버 접속"):
            chrome_driver.get("https://www.naver.com")
            assert "NAVER" in chrome_driver.title

        with allure.step(f"2. '{search_keyword}' 검색"):
            search_bar = chrome_driver.find_element(By.ID, "query")
            search_bar.send_keys(search_keyword)
            search_bar.submit()
            time.sleep(2)

        with allure.step("3. 검색 결과 확인"):
            assert search_keyword in chrome_driver.title
            result_title = chrome_driver.title

        with allure.step("4. DB에 기록 저장"):
            cursor = db_connection.cursor()
            cursor.execute(
                "INSERT INTO search_history (keyword, result_title) VALUES (%s, %s)",
                (search_keyword, result_title)
            )
            db_connection.commit()
            cursor.close()

        print(f"\n  → 네이버 E2E 테스트 완료: {search_keyword}")


@allure.epic("Phase 3 통합 프로젝트")
@allure.feature("DB 통합 테스트")
@allure.story("데이터 조회 및 통계")
class TestDatabaseIntegration:
    """DB 통합 테스트"""

    @allure.title("검색 기록 통계 조회")
    @allure.severity(allure.severity_level.MINOR)
    def test_search_statistics(self, db_connection):
        """DB에서 검색 통계 조회"""

        with allure.step("1. 전체 검색 기록 수 조회"):
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM search_history")
            total_count = cursor.fetchone()[0]
            allure.attach(f"Total: {total_count}", "Search Count", allure.attachment_type.TEXT)

        with allure.step("2. 최근 5개 검색 조회"):
            cursor.execute("SELECT keyword, search_time FROM search_history ORDER BY id DESC LIMIT 5")
            recent_searches = cursor.fetchall()
            allure.attach(str(recent_searches), "Recent Searches", allure.attachment_type.TEXT)

        cursor.close()
        print(f"\n  → DB 통계 조회 완료: 총 {total_count}건")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 44-45: Phase 3 통합 프로젝트 E2E 테스트")
    print("=" * 60)
    print("\n[사전 준비]")
    print("  docker-compose up -d")
    print("\n[실행 방법]")
    print("  py -m pytest day44_e2e_test.py -v -s --alluredir=./allure-results")
    print("  allure serve ./allure-results")
    print("\n[인프라 구성]")
    print("  - Selenium Hub + Chrome + Firefox")
    print("  - MariaDB (검색 기록 저장)")
    print("  - Pytest + Allure Report")

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=./allure-results"
    ])