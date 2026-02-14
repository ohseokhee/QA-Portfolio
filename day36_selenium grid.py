import subprocess
import os
import time
import urllib.request
import json

def run_day36_selenium_grid():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(current_dir, "docker-compose.yml")

    # Docker Compose 설정 (Selenium Grid)
    compose_content = """services:
  selenium-hub:
    image: selenium/hub:4.18.1
    container_name: day36_hub
    ports:
      - "4442:4442"
      - "4443:4443"
      - "4444:4444"
    networks:
      - grid_network
    restart: always

  chrome-node:
    image: selenium/node-chrome:4.18.1
    container_name: day36_chrome
    shm_size: 2gb
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
      - SE_NODE_MAX_SESSIONS=3
    networks:
      - grid_network
    restart: always

  firefox-node:
    image: selenium/node-firefox:4.18.1
    container_name: day36_firefox
    shm_size: 2gb
    depends_on:
      - selenium-hub
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
      - SE_NODE_MAX_SESSIONS=3
    networks:
      - grid_network
    restart: always

networks:
  grid_network:
    driver: bridge
    name: day36_grid_net
"""

    # docker-compose.yml 생성
    print("[생성] docker-compose.yml 작성 중...")
    with open(compose_file, 'w', encoding='utf-8') as f:
        f.write(compose_content)
    print("[확인] docker-compose.yml 생성 완료")

    # 기존 컨테이너 정리
    print("\n[정리] 기존 컨테이너 제거 중...")
    subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"],
                   cwd=current_dir, check=False)

    # Docker Compose 실행
    print("\n[실행] Selenium Grid 환경 시작...")
    result = subprocess.run(["docker-compose", "-f", compose_file, "up", "-d"],
                            cwd=current_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print("[성공] 컨테이너 실행 완료")
    else:
        print(f"[오류] 실행 실패:\n{result.stderr}")
        return

    # Grid Hub 준비 대기
    print("\n[대기] Selenium Grid Hub 준비 중...")
    for i in range(12):
        time.sleep(5)
        try:
            url = "http://localhost:4444/wd/hub/status"
            req = urllib.request.urlopen(url, timeout=3)
            data = json.loads(req.read().decode())
            if data.get("value", {}).get("ready"):
                print(f"[확인] Grid Hub 준비 완료 ({(i+1)*5}초 경과)")
                break
        except Exception:
            print(f"  → 대기 중... ({(i+1)*5}초 경과)")
    else:
        print("[경고] Hub 준비 타임아웃 - 수동 확인 필요")
        return

    # Grid 상태 확인
    print("\n[검증 1] Grid 노드 등록 상태 확인")
    print("=" * 60)
    try:
        url = "http://localhost:4444/wd/hub/status"
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read().decode())
        nodes = data.get("value", {}).get("nodes", [])
        print(f"  → 등록된 노드 수: {len(nodes)}개")
        for node in nodes:
            caps = node.get("slots", [])
            browsers = set(s.get("stereotype", {}).get("browserName", "") for s in caps)
            print(f"  → 노드: {node.get('id', '')[:8]}... | 브라우저: {', '.join(browsers)} | 세션: {len(caps)}슬롯")
    except Exception as e:
        print(f"  → 상태 조회 실패: {e}")

    # 컨테이너 상태 확인
    print("\n[검증 2] 컨테이너 실행 상태")
    print("=" * 60)
    subprocess.run(["docker", "ps", "--filter", "name=day36", "--format",
                    "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])

    # Grid UI 안내
    print("\n[안내] Selenium Grid UI 접속:")
    print("  → http://localhost:4444/ui")
    print("  → Chrome 노드: 최대 3세션")
    print("  → Firefox 노드: 최대 3세션")

    # RemoteWebDriver 테스트 코드 안내
    print("\n[검증 3] RemoteWebDriver 연결 테스트")
    print("=" * 60)
    try:
        from selenium import webdriver
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

        print("  → Chrome RemoteWebDriver 연결 시도...")
        chrome_options = webdriver.ChromeOptions()
        driver = webdriver.Remote(
            command_executor="http://localhost:4444/wd/hub",
            options=chrome_options
        )
        driver.get("https://www.google.com")
        print(f"  → Chrome 접속 성공: {driver.title}")
        driver.quit()

        print("  → Firefox RemoteWebDriver 연결 시도...")
        firefox_options = webdriver.FirefoxOptions()
        driver = webdriver.Remote(
            command_executor="http://localhost:4444/wd/hub",
            options=firefox_options
        )
        driver.get("https://www.google.com")
        print(f"  → Firefox 접속 성공: {driver.title}")
        driver.quit()

        print("\n[성공] Chrome / Firefox 양쪽 Grid 연결 완료")

    except ImportError:
        print("  → selenium 미설치: pip install selenium")
    except Exception as e:
        print(f"  → RemoteWebDriver 연결 실패: {e}")

    print("\n[안내] 컨테이너 중지 명령어:")
    print(f"  → docker-compose -f {compose_file} down")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 36: Selenium Grid 도커 기반 병렬 테스트 인프라 구축")
    print("=" * 60)
    run_day36_selenium_grid()