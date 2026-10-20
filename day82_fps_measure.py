"""ADB 프레임 측정: SurfaceFlinger --latency·--timestats / gfxinfo → 평균·하위 10%·하위 1% FPS, CSV·그래프·리포트

사용
  py day82_fps_measure.py --method sf --layer "SurfaceView[com.example.game/...]" --label battle --seconds 30
  py day82_fps_measure.py --method ts --layer ChromeChildSurface --label light --seconds 10 --out day82_fps_chrome
  py day82_fps_measure.py --method gfx --package com.android.settings --label scroll --seconds 10
  py day82_fps_measure.py --demo     (기기 없이 합성 데이터로 파싱·계산·그래프 검증, 실측 아님)
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

TARGET = {"avg": 55, "p90": 50, "p99": 30}  # 구글 플레이 레벨업 성능 기준 (Day 76)
PENDING = 9223372036854775807               # SurfaceFlinger가 아직 표시 안 된 프레임에 쓰는 값
ADB = "adb"


def parse_sf_latency(text):
    """dumpsys SurfaceFlinger --latency <레이어> → (화면 주기 ns, 실제 표시 시각 ns 목록)
    첫 줄 = 주기, 이후 줄 = 목표 표시 / 실제 표시 / 프레임 준비 시각"""
    lines = [ln.split() for ln in text.strip().splitlines() if ln.strip()]
    if not lines or len(lines[0]) != 1 or not lines[0][0].isdigit():
        raise ValueError("SurfaceFlinger latency 형식이 아님: " + text.strip()[:80])
    period = int(lines[0][0])
    presents = [int(cols[1]) for cols in lines[1:] if len(cols) == 3 and 0 < int(cols[1]) < PENDING]
    return period, presents


def parse_gfxinfo(text):
    """dumpsys gfxinfo <패키지> 요약 → 프레임 수, 버벅임 비율, 프레임 시간 백분위(ms)"""
    total = re.search(r"Total frames rendered:\s*(\d+)", text)
    if not total:
        raise ValueError("gfxinfo 형식이 아님: " + text.strip()[:80])
    janky = re.search(r"Janky frames:\s*(\d+)\s*\(([\d.]+)%\)", text)
    row = {"frames": int(total.group(1)),
           "janky": int(janky.group(1)) if janky else 0,
           "janky_pct": float(janky.group(2)) if janky else 0.0}
    for pct in (50, 90, 95, 99):
        m = re.search(rf"^\s*{pct}th percentile:\s*(\d+)ms", text, re.M)
        row[f"p{pct}_ms"] = int(m.group(1)) if m else None
    return row


def parse_framestats(text):
    """gfxinfo framestats의 PROFILEDATA 구간 → 완료 시각 ns 목록 (Flags가 0이 아닌 프레임 제외)"""
    presents = []
    for block in re.findall(r"---PROFILEDATA---\n(.*?)---PROFILEDATA---", text, re.S):
        rows = [ln.rstrip(",").split(",") for ln in block.strip().splitlines()]
        header, data = rows[0], rows[1:]
        flags, done = header.index("Flags"), header.index("FrameCompleted")
        presents += [int(r[done]) for r in data if r[flags] == "0"]
    return sorted(presents)


def parse_timestats(text):
    """dumpsys SurfaceFlinger --timestats -dump → 레이어별 프레임 수·평균 FPS·present2present 히스토그램(ms: 개수)"""
    layers = []
    for block in text.split("layerName = ")[1:]:
        name = block.splitlines()[0].strip()
        hist = re.search(r"present2present histogram is as below:\n(.*)", block)
        layers.append({
            "layer": name,
            "frames": int(re.search(r"totalFrames = (\d+)", block).group(1)),
            "dropped": int(re.search(r"droppedFrames = (\d+)", block).group(1)),
            "avg_fps": float(re.search(r"averageFPS = ([\d.]+)", block).group(1)) if "averageFPS" in block else 0.0,
            "hist": {int(ms): int(c) for ms, c in re.findall(r"(\d+)ms=(\d+)", hist.group(1))} if hist else {},
        })
    if not layers:
        raise ValueError("timestats 형식이 아님: " + text.strip()[:80])
    return layers


def hist_intervals(hist):
    """히스토그램 → 간격(ms) 목록. 0ms 칸(같은 vsync에 겹친 표시)은 간격이 아니므로 제외. 칸 해상도 1ms(34ms 이후 2~50ms)"""
    return [ms for ms, count in sorted(hist.items()) if ms > 0 for _ in range(count)]


def percentile(values, q):
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q / 100 * (len(s) - 1))))]


def fps_metrics(presents):
    """표시 시각 → 평균 FPS, 하위 10%(P90 프레임 시간)·하위 1%(P99) FPS"""
    intervals = [(b - a) / 1e6 for a, b in zip(presents, presents[1:]) if b > a]
    if len(intervals) < 10:
        raise ValueError(f"프레임이 너무 적음: {len(intervals) + 1}개")
    span = (presents[-1] - presents[0]) / 1e9
    return {"frames": len(intervals) + 1,
            "avg": len(intervals) / span,
            "p90": 1000 / percentile(intervals, 90),
            "p99": 1000 / percentile(intervals, 99),
            "max_ms": max(intervals),
            "intervals": intervals}


def fps_metrics_from_intervals(intervals):
    """구간별 간격을 이어 붙여 전체 지표 계산"""
    presents = [0]
    for ms in intervals:
        presents.append(presents[-1] + int(ms * 1e6))
    return fps_metrics(presents)


def judge(m):
    """소수 첫째 자리로 반올림해 비교: 60Hz에서 vsync 2개(33.333334ms) 프레임이 29.99999fps로 계산돼 30 미달이 되는 것 방지"""
    return {k: round(m[k], 1) >= v for k, v in TARGET.items()}


def adb(serial, *args):
    cmd = [ADB] + (["-s", serial] if serial else []) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout


def connected_devices():
    lines = adb(None, "devices").splitlines()[1:]
    return [ln.split()[0] for ln in lines if ln.strip().endswith("device")]


def collect_sf(serial, layer, seconds):
    """SurfaceFlinger 버퍼는 최근 약 128프레임만 보관 → 1초마다 읽고 이어 붙임"""
    seen = set()
    end = time.time() + seconds
    adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--latency-clear")
    while time.time() < end:
        time.sleep(1)
        _, presents = parse_sf_latency(adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--latency", layer))
        seen.update(presents)
    return sorted(seen)


def collect_gfx(serial, package, seconds):
    """gfxinfo는 reset 이후 전체 요약 + 최근 120프레임 framestats"""
    adb(serial, "shell", "dumpsys", "gfxinfo", package, "reset")
    time.sleep(seconds)
    text = adb(serial, "shell", "dumpsys", "gfxinfo", package, "framestats")
    return parse_gfxinfo(text), parse_framestats(text)


def collect_ts(serial, layer, seconds):
    """timestats는 기간 동안 레이어별 표시 간격 히스토그램을 누적 → 프레임 수가 가장 많은(또는 이름이 맞는) 레이어 선택"""
    adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--timestats", "-clear")
    adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--timestats", "-enable")
    time.sleep(seconds)
    text = adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--timestats", "-dump")
    adb(serial, "shell", "dumpsys", "SurfaceFlinger", "--timestats", "-disable")
    layers = [x for x in parse_timestats(text) if not layer or layer in x["layer"]]
    if not layers:
        raise RuntimeError(f"레이어 '{layer}' 없음")
    return max(layers, key=lambda x: x["frames"])


def load_segments(path):
    """--out으로 이어 쓰기: 저장된 CSV의 구간별 간격을 다시 읽어 지표 재계산"""
    if not Path(path).exists():
        return []
    groups = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            groups.setdefault(r["label"], []).append(float(r["interval_ms"]))
    return [(label, fps_metrics_from_intervals(v)) for label, v in groups.items()]


DEMO_SEGMENTS = [  # (구간, 프레임 수, 프레임당 vsync 수 분포)
    ("lobby", 900, {1: 0.995, 2: 0.005}),
    ("battle", 1800, {1: 0.94, 2: 0.055, 3: 0.005}),
    ("boss_skill", 600, {1: 0.80, 2: 0.15, 3: 0.03, 4: 0.02}),
]


def demo_sf_texts(seed=82, period=16_666_667, chunk=127):
    """합성 시나리오: 60Hz 화면에서 구간별로 프레임이 vsync 1~4개를 차지하는 SurfaceFlinger --latency 형식 텍스트"""
    rnd = random.Random(seed)
    t = 1_000_000_000_000
    for label, frames, dist in DEMO_SEGMENTS:
        times = []
        for _ in range(frames):
            t += period * rnd.choices(list(dist), weights=list(dist.values()))[0]
            times.append(t)
        texts = []
        for i in range(0, len(times), chunk):
            rows = [f"{p - period} {p} {p - period // 2}" for p in times[i:i + chunk]]
            texts.append("\n".join([str(period), *rows, f"0 {PENDING} 0"]))
        yield label, texts


def save_csv(segments, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "frame", "interval_ms", "fps"])
        for label, m in segments:
            for i, ms in enumerate(m["intervals"], 1):
                w.writerow([label, i, f"{ms:.3f}", f"{1000 / ms:.1f}"])


def save_chart(segments, path, title, hist=False):
    """시각 순서가 있으면 프레임별 시간 그래프, timestats(히스토그램, 순서 없음)면 프레임 시간 분포 막대"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if hist:
        width = 0.8 / len(segments)
        for i, (label, m) in enumerate(segments):
            counts = {}
            for ms in m["intervals"]:
                counts[round(ms)] = counts.get(round(ms), 0) + 1
            buckets = sorted(counts)
            ax.bar([b + (i - (len(segments) - 1) / 2) * width * 4 for b in buckets],
                   [counts[b] / len(m["intervals"]) * 100 for b in buckets], width=width * 4,
                   label=f"{label} (avg {m['avg']:.1f} / P90 {m['p90']:.1f} / P99 {m['p99']:.1f} fps)")
        for fps, style in ((TARGET["p90"], "--"), (TARGET["p99"], ":")):
            ax.axvline(1000 / fps, color="red", linestyle=style, linewidth=0.8)
            ax.text(1000 / fps, ax.get_ylim()[1] * 0.95, f" {fps} fps", color="red", fontsize=7)
        ax.set_xlabel("frame time (ms, present-to-present bucket)")
        ax.set_ylabel("share of frames (%)")
        ax.set_title(title)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(path, dpi=110)
        plt.close(fig)
        return
    x0 = 0
    for label, m in segments:
        xs = range(x0, x0 + len(m["intervals"]))
        ax.plot(xs, m["intervals"], linewidth=0.6, label=f"{label} (avg {m['avg']:.1f} / P90 {m['p90']:.1f} / P99 {m['p99']:.1f} fps)")
        x0 += len(m["intervals"])
    for fps, style in ((TARGET["p90"], "--"), (TARGET["p99"], ":")):
        ax.axhline(1000 / fps, color="red", linestyle=style, linewidth=0.8)
        ax.text(0, 1000 / fps, f" {fps} fps ({1000 / fps:.1f} ms)", color="red", fontsize=7, va="bottom")
    ax.set_xlabel("frame")
    ax.set_ylabel("frame time (ms)")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def write_report(segments, path, demo, info=""):
    lines = ["# 프레임(FPS) 측정 리포트", ""] + ([f"> {info}", ""] if info else [])
    if demo:
        lines += ["> **합성 데모 데이터 (실측 아님)**: 기기 연결 전 파싱·계산·그래프·판정 로직 검증용. "
                  "60Hz 화면에서 구간별로 프레임이 vsync 1~4개를 차지하도록 만든 SurfaceFlinger `--latency` 형식 텍스트를 입력으로 사용", ""]
    lines += ["| 구간 | 프레임 | 평균 FPS | 하위 10% FPS | 하위 1% FPS | 최장 프레임 (ms) | 판정 (55 / 50 / 30) |",
              "|---|---|---|---|---|---|---|"]
    for label, m in segments:
        ok = judge(m)
        verdict = "PASS" if all(ok.values()) else "FAIL (" + ", ".join(k for k, v in ok.items() if not v) + ")"
        lines.append(f"| {label} | {m['frames']} | {m['avg']:.1f} | {m['p90']:.1f} | {m['p99']:.1f} | {m['max_ms']:.1f} | {verdict} |")
    lines += ["", "## 계산 방법", "",
              "- 평균 FPS = (프레임 수 - 1) / (마지막 표시 시각 - 첫 표시 시각)",
              "- 하위 10% FPS = 1000 / 프레임 간격 90번째 백분위(ms), 하위 1% FPS = 1000 / 99번째 백분위(ms)",
              "- 구간을 나눠 계산 → 전체 평균이 높아도 전투·스킬 연출 구간의 끊김이 드러나게 함",
              "", "## 구글 플레이 레벨업 기준과의 연결 (Day 76)", "",
              "- 성능 기준: 기준 기기 실제 플레이 중 평균 55fps, 하위 10% 50fps, 하위 1% 30fps 이상",
              "- 게임 엔진(Unity 등)은 SurfaceView로 그려서 `gfxinfo`(안드로이드 UI 렌더러 기준)에 프레임이 잡히지 않을 수 있음 → "
              "게임은 SurfaceFlinger `--latency`(레이어 단위 실제 표시 시각), 일반 앱 화면은 `gfxinfo`",
              "- SurfaceFlinger는 최근 약 128프레임만 보관 → 1초마다 읽어 이어 붙임",
              "- `--latency`가 0만 돌려주는 환경(LDPlayer 안드로이드 14에서 확인)은 `--timestats`의 레이어별 present2present "
              "히스토그램 사용 (1ms 칸 해상도, 34ms 이후는 2~50ms 칸)",
              "- 히스토그램 칸 하한값을 간격으로 쓰므로 60Hz 한 프레임(16.7ms)이 16ms로 계산돼 62.5fps로 표시됨 (실제보다 약 4% 높음). "
              "기준 경계 근처(예: 33ms 칸 = 30.3fps)는 원본 히스토그램과 timestats averageFPS를 함께 확인"]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_segment(label, m):
    ok = judge(m)
    marks = " / ".join(f"{k} {m[k]:.1f}{'' if ok[k] else ' (기준 ' + str(TARGET[k]) + ' 미달)'}" for k in TARGET)
    print(f"[{'PASS' if all(ok.values()) else 'FAIL'}] {label:<11} 프레임 {m['frames']:>5}  {marks}  최장 {m['max_ms']:.1f}ms")


def main():
    global ADB
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--method", choices=["sf", "ts", "gfx"], default="sf")
    p.add_argument("--layer")
    p.add_argument("--package")
    p.add_argument("--label", default="sample")
    p.add_argument("--seconds", type=int, default=30)
    p.add_argument("--serial")
    p.add_argument("--adb", default="adb")
    p.add_argument("--out", help="같은 이름으로 여러 번 실행하면 구간을 이어 붙임 (예: day82_fps_chrome)")
    p.add_argument("--analyze", help="측정 없이 저장된 CSV로 지표·그래프·리포트 다시 생성 (예: day82_fps_chrome)")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    segments, info = [], ""
    if a.demo:
        print("[모드] 합성 데모 데이터 (실측 아님), SurfaceFlinger --latency 형식")
        for label, texts in demo_sf_texts():
            presents = set()
            for text in texts:
                presents.update(parse_sf_latency(text)[1])
            segments.append((label, fps_metrics(sorted(presents))))
        out = Path("day82_fps_demo")
    elif a.analyze:
        out = Path(a.analyze)
        segments = load_segments(out.with_suffix(".csv"))
        old = out.with_suffix(".md")
        kept = [ln[2:] for ln in old.read_text(encoding="utf-8").splitlines() if ln.startswith("> 실측")] if old.exists() else []
        info = kept[0] if kept else ""
        a.method = "ts" if "timestats" in info else a.method
        print(f"[재분석] {out.with_suffix('.csv')} 구간 {len(segments)}개 (측정 없음)")
    else:
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
        out = Path(a.out or f"day82_fps_{a.label}_{datetime.now():%Y%m%d_%H%M%S}")
        segments = [sg for sg in load_segments(out.with_suffix(".csv")) if sg[0] != a.label]
        if a.method == "ts":
            ts = collect_ts(serial, a.layer, a.seconds)
            info = f"실측: {serial} ({model}, Android {release}) / SurfaceFlinger timestats / 레이어 {ts['layer']}"
            print(f"[기기] {serial} ({model}, Android {release}) / [레이어] {ts['layer']} / {a.seconds}초 / "
                  f"timestats 프레임 {ts['frames']}, 드롭 {ts['dropped']}, averageFPS {ts['avg_fps']}")
            segments.append((a.label, fps_metrics_from_intervals(hist_intervals(ts["hist"]))))
        elif a.method == "sf":
            if not a.layer:
                p.error("--layer 필요 (adb shell dumpsys SurfaceFlinger --list 로 확인)")
            info = f"실측: {serial} ({model}, Android {release}) / SurfaceFlinger latency / 레이어 {a.layer}"
            print(f"[기기] {serial} ({model}, Android {release}) / [레이어] {a.layer} / {a.seconds}초")
            segments.append((a.label, fps_metrics(collect_sf(serial, a.layer, a.seconds))))
        else:
            if not a.package:
                p.error("--package 필요")
            info = f"실측: {serial} ({model}, Android {release}) / gfxinfo framestats(최근 120프레임) / 앱 {a.package}"
            print(f"[기기] {serial} ({model}, Android {release}) / [앱] {a.package} / {a.seconds}초")
            summary, presents = collect_gfx(serial, a.package, a.seconds)
            print(f"[gfxinfo] 프레임 {summary['frames']}, 버벅임 {summary['janky']} ({summary['janky_pct']}%), "
                  f"P50 {summary['p50_ms']}ms P90 {summary['p90_ms']}ms P99 {summary['p99_ms']}ms")
            segments.append((a.label, fps_metrics(presents)))

    rows = list(segments)
    if len(segments) > 1:
        rows.append(("전체", fps_metrics_from_intervals([ms for _, m in segments for ms in m["intervals"]])))
    for label, m in rows:
        print_segment(label, m)
    save_csv(segments, out.with_suffix(".csv"))
    save_chart(segments, out.with_suffix(".png"), "Frame time (synthetic demo, not measured)" if a.demo
               else f"Frame time {out.name}", hist=a.method == "ts" and not a.demo)
    report = "day82_fps_report.md" if a.demo else out.with_suffix(".md")
    write_report(rows, report, a.demo, info)
    print(f"\n[저장] {out.with_suffix('.csv')}, {out.with_suffix('.png')}, {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
