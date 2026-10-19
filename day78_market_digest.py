"""
Day 78 : 마켓 소식 다이제스트 (공개판)
- 안드로이드·애플 개발자 공식 소식(RSS/Atom)을 수집 → QA 관점 키워드로 우선순위 점수 → 상위 N건을 디스코드 웹훅으로 발송
- 웹훅 URL은 .env의 DISCORD_WEBHOOK_URL. 없으면 실제 발송 없이 미리보기 파일(day78_digest_preview.md)만 저장 (dry-run)
- 외부 요청은 최소 1초 간격, 시스템 프록시(Fiddler 등)는 거치지 않음
실행: py day78_market_digest.py [--top 10] [--days 60] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
PREVIEW_FILE = os.path.join(BASE_DIR, "day78_digest_preview.md")
USER_AGENT = "QA-Portfolio-market-digest/1.0 (+https://github.com/ohseokhee/QA-Portfolio)"
REQUEST_INTERVAL = 1.0

SOURCES = [
    {"name": "Android Developers Blog", "url": "https://android-developers.googleblog.com/feeds/posts/default"},
    {"name": "Apple Developer News", "url": "https://developer.apple.com/news/rss/news.rss"},
]

# QA 관점 키워드 가중치 (정책·마감·심사 > 기술 요구사항 > 일반)
KEYWORDS = {
    "policy": 5, "deadline": 5, "requirement": 4, "required": 4, "target api": 5, "targetsdk": 5,
    "review guidelines": 5, "age rating": 5, "age assurance": 5, "16 kb": 5, "page size": 4,
    "privacy": 4, "data safety": 4, "billing": 4, "in-app purchase": 4, "payments": 3,
    "deprecat": 3, "sdk": 2, "play console": 3, "app store connect": 3, "testflight": 2,
    "memory": 3, "performance": 2, "vitals": 3, "crash": 3, "anr": 3, "game": 2,  # "game"이 "games"도 포함
    "upcoming": 2, "beta": 1, "accessibility": 2,
}
ATOM = "{http://www.w3.org/2005/Atom}"


def new_session():
    session = requests.Session()
    session.trust_env = False
    session.headers["User-Agent"] = USER_AGENT
    return session


def strip_html(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def parse_feed(source, xml_text):
    root = ET.fromstring(xml_text)
    items = []
    if root.tag == f"{ATOM}feed":
        for e in root.findall(f"{ATOM}entry"):
            link = next((l.get("href") for l in e.findall(f"{ATOM}link") if l.get("rel", "alternate") == "alternate"), "")
            published = e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated") or ""
            items.append({"source": source, "title": strip_html(e.findtext(f"{ATOM}title")), "link": link,
                          "date": datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None,
                          "summary": strip_html(e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content"))[:400]})
    else:
        for e in root.iter("item"):
            pub = e.findtext("pubDate")
            items.append({"source": source, "title": strip_html(e.findtext("title")), "link": e.findtext("link") or "",
                          "date": parsedate_to_datetime(pub) if pub else None,
                          "summary": strip_html(e.findtext("description"))[:400]})
    return items


def score(item):
    text = f"{item['title']} {item['summary']}".lower()
    hits = [k for k in KEYWORDS if k in text]
    return sum(KEYWORDS[k] for k in hits), hits


def collect(session, days):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    items, stats = [], []
    for i, src in enumerate(SOURCES):
        if i:
            time.sleep(REQUEST_INTERVAL)
        res = session.get(src["url"], timeout=20)
        res.raise_for_status()
        parsed = parse_feed(src["name"], res.text)
        recent = [it for it in parsed if it["date"] and it["date"] >= since]
        stats.append((src["name"], res.status_code, len(parsed), len(recent)))
        items += recent
    for it in items:
        it["score"], it["hits"] = score(it)
    items.sort(key=lambda it: (it["score"], it["date"]), reverse=True)
    return items, stats


def discord_payload(items, top):
    picked = items[:top]
    embeds = [{
        "title": it["title"][:256],
        "url": it["link"],
        "description": (it["summary"][:300] + ("…" if len(it["summary"]) > 300 else "")),
        "footer": {"text": f"{it['source']} · {it['date']:%Y-%m-%d} · 점수 {it['score']} ({', '.join(it['hits'][:5]) or '-'})"},
    } for it in picked]
    return {"content": f"📱 마켓 소식 다이제스트 {datetime.now():%Y-%m-%d} (상위 {len(picked)}건)", "embeds": embeds[:10]}


def send(payload, webhook_url, session):
    res = session.post(webhook_url, json=payload, timeout=15)
    return res.status_code


def write_preview(items, top, stats, sent_status):
    lines = [f"# 마켓 소식 다이제스트 미리보기 ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"- 발송: {sent_status}", ""]
    lines += ["| 출처 | HTTP | 전체 | 기간 내 |", "|---|---|---|---|"]
    lines += [f"| {n} | {c} | {a} | {r} |" for n, c, a, r in stats]
    lines += ["", "| 순위 | 점수 | 날짜 | 출처 | 제목 | 매칭 키워드 |", "|---|---|---|---|---|---|"]
    for i, it in enumerate(items[:top], 1):
        lines.append(f"| {i} | {it['score']} | {it['date']:%Y-%m-%d} | {it['source']} | "
                     f"[{it['title'].replace('|', '/')}]({it['link']}) | {', '.join(it['hits']) or '-'} |")
    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(top=10, days=60, dry_run=False, items_filter=None):
    """다이제스트 1회 실행. items_filter가 있으면 수집 결과를 걸러 낸 뒤 발송 (Day 79 중복 제거용)"""
    session = new_session()
    items, stats = collect(session, days)
    for name, code, total, recent in stats:
        print(f"  [수집] {name}: HTTP {code}, 전체 {total}건, 최근 {days}일 {recent}건")
    if items_filter:
        items = items_filter(items)
    payload = discord_payload(items, top)
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not items:
        status = "보낼 새 소식 없음"
    elif dry_run or not webhook:
        status = "dry-run (DISCORD_WEBHOOK_URL 없음, 미리보기만 저장)" if not webhook else "dry-run (--dry-run)"
    else:
        status = f"디스코드 웹훅 HTTP {send(payload, webhook, session)}"
    write_preview(items, top, stats, status)
    return items[:top], payload, status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"[1] 공식 소식 수집 (출처 {len(SOURCES)}곳, 요청 간격 {REQUEST_INTERVAL}초)")
    picked, payload, status = run(args.top, args.days, args.dry_run)
    print(f"\n[2] 우선순위 상위 {len(picked)}건 (점수 = 키워드 가중치 합)")
    for i, it in enumerate(picked, 1):
        print(f"  {i:2d}. [{it['score']:2d}] {it['date']:%Y-%m-%d} {it['source']} | {it['title'][:70]}"
              f" ({', '.join(it['hits'][:4]) or '-'})")
    print(f"\n[3] 디스코드 메시지: embed {len(payload['embeds'])}개, 본문 \"{payload['content']}\"")
    print(f"    payload 크기 {len(json.dumps(payload, ensure_ascii=False))}자 / 발송: {status}")
    print(f"\n[결과] 미리보기 저장 → {os.path.relpath(PREVIEW_FILE, BASE_DIR)}")


if __name__ == "__main__":
    main()
