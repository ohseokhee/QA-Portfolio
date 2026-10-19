# Day 67 요청 변조 케이스 (day66_https_server.py)

> 클라이언트는 항상 `{"item_id": 101, "quantity": 1}`(price 없음)을 보내고, 프록시가 중간에서 본문을 변조했다. 기대값은 `day59_api_spec.md` 업무 규칙 기준. 케이스마다 fc_qa_lab 시드(qa_user1 FC 5000)에서 시작.

| ID | 변조 내용 | 응답 | 응답 요약 | FC 변화 | 인벤토리 증가 | 기대 (상태 / FC 변화 / 증가) | 근거 | 판정 |
|---|---|---|---|---|---|---|---|---|
| TM-01 | 변조 없음 (기준) | 200 | unit_price=1000, balance_after=4000 | -1000 | 1 | 200 / FC -1000 / +1 | 정상 구매 | PASS |
| TM-02 | price 1 추가 | 200 | unit_price=1, balance_after=4999 | -1 | 1 | 200 / FC -1000 / +1 | R5 클라이언트 가격 무시 | **FAIL** |
| TM-03 | price 0 추가 | 200 | unit_price=0, balance_after=5000 | +0 | 1 | 200 / FC -1000 / +1 | R5 | **FAIL** |
| TM-04 | price -1000 추가 | 200 | unit_price=-1000, balance_after=6000 | +1000 | 1 | 200 / FC -1000 / +1 | R5 | **FAIL** |
| TM-05 | quantity 0 | 200 | unit_price=1000, balance_after=5000 | +0 | 0 | 400 / FC +0 / +0 | R3 수량 1 이상 | **FAIL** |
| TM-06 | quantity -1 | 400 | VALIDATION_ERROR | +0 | 0 | 400 / FC +0 / +0 | R3 | PASS |
| TM-07 | quantity 11 (1회 최대 10) | 400 | VALIDATION_ERROR | +0 | 0 | 400 / FC +0 / +0 | R3 | PASS |
| TM-08 | quantity 10, price 1 | 200 | unit_price=1, balance_after=4990 | -10 | 10 | 409 / FC +0 / +0 | R5 서버 가격 10000 > 잔액 5000 | **FAIL** |
| TM-09 | item_id 105 (판매 종료) | 409 | ITEM_NOT_ON_SALE | +0 | 0 | 409 / FC +0 / +0 | R10 | PASS |
| TM-10 | item_id 999 (없는 아이템) | 404 | ITEM_NOT_FOUND | +0 | 0 | 404 / FC +0 / +0 | ITEM_NOT_FOUND | PASS |
| TM-11 | item_id 104 (FC 3000) | 200 | unit_price=3000, balance_after=2000 | -3000 | 1 | 200 / FC -3000 / +1 | 서버 가격으로 차감 | PASS |

- 결과: 6/11 PASS, 결함 의심 5건
  - TM-02 price 1 추가: 응답 200, FC -1, 인벤토리 +1
  - TM-03 price 0 추가: 응답 200, FC +0, 인벤토리 +1
  - TM-04 price -1000 추가: 응답 200, FC +1000, 인벤토리 +1
  - TM-05 quantity 0: 응답 200, FC +0, 인벤토리 +0
  - TM-08 quantity 10, price 1: 응답 200, FC -10, 인벤토리 +10
