"""
Day 54 : EC2 + RDS + Grid 통합 실행 - Phase 4 전체 플로우 1회 완주 (1/2)
의존성: py -m pip install paramiko
사전 준비: Day 46(EC2 접속)~Day 50(RDS E2E) 자산 + 재생성된 RDS(qa-portfolio-rds)
⚠️ RDS는 Day 50 이후 비용 절감을 위해 삭제되었다가 Day 54에서 재생성됨 (엔드포인트 변경)
"""

import os
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 접속 정보 ─────────────────────────────────────────────────────────────
EC2_HOST = "3.26.158.35"
EC2_USER = "ubuntu"
KEY_PATH = r"C:\Users\USER\PycharmProjects\QAOps\qa-key.pem"
REMOTE_DIR = "/home/ubuntu/qa-portfolio"

RDS_HOST     = "qa-portfolio-rds.cz0euwqk8xws.ap-southeast-2.rds.amazonaws.com"
RDS_PORT     = 3306
RDS_USER     = "admin"
RDS_PASSWORD = os.environ.get("RDS_PASSWORD", "YOUR_PASSWORD")
RDS_DB       = "qa_db"
# ──────────────────────────────────────────────────────────────────────────

LOCAL_ALLURE_RESULTS = "allure-results"
REMOTE_ALLURE_RESULTS = f"{REMOTE_DIR}/allure-results"

CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS search_results ("
    "id INT AUTO_INCREMENT PRIMARY KEY, "
    "browser VARCHAR(20), site VARCHAR(20), "
    "keyword VARCHAR(100), result_title VARCHAR(255))"
)

PY_CREATE_TABLE = (
    "import pymysql; "
    f"c = pymysql.connect(host='{RDS_HOST}', port={RDS_PORT}, user='{RDS_USER}', "
    f"password='{RDS_PASSWORD}', database='{RDS_DB}'); "
    f"cur = c.cursor(); cur.execute(\\\"{CREATE_TABLE_SQL}\\\"); c.commit(); "
    "print('테이블 준비 완료: search_results')"
)

EC2_COMMANDS = [
    ("파이썬 의존성 설치 (EC2 재생성/컨테이너 초기화로 재설치 필요)",
     f"cd {REMOTE_DIR} && python3 -m pip install --break-system-packages -q "
     f"selenium pytest pymysql allure-pytest boto3"),

    ("Selenium Grid 기동 확인/시작",
     f"cd {REMOTE_DIR} && docker compose --ansi never -f day47_docker-compose.yml up -d selenium-hub chrome && "
     f"sleep 5 && docker compose --ansi never -f day47_docker-compose.yml ps"),

    ("RDS 대상 테이블 준비 (재생성된 RDS라 스키마 없음)",
     f'cd {REMOTE_DIR} && python3 -c "{PY_CREATE_TABLE}"'),

    ("E2E 테스트 실행 (Grid + RDS, Allure 결과 수집)",
     f"cd {REMOTE_DIR} && rm -rf allure-results && "
     f"DB_HOST='{RDS_HOST}' DB_PORT='{RDS_PORT}' "
     f"DB_USER='{RDS_USER}' DB_PASSWORD='{RDS_PASSWORD}' DB_NAME='{RDS_DB}' "
     f"python3 -m pytest day50_e2e_rds.py --alluredir=allure-results -v 2>&1 | tail -30"),
]


def upload_test_script(client):
    """day50_e2e_rds.py가 EC2에 없으므로(컨테이너/파일 초기화) 업로드"""
    print("[E2E 테스트 스크립트 업로드]")
    sftp = client.open_sftp()
    sftp.put("day50_e2e_rds.py", f"{REMOTE_DIR}/day50_e2e_rds.py")
    sftp.close()
    print(f"  업로드 완료: day50_e2e_rds.py → {REMOTE_DIR}/\n")


def run_ec2_commands(client):
    for label, cmd in EC2_COMMANDS:
        _, stdout, stderr = client.exec_command(cmd, get_pty=True)
        output = stdout.read().decode().strip()
        print(f"[{label}]")
        for line in output.splitlines():
            print(f"  {line}")
        print()


def fetch_allure_results(client):
    """EC2의 allure-results 디렉토리를 로컬로 회수 (재귀 다운로드)"""
    print("[Allure 결과 회수]")
    sftp = client.open_sftp()
    os.makedirs(LOCAL_ALLURE_RESULTS, exist_ok=True)

    count = 0
    for filename in sftp.listdir(REMOTE_ALLURE_RESULTS):
        remote_path = f"{REMOTE_ALLURE_RESULTS}/{filename}"
        local_path = os.path.join(LOCAL_ALLURE_RESULTS, filename)
        sftp.get(remote_path, local_path)
        count += 1
    sftp.close()
    print(f"  회수 완료: {count}개 파일 → {LOCAL_ALLURE_RESULTS}/\n")


def run():
    print("=" * 55)
    print("  Day 54 EC2+RDS+Grid 통합 실행")
    print(f"  EC2 : {EC2_HOST}")
    print(f"  RDS : {RDS_HOST}")
    print("=" * 55 + "\n")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=EC2_HOST, username=EC2_USER, key_filename=KEY_PATH, timeout=10)
        print("[EC2 연결 성공]\n")

        upload_test_script(client)
        run_ec2_commands(client)
        fetch_allure_results(client)

    except Exception as e:
        print(f"[실패] {e}")
        sys.exit(1)
    finally:
        client.close()

    print("=" * 55)
    print("  Day 54 통합 실행 완료")
    print("=" * 55)


if __name__ == "__main__":
    run()
