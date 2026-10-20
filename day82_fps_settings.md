# 프레임(FPS) 측정 리포트

> 실측: emulator-5554 (ASUS AI2201_B, Android 14) / gfxinfo framestats(최근 120프레임) / 앱 com.android.settings

| 구간 | 프레임 | 평균 FPS | 하위 10% FPS | 하위 1% FPS | 최장 프레임 (ms) | 판정 (55 / 50 / 30) |
|---|---|---|---|---|---|---|
| settings_scroll | 120 | 60.0 | 53.1 | 42.7 | 24.3 | PASS |

## 계산 방법

- 평균 FPS = (프레임 수 - 1) / (마지막 표시 시각 - 첫 표시 시각)
- 하위 10% FPS = 1000 / 프레임 간격 90번째 백분위(ms), 하위 1% FPS = 1000 / 99번째 백분위(ms)
- 구간을 나눠 계산 → 전체 평균이 높아도 전투·스킬 연출 구간의 끊김이 드러나게 함

## 구글 플레이 레벨업 기준과의 연결 (Day 76)

- 성능 기준: 기준 기기 실제 플레이 중 평균 55fps, 하위 10% 50fps, 하위 1% 30fps 이상
- 게임 엔진(Unity 등)은 SurfaceView로 그려서 `gfxinfo`(안드로이드 UI 렌더러 기준)에 프레임이 잡히지 않을 수 있음 → 게임은 SurfaceFlinger `--latency`(레이어 단위 실제 표시 시각), 일반 앱 화면은 `gfxinfo`
- SurfaceFlinger는 최근 약 128프레임만 보관 → 1초마다 읽어 이어 붙임
- `--latency`가 0만 돌려주는 환경(LDPlayer 안드로이드 14에서 확인)은 `--timestats`의 레이어별 present2present 히스토그램 사용 (1ms 칸 해상도, 34ms 이후는 2~50ms 칸)
- 히스토그램 칸 하한값을 간격으로 쓰므로 60Hz 한 프레임(16.7ms)이 16ms로 계산돼 62.5fps로 표시됨 (실제보다 약 4% 높음). 기준 경계 근처(예: 33ms 칸 = 30.3fps)는 원본 히스토그램과 timestats averageFPS를 함께 확인
