"""
Day 64 : 모의 게임 서버 동시 요청 검증 (이중 차감·중복 지급 탐지)
대상 TC: day59_api_spec.md 4.3의 실행 Day 64 (TC-SHOP-17, TC-SHOP-18)
실행: py -m pytest day64_test_concurrency.py --alluredir=allure-results --clean-alluredir -s
"""

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import allure
import pytest
import requests

# Day 63의 서버·DB·토큰 픽스처와 헬퍼 재사용
from day63_test_db_integrity import BASE_URL, api, db, db_balances, query, server, tokens  # noqa: F401

sys.stdout.reconfigure(encoding="utf-8")

CONCURRENCY = 10


def send_concurrently(token, bodies):
    """Barrier로 모든 스레드를 출발선에 세운 뒤 동시에 구매 요청을 보낸다."""
    barrier = threading.Barrier(len(bodies))

    def worker(body):
        barrier.wait()
        res = requests.post(BASE_URL + "/shop/purchase", json=body,
                            headers={"Authorization": f"Bearer {token}"}, timeout=10)
        try:
            data = res.json()
        except ValueError:
            data = {"raw": res.text}
        return res.status_code, data

    with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
        results = list(pool.map(worker, bodies))
    allure.attach(json.dumps([{"status": s, "response": d} for s, d in results], ensure_ascii=False, indent=2),
                  name=f"동시 요청 {len(bodies)}건 응답", attachment_type=allure.attachment_type.JSON)
    return results


def print_results(title, results):
    print(f"\n[{title}]")
    for i, (status, data) in enumerate(results, 1):
        print(f"  #{i:02d} {status} {json.dumps(data, ensure_ascii=False)}")


# ============================================================
# TC-SHOP-17 같은 request_id로 동시 10회
# ============================================================

@pytest.fixture(scope="module")
def same_request_burst(db, tokens):
    request_id = f"d64-same-{time.time_ns()}"
    before = {
        "fc": db_balances(db, 1)["FC"],
        "inventory": sum(r["quantity"] for r in query(
            db, "SELECT quantity FROM inventory WHERE account_id = 1 AND item_id = 101")),
    }
    body = {"item_id": 101, "quantity": 1, "request_id": request_id}
    with allure.step(f"qa_user1 101 x 1, 같은 request_id로 동시 {CONCURRENCY}회"):
        results = send_concurrently(tokens["user1"], [body] * CONCURRENCY)
    print_results(f"TC-SHOP-17 같은 request_id 동시 {CONCURRENCY}회", results)
    return request_id, before, results


@allure.feature("동시성")
@allure.story("멱등성 (R7)")
@allure.title("TC-SHOP-17 같은 request_id 동시 10회 → 구매 이력 1건, 차감 1회, 인벤토리 +1")
def test_tc_shop_17_same_request_id_db(db, same_request_burst):
    request_id, before, _ = same_request_burst
    with allure.step("purchase_history에 해당 request_id 1건"):
        rows = query(db, "SELECT purchase_id FROM purchase_history WHERE account_id = 1 AND request_id = %s",
                     (request_id,))
        history_count = len(rows)
    with allure.step("currency_transactions의 해당 구매 차감 이력 수"):
        tx_count = query(db, """
            SELECT COUNT(*) AS n FROM currency_transactions t
            JOIN purchase_history h ON t.purchase_id = h.purchase_id
            WHERE h.account_id = 1 AND h.request_id = %s
        """, (request_id,))[0]["n"]
    fc_after = db_balances(db, 1)["FC"]
    inventory_after = sum(r["quantity"] for r in query(
        db, "SELECT quantity FROM inventory WHERE account_id = 1 AND item_id = 101"))
    print(f"\n  이력 {history_count}건, 차감 이력 {tx_count}건, FC {before['fc']} → {fc_after}, "
          f"101 보유 {before['inventory']} → {inventory_after}")
    assert history_count == 1
    assert tx_count == 1
    assert before["fc"] - fc_after == 1000, "이중 차감"
    assert inventory_after - before["inventory"] == 1, "중복 지급"


@allure.feature("동시성")
@allure.story("멱등성 (R7)")
@allure.title("TC-SHOP-17 같은 request_id 동시 10회 → 응답 전부 200, 같은 purchase_id")
def test_tc_shop_17_same_request_id_responses(same_request_burst):
    _, _, results = same_request_burst
    statuses = [s for s, _ in results]
    # 본문이 JSON 객체가 아닌 응답(null 등)도 실패로 집계되도록 dict만 purchase_id를 읽음
    purchase_ids = {d.get("purchase_id") if isinstance(d, dict) else repr(d) for _, d in results}
    print(f"\n  상태 코드 {statuses}, purchase_id {purchase_ids}")
    assert statuses == [200] * CONCURRENCY
    assert len(purchase_ids) == 1, f"응답마다 다른 본문 {purchase_ids}"


# ============================================================
# TC-SHOP-18 다른 request_id로 잔액보다 많은 동시 구매
# ============================================================

@pytest.fixture(scope="module")
def overspend_burst(db, tokens):
    with allure.step("준비: ADMIN이 qa_user2에 FC 5000 지급 (101 5개분)"):
        status, body = api("POST", "/admin/currency/grant", tokens["admin"],
                           {"account_id": 2, "currency_type": "FC", "amount": 5000})
        assert status == 200, body
    before = {
        "fc": db_balances(db, 2)["FC"],
        "history": query(db, "SELECT COUNT(*) AS n FROM purchase_history WHERE account_id = 2")[0]["n"],
        "inventory": sum(r["quantity"] for r in query(
            db, "SELECT quantity FROM inventory WHERE account_id = 2 AND item_id = 101")),
    }
    stamp = time.time_ns()
    bodies = [{"item_id": 101, "quantity": 1, "request_id": f"d64-over-{stamp}-{i}"} for i in range(CONCURRENCY)]
    with allure.step(f"qa_user2 FC {before['fc']}에서 101 x 1을 다른 request_id로 동시 {CONCURRENCY}회"):
        results = send_concurrently(tokens["user2"], bodies)
    print_results(f"TC-SHOP-18 다른 request_id 동시 {CONCURRENCY}회 (FC {before['fc']})", results)
    return before, results


@allure.feature("동시성")
@allure.story("잔액 경쟁 상태")
@allure.title("TC-SHOP-18 잔액보다 많은 동시 구매 → 잔액 음수 없음, 성공 건수 x 가격 = 차감액")
def test_tc_shop_18_overspend(db, overspend_burst):
    before, results = overspend_burst
    success = sum(1 for s, _ in results if s == 200)
    rejected = [d.get("error_code") for s, d in results if s != 200]
    fc_after = db_balances(db, 2)["FC"]
    history = query(db, "SELECT COUNT(*) AS n FROM purchase_history WHERE account_id = 2")[0]["n"] - before["history"]
    inventory = sum(r["quantity"] for r in query(
        db, "SELECT quantity FROM inventory WHERE account_id = 2 AND item_id = 101")) - before["inventory"]
    print(f"\n  성공 {success}건, 거부 {rejected}, FC {before['fc']} → {fc_after}, "
          f"이력 +{history}건, 101 보유 +{inventory}")
    with allure.step("잔액 음수 없음"):
        assert fc_after >= 0
    with allure.step("성공 건수 x 가격 = 차감액"):
        assert success * 1000 == before["fc"] - fc_after
    with allure.step("성공 건수 = 구매 이력 증가 = 인벤토리 증가"):
        assert success == history == inventory
    with allure.step("거부 응답은 409 INSUFFICIENT_BALANCE"):
        assert all(code == "INSUFFICIENT_BALANCE" for code in rejected)
