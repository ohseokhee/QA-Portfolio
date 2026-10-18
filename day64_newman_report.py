"""
Day 64 : Day 61~62 컬렉션 Newman 일괄 실행 + HTML 리포트 (Day 58 htmlextra 방식 재사용)
의존성: npm install -g newman newman-reporter-htmlextra (Day 58에 설치)
컬렉션마다 DB 초기화·서버 기동 → newman (cli, htmlextra, json) → 서버 종료
→ json 결과로 요약 리포트 day64_newman_report.html 생성 (상세는 day64-report/*.html)
"""

import html
import json
import os
import subprocess
import sys
from datetime import datetime

from day59_apply_schema import apply_schema
from day60_smoke_check import wait_for_server
from day62_run_negative import prepare_state

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = "day64-report"
SUMMARY_FILE = "day64_newman_report.html"
RUNS = [
    {"name": "day61", "title": "Day 61 정상 흐름", "collection": "day61_collection.json",
     "data": None, "prepare": False},
    {"name": "day62", "title": "Day 62 부정·경계값 (CSV 데이터 주도)", "collection": "day62_negative_collection.json",
     "data": "day62_negative_cases.csv", "prepare": True},
]


def run_collection(run):
    print(f"\n===== {run['title']} =====")
    apply_schema()
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "day60_server_v1:app",
                               "--host", "127.0.0.1", "--port", "8000"],
                              cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_server()
        cmd = ["newman", "run", run["collection"], "-e", "day61_environment.json",
               "-r", "cli,htmlextra,json",
               "--reporter-htmlextra-export", f"{REPORT_DIR}/{run['name']}.html",
               "--reporter-htmlextra-title", run["title"],
               "--reporter-json-export", f"{REPORT_DIR}/{run['name']}.json",
               "--color", "off"]
        if run["data"]:
            cmd += ["-d", run["data"]]
        if run["prepare"]:
            expired_token, expiring_token = prepare_state()
            cmd += ["--env-var", f"expired_token={expired_token}",
                    "--env-var", f"expiring_token={expiring_token}"]
        print(f"newman run {run['collection']}" + (f" -d {run['data']}" if run["data"] else ""))
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, shell=True,
                                encoding="utf-8", errors="replace")
        # 콘솔에는 결과 집계 표부터 출력 (요청별 상세는 HTML 리포트에 있음)
        stdout = result.stdout
        print(stdout[stdout.find("┌"):] if "┌" in stdout else stdout)
    finally:
        server.terminate()
        server.wait(timeout=10)
    return result.returncode


def load_summary(run):
    with open(os.path.join(BASE_DIR, REPORT_DIR, f"{run['name']}.json"), encoding="utf-8") as f:
        data = json.load(f)["run"]
    stats = data["stats"]
    failures = [{
        "iteration": f["cursor"].get("iteration", 0) + 1,
        "request": f["source"].get("name", ""),
        "test": f["error"].get("test", ""),
        "message": f["error"].get("message", ""),
    } for f in data["failures"]]
    return {
        "title": run["title"], "name": run["name"],
        "iterations": stats["iterations"], "requests": stats["requests"], "assertions": stats["assertions"],
        "failures": failures,
    }


def write_summary_html(summaries):
    rows = "".join(
        f"<tr><td>{html.escape(s['title'])}</td><td>{s['iterations']['total']}</td>"
        f"<td>{s['requests']['total']}</td><td>{s['assertions']['total']}</td>"
        f"<td class='{'fail' if s['assertions']['failed'] else 'pass'}'>{s['assertions']['failed']}</td>"
        f"<td><a href='{REPORT_DIR}/{s['name']}.html'>{s['name']}.html</a></td></tr>"
        for s in summaries)
    failure_rows = "".join(
        f"<tr><td>{html.escape(s['name'])}</td><td>{f['iteration']}</td><td>{html.escape(f['request'])}</td>"
        f"<td>{html.escape(f['test'])}</td><td>{html.escape(f['message'])}</td></tr>"
        for s in summaries for f in s["failures"]) or "<tr><td colspan='5'>없음</td></tr>"
    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Day 64 Newman 일괄 실행 리포트</title>
<style>
body {{ font-family: sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; margin-bottom: 24px; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 14px; }}
th {{ background: #f0f0f0; }}
.pass {{ color: #1a7f37; font-weight: bold; }}
.fail {{ color: #cf222e; font-weight: bold; }}
</style></head><body>
<h1>모의 게임 서버 API 테스트 일괄 실행 (Newman)</h1>
<p>생성: {datetime.now():%Y-%m-%d %H:%M:%S} · 서버: day60_server_v1 · 명세: day59_api_spec.md</p>
<h2>컬렉션별 결과</h2>
<table><tr><th>컬렉션</th><th>iteration</th><th>요청</th><th>assertion</th><th>실패</th><th>상세 리포트</th></tr>{rows}</table>
<h2>실패한 assertion</h2>
<table><tr><th>컬렉션</th><th>iteration</th><th>요청</th><th>테스트</th><th>메시지</th></tr>{failure_rows}</table>
</body></html>
"""
    with open(os.path.join(BASE_DIR, SUMMARY_FILE), "w", encoding="utf-8") as f:
        f.write(page)


def run():
    codes = {r["name"]: run_collection(r) for r in RUNS}
    print("\nfc_qa_lab 시드 상태로 재초기화")
    apply_schema()

    summaries = [load_summary(r) for r in RUNS]
    write_summary_html(summaries)
    print(f"\n[요약 리포트] {SUMMARY_FILE}")
    for s in summaries:
        print(f"  {s['name']}: iteration {s['iterations']['total']}, 요청 {s['requests']['total']}, "
              f"assertion {s['assertions']['total']} (실패 {s['assertions']['failed']}), "
              f"newman 종료 코드 {codes[s['name']]}")
    print(f"  상세: {REPORT_DIR}/day61.html, {REPORT_DIR}/day62.html")


if __name__ == "__main__":
    run()
