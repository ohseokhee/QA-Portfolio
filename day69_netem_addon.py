"""
Day 69 : mitmproxy 애드온 - 구매 요청 구간의 네트워크 불량 상태 흉내 (Clumsy 대체)
cond_file(JSON) {"run": 실행 ID, "cond": 조건}
- latency      : 서버는 즉시 처리, 응답만 latency_ms 늦게 전달 (클라이언트 타임아웃 유발)
- loss_request : 첫 요청을 서버에 보내기 전에 끊음 (요청 패킷 손실)
- loss_response: 첫 요청은 서버가 처리한 뒤 응답을 버리고 끊음 (응답 패킷 손실)
- reorder      : 요청을 hold_count개 모일 때까지 붙잡았다가 역순으로 한꺼번에 전달 (지연된 원 요청과 재시도가 뒤섞여 동시 도착)
                 앞서 붙잡힌 요청은 클라이언트가 타임아웃으로 끊어도 네트워크에 남아 있던 것처럼 프록시가 복제본을 서버에 보낸다
- flaky        : 처음 flaky_count개 응답을 끊음 (일시 끊김 후 복구)
"""

import asyncio
import json
import os

from mitmproxy import ctx, http

PURCHASE_PATH = "/shop/purchase"


class NetEm:
    def __init__(self):
        self.run = None
        self.seen = 0
        self.held = []

    def load(self, loader):
        loader.add_option("cond_file", str, "day69_cond.json", "네트워크 조건 파일")

    def _cond(self):
        if not os.path.exists(ctx.options.cond_file):
            return {"run": None, "cond": "none"}
        with open(ctx.options.cond_file, encoding="utf-8") as f:
            cond = json.load(f)
        if cond["run"] != self.run:  # 새 실행이면 카운터 초기화
            self.run, self.seen, self.held = cond["run"], 0, []
        return cond

    async def request(self, flow: http.HTTPFlow):
        if flow.request.path != PURCHASE_PATH or flow.is_replay == "request":
            return
        cond = self._cond()
        self.seen += 1
        flow.metadata["nth"] = self.seen
        if cond["cond"] == "loss_request" and self.seen == 1:
            flow.kill()
        elif cond["cond"] == "reorder":
            if len(self.held) + 1 < cond.get("hold_count", 3):
                event = asyncio.Event()
                self.held.append((event, flow.copy()))
                try:
                    await asyncio.wait_for(event.wait(), timeout=cond.get("hold_max_s", 6))
                except asyncio.TimeoutError:
                    pass
                flow.kill()  # 원래 연결은 클라이언트가 이미 끊음. 서버 전달은 아래 복제본이 담당
            else:
                # 마지막 요청은 그대로 진행하고, 앞서 붙잡힌 요청 복제본을 역순으로 동시에 서버에 보냄
                copies = [c for _, c in reversed(self.held)]
                ctx.master.commands.call("replay.client", copies)
                for event, _ in self.held:
                    event.set()
                self.held = []

    async def response(self, flow: http.HTTPFlow):
        if flow.request.path != PURCHASE_PATH or flow.is_replay == "request":
            return
        cond = self._cond()
        nth = flow.metadata.get("nth", 0)
        if cond["cond"] == "latency":
            await asyncio.sleep(cond.get("latency_ms", 1500) / 1000)
        elif cond["cond"] == "loss_response" and nth == 1:
            flow.kill()
        elif cond["cond"] == "flaky" and nth <= cond.get("flaky_count", 2):
            flow.kill()


addons = [NetEm()]
