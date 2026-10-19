"""
Day 68 : 응답 조작(500·점검·지연) 시 상점 페이지(클라이언트) 처리 확인
- Chrome(headless)을 프록시(mitmproxy + AutoResponder 애드온) 경유로 띄워 상점 페이지에서 로그인 → 구매
- 화면에 보이는 상태(재화·인벤토리·안내 문구)와 DB 변화를 기록하고 스크린샷 저장
- 지연 모드에서는 응답을 기다리는 동안 [구매]를 한 번 더 눌러 중복 구매 여부 확인
실행: py day68_client_check.py
"""

import contextlib
import io
import json
import os
import socket
import sys
import time

import pymysql
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from day59_apply_schema import APP_PASSWORD, APP_USER, DB_HOST, DB_NAME, DB_PORT, apply_schema
from day66_proxy_lab import BASE_DIR, PROXY_PORT, start_mitm, start_server, stop

sys.stdout.reconfigure(encoding="utf-8")

PAGE_URL = "http://127.0.0.1:8000/shop"
MODE_FILE = os.path.join(BASE_DIR, "handoff", "day68_mode.json")
SHOT_DIR = os.path.join(BASE_DIR, "day68_screenshots")

# (모드, 설명, 응답 대기 중 [구매] 추가 클릭 여부)
SCENARIOS = [
    ({"mode": "none"}, "정상 응답 (기준)", False),
    ({"mode": "error500"}, "500 Internal Server Error", False),
    ({"mode": "maintenance"}, "503 점검 중", False),
    ({"mode": "delay", "delay_seconds": 6}, "응답 6초 지연 + 대기 중 [구매] 한 번 더", True),
]


def db_state():
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER, password=APP_PASSWORD, database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM account_currency WHERE account_id = 1 AND currency_type = 'FC'")
            fc = int(cur.fetchone()["balance"])
            cur.execute("SELECT COUNT(*) AS n FROM purchase_history WHERE account_id = 1")
            purchases = cur.fetchone()["n"]
        return fc, purchases
    finally:
        conn.close()


def reset_db():
    with contextlib.redirect_stdout(io.StringIO()):
        apply_schema()


def assert_ports_free(*ports):
    """이미 떠 있는 서버가 있으면 새 서버가 바인딩에 실패하고 엉뚱한 서버로 접속하므로 먼저 확인"""
    for port in ports:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"[중단] 127.0.0.1:{port}에 이미 실행 중인 프로세스가 있습니다. 종료 후 다시 실행하세요.")


def new_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=480,1100")
    options.add_argument(f"--proxy-server=http://127.0.0.1:{PROXY_PORT}")
    options.add_argument("--proxy-bypass-list=<-loopback>")  # 127.0.0.1도 프록시를 거치게
    return webdriver.Chrome(options=options)


def run_scenario(driver, mode, desc, double_click, index):
    reset_db()
    with open(MODE_FILE, "w", encoding="utf-8") as f:
        json.dump(mode, f)
    driver.get(PAGE_URL)
    wait = WebDriverWait(driver, 15)
    driver.find_element(By.ID, "btn-login").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "status"), "로그인됨"))
    wait.until(EC.text_to_be_present_in_element((By.ID, "balances"), "FC"))
    fc_before, _ = db_state()

    buy = driver.find_element(By.CSS_SELECTOR, "button[data-item='101']")
    started = time.time()
    buy.click()
    if double_click:
        time.sleep(1.5)
        clickable = buy.is_enabled()
        buy.click()  # 응답이 안 와서 다시 누르는 사용자
    else:
        clickable = None
    # 구매 응답이 로그에 찍힐 때까지 대기 (지연 모드는 최대 15초)
    WebDriverWait(driver, 20).until(lambda d: "POST /shop/purchase" in d.find_element(By.ID, "log").text)
    if double_click:
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.ID, "log").text.count("POST /shop/purchase") >= 2)
    elapsed = time.time() - started
    time.sleep(1)

    fc_after, purchases = db_state()
    log_lines = [line for line in driver.find_element(By.ID, "log").text.splitlines() if "/shop/purchase" in line]
    alerts = driver.execute_script("return document.querySelectorAll('[role=alert], .error, .toast').length")
    shot = os.path.join(SHOT_DIR, f"day68_client_{index}_{mode['mode']}.png")
    driver.save_screenshot(shot)
    return {
        "desc": desc, "mode": mode["mode"], "elapsed": round(elapsed, 1),
        "balances_text": driver.find_element(By.ID, "balances").text,
        "purchase_log": log_lines, "alerts": alerts, "button_enabled_while_waiting": clickable,
        "fc_change": fc_after - fc_before, "purchases": purchases, "screenshot": os.path.relpath(shot, BASE_DIR),
    }


def main():
    assert_ports_free(8000, PROXY_PORT)
    os.makedirs(SHOT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
    reset_db()
    print("[1] HTTP 서버 기동: py day65_serve_client.py --no-reset (127.0.0.1:8000)")
    server = start_server(["day65_serve_client.py", "--no-reset"], "http://127.0.0.1:8000/openapi.json")
    print(f"[2] AutoResponder 프록시 기동: mitmdump -s day68_autoresponder_addon.py (127.0.0.1:{PROXY_PORT})")
    mitm = start_mitm("day68_autoresponder_addon.py", {"mode_file": MODE_FILE})
    driver = None
    results = []
    try:
        print("[3] Chrome(headless) 프록시 경유로 상점 페이지 조작\n")
        driver = new_driver()
        for i, (mode, desc, double_click) in enumerate(SCENARIOS, 1):
            r = run_scenario(driver, mode, desc, double_click, i)
            results.append(r)
            print(f"  [{r['mode']}] {r['desc']} ({r['elapsed']}초)")
            for line in r["purchase_log"]:
                print(f"    화면 로그: {line}")
            print(f"    재화 표시: {r['balances_text']} / 사용자 안내 요소: {r['alerts']}개"
                  + (f" / 대기 중 구매 버튼 활성: {r['button_enabled_while_waiting']}"
                     if r["button_enabled_while_waiting"] is not None else ""))
            print(f"    DB: FC {r['fc_change']:+d}, 구매 이력 {r['purchases']}건 / 스크린샷 {r['screenshot']}\n")
    finally:
        if driver:
            driver.quit()
        stop(mitm)
        stop(server)
        reset_db()

    print("[4] 클라이언트 처리 판정")
    findings = []
    by_mode = {r["mode"]: r for r in results}
    for m in ("error500", "maintenance"):
        if by_mode[m]["alerts"] == 0:
            findings.append(f"{m}: 사용자에게 보이는 오류·점검 안내 없음 (개발용 로그에만 상태 코드 표시)")
    d = by_mode["delay"]
    if d["button_enabled_while_waiting"]:
        findings.append("delay: 응답 대기 중 구매 버튼이 비활성화되지 않아 다시 누를 수 있음")
    if d["purchases"] >= 2:
        findings.append(f"delay: 재클릭이 새 request_id로 전송돼 중복 구매 {d['purchases']}건, FC {d['fc_change']:+d}")
    for f in findings:
        print(f"  - {f}")
    print(f"\n[결과] 시나리오 {len(results)}개 실행, 클라이언트 처리 결함 {len(findings)}건")


if __name__ == "__main__":
    main()
