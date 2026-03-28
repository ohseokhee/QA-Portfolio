"""
Day 48 : 로컬에서 EC2를 통해 RDS 연결 결과 검증
의존성: py -m pip install paramiko
⚠️ EC2 재시작 후 EC2_HOST 값 업데이트 필요
"""

import paramiko
import sys

# ── 접속 정보 (EC2 재시작 시 EC2_HOST 업데이트 필요) ──────────────────────
EC2_HOST = "YOUR_EC2_DNS"   # 예: ec2-xx-xx-xx-xx.ap-southeast-2.compute.amazonaws.com
EC2_USER = "ubuntu"
KEY_PATH = r"C:\Users\USER\PycharmProjects\QAOps\qa-key.pem"

RDS_HOST     = "YOUR_RDS_ENDPOINT"  # RDS 콘솔에서 확인
RDS_USER     = "admin"
RDS_PASSWORD = "YOUR_PASSWORD"
RDS_DB       = "qa_db"
# ──────────────────────────────────────────────────────────────────────────

COMMANDS = [
    ("pymysql 설치 확인",
     "pip show pymysql 2>&1 | grep Version"),
    ("RDS 연결 테스트 실행",
     f"RDS_HOST='{RDS_HOST}' RDS_USER='{RDS_USER}' "
     f"RDS_PASSWORD='{RDS_PASSWORD}' RDS_DB='{RDS_DB}' "
     f"python3 /home/ubuntu/qa-portfolio/day48_rds_test.py"),
]


def run_verify():
    print("=" * 55)
    print("  Day 48 RDS 연결 검증")
    print(f"  EC2  : {EC2_HOST}")
    print(f"  RDS  : {RDS_HOST}")
    print("=" * 55)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=EC2_HOST,
            username=EC2_USER,
            key_filename=KEY_PATH,
            timeout=10,
        )
        print("[EC2 연결 성공]\n")

        for label, cmd in COMMANDS:
            _, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode().strip()
            error  = stderr.read().decode().strip()
            result = output if output else error if error else "(출력 없음)"
            print(f"[{label}]")
            for line in result.splitlines():
                print(f"  {line}")
            print()

    except Exception as e:
        print(f"[연결 실패] {e}")
        sys.exit(1)

    finally:
        client.close()
        print("=" * 55)
        print("  검증 완료")
        print("=" * 55)


if __name__ == "__main__":
    run_verify()