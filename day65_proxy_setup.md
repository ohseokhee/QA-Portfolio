# Day 65 프록시 캡처 환경 구성

> 대상: 로컬 모의 게임 서버(`day60_server_v1` + 상점 페이지)만. 상용 게임·외부 서비스 트래픽은 캡처·변조하지 않는다.

## 1. 구성도

```
[LDPlayer 브라우저] --(Wi-Fi 프록시: PC IP:8888)--> [Fiddler Classic (PC)] --> [모의 서버 127.0.0.1:8000]
        http://ipv4.fiddler:8000/shop                    요청·응답 기록
```

- LDPlayer는 PC 안의 가상 안드로이드 기기. 네트워크상으로는 PC와 다른 기기처럼 동작한다
- 안드로이드 Wi-Fi 설정의 수동 프록시를 PC의 Fiddler 포트(8888)로 지정하면 브라우저의 HTTP 요청이 모두 Fiddler를 거친다
- `ipv4.fiddler`는 Fiddler가 인식하는 특수 호스트명으로, Fiddler를 실행 중인 PC의 `127.0.0.1`로 연결된다. 서버를 `127.0.0.1`에만 열어 두고도 LDPlayer에서 접속할 수 있다 (프록시를 거치지 않으면 접속되지 않으므로 캡처 경로 확인도 겸함)

### 1.1 실제 진행 결과

- PC 클라이언트(`day65_client_check.py --proxy http://127.0.0.1:8888`) 캡처 성공: Fiddler 세션 6건, Process `python`
- LDPlayer: Fiddler까지 연결은 확인(`http://{PC IP}:8888` Echo Service, Originating Process `ld9boxheadless`)했으나 크롬이 Wi-Fi 수동 프록시를 타지 않아 상점 페이지 캡처 실패
- Day 66~70은 LDPlayer 대신 PC 브라우저를 클라이언트로 사용 (Fiddler 실행 시 Windows 시스템 프록시로 자동 등록되므로 PC 크롬은 별도 설정 없이 캡처됨)

## 2. 구성 요소

| 구성 요소 | 값 | 비고 |
|---|---|---|
| 서버 실행 | `py day65_serve_client.py` | 시드 초기화 후 `127.0.0.1:8000` 기동 |
| 상점 페이지 | `GET /shop` → `day65_shop_client.html` | 로그인·재화 조회·구매·인벤토리 조회 버튼. 같은 출처로 `fetch` |
| Fiddler 포트 | 8888 (기본값) | Tools > Options > Connections |
| 원격 접속 허용 | Allow remote computers to connect | 체크 후 Fiddler 재시작 필요 |
| PC IP | `ipconfig`의 실제 네트워크 어댑터 IPv4 | vEthernet(WSL·Hyper-V) 어댑터 주소 아님 |
| LDPlayer 프록시 | 수동, 호스트 = PC IP, 포트 = 8888 | 설정 > Wi-Fi > 네트워크 길게 누르기 > 네트워크 수정 > 고급 옵션 |
| 접속 URL | `http://ipv4.fiddler:8000/shop` | `http://`까지 직접 입력 |

## 3. 페이지가 보내는 요청

| 순서 | 버튼 | 요청 | 확인할 내용 |
|---|---|---|---|
| 1 | 로그인 | `POST /auth/login` | 요청 본문에 아이디·비밀번호가 평문 JSON으로 보임 (HTTP라서) |
| 2 | (자동) | `GET /accounts/{id}/currency` | `Authorization: Bearer {token}` 헤더 |
| 3 | 구매 | `POST /shop/purchase` | 본문 `item_id`, `quantity`, `request_id` |
| 4 | (자동) | `GET /accounts/{id}/currency`, `GET /accounts/{id}/inventory` | 차감 후 잔액, 인벤토리 수량 |

## 4. 대체 경로

- `ipv4.fiddler` 접속이 안 될 때: `py day65_serve_client.py --host 0.0.0.0`으로 실행하고 `http://{PC IP}:8000/shop` 접속. Windows 방화벽에서 Python의 개인 네트워크 접속 허용 필요
- PC 단독 확인: `py day65_client_check.py --proxy http://127.0.0.1:8888` → 같은 요청이 Fiddler를 거쳐 전송됨
- PC 브라우저: Fiddler를 켠 상태에서 PC 크롬으로 `http://ipv4.fiddler:8000/shop` 접속

## 4.1 주의

- Fiddler는 켜질 때 Windows 시스템 프록시(`127.0.0.1:8888`)로 자동 등록된다. 파이썬 `urllib`·`requests`도 이를 따라가므로, 프록시를 의도하지 않은 요청(서버 기동 확인 등)은 `requests.Session().trust_env = False`로 직접 접속해야 한다

## 5. Charles와 비교 (개념)

| 항목 | Fiddler Classic | Charles |
|---|---|---|
| 플랫폼 | Windows | Windows·macOS·Linux (Java) |
| 가격 | 무료 | 유료 (30일 체험) |
| 요청 멈춤·수정 | Breakpoints | Breakpoints |
| 미리 정한 응답 | AutoResponder | Map Local / Rewrite |
| 네트워크 지연 흉내 | 제한적 (스크립트) | Throttling 내장 |
