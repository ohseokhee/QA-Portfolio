"""
Day 65 : 상점 웹 페이지를 함께 제공하는 모의 게임 서버 실행
- day60_server_v1의 app에 GET /shop (day65_shop_client.html) 경로만 추가
- 기본 127.0.0.1:8000 바인딩. LDPlayer 브라우저는 Fiddler 프록시를 거쳐
  http://ipv4.fiddler:8000/shop 으로 접속 (Fiddler가 ipv4.fiddler를 PC의 127.0.0.1로 연결)
실행: py day65_serve_client.py [--host 0.0.0.0] [--no-reset]
"""

import argparse
import os
import sys

import uvicorn
from fastapi.responses import FileResponse

from day59_apply_schema import apply_schema
from day60_server_v1 import app

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_FILE = os.path.join(BASE_DIR, "day65_shop_client.html")


@app.get("/shop", include_in_schema=False)
def shop_page():
    return FileResponse(CLIENT_FILE, media_type="text/html; charset=utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reset", action="store_true", help="fc_qa_lab 시드 초기화 생략")
    args = parser.parse_args()

    if not args.no_reset:
        print("[준비] fc_qa_lab 시드 상태로 초기화")
        apply_schema()

    print(f"\n[서버] http://{args.host}:{args.port}/shop (종료: Ctrl+C)")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
