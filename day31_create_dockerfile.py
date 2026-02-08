import os
import time


def create_docker_configs():
    # 1. Dockerfile 내용 정의
    dockerfile_content = """# 1. 베이스 이미지 설정
FROM python:3.10-slim

# 2. 필수 도구 설치
RUN apt-get update && apt-get install -y \\
    wget \\
    gnupg \\
    unzip \\
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 복사
COPY . .

# 6. 실행 (30일차 결과 확인)
CMD ["python", "day30_final_integration.py"]
"""

    # 2. requirements.txt 내용 정의 (실습에 필요한 최소 라이브러리)
    requirements_content = """selenium
sqlite3
"""

    print("1. Docker 설정 파일 생성 시작...")

    # Dockerfile 생성
    with open("Dockerfile", "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    print("   [확인] Dockerfile 생성 완료.")
    time.sleep(5)

    # requirements.txt 생성
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements_content)
    print("   [확인] requirements.txt 생성 완료.")
    time.sleep(5)

    print("2. 모든 설정 파일이 준비되었습니다. 이제 빌드 스크립트를 다시 돌려보세요.")


if __name__ == "__main__":
    create_docker_configs()