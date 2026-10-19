"""
Day 66 : 상점 페이지 포함 모의 게임 서버를 HTTPS로 실행
- day65_serve_client의 app(v1 + GET /shop)을 그대로 쓰고 TLS만 추가
- 인증서: day66_make_certs.py가 만든 로컬 CA 서명 서버 인증서
실행: py day66_https_server.py [--port 8443] [--no-reset]
"""

import argparse
import sys

import uvicorn

from day59_apply_schema import apply_schema
from day65_serve_client import app
from day66_make_certs import SERVER_CERT, SERVER_KEY, make_certs

sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--no-reset", action="store_true", help="fc_qa_lab 시드 초기화 생략")
    args = parser.parse_args()

    make_certs()
    if not args.no_reset:
        print("[준비] fc_qa_lab 시드 상태로 초기화")
        apply_schema()

    print(f"\n[서버] https://127.0.0.1:{args.port}/shop (종료: Ctrl+C)")
    uvicorn.run(app, host="127.0.0.1", port=args.port, ssl_certfile=SERVER_CERT, ssl_keyfile=SERVER_KEY)


if __name__ == "__main__":
    main()
