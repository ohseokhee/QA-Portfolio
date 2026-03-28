import os
import pytest
import pymysql
from selenium import webdriver

from bing_page import BingPage

# ── 환경변수 기반 설정 ────────────────────────────────────────────────────
GRID_URL = os.environ.get("GRID_URL", "http://localhost:4444/wd/hub")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3307)),
    "user": os.environ.get("DB_USER", "qa_user"),
    "password": os.environ.get("DB_PASSWORD", "qa_pass"),
    "database": os.environ.get("DB_NAME", "qa_db"),
}

SEARCH_KEYWORD = "Selenium Grid Docker"


# ── 픽스처 ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Remote(
        command_executor=GRID_URL,
        options=options,
    )
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="module")
def db_conn():
    conn = pymysql.connect(**DB_CONFIG)
    yield conn
    conn.close()


# ── 테스트 ────────────────────────────────────────────────────────────────
class TestE2ELite:

    def test_bing_search_chrome(self, chrome_driver, db_conn):
        """Bing 검색 → DB 저장 (Chrome)"""
        page = BingPage(chrome_driver)
        page.open()
        page.search(SEARCH_KEYWORD)
        title = page.get_result_title()

        assert title, "Bing 검색 결과 제목이 비어 있음"

        with db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO search_results (browser, site, keyword, result_title) "
                "VALUES (%s, %s, %s, %s)",
                ("chrome", "bing", SEARCH_KEYWORD, title),
            )
        db_conn.commit()
        print(f"[Chrome][Bing] 저장 완료: {title}")

    def test_db_verify(self, db_conn):
        """DB 저장 결과 검증"""
        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM search_results WHERE keyword = %s",
                (SEARCH_KEYWORD,),
            )
            count = cursor.fetchone()[0]

        assert count >= 1, f"DB 저장 건수 부족: {count}"
        print(f"[DB 검증] 저장된 검색 결과 건수: {count}")
