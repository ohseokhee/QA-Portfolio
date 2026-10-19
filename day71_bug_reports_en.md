# Day 71 Bug Reports (English)

> Defects found while testing the mock game shop server (Day 59~70). All numbers come from the test run logs of each Day.
> Test target: local mock server only (FastAPI + MariaDB `fc_qa_lab`). Seed account `qa_user1` starts with FC 5,000.

## Common Environment

| Item | Value |
|---|---|
| OS | Windows 11 Home (10.0.26200) |
| Server | `day60_server_v1.py` (v1), `day68_server_v2.py` (v2), FastAPI 0.143.3, Uvicorn 0.54.0, Python 3.14.2 |
| DB | MariaDB 10.6 (Docker, port 3307), schema `fc_qa_lab` |
| Client | `day65_shop_client.html` on Chrome (headless, Selenium 4.40.0) |
| Proxy | mitmproxy 12.2.3 (same role as Fiddler Breakpoint / AutoResponder) |

---

## BUG-001 Server trusts client-supplied price; negative price increases currency

| Field | Value |
|---|---|
| Summary | `POST /shop/purchase` uses the `price` field from the request body as the unit price. Sending `price: -1000` completes the purchase and **adds** 1,000 FC to the balance. |
| Build | Server v1 (`day60_server_v1.py`) |
| Severity | Critical (currency can be created out of nothing; no client mod needed, only a proxy) |
| Priority | P1 (block release) |
| Reproducibility | 5/5 (TM-02, 03, 04, 08 and Day 62 TC-SHOP-13 all reproduce) |

**Steps to Reproduce**
1. Reset DB seed. Log in as `qa_user1` (FC 5,000).
2. Set a request breakpoint on `POST /shop/purchase` in the proxy.
3. In the shop page, buy item 101 (Premium Player Pack, server price 1,000 FC) x1.
4. At the breakpoint, change the body from `{"item_id": 101, "quantity": 1}` to `{"item_id": 101, "quantity": 1, "price": -1000}` and resume.
5. Check the response and `GET /accounts/{account_id}/currency`.

**Expected Result**
- The server ignores any client price (API spec R5) and charges the server price.
- 200, `unit_price: 1000`, `balance_after: 4000`, inventory +1.

**Actual Result**
- 200, `unit_price: -1000`, `balance_after: 6000` (FC **+1,000**), inventory +1.
- Same pattern with other values:

| Case | Body change | Response | FC change | Inventory |
|---|---|---|---|---|
| TM-02 | `price: 1` | 200, unit_price 1 | -1 | +1 |
| TM-03 | `price: 0` | 200, unit_price 0 | 0 | +1 |
| TM-04 | `price: -1000` | 200, unit_price -1000 | **+1,000** | +1 |
| TM-08 | `quantity: 10, price: 1` | 200, unit_price 1 | -10 | +10 (expected 409, server total 10,000 > balance 5,000) |

**Root Cause**
- The request model accepts an optional `price` field, and the purchase handler uses it as the unit price when present instead of reading `shop_items.price`.

**Fix / Verification**
- v2 removed `price` from the request model, so the server price is always used.
- Re-ran the same 11 tamper cases on v2: 6/11 → 10/11 PASS. TM-02~04 now charge 1,000 FC.

**Attachments**
- `day67_tamper_cases.md` (v1 result table), `day68_tamper_cases_v2.md` (v2 result table)
- Proxy log: `handoff/day67_tamper_log.jsonl`

---

## BUG-002 Purchase button stays enabled during a slow response; second click charges twice

| Field | Value |
|---|---|
| Summary | While the purchase response is delayed, the shop page keeps the Buy button enabled and shows no loading state. Clicking again sends a second purchase with a new `request_id`, and both are charged. |
| Build | Client `day65_shop_client.html`, Server v1 |
| Severity | Major (duplicate charge to the user; refund/CS issue) |
| Priority | P2 |
| Reproducibility | 1/1 (automated Selenium scenario, response delayed 6 s) |

**Steps to Reproduce**
1. Reset DB seed. Open `http://127.0.0.1:8000/shop` through the proxy and log in as `qa_user1`.
2. Set the proxy to hold the `POST /shop/purchase` response for 6 seconds (AutoResponder delay rule).
3. Click Buy for item 101 x1.
4. While waiting (about 1.5 s later), click Buy again.
5. Wait for both responses and check the balance and purchase history.

**Expected Result**
- The Buy button is disabled (or shows a loading state) until the first response arrives.
- Only one purchase is created: FC -1,000, purchase history 1 row.

**Actual Result**
- Buy button enabled during the wait: `True`.
- Two `200` responses (`purchase_id` 1 and 2). FC 5,000 → 3,000 (**-2,000**), purchase history **2 rows**.
- No message shown to the user during the delay.

**Root Cause**
- The client creates a new `request_id` on every click and has no in-flight guard. The server treats the second click as a new purchase, which is correct for a different `request_id`.

**Suggested Fix**
- Disable the Buy button until the response (or timeout) arrives.
- Reuse the same `request_id` for the same purchase intent so the server can drop duplicates.

**Related Findings (same run)**
- 500 and 503 (maintenance) responses: no error message is shown to the user; the status is only in the developer log area.

**Attachments**
- Screenshot: `day68_screenshots/day68_client_4_delay.png`
- Console log: `handoff/day68_console.txt`

---

## BUG-003 Concurrent retries with the same request_id grant the item twice

| Field | Value |
|---|---|
| Summary | When the original request and its retries (same `request_id`) reach the server at the same time, only one purchase is recorded and charged, but the item is added to the inventory twice. |
| Build | Server v2 (`day68_server_v2.py`) |
| Severity | Major (item duplication; currency and inventory no longer match) |
| Priority | P2 |
| Reproducibility | 1/1 in the network matrix run; the concurrency test (Day 64, 10 parallel requests) shows the same lack of locking |

**Steps to Reproduce**
1. Reset DB seed. Log in as `qa_user1`.
2. Configure the proxy condition "reorder": hold the purchase request and its retries, then release all of them at once in reverse order.
3. Client buys item 101 x1 with timeout 1 s, max 3 attempts, 0.2 s interval, reusing the same `request_id` (also sent as `Idempotency-Key`).
4. After the last attempt returns, check `purchases`, `currency` and `inventory`.

**Expected Result**
- One purchase row, FC -1,000, inventory +1 (the request is idempotent).

**Actual Result**
- Attempts: Timeout → Timeout → 200 (client shows success).
- Purchase history 1 row, FC -1,000, inventory **+2**.

**Root Cause**
- The duplicate check is "SELECT by request_id, then INSERT" with no lock, on an autocommit connection. The inventory is updated before the purchase row is inserted. When requests arrive together, all of them pass the check and update the inventory; the later ones fail on the unique `request_id` INSERT and return the first result, but their inventory updates are already committed.

**Fix / Verification**
- v3 (`day70_server_v3.py`): the `Idempotency-Key` is claimed first (`IN_PROGRESS` → `DONE`, stored response), and balance and inventory are updated in one transaction with `SELECT ... FOR UPDATE`.
- Same matrix on v3: same-id retries 4/5 → **5/5 PASS** (this case: 1 row / FC -1,000 / inventory +1). Day 63·64 DB integrity and concurrency tests: **13 passed**.

**Open Issue**
- If the client creates a new `request_id` on every retry, the server cannot tell it is the same purchase (v3 still fails 4/5 new-id cases). This needs a client-side requirement as well.

**Attachments**
- `day69_network_matrix.md`, `day70_retry_compare.md`
- Console log: `handoff/day70_console.txt`

---

## Writing Notes
- Summary in one sentence: what is wrong + the impact in numbers.
- Severity is about impact on the user/service; Priority is about how soon to fix. BUG-001 is both high because currency can be created freely.
- Steps include the starting state (seed reset, balance) so anyone can reproduce with the same numbers.
