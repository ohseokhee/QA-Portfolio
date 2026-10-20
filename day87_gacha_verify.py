"""
Day 87 : 확률형 아이템 공시 확률 검증 (뽑기 로그 기반)
- 빌드(v1, v2)마다 10연차를 반복해 뽑기 로그를 만들고, 로그만 보고 공시 규칙을 판정
	C1 기본 확률: 확정 뽑기(천장·10연차 보장)를 뺀 일반 뽑기의 등급 분포를 공시 확률과 카이제곱 적합도 검정 (유의수준 0.001)
	C2 천장: SSR 사이 간격이 80회를 넘지 않고, 천장 확정은 정확히 80번째에서만 발생
	C3 10연차 보장: 모든 10연차에 SR 이상이 1개 이상
- 표본 수 1,000 / 10,000 / 100,000회로 같은 검증을 반복해 "몇 번 뽑아야 차이가 보이는지" 비교
- 결과: day87_gacha_report.md
실행: py day87_gacha_verify.py
"""

import math
import os
import sys

from day87_gacha import ANNOUNCED, GRADES, MULTI, PITY, GachaMachine

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = os.path.join(BASE_DIR, "day87_gacha_report.md")
SAMPLE_SIZES = [1_000, 10_000, 100_000]
ALPHA = 0.001
SEED = 87


# ============================================================
# 통계 함수 (표준 라이브러리만 사용)
# ============================================================

def _gammq(a, x):
    """정규화 상부 불완전 감마 함수 Q(a, x) (급수 / 연분수 전개)"""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        term = total = 1.0 / a
        ap = a
        for _ in range(1000):
            ap += 1
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return 1.0 - total * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c = 1 / 1e-300
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def chi2_sf(x, df):
    """카이제곱 분포 상위 확률 (p-value)"""
    return _gammq(df / 2, x / 2)


def chi_square(observed, expected_probs):
    n = sum(observed.values())
    stat = sum((observed[g] - n * p) ** 2 / (n * p) for g, p in expected_probs.items())
    return stat, chi2_sf(stat, len(expected_probs) - 1)


def wilson(k, n, z=2.5758):
    """비율 k/n의 99% 윌슨 신뢰구간"""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return center - half, center + half


def required_n(p0, p1, z_alpha=3.2905, z_beta=1.2816):
    """양측 유의수준 0.001, 검정력 90%로 p0와 p1의 차이를 잡는 데 필요한 표본 수"""
    num = z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p0 - p1)) ** 2)


# ============================================================
# 로그 판정
# ============================================================

def simulate(build, draws, seed=SEED):
    machine = GachaMachine(build, seed)
    for _ in range(draws // MULTI):
        machine.multi()
    return machine.log


def check_base_rate(log):
    normal = [e for e in log if e["forced"] is None]
    observed = {g: sum(1 for e in normal if e["grade"] == g) for g in GRADES}
    stat, p = chi_square(observed, ANNOUNCED)
    low, high = wilson(observed["SSR"], len(normal))
    return {"ok": p >= ALPHA, "n": len(normal), "observed": observed, "stat": stat, "p": p,
            "ssr_ci": (low, high), "ssr_rate": observed["SSR"] / len(normal)}


def check_pity(log):
    gaps, since, bad_pity = [], 0, []
    for e in log:
        since += 1
        if e["forced"] == "pity" and since != PITY:
            bad_pity.append(e["n"])
        if e["grade"] == "SSR":
            gaps.append(since)
            since = 0
    longest = max(gaps + [since])
    pity_count = sum(1 for e in log if e["forced"] == "pity")
    return {"ok": longest <= PITY and not bad_pity, "longest": longest, "pity_count": pity_count,
            "over": sum(1 for g in gaps if g > PITY), "bad_pity": bad_pity[:5]}


def check_multi(log):
    groups = {}
    for e in log:
        groups.setdefault(e["multi"], []).append(e["grade"])
    missing = [k for k, grades in groups.items() if all(g == "R" for g in grades)]
    return {"ok": not missing, "groups": len(groups), "missing": len(missing)}


def verdict(ok):
    return "PASS" if ok else "**FAIL**"


def main():
    print(f"[공시] SSR {ANNOUNCED['SSR']:.1%} / SR {ANNOUNCED['SR']:.1%} / R {ANNOUNCED['R']:.1%}, "
          f"천장 {PITY}회, 10연차 SR 이상 보장 / 유의수준 {ALPHA}, 시드 {SEED}")
    rows = []
    for build in ["v1", "v2"]:
        for n in SAMPLE_SIZES:
            log = simulate(build, n)
            base, pity, multi = check_base_rate(log), check_pity(log), check_multi(log)
            rows.append((build, n, base, pity, multi))
            obs = base["observed"]
            print(f"\n  [{build}] {n:,}회 (일반 뽑기 {base['n']:,}회)")
            print(f"    C1 기본 확률 {verdict(base['ok']).strip('*')}: SSR {obs['SSR'] / base['n']:.3%} "
                  f"SR {obs['SR'] / base['n']:.3%} R {obs['R'] / base['n']:.3%} / "
                  f"카이제곱 {base['stat']:.2f}, p={base['p']:.2e} / "
                  f"SSR 99% 구간 {base['ssr_ci'][0]:.3%}~{base['ssr_ci'][1]:.3%}")
            print(f"    C2 천장 {verdict(pity['ok']).strip('*')}: 최장 무SSR 구간 {pity['longest']}회, "
                  f"80회 초과 {pity['over']}건, 천장 확정 {pity['pity_count']}회")
            print(f"    C3 10연차 보장 {verdict(multi['ok']).strip('*')}: 10연차 {multi['groups']:,}회 중 "
                  f"SR 이상 없음 {multi['missing']}회")

    need = required_n(ANNOUNCED["SSR"], 0.012)
    print(f"\n[표본 수] SSR 1.5% vs 1.2% 차이를 잡으려면 일반 뽑기 약 {need:,}회 필요 "
          f"(양측 유의수준 0.001, 검정력 90%)")

    lines = [
        "# Day 87 확률형 아이템 공시 확률 검증 결과",
        "",
        f"> 공시: SSR {ANNOUNCED['SSR']:.1%} / SR {ANNOUNCED['SR']:.1%} / R {ANNOUNCED['R']:.1%}, "
        f"천장 {PITY}회(80번째 SSR 확정), 10연차 SR 이상 1개 보장. 10연차 반복 뽑기 로그로 판정, 시드 {SEED}, 유의수준 {ALPHA}",
        "",
        "| 빌드 | 뽑기 수 | 일반 뽑기 SSR | SSR 99% 구간 | 카이제곱 p | C1 기본 확률 | 최장 무SSR | C2 천장 | C3 10연차 보장 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for build, n, base, pity, multi in rows:
        lines.append(f"| {build} | {n:,} | {base['ssr_rate']:.3%} | {base['ssr_ci'][0]:.3%}~{base['ssr_ci'][1]:.3%} | "
                     f"{base['p']:.2e} | {verdict(base['ok'])} | {pity['longest']}회 | {verdict(pity['ok'])} | "
                     f"{verdict(multi['ok'])} |")
    lines += [
        "",
        f"- SSR 1.5% vs 1.2% 차이를 잡는 데 필요한 일반 뽑기 수: 약 {need:,}회 (양측 유의수준 0.001, 검정력 90%)",
        "- 일반 뽑기만 검정한 이유: 천장·10연차 보장으로 확정된 뽑기를 섞으면 실제 확률이 공시값보다 높게 나와 "
        "기본 확률 오류와 구분할 수 없음",
        "- 천장은 확률 검정이 아니라 규칙 검증(SSR 간 최대 간격)이라 표본이 적어도 천장 구간만 나오면 바로 판정 가능",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    fails = [(b, n) for b, n, base, pity, multi in rows if not (base["ok"] and pity["ok"] and multi["ok"])]
    print(f"\n[결과] {len(rows)}회 검증 중 FAIL {len(fails)}회 {fails} → {os.path.basename(REPORT_FILE)}")


if __name__ == "__main__":
    main()
