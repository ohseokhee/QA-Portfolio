"""
Day 66 : mitmproxy 애드온 - 복호화된 요청·응답을 JSON Lines로 기록 (Fiddler 세션 목록·Inspectors 역할)
실행 예: mitmdump -p 8889 -s day66_capture_addon.py --set capture_file=day66_capture.jsonl
"""

import json

from mitmproxy import ctx, http


class Capture:
    def load(self, loader):
        loader.add_option("capture_file", str, "day66_capture.jsonl", "캡처 기록 파일 경로")

    def response(self, flow: http.HTTPFlow):
        record = {
            "scheme": flow.request.scheme,
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "request_headers": {k.lower(): v for k, v in flow.request.headers.items() if k.lower() in
                                ("authorization", "content-type", "idempotency-key")},
            "request_body": flow.request.get_text(strict=False) or "",
            "status": flow.response.status_code,
            "response_body": flow.response.get_text(strict=False) or "",
            "server_cert_cn": (flow.server_conn.certificate_list[0].cn
                               if flow.server_conn.certificate_list else None),
        }
        with open(ctx.options.capture_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


addons = [Capture()]
