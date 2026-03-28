"""
Day 46 : 로컬에서 EC2 SSH 접속 및 Docker 설치 검증
의존성: pip install paramiko
"""

import paramiko
import sys

# ── 설정 (본인 환경에 맞게 수정) ─────────────────────────────────────────
EC2_HOST = "ec2-54-252-167-37.ap-southeast-2.compute.amazonaws.com"
EC2_USER = "ubuntu"                       # Ubuntu AMI 기본 유저
KEY_PATH = r"C:\Users\USER\OneDrive\바탕 화면\QAOps\qa-key.pem"
# ──────────────────────────────────────────────────────────────────────────

COMMANDS = [
    ("OS 정보 확인",       "lsb_release -a 2>/dev/null | grep Description"),
    ("Docker 버전 확인",   "docker --version"),
    ("Compose 버전 확인",  "docker-compose --version"),
    ("Docker 상태 확인",   "sudo systemctl is-active docker"),
]


def run_ssh_check():
    print("=" * 50)
    print(f"  EC2 SSH 접속 검증 시작")
    print(f"  Host : {EC2_HOST}")
    print(f"  User : {EC2_USER}")
    print("=" * 50)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=EC2_HOST,
            username=EC2_USER,
            key_filename=KEY_PATH,
            timeout=10,
        )
        print("[연결 성공]\n")

        for label, cmd in COMMANDS:
            stdin, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode().strip()
            error  = stderr.read().decode().strip()
            result = output if output else error if error else "(출력 없음)"
            print(f"[{label}]")
            print(f"  → {result}\n")

    except Exception as e:
        print(f"[연결 실패] {e}")
        sys.exit(1)

    finally:
        client.close()
        print("=" * 50)
        print("  검증 완료")
        print("=" * 50)


if __name__ == "__main__":
    run_ssh_check()