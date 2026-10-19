"""
Day 68 : mitmproxy 애드온 - 구매 요청에 미리 정한 응답 돌려주기 (Fiddler AutoResponder 자동화판)
mode_file(JSON)의 "mode":
- none        : 그대로 통과
- error500    : 서버로 보내지 않고 500 응답
- maintenance : 서버로 보내지 않고 503 점검 응답 (Retry-After 포함)
- delay       : 서버는 처리하고, 응답만 delay_seconds 동안 붙잡았다가 전달
"""

import asyncio
import json
import os

from mitmproxy import ctx, http

PURCHASE_PATH = "/shop/purchase"


class AutoResponder:
    def load(self, loader):
        loader.add_option("mode_file", str, "day68_mode.json", "응답 조작 모드 파일")

    def _mode(self):
        if not os.path.exists(ctx.options.mode_file):
            return {"mode": "none"}
        with open(ctx.options.mode_file, encoding="utf-8") as f:
            return json.load(f)

    def request(self, flow: http.HTTPFlow):
        if flow.request.path != PURCHASE_PATH:
            return
        mode = self._mode()
        if mode["mode"] == "error500":
            flow.response = http.Response.make(
                500, json.dumps({"error_code": "INTERNAL_ERROR", "message": "Internal Server Error"}),
                {"Content-Type": "application/json"})
        elif mode["mode"] == "maintenance":
            flow.response = http.Response.make(
                503, json.dumps({"error_code": "MAINTENANCE", "message": "서버 점검 중입니다. 18:00 이후 이용해 주세요."},
                                ensure_ascii=False),
                {"Content-Type": "application/json; charset=utf-8", "Retry-After": "3600"})

    async def response(self, flow: http.HTTPFlow):
        if flow.request.path != PURCHASE_PATH:
            return
        mode = self._mode()
        if mode["mode"] == "delay":
            await asyncio.sleep(mode.get("delay_seconds", 5))


addons = [AutoResponder()]
