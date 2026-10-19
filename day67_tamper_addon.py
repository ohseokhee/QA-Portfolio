"""
Day 67 : mitmproxy 애드온 - 구매 요청 본문 변조 (Fiddler Breakpoint로 값을 고쳐 보내는 작업의 자동화판)
- tamper_file(JSON)의 "set" 값으로 POST /shop/purchase 본문 필드를 덮어쓴다. 파일이 비면 그대로 통과
- 변조 전·후 본문과 응답을 tamper_log(JSON Lines)에 기록
"""

import json
import os

from mitmproxy import ctx, http


class Tamper:
    def load(self, loader):
        loader.add_option("tamper_file", str, "day67_tamper.json", "변조 규칙 파일")
        loader.add_option("tamper_log", str, "day67_tamper_log.jsonl", "변조 기록 파일")

    def request(self, flow: http.HTTPFlow):
        if flow.request.method != "POST" or flow.request.path != "/shop/purchase":
            return
        rule = {}
        if os.path.exists(ctx.options.tamper_file):
            with open(ctx.options.tamper_file, encoding="utf-8") as f:
                rule = json.load(f)
        original = flow.request.get_text()
        body = json.loads(original)
        body.update(rule.get("set", {}))
        flow.request.set_text(json.dumps(body, ensure_ascii=False))
        flow.metadata["tamper"] = {"case": rule.get("case"), "original": original,
                                   "tampered": flow.request.get_text()}

    def response(self, flow: http.HTTPFlow):
        info = flow.metadata.get("tamper")
        if not info:
            return
        info.update(status=flow.response.status_code, response=flow.response.get_text(strict=False))
        with open(ctx.options.tamper_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(info, ensure_ascii=False) + "\n")


addons = [Tamper()]
