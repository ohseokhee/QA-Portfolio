import subprocess
import os
import time


def run_day33_docker_volume():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(current_dir, "docker-compose.yml")

    # Docker Compose 설정 (Volume 추가)
    compose_content = """services:
  db:
    image: mariadb:10.6
    container_name: day33_db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: password
    volumes:
      - ./db_data:/var/lib/mysql
  app:
    image: python:3.10-slim
    container_name: day33_app
    depends_on:
      - db
    command: ["python", "-c", "print('Docker Volume Test Success')"]
"""

    with open(compose_file, "w", encoding="utf-8") as f:
        f.write(compose_content)
    print(f"   [확인] {compose_file} 생성 완료.")

    print("   [실행] Docker Volume 환경 가동 및 데이터 보존 테스트...")
    subprocess.run(["docker", "compose", "down"], cwd=current_dir, shell=True, capture_output=True)
    subprocess.run(["docker", "compose", "up", "-d"], cwd=current_dir, shell=True, capture_output=True)

    time.sleep(5)
    try:
        ps_res = subprocess.check_output(
            ["docker", "compose", "ps"],
            cwd=current_dir, shell=True, text=True, encoding='utf-8'
        )
        print("\n[Docker Compose Status]")
        print(ps_res.strip())

        # 호스트에 데이터 디렉토리가 생성되었는지 확인
        if os.path.exists(os.path.join(current_dir, "db_data")):
            print("   [체크] 호스트 볼륨 디렉토리(db_data) 생성 확인 완료.")
    except Exception as e:
        print(f"   [오류] {e}")


if __name__ == "__main__":
    run_day33_docker_volume()