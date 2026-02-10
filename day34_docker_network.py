import subprocess
import os
import time

def run_day34_docker_network():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.join(current_dir, "docker-compose.yml")

    # Docker Network 설정 추가
    compose_content = """services:
  frontend:
    image: nginx:alpine
    container_name: day34_frontend
    networks:
      - frontend_network
    ports:
      - "8080:80"
    restart: always

  backend:
    image: python:3.10-slim
    container_name: day34_backend
    networks:
      - frontend_network
      - backend_network
    command: python -m http.server 8000
    restart: always

  db:
    image: mariadb:10.6
    container_name: day34_db
    networks:
      - backend_network
    environment:
      MYSQL_ROOT_PASSWORD: rootpass123
      MYSQL_DATABASE: testdb
    restart: always

networks:
  frontend_network:
    driver: bridge
    name: day34_frontend_net
  backend_network:
    driver: bridge
    name: day34_backend_net
"""
    
    # docker-compose.yml 파일 생성
    print("[생성] docker-compose.yml 작성 중...")
    with open(compose_file, 'w', encoding='utf-8') as f:
        f.write(compose_content)
    print("[확인] docker-compose.yml 생성 완료")
    
    # 기존 컨테이너 정리
    print("\n[정리] 기존 컨테이너 및 네트워크 제거 중...")
    subprocess.run(["docker-compose", "-f", compose_file, "down", "-v"], 
                   cwd=current_dir, check=False)
    
    # Docker Compose 실행
    print("\n[실행] Docker Network 환경 시작...")
    result = subprocess.run(["docker-compose", "-f", compose_file, "up", "-d"], 
                          cwd=current_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("[성공] 모든 컨테이너 실행 완료\n")
    else:
        print(f"[오류] Docker Compose 실행 실패:\n{result.stderr}")
        return
    
    # 네트워크 구조 확인
    time.sleep(5)
    
    print("=" * 60)
    print("[검증 1] 네트워크 목록 확인")
    print("=" * 60)
    subprocess.run(["docker", "network", "ls"])
    
    print("\n" + "=" * 60)
    print("[검증 2] frontend_network 상세 정보")
    print("=" * 60)
    subprocess.run(["docker", "network", "inspect", "day34_frontend_net"])
    
    print("\n" + "=" * 60)
    print("[검증 3] backend_network 상세 정보")
    print("=" * 60)
    subprocess.run(["docker", "network", "inspect", "day34_backend_net"])
    
    # 컨테이너 간 통신 테스트
    print("\n" + "=" * 60)
    print("[검증 4] 네트워크 격리 테스트")
    print("=" * 60)
    
    print("\n[테스트 1] Frontend → Backend 통신 (성공 예상)")
    result_fb = subprocess.run(
        ["docker", "exec", "day34_frontend", "ping", "-c", "3", "day34_backend"],
        capture_output=True, text=True
    )
    if result_fb.returncode == 0:
        print("✅ Frontend에서 Backend 접근 가능 (같은 네트워크)")
    else:
        print("❌ 통신 실패")
    
    print("\n[테스트 2] Frontend → DB 통신 (실패 예상)")
    result_fd = subprocess.run(
        ["docker", "exec", "day34_frontend", "ping", "-c", "3", "day34_db"],
        capture_output=True, text=True
    )
    if result_fd.returncode == 0:
        print("⚠️  Frontend에서 DB 접근 가능 (보안 문제)")
    else:
        print("✅ Frontend에서 DB 접근 차단됨 (네트워크 격리 성공)")
    
    print("\n[테스트 3] Backend → DB 통신 (성공 예상)")
    result_bd = subprocess.run(
        ["docker", "exec", "day34_backend", "ping", "-c", "3", "day34_db"],
        capture_output=True, text=True
    )
    if result_bd.returncode == 0:
        print("✅ Backend에서 DB 접근 가능 (같은 네트워크)")
    else:
        print("❌ 통신 실패")
    
    # 최종 요약
    print("\n" + "=" * 60)
    print("[최종 결과] Docker Network 격리 구조")
    print("=" * 60)
    print("""
    ┌─────────────────────────────────────────────┐
    │         Docker Network 아키텍처             │
    ├─────────────────────────────────────────────┤
    │                                             │
    │  [frontend_network]      [backend_network]  │
    │         │                       │           │
    │    ┌────┴────┐            ┌─────┴──────┐   │
    │    │ Frontend│────────────│  Backend   │   │
    │    │ (Nginx) │            │  (Python)  │   │
    │    └─────────┘            └─────┬──────┘   │
    │                                 │           │
    │                           ┌─────┴──────┐   │
    │                           │     DB     │   │
    │                           │  (MariaDB) │   │
    │                           └────────────┘   │
    │                                             │
    │  ✅ Frontend ↔ Backend (통신 가능)          │
    │  ❌ Frontend ↔ DB (통신 차단)               │
    │  ✅ Backend ↔ DB (통신 가능)                │
    │                                             │
    └─────────────────────────────────────────────┘
    """)
    
    print("\n[안내] 컨테이너 중지 명령어:")
    print(f"  → docker-compose -f {compose_file} down")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 34: Docker Network - 컨테이너 간 독립 통신망 구축")
    print("=" * 60)
    run_day34_docker_network()
