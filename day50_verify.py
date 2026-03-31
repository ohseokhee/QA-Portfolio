"""
Day 50 : 로컬에서 EC2 경유 RDS E2E 결과 검증
의존성: py -m pip install paramiko pymysql
⚠️ EC2 재시작 후 EC2_HOST 업데이트 필요
⚠️ RDS 엔드포인트는 재시작해도 변하지 않음
"""

import paramiko
import pymysql
import sys

# ── 접속 정보 ─────────────────────────────────────────────────────────────
EC2_HOST     = "YOUR_EC2_DNS"
EC2_USER     = "ubuntu"
KEY_PATH     = r"C:\Users\USER\PycharmProjects\QAOps\qa-key.pem"

RDS_HOST     = "YOUR_RDS_ENDPOINT"
RDS_PORT     = 3306
RDS_USER     = "admin"
RDS_PASSWORD = "YOUR_PASSWORD"
RDS_DB       = "qa_db"
# ──────────────────────────────────────────────────────────────────────────

REMOTE_DIR = "/home/ubuntu/qa-portfolio"

EC2_COMMANDS = [
    ("컨테이너 상태 확인",
     f"cd {REMOTE_DIR} && docker compose -f day47_docker-compose.yml ps"),
    ("E2E 테스트 실행 (RDS 대상)",
     f"cd {REMOTE_DIR} && "
     f"DB_HOST='{RDS_HOST}' DB_PORT='3306' "
     f"DB_USER='{RDS_USER}' DB_PASSWORD='{RDS_PASSWORD}' DB_NAME='{RDS_DB}' "
     f"python -m pytest day50_e2e_rds.py -v 2>&1 | tail -20"),
]


def check_rds_result():
    """RDS에 저장된 최신 결과 직접 조회"""
    print("[RDS 최종 데이터 확인]")
    try:
        conn = pymysql.connect(
            host=RDS_HOST, port=RDS_PORT,
            user=RDS_USER, password=RDS_PASSWORD,
            database=RDS_DB, connect_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT browser, site, keyword, result_title, id "
                "FROM search_results ORDER BY id DESC LIMIT 5"
            )
            rows = cursor.fetchall()
            for row in rows:
                print(f"  id={row[4]} | {row[0]} | {row[1]} | {row[3]}")
        conn.close()
        print()
    except Exception as e:
        print(f"  RDS 직접 접근 불가 (퍼블릭 비활성화): {e}\n")


def run_via_ec2():
    """EC2 경유 E2E 테스트 실행 및 결과 확인"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=EC2_HOST, username=EC2_USER,
            key_filename=KEY_PATH, timeout=10,
        )
        print("[EC2 연결 성공]\n")

        for label, cmd in EC2_COMMANDS:
            _, stdout, stderr = client.exec_command(cmd, get_pty=True)
            output = stdout.read().decode().strip()
            print(f"[{label}]")
            for line in output.splitlines():
                print(f"  {line}")
            print()

    except Exception as e:
        print(f"[EC2 연결 실패] {e}")
        sys.exit(1)
    finally:
        client.close()


def run():
    print("=" * 55)
    print("  Day 50 RDS E2E 통합 검증")
    print(f"  EC2 : {EC2_HOST}")
    print(f"  RDS : {RDS_HOST}")
    print("=" * 55 + "\n")

    run_via_ec2()
    check_rds_result()

    print("=" * 55)
    print("  검증 완료")
    print("=" * 55)


if __name__ == "__main__":
    run()
