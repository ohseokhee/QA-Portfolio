"""
Day 70 : 모의 게임 서버 v3 - 재시도 안전 처리 (Idempotency-Key + 트랜잭션)
- POST /shop/purchase는 Idempotency-Key 헤더(없으면 본문 request_id)로 요청을 식별
	- 처음 보는 키: IN_PROGRESS로 선점 후 처리, 결과(상태 코드·본문)를 저장하고 DONE
	- 이미 DONE인 키: 다시 처리하지 않고 저장된 응답을 그대로 반환
	- 처리 중(IN_PROGRESS)인 키: 최대 3초 기다렸다가 저장된 응답 반환, 그래도 안 끝나면 409 REQUEST_IN_PROGRESS
- 구매는 한 트랜잭션(잔액·인벤토리 행 잠금 → 검증 → 이력·차감·재화 이력·인벤토리 → 커밋), 실패 시 전부 롤백 (R6)
- 그 외 동작은 v2와 동일 (가격·수량 서버 검증 포함)
실행: py day70_server_v3.py [--http] [--port N] [--no-reset]  (기본 HTTPS 8443, /shop 페이지 포함)
      py -m uvicorn day70_server_v3:app --port 8000          (HTTP, 기존 컬렉션·pytest 회귀용)
"""

import hashlib
import json
import os
import secrets
import sys
import time
from typing import Literal, Optional

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StrictInt, StrictStr

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DB_HOST = "127.0.0.1"
DB_PORT = int(os.getenv("MYSQL_PORT", "3307"))
DB_NAME = os.getenv("FC_DB_NAME")
DB_USER = os.getenv("MARIADB_USER") or os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD") or os.getenv("MYSQL_PASSWORD")

TOKEN_TTL_SECONDS = 1800
BALANCE_MAX = 99_999_999

app = FastAPI(title="모의 게임 서버 v3 (상점·재화)")


class ApiError(Exception):
    def __init__(self, status, error_code, message):
        self.status = status
        self.error_code = error_code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status,
                        content={"error_code": exc.error_code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # 명세: FastAPI 기본 422 대신 400 VALIDATION_ERROR로 통일
    return JSONResponse(status_code=400,
                        content={"error_code": "VALIDATION_ERROR", "message": "요청 값이 올바르지 않습니다."})


def get_conn():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
                           database=DB_NAME, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)


def authenticate(request: Request, cur):
    """Authorization: Bearer {token} 헤더를 검사하고 계정 행을 반환한다."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "인증 토큰이 없습니다.")
    token = header[len("Bearer "):].strip()
    cur.execute("""
        SELECT a.account_id, a.role, a.status,
               TIMESTAMPDIFF(MINUTE, t.expires_at, NOW()) AS expired_minutes
        FROM auth_tokens t JOIN accounts a ON t.account_id = a.account_id
        WHERE t.token = %s
    """, (token,))
    row = cur.fetchone()
    if row is None:
        raise ApiError(401, "UNAUTHORIZED", "유효하지 않은 토큰입니다.")
    if row["expired_minutes"] >= 1:
        raise ApiError(401, "TOKEN_EXPIRED", "토큰이 만료되었습니다.")
    return row


def account_exists(cur, account_id):
    cur.execute("SELECT 1 FROM accounts WHERE account_id = %s", (account_id,))
    return cur.fetchone() is not None


# ---------- 2.1 로그인 ----------
class LoginRequest(BaseModel):
    username: StrictStr = Field(min_length=4, max_length=20)
    password: StrictStr = Field(min_length=8, max_length=20)


@app.post("/auth/login")
def login(body: LoginRequest):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT account_id, password_hash, status FROM accounts WHERE username = %s",
                        (body.username,))
            row = cur.fetchone()
            password_hash = hashlib.sha256(body.password.encode("utf-8")).hexdigest()
            if row is None or row["password_hash"] != password_hash:
                raise ApiError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 일치하지 않습니다.")
            if row["status"] == "BANNED":
                raise ApiError(403, "ACCOUNT_BANNED", "이용이 제한된 계정입니다.")
            token = secrets.token_hex(32)
            cur.execute("""
                INSERT INTO auth_tokens (token, account_id, issued_at, expires_at)
                VALUES (%s, %s, NOW(), NOW() + INTERVAL %s SECOND)
            """, (token, row["account_id"], TOKEN_TTL_SECONDS))
        return {"access_token": token, "token_type": "Bearer",
                "expires_in": TOKEN_TTL_SECONDS, "account_id": row["account_id"]}
    finally:
        conn.close()


# ---------- 2.2 재화 조회 ----------
@app.get("/accounts/{account_id}/currency")
def get_currency(account_id: int, request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            me = authenticate(request, cur)
            if me["role"] != "ADMIN" and me["account_id"] != account_id:
                raise ApiError(403, "FORBIDDEN", "다른 계정은 조회할 수 없습니다.")
            if not account_exists(cur, account_id):
                raise ApiError(404, "ACCOUNT_NOT_FOUND", "계정이 없습니다.")
            cur.execute("SELECT currency_type, balance FROM account_currency WHERE account_id = %s",
                        (account_id,))
            balances = {"FC": 0, "BP": 0}
            for row in cur.fetchall():
                balances[row["currency_type"]] = int(row["balance"])
        return {"account_id": account_id, "balances": balances}
    finally:
        conn.close()


# ---------- 2.3 재화 지급 (운영툴) ----------
class GrantRequest(BaseModel):
    account_id: StrictInt
    currency_type: Literal["FC", "BP"]
    amount: StrictInt = Field(ge=1, le=1_000_000)
    memo: Optional[StrictStr] = Field(default=None, max_length=100)


@app.post("/admin/currency/grant")
def grant_currency(body: GrantRequest, request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            me = authenticate(request, cur)
            if me["role"] != "ADMIN":
                raise ApiError(403, "FORBIDDEN", "운영자만 지급할 수 있습니다.")
            if not account_exists(cur, body.account_id):
                raise ApiError(404, "ACCOUNT_NOT_FOUND", "계정이 없습니다.")
            cur.execute("""
                UPDATE account_currency SET balance = balance + %s
                WHERE account_id = %s AND currency_type = %s
            """, (body.amount, body.account_id, body.currency_type))
            cur.execute("SELECT balance FROM account_currency WHERE account_id = %s AND currency_type = %s",
                        (body.account_id, body.currency_type))
            balance_after = int(cur.fetchone()["balance"])
            cur.execute("""
                INSERT INTO currency_transactions
                    (account_id, currency_type, amount, balance_after, reason, operator_id, memo)
                VALUES (%s, %s, %s, %s, 'GRANT', %s, %s)
            """, (body.account_id, body.currency_type, body.amount, balance_after,
                  me["account_id"], body.memo))
            tx_id = cur.lastrowid
        return {"tx_id": tx_id, "account_id": body.account_id, "currency_type": body.currency_type,
                "amount": body.amount, "balance_after": balance_after}
    finally:
        conn.close()


# ---------- 2.4 상점 구매 (v3: 멱등 키 + 트랜잭션) ----------
class PurchaseRequest(BaseModel):
    item_id: StrictInt
    quantity: StrictInt
    request_id: StrictStr = Field(min_length=1, max_length=64)


IDEMPOTENCY_DDL = """
    CREATE TABLE IF NOT EXISTS idempotency_keys (
        account_id    INT NOT NULL,
        idem_key      VARCHAR(64) NOT NULL,
        status        ENUM('IN_PROGRESS', 'DONE') NOT NULL,
        response_code INT NULL,
        response_body TEXT NULL,
        created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (account_id, idem_key)
    )
"""
IN_PROGRESS_WAIT_SECONDS = 3.0


def claim_key(cur, account_id, key):
    """키를 선점한다. 처음 보는 키면 None, 이미 처리된 키면 저장된 (상태 코드, 본문)을 반환"""
    cur.execute(IDEMPOTENCY_DDL)
    try:
        cur.execute("INSERT INTO idempotency_keys (account_id, idem_key, status) VALUES (%s, %s, 'IN_PROGRESS')",
                    (account_id, key))
        return None
    except pymysql.err.IntegrityError:
        pass
    deadline = time.time() + IN_PROGRESS_WAIT_SECONDS
    while True:
        cur.execute("SELECT status, response_code, response_body FROM idempotency_keys "
                    "WHERE account_id = %s AND idem_key = %s", (account_id, key))
        row = cur.fetchone()
        if row and row["status"] == "DONE":
            return row["response_code"], json.loads(row["response_body"])
        if time.time() > deadline:
            raise ApiError(409, "REQUEST_IN_PROGRESS", "같은 요청을 처리 중입니다. 잠시 후 다시 시도해 주세요.")
        time.sleep(0.05)


def finish_key(cur, account_id, key, status_code, body):
    cur.execute("UPDATE idempotency_keys SET status = 'DONE', response_code = %s, response_body = %s "
                "WHERE account_id = %s AND idem_key = %s",
                (status_code, json.dumps(body, ensure_ascii=False), account_id, key))


def process_purchase(account_id, body):
    """한 트랜잭션으로 구매 처리. 잔액·인벤토리 행을 잠가 동시 요청의 갱신 손실을 막고, 검증을 모두 마친 뒤에만 변경 (R6)"""
    conn = get_conn()
    conn.autocommit(False)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM shop_items WHERE item_id = %s", (body.item_id,))
            item = cur.fetchone()
            if item is None:
                raise ApiError(404, "ITEM_NOT_FOUND", "아이템이 없습니다.")
            if body.quantity < 1 or body.quantity > item["max_per_purchase"]:
                raise ApiError(400, "VALIDATION_ERROR", "구매 수량이 허용 범위를 벗어났습니다.")
            if not item["is_on_sale"]:
                raise ApiError(409, "ITEM_NOT_ON_SALE", "판매가 종료된 아이템입니다.")

            currency = item["currency_type"]
            cur.execute("SELECT balance FROM account_currency WHERE account_id = %s AND currency_type = %s FOR UPDATE",
                        (account_id, currency))
            balance = int(cur.fetchone()["balance"])
            cur.execute("SELECT quantity FROM inventory WHERE account_id = %s AND item_id = %s FOR UPDATE",
                        (account_id, body.item_id))
            inv = cur.fetchone()
            owned = inv["quantity"] if inv else 0
            if owned + body.quantity > item["max_owned"]:
                raise ApiError(409, "INVENTORY_LIMIT_EXCEEDED", "보유 수량 상한을 넘습니다.")

            unit_price = item["price"]
            total_price = unit_price * body.quantity
            if balance < total_price:
                raise ApiError(409, "INSUFFICIENT_BALANCE", "잔액이 부족합니다.")

            try:
                cur.execute("""
                    INSERT INTO purchase_history
                        (account_id, item_id, quantity, unit_price, total_price, currency_type, request_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (account_id, body.item_id, body.quantity, unit_price, total_price, currency, body.request_id))
            except pymysql.err.IntegrityError:
                raise ApiError(409, "DUPLICATE_REQUEST_ID", "이미 사용한 request_id입니다.")
            purchase_id = cur.lastrowid

            balance_after = balance - total_price
            cur.execute("UPDATE account_currency SET balance = %s WHERE account_id = %s AND currency_type = %s",
                        (balance_after, account_id, currency))
            cur.execute("""
                INSERT INTO currency_transactions
                    (account_id, currency_type, amount, balance_after, reason, purchase_id)
                VALUES (%s, %s, %s, %s, 'PURCHASE', %s)
            """, (account_id, currency, -total_price, balance_after, purchase_id))
            cur.execute("""
                INSERT INTO inventory (account_id, item_id, quantity) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """, (account_id, body.item_id, body.quantity))
            cur.execute("SELECT quantity FROM inventory WHERE account_id = %s AND item_id = %s",
                        (account_id, body.item_id))
            inventory_quantity = cur.fetchone()["quantity"]
        conn.commit()
        return {"purchase_id": purchase_id, "item_id": body.item_id, "quantity": body.quantity,
                "unit_price": unit_price, "total_price": total_price, "currency_type": currency,
                "balance_after": balance_after, "inventory_quantity": inventory_quantity}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/shop/purchase")
def purchase(body: PurchaseRequest, request: Request):
    conn = get_conn()  # autocommit: 키 상태가 다른 요청에 바로 보이도록
    try:
        with conn.cursor() as cur:
            me = authenticate(request, cur)
            account_id = me["account_id"]
            key = request.headers.get("Idempotency-Key") or body.request_id
            if len(key) > 64:
                raise ApiError(400, "VALIDATION_ERROR", "Idempotency-Key는 64자 이하입니다.")

            stored = claim_key(cur, account_id, key)
            if stored is not None:
                return JSONResponse(status_code=stored[0], content=stored[1])
            try:
                status_code, result = 200, process_purchase(account_id, body)
            except ApiError as e:
                status_code, result = e.status, {"error_code": e.error_code, "message": e.message}
            except Exception:
                # 예기치 못한 오류는 결과를 저장하지 않고 키를 풀어 재시도를 허용
                cur.execute("DELETE FROM idempotency_keys WHERE account_id = %s AND idem_key = %s", (account_id, key))
                raise
            finish_key(cur, account_id, key, status_code, result)
        return JSONResponse(status_code=status_code, content=result)
    finally:
        conn.close()


# ---------- 2.5 인벤토리 조회 ----------
@app.get("/accounts/{account_id}/inventory")
def get_inventory(account_id: int, request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            authenticate(request, cur)
            if not account_exists(cur, account_id):
                raise ApiError(404, "ACCOUNT_NOT_FOUND", "계정이 없습니다.")
            cur.execute("""
                SELECT i.item_id, s.name, i.quantity
                FROM inventory i JOIN shop_items s ON i.item_id = s.item_id
                WHERE i.account_id = %s AND i.quantity > 0
                ORDER BY i.item_id
            """, (account_id,))
            items = [{"item_id": r["item_id"], "name": r["name"], "quantity": r["quantity"]}
                     for r in cur.fetchall()]
        return {"account_id": account_id, "items": items}
    finally:
        conn.close()


# ---------- 상점 페이지 (Day 65) ----------
@app.get("/shop", include_in_schema=False)
def shop_page():
    return FileResponse(os.path.join(BASE_DIR, "day65_shop_client.html"), media_type="text/html; charset=utf-8")


if __name__ == "__main__":
    import argparse

    import uvicorn

    from day59_apply_schema import apply_schema
    from day66_make_certs import SERVER_CERT, SERVER_KEY, make_certs

    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="HTTP로 실행 (기본 HTTPS)")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-reset", action="store_true", help="fc_qa_lab 시드 초기화 생략")
    args = parser.parse_args()
    if not args.no_reset:
        apply_schema()
    if args.http:
        uvicorn.run(app, host="127.0.0.1", port=args.port or 8000)
    else:
        make_certs()
        uvicorn.run(app, host="127.0.0.1", port=args.port or 8443, ssl_certfile=SERVER_CERT, ssl_keyfile=SERVER_KEY)
