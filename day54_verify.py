"""
Day 54 : EC2 경유 재생성 RDS 최종 저장 결과 검증
의존성: py -m pip install paramiko
⚠️ RDS는 퍼블릭 액세스가 비활성화되어 있어 EC2를 경유해 python3 인라인 쿼리로 확인
"""

import os
import sys

import paramiko

EC2_HOST = "3.26.158.35"
EC2_USER = "ubuntu"
KEY_PATH = r"C:\Users\USER\PycharmProjects\QAOps\qa-key.pem"

RDS_HOST     = "qa-portfolio-rds.cz0euwqk8xws.ap-southeast-2.rds.amazonaws.com"
RDS_PORT     = 3306
RDS_USER     = "admin"
RDS_PASSWORD = os.environ.get("RDS_PASSWORD", "YOUR_PASSWORD")
RDS_DB       = "qa_db"

PY_QUERY = (
    "import pymysql; "
    f"c = pymysql.connect(host='{RDS_HOST}', port={RDS_PORT}, user='{RDS_USER}', "
    f"password='{RDS_PASSWORD}', database='{RDS_DB}'); "
    "cur = c.cursor(); "
    "cur.execute(\\\"SELECT id, browser, site, keyword, result_title FROM search_results ORDER BY id DESC LIMIT 5\\\"); "
    "rows = cur.fetchall(); "
    "[print(f'  id={r[0]} | {r[1]} | {r[2]} | {r[4]}') for r in rows]; "
    "print(f'[총 저장 건수] {len(rows)}건 조회됨')"
)


def run():
    print("=" * 55)
    print("  Day 54 재생성 RDS 최종 저장 결과 검증")
    print(f"  EC2 : {EC2_HOST}")
    print(f"  RDS : {RDS_HOST}")
    print("=" * 55 + "\n")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=EC2_HOST, username=EC2_USER, key_filename=KEY_PATH, timeout=10)
        print("[EC2 연결 성공]\n")

        _, stdout, stderr = client.exec_command(f'python3 -c "{PY_QUERY}"')
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        print("[RDS 최종 데이터 확인]")
        for line in output.splitlines():
            print(f"  {line}")
        if error:
            print(f"  [stderr] {error}")

        assert "총 저장 건수" in output, "RDS 조회 결과를 확인할 수 없음"
        assert "0건 조회됨" not in output, "RDS에 저장된 데이터가 없음"

    except Exception as e:
        print(f"[검증 실패] {e}")
        sys.exit(1)
    finally:
        client.close()

    print("\n" + "=" * 55)
    print("  검증 완료: EC2 -> Grid -> RDS 전체 플로우 정상 동작 확인")
    print("=" * 55)


if __name__ == "__main__":
    run()
