"""
Day 67 : 프록시 요청 변조 테스트 - 서버가 클라이언트 값을 그대로 믿는지 확인
클라이언트는 항상 정상 요청(101 x1, price 없음)을 보내고, 프록시가 중간에서 가격·수량·아이템 ID를 바꾼다.
케이스마다 DB를 시드로 초기화 → 변조 구매 → 응답과 DB(FC 잔액·인벤토리) 변화를 명세 기대값과 대조
결과는 day67_tamper_cases.md 표로 저장
실행: py day67_tamper_test.py [--server day66_https_server.py] [--out day67_tamper_cases.md]
"""

import argparse
import contextlib
import io
import json
import os
import sys
import time

import pymysql

from day59_apply_schema import APP_PASSWORD, APP_USER, DB_HOST, DB_NAME, DB_PORT, apply_schema
from day66_make_certs import CA_CERT, make_certs
from day66_proxy_lab import BASE_DIR, MITM_CA, PROXY_PORT, new_session, start_mitm, start_server, stop

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://127.0.0.1:8443"
PROXY = f"http://127.0.0.1:{PROXY_PORT}"
TAMPER_FILE = os.path.join(BASE_DIR, "handoff", "day67_tamper.json")
TAMPER_LOG = os.path.join(BASE_DIR, "handoff", "day67_tamper_log.jsonl")

# (ID, 변조 내용, 덮어쓸 필드, 기대 상태, 기대 FC 차감, 기대 인벤토리 증가, 기대 근거)
CASES = [
    ("TM-01", "변조 없음 (기준)", {}, 200, 1000, 1, "정상 구매"),
    ("TM-02", "price 1 추가", {"price": 1}, 200, 1000, 1, "R5 클라이언트 가격 무시"),
    ("TM-03", "price 0 추가", {"price": 0}, 200, 1000, 1, "R5"),
    ("TM-04", "price -1000 추가", {"price": -1000}, 200, 1000, 1, "R5"),
    ("TM-05", "quantity 0", {"quantity": 0}, 400, 0, 0, "R3 수량 1 이상"),
    ("TM-06", "quantity -1", {"quantity": -1}, 400, 0, 0, "R3"),
    ("TM-07", "quantity 11 (1회 최대 10)", {"quantity": 11}, 400, 0, 0, "R3"),
    ("TM-08", "quantity 10, price 1", {"quantity": 10, "price": 1}, 409, 0, 0, "R5 서버 가격 10000 > 잔액 5000"),
    ("TM-09", "item_id 105 (판매 종료)", {"item_id": 105}, 409, 0, 0, "R10"),
    ("TM-10", "item_id 999 (없는 아이템)", {"item_id": 999}, 404, 0, 0, "ITEM_NOT_FOUND"),
    ("TM-11", "item_id 104 (FC 3000)", {"item_id": 104}, 200, 3000, 1, "서버 가격으로 차감"),
]


def db_state(item_id):
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=APP_USER, password=APP_PASSWORD, database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM account_currency WHERE account_id = 1 AND currency_type = 'FC'")
            fc = int(cur.fetchone()["balance"])
            cur.execute("SELECT COALESCE(SUM(quantity), 0) AS q FROM inventory WHERE account_id = 1 AND item_id = %s",
                        (item_id,))
            inv = int(cur.fetchone()["q"])
        return fc, inv
    finally:
        conn.close()


def reset_db():
    with contextlib.redirect_stdout(io.StringIO()):
        apply_schema()


def run_case(case):
    cid, desc, overrides, exp_status, exp_fc, exp_inv, basis = case
    reset_db()
    with open(TAMPER_FILE, "w", encoding="utf-8") as f:
        json.dump({"case": cid, "set": overrides}, f)
    item_id = overrides.get("item_id", 101)
    fc_before, inv_before = db_state(item_id)

    session = new_session(proxy=PROXY, verify=MITM_CA)
    token = session.post(BASE_URL + "/auth/login", json={"username": "qa_user1", "password": "Test1234!"},
                         timeout=5).json()["access_token"]
    # 클라이언트는 항상 정상 요청
    res = session.post(BASE_URL + "/shop/purchase", headers={"Authorization": f"Bearer {token}"}, timeout=5,
                       json={"item_id": 101, "quantity": 1, "request_id": f"{cid}-{time.time_ns()}"})
    fc_after, inv_after = db_state(item_id)
    charged, gained = fc_before - fc_after, inv_after - inv_before
    ok = res.status_code == exp_status and charged == exp_fc and gained == exp_inv
    try:
        body = res.json()
        summary = body.get("error_code") or f"unit_price={body.get('unit_price')}, balance_after={body.get('balance_after')}"
    except ValueError:
        summary = res.text[:60]
    return {"id": cid, "desc": desc, "status": res.status_code, "summary": summary, "charged": charged,
            "gained": gained, "exp": f"{exp_status} / FC {-exp_fc:+d} / +{exp_inv}", "basis": basis, "ok": ok}


def write_md(path, rows, server_label):
    lines = [
        f"# Day 67 요청 변조 케이스 ({server_label})",
        "",
        "> 클라이언트는 항상 `{\"item_id\": 101, \"quantity\": 1}`(price 없음)을 보내고, 프록시가 중간에서 본문을 변조했다. "
        "기대값은 `day59_api_spec.md` 업무 규칙 기준. 케이스마다 fc_qa_lab 시드(qa_user1 FC 5000)에서 시작.",
        "",
        "| ID | 변조 내용 | 응답 | 응답 요약 | FC 변화 | 인벤토리 증가 | 기대 (상태 / FC 변화 / 증가) | 근거 | 판정 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {r['desc']} | {r['status']} | {r['summary']} | {-r['charged']:+d} | {r['gained']} "
                     f"| {r['exp']} | {r['basis']} | {'PASS' if r['ok'] else '**FAIL**'} |")
    failed = [r for r in rows if not r["ok"]]
    lines += ["", f"- 결과: {len(rows) - len(failed)}/{len(rows)} PASS, 결함 의심 {len(failed)}건"]
    for r in failed:
        lines.append(f"  - {r['id']} {r['desc']}: 응답 {r['status']}, FC {-r['charged']:+d}, 인벤토리 +{r['gained']}")
    with open(os.path.join(BASE_DIR, path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="day66_https_server.py", help="HTTPS 8443으로 뜨는 서버 스크립트")
    parser.add_argument("--out", default="day67_tamper_cases.md")
    args = parser.parse_args()

    make_certs()
    os.makedirs(os.path.dirname(TAMPER_LOG), exist_ok=True)
    for p in (TAMPER_FILE, TAMPER_LOG):
        if os.path.exists(p):
            os.remove(p)
    reset_db()
    print(f"[1] 서버 기동: py {args.server} --no-reset (https://127.0.0.1:8443)")
    server = start_server([args.server, "--no-reset"], BASE_URL + "/openapi.json", verify=CA_CERT)
    print(f"[2] 변조 프록시 기동: mitmdump -s day67_tamper_addon.py (127.0.0.1:{PROXY_PORT})\n")
    mitm = start_mitm("day67_tamper_addon.py", {"tamper_file": TAMPER_FILE, "tamper_log": TAMPER_LOG},
                      upstream_ca=CA_CERT)
    rows = []
    try:
        for case in CASES:
            r = run_case(case)
            rows.append(r)
            print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['id']} {r['desc']} → {r['status']} {r['summary']} "
                  f"(FC {-r['charged']:+d}, 인벤토리 +{r['gained']}) / 기대 {r['exp']}")
    finally:
        stop(mitm)
        stop(server)
    reset_db()

    print("\n[3] 프록시 변조 기록 (변조 전 → 후)")
    with open(TAMPER_LOG, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            print(f"  {t['case']}: {t['original']} → {t['tampered']} → {t['status']}")

    write_md(args.out, rows, args.server)
    failed = sum(not r["ok"] for r in rows)
    print(f"\n[결과] {len(rows) - failed}/{len(rows)} PASS, 결함 의심 {failed}건 → {args.out}")


if __name__ == "__main__":
    main()
