# 구글 플레이 16KB 메모리 페이지 크기 대응 정리

> 공개 자료만 사용. 사내 빌드 정보·일정·수치는 넣지 않음. 확인일 2026-10-20

## 1. 변경 내용

- 안드로이드 15부터 메모리 페이지 크기 16KB 기기 지원 (기존 4KB)
- 구글 플레이: **안드로이드 15(API 35) 이상을 타깃으로 하는 앱은 64비트 기기에서 16KB 페이지를 지원해야 함**
- 해당 대상: 네이티브 코드(`.so`)를 포함한 앱. 자바·코틀린만 쓰는 앱은 이미 지원
	- 게임은 엔진(Unity `libunity.so`, Unreal) 자체가 네이티브 → **사실상 모든 엔진 게임이 대상**
	- 서드파티 SDK(광고·결제·보안·분석)의 `.so`도 각각 16KB 정렬이어야 함
- 정렬이 안 된 앱은 16KB 기기에서 설치·실행 실패, 또는 호환 모드로 실행되며 경고 표시

## 2. 적용 일정

| 날짜 | 내용 |
|---|---|
| 2025-11-01 | 신규 앱·업데이트 중 안드로이드 15+ 타깃 앱 16KB 지원 요구 시작 (Play Console에서 연장 요청 가능) |
| 2026-05 전후 | 연장 신청 앱의 유예 종료 (개발자 포럼 기준, 공식 문서 미확인) |
| **2027-02-01** | 16KB를 지원하지 않는 업데이트는 **출시 불가** (현재 안드로이드 공식 문서) |

- 일정은 여러 번 바뀌었으므로 제출 전 Play Console 정책 상태와 공식 문서를 다시 확인

## 3. 게임에 미치는 영향

| 구분 | 내용 |
|---|---|
| Unity | 16KB 지원 시작 버전: **6000.0.38f1, 2022.3.56f1, 2021.3.48f1** 이상. 이전 버전 빌드는 재빌드 필요 |
| 빌드 도구 | AGP 8.5.1 이상 + 압축하지 않은 공유 라이브러리, NDK r28 이상은 기본 16KB 정렬 (r27 이하는 링커 옵션 추가) |
| 서드파티 SDK | 미리 빌드된 `.so`는 SDK 제공사가 16KB 정렬 버전을 내야 함 → **SDK 업데이트 대기가 일정의 병목** |
| 코드 | `PAGE_SIZE`·4096을 하드코딩한 네이티브 코드는 `getpagesize()` 등으로 교체 |
| 위험 | RELRO 구간 정렬이 맞지 않으면 런타임 세그멘테이션 오류(크래시) |

- Day 74(Unity 보안 패치)처럼 **엔진 버전 업 → 전체 회귀**로 이어지는 유형. 두 대응을 한 번의 엔진 업데이트로 묶으면 회귀를 한 번에 끝낼 수 있음 (2022.3은 2022.3.62f2 이상이면 둘 다 충족)

## 4. QA 체크리스트

### 4-1. 빌드 확인 (정적)
- [ ] Android Studio **Build > Analyze APK** → `lib/arm64-v8a`의 `.so` 목록 확인 (엔진·SDK별)
- [ ] `zipalign -c -P 16 -v 4 <APK>` → 마지막 줄 `Verification successful`
- [ ] `check_elf_alignment.sh <APK>` → 모든 arm64 라이브러리 `ALIGNED`
- [ ] UNALIGNED 라이브러리가 있으면 어느 SDK 것인지 목록화해 담당자에게 전달
- [ ] Play Console 업로드 시 16KB 경고 없음

### 4-2. 실행 확인 (동적)
- [ ] 16KB 환경 준비: 에뮬레이터 "16 KB Page Size" 시스템 이미지 또는 Pixel 개발자 옵션 **Boot with 16KB page size**
- [ ] `adb shell getconf PAGE_SIZE` → `16384` 확인 후 테스트
- [ ] 설치·첫 실행·호환 모드 경고 팝업이 뜨지 않는지
- [ ] 엔진 초기화, 로그인, 결제 SDK, 광고 SDK, 보안 솔루션 초기화 (SDK `.so`가 로드되는 시점)
- [ ] 리소스 다운로드·씬 전환·장시간 플레이 크래시 없음
- [ ] 같은 빌드를 4KB 기기에서도 실행 (한 빌드가 두 페이지 크기 모두 지원해야 함)

## 5. 정리
- 16KB 대응은 게임 코드보다 **엔진 버전과 SDK 목록 관리**가 핵심. QA는 `zipalign`·ELF 정렬 확인으로 출시 전에 걸러낼 수 있음
- 실기기가 없어도 16KB 에뮬레이터 이미지로 실행 검증 가능

## 출처
1. Android Developers, Support 16 KB page sizes: https://developer.android.com/guide/practices/page-sizes
2. Unity Discussions, Unity Engine support for 16 KB memory page sizes (Android 15+): https://discussions.unity.com/t/info-unity-engine-support-for-16-kb-memory-page-sizes-android-15/1589588
3. Unity Manual, Android requirements and compatibility: https://docs.unity.com/en-us/engine/6000.0/manual/platform-specific/android/introducing/requirements-and-compatibility
4. Qt Blog, Android 15 and 16 support (Google Play 16KB 요구 범위): https://www.qt.io/blog/android-15-and-16-support
