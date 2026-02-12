import subprocess
import os
import time

def run_day35_mariadb_env():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(current_dir, "docker-compose.yml")
    env_file = os.path.join(current_dir, ".env")
    init_sql_file = os.path.join(current_dir, "init.sql")

    # .env 파일 생성
    print("[생성] .env 파일 작성 중...")
    env_content = """MYSQL_ROOT_PASSWORD=secureRootPass123!
MYSQL_DATABASE=testdb
MYSQL_USER=testuser
MYSQL_PASSWORD=secureUserPass456!
MYSQL_PORT=3307
"""
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    print("[확인] .env 파일 생성 완료")

    # init.sql 파일 생성
    print("\n[생성] init.sql 파일 작성 중...")
    init_sql_content = """CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_name VARCHAR(100) NOT NULL,
    status ENUM('PASS', 'FAIL', 'SKIP') NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, email) VALUES
    ('qa_engineer', 'qa@test.com'),
    ('dev_ops', 'devops@test.com');

INSERT INTO test_results (test_name, status) VALUES
    ('login_test', 'PASS'),
    ('network_test', 'PASS'),
    ('db_connection_test', 'PASS');
"""
    with open(init_sql_file, 'w', encoding='utf-8') as f:
        f.write(init_sql_content)
    print("[확인] init.sql 파일 생성 완료")

    # docker-compose.yml 생성
    print("\n[생성] docker-compose.yml 작성 중...")
    compose_content = """services:
  db:
    image: mariadb:10.6
    container_name: day35_db
    restart: always
    env_file:
      - .env
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "${MYSQL_PORT}:3306"
    volumes:
      - ./db_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - backend_network
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    image: python:3.10-slim
    container_name: day35_app
    restart: always
    networks:
      - backend_network
    depends_on:
      db:
        condition: service_healthy
    command: python -c "print('Day35 App Connected')"

networks:
  backend_network:
    driver: bridge
    name: day35_backend_net
"""
    with open(compose_file, 'w', encoding='utf-8') as f:
        f.write(compose_content)
    print("[확인] docker-compose.yml 생성 완료")

    # .gitignore 확인 및 .env 추가
    print("\n[보안] .gitignore에 .env 추가 중...")
    gitignore_file = os.path.join(current_dir, ".gitignore")
    gitignore_entries = [".env\n", "db_data/\n"]
    existing_content = ""
    if os.path.exists(gitignore_file):
        with open(gitignore_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    with open(gitignore_file, 'a', encoding='utf-8') as f:
        for entry in gitignore_entries:
            if entry.strip() not in existing_content:
                f.write(entry)
    print("[확인] .gitignore 보안 설정 완료 (.env, db_data/ 제외)")

    # 기존 컨테이너 정리
    print("\n[정리] 기존 컨테이너 제거 중...")
    subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"],
                   cwd=current_dir, check=False)

    # Docker Compose 실행
    print("\n[실행] MariaDB 컨테이너 환경 시작...")
    result = subprocess.run(["docker-compose", "-f", compose_file, "up", "-d"],
                            cwd=current_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print("[성공] 컨테이너 실행 완료")
    else:
        print(f"[오류] 실행 실패:\n{result.stderr}")
        return

    # 헬스체크 대기
    print("\n[대기] MariaDB 헬스체크 통과 대기 중...")
    for i in range(12):
        time.sleep(5)
        health = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", "day35_db"],
            capture_output=True, text=True
        )
        status = health.stdout.strip()
        print(f"  → 헬스 상태: {status} ({(i+1)*5}초 경과)")
        if status == "healthy":
            print("[확인] MariaDB 정상 기동 완료")
            break
    else:
        print("[경고] 헬스체크 타임아웃 - 수동 확인 필요")

    # DB 연결 및 쿼리 검증
    print("\n[검증] Python에서 MariaDB 연결 테스트...")
    try:
        import pymysql
        from dotenv import load_dotenv
        load_dotenv(env_file)

        conn = pymysql.connect(
            host='127.0.0.1',
            port=int(os.getenv('MYSQL_PORT', 3307)),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        print("\n[쿼리 1] users 테이블 조회")
        cursor.execute("SELECT * FROM users;")
        for row in cursor.fetchall():
            print(f"  → {row}")

        print("\n[쿼리 2] test_results 테이블 조회")
        cursor.execute("SELECT * FROM test_results;")
        for row in cursor.fetchall():
            print(f"  → {row}")

        print("\n[쿼리 3] PASS 결과 수 집계")
        cursor.execute("SELECT status, COUNT(*) FROM test_results GROUP BY status;")
        for row in cursor.fetchall():
            print(f"  → {row}")

        cursor.close()
        conn.close()
        print("\n[성공] DB 연결 및 쿼리 검증 완료")

    except ImportError:
        print("[안내] pymysql 미설치 - pip install pymysql 실행 후 재시도")
    except Exception as e:
        print(f"[오류] DB 연결 실패: {e}")

    # 보안 체크리스트 출력
    print("\n" + "=" * 60)
    print("[보안 체크리스트]")
    print("=" * 60)
    print(f"  .env 존재 여부        : {'✅' if os.path.exists(env_file) else '❌'}")
    gitignore_content = open(gitignore_file).read() if os.path.exists(gitignore_file) else ""
    print(f"  .env gitignore 등록   : {'✅' if '.env' in gitignore_content else '❌'}")
    print(f"  db_data gitignore 등록: {'✅' if 'db_data' in gitignore_content else '❌'}")
    print(f"  init.sql 존재 여부    : {'✅' if os.path.exists(init_sql_file) else '❌'}")

    print("\n[안내] 컨테이너 중지 명령어:")
    print(f"  → docker-compose -f {compose_file} down")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 35: MariaDB 컨테이너 구축 및 환경변수 보안 관리")
    print("=" * 60)
    run_day35_mariadb_env()