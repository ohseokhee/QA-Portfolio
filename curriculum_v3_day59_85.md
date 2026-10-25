# [Day 59~85] 게임 QA 포트폴리오 보완 커리큘럼 (v3)

> 목표: 지원 서류에서 드러난 공백(API 테스트, 프록시 툴, 네트워크 조건, 영어 리포트, 글로벌·현지화)을 실습 결과물로 메우고, 강점(마켓 정책 대응, 자체 제작 도구)을 공개 가능한 형태로 만든다.
>
> 번호: 기존 QA-Portfolio 저장소에 이어서 Day 59부터
>
> 이전 단계: Day 51~58은 v2(archive/curriculum_v2_day51_75.md) 기준 완료. v2의 남은 Phase 6~9는 이 문서로 대체

---

## v2 잔여 항목 처리

| v2 항목 | 처리 | 사유 |
|---|---|---|
| Postman 기초·검증 스크립트·Newman (Day 56~58) | 완료, Phase A에서 재사용 | 기초는 끝났으므로 게임 상점 API에 적용만 함 |
| Appium (Day 59~62) | 제외 | Unity 등 엔진 게임은 화면 전체를 한 장으로 그려서 Appium이 게임 내 버튼을 요소로 인식하지 못함. 게임 UI 자동화는 이미 OpenCV 이미지 인식으로 해본 경험이 더 직접적. 카카오·크림이 목표에서 빠진 것도 이유 |
| Locust 부하 테스트 (Day 63~66) | 제외 | 목표 3사(스마일게이트·EA·넷마블) 게임 QA 요구사항과 거리가 있음. 서버 부하는 보통 서버·인프라 조직 담당 |
| GitHub Actions·Jenkins (Day 67~73) | 보류 | 필요하면 Phase G 뒤에 1일 추가 (API 테스트 자동 실행 워크플로우) |
| README·회고 (Day 74~75) | Phase G로 흡수 | - |

---

## 전체 구조

| Phase | Day | 주제 | 메우는 공백 | 주 타깃 |
|---|---|---|---|---|
| A | 59~64 | 모의 게임 서버 + API 테스트 | API 실무 경험 없음 | 스마일게이트, 넷마블 |
| B | 65~68 | 프록시 툴(Fiddler) | 클라이언트-서버 통신 검증 | 스마일게이트 |
| C | 69~71 | 네트워크 조건 + 영어 버그 리포트 | 네트워크 품질, 영어 리포팅 | EA |
| D | 72~73 | 현지화 검수(LQA) | 글로벌 서비스 경험 없음 | 스마일게이트, EA |
| E | 74~77 | 마켓 정책 대응 아카이브 | 강점의 가시화 | 전체 |
| F | 78~82 | 사내 도구 공개판 | 회사 코드 비공개 문제 | 전체 |
| G | 83~85 | 정리·면접 대비 | - | 전체 |
| H | 89~91 | 현지화 검수 확장 | 글로벌 서비스 경험 없음 (자동 점검으로 보강) | 스마일게이트, EA |
| 병행 | - | ISTQB CTAL | 상위 자격 | 전체 |

---

## 진행 방식

1. PyCharm 클로드: `Day ## 진행해줘` 입력 → 코드 작성·실행·커밋·push와 인계 파일 `handoff/day##_handoff.md` 생성까지 자동 (세부 절차는 CLAUDE.md)
2. 채팅 세션: 인계 파일을 첨부하면 노션 기록 `day##_notion.md` 작성·제출 (실제 로그 기준으로만)
3. [문서] 표시 Day: 코드 없이 이 세션에서 바로 작성. 노션 형식의 '코드'와 '최종 결과값' 칸은 '산출물'과 '출처'로 대체

---

## Phase A — 모의 게임 서버 + API 테스트 (Day 59~64)

배경: FC 온라인 구조로 만든 fc_qa_lab(MariaDB)을 그대로 DB로 쓴다. 상점·재화 API는 퍼블리싱·플랫폼 QA 면접에서 자주 묻는 결제·재화 영역과 겹친다.

### Day 59 — API 명세와 테스트 설계
- 엔드포인트 5개: 로그인(토큰 발급), 재화 조회, 재화 지급(운영툴 역할), 상점 구매, 인벤토리 조회
- fc_qa_lab에 재화·구매 이력 테이블 추가
- 동등 분할, 경계값 분석으로 테스트 케이스 목록 작성
	- 동등 분할: 같은 결과가 나올 입력끼리 묶어 대표값만 테스트하는 기법
	- 경계값 분석: 0, 최대값처럼 결함이 몰리는 경계 근처를 집중 테스트하는 기법
- 파일: `day59_api_spec.md`, `day59_schema.sql`

### Day 60 — 서버 v1 구현 + 결함 시딩
- FastAPI로 서버 구현
	- FastAPI: 파이썬으로 API 서버를 빠르게 만드는 프레임워크
- PyCharm 클로드가 결함 5~7개를 일부러 심고 목록을 `sealed/day60_seeded_defects.md`에 봉인 (Day 64 전까지 열지 않기, 저장소에 올리지 않음)
	- 결함 시딩: 일부러 결함을 심어 두고 테스트가 몇 개를 잡는지로 테스트 품질을 재는 기법 (ISTQB 용어)
- 파일: `day60_server_v1.py`

### Day 61 — Postman 정상 흐름 컬렉션 (Day 56~57 기초 적용)
- 환경 변수 구성, 로그인 응답의 토큰을 자동 저장해 다음 요청에 사용 (요청 체이닝)
- 상태 코드, 응답 구조, 응답 시간 검증 스크립트
- 파일: `day61_collection.json`

### Day 62 — 부정 케이스 (Day 57 데이터 주도 테스트 적용)
- 수량 0·음수·최대값 초과, 잔액 부족, 존재하지 않는 아이템, 만료 토큰, 다른 계정 토큰으로 요청(권한 검증)
- 케이스 값은 CSV로 분리해 컬렉션 한 번 실행으로 전부 돌림
	- 데이터 주도 테스트: 테스트 절차는 하나로 두고 입력값만 파일에서 바꿔 가며 반복 실행하는 방식
- 파일: `day62_negative_collection.json`, `day62_negative_cases.csv`

### Day 63 — DB 정합성 자동 검증
- pytest + requests로 API 호출 후 SQL로 실제 값 대조 (응답 잔액 = DB 잔액, 차감액 합계 = 구매 이력 합계)
- 결과는 Allure 리포트로 출력 (기존 conftest.py, pytest.ini 재사용)
- 파일: `day63_test_db_integrity.py`

### Day 64 — 동시 요청과 리포트
- 같은 구매 요청을 동시에 N회 전송 → 이중 차감·중복 지급 탐지
	- 멱등성: 같은 요청을 여러 번 보내도 결과가 한 번 보낸 것과 같아야 하는 성질
- Newman으로 Day 61~62 컬렉션 일괄 실행 + HTML 리포트 (Day 58 방식 재사용)
- 봉인 목록 개봉 → 결함 탐지율 계산 (포트폴리오 수치로 사용)
- 파일: `day64_test_concurrency.py`, `day64_newman_report.html`

---

## Phase B — 프록시 툴 (Day 65~68)

도구: Fiddler Classic (윈도우 무료). Charles는 개념 비교만.
원칙: 상용 게임 트래픽 변조는 약관 위반 소지가 있으므로 모의 서버에서만 진행.

### Day 65 — 캡처 환경
- 서버가 간단한 상점 웹 페이지 제공 → LDPlayer 브라우저로 접속
- LDPlayer Wi-Fi 프록시를 PC의 Fiddler로 지정해 요청·응답 캡처
- 파일: `day65_shop_client.html`, `day65_proxy_setup.md`

### Day 66 — HTTPS 복호화
- 서버를 HTTPS로 전환, Fiddler 인증서를 PC와 LDPlayer에 설치
- 정리: 안드로이드 7 이상에서 앱이 사용자 설치 인증서를 기본으로 신뢰하지 않는 이유 (실무에서 QA 빌드에 별도 설정을 요청하는 배경)

### Day 67 — 요청 변조
- Breakpoint로 가격·수량·아이템 ID를 바꿔 전송 → 서버가 클라이언트 값을 그대로 믿는 결함 확인
	- Breakpoint: 요청을 중간에 멈춰 세우고 값을 고친 뒤 보내는 기능
- 파일: `day67_tamper_cases.md`

### Day 68 — 응답 조작 + 수정 검증
- AutoResponder로 500 오류, 점검 중, 지연 응답을 흉내 → 클라이언트 처리 확인
	- AutoResponder: 실제 서버 대신 미리 정해 둔 응답을 돌려주는 기능
- 서버 v2: 가격·수량을 서버에서 검증하도록 수정 → Day 61~64 컬렉션 회귀 실행
- 파일: `day68_server_v2.py`

---

## Phase C — 네트워크 조건 + 영어 리포트 (Day 69~71)

### Day 69 — Clumsy 네트워크 조건 테스트
- 지연, 패킷 손실, 순서 뒤바뀜, 일시 끊김 조건별로 구매 시도
	- Clumsy: 윈도우에서 네트워크 불량 상태를 인위로 만드는 도구
- 타임아웃 후 재시도 시 중복 구매가 생기는지 확인, 조건별 결과 매트릭스 작성
- 파일: `day69_network_matrix.md`, `day69_test_retry.py`

### Day 70 — 재시도 안전 처리 검증
- 서버 v3: 요청마다 고유 키(Idempotency-Key)를 받아 중복 처리 차단
- Day 69 매트릭스 재실행 → 수정 전후 비교
- 파일: `day70_server_v3.py`

### Day 71 — [문서] 영어 버그 리포트 3건
- Phase A~C에서 실제로 찾은 결함 기준
- 구조: Summary / Environment / Steps to Reproduce / Expected / Actual / Severity·Priority / Root Cause / Attachments
- 파일: `day71_bug_reports_en.md`

---

## Phase D — 현지화 검수 LQA (Day 72~73)

### Day 72 — [문서] 에픽세븐 다국어 관찰 기록
- 언어 설정을 바꿔 가며 텍스트 넘침·잘림, 폰트 대체, 날짜·숫자 형식, 이미지 속 미번역 텍스트 관찰 (스크린샷 첨부)
- 결과물: LQA 체크리스트 1장 + 관찰 기록
	- LQA: 번역문이 게임 화면과 문맥에 맞게 들어갔는지 검수하는 작업
- 파일: `day72_lqa_checklist.md`

### Day 73 — 의사 현지화 자동 점검
- 모의 상점 페이지 문자열을 30~40% 늘리고 특수 문자로 바꾼 버전 생성 → Selenium으로 요소 넘침 자동 탐지 + 스크린샷
	- 의사 현지화: 번역 전에 가짜로 긴 문자열을 넣어 UI가 버티는지 미리 보는 기법
- 파일: `day73_pseudo_loc.py`

---

## Phase E — [문서] 마켓 정책 대응 아카이브 (Day 74~77)

형식: 변경 내용 → 적용 일정 → 게임에 미치는 영향 → QA 체크리스트 → 출처
원칙: 사내 수치, 빌드 정보, 내부 일정은 제외

- Day 74 — 원스토어 Unity 보안 취약점(CVE-2025-59489) 대응 → `day74_policy_onestore_unity.md`
- Day 75 — 애플 연령 등급 개편과 연령 확인 대응 → `day75_policy_apple_age.md`
- Day 76 — 구글 플레이 레벨업과 메모리 기준 → `day76_policy_google_levelup.md`
- Day 77 — (선택) 구글 플레이 16KB 페이지 크기 대응 → `day77_policy_16kb.md`

---

## Phase F — 사내 도구 공개판 (Day 78~82)

원칙: 사내 URL, 시트 ID, 패키지명, 사내 메신저 연동 제거. 공개 데이터와 공개 서비스만 사용.

### Day 78~79 — 마켓 소식 다이제스트
- 안드로이드·애플 개발자 공식 소식 수집 → 키워드 우선순위 정렬 → 디스코드 웹훅 발송
	- 웹훅: 정해진 주소로 메시지를 자동 전송하는 방식
- 파일: `day78_market_digest.py`, `day79_digest_scheduler.py`

### Day 80 — KBO 선수 조회 파이썬판
- 요청 간격 제한, 동명이인 판별(팀 → 생년월일) + 판별 로직 테스트 케이스
- 파일: `day80_kbo_lookup.py`

### Day 81~82 — 메모리·FPS 측정 범용판
- ADB로 메모리(dumpsys meminfo)와 프레임(gfxinfo) 측정 → CSV·그래프, 공개 앱으로 데모
- 측정 가이드에 구글 플레이 메모리 기준과의 연결 설명
- 파일: `day81_mem_measure.py`, `day82_fps_measure.py`

---

## Phase G — 정리 (Day 83~85)

- Day 83 — GitHub README: 프로젝트별 문제 → 해결 → 결과(수치) 한 화면 요약
- Day 84 — [문서] 지원서 포트폴리오에 신규 사례 반영 (회사별 제시 순서 포함)
- Day 85 — [문서] 면접 Q&A 20문항: "왜 이 방식을 택했나" 중심

---

## 추가 — 실무 보강 (Day 86~88)

목표 3사 공고에서 자주 보이는 요구(테스트 자동 실행, 확률형 아이템 검증, 테스트 계획 수립)를 기존 실습 결과 위에 덧붙인다.

- Day 86 — GitHub Actions로 push마다 API 회귀 테스트 자동 실행 (v3 전부 통과 + v1 시딩 결함 탐지 유지 확인)
	- 파일: `.github/workflows/day86_api_regression.yml`, `day86_ci_run.py`
- Day 87 — 확률형 아이템 공시 확률 검증: 뽑기 로그로 기본 확률(카이제곱 적합도 검정)·천장·10연차 보장 판정, 표본 수 설계
	- 파일: `day87_gacha.py`, `day87_gacha_verify.py`, `day87_test_gacha.py`, `day87_gacha_qa_checklist.md`
- Day 88 — [문서] 상점·재화 기능 테스트 계획서: 리스크 기반 우선순위, 진입·종료 기준, Day 59~87 결과를 근거로
	- 파일: `day88_test_plan.md`

## Phase H — 현지화 검수 확장 (Day 89~91)

배경: Day 72 LQA 체크리스트(LQA-01~09)와 Day 73 의사 현지화를 실제 리소스 파일, 로캘 형식, 공개 스토어 등록정보 점검으로 넓힌다. 사용자가 할 일 없이 끝까지 자동으로 진행되는 범위만 다룬다. 실무 LQA 경험이 아니라 개인 실습으로 표기한다.

### Day 89 — 다국어 문자열 리소스 LQA 자동 점검
- 모의 상점 화면 문자열(명세 1.4 아이템 이름과 상태 문구, Day 73 변환 대상)을 기준어 한국어 + en, ja, zh-TW, th, es 리소스 JSON으로 구성하고 용어집 CSV 작성
	- 번역문은 연습용으로 만든 데이터. 리포트 머리에 명시
- 생성 스크립트가 고정 seed로 LQA 결함 10~12개를 주입, 정답표는 `sealed/day89_answer_key.json`
- 점검 규칙 (각 규칙을 LQA-01~09에 매핑)
	1. 키 누락과 문자열 ID 노출
	2. 미번역 (원문과 같음, 허용 목록 FC·BP 등 제외)
	3. 자리표시자와 태그 불일치 (`{count}`, `{item}`, Unity TextMeshPro 리치 텍스트 `<color>`, `<b>`)
	4. 숫자와 % 불일치 (원문 수치와 번역 수치 대조, Day 72 "수치와 효과는 데이터와 대조")
	5. 용어집 위반 (정해진 번역 누락, 금지 번역 사용)
	6. 길이 예산 초과 (키별 최대 폭, 전각 문자 2칸, 태국어 결합 문자 0칸으로 추정)
	7. 문자 체계 혼입 (ja에 한글, zh-TW에 간체 빈출 글자, th에 번역 없이 라틴 문자만)
	8. 문장 부호와 공백 (전각과 반각 혼용, 스페인어 ¿ ¡ 누락, 이중 공백, 앞뒤 공백)
	9. 같은 원문 다른 번역 (일관성)
- 결과: 언어 × 규칙 매트릭스 리포트(md, csv), 정답표 대조 정밀도·재현율, 규칙별 pytest
	- 정밀도: 잡아낸 것 중 실제 결함 비율 / 재현율: 실제 결함 중 잡아낸 비율
- 파일: `day89_make_strings.py`, `day89_lqa_lint.py`, `day89_test_lqa_lint.py`, `day89_strings/`, `day89_glossary.csv`, `day89_lqa_report.md`

### Day 90 — 로캘 형식, 시간대, 폰트 글리프 점검
- Babel(CLDR)로 ko_KR, en_US, ja_JP, zh_TW, th_TH, es_ES, de_DE의 숫자, 통화, 날짜 표기 기준표 생성 → Day 89 문자열과 상점 화면의 하드코딩 형식(`1,000`, `2026-10-25 05:00`) 탐지
- zoneinfo(Windows는 `tzdata` 패키지 필요)로 KST 기준 이벤트 일정(일일 초기화 05:00, 이벤트 종료 시각)을 지역 시간으로 변환하고 서머타임 경계 검증
	- 2026-10-25 유럽 서머타임 종료, 2026-11-01 미국 서머타임 종료: 같은 KST 05:00 초기화가 현지 시각으로 1시간 바뀌는지, 현지 시각 기준 일정에서 중복되거나 없는 시각(fold) 처리
- fontTools로 Windows 기본 폰트(맑은 고딕, Yu Gothic 또는 Meiryo, Microsoft JhengHei, Leelawadee UI, Segoe UI)의 글리프 보유 여부를 언어별 문자열로 점검 → 빠진 글자(두부 □) 목록과 폴백 폰트 필요 여부
	- 폰트는 파일명 대신 패밀리 이름으로 찾고 읽기만 함 (복사·커밋 금지)
	- pytest는 fontTools FontBuilder로 만든 작은 테스트 폰트로 (기기와 OS에 상관없이 재현)
- 파일: `day90_locale_check.py`, `day90_test_locale_check.py`, `day90_locale_report.md`

### Day 91 — App Store 공개 등록정보 다국어 점검
- Apple 공개 iTunes Search/Lookup API로 게임 3종의 국가별 스토어(kr, us, jp, tw, th, es) 등록정보 수집
	- 대상: 에픽세븐(스마일게이트, Day 72와 연결), EA SPORTS FC Mobile(EA), 세븐나이츠 리버스(넷마블). 검색으로 찾은 trackId를 리포트에 기록
- 점검: 국가별 출시 여부, 버전과 출시일 차이(단계 출시), 릴리스 노트 문자 체계와 스토어 언어 일치, 지원 언어 목록(languageCodesISO2A), 연령 등급(contentAdvisoryRating, Day 75 연결), 가격 표기(formattedPrice)와 통화, 최소 OS
- 요청 간격 3초 이상, 응답 JSON은 `day91_fixtures/`에 저장, 판정 로직 pytest는 저장본으로
- 구글 플레이는 공개 API가 없어 제외 (페이지 크롤링 하지 않음)
- 파일: `day91_store_listing_check.py`, `day91_test_store_listing.py`, `day91_fixtures/`, `day91_store_report.md`

---

## 병행 — ISTQB CTAL

- KSTQB 공식 홈페이지에서 시험 일정과 응시 조건 확인
- 모듈 후보
	- CTAL-TA (테스트 분석가): 테스트 설계 기법 중심. 현재 TC 설계 업무와 가장 가까움
	- CTAL-TTA (기술 테스트 분석가): 성능·보안·유지보수성 등 기술 품질 중심
- 주 1회, 실라버스 챕터를 Phase A~D 실습에 매핑해 노션에 정리

---

## 기존 규칙 유지

- 파일명: 소문자 `day##_*.py`
- 커밋 메시지: `Day ## 실습 : [한글 핵심 내용]` ("프로젝트" 대신 "실습")
- 커밋: 일차별 분리
- 노션 기록: 실제 실행 로그 기준으로만 작성
- 패키지 설치: `py -m pip install [패키지명]`
- 실행: `py -m pytest`

---

## PyCharm 클로드 사용법

- 일차 진행: `Day ## 진행해줘` 또는 `다음 일차 진행해줘`
- [문서] Day 커밋: 채팅에서 받은 md 파일을 프로젝트에 넣고 `Day ## 커밋해줘`
- 수동 작업이 섞인 Day(65~70)는 중간에 멈추고 `handoff/day##_manual.md` 절차를 안내함 → 끝나면 결과를 알려주면 이어서 진행
