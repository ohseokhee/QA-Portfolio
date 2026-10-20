# QA-Portfolio

[![Day 86 API Regression](https://github.com/ohseokhee/QA-Portfolio/actions/workflows/day86_api_regression.yml/badge.svg)](https://github.com/ohseokhee/QA-Portfolio/actions/workflows/day86_api_regression.yml)

게임 QA 엔지니어 기술 실습 기록. 모의 게임 서버(상점·재화 API)를 직접 만들고 결함을 심은 뒤, **명세 기반 테스트 → 프록시 변조 → 네트워크 불량 재현 → 수정·회귀**까지 한 사이클을 실행 로그와 수치로 남겼습니다.

> 모든 수치는 각 Day 실행 로그에서 가져왔습니다. 트래픽 캡처·변조·네트워크 조건 실습은 로컬 모의 서버만 대상으로 했습니다.

## 한눈에 보기

| 영역 | 문제 | 해결 | 결과 |
|---|---|---|---|
| API 테스트 (Day 59~64) | 실제 서비스 API 테스트 경험이 없음 | 모의 게임 서버(FastAPI + MariaDB)에 결함 7개를 숨겨 심고, 명세만 보고 Postman·pytest로 블랙박스 테스트 | **시딩 결함 7/7 탐지 (100%)** |
| 프록시 툴 (Day 65~68) | 클라이언트-서버 통신을 검증·변조해 본 경험이 없음 | 프록시로 HTTPS 복호화, 구매 요청 변조, 오류·지연 응답 조작 후 서버 v2 수정 | 변조 테스트 **결함 5건**(음수 가격으로 재화 증가 포함) → v2 회귀 **6/11 → 10/11 PASS** |
| 네트워크 조건 (Day 69~70) | 타임아웃 후 재시도가 중복 결제를 만드는지 확인한 적 없음 | 지연·패킷 손실·순서 뒤바뀜·일시 끊김 5조건 매트릭스, 서버 v3에 Idempotency-Key + 트랜잭션 | 같은 키 재시도 **4/5 → 5/5 PASS**, DB 정합성·동시성 테스트 **13/13 통과** |
| 현지화 (Day 72~73) | 번역 전 UI 깨짐을 미리 찾는 방법 부재 | 의사 현지화 페이지 자동 생성 + Selenium 넘침·줄바꿈 탐지 | 모바일 360px에서 **줄바꿈 10건** 자동 탐지 (원본 0건); 에픽세븐 공식 패치노트 언어별 수정 사례 7건 → LQA 체크리스트 9항목 |
| 도구 공개판 (Day 78~82) | 회사에서 만든 도구를 외부에 보여줄 수 없음 | 사내 연동을 빼고 공개 데이터·서비스로 재구성 | 마켓 소식 다이제스트·스케줄러, KBO 선수 조회(판별 테스트 **17/17 통과**), ADB 메모리·FPS 측정(에뮬레이터 실측, 레벨업 기준 55/50/30 판정) |
| CI (Day 86) | 테스트를 고치다 탐지력이 떨어져도 모름 | GitHub Actions에서 최신 서버 통과 + 결함 시딩 서버 탐지 유지를 함께 게이트로 | push마다 v3 **13/13 통과**, v1 시딩 결함 탐지 유지(DB 대조 3건 + 동시성 D5·D6) |
| 확률형 아이템 (Day 87) | "많이 뽑아 보면 안다"는 감으로 확률 검증 | 뽑기 로그로 카이제곱 적합도 검정·천장 규칙 검증, 필요 표본 수 계산 | 결함 빌드: 천장 오류는 1,000회부터, 확률 오류(1.5%→1.2%)는 100,000회에서 FAIL (필요 약 **32,000회**) |

## 1. 모의 게임 서버 + API 테스트 (Day 59~64)

- **문제**: 테스트 대상 서버가 없어서 API 테스트를 "실제로" 해 볼 수 없음
- **해결**
	- Day 59: 상점·재화 API 명세(엔드포인트 5개, 업무 규칙 R1~R11)와 동등 분할·경계값 분석으로 테스트 케이스 설계 → [`day59_api_spec.md`](day59_api_spec.md)
	- Day 60: FastAPI 서버 v1 구현 + 결함 7개 시딩 (목록은 Day 64까지 봉인)
	- Day 61~62: Postman 정상 흐름(토큰 체이닝) + CSV 데이터 주도 부정·경계값 54케이스, Newman 실행
	- Day 63: API 응답과 DB를 대조하는 pytest 정합성 검증 + Allure 리포트
	- Day 64: `threading.Barrier`로 동시 구매 10건 → 이중 차감 검증, 봉인 해제 후 탐지율 집계
- **결과**
	- 시딩 결함 7/7 탐지. Day별 최초 탐지: Day 62 5개, Day 63 1개(DB 대조로만 드러남), Day 64 1개(동시 요청으로만 재현)
	- 응답만 보는 검증으로는 못 잡는 결함(실패한 구매의 인벤토리 증가)과 순차 요청으로는 재현되지 않는 결함(갱신 손실)을 각각 DB 대조·동시성 테스트로 탐지 → [`day64_seeded_defects.md`](day64_seeded_defects.md), [`day64_newman_report.html`](day64_newman_report.html)

## 2. 프록시 툴: 캡처·복호화·변조·응답 조작 (Day 65~68)

- **문제**: 게임 QA에서 자주 쓰는 프록시 툴(Fiddler 등)로 통신을 검증해 본 경험이 없음
- **해결**
	- Day 65: 상점 웹 클라이언트를 붙이고 Fiddler로 요청·응답 캡처
	- Day 66: 로컬 CA로 서버를 HTTPS 전환, 프록시 인증서 신뢰 전·후 비교 (검증 끄기 옵션 미사용) + 안드로이드 7+ 사용자 인증서 정책 정리 → [`day66_android_cert_trust.md`](day66_android_cert_trust.md)
	- Day 67: 클라이언트는 정상 요청만 보내고 프록시가 가격·수량·아이템 ID를 바꾸는 변조 11케이스 → [`day67_tamper_cases.md`](day67_tamper_cases.md)
	- Day 68: 500·점검(503)·지연 응답을 프록시가 대신 돌려줄 때 상점 페이지 반응을 Selenium으로 확인, 서버 v2(가격·수량 서버 검증) 회귀
- **결과**
	- 변조 11건 중 결함 5건: 서버가 요청의 `price`를 그대로 사용 → **`price -1000`이면 구매했는데 FC 5000 → 6000**
	- 클라이언트 결함 4건: 오류·점검 안내 없음, 응답 지연 중 구매 버튼 활성 → 재클릭으로 **중복 구매 2건**
	- 서버 v2 회귀(기존 테스트 파일 수정 없이 서버만 교체): Day 62 실패 14 → 10, Day 63·64 실패 6 → 5, 변조 6/11 → 10/11
	- 가격 결함이 고쳐지자 숨어 있던 "실패해도 인벤토리 증가" 결함이 드러남(결함 가려짐) → [`day68_tamper_cases_v2.md`](day68_tamper_cases_v2.md)

## 3. 네트워크 불량 조건과 재시도 안전 처리 (Day 69~70)

- **문제**: 응답을 못 받은 클라이언트가 재시도할 때 서버가 이미 처리했다면 중복 결제가 생김
- **해결**
	- Day 69: 지연·요청 유실·응답 유실·순서 뒤바뀜(지연된 원 요청과 재시도 동시 도착)·일시 끊김 5조건 x 재시도 방식 2종(새 ID / 같은 ID) 매트릭스 → [`day69_network_matrix.md`](day69_network_matrix.md)
	- Day 70: 서버 v3 — Idempotency-Key 선점(IN_PROGRESS → DONE, 결과 저장) + 잔액·인벤토리 행 잠금 트랜잭션
- **결과**
	- v2: 10회 중 5회 PASS. 재시도마다 새 ID를 쓰면 최대 **3건 중복 결제**, 같은 ID여도 동시 도착 시 인벤토리 +2
	- v3: 같은 키 재시도 **5/5 PASS**, Day 63·64 DB 정합성·동시성 테스트 **13/13 통과** (v1 6개·v2 5개 실패)
	- 재시도마다 새 키를 만드는 클라이언트는 서버만으로 막을 수 없음 → 서버·클라이언트 양쪽 요구사항으로 정리 → [`day70_retry_compare.md`](day70_retry_compare.md)

## 4. 현지화: 공개 사례 LQA·의사 현지화 자동 점검 (Day 72~73)

- **문제**: 번역문이 길어지면 버튼·표가 깨지는지 번역 전에 알 수 없음
- **해결**: 화면 문자열을 악센트 문자 + 35% 확장 + `[ ]`로 바꾼 페이지를 자동 생성하고, Chrome(headless)으로 모바일 360px·데스크톱 1280px에서 넘침·화면 밖·줄바꿈을 JS로 탐지
- **LQA 체크리스트 (Day 72)**: 에픽세븐 공식 패치노트의 언어별 텍스트 수정 7건(스페인어 스킬 툴팁 대상 오역, 태국어 효과 문구, 특정 언어 팝업 겹침, 비영어 설치 경로 접속 불가 등)을 유형별로 나눠 체크리스트 9항목·심각도 기준으로 정리 → [`day72_lqa_checklist.md`](day72_lqa_checklist.md)
- **결과**: 원본 0건 → 의사 현지화 모바일 **줄바꿈 10건**(구매 버튼 5, 아이템 이름 3, 가격 2), 문제 요소에 테두리를 그린 스크린샷 자동 저장 → [`day73_pseudo_loc_report.md`](day73_pseudo_loc_report.md)

## 5. 도구 공개판 (Day 78~82)

| 도구 | 내용 | 결과 |
|---|---|---|
| 마켓 소식 다이제스트 (Day 78) | 안드로이드·애플 개발자 공식 피드 수집 → QA 키워드 가중치 우선순위 → 디스코드 웹훅 | 최근 60일 38건 중 상위 10건 선정 → [`day78_digest_preview.md`](day78_digest_preview.md) |
| 다이제스트 스케줄러 (Day 79) | 발송 상태 저장으로 중복 제거, 매일 지정 시각 실행 | 두 번째 실행 새 소식 0건, 새 소식 2건 재현 시 정확히 2건만 발송 |
| KBO 선수 조회 (Day 80) | Wikidata 공개 데이터, 요청 간격 1초 제한, 동명이인 팀 → 생년월일 판별 | 판별·간격 테스트 17/17 통과, 실제 조회 요청 간격 최소 1.00초 |
| 메모리 측정 (Day 81) | ADB `dumpsys meminfo`(Heap Alloc 열) + `RssAnon+VmSwap`(구글 플레이 2027-02 기준 지표), 구간별 누수·백그라운드 해제 판정 | 설정 앱 실측: 6회 왕복은 힙 할당량이 계속 올라 "누수 의심", 15회 왕복에서 8회째부터 42MB 근처 평탄 → **"증가 후 안정(캐시)" 판정 규칙 추가** → [`day81_mem_settings_15r.md`](day81_mem_settings_15r.md) |
| FPS 측정 (Day 82) | SurfaceFlinger `--latency`·`--timestats`(게임·SurfaceView)·`gfxinfo`(일반 앱), 평균·하위 10%·하위 1% FPS를 레벨업 기준으로 구간별 판정 | Chrome 부하 페이지 입자 300 / 3,000개 PASS, 10,000개 **평균 24.8 / 하위 1% 15.2fps FAIL** → [`day82_fps_chrome.md`](day82_fps_chrome.md), 측정 가이드 [`day82_measure_guide.md`](day82_measure_guide.md) |

- 공개판 원칙: 사내 URL·시트·메신저·계정 제거, 공개 데이터와 공개 서비스만 사용, 외부 요청 최소 1초 간격, 비밀값은 `.env`
- KBO 공식 홈페이지는 robots.txt가 자동 수집을 금지해 사용하지 않았습니다
- 메모리·FPS는 LDPlayer(안드로이드 14) 에뮬레이터에서 공개 기본 앱(설정·Chrome)으로 실측했습니다. 에뮬레이터는 PC GPU로 그려 실기기와 절대값이 다르므로 도구·절차 검증과 상대 비교용입니다. `*_demo`·`*_report.md`는 판정 로직 검증용 합성 데이터(실측 아님)입니다
- 실측 중 발견: 에뮬레이터는 meminfo 요약의 힙 PSS가 0(Heap Alloc 열로 대체), SurfaceFlinger `--latency`가 0만 반환(`--timestats`로 대체), 웹 화면은 `gfxinfo`에 21프레임만 기록

## 6. CI·확률형 아이템 (Day 86~87)

- **CI (Day 86)**: [`.github/workflows/day86_api_regression.yml`](.github/workflows/day86_api_regression.yml), [`day86_ci_run.py`](day86_ci_run.py)
	- MariaDB 컨테이너 비밀번호를 실행마다 무작위로 만들어 `.env`에 기록 (저장소에 비밀값 없음)
	- 게이트: 서버 v3 DB 정합성·동시성 전부 통과 / 서버 v1 시딩 결함 탐지 유지 / 단위 테스트
	- GitHub 러너(2코어)에서는 동시성 결함이 회차마다 1~3건만 재현되고, 같은 request_id 응답 검증 테스트는 10회 중 0회 재현 → 결정적 결함(매번 탐지)과 동시성 결함(시딩 결함 D5·D6별 최대 10회 반복 누적 탐지)으로 게이트를 분리
- **확률형 아이템 (Day 87)**: [`day87_gacha_report.md`](day87_gacha_report.md), [`day87_gacha_qa_checklist.md`](day87_gacha_qa_checklist.md)
	- 공시 SSR 1.5%·천장 80회·10연차 SR 보장 규칙을 뽑기 로그만으로 판정. 확정 뽑기를 뺀 일반 뽑기만 카이제곱 검정
	- 결함 빌드(v1: SSR 가중치 1.2%, 천장 81회): 천장은 1,000회부터 FAIL, 기본 확률은 10,000회까지 PASS(99% 구간 1.015%~1.605%에 1.5% 포함) → 100,000회에서 FAIL

## 7. 문서 산출물

| 문서 | 내용 |
|---|---|
| [`day71_bug_reports_en.md`](day71_bug_reports_en.md) | 실측 결함 기반 영어 버그 리포트 3건 (Critical 1, Major 2) |
| [`day74_policy_onestore_unity.md`](day74_policy_onestore_unity.md) | Unity 런타임 취약점 CVE-2025-59489 대응 |
| [`day75_policy_apple_age.md`](day75_policy_apple_age.md) | 애플 연령 등급 개편(13+·16+·18+)과 연령 확인 |
| [`day76_policy_google_levelup.md`](day76_policy_google_levelup.md) | 구글 플레이 게임즈 레벨업·메모리 기준(2027-02) |
| [`day77_policy_16kb.md`](day77_policy_16kb.md) | 구글 플레이 16KB 메모리 페이지 크기 |
| [`day88_test_plan.md`](day88_test_plan.md) | 상점·재화 기능 리스크 기반 테스트 계획서 |

## 8. 기반 실습 (Day 1~58)

| 구간 | 내용 |
|---|---|
| Day 1~30 | 파이썬 기초, SQL(조회·조인·집계·제약조건), 통합 실습 |
| Day 31~37 | Docker·Compose·볼륨·네트워크, MariaDB 컨테이너, Selenium Grid 병렬 실행 |
| Day 38~45 | pytest 픽스처·마커·conftest, Allure 리포트(실패 스크린샷, Epic/Feature/Story), Page Object Pattern E2E |
| Day 46~55 | AWS EC2 배포, RDS 마이그레이션·백업, S3 + CloudFront로 Allure 리포트 배포 |
| Day 56~58 | Postman 컬렉션·Chai assertion·데이터 주도 테스트, Newman CLI·HTML 리포트 |

## 기술 스택

- 언어·테스트: Python 3.14, pytest, Allure, Selenium, requests
- API 테스트: Postman, Newman (htmlextra)
- 서버·DB: FastAPI, Uvicorn, MariaDB (Docker)
- 프록시·네트워크: Fiddler Classic, mitmproxy (애드온으로 변조·응답 조작·네트워크 조건 자동화)
- 성능 측정: ADB (dumpsys meminfo, SurfaceFlinger, gfxinfo), matplotlib
- 인프라·CI: Docker Compose, GitHub Actions, AWS (EC2, RDS, S3, CloudFront)

## 실행 방법 (Day 59~)

```bash
# 1) DB: MariaDB 10.6 컨테이너 (호스트 3307 포트), 접속 정보는 .env
docker run -d --name qa-mariadb -p 3307:3306 --env-file .env mariadb:10.6
py day59_apply_schema.py            # fc_qa_lab 스키마·시드 초기화

# 2) 패키지
py -m pip install -r requirements.txt

# 3) 예시
py day61_run_collection.py          # Postman 정상 흐름 (Newman)
py -m pytest day63_test_db_integrity.py day64_test_concurrency.py
py day67_tamper_test.py             # 프록시 요청 변조 (mitmproxy)
py day70_compare.py                 # 네트워크 매트릭스 v2/v3 비교
py day73_pseudo_loc.py              # 의사 현지화 점검
py day86_ci_run.py                  # CI 게이트 로컬 실행
py day87_gacha_verify.py            # 확률형 아이템 검증
py day81_mem_measure.py --demo      # 메모리 측정 (기기: --package <패키지> --label <구간>)
py day82_fps_measure.py --demo      # FPS 측정 (기기: --method sf --layer <레이어>)
```

- `.env` 필요 항목: `MYSQL_ROOT_PASSWORD`, `MARIADB_USER`, `MARIADB_PASSWORD`, `MYSQL_PORT`, `FC_DB_NAME` (선택: `DISCORD_WEBHOOK_URL`)
- 인증서·개인키(`day66_certs/`, `day66_mitm/`)는 실행 시 자동 생성되며 저장소에 포함하지 않습니다

## 서버 버전

| 버전 | 파일 | 변경 |
|---|---|---|
| v1 | `day60_server_v1.py` | 결함 7개 시딩 |
| v2 | `day68_server_v2.py` | 가격은 서버 값만 사용, 수량 하한 1 |
| v3 | `day70_server_v3.py` | Idempotency-Key 선점·결과 저장, 행 잠금 트랜잭션 |
