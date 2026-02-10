import subprocess
import os
import time


def run_day32_docker_compose():
    # 1. 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(current_dir, "docker-compose.yml")

    # 2. docker-compose.yml 내용 정의 (최신 사양에 맞춰 version 제거)
    compose_content = """services:
  db:
    image: mariadb:10.6
    container_name: day32_db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: password
  app:
    image: python:3.10-slim
    container_name: day32_app
    depends_on:
      - db
    command: ["python", "-c", "print('Docker Compose App Execution Success')"]
"""

    # 3. YAML 파일 생성
    with open(compose_file, "w", encoding="utf-8") as f:
        f.write(compose_content)
    print(f"   [확인] {compose_file} 생성 완료.")

    # 4. 기존 컨테이너 정리 및 실행
    print("   [실행] Docker Compose 환경 가동 중...")
    subprocess.run(["docker", "compose", "down"], cwd=current_dir, shell=True, capture_output=True)

    # up -d: 백그라운드 가동
    subprocess.run(["docker", "compose", "up", "-d"], cwd=current_dir, shell=True, capture_output=True)

    # 5. 상태 확인 (UnicodeDecodeError 방지를 위해 encoding='utf-8' 추가)
    time.sleep(3)
    try:
        ps_res = subprocess.check_output(
            ["docker", "compose", "ps"],
            cwd=current_dir,
            shell=True,
            text=True,
            encoding='utf-8'
        )
        print("\n[Docker Compose Status]")
        print(ps_res.strip())
    except subprocess.CalledProcessError as e:
        print(f"   [오류] 프로세스 실행 실패: {e}")


if __name__ == "__main__":
    run_day32_docker_compose()