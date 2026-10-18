# QA-Portfolio 프로젝트 규칙

## 커리큘럼 현황
- 완료: Day 1~59
- 다음: Day 60 (서버 v1 구현 + 결함 시딩)
- 커리큘럼 파일: `curriculum_v3_day59_85.md` (이 파일만 참조)
- `archive/` 폴더는 지난 커리큘럼 보관용. 읽거나 참조하지 말 것
- 최초 1회: 루트에 `curriculum_v2_day51_75.md`가 있으면 `git mv`로 `archive/`에 옮기고 Day 59 커밋에 포함

## 환경
- OS: Windows 11
- Python: 3.14.2
- IDE: PyCharm 2025.3.1.1
- Python 실행: `py` (python 아님)
- pytest 실행: `py -m pytest`
- 패키지 설치: `py -m pip install [패키지명]`
- Docker: Docker Desktop
- 콘솔 한글 깨짐 방지: 스크립트 첫머리에 `sys.stdout.reconfigure(encoding="utf-8")`
- DB: fc_qa_lab (MariaDB). 접속 정보는 `.env`에서 읽고 코드에 하드코딩 금지

---

## 딸깍 실행 규칙

### 트리거
- "Day ## 진행해줘", "다음 일차 진행해줘", "다음"
- "다음"류 요청은 위 '커리큘럼 현황'의 다음 일차를 진행

### 자동 진행 순서 (확인 없이 끝까지)
1. `curriculum_v3_day59_85.md`에서 해당 Day 범위 확인. 범위 밖 기능 추가 금지
2. 필요한 패키지를 먼저 `requirements.txt`에 적고 `py -m pip install -r requirements.txt`로 설치 (개별 `pip install` 대신)
3. 코드 작성 → 실행 → 실패하면 원인 수정 후 재실행
4. 최종 성공 실행의 콘솔 로그 확보
5. 인계 파일 `handoff/day##_handoff.md` 작성 (아래 형식)
6. 이 파일의 '커리큘럼 현황' 갱신 (완료 / 다음)
7. git add → commit → push (일차당 1커밋)
8. 사용자에게 3줄 보고: 커밋 메시지, 생성 파일, 인계 파일 경로

### 멈추고 확인받는 경우
- 사용자가 직접 해야 하는 GUI 작업이 있는 Day (아래 '수동 작업이 섞인 Day')
- 같은 오류가 3회 반복될 때 (오류 원문과 시도한 방법을 보고)
- 필요한 외부 값이 없을 때: `adb devices`에 기기 없음, `.env`에 웹훅 URL 없음 등
- 파일 삭제, 새 Docker 이미지 pull
- 커리큘럼 범위를 벗어나는 변경이 필요해 보일 때

### 수동 작업이 섞인 Day (Day 65~70)
- Fiddler, Clumsy, LDPlayer 조작은 사용자가 직접 수행
- 순서
	1. 자동화할 수 있는 준비(서버 기동, 클라이언트 페이지, 스크립트)를 먼저 끝냄
	2. `handoff/day##_manual.md`에 번호 매긴 수동 절차 작성 (클릭할 메뉴 이름까지 구체적으로)
	3. 멈추고 "수동 절차 완료 후 결과를 알려 달라"고 요청
	4. 사용자 보고를 받은 뒤 자동 진행 5~8단계 수행
- 사용자 보고 내용은 인계 파일 '수동 확인 결과'에 그대로 기록

### [문서] Day (Day 71, 72, 74~77, 84, 85)
- 이 프로젝트에서 작성하지 않음 (채팅 세션에서 작성)
- 사용자가 md 파일을 넣고 "Day ## 커밋해줘"라고 하면 해당 파일만 커밋·push하고 커리큘럼 현황 갱신

---

## 인계 파일 형식 (`handoff/day##_handoff.md`)

- 용도: 사용자가 채팅 세션에 첨부 → 채팅 세션이 노션 기록 작성. 이 프로젝트에서는 노션 기록을 작성하지 않음
- `handoff/`는 .gitignore에 등록
- 콘솔 출력과 오류 메시지는 가공·요약 없이 원문 그대로
- 콘솔 출력이 200줄을 넘으면 전체를 `handoff/day##_console.txt`로 저장하고, 인계 파일에는 결과 집계 구간만 원문 발췌

~~~markdown
# Day ## 인계

- 커밋 메시지: Day ## 실습 : [내용]
- 노션 제목: [커밋 메시지에서 "Day ## 실습 : "를 뺀 부분]
- 생성·수정 파일: [목록]
- 실행 명령: [실제 실행한 명령]

## 코드 동작 순서
1. [3~5줄]

## 핵심 개념
1. [용어]: [한 줄 설명] (이번 Day에 실제로 쓴 것 3~5개)

## 겪은 오류와 해결
1. [오류 원문 1줄] / 원인: [ ] / 해결: [ ] (실제로 발생한 것만, 없으면 "없음")

## 수동 확인 결과
[해당 Day만. 사용자 보고 원문]

## 콘솔 출력 (최종 성공 실행, 원문)
```
[원문]
```

## 남은 이슈
[없으면 "없음"]
~~~

---

## Phase별 특수 규칙

### Phase A (Day 59~64) 결함 시딩
- Day 60: 결함 5~7개를 심고 목록은 `sealed/day60_seeded_defects.md`에 저장. `sealed/`는 .gitignore에 등록
- Day 60 보고와 인계 파일에는 "N개 시딩 완료"만 쓰고 결함 내용은 밝히지 않음
- Day 61~63: 테스트는 `day59_api_spec.md`만 보고 설계 (명세 기반 블랙박스). `day60_server_v1.py` 소스와 `sealed/`는 읽지 않음. 서버 실행은 허용
- Day 64: 봉인 해제 → 탐지/미탐지 대조표와 탐지율을 인계 파일에 기록. 봉인 파일은 `day64_seeded_defects.md`로 옮겨 커밋

### Phase B·C (Day 65~70)
- 트래픽 캡처·변조는 로컬 모의 서버만 대상. 상용 게임과 외부 서비스 대상 금지
- HTTPS 요청 시 `verify=False`, `--insecure` 같은 검증 끄기 옵션 금지. 자체 서명 인증서는 인증서 파일 경로를 `verify`에 지정

### Phase F (Day 78~82)
- 사내 URL, 시트 ID, 사내 패키지명, 사내 메신저, 사내 계정 정보 사용 금지. 공개 데이터와 공개 서비스만 사용
- 외부 사이트 요청은 최소 1초 간격
- 웹훅 URL 등 비밀값은 `.env`

---

## 파일 규칙
- 파일명: 소문자 `day##_*` (예: `day60_server_v1.py`)
- 파일명에 공백 금지 (언더스코어 사용)

## Git 커밋 규칙
- 커밋 메시지: `Day ## 실습 : [한글 핵심 내용]`
- "프로젝트" 사용 금지 → 무조건 "실습"
- 각 일차별 따로따로 커밋 (절대 묶지 말 것)
- Git 문제 발생 시 간단한 방법부터 (rebase 지양, 윈도우 한글 인코딩 문제 있음)
- 예시:
  ```
  git add day60_server_v1.py requirements.txt CLAUDE.md
  git commit -m "Day 60 실습 : FastAPI 모의 게임 서버 구현 및 결함 시딩"
  git push
  ```

---

## 안전 규칙

- 이 프로젝트는 auto 모드(권한 자동 판단) 사용 전제. 아래 목록은 작업 지침이며, 실제 허용 여부는 Claude Code 권한 모드가 결정
- auto 모드에서 작업이 차단되면 다른 명령으로 우회하지 말고, 차단된 명령과 사유를 사용자에게 보고

### 금지 (사용자 명시 요청 없이는 실행 불가)
- `aws` 명령 전체 (v3에서는 사용하지 않음)
- `docker pull` (새 이미지)
- `docker compose down -v` (볼륨 삭제 = fc_qa_lab 데이터 삭제)
- 프로젝트 폴더 밖 파일 수정·삭제
- `.env`, `sealed/` 내용 출력 또는 커밋

### 자동 허용
- 파일 읽기/쓰기, `py` 실행, `py -m pytest`
- `py -m pip install`, `npm install` (해당 Day에 필요한 것만)
- 기존 compose 파일로 `docker compose up -d` / `docker compose down` (-v 없이)
- git add, commit, push (딸깍 실행 범위 안에서)
- git status, git log, docker ps, adb devices, dir, type

### 확인 필요
- 파일 삭제
- 위 '멈추고 확인받는 경우' 전체

---

## 코드 제공 방식
1. 사용자 요구사항 외 임의 수정 절대 금지
2. 사용자 우려사항 반드시 반영
3. 로그는 실제 실행 결과만 사용 (예상 출력 작성 금지)

## 목표 공고
- 스마일게이트 게임 퍼블리싱 QA (2026-10 지원 완료)
- EA 코리아, 넷마블 (넷마블 계열 IGS 제외)
- 보유 자격: ISTQB FL + Game Testing + AI Testing, SQLD
