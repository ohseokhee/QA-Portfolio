# Day 70 재시도 안전 처리 수정 전후 비교

> 같은 클라이언트(`day69_test_retry.py`: 타임아웃 1초, 최대 3회, Idempotency-Key 헤더 = request_id)로 서버 v2(request_id 순차 중복 검사)와 v3(Idempotency-Key 선점 + 트랜잭션·행 잠금)를 비교. 기대값: 구매 이력 1건 / FC -1000 / 인벤토리 +1

| 조건 | 재시도 방식 | v2 구매·FC·인벤토리 | v2 판정 | v3 시도 결과 | v3 구매·FC·인벤토리 | v3 판정 |
|---|---|---|---|---|---|---|
| 지연 (응답 1.5초 지연 > 타임아웃 1초) | new-id | 3 / -3000 / +3 | **FAIL** | Timeout → Timeout → Timeout | 3 / -3000 / +3 | **FAIL** |
| 지연 (응답 1.5초 지연 > 타임아웃 1초) | same-id | 1 / -1000 / +1 | PASS | Timeout → Timeout → Timeout | 1 / -1000 / +1 | PASS |
| 패킷 손실 - 첫 요청 유실 | new-id | 1 / -1000 / +1 | PASS | ConnErr → 200 | 1 / -1000 / +1 | PASS |
| 패킷 손실 - 첫 요청 유실 | same-id | 1 / -1000 / +1 | PASS | ConnErr → 200 | 1 / -1000 / +1 | PASS |
| 패킷 손실 - 첫 응답 유실 (서버는 처리) | new-id | 2 / -2000 / +2 | **FAIL** | ConnErr → 200 | 2 / -2000 / +2 | **FAIL** |
| 패킷 손실 - 첫 응답 유실 (서버는 처리) | same-id | 1 / -1000 / +1 | PASS | ConnErr → 200 | 1 / -1000 / +1 | PASS |
| 순서 뒤바뀜 (원 요청·재시도 3개가 역순 동시 도착) | new-id | 3 / -2000 / +3 | **FAIL** | Timeout → Timeout → 200 | 3 / -3000 / +3 | **FAIL** |
| 순서 뒤바뀜 (원 요청·재시도 3개가 역순 동시 도착) | same-id | 1 / -1000 / +2 | **FAIL** | Timeout → Timeout → 200 | 1 / -1000 / +1 | PASS |
| 일시 끊김 (처음 2개 응답 끊김 후 복구) | new-id | 3 / -3000 / +3 | **FAIL** | ConnErr → ConnErr → 200 | 3 / -3000 / +3 | **FAIL** |
| 일시 끊김 (처음 2개 응답 끊김 후 복구) | same-id | 1 / -1000 / +1 | PASS | ConnErr → ConnErr → 200 | 1 / -1000 / +1 | PASS |

- 전체: v2 5/10 PASS → v3 6/10 PASS
- same-id(같은 키로 재시도): v2 4/5 → v3 5/5
- new-id(재시도마다 새 키): 서버는 서로 다른 구매로 볼 수밖에 없음 → 클라이언트가 구매 의도 단위로 키를 한 번 만들고 재시도에 재사용해야 함 (클라이언트 요구사항)
- Day 63·64 pytest(v3) 종료 코드: 0 (0 = 전체 통과)
