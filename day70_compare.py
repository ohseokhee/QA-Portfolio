"""
Day 70 : 재시도 안전 처리 수정 전후 비교
1) Day 69 네트워크 조건 매트릭스를 서버 v2(수정 전)와 v3(수정 후)에 같은 클라이언트로 다시 실행
2) Day 63·64 DB 정합성·동시성 테스트를 v3에 실행 (기존 테스트 파일 수정 없이 서버 모듈만 교체)
3) 비교표를 day70_retry_compare.md로 저장
실행: py day70_compare.py
"""

import os
import socket
import subprocess
import sys

import pytest

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS = [("v2", "day68_server_v2.py", "day70_network_matrix_v2.md"),
        ("v3", "day70_server_v3.py", "day70_network_matrix_v3.md")]
os.environ["NO_PROXY"] = "127.0.0.1,localhost"


def assert_ports_free(*ports):
    for port in ports:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"[중단] 127.0.0.1:{port}에 이미 실행 중인 프로세스가 있습니다. 종료 후 다시 실행하세요.")


def run_matrix(label, server, out):
    print("=" * 20, f"[매트릭스] 서버 {label}: {server}", "=" * 20)
    result = subprocess.run([sys.executable, "day69_test_retry.py", "--server", server,
                             "--label", f"서버 {label}", "--out", out],
                            cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return parse_matrix(out)


def parse_matrix(path):
    rows = []
    with open(os.path.join(BASE_DIR, path), encoding="utf-8") as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 8 and cells[0] not in ("조건", "---"):
                rows.append({"cond": cells[0], "policy": cells[1], "attempts": cells[2], "client": cells[3],
                             "purchases": cells[4], "fc": cells[5], "inv": cells[6], "verdict": cells[7]})
    return rows


class _PopenV3(subprocess.Popen):
    """Day 63·64 테스트가 띄우는 'uvicorn day60_server_v1:app'을 v3로 바꿔 기동"""
    def __init__(self, args, *a, **kw):
        if isinstance(args, (list, tuple)):
            args = ["day70_server_v3:app" if x == "day60_server_v1:app" else x for x in args]
        super().__init__(args, *a, **kw)


def run_pytest_v3():
    print("=" * 20, "[회귀] Day 63·64 pytest → v3", "=" * 20)
    original = subprocess.Popen
    subprocess.Popen = _PopenV3
    try:
        return pytest.main(["day63_test_db_integrity.py", "day64_test_concurrency.py",
                            "-q", "--tb=line", "-rf", "-p", "no:cacheprovider"])
    finally:
        subprocess.Popen = original


def write_compare(v2_rows, v3_rows, pytest_code):
    lines = [
        "# Day 70 재시도 안전 처리 수정 전후 비교",
        "",
        "> 같은 클라이언트(`day69_test_retry.py`: 타임아웃 1초, 최대 3회, Idempotency-Key 헤더 = request_id)로 "
        "서버 v2(request_id 순차 중복 검사)와 v3(Idempotency-Key 선점 + 트랜잭션·행 잠금)를 비교. "
        "기대값: 구매 이력 1건 / FC -1000 / 인벤토리 +1",
        "",
        "| 조건 | 재시도 방식 | v2 구매·FC·인벤토리 | v2 판정 | v3 시도 결과 | v3 구매·FC·인벤토리 | v3 판정 |",
        "|---|---|---|---|---|---|---|",
    ]
    for a, b in zip(v2_rows, v3_rows):
        lines.append(f"| {a['cond']} | {a['policy']} | {a['purchases']} / {a['fc']} / {a['inv']} | {a['verdict']} | "
                     f"{b['attempts']} | {b['purchases']} / {b['fc']} / {b['inv']} | {b['verdict']} |")
    count = lambda rows: sum(r["verdict"] == "PASS" for r in rows)
    same = lambda rows: [r for r in rows if r["policy"] == "same-id"]
    lines += [
        "",
        f"- 전체: v2 {count(v2_rows)}/{len(v2_rows)} PASS → v3 {count(v3_rows)}/{len(v3_rows)} PASS",
        f"- same-id(같은 키로 재시도): v2 {count(same(v2_rows))}/{len(same(v2_rows))} → "
        f"v3 {count(same(v3_rows))}/{len(same(v3_rows))}",
        "- new-id(재시도마다 새 키): 서버는 서로 다른 구매로 볼 수밖에 없음 → 클라이언트가 구매 의도 단위로 키를 한 번 만들고 "
        "재시도에 재사용해야 함 (클라이언트 요구사항)",
        f"- Day 63·64 pytest(v3) 종료 코드: {int(pytest_code)} (0 = 전체 통과)",
    ]
    with open(os.path.join(BASE_DIR, "day70_retry_compare.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[4:]))


if __name__ == "__main__":
    assert_ports_free(8000, 8443, 8889)
    results = {label: run_matrix(label, server, out) for label, server, out in RUNS}
    code = run_pytest_v3()
    print("\n" + "=" * 20, "[비교] day70_retry_compare.md", "=" * 20)
    write_compare(results["v2"], results["v3"], code)
