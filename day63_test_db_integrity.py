"""
Day 63 : 모의 게임 서버 DB 정합성 자동 검증 (pytest + requests + SQL 대조, Allure 리포트)
대상 TC: day59_api_spec.md 4.3의 실행 Day 63 (TC-GRANT-09, TC-SHOP-15, TC-SHOP-16, TC-INV-04, TC-DB-01)
실행: py -m pytest day63_test_db_integrity.py --alluredir=allure-results --clean-alluredir
"""

import json
import os
import subprocess
import sys
import time

import allure
import pymysql
import pytest
import requests

from day59_apply_schema import APP_PASSWORD, APP_USER, DB_HOST, DB_NAME, DB_PORT, apply_schema
from day60_smoke_check import wait_for_server

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "http://127.0.0.1:8000"
ACCOUNTS = {
    "user1": ("qa_user1", "Test1234!"),
    "user2": ("qa_user2", "Test1234!"),
    "admin": ("qa_admin", "Admin1234!"),
}


# ============================================================
# 헬퍼
# ============================================================

def api(method, path, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    res = requests.request(method, BASE_URL + path, json=body, headers=headers, timeout=5)
    try:
        data = res.json()
    except ValueError:
        data = {"raw": res.text}
    allure.attach(json.dumps({"request": {"method": method, "path": path, "body": body},
                              "status": res.status_code, "response": data}, ensure_ascii=False, indent=2),
                  name=f"{method} {path} → {res.status_code}", attachment_type=allure.attachment_type.JSON)
    return res.status_code, data


def query(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    allure.attach(f"{sql}\nparams={params}\n\n" + json.dumps(rows, ensure_ascii=False, indent=2, default=str),
                  name="SQL", attachment_type=allure.attachment_type.TEXT)
    return rows


def db_balances(conn, account_id):
    rows = query(conn, "SELECT currency_type, balance FROM account_currency WHERE account_id = %s", (account_id,))
    return {r["currency_type"]: r["balance"] for r in rows}


def snapshot(conn, account_id):
    """잔액·인벤토리·구매 이력·재화 이력 상태를 한 번에 읽는다 (R6 무변동 비교용)."""
    return {
        "balances": db_balances(conn, account_id),
        "inventory": {r["item_id"]: r["quantity"] for r in query(
            conn, "SELECT item_id, quantity FROM inventory WHERE account_id = %s", (account_id,))},
        "purchase_count": query(conn, "SELECT COUNT(*) AS n FROM purchase_history WHERE account_id = %s",
                                (account_id,))[0]["n"],
        "tx_count": query(conn, "SELECT COUNT(*) AS n FROM currency_transactions WHERE account_id = %s",
                          (account_id,))[0]["n"],
    }


def new_request_id(tag):
    return f"d63-{tag}-{time.time_ns()}"


# ============================================================
# 픽스처
# ============================================================

@pytest.fixture(scope="module")
def server():
    """시드 상태 DB로 서버를 띄우고, 끝나면 서버 종료 후 DB 재초기화"""
    apply_schema()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "day60_server_v1:app",
                             "--host", "127.0.0.1", "--port", "8000"],
                            cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_for_server()
    yield
    proc.terminate()
    proc.wait(timeout=10)
    apply_schema()


@pytest.fixture(scope="module")
def db(server):
    # autocommit: 매 조회마다 서버가 커밋한 최신 값을 읽음 (REPEATABLE READ 스냅샷 방지)
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER, password=APP_PASSWORD,
                           database=DB_NAME, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def initial_balances(db):
    """시드 직후 잔액 (TC-DB-01의 '초기 잔액'). autouse로 첫 테스트 전에 한 번 읽음"""
    rows = query(db, "SELECT account_id, currency_type, balance FROM account_currency")
    return {(r["account_id"], r["currency_type"]): r["balance"] for r in rows}


@pytest.fixture(scope="module")
def tokens(server):
    result = {}
    for key, (username, password) in ACCOUNTS.items():
        status, body = api("POST", "/auth/login", body={"username": username, "password": password})
        assert status == 200, f"준비 로그인 실패: {username} {status} {body}"
        result[key] = body["access_token"]
    return result


@pytest.fixture(scope="module")
def workload(tokens, initial_balances):
    """TC-INV-04·TC-DB-01용 '전체 실행': 지급·구매·멱등 재전송·명세상 거부/무시돼야 하는 요청을 섞어 보낸다"""
    idem_id = new_request_id("idem")
    steps = [
        ("ADMIN이 qa_user1에 FC 10000 지급", "admin", "/admin/currency/grant",
         {"account_id": 1, "currency_type": "FC", "amount": 10000, "memo": "Day63 준비"}),
        ("ADMIN이 qa_user2에 FC 2000 지급", "admin", "/admin/currency/grant",
         {"account_id": 2, "currency_type": "FC", "amount": 2000}),
        ("qa_user1 103 x 2 (BP)", "user1", "/shop/purchase",
         {"item_id": 103, "quantity": 2, "request_id": new_request_id("w1")}),
        ("qa_user1 104 x 1 (FC)", "user1", "/shop/purchase",
         {"item_id": 104, "quantity": 1, "request_id": new_request_id("w2")}),
        ("qa_user1 101 x 3 첫 요청", "user1", "/shop/purchase",
         {"item_id": 101, "quantity": 3, "request_id": idem_id}),
        ("qa_user1 101 x 3 같은 request_id 재전송 (R7)", "user1", "/shop/purchase",
         {"item_id": 101, "quantity": 3, "request_id": idem_id}),
        ("qa_user1 101 x 1 본문에 price 1 추가 (R5)", "user1", "/shop/purchase",
         {"item_id": 101, "quantity": 1, "price": 1, "request_id": new_request_id("w3")}),
        ("qa_user1 101 x 0 (R3 범위 밖)", "user1", "/shop/purchase",
         {"item_id": 101, "quantity": 0, "request_id": new_request_id("w4")}),
        ("qa_user2 101 x 2 (FC 2000 전액 사용)", "user2", "/shop/purchase",
         {"item_id": 101, "quantity": 2, "request_id": new_request_id("w5")}),
        ("qa_user2 102 x 1 (BP 0, 잔액 부족)", "user2", "/shop/purchase",
         {"item_id": 102, "quantity": 1, "request_id": new_request_id("w6")}),
    ]
    results = []
    with allure.step("전체 실행 워크로드"):
        for title, who, path, body in steps:
            with allure.step(title):
                status, data = api("POST", path, tokens[who], body)
                results.append((title, status))
    print("\n[워크로드]")
    for title, status in results:
        print(f"  {status}  {title}")
    return results


# ============================================================
# 테스트
# ============================================================

@allure.feature("DB 정합성")
@allure.story("재화 지급")
@allure.title("TC-GRANT-09 지급 1회 → currency_transactions에 +amount, operator_id = 3 기록")
def test_tc_grant_09_grant_transaction_logged(db, tokens):
    before = db_balances(db, 2)
    with allure.step("ADMIN이 qa_user2에 FC 5000 지급"):
        status, body = api("POST", "/admin/currency/grant", tokens["admin"],
                           {"account_id": 2, "currency_type": "FC", "amount": 5000, "memo": "TC-GRANT-09"})
        assert status == 200, body
    with allure.step("응답 tx_id로 currency_transactions 조회"):
        rows = query(db, "SELECT * FROM currency_transactions WHERE tx_id = %s", (body["tx_id"],))
        assert len(rows) == 1, "tx_id에 해당하는 변동 이력이 없음"
        tx = rows[0]
    with allure.step("이력 값 대조"):
        assert tx["account_id"] == 2
        assert tx["currency_type"] == "FC"
        assert tx["amount"] == 5000
        assert tx["reason"] == "GRANT"
        assert tx["operator_id"] == 3
        assert tx["memo"] == "TC-GRANT-09"
    with allure.step("응답 balance_after = 이력 balance_after = DB 잔액 = 지급 전 + 5000"):
        after = db_balances(db, 2)
        assert body["balance_after"] == tx["balance_after"] == after["FC"] == before["FC"] + 5000


@allure.feature("DB 정합성")
@allure.story("상점 구매")
@allure.title("TC-SHOP-15 구매 1회 → 응답 잔액 = DB 잔액, 구매 이력 1건, 재화 이력 -total")
def test_tc_shop_15_purchase_matches_db(db, tokens):
    before = snapshot(db, 1)
    price = query(db, "SELECT price FROM shop_items WHERE item_id = 101")[0]["price"]
    request_id = new_request_id("shop15")
    with allure.step("qa_user1 101 x 2 구매"):
        status, body = api("POST", "/shop/purchase", tokens["user1"],
                           {"item_id": 101, "quantity": 2, "request_id": request_id})
        assert status == 200, body
    with allure.step("응답 balance_after = DB 잔액 = 구매 전 - 가격 x 수량"):
        after = db_balances(db, 1)
        assert body["total_price"] == price * 2
        assert body["balance_after"] == after["FC"] == before["balances"]["FC"] - price * 2
    with allure.step("purchase_history 1건 (request_id로 조회)"):
        rows = query(db, "SELECT * FROM purchase_history WHERE account_id = 1 AND request_id = %s", (request_id,))
        assert len(rows) == 1
        ph = rows[0]
        assert ph["purchase_id"] == body["purchase_id"]
        assert (ph["item_id"], ph["quantity"], ph["unit_price"], ph["total_price"], ph["currency_type"]) == \
               (101, 2, price, price * 2, "FC")
    with allure.step("currency_transactions에 -total, reason PURCHASE, purchase_id 연결"):
        rows = query(db, "SELECT * FROM currency_transactions WHERE purchase_id = %s", (body["purchase_id"],))
        assert len(rows) == 1
        tx = rows[0]
        assert (tx["account_id"], tx["currency_type"], tx["amount"], tx["reason"]) == (1, "FC", -price * 2, "PURCHASE")
        assert tx["balance_after"] == after["FC"]
    with allure.step("응답 inventory_quantity = DB 인벤토리 = 구매 전 + 2"):
        inv = query(db, "SELECT quantity FROM inventory WHERE account_id = 1 AND item_id = 101")[0]["quantity"]
        assert body["inventory_quantity"] == inv == before["inventory"].get(101, 0) + 2


@allure.feature("DB 정합성")
@allure.story("상점 구매")
@allure.title("TC-SHOP-16 실패한 구매 → 잔액·인벤토리·이력 모두 변화 없음 (R6) : {case}")
@pytest.mark.parametrize("case, who, account_id, body, expected_status", [
    ("잔액 부족 (qa_user2 FC 5000에 101 x 6)", "user2", 2, {"item_id": 101, "quantity": 6}, 409),
    ("판매 종료 아이템 105", "user1", 1, {"item_id": 105, "quantity": 1}, 409),
    ("quantity 11 (1회 최대 초과)", "user1", 1, {"item_id": 101, "quantity": 11}, 400),
])
def test_tc_shop_16_failed_purchase_no_side_effect(db, tokens, case, who, account_id, body, expected_status):
    before = snapshot(db, account_id)
    with allure.step(f"실패해야 하는 구매 요청: {case}"):
        status, data = api("POST", "/shop/purchase", tokens[who], {**body, "request_id": new_request_id("shop16")})
        assert status == expected_status, data
    with allure.step("요청 전후 DB 상태 비교"):
        after = snapshot(db, account_id)
        assert after == before


@allure.feature("DB 정합성")
@allure.story("인벤토리")
@allure.title("TC-INV-04 전체 구매 후 → 구매 이력 수량 합계 = 인벤토리 수량 = 인벤토리 API 수량")
def test_tc_inv_04_inventory_equals_history(db, tokens, workload):
    rows = query(db, """
        SELECT COALESCE(h.account_id, i.account_id) AS account_id, COALESCE(h.item_id, i.item_id) AS item_id,
               COALESCE(h.qty, 0) AS history_qty, COALESCE(i.quantity, 0) AS inventory_qty
        FROM (SELECT account_id, item_id, SUM(quantity) AS qty FROM purchase_history GROUP BY account_id, item_id) h
        LEFT JOIN inventory i ON h.account_id = i.account_id AND h.item_id = i.item_id
        UNION
        SELECT i.account_id, i.item_id, 0, i.quantity
        FROM inventory i LEFT JOIN purchase_history h ON h.account_id = i.account_id AND h.item_id = i.item_id
        WHERE h.purchase_id IS NULL
    """)
    with allure.step("DB: 이력 합계 = 인벤토리 (계정·아이템별)"):
        mismatch = [r for r in rows if r["history_qty"] != r["inventory_qty"]]
        assert not mismatch, f"불일치 {mismatch}"
    with allure.step("API: 인벤토리 조회 응답 = DB 인벤토리 (수량 0 제외)"):
        for account_id in (1, 2):
            status, body = api("GET", f"/accounts/{account_id}/inventory", tokens["admin"])
            assert status == 200
            db_inv = {r["item_id"]: r["quantity"] for r in query(
                db, "SELECT item_id, quantity FROM inventory WHERE account_id = %s AND quantity > 0", (account_id,))}
            assert {i["item_id"]: i["quantity"] for i in body["items"]} == db_inv


@allure.feature("DB 정합성")
@allure.story("재화 잔액")
@allure.title("TC-DB-01 전체 실행 후 → 초기 잔액 + 변동 이력 합계 = 현재 잔액 (계정·재화별)")
def test_tc_db_01_balance_equals_initial_plus_transactions(db, initial_balances, workload):
    tx_sum = {(r["account_id"], r["currency_type"]): int(r["total"]) for r in query(
        db, "SELECT account_id, currency_type, SUM(amount) AS total FROM currency_transactions "
            "GROUP BY account_id, currency_type")}
    current = {(r["account_id"], r["currency_type"]): r["balance"] for r in query(
        db, "SELECT account_id, currency_type, balance FROM account_currency")}
    mismatch = {f"{k[0]}/{k[1]}": {"초기": initial_balances[k], "이력합계": tx_sum.get(k, 0), "현재": v}
                for k, v in current.items() if initial_balances[k] + tx_sum.get(k, 0) != v}
    assert not mismatch, f"불일치 {mismatch}"


@allure.feature("DB 정합성")
@allure.story("재화 잔액")
@allure.title("TC-DB-01 전체 실행 후 → 구매 차감액 합계 = 구매 이력 금액 합계 (계정·재화별)")
def test_tc_db_01_deduction_equals_purchase_history(db, workload):
    deducted = {(r["account_id"], r["currency_type"]): -int(r["total"]) for r in query(
        db, "SELECT account_id, currency_type, SUM(amount) AS total FROM currency_transactions "
            "WHERE reason = 'PURCHASE' GROUP BY account_id, currency_type")}
    purchased = {(r["account_id"], r["currency_type"]): int(r["total"]) for r in query(
        db, "SELECT account_id, currency_type, SUM(total_price) AS total FROM purchase_history "
            "GROUP BY account_id, currency_type")}
    assert deducted == purchased


@allure.feature("DB 정합성")
@allure.story("재화 잔액")
@allure.title("TC-DB-01 전체 실행 후 → 구매 이력 금액 = shop_items.price x 수량 (R5)")
def test_tc_db_01_history_price_equals_server_price(db, workload):
    rows = query(db, """
        SELECT h.purchase_id, h.item_id, h.quantity, h.unit_price, h.total_price, s.price
        FROM purchase_history h JOIN shop_items s ON h.item_id = s.item_id
        WHERE h.unit_price <> s.price OR h.total_price <> s.price * h.quantity
    """)
    assert not rows, f"서버 가격과 다른 구매 이력 {rows}"


@allure.feature("DB 정합성")
@allure.story("재화 잔액")
@allure.title("TC-DB-01 전체 실행 후 → 재화 조회 API 잔액 = DB 잔액 (전 계정)")
def test_tc_db_01_currency_api_equals_db(db, tokens, workload):
    for account_id in (1, 2, 3, 4):
        status, body = api("GET", f"/accounts/{account_id}/currency", tokens["admin"])
        assert status == 200
        assert body["balances"] == db_balances(db, account_id)
