# Day 91 App Store 공개 등록정보 다국어 점검 리포트

> Apple 공개 iTunes Search/Lookup API 응답(day91_fixtures/)에서 관찰한 사실만 기록. 품질 평가는 하지 않음. 구글 플레이는 공개 API가 없어 제외

## Epic Seven

- trackId: 1322399438

| 국가 | 앱 이름 | 버전 | 버전 출시일 | 노트 문자 | 스토어 언어 지원 | 지원 언어 수 | 연령 | 가격 | 통화 | 최소 OS |
|---|---|---|---|---|---|---|---|---|---|---|
| kr | 에픽세븐 | 1.0.1023 | 2026-10-29 | Hangul | O | 10 | 12+ | 무료 | KRW | 15.0 |
| us | Epic Seven | 1.0.1023 | 2026-10-29 | Latin | O | 10 | 12+ | Free | USD | 15.0 |
| jp | エピックセブン | 1.0.1023 | 2026-10-29 | Japanese | O | 10 | 12+ | 無料 | JPY | 15.0 |
| tw | 第七史詩 | 1.0.1023 | 2026-10-29 | Han | O | 10 | 12+ | 免費 | TWD | 15.0 |
| th | Epic Seven | 1.0.1023 | 2026-10-29 | Latin | O | 10 | 12+ | Free | THB | 15.0 |
| es | Epic Seven | 1.0.1023 | 2026-10-29 | Latin | O | 10 | 12+ | Gratis | EUR | 15.0 |

### 관찰

- [C3] th 릴리스 노트 문자 체계 Latin (스토어 언어 Thai)

## EA SPORTS FC Mobile

- trackId: 1094930513

| 국가 | 앱 이름 | 버전 | 버전 출시일 | 노트 문자 | 스토어 언어 지원 | 지원 언어 수 | 연령 | 가격 | 통화 | 최소 OS |
|---|---|---|---|---|---|---|---|---|---|---|
| kr | (조회 결과 없음) | | | | | | | | | |
| us | EA SPORTS FC Soccer Mobile 27 | 28.0.01 | 2026-09-24 | Latin | O | 23 | 4+ | Free | USD | 15.0 |
| jp | EA SPORTS FC™ サッカー Mobile 27 | 28.0.01 | 2026-09-24 | Japanese | O | 23 | 4+ | 無料 | JPY | 15.0 |
| tw | EA SPORTS FC™ 足球 Mobile 27 | 28.0.01 | 2026-09-24 | Han | O | 23 | 4+ | 免費 | TWD | 15.0 |
| th | EA SPORTS FC™ Football Mobile | 28.0.01 | 2026-09-24 | Latin | O | 23 | 4+ | Free | THB | 15.0 |
| es | EA SPORTS FC™ Fútbol Mobile 27 | 28.0.01 | 2026-09-24 | Latin | O | 23 | 4+ | Gratis | EUR | 15.0 |

### 관찰

- [C1] 미출시(조회 결과 없음): kr
- [C3] th 릴리스 노트 문자 체계 Latin (스토어 언어 Thai)

## 세븐나이츠 리버스

- trackId: 6479595079

| 국가 | 앱 이름 | 버전 | 버전 출시일 | 노트 문자 | 스토어 언어 지원 | 지원 언어 수 | 연령 | 가격 | 통화 | 최소 OS |
|---|---|---|---|---|---|---|---|---|---|---|
| kr | 세븐나이츠 리버스 | 1.30.03 | 2026-10-28 | Hangul | O | 7 | 12+ | 무료 | KRW | 15.0 |
| us | Seven Knights Re:BIRTH | 1.30.03 | 2026-10-28 | Latin | O | 7 | 12+ | Free | USD | 15.0 |
| jp | セブンナイツ Re:BIRTH（セナリバ) | 1.30.03 | 2026-10-28 | Japanese | O | 7 | 12+ | 無料 | JPY | 15.0 |
| tw | 七騎士 Re:BIRTH | 1.30.03 | 2026-10-28 | Han | O | 7 | 12+ | 免費 | TWD | 15.0 |
| th | Seven Knights Re:BIRTH | 1.30.03 | 2026-10-28 | Latin | O | 7 | 12+ | Free | THB | 15.0 |
| es | Seven Knights Re:BIRTH | 1.30.03 | 2026-10-28 | Latin | X | 7 | 12+ | Gratis | EUR | 15.0 |

### 관찰

- [C3] th 릴리스 노트 문자 체계 Latin (스토어 언어 Thai)
- [C4] es 지원 언어 목록에 ES 없음

## 점검 항목

- C1 국가별 출시 여부, C2 버전과 버전 출시일 차이(단계 출시), C3 릴리스 노트 문자 체계와 스토어 언어
- C4 지원 언어 목록(languageCodesISO2A)에 스토어 국가 언어 포함 여부, C5 연령 등급(contentAdvisoryRating)
- C6 가격 표기(formattedPrice)와 통화, C7 최소 OS(minimumOsVersion)

- 관찰 합계: 5건 (C1 1건, C3 3건, C4 1건)
