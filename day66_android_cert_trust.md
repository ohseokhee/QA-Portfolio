# Day 66 HTTPS 복호화와 안드로이드 인증서 신뢰

## 1. 프록시가 HTTPS를 복호화하는 원리

```
[클라이언트] --TLS(프록시가 즉석 발급한 인증서)--> [프록시] --TLS(서버 진짜 인증서)--> [서버]
```

- 프록시(Fiddler, Charles, mitmproxy)는 클라이언트에게 "그 서버인 척" 인증서를 즉석에서 만들어 보여 준다. 이 인증서는 프록시 자신의 루트 CA가 서명한다
- 클라이언트가 프록시 루트 CA를 신뢰하지 않으면 TLS 핸드셰이크 단계에서 실패한다 → 그래서 PC·단말에 프록시 인증서를 설치한다
- 프록시와 서버 사이 구간은 프록시가 일반 클라이언트처럼 서버 인증서를 검증한다

## 2. Day 66 실측 (day66_https_capture.py)

| 단계 | 클라이언트가 신뢰하는 CA | 결과 |
|---|---|---|
| 직접 접속 | 시스템 기본 저장소 | 실패 `certificate verify failed: unable to get local issuer certificate` (자체 발급 CA라서) |
| 직접 접속 | 로컬 CA(`day66_certs/ca.pem`) | 200 |
| 프록시 경유, 인증서 설치 전 | 로컬 CA만 | 실패 (프록시가 발급한 인증서를 모름) |
| 프록시 경유, 인증서 설치 후 | 프록시 CA(`day66_mitm/mitmproxy-ca-cert.pem`) | 200, 구매 요청 본문·토큰이 프록시에서 평문으로 보임 |

- 검증 끄기 옵션(`verify=False`)은 쓰지 않았다. 신뢰할 CA 파일 경로를 `verify`에 지정하는 방식이 실제 "인증서 설치"와 같은 의미다
- 프록시→서버 구간도 `ssl_verify_upstream_trusted_ca`로 로컬 CA를 지정해 검증했다

## 3. 안드로이드 7(API 24) 이상에서 사용자 인증서를 기본으로 믿지 않는 이유

| 구분 | 안드로이드 6 이하 | 안드로이드 7 이상 |
|---|---|---|
| 시스템 인증서 (OS 기본 탑재) | 신뢰 | 신뢰 |
| 사용자 인증서 (설정에서 직접 설치) | 신뢰 | **앱이 명시적으로 허용할 때만 신뢰** |

- 이유: 악성 앱이나 공격자가 사용자를 속여 인증서를 설치하게 하면 모든 앱의 HTTPS 통신을 엿볼 수 있었기 때문. 기본값을 "앱이 허용한 경우만"으로 바꿔 피해 범위를 줄였다
- 결과: 프록시 인증서를 단말에 설치해도 **브라우저(크롬)는 사용자 인증서를 신뢰하지만, 일반 앱·게임은 신뢰하지 않아** 캡처가 안 된다
- 추가로 게임은 인증서 고정(Certificate Pinning)을 쓰는 경우가 많다. 특정 인증서만 받도록 코드에 박아 두어 사용자 인증서를 허용해도 프록시를 거부한다

## 4. 실무에서 QA 빌드에 별도 설정을 요청하는 배경

QA가 단말에서 게임 통신을 캡처하려면 개발팀에 **QA(디버그) 빌드에서만** 아래 설정을 넣어 달라고 요청한다.

```xml
<!-- res/xml/network_security_config.xml (debug 빌드 전용) -->
<network-security-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />   <!-- 사용자 설치 인증서 신뢰 -->
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```

- `debug-overrides`는 `android:debuggable="true"` 빌드에서만 적용되므로 라이브(릴리스) 빌드에는 영향이 없다
- 인증서 고정을 쓰는 게임은 QA 빌드에서 고정을 끄는 플래그도 함께 요청한다
- 릴리스 빌드에 이 설정이 남아 있으면 보안 결함이다 → 출시 전 체크리스트 항목 (릴리스 APK의 `network_security_config` 확인)

## 5. Fiddler에서 같은 작업을 할 때

| 작업 | Fiddler Classic 메뉴 |
|---|---|
| HTTPS 복호화 켜기 | Tools > Options > HTTPS > Capture HTTPS CONNECTs, Decrypt HTTPS traffic 체크 |
| PC에 루트 인증서 신뢰 | 같은 탭 Actions > Trust Root Certificate |
| 단말에 인증서 설치 | 단말 브라우저로 `http://{PC IP}:8888` 접속 → FiddlerRoot certificate 다운로드 → 설정 > 보안 > 인증서 설치 |
| 로컬 모의 서버만 복호화 | HTTPS 탭 "...from all processes" 대신 Skip decryption 목록 활용 |
