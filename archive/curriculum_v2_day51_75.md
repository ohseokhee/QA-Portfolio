# QA 커리큘럼 재개편안 (Day 51~75)

> 기준: 목표 공고 6개(111%, 넷마블, EA, 카카오, NHN커머스, 크림) 요구/우대사항 직결 항목만 유지
> 보유 자격: ISTQB FL / Game Testing / AI Testing → 자격증 트랙 제외
> 현재 위치: Day 58 완료 (Postman/Newman API 테스트 - Phase 5 마무리). 다음: Day 59 (Appium 서버 + 에뮬레이터 연결)

---

## 스킵 항목 및 사유

| 기존 항목 | 사유 |
|---|---|
| Terraform IaC (기존 Day 55-57) | 6개 공고 미언급. DevOps 전향용 스킬 |
| Phase 5 Kubernetes 전체 (기존 Day 61-75) | QA 직군 오버스펙. 15일 투자 대비 서류 기여 없음 |
| Lighthouse CI (기존 Day 76-78) | 웹 프론트 성능 지표. 공고 요구와 거리 있음 |
| Datadog APM (기존 Day 83-86) | 운영/SRE 영역. QA 공고 무관 |

---

## 재개편 커리큘럼

### Phase 4 마무리: AWS (Day 51~55)

- **Day 51-53: S3 + CloudFront Allure Report 호스팅**
  - 테스트 리포트를 팀 공유 가능한 정적 사이트로 배포
  - 공고 연결: 넷마블 "품질 지표 시각화·공유", QA 리포팅 체계 증빙

- **Day 54-55: Phase 4 통합 검증**
  - EC2 + RDS + Grid + S3 리포트 전체 플로우 1회 완주
  - 포트폴리오 아키텍처 다이어그램 작성

### Phase 5 (신규): API 테스트 - Postman (Day 56~58)

- **Day 56: Postman 기초 + 공개 API 테스트 (컬렉션, 환경변수)**
- **Day 57: 검증 스크립트 (Tests 탭, Chai assertion) + 데이터 주도 테스트**
- **Day 58: Newman CLI 실행 + 리포트 생성 (자동화 연계 준비)**
  - 공고 연결: 카카오 우대 "Postman", 서버/API 레벨 QA 커버

### Phase 6 (신규): 모바일 자동화 - Appium (Day 59~62)

- **Day 59: Appium 서버 + 에뮬레이터 연결 (기존 LDPlayer 경험 재활용)**
- **Day 60: UiAutomator2 요소 탐색 + 기본 시나리오**
- **Day 61: Page Object Pattern 적용 모바일 테스트**
- **Day 62: pytest + Allure 통합 (기존 Phase 3 자산 재사용)**
  - 공고 연결: 카카오 우대 "Appium", 크림 "APP(Android/iOS) QA"
  - 이력서 효과: LDPlayer/ADB 자체 구축 경험 → 표준 프레임워크 검증으로 승격

### Phase 7: 부하 테스트 - Locust (Day 63~66)

- **Day 63: Locust 기초 + 단일 시나리오 부하**
- **Day 64: 사용자 시나리오 모델링 (로그인→조회→구매 플로우)**
- **Day 65: 분산 부하 + 결과 지표 분석 (RPS, 응답시간, 실패율)**
- **Day 66: 부하 테스트 리포트 작성 (통계 역량과 결합)**
  - 공고 연결: 111% "비기능 테스트", 게임 라이브 서버 부하 검증 실무 언어

### Phase 8: CI/CD 파이프라인 (Day 67~73)

- **Day 67-68: GitHub Actions - pytest 자동 실행 워크플로우**
- **Day 69-70: GitHub Actions - Allure Report 자동 생성 + GitHub Pages 배포**
- **Day 71-72: Jenkins 파이프라인 구축 (Docker 기반)**
- **Day 73: Jenkins + Selenium Grid + Allure 통합**
  - 공고 연결: 넷마블 "테스트 자동화 활용", 카카오 "자동화 설계 경험"
  - 포트폴리오 임팩트 최대 구간: 커밋 → 테스트 → 리포트 전자동 파이프라인

### Phase 9: 포트폴리오 완성 (Day 74~75)

- **Day 74: GitHub README 재정리 (공고 용어 기준 3개 핵심 프로젝트 압축)**
  - ① 통계 기반 밸런스 검증 파이프라인 → "테스트 설계 기법"
  - ② 멀티 에뮬레이터 자동화 + Appium → "모바일 UI 자동화 프레임워크"
  - ③ CI/CD 통합 파이프라인 → "테스트 자동화 인프라 구축"
- **Day 75: 전체 회고 + 공고별 자소서 소재 매핑표 작성**

---

## 기존 규칙 유지

- 파일명: 소문자 `day##_*.py`
- 커밋 메시지: `Day ## 실습 : [한글 핵심 내용]`
- 커밋: 일차별 분리
- 노션 템플릿: 실제 실행 로그 기준 최종 갱신
- 패키지 설치: `py -m pip install [패키지명]`
- 실행: `py -m pytest`

---

## 요약

- 기존 100일 → **75일 완주** (25일 단축)
- 스킵: K8s, Terraform, Lighthouse, Datadog
- 신규 추가: Postman(3일), Appium(4일) — 카카오/크림 우대 직결
- 유지: S3 리포트 호스팅, Locust, Jenkins/GitHub Actions
