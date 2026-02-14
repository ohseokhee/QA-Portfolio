import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

GRID_URL = "http://localhost:4444/wd/hub"

TEST_URLS = [
    "https://www.google.com",
    "https://www.naver.com",
    "https://www.github.com",
    "https://www.wikipedia.org",
    "https://www.python.org",
]


def get_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Remote(command_executor=GRID_URL, options=options)


def get_firefox_driver():
    options = webdriver.FirefoxOptions()
    return webdriver.Remote(command_executor=GRID_URL, options=options)


def run_single_test(test_info):
    """단일 테스트: URL 접속 후 타이틀 반환"""
    index, url, browser = test_info
    driver = None
    try:
        if browser == "chrome":
            driver = get_chrome_driver()
        else:
            driver = get_firefox_driver()

        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        title = driver.title
        return {"index": index, "url": url, "browser": browser, "title": title, "status": "PASS"}
    except Exception as e:
        return {"index": index, "url": url, "browser": browser, "title": "", "status": "FAIL", "error": str(e)}
    finally:
        if driver:
            driver.quit()


def run_sequential(test_cases):
    """순차 실행"""
    print("\n[순차 실행] 시작...")
    start = time.time()
    results = []
    for case in test_cases:
        result = run_single_test(case)
        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"  {status_icon} [{result['browser'].upper()}] {result['url']} → {result['title'][:30]}")
        results.append(result)
    elapsed = time.time() - start
    return results, elapsed


def run_parallel(test_cases, max_workers=5):
    """병렬 실행"""
    print("\n[병렬 실행] 시작...")
    start = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_test, case): case for case in test_cases}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {status_icon} [{result['browser'].upper()}] {result['url']} → {result['title'][:30]}")
            results.append(result)
    elapsed = time.time() - start
    return results, elapsed


def print_summary(seq_results, seq_time, par_results, par_time):
    """결과 요약 출력"""
    print("\n" + "=" * 60)
    print("[최종 결과] 순차 vs 병렬 성능 비교")
    print("=" * 60)

    seq_pass = sum(1 for r in seq_results if r["status"] == "PASS")
    par_pass = sum(1 for r in par_results if r["status"] == "PASS")
    total = len(seq_results)

    print(f"""
  ┌──────────────────────────────────────────────┐
  │            성능 비교 결과                    │
  ├──────────────┬───────────────┬───────────────┤
  │              │   순차 실행   │   병렬 실행   │
  ├──────────────┼───────────────┼───────────────┤
  │ 총 테스트 수  │   {total}개       │   {total}개       │
  │ 성공         │   {seq_pass}개       │   {par_pass}개       │
  │ 실패         │   {total - seq_pass}개       │   {total - par_pass}개       │
  │ 실행 시간    │  {seq_time:.1f}초      │  {par_time:.1f}초      │
  │ 속도 향상    │      -        │  {seq_time/par_time:.1f}배 빠름  │
  └──────────────┴───────────────┴───────────────┘
    """)


def run_day37_parallel_test():
    # Chrome 5개 + Firefox 5개 = 총 10개 테스트
    test_cases = []
    for i, url in enumerate(TEST_URLS):
        test_cases.append((i * 2, url, "chrome"))
        test_cases.append((i * 2 + 1, url, "firefox"))

    print("=" * 60)
    print("Day 37: 순차 vs 병렬 테스트 성능 비교")
    print(f"총 테스트 케이스: {len(test_cases)}개 (Chrome {len(TEST_URLS)}개 + Firefox {len(TEST_URLS)}개)")
    print("=" * 60)

    # 순차 실행
    seq_results, seq_time = run_sequential(test_cases)
    print(f"  → 순차 실행 완료: {seq_time:.1f}초")

    # 병렬 실행
    par_results, par_time = run_parallel(test_cases, max_workers=6)
    print(f"  → 병렬 실행 완료: {par_time:.1f}초")

    # 최종 요약
    print_summary(seq_results, seq_time, par_results, par_time)


if __name__ == "__main__":
    run_day37_parallel_test()