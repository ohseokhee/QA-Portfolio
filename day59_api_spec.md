# 모의 게임 서버 API 명세 v1 (Day 59)

> FC 온라인 구조를 본뜬 상점·재화 API. Day 60에서 FastAPI로 구현하고, Day 61~64 테스트는 이 문서만 보고 설계한다(명세 기반 블랙박스).

## 1. 공통

| 항목 | 값 |
|---|---|
| Base URL | `http://localhost:8000` |
| DB | fc_qa_lab (MariaDB, 스키마: `day59_schema.sql`) |
| 요청·응답 형식 | JSON (`Content-Type: application/json`) |
| 인증 | 로그인 API가 발급한 토큰을 `Authorization: Bearer {token}` 헤더로 전송 |
| 토큰 유효기간 | 발급 후 1800초(30분) |
| 재화 | `FC`(유료 재화), `BP`(무료 재화). 정수만 사용 |

### 1.1 업무 규칙

| ID | 규칙 |
|---|---|
| R1 | 재화 잔액은 재화 종류별로 0 이상 99,999,999 이하 |
| R2 | 1회 지급량은 1 이상 1,000,000 이하 |
| R3 | 1회 구매 수량은 1 이상, 아이템별 `max_per_purchase` 이하 |
| R4 | 구매 후 보유 수량이 아이템별 `max_owned`를 넘으면 구매 불가 |
| R5 | 구매 금액 = 서버의 `shop_items.price` × 수량. 클라이언트가 보낸 가격은 받지 않는다 |
| R6 | 잔액 차감, 인벤토리 증가, 구매 이력, 재화 변동 이력은 한 트랜잭션. 하나라도 실패하면 전부 취소 |
| R7 | 같은 계정이 같은 `request_id`로 다시 구매하면 새로 차감하지 않고 처음 결과를 그대로 반환 (멱등성) |
| R8 | 일반 사용자는 자기 계정의 재화·인벤토리만 조회 가능. ADMIN은 모든 계정 조회 가능 |
| R9 | 재화 지급은 ADMIN만 가능하며 지급마다 `currency_transactions`에 운영자 ID와 함께 기록 |
| R10 | `is_on_sale = 0`인 아이템은 구매 불가 |
| R11 | BANNED 계정은 로그인 불가 |

### 1.2 오류 응답 형식

```json
{ "error_code": "INSUFFICIENT_BALANCE", "message": "잔액이 부족합니다." }
```

| HTTP | error_code | 상황 |
|---|---|---|
| 400 | VALIDATION_ERROR | 필수값 누락, 타입 오류, 범위 밖 값 (FastAPI 기본 422 대신 400으로 통일) |
| 401 | UNAUTHORIZED | 토큰 없음, 형식 오류, 존재하지 않는 토큰 |
| 401 | TOKEN_EXPIRED | 만료된 토큰 |
| 401 | INVALID_CREDENTIALS | 아이디 또는 비밀번호 불일치 |
| 403 | ACCOUNT_BANNED | 제재 계정 로그인 |
| 403 | FORBIDDEN | 권한 없음 (다른 계정 조회, 일반 사용자의 지급 요청) |
| 404 | ACCOUNT_NOT_FOUND | 없는 계정 |
| 404 | ITEM_NOT_FOUND | 없는 아이템 |
| 409 | INSUFFICIENT_BALANCE | 잔액 부족 |
| 409 | BALANCE_CAP_EXCEEDED | 지급 후 잔액이 99,999,999 초과 |
| 409 | ITEM_NOT_ON_SALE | 판매 종료 아이템 |
| 409 | INVENTORY_LIMIT_EXCEEDED | 구매 후 보유 수량이 상한 초과 |

### 1.3 테스트 계정 (로컬 모의 서버 전용 시드 데이터)

| account_id | username | password | role | status | FC | BP |
|---|---|---|---|---|---|---|
| 1 | qa_user1 | Test1234! | USER | ACTIVE | 5,000 | 200,000 |
| 2 | qa_user2 | Test1234! | USER | ACTIVE | 0 | 0 |
| 3 | qa_admin | Admin1234! | ADMIN | ACTIVE | 0 | 0 |
| 4 | qa_banned | Test1234! | USER | BANNED | 1,000 | 1,000 |

### 1.4 상점 아이템 (시드 데이터)

| item_id | 이름 | 재화 | 가격 | 1회 최대 | 보유 상한 | 판매 |
|---|---|---|---|---|---|---|
| 101 | 프리미엄 선수팩 | FC | 1,000 | 10 | 999 | O |
| 102 | 일반 선수팩 | BP | 50,000 | 10 | 999 | O |
| 103 | 훈련 부스터 | BP | 10,000 | 10 | 999 | O |
| 104 | 클럽 유니폼 세트 | FC | 3,000 | 1 | 1 | O |
| 105 | 이벤트 한정팩 | FC | 500 | 10 | 999 | X |

---

## 2. 엔드포인트

### 2.1 로그인 (토큰 발급)

`POST /auth/login` · 인증 불필요

요청
```json
{ "username": "qa_user1", "password": "Test1234!" }
```

| 필드 | 타입 | 규칙 |
|---|---|---|
| username | string | 필수, 4~20자 |
| password | string | 필수, 8~20자 |

응답 200
```json
{ "access_token": "64자리 hex", "token_type": "Bearer", "expires_in": 1800, "account_id": 1 }
```

오류: 400 VALIDATION_ERROR, 401 INVALID_CREDENTIALS, 403 ACCOUNT_BANNED

### 2.2 재화 조회

`GET /accounts/{account_id}/currency` · 인증 필요 (R8)

응답 200
```json
{ "account_id": 1, "balances": { "FC": 5000, "BP": 200000 } }
```

오류: 401 UNAUTHORIZED / TOKEN_EXPIRED, 403 FORBIDDEN, 404 ACCOUNT_NOT_FOUND

### 2.3 재화 지급 (운영툴)

`POST /admin/currency/grant` · ADMIN 토큰 필요 (R9)

요청
```json
{ "account_id": 2, "currency_type": "FC", "amount": 10000, "memo": "보상 지급" }
```

| 필드 | 타입 | 규칙 |
|---|---|---|
| account_id | int | 필수, 존재하는 계정 |
| currency_type | string | 필수, `FC` 또는 `BP` |
| amount | int | 필수, 1~1,000,000 (R2) |
| memo | string | 선택, 100자 이하 |

응답 200
```json
{ "tx_id": 1, "account_id": 2, "currency_type": "FC", "amount": 10000, "balance_after": 10000 }
```

오류: 400 VALIDATION_ERROR, 401, 403 FORBIDDEN, 404 ACCOUNT_NOT_FOUND, 409 BALANCE_CAP_EXCEEDED

### 2.4 상점 구매

`POST /shop/purchase` · 인증 필요. 구매 계정은 토큰의 계정

요청
```json
{ "item_id": 101, "quantity": 2, "request_id": "c1b7c0e2-0001" }
```

| 필드 | 타입 | 규칙 |
|---|---|---|
| item_id | int | 필수, 존재하는 아이템 |
| quantity | int | 필수, 1~`max_per_purchase` (R3) |
| request_id | string | 필수, 1~64자, 계정 안에서 유일 (R7) |

응답 200
```json
{
  "purchase_id": 1, "item_id": 101, "quantity": 2,
  "unit_price": 1000, "total_price": 2000, "currency_type": "FC",
  "balance_after": 3000, "inventory_quantity": 2
}
```

같은 `request_id` 재요청: 200, 처음 응답과 같은 본문, 잔액·인벤토리 변화 없음 (R7)

오류: 400 VALIDATION_ERROR, 401, 404 ITEM_NOT_FOUND, 409 INSUFFICIENT_BALANCE / ITEM_NOT_ON_SALE / INVENTORY_LIMIT_EXCEEDED

### 2.5 인벤토리 조회

`GET /accounts/{account_id}/inventory` · 인증 필요 (R8)

응답 200 (수량 0인 아이템은 제외, item_id 오름차순)
```json
{ "account_id": 1, "items": [ { "item_id": 101, "name": "프리미엄 선수팩", "quantity": 2 } ] }
```

오류: 401, 403 FORBIDDEN, 404 ACCOUNT_NOT_FOUND

---

## 3. DB 테이블 (fc_qa_lab)

| 테이블 | 용도 | 테스트에서 대조할 값 |
|---|---|---|
| accounts | 계정, 권한, 제재 상태 | role, status |
| auth_tokens | 발급 토큰과 만료 시각 | expires_at (만료 토큰 만들기) |
| account_currency | 재화 종류별 잔액 (CHECK 0~99,999,999) | 응답 잔액 = DB 잔액 |
| shop_items | 가격, 1회 최대, 보유 상한, 판매 여부 | 가격 × 수량 = 차감액 |
| inventory | 계정별 보유 수량 | 응답 수량 = DB 수량 |
| purchase_history | 구매 이력, request_id 유일 | 구매 합계 = 차감 합계 |
| currency_transactions | 지급(+)·구매(-) 변동 이력 | 이력 합계 + 초기 잔액 = 현재 잔액 |

---

## 4. 테스트 설계

### 4.1 동등 분할 (Equivalence Partitioning)

같은 결과가 나올 입력끼리 묶고 각 묶음에서 대표값 하나만 고른다.

| 입력 | 유효 분할 (대표값) | 무효 분할 (대표값) |
|---|---|---|
| 로그인 계정 | ACTIVE 계정 + 맞는 비밀번호 (qa_user1) | 틀린 비밀번호 / 없는 계정 / BANNED 계정 |
| 토큰 | 유효 토큰 | 헤더 없음 / 임의 문자열 / 만료 토큰 |
| 조회 대상 계정 | 본인 계정, ADMIN이 조회한 타인 계정 | 일반 사용자가 조회한 타인 계정 / 없는 계정(9999) |
| currency_type | FC, BP | "GOLD", 빈 문자열, 소문자 "fc" |
| amount (지급) | 1~1,000,000 (5000) | 0 이하 (-100), 1,000,000 초과 (2,000,000), 문자열 ("100") |
| 지급 요청자 | ADMIN | USER |
| item_id | 판매 중 (101) | 없는 아이템 (999), 판매 종료 (105) |
| quantity | 1~max (3) | 0 이하 (-1), max 초과 (11), 소수 (1.5) |
| 잔액 상태 | 잔액 ≥ 구매 금액 | 잔액 < 구매 금액 |
| request_id | 처음 쓰는 값 | 이미 쓴 값 (멱등 처리 대상) |

### 4.2 경계값 분석 (Boundary Value Analysis)

경계 바로 아래·경계·바로 위 3점을 테스트한다.

| 대상 | 경계 | 테스트 값 | 기대 결과 |
|---|---|---|---|
| 지급 amount 하한 | 1 | 0 / 1 / 2 | 400 / 200 / 200 |
| 지급 amount 상한 | 1,000,000 | 999,999 / 1,000,000 / 1,000,001 | 200 / 200 / 400 |
| 지급 후 잔액 상한 | 99,999,999 | 잔액 98,999,999에 1,000,000 지급(=99,999,999) / 잔액 99,999,999에 1 지급 | 200 / 409 |
| 구매 quantity 하한 | 1 | 0 / 1 / 2 | 400 / 200 / 200 |
| 구매 quantity 상한 (101) | 10 | 9 / 10 / 11 | 200 / 200 / 400 |
| 구매 quantity 상한 (104) | 1 | 1 / 2 | 200 / 400 |
| 잔액 = 구매 금액 | 잔액 - 금액 = 0 | FC 1,000에서 101 1개 (잔액 0) / FC 999에서 101 1개 | 200 / 409 |
| 보유 상한 (104) | 1 | 미보유에서 1개 / 1개 보유에서 1개 | 200 / 409 |
| 보유 상한 (101) | 999 | 990 보유에서 9개(=999) / 990 보유에서 10개(=1000) | 200 / 409 |
| 토큰 유효기간 | 발급 후 1800초 | 만료 1초 전 / 만료 1초 후 (DB의 expires_at 조작) | 200 / 401 TOKEN_EXPIRED |
| username 길이 | 4~20 | 3자 / 4자 / 20자 / 21자 (모두 없는 계정) | 400 / 401 / 401 / 400 (길이 검증 통과 시 계정 확인 단계에서 401) |
| request_id 길이 | 1~64 | 빈 문자열 / 64자 / 65자 | 400 / 200 / 400 |

### 4.3 테스트 케이스 목록

| TC ID | API | 분류 | 기법 | 조건 | 기대 결과 | 실행 Day |
|---|---|---|---|---|---|---|
| TC-AUTH-01 | 로그인 | 정상 | EP | qa_user1 / Test1234! | 200, 토큰 64자, expires_in 1800 | 61 |
| TC-AUTH-02 | 로그인 | 부정 | EP | 틀린 비밀번호 | 401 INVALID_CREDENTIALS | 62 |
| TC-AUTH-03 | 로그인 | 부정 | EP | 없는 username | 401 INVALID_CREDENTIALS | 62 |
| TC-AUTH-04 | 로그인 | 부정 | EP | qa_banned | 403 ACCOUNT_BANNED | 62 |
| TC-AUTH-05 | 로그인 | 부정 | EP | password 필드 누락 | 400 VALIDATION_ERROR | 62 |
| TC-AUTH-06 | 로그인 | 부정 | BVA | username 3자 / 21자 | 400 VALIDATION_ERROR | 62 |
| TC-AUTH-07 | 공통 | 부정 | EP | Authorization 헤더 없이 재화 조회 | 401 UNAUTHORIZED | 62 |
| TC-AUTH-08 | 공통 | 부정 | EP | 임의 문자열 토큰 | 401 UNAUTHORIZED | 62 |
| TC-AUTH-09 | 공통 | 부정 | BVA | 만료 1초 후 토큰 | 401 TOKEN_EXPIRED | 62 |
| TC-AUTH-10 | 공통 | 정상 | BVA | 만료 1초 전 토큰 | 200 | 62 |
| TC-CUR-01 | 재화 조회 | 정상 | EP | 본인 계정 조회 | 200, FC·BP 키 모두 존재, 정수 | 61 |
| TC-CUR-02 | 재화 조회 | 정상 | EP | ADMIN이 타인 계정 조회 | 200 | 61 |
| TC-CUR-03 | 재화 조회 | 부정 | EP | qa_user1 토큰으로 계정 2 조회 | 403 FORBIDDEN | 62 |
| TC-CUR-04 | 재화 조회 | 부정 | EP | ADMIN이 계정 9999 조회 | 404 ACCOUNT_NOT_FOUND | 62 |
| TC-GRANT-01 | 재화 지급 | 정상 | EP | ADMIN, FC 5000 | 200, balance_after = 이전 + 5000 | 61 |
| TC-GRANT-02 | 재화 지급 | 정상 | BVA | amount 1 / 1,000,000 | 200 | 62 |
| TC-GRANT-03 | 재화 지급 | 부정 | BVA | amount 0 / 1,000,001 | 400 VALIDATION_ERROR | 62 |
| TC-GRANT-04 | 재화 지급 | 부정 | EP | amount -100 | 400 VALIDATION_ERROR | 62 |
| TC-GRANT-05 | 재화 지급 | 부정 | EP | currency_type "GOLD" | 400 VALIDATION_ERROR | 62 |
| TC-GRANT-06 | 재화 지급 | 부정 | EP | USER 토큰으로 지급 | 403 FORBIDDEN, 잔액 변화 없음 | 62 |
| TC-GRANT-07 | 재화 지급 | 부정 | EP | 없는 account_id 9999 | 404 ACCOUNT_NOT_FOUND | 62 |
| TC-GRANT-08 | 재화 지급 | 부정 | BVA | 지급 후 잔액 99,999,999 / 100,000,000 | 200 / 409 BALANCE_CAP_EXCEEDED | 62 |
| TC-GRANT-09 | 재화 지급 | DB | - | 지급 1회 | currency_transactions에 +amount, operator_id = 3 기록 | 63 |
| TC-SHOP-01 | 구매 | 정상 | EP | 101 × 2 | 200, total 2000, 잔액 -2000, 인벤토리 +2 | 61 |
| TC-SHOP-02 | 구매 | 정상 | EP | BP 아이템 103 × 1 | 200, BP만 차감, FC 변화 없음 | 61 |
| TC-SHOP-03 | 구매 | 정상 | BVA | quantity 1 / 10 (101) | 200 | 62 |
| TC-SHOP-04 | 구매 | 부정 | BVA | quantity 0 / 11 (101) | 400 VALIDATION_ERROR | 62 |
| TC-SHOP-05 | 구매 | 부정 | EP | quantity -1 | 400 VALIDATION_ERROR, 잔액 증가 없음 | 62 |
| TC-SHOP-06 | 구매 | 부정 | EP | 잔액 부족 (qa_user2) | 409 INSUFFICIENT_BALANCE | 62 |
| TC-SHOP-07 | 구매 | 정상 | BVA | 잔액 = 구매 금액 | 200, balance_after 0 | 62 |
| TC-SHOP-08 | 구매 | 부정 | BVA | 잔액 = 구매 금액 - 1 | 409 INSUFFICIENT_BALANCE | 62 |
| TC-SHOP-09 | 구매 | 부정 | EP | 없는 item_id 999 | 404 ITEM_NOT_FOUND | 62 |
| TC-SHOP-10 | 구매 | 부정 | EP | 판매 종료 105 | 409 ITEM_NOT_ON_SALE | 62 |
| TC-SHOP-11 | 구매 | 부정 | BVA | 104 보유 중 재구매 | 409 INVENTORY_LIMIT_EXCEEDED | 62 |
| TC-SHOP-12 | 구매 | 부정 | BVA | 104 quantity 2 | 400 VALIDATION_ERROR | 62 |
| TC-SHOP-13 | 구매 | 부정 | EP | 요청 본문에 price: 1 추가 | 무시, 서버 가격으로 차감 (R5) | 62 |
| TC-SHOP-14 | 구매 | 정상 | EP | 같은 request_id 재전송 | 200, 같은 purchase_id, 추가 차감 없음 (R7) | 62 |
| TC-SHOP-15 | 구매 | DB | - | 구매 1회 | 응답 잔액 = DB 잔액, 이력 1건, 재화 이력 -total | 63 |
| TC-SHOP-16 | 구매 | DB | - | 실패한 구매(잔액 부족) | 잔액·인벤토리·이력 모두 변화 없음 (R6) | 63 |
| TC-SHOP-17 | 구매 | 동시성 | - | 같은 request_id로 동시 10회 | 차감 1회, 이력 1건 | 64 |
| TC-SHOP-18 | 구매 | 동시성 | - | 다른 request_id로 잔액보다 많은 동시 구매 | 잔액 음수 없음, 성공 건수 × 가격 = 차감액 | 64 |
| TC-INV-01 | 인벤토리 | 정상 | EP | 구매 후 본인 조회 | 200, 수량 = 구매 수량 합계 | 61 |
| TC-INV-02 | 인벤토리 | 정상 | EP | 구매 이력 없는 계정 | 200, items 빈 배열 | 61 |
| TC-INV-03 | 인벤토리 | 부정 | EP | 타인 계정 조회 | 403 FORBIDDEN | 62 |
| TC-INV-04 | 인벤토리 | DB | - | 전체 구매 후 | 이력 수량 합계 = 인벤토리 수량 | 63 |
| TC-DB-01 | 정합성 | DB | - | 전체 실행 후 | 초기 잔액 + 변동 이력 합계 = 현재 잔액 (계정·재화별) | 63 |

집계: 46건 (정상 13, 부정 26, DB 정합성 5, 동시성 2) · 실행 Day별 61: 8건, 62: 31건, 63: 5건, 64: 2건
