"""
Day 68 : 서버 v2 회귀 실행 - Day 61~64 테스트와 Day 67 변조 케이스를 v2에 그대로 다시 돌린다
- 기존 테스트 파일은 수정하지 않고, 하위 프로세스 기동 명령의 서버 모듈만 day60_server_v1 → day68_server_v2로 바꿔 실행
- Day 61·62 Newman: day64_newman_report 재사용 (리포트는 day68-report/, day68_regression_newman.html)
- Day 63·64 pytest: DB 정합성·동시성 테스트
- Day 67 변조 케이스: day67_tamper_test.py --server day68_server_v2.py
실행: py day68_regression.py
"""

import os
import subprocess
import sys

import pytest

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
V1, V2 = "day60_server_v1:app", "day68_server_v2:app"

# Fiddler 등 시스템 프록시를 거치지 않게 (기존 테스트의 requests·urllib 대상)
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

_Popen = subprocess.Popen


class _PopenV2(_Popen):
    """기존 스크립트가 띄우는 'uvicorn day60_server_v1:app'을 v2로 바꿔 기동"""
    def __init__(self, args, *a, **kw):
        if isinstance(args, (list, tuple)):
            args = [V2 if x == V1 else x for x in args]
        super().__init__(args, *a, **kw)


subprocess.Popen = _PopenV2

import day64_newman_report as newman_report  # noqa: E402  (Popen 교체 후 import)


def assert_ports_free(*ports):
    """이미 떠 있는 서버가 있으면 새 서버가 바인딩에 실패하고 테스트가 엉뚱한 서버로 가므로 먼저 확인"""
    import socket
    for port in ports:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"[중단] 127.0.0.1:{port}에 이미 실행 중인 프로세스가 있습니다. 종료 후 다시 실행하세요.")


def run_newman():
    print("=" * 20, "[A] Day 61·62 Newman 컬렉션 → v2", "=" * 20)
    newman_report.REPORT_DIR = "day68-report"
    newman_report.SUMMARY_FILE = "day68_regression_newman.html"
    os.makedirs(os.path.join(BASE_DIR, "day68-report"), exist_ok=True)
    newman_report.run()
    path = os.path.join(BASE_DIR, newman_report.SUMMARY_FILE)
    with open(path, encoding="utf-8") as f:
        page = f.read().replace("서버: day60_server_v1", "서버: day68_server_v2 (회귀)")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def run_pytest():
    print("\n" + "=" * 20, "[B] Day 63·64 pytest → v2", "=" * 20)
    return pytest.main(["day63_test_db_integrity.py", "day64_test_concurrency.py",
                        "-q", "--tb=line", "-rf", "-p", "no:cacheprovider"])


def run_tamper():
    print("\n" + "=" * 20, "[C] Day 67 요청 변조 케이스 → v2", "=" * 20)
    result = _run([sys.executable, "day67_tamper_test.py", "--server", "day68_server_v2.py",
                   "--out", "day68_tamper_cases_v2.md"])
    print(result.stdout)


def _run(cmd):
    return subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")


if __name__ == "__main__":
    assert_ports_free(8000, 8443, 8889)
    run_newman()
    code = run_pytest()
    run_tamper()
    print(f"[완료] pytest 종료 코드 {int(code)}")
