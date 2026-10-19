"""
Day 79 : 마켓 소식 다이제스트 스케줄러
- 실행마다 Day 78 수집기를 호출하고, 이전에 본 소식(링크)은 빼고 새 소식만 발송 (상태 파일 day79_digest_state.json)
- 첫 실행은 기준선: 상위 N건을 보내고 수집된 소식 전체를 '본 것'으로 기록 → 다음 실행부터 새 소식만
- 실행 방식
	--once                  : 지금 1회 실행
	--at HH:MM              : 매일 지정 시각에 실행 (프로세스가 떠 있는 동안 반복)
	--interval-seconds N    : N초 간격 반복 (동작 확인용), --max-runs로 횟수 제한
	--forget-latest K       : 실행 전 가장 최근 소식 K건을 상태에서 지워 '새 소식' 상황을 재현 (확인용)
	--print-task            : Windows 작업 스케줄러 등록 명령만 출력 (등록은 하지 않음)
실행: py day79_digest_scheduler.py --once
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

import day78_market_digest as digest

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "day79_digest_state.json")
digest.PREVIEW_FILE = os.path.join(BASE_DIR, "day79_digest_preview.md")  # Day 78 미리보기와 분리


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen": {}, "runs": []}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def forget_latest(state, k):
    latest = sorted(state["seen"].items(), key=lambda kv: kv[1], reverse=True)[:k]
    for link, _ in latest:
        del state["seen"][link]
    return [link for link, _ in latest]


def run_once(top, days, dry_run):
    state = load_state()
    first_run = not state["seen"]
    collected = []

    def only_new(items):
        collected.extend(items)
        return [it for it in items if it["link"] not in state["seen"]]

    picked, _, status = digest.run(top=top, days=days, dry_run=dry_run, items_filter=only_new)
    new_count = len([it for it in collected if it["link"] not in state["seen"]])
    for it in collected:  # 이번에 본 소식은 모두 기록 (보내지 않은 하위 순위 포함)
        state["seen"].setdefault(it["link"], it["date"].isoformat())
    state["runs"].append({"at": datetime.now().isoformat(timespec="seconds"), "collected": len(collected),
                          "new": new_count, "sent": len(picked), "status": status})
    save_state(state)
    label = "기준선(첫 실행)" if first_run else "증분"
    print(f"  [{label}] 수집 {len(collected)}건 중 새 소식 {new_count}건 → 발송 {len(picked)}건 / {status}")
    for it in picked[:5]:
        print(f"      · [{it['score']}] {it['date']:%Y-%m-%d} {it['title'][:60]}")
    print(f"  상태 파일: 본 소식 누적 {len(state['seen'])}건, 실행 기록 {len(state['runs'])}회")
    return len(picked)


def next_daily(hhmm, now=None):
    now = now or datetime.now()
    hour, minute = map(int, hhmm.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def print_task_command(hhmm):
    script = os.path.join(BASE_DIR, "day79_digest_scheduler.py")
    print("Windows 작업 스케줄러 등록 예시 (실행하지 않음):")
    print(f'  schtasks /Create /SC DAILY /ST {hhmm} /TN "QA-Portfolio Market Digest" '
          f'/TR "py \\"{script}\\" --once" /F')
    print("삭제: schtasks /Delete /TN \"QA-Portfolio Market Digest\" /F")


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--at", metavar="HH:MM")
    mode.add_argument("--interval-seconds", type=int)
    mode.add_argument("--print-task", metavar="HH:MM")
    parser.add_argument("--max-runs", type=int, default=0, help="반복 모드 최대 실행 횟수 (0 = 무제한)")
    parser.add_argument("--forget-latest", type=int, default=0)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.print_task:
        print_task_command(args.print_task)
        return
    if args.forget_latest:
        state = load_state()
        removed = forget_latest(state, args.forget_latest)
        save_state(state)
        print(f"[준비] 최근 소식 {len(removed)}건을 상태에서 제거 (새 소식 재현): {removed}")

    runs = 0
    while True:
        runs += 1
        if args.at:
            target = next_daily(args.at)
            print(f"[대기] 다음 실행 {target:%Y-%m-%d %H:%M} ({(target - datetime.now()).total_seconds():.0f}초 후)")
            time.sleep(max(0, (target - datetime.now()).total_seconds()))
        print(f"[실행 {runs}] {datetime.now():%Y-%m-%d %H:%M:%S}")
        run_once(args.top, args.days, args.dry_run)
        if args.once or (args.max_runs and runs >= args.max_runs):
            break
        if args.interval_seconds:
            time.sleep(args.interval_seconds)
    print(f"[결과] 실행 {runs}회 완료 → 미리보기 {os.path.relpath(digest.PREVIEW_FILE, BASE_DIR)}")


if __name__ == "__main__":
    main()
