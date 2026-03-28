"""
Day 47 : 로컬에서 EC2 배포 결과 검증
의존성: py -m pip install paramiko
"""

import paramiko
import sys

EC2_HOST = "3.26.158.35"
EC2_USER = "ubuntu"
KEY_PATH = r"C:\Users\USER\PycharmProjects\QAOps\qa-key.pem"
REMOTE_DIR = "/home/ubuntu/qa-portfolio"

COMMANDS = [
    ("컨테이너 상태 확인",
     f"cd {REMOTE_DIR} && docker compose -f day47_docker-compose.yml ps"),
    ("pytest-runner 로그 확인",
     "docker logs pytest-runner 2>&1 | tail -20"),
    ("DB 저장 결과 확인",
     "docker exec qa-mariadb mariadb -u qa_user -pqa_pass qa_db "
     "-e 'SELECT browser, site, keyword, result_title FROM search_results;'"),
]


def run_verify():
    print("=" * 55)
    print("  Day 47 EC2 배포 결과 검증")
    print(f"  Host : {EC2_HOST}")
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
        print("[연결 성공]\n")

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