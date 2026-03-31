"""
Day 49 : 로컬에서 RDS 마이그레이션 결과 검증
의존성: py -m pip install paramiko pymysql
⚠️ EC2 재시작 후 EC2_HOST 값 업데이트 필요
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


def check_rds_direct():
    """로컬에서 직접 RDS 조회 (퍼블릭 접근 활성화 시에만 가능)"""
    print("[RDS 직접 조회 시도]")
    try:
        conn = pymysql.connect(
            host=RDS_HOST, port=RDS_PORT,
            user=RDS_USER, password=RDS_PASSWORD,
            database=RDS_DB, connect_timeout=5,
        )
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"  테이블 목록: {[t[0] for t in tables]}")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  {table[0]}: {count}건")
        conn.close()
        print("  RDS 직접 조회 완료\n")
    except Exception as e:
        print(f"  RDS 직접 접근 불가 (퍼블릭 접근 비활성화 상태): {e}\n")


def check_via_ec2():
    """EC2 경유 RDS 조회"""
    print("[EC2 경유 RDS 조회]")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    COMMANDS = [
        ("마이그레이션 스크립트 실행",
         f"RDS_HOST='{RDS_HOST}' RDS_USER='{RDS_USER}' "
         f"RDS_PASSWORD='{RDS_PASSWORD}' RDS_DB='{RDS_DB}' "
         f"bash /home/ubuntu/qa-portfolio/day49_migrate.sh"),
        ("RDS search_results 조회",
         f"mysql -h {RDS_HOST} -P 3306 -u {RDS_USER} -p{RDS_PASSWORD} {RDS_DB} "
         f"-e 'SELECT browser, site, keyword, result_title FROM search_results LIMIT 5;'"),
    ]

    try:
        client.connect(hostname=EC2_HOST, username=EC2_USER,
                       key_filename=KEY_PATH, timeout=10)
        print("  EC2 연결 성공\n")

        for label, cmd in COMMANDS:
            _, stdout, stderr = client.exec_command(cmd, get_pty=True)
            output = stdout.read().decode().strip()
            print(f"  [{label}]")
            for line in output.splitlines():
                print(f"    {line}")
            print()

    except Exception as e:
        print(f"  EC2 연결 실패: {e}")
        sys.exit(1)
    finally:
        client.close()


def run():
    print("=" * 55)
    print("  Day 49 RDS 마이그레이션 검증")
    print(f"  EC2 : {EC2_HOST}")
    print(f"  RDS : {RDS_HOST}")
    print("=" * 55 + "\n")

    check_rds_direct()
    check_via_ec2()

    print("=" * 55)
    print("  검증 완료")
    print("=" * 55)


if __name__ == "__main__":
    run()
