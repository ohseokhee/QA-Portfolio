# 메모리·FPS 측정 가이드 (Day 81·82 도구 사용법)

> 대상: 안드로이드 기기 또는 에뮬레이터(ADB 디버깅 켜짐). 도구: `day81_mem_measure.py`, `day82_fps_measure.py`
> 기준: 구글 플레이 레벨업 성능(평균 55 / 하위 10% 50 / 하위 1% 30fps), 2027-02 메모리 기준(Anonymous RSS + swap, 상태별 평가) — 자세한 내용은 `day76_policy_google_levelup.md`

## 1. 측정 전 고정할 것

| 항목 | 이유 | 기록 예 |
|---|---|---|
| 기기·OS·화면 주사율 | 같은 빌드도 기기 성능 등급·주사율(60/90/120Hz)에 따라 결과가 다름. 구글 기준도 성능 등급별 평가 | 기기명, Android 버전, RAM, 60Hz |
| 시나리오 | 측정마다 플레이 내용이 다르면 빌드 간 비교가 안 됨 | 로비 30초 → 전투 3판 → 로비 복귀 → 홈 버튼 1분 → 복귀 |
| 빌드 | 디버그 빌드는 메모리·프레임이 릴리스와 다름 | 릴리스 후보 빌드 번호 |
| 발열·충전 상태 | 발열로 클럭이 내려가면 후반 FPS가 떨어짐 | 시작 배터리 온도, 충전 케이블 분리 |

## 2. 연결 확인

```
adb devices                                  # 기기 1대 이상 "device" 상태
adb shell pidof <패키지>                       # 앱 실행 중인지
adb shell dumpsys SurfaceFlinger --list      # 게임 레이어 이름 확인 (SurfaceView[...] 형태)
```
- 에뮬레이터(LDPlayer)는 설정 > 기타 설정 > ADB 디버깅 "로컬 연결 열기"가 켜져 있어야 `adb devices`에 나타남
- adb가 PATH에 없으면 두 도구 모두 `--adb <adb.exe 경로>` 지정

## 3. 메모리 (Day 81)

```
py day81_mem_measure.py --package <패키지> --label lobby --count 10 --interval 2
py day81_mem_measure.py --package <패키지> --label battle1 --count 10 --interval 2
...
py day81_mem_measure.py --package <패키지> --label background --count 10 --interval 2   # 홈 버튼 후
```
- 구간을 여러 번 실행할 때는 `--out <이름>`을 같게 주면 한 CSV에 이어 붙고 전체 구간으로 다시 판정. 측정 없이 판정만 다시 하려면 `--analyze <이름>`
- 구간 라벨 규칙: 처음 로비 `lobby`, 전투 뒤 로비 `lobby_after1~N`, 백그라운드 `background` → 누수(M1)·해제(M2) 판정에 사용
- 왕복은 8회 이상: 설정 앱 실측에서 6회까지는 계속 올라 "누수 의심"이었지만 15회 왕복에서는 8회째부터 평탄(상한 있는 캐시) → M1은 최근 5회 증가율로 "누수 의심 / 증가 후 안정"을 나눔
- 기록 값: TOTAL PSS(앱 간 비교), RssAnon + VmSwap(구글 플레이 기준 지표), 힙 할당량(상세 표 Heap Alloc 열, Native+Dalvik), Graphics
- 에뮬레이터(LDPlayer 안드로이드 14)는 App Summary의 Native Heap·Java Heap PSS가 0으로 나옴(Unknown으로 집계) → 누수 판정은 Heap Alloc 열 기준. 스왑 줄은 `TOTAL SWAP (KB):` 형식
- 판정: 같은 로비로 돌아와도 Native Heap이 계속 오르면 누수 의심, 백그라운드에서 내려가지 않으면 텍스처·비트맵 해제 확인 요청
- 안드로이드 17 기기에서 장시간 플레이 후 종료되면 `ApplicationExitInfo` 사유에 `MemoryLimiter:AnonSwap`이 있는지 확인 (크래시 리포트에 안 잡힘)

## 4. FPS (Day 82)

```
py day82_fps_measure.py --method sf --layer "<레이어 이름>" --label battle --seconds 60
py day82_fps_measure.py --method ts --layer <레이어 이름 일부> --label battle --seconds 10 --out <이름>
py day82_fps_measure.py --method gfx --package <패키지> --label menu --seconds 10
```
- `--latency`가 0만 돌려주는 환경(LDPlayer 안드로이드 14에서 확인)은 `--method ts`: `--timestats`의 레이어별 present2present 히스토그램. 프레임 순서가 없으므로 그래프는 프레임 시간 분포로 그림
- timestats는 칸 하한값(16ms)을 쓰므로 60Hz에서 62.5fps로 표시됨(약 4% 높음). 33ms 칸(30.3fps)처럼 기준 경계에 걸리면 원본 히스토그램과 averageFPS를 함께 확인
- 게임(Unity·Unreal 등 SurfaceView 렌더링)은 `--method sf`: 레이어 단위 실제 표시 시각. `gfxinfo`는 안드로이드 UI 렌더러 기준이라 게임 화면 프레임이 안 잡힐 수 있음
- 일반 앱 화면·게임의 네이티브 UI(결제창 등)는 `--method gfx`: 버벅임 비율과 프레임 시간 백분위도 함께 출력
- 구간을 나눠 측정: 전체 평균은 기준을 넘어도 보스 스킬·대규모 이펙트 구간의 하위 1%가 30fps 아래로 떨어질 수 있음 (데모 리포트의 `전체` vs `boss_skill`)
- 하위 10%·하위 1% FPS = 프레임 간격 90·99번째 백분위의 역수. 60Hz에서 vsync 2개(33.3ms) 프레임은 30fps로 보고 기준 충족 처리 (부동소수 오차 반올림)

## 5. 리포트에 쓸 것

1. 환경(1번 표), 시나리오, 빌드
2. 구간별 표: 메모리(TOTAL PSS, Anon RSS+swap, Native, Graphics), FPS(평균, 하위 10%, 하위 1%, 최장 프레임)
3. 기준 미달 구간과 재현 조건 (예: "boss_skill 구간 하위 1% 15fps, 스킬 연출 시작 직후 66.7ms 프레임 반복")
4. 이전 빌드 같은 시나리오 결과와 비교
5. 첨부: CSV, 그래프 PNG

## 6. 현재 상태

- LDPlayer(ASUS AI2201_B 프로필, 안드로이드 14, 60Hz)에서 공개 기본 앱으로 실측 완료
	- 메모리: 설정 앱 6회 왕복 `day81_mem_settings.md`, 15회 왕복 `day81_mem_settings_15r.md` (힙 할당량 23.3 → 42.5MB에서 평탄 = 증가 후 안정)
	- FPS: Chrome 부하 페이지(`day82_fps_anim.html`, 입자 300 / 3,000 / 10,000개) timestats `day82_fps_chrome.md`, 설정 앱 스크롤 gfxinfo `day82_fps_settings.md`
- 합성 데모 결과(`day81_mem_report.md`, `day82_fps_report.md`)는 판정 로직 검증용으로 남겨 둠 (실측 아님)
- 에뮬레이터는 PC GPU로 그리므로 실제 기기와 절대값이 다름 → 기준 판정은 실기기, 에뮬레이터는 도구·절차 검증과 빌드 간 상대 비교용
