# Day 60 시딩 결함 목록 (봉인 — Day 64 전까지 열지 않기)

대상: `day60_server_v1.py` / 명세: `day59_api_spec.md` / 7개

| ID | 위치 | 위반 규칙 | 결함 내용 | 재현 조건 | 실제 결과 (Day 60 비공개 확인) | 잡을 수 있는 TC |
|---|---|---|---|---|---|---|
| D1 | L216 | R3 수량 하한 | 수량 하한 검사가 `< 0`이라 quantity 0이 통과 | 101 quantity 0 구매 | 200, total_price 0, 구매 이력 1건 생성 | TC-SHOP-04 |
| D2 | L64, L71 | 토큰 유효기간 1800초 | 만료 판정을 `TIMESTAMPDIFF(MINUTE, ...) >= 1`로 해 만료 후 최대 59초 동안 토큰이 유효 | expires_at = NOW() - 1초로 조작 후 조회 | 200 (기대 401 TOKEN_EXPIRED) | TC-AUTH-09 |
| D3 | L277~ | R8 권한 | 인벤토리 조회에 본인/ADMIN 확인 누락 (재화 조회에는 있음) | qa_user2 토큰으로 계정 1 인벤토리 조회 | 200 (기대 403 FORBIDDEN) | TC-INV-03 |
| D4 | L151 | R1 잔액 상한 / 409 BALANCE_CAP_EXCEEDED | 지급 전 상한 검사 누락. DB CHECK가 막아 500 응답 (JSON 아님) | 잔액 99,999,999에 1 지급 | 500 Internal Server Error (기대 409) | TC-GRANT-08 |
| D5 | L232~L258 | R6, 동시성 | 잔액을 SELECT로 읽고 파이썬에서 계산한 값으로 UPDATE (잠금 없음) → 동시 구매 시 갱신 손실 | FC 5000에서 101 × 1을 다른 request_id로 동시 10회 | 10건 모두 200, 실제 차감 2000 (기대 차감 = 성공 건수 × 1000) | TC-SHOP-18 |
| D6 | L52, L237, L241 | R6 원자성 | autocommit 연결 + 인벤토리 증가를 잔액 검사보다 먼저 실행 → 잔액 부족으로 실패해도 인벤토리가 늘어남 | qa_user2(FC 0)로 101 × 1 구매 | 409 INSUFFICIENT_BALANCE, 그러나 inventory (2, 101, 1) 생성 | TC-SHOP-16, TC-INV-04, TC-DB-01(간접) |
| D7 | L228 | R5 서버 가격 | 요청 본문에 `price`가 있으면 그 값을 단가로 사용 | 101 × 1에 price: 1 추가 | 200, unit_price 1, 잔액 1만 차감 | TC-SHOP-13 |

## 참고
- 정상 흐름(Day 61 대상 TC 8건)에는 영향이 없도록 심음. 기동 점검 `day60_smoke_check.py` 7/7 PASS
- D6 때문에 같은 request_id 동시 요청 시 응답은 멱등 처리되지만 인벤토리가 중복 증가할 수 있음 (TC-SHOP-17에서 인벤토리까지 확인하면 함께 드러남)
