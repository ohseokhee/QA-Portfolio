import subprocess
import os


def run_day31_docker_pipeline():
    # 1. 설정 변수 정의 (파일명 규칙 엄수)
    file_name = "day30_integraion.py"
    image_name = "day31_image"
    container_name = "day31_docker"
    current_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"--- 31일차 도커 통합 파이프라인 가동: {container_name} ---")

    # 2. 설계도(Dockerfile) 및 의존성 파일 생성
    dockerfile_content = f"""FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY {file_name} .
CMD ["python", "{file_name}"]
"""
    with open(os.path.join(current_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    with open(os.path.join(current_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("selenium\n")

    # 3. 이미지 빌드 (Build)
    print(f"1. 이미지 빌드 시작: {image_name}")
    build_res = subprocess.run(
        ["docker", "build", "-t", image_name, "."],
        cwd=current_dir, shell=True, capture_output=True, text=True
    )
    if build_res.returncode != 0:
        print(f"   [빌드에러] {build_res.stderr}")
        return

    # 4. 컨테이너 생성 및 실행 (Run)
    print(f"2. 컨테이너 재생성 및 실행: {container_name}")
    # 이름 충돌 방지를 위해 기존 컨테이너 선제 삭제
    subprocess.run(["docker", "rm", "-f", container_name], shell=True, capture_output=True)

    run_res = subprocess.run(
        ["docker", "run", "--name", container_name, image_name],
        cwd=current_dir, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
    )

    # 5. 실행 로그 확인
    print("\n--- [도커 내부 실행 로그] ---")
    if run_res.stdout:
        print(run_res.stdout.strip())
    if run_res.stderr:
        print(run_res.stderr.strip())
    print("------------------------------")

    # 6. 생성된 이미지 목록 조회 (Images)
    print("\n3. 로컬 도커 이미지 리스트 확인")
    image_list = subprocess.check_output(
        ["docker", "images", image_name],
        shell=True, text=True, encoding='utf-8'
    )
    print(image_list.strip())

    if image_name in image_list:
        print(f"\n[최종검증] '{image_name}' 보관 완료. 31일차 인프라 실습 종료.")


if __name__ == "__main__":
    run_day31_docker_pipeline()