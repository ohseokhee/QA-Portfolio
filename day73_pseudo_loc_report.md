# Day 73 의사 현지화 점검 결과

- 대상: `day65_shop_client.html` → `day73_shop_client_pseudo.html` (문자열 25개 변환)
- 변환 문자열 길이 합계: 134자 → 채움 문자 포함 194자 (+45%) → 괄호·공백까지 269자 (+101%)
- 변환 규칙: 라틴 문자 → 악센트 문자, 길이 35%만큼 채움 문자(ẞŦǾŴ) 추가, `[ ]`로 감싸 잘림 확인

| 페이지 | 화면 | 페이지 폭 / 화면 폭 | 가로 스크롤 | 넘침·화면 밖 | 줄바꿈 | 스크린샷 |
|---|---|---|---|---|---|---|
| original | mobile | 360 / 360 | 없음 | 0 | 0 | day73_screenshots\day73_original_mobile.png |
| original | desktop | 1265 / 1280 | 없음 | 0 | 0 | day73_screenshots\day73_original_desktop.png |
| pseudo | mobile | 360 / 360 | 없음 | 0 | 10 | day73_screenshots\day73_pseudo_mobile.png |
| pseudo | desktop | 1265 / 1280 | 없음 | 0 | 0 | day73_screenshots\day73_pseudo_desktop.png |

## 문제 요소 (의사 현지화 페이지, 빨강 = 넘침, 주황 = 줄바꿈)

| 화면 | 요소 | 종류 | 오른쪽 끝(px) | 폭(px) | 텍스트 |
|---|---|---|---|---|---|
| mobile | TD | wrap | 145 | 121 | [프리미엄 선수팩 ẞŦǾ] |
| mobile | BUTTON | wrap | 332 | 58 | [구매 ẞ] |
| mobile | TD | wrap | 206 | 61 | BP 50000 |
| mobile | BUTTON | wrap | 332 | 58 | [구매 ẞ] |
| mobile | TD | wrap | 206 | 61 | BP 10000 |
| mobile | BUTTON | wrap | 332 | 58 | [구매 ẞ] |
| mobile | TD | wrap | 145 | 121 | [클럽 유니폼 세트 ẞŦǾŴ] |
| mobile | BUTTON | wrap | 332 | 58 | [구매 ẞ] |
| mobile | TD | wrap | 145 | 121 | [이벤트 한정팩 ẞŦǾ] |
| mobile | BUTTON | wrap | 332 | 58 | [구매 ẞ] |
