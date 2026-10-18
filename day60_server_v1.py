import hashlib
import os
import secrets
import sys
from typing import Literal, Optional

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

app = FastAPI(title="모의 게임 서버 v1 (상점·재화)")


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


# ---------- 2.4 상점 구매 ----------
class PurchaseRequest(BaseModel):
    item_id: StrictInt
    quantity: StrictInt
    request_id: StrictStr = Field(min_length=1, max_length=64)
    price: Optional[int] = None


def find_purchase(cur, account_id, request_id):
    """같은 request_id로 이미 처리된 구매가 있으면 처음 응답을 다시 만든다 (R7)."""
    cur.execute("""
        SELECT p.purchase_id, p.item_id, p.quantity, p.unit_price, p.total_price, p.currency_type,
               t.balance_after
        FROM purchase_history p
        JOIN currency_transactions t ON t.purchase_id = p.purchase_id
        WHERE p.account_id = %s AND p.request_id = %s
    """, (account_id, request_id))
    row = cur.fetchone()
    if row is None:
        return None
    cur.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS qty FROM purchase_history
        WHERE account_id = %s AND item_id = %s AND purchase_id <= %s
    """, (account_id, row["item_id"], row["purchase_id"]))
    return {"purchase_id": row["purchase_id"], "item_id": row["item_id"], "quantity": row["quantity"],
            "unit_price": row["unit_price"], "total_price": int(row["total_price"]),
            "currency_type": row["currency_type"], "balance_after": int(row["balance_after"]),
            "inventory_quantity": int(cur.fetchone()["qty"])}


@app.post("/shop/purchase")
def purchase(body: PurchaseRequest, request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            me = authenticate(request, cur)
            account_id = me["account_id"]

            previous = find_purchase(cur, account_id, body.request_id)
            if previous is not None:
                return previous

            cur.execute("SELECT * FROM shop_items WHERE item_id = %s", (body.item_id,))
            item = cur.fetchone()
            if item is None:
                raise ApiError(404, "ITEM_NOT_FOUND", "아이템이 없습니다.")
            if body.quantity < 0 or body.quantity > item["max_per_purchase"]:
                raise ApiError(400, "VALIDATION_ERROR", "구매 수량이 허용 범위를 벗어났습니다.")
            if not item["is_on_sale"]:
                raise ApiError(409, "ITEM_NOT_ON_SALE", "판매가 종료된 아이템입니다.")

            cur.execute("SELECT quantity FROM inventory WHERE account_id = %s AND item_id = %s",
                        (account_id, body.item_id))
            inv = cur.fetchone()
            owned = inv["quantity"] if inv else 0
            if owned + body.quantity > item["max_owned"]:
                raise ApiError(409, "INVENTORY_LIMIT_EXCEEDED", "보유 수량 상한을 넘습니다.")

            unit_price = body.price if body.price is not None else item["price"]
            total_price = unit_price * body.quantity
            currency = item["currency_type"]

            cur.execute("SELECT balance FROM account_currency WHERE account_id = %s AND currency_type = %s",
                        (account_id, currency))
            balance = int(cur.fetchone()["balance"])

            cur.execute("""
                INSERT INTO inventory (account_id, item_id, quantity) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """, (account_id, body.item_id, body.quantity))

            if balance < total_price:
                raise ApiError(409, "INSUFFICIENT_BALANCE", "잔액이 부족합니다.")

            try:
                cur.execute("""
                    INSERT INTO purchase_history
                        (account_id, item_id, quantity, unit_price, total_price, currency_type, request_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (account_id, body.item_id, body.quantity, unit_price, total_price, currency,
                      body.request_id))
            except pymysql.err.IntegrityError:
                # 동시에 들어온 같은 request_id: 먼저 처리된 결과를 반환
                return find_purchase(cur, account_id, body.request_id)
            purchase_id = cur.lastrowid

            balance_after = balance - total_price
            cur.execute("UPDATE account_currency SET balance = %s WHERE account_id = %s AND currency_type = %s",
                        (balance_after, account_id, currency))
            cur.execute("""
                INSERT INTO currency_transactions
                    (account_id, currency_type, amount, balance_after, reason, purchase_id)
                VALUES (%s, %s, %s, %s, 'PURCHASE', %s)
            """, (account_id, currency, -total_price, balance_after, purchase_id))

            cur.execute("SELECT quantity FROM inventory WHERE account_id = %s AND item_id = %s",
                        (account_id, body.item_id))
            inventory_quantity = cur.fetchone()["quantity"]
        return {"purchase_id": purchase_id, "item_id": body.item_id, "quantity": body.quantity,
                "unit_price": unit_price, "total_price": total_price, "currency_type": currency,
                "balance_after": balance_after, "inventory_quantity": inventory_quantity}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
