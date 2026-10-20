"""ADB 메모리 측정: dumpsys meminfo + /proc/<pid>/status → CSV·그래프·요약 리포트

사용
  py day81_mem_measure.py --package com.android.settings --label lobby --count 5
  py day81_mem_measure.py --demo     (기기 없이 합성 데이터로 파싱·집계·그래프 검증, 실측 아님)
"""
import argparse
import csv
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SUMMARY_KEYS = {
    "Java Heap": "java_heap",
    "Native Heap": "native_heap",
    "Code": "code",
    "Stack": "stack",
    "Graphics": "graphics",
    "Private Other": "private_other",
    "System": "system",
}
FIELDS = ["t_sec", "label", "total_pss", "total_rss", "swap_pss", "rss_anon", "vm_swap", "anon_swap",
          "native_alloc", "dalvik_alloc", "heap_alloc", *SUMMARY_KEYS.values()]
LEAK_RATE = 0.05        # 같은 화면(로비) 복귀 값이 처음보다 5% 이상 늘고
TAIL_RATE = 0.02        # 최근 복귀 5회 구간에서도 2% 이상 계속 오르면 누수 의심 (평탄하면 증가 후 안정 = 캐시 추정)
TAIL_COUNT = 5
BG_RELEASE_RATE = 0.20  # 백그라운드 전환 후 직전 로비보다 20% 이상 내려가야 해제로 판단
ADB = "adb"             # PATH에 없으면 --adb로 경로 지정 (예: C:/LDPlayer/LDPlayer14/adb.exe)


def parse_meminfo(text):
    """dumpsys meminfo <패키지>의 App Summary 구간 + 상세 표 Heap Alloc 열 → KB 단위 dict"""
    total = re.search(r"^\s*TOTAL(?: PSS)?:\s+(\d+)", text, re.M)
    if not total:
        raise ValueError("meminfo 형식이 아님: " + text.strip()[:80])
    row = {"total_pss": int(total.group(1))}
    for label, key in SUMMARY_KEYS.items():
        m = re.search(rf"^\s*{label}:\s+(\d+)", text, re.M)
        row[key] = int(m.group(1)) if m else 0
    rss = re.search(r"TOTAL RSS:\s+(\d+)", text)
    swap = re.search(r"TOTAL SWAP (?:PSS|\(KB\)):\s+(\d+)", text)  # 안드로이드 14는 "TOTAL SWAP (KB):"
    row["total_rss"] = int(rss.group(1)) if rss else 0
    row["swap_pss"] = int(swap.group(1)) if swap else 0
    # 상세 표 행의 마지막 세 값 = Heap Size / Heap Alloc / Heap Free (에뮬레이터는 Summary 힙 PSS가 0이어도 이 값은 나옴)
    for name, key in (("Native Heap", "native_alloc"), ("Dalvik Heap", "dalvik_alloc")):
        m = re.search(rf"^\s*{name}((?:\s+\d+){{7,8}})\s*$", text, re.M)
        row[key] = int(m.group(1).split()[-2]) if m else 0
    row["heap_alloc"] = row["native_alloc"] + row["dalvik_alloc"]
    return row


def parse_status(text):
    """/proc/<pid>/status → RssAnon·VmSwap (KB). 구글 플레이 동적 메모리 = Anonymous RSS + swap"""
    row = {}
    for name, key in (("RssAnon", "rss_anon"), ("VmSwap", "vm_swap")):
        m = re.search(rf"^{name}:\s+(\d+) kB", text, re.M)
        row[key] = int(m.group(1)) if m else 0
    row["anon_swap"] = row["rss_anon"] + row["vm_swap"]
    return row


def adb(serial, *args):
    cmd = [ADB] + (["-s", serial] if serial else []) + list(args)
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    return out.stdout


def connected_devices():
    lines = adb(None, "devices").splitlines()[1:]
    return [ln.split()[0] for ln in lines if ln.strip().endswith("device")]


def device_sample(serial, package):
    pids = adb(serial, "shell", "pidof", package).split()
    if not pids:
        raise RuntimeError(f"{package} 프로세스가 없음 (앱 실행 후 다시 측정)")
    return adb(serial, "shell", "dumpsys", "meminfo", package), adb(serial, "shell", "cat", f"/proc/{pids[0]}/status")


DEMO_PHASES = [("lobby", 5), ("battle1", 5), ("lobby_after1", 3), ("battle2", 5), ("lobby_after2", 3),
               ("battle3", 5), ("lobby_after3", 3), ("background", 4), ("foreground", 3)]
MEMINFO_TEMPLATE = """Applications Memory Usage (in Kilobytes):
Uptime: 5123456 Realtime: 5123456

** MEMINFO in pid 4321 [demo.game] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap   {native_heap:>6}   {native_heap:>6}        0        0   {native_heap:>6}   {native_size:>6}   {native_alloc:>6}   {native_free:>6}
  Dalvik Heap   {java_heap:>6}   {java_heap:>6}        0        0   {java_heap:>6}   {dalvik_size:>6}   {dalvik_alloc:>6}   {dalvik_free:>6}

 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:    {java_heap:>6}                          {java_rss:>6}
         Native Heap:    {native_heap:>6}                          {native_heap:>6}
                Code:    {code:>6}                          {code_rss:>6}
               Stack:    {stack:>6}                          {stack:>6}
            Graphics:    {graphics:>6}                          {graphics:>6}
       Private Other:    {private_other:>6}
              System:    {system:>6}

           TOTAL PSS:   {total_pss:>6}            TOTAL RSS:   {total_rss:>6}       TOTAL SWAP PSS:   {swap_pss:>6}
"""
STATUS_TEMPLATE = """Name:\tdemo.game
State:\tS (sleeping)
Pid:\t4321
VmRSS:\t  {vm_rss} kB
RssAnon:\t  {rss_anon} kB
RssFile:\t  {rss_file} kB
VmSwap:\t  {vm_swap} kB
"""


def demo_texts(seed=81):
    """합성 시나리오: 전투마다 네이티브 힙 8MB가 해제되지 않는 빌드를 가정한 dumpsys 형식 텍스트"""
    rnd = random.Random(seed)
    leaked = 0
    for label, count in DEMO_PHASES:
        battle = label.startswith("battle")
        if label.startswith("lobby_after"):
            leaked += 8000
        for _ in range(count):
            n = lambda base, spread=0.02: int(base * (1 + rnd.uniform(-spread, spread)))
            v = {
                "java_heap": n(26000 + (6000 if battle else 0)),
                "native_heap": n(92000 + (30000 if battle else 0) + leaked),
                "code": n(31000, 0.005),
                "stack": n(1300, 0.01),
                "graphics": n(112000 + (64000 if battle else 0)),
                "private_other": n(9000),
                "system": n(11000, 0.01),
                "swap_pss": n(300),
            }
            if label == "background":
                v["graphics"] = n(30000)
                v["java_heap"] = n(20000)
                v["swap_pss"] = n(9000)
            v["total_pss"] = sum(v[k] for k in SUMMARY_KEYS.values())
            v["java_rss"], v["code_rss"] = int(v["java_heap"] * 1.6), int(v["code"] * 3.2)
            v["native_alloc"], v["dalvik_alloc"] = int(v["native_heap"] * 0.9), int(v["java_heap"] * 0.8)
            v["native_size"], v["dalvik_size"] = v["native_heap"], v["java_heap"]
            v["native_free"] = v["native_size"] - v["native_alloc"]
            v["dalvik_free"] = v["dalvik_size"] - v["dalvik_alloc"]
            v["total_rss"] = int(v["total_pss"] * 1.25)
            rss_anon = v["java_heap"] + v["native_heap"] + v["graphics"] + v["private_other"]
            status = {"rss_anon": rss_anon, "vm_swap": v["swap_pss"], "rss_file": v["code_rss"],
                      "vm_rss": rss_anon + v["code_rss"]}
            yield label, MEMINFO_TEMPLATE.format(**v), STATUS_TEMPLATE.format(**status)


def analyze(rows):
    """구간별 평균, 로비 복귀 누수 패턴, 백그라운드 해제 여부"""
    phases = {}
    for r in rows:
        phases.setdefault(r["label"], []).append(r)
    summary = {label: {k: sum(r[k] for r in rs) / len(rs)
                       for k in ("total_pss", "anon_swap", "heap_alloc", "native_heap", "graphics")}
               for label, rs in phases.items()}
    # 힙 할당량(Native+Dalvik Alloc)이 있으면 그 값으로, 없으면 Summary Native Heap PSS로 누수 판정
    leak_key, leak_name = (("heap_alloc", "힙 할당량(Native+Dalvik Alloc)") if any(r["heap_alloc"] for r in rows)
                           else ("native_heap", "Native Heap"))
    checks = []
    lobby = [label for label in summary if label == "lobby" or label.startswith("lobby_after")]
    if len(lobby) >= 3:
        vals = [summary[label][leak_key] for label in lobby]
        rate = vals[-1] / vals[0] - 1
        tail = vals[-TAIL_COUNT:]
        tail_rate = tail[-1] / tail[0] - 1
        if rate < LEAK_RATE:
            verdict = "PASS"
        elif tail_rate >= TAIL_RATE:
            verdict = "누수 의심"
        else:
            verdict = "증가 후 안정"
        checks.append((f"M1 로비 복귀 시 {leak_name}", verdict,
                       " → ".join(f"{v / 1024:.1f}" for v in vals)
                       + f" MB (처음 대비 {rate:+.1%}, 최근 {len(tail)}회 {tail_rate:+.1%})"))
    if "background" in summary and lobby:
        before = summary[lobby[-1]]["anon_swap"]
        after = summary["background"]["anon_swap"]
        drop = 1 - after / before
        verdict = "PASS" if drop >= BG_RELEASE_RATE else "확인 필요"
        checks.append(("M2 백그라운드 전환 후 Anon RSS+swap", verdict,
                       f"{before / 1024:.1f} → {after / 1024:.1f} MB ({-drop:+.1%})"))
    return summary, checks


def load_csv(path):
    """--out으로 이어 쓰기: 이전 구간 측정 행을 불러와 전체 구간으로 다시 판정"""
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [{k: (v if k == "label" else float(v) if k == "t_sec" else int(v)) for k, v in r.items()}
                for r in csv.DictReader(f)]


def save_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r[k] for k in FIELDS} for r in rows)


def save_chart(rows, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = [r["t_sec"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for key, name in (("total_pss", "TOTAL PSS"), ("anon_swap", "Anon RSS + swap"), ("heap_alloc", "Heap Alloc (Native+Dalvik)"),
                      ("graphics", "Graphics")):
        ax.plot(x, [r[key] / 1024 for r in rows], marker=".", label=name)
    top = ax.get_ylim()[1]
    start, phase = 0, 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i]["label"] != rows[start]["label"]:
            ax.axvspan(rows[start]["t_sec"], rows[i - 1]["t_sec"], color="gray", alpha=0.12 if phase % 2 else 0.04)
            ax.text(rows[start]["t_sec"], top * 0.98, rows[start]["label"].replace("lobby_after", "after"),
                    fontsize=6, va="top", rotation=90)
            start, phase = i, phase + 1
    ax.set_xlabel("time (s)")
    ax.set_ylabel("MB")
    ax.set_title(title)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def write_report(rows, summary, checks, path, demo, info=""):
    lines = ["# 메모리 측정 리포트", ""] + ([f"> {info}", ""] if info else [])
    if demo:
        lines += ["> **합성 데모 데이터 (실측 아님)**: 기기 연결 전 파싱·집계·그래프·판정 로직 검증용. "
                  "전투마다 Native Heap 8MB가 해제되지 않는 빌드를 가정해 만든 dumpsys 형식 텍스트를 입력으로 사용", ""]
    lines += ["| 구간 | 샘플 | TOTAL PSS (MB) | Anon RSS+swap (MB) | Heap Alloc (MB) | Graphics (MB) |",
              "|---|---|---|---|---|---|"]
    counts = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    for label, s in summary.items():
        lines.append(f"| {label} | {counts[label]} | {s['total_pss'] / 1024:.1f} | {s['anon_swap'] / 1024:.1f} | "
                     f"{s['heap_alloc'] / 1024:.1f} | {s['graphics'] / 1024:.1f} |")
    lines += ["", "| 점검 | 판정 | 근거 |", "|---|---|---|"]
    lines += [f"| {name} | {verdict} | {detail} |" for name, verdict, detail in checks]
    lines += ["", f"- M1 기준: 복귀 값이 처음보다 {LEAK_RATE:.0%} 이상 늘었을 때 최근 {TAIL_COUNT}회 구간도 {TAIL_RATE:.0%} 이상 오르면 "
              "누수 의심, 평탄하면 증가 후 안정(상한 있는 캐시 추정). 판정이 바뀔 수 있으므로 왕복 횟수를 충분히(8회 이상) 둘 것",
              "", "## 구글 플레이 메모리 기준과의 연결 (Day 76)", "",
              "- 2027-02 적용 기준의 동적 메모리 = Anonymous RSS + swap → `/proc/<pid>/status`의 `RssAnon + VmSwap`으로 기록",
              "- 기준은 앱 상태(사용 중·백그라운드)별로 평가 → 같은 시나리오에서 포그라운드·백그라운드 구간을 나눠 측정",
              "- 공개된 수치 한도는 없어 절대값 PASS/FAIL 대신 **패턴**(복귀 시 계속 증가, 백그라운드 미해제)으로 판정. "
              f"판정 비율(누수 {LEAK_RATE:.0%}, 해제 {BG_RELEASE_RATE:.0%})은 자체 기준",
              "- TOTAL PSS는 공유 메모리를 나눠 계산한 값이라 Anon RSS+swap과 다를 수 있음 → 두 값을 함께 기록"]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--package")
    p.add_argument("--label", default="sample")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--serial")
    p.add_argument("--adb", default="adb")
    p.add_argument("--out", help="같은 이름으로 여러 번 실행하면 구간을 이어 붙임 (예: day81_mem_settings)")
    p.add_argument("--analyze", help="측정 없이 저장된 CSV를 다시 판정 (예: day81_mem_settings)")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    rows, info = [], ""
    if a.demo:
        print("[모드] 합성 데모 데이터 (실측 아님)")
        for i, (label, meminfo, status) in enumerate(demo_texts()):
            rows.append({"t_sec": i * a.interval, "label": label, **parse_meminfo(meminfo), **parse_status(status)})
        out = Path("day81_mem_demo")
    elif a.analyze:
        out = Path(a.analyze)
        rows = load_csv(out.with_suffix(".csv"))
        old = out.with_suffix(".md")
        kept = [ln[2:] for ln in old.read_text(encoding="utf-8").splitlines() if ln.startswith("> 실측")] if old.exists() else []
        info = kept[0] if kept else ""
        print(f"[재분석] {out.with_suffix('.csv')} {len(rows)}행 (측정 없음)")
        a.package = a.package or (info.split("앱 ")[1].split(" /")[0] if "앱 " in info else "")
    else:
        if not a.package:
            p.error("--package 필요 (또는 --demo)")
        global ADB
        ADB = a.adb
        try:
            devices = connected_devices()
        except FileNotFoundError:
            print(f"[중단] adb 실행 파일 없음: {ADB} → --adb로 경로 지정")
            return 2
        if not devices:
            print("[중단] adb devices에 기기 없음 → 에뮬레이터 ADB 디버깅 설정 확인")
            return 2
        serial = a.serial or devices[0]
        model = adb(serial, "shell", "getprop", "ro.product.model").strip()
        release = adb(serial, "shell", "getprop", "ro.build.version.release").strip()
        info = f"실측: {serial} ({model}, Android {release}) / 앱 {a.package} / {a.interval}초 간격"
        print(f"[기기] {serial} ({model}, Android {release}) / [앱] {a.package} / [구간] {a.label} x {a.count}회, "
              f"{a.interval}초 간격")
        out = Path(a.out or f"day81_mem_{a.package}_{datetime.now():%Y%m%d_%H%M%S}")
        rows = load_csv(out.with_suffix(".csv"))
        offset = rows[-1]["t_sec"] + a.interval if rows else 0
        t0 = time.time()
        for _ in range(a.count):
            meminfo, status = device_sample(serial, a.package)
            rows.append({"t_sec": round(offset + time.time() - t0, 1), "label": a.label, **parse_meminfo(meminfo),
                         **parse_status(status)})
            time.sleep(a.interval)

    for r in rows:
        print(f"  {r['t_sec']:>6.1f}s {r['label']:<13} PSS {r['total_pss'] / 1024:7.1f}MB  "
              f"Anon+swap {r['anon_swap'] / 1024:7.1f}MB  HeapAlloc {r['heap_alloc'] / 1024:6.1f}MB  "
              f"Graphics {r['graphics'] / 1024:6.1f}MB")
    summary, checks = analyze(rows)
    print()
    for name, verdict, detail in checks:
        print(f"[{verdict}] {name}: {detail}")
    save_csv(rows, out.with_suffix(".csv"))
    save_chart(rows, out.with_suffix(".png"), "Memory (synthetic demo, not measured)" if a.demo else f"Memory {a.package}")
    report = "day81_mem_report.md" if a.demo else out.with_suffix(".md")
    write_report(rows, summary, checks, report, a.demo, info)
    print(f"\n[저장] {out.with_suffix('.csv')}, {out.with_suffix('.png')}, {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
