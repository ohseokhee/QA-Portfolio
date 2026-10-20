"""
Day 86 : API 회귀 테스트 CI 실행기 (GitHub Actions와 로컬 공용)
- 게이트 1: 서버 v3에 Day 63·64 DB 정합성·동시성 테스트 → 전부 통과해야 함
- 게이트 2: 서버 v1(결함 시딩)에 같은 테스트 → 시딩 결함을 계속 잡아내는지 확인 (실패 수가 줄면 테스트가 약해진 것)
	- Day 63(DB 대조): 결정적 결함이라 매번 3건 실패해야 함
	- Day 64(동시성): 경쟁 상태라 실행 환경(CPU 수)에 따라 재현 여부가 달라짐 → 최대 10회 반복,
	  시딩 결함 D5(갱신 손실)·D6(중복 지급)을 잡는 DB 검증 테스트가 각각 한 번 이상 실패해야 함 (응답 검증 테스트는 참고)
- 게이트 3: DB 없이 도는 단위 테스트 (Day 80 판별 로직, Day 87 확률 검증)
- JUnit XML은 ci-results/, 요약은 GITHUB_STEP_SUMMARY(있을 때)와 콘솔에 출력
실행: py day86_ci_run.py
"""

import os
import socket
import subprocess
import sys

import pytest

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(BASE_DIR, "ci-results")
DB_TESTS = ["day63_test_db_integrity.py", "day64_test_concurrency.py"]
UNIT_TESTS = ["day80_test_kbo_lookup.py", "day87_test_gacha.py"]
V1_DB_FAILURES = 3          # Day 64 봉인 해제 기준: Day 63 3건
CONCURRENCY_REQUIRED = {  # 시딩 결함별로 반드시 잡혀야 하는 테스트
    "day64_test_concurrency.py::test_tc_shop_18_overspend": "D5 갱신 손실",
    "day64_test_concurrency.py::test_tc_shop_17_same_request_id_db": "D6 중복 지급",
}
CONCURRENCY_RETRIES = 10  # GitHub 러너(2코어)에서 회차당 탐지 1~2건으로 들쭉날쭉 → 넉넉히 반복, 다 잡히면 즉시 중단
os.environ["NO_PROXY"] = "127.0.0.1,localhost"


class Counter:
    """pytest 플러그인: 테스트 결과 수집"""
    def __init__(self):
        self.passed, self.failed = [], []

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            (self.passed if report.outcome == "passed" else self.failed).append(report.nodeid)


def swap_server(module):
    """테스트가 띄우는 'uvicorn day60_server_v1:app'을 다른 서버 모듈로 바꾸는 Popen"""
    class _Popen(subprocess.Popen):
        def __init__(self, args, *a, **kw):
            if isinstance(args, (list, tuple)):
                args = [f"{module}:app" if x == "day60_server_v1:app" else x for x in args]
            super().__init__(args, *a, **kw)
    return _Popen


def run(name, files, server=None):
    counter = Counter()
    original = subprocess.Popen
    if server:
        subprocess.Popen = swap_server(server)
    try:
        pytest.main(files + ["-q", "--tb=line", "-p", "no:cacheprovider",
                             f"--junitxml={os.path.join(RESULT_DIR, name + '.xml')}"], plugins=[counter])
    finally:
        subprocess.Popen = original
    return counter


def assert_port_free(port):
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            sys.exit(f"[중단] 127.0.0.1:{port}에 이미 실행 중인 프로세스가 있습니다.")


def main():
    assert_port_free(8000)
    os.makedirs(RESULT_DIR, exist_ok=True)
    gates = []

    print("=" * 16, "[게이트 1] 서버 v3 + Day 63·64 (전부 통과)", "=" * 16)
    v3 = run("v3_db", DB_TESTS, "day70_server_v3")
    gates.append(("서버 v3 DB 정합성·동시성", f"{len(v3.passed)} passed, {len(v3.failed)} failed",
                  "실패 0", not v3.failed and v3.passed))

    print("=" * 16, f"[게이트 2-1] 서버 v1 + Day 63 (결정적 결함 {V1_DB_FAILURES}건 탐지)", "=" * 16)
    v1 = run("v1_db", DB_TESTS[:1])
    gates.append(("서버 v1 DB 대조 결함 탐지", f"{len(v1.passed)} passed, {len(v1.failed)} failed",
                  f"실패 {V1_DB_FAILURES}", len(v1.failed) == V1_DB_FAILURES))

    detected, tries = set(), []
    for attempt in range(1, CONCURRENCY_RETRIES + 1):
        print("=" * 16, f"[게이트 2-2] 서버 v1 + Day 64 동시성 ({attempt}/{CONCURRENCY_RETRIES}회차)", "=" * 16)
        rep = run(f"v1_concurrency_{attempt}", DB_TESTS[1:])
        detected |= set(rep.failed)
        tries.append(len(rep.failed))
        if set(CONCURRENCY_REQUIRED) <= detected:
            break
    v1.failed += sorted(detected)
    missing = [d for t, d in CONCURRENCY_REQUIRED.items() if t not in detected]
    gates.append(("서버 v1 동시성 결함 탐지", f"회차별 실패 {tries}, 누적 탐지 {len(detected)}건"
                  + (f", 미탐지 {missing}" if missing else ""),
                  f"D5·D6 각 1회 이상 ({CONCURRENCY_RETRIES}회 안)", not missing))

    print("=" * 16, "[게이트 3] 단위 테스트 (DB 불필요)", "=" * 16)
    unit = run("unit", UNIT_TESTS)
    gates.append(("단위 테스트", f"{len(unit.passed)} passed, {len(unit.failed)} failed",
                  "실패 0", not unit.failed and unit.passed))

    lines = ["## API 회귀 테스트 결과", "", "| 게이트 | 결과 | 기대 | 판정 |", "|---|---|---|---|"]
    lines += [f"| {g} | {r} | {e} | {'PASS' if ok else 'FAIL'} |" for g, r, e, ok in gates]
    if v1.failed:
        lines += ["", "서버 v1에서 실패한 테스트 (시딩 결함 탐지):", ""] + [f"- `{n.split('[')[0]}`" for n in v1.failed]
    summary = "\n".join(lines)
    print("\n" + summary)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    failed = [g for g, _, _, ok in gates if not ok]
    print(f"\n[결과] 게이트 {len(gates)}개 중 통과 {len(gates) - len(failed)}개" + (f", 실패: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
