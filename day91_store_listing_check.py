"""
Day 91 : App Store 공개 등록정보 다국어 점검
1) Apple 공개 iTunes Search/Lookup API로 게임 3종의 국가별 스토어(kr, us, jp, tw, th, es) 등록정보 수집
   - 요청 간격 3초 이상, 응답 JSON은 day91_fixtures/에 저장 (--fetch일 때만 네트워크 사용)
   - 구글 플레이는 공개 API가 없어 대상에서 제외 (페이지 크롤링 하지 않음)
2) 저장본으로 국가별 차이 점검 (관찰한 사실만 기록, 품질 평가 없음)
   - C1 국가별 출시 여부 / C2 버전·버전 출시일 차이 / C3 릴리스 노트 문자 체계와 스토어 언어
   - C4 지원 언어 목록에 스토어 국가 언어 포함 여부 / C5 연령 등급 / C6 가격 표기와 통화 / C7 최소 OS
결과: day91_store_report.md
실행: py day91_store_listing_check.py --fetch (수집 + 점검) / py day91_store_listing_check.py (저장본으로 점검)
"""

import json
import os
import sys
import time
import unicodedata

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(BASE_DIR, "day91_fixtures")
REPORT = os.path.join(BASE_DIR, "day91_store_report.md")
SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"
USER_AGENT = "QA-Portfolio practice (https://github.com/ohseokhee/QA-Portfolio)"
MIN_INTERVAL = 3.0

COUNTRIES = ["kr", "us", "jp", "tw", "th", "es"]
STORE_LANG = {"kr": "KO", "us": "EN", "jp": "JA", "tw": "ZH", "th": "TH", "es": "ES"}
STORE_SCRIPT = {"kr": "Hangul", "us": "Latin", "jp": "Japanese", "tw": "Han", "th": "Thai", "es": "Latin"}
STORE_CURRENCY = {"kr": "KRW", "us": "USD", "jp": "JPY", "tw": "TWD", "th": "THB", "es": "EUR"}
GAMES = [  # (키, 검색어, 검색 국가, 판매자 이름에 들어갈 문자열, 앱 이름 키워드)
    ("epicseven", "Epic Seven", "kr", "Smilegate", ("에픽세븐", "Epic Seven")),
    ("fcmobile", "EA SPORTS FC Mobile", "us", "Electronic Arts", ("FC Mobile", "FC Soccer Mobile")),
    ("sevenknights_rebirth", "세븐나이츠 리버스", "kr", "Netmarble", ("세븐나이츠 리버스", "Seven Knights Re")),
]
GAMES_GENRE_ID = "6014"  # App Store 장르 ID: Games (genres 이름은 스토어 언어로 바뀜)


# ---------- 수집 ----------
class RateLimiter:
    def __init__(self, interval=MIN_INTERVAL, clock=time.monotonic, sleep=time.sleep):
        self.interval, self.clock, self.sleep, self.last = interval, clock, sleep, None
        self.starts = []

    def wait(self):
        if self.last is not None:
            remain = self.interval - (self.clock() - self.last)
            if remain > 0:
                self.sleep(remain)
        self.last = self.clock()
        self.starts.append(self.last)


def get_json(url, params, limiter, session):
    limiter.wait()
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8"))


def fetch_all(fixture_dir=FIXTURE_DIR):
    os.makedirs(fixture_dir, exist_ok=True)
    session = requests.Session()
    session.trust_env = False
    session.headers["User-Agent"] = USER_AGENT
    limiter = RateLimiter()
    ids = {}
    for key, term, country, seller, names in GAMES:
        data = get_json(SEARCH_URL, {"term": term, "country": country, "entity": "software", "limit": 10}, limiter, session)
        save(fixture_dir, f"search_{key}.json", data)
        track_id = pick_track(data, seller, names)
        ids[key] = track_id
        print(f"  [검색] {term} ({country}) 결과 {data.get('resultCount', 0)}건 → trackId {track_id}")
        if track_id is None:
            continue
        for c in COUNTRIES:
            look = get_json(LOOKUP_URL, {"id": track_id, "country": c}, limiter, session)
            save(fixture_dir, f"lookup_{key}_{c}.json", look)
    gaps = [b - a for a, b in zip(limiter.starts, limiter.starts[1:])]
    print(f"  [요청] {len(limiter.starts)}회, 요청 시작 간격 최소 {min(gaps):.2f}초")
    save(fixture_dir, "track_ids.json", ids)
    return ids


def pick_track(search, seller, names):
    """검색 결과 중 판매자 이름과 앱 이름 키워드가 맞는 첫 번째 게임 앱 (장르는 ID로 판정)"""
    for r in search.get("results", []):
        by_seller = seller.lower() in (r.get("sellerName", "") + " " + r.get("artistName", "")).lower()
        by_name = any(n.lower() in r.get("trackName", "").lower() for n in names)
        is_game = str(r.get("primaryGenreId")) == GAMES_GENRE_ID or GAMES_GENRE_ID in r.get("genreIds", [])
        if by_seller and by_name and is_game:
            return r["trackId"]
    return None


def save(fixture_dir, name, data):
    with open(os.path.join(fixture_dir, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load(fixture_dir, name):
    with open(os.path.join(fixture_dir, name), encoding="utf-8") as f:
        return json.load(f)


# ---------- 점검 ----------
def script_of(text):
    """문자 수가 가장 많은 문자 체계 (Hangul / Japanese / Han / Thai / Latin / None)"""
    counts = {}
    for ch in text or "":
        if not ch.isalpha():
            continue
        name = unicodedata.name(ch, "")
        if name.startswith("HANGUL"):
            s = "Hangul"
        elif name.startswith(("HIRAGANA", "KATAKANA")):
            s = "Kana"
        elif name.startswith("CJK"):
            s = "Han"
        elif name.startswith("THAI"):
            s = "Thai"
        elif name.startswith("LATIN"):
            s = "Latin"
        else:
            continue
        counts[s] = counts.get(s, 0) + 1
    if not counts:
        return None
    if counts.get("Kana", 0) > 0 and counts.get("Kana", 0) + counts.get("Han", 0) >= max(counts.values()):
        return "Japanese"
    return max(counts, key=counts.get)


def listing(lookup):
    return lookup["results"][0] if lookup.get("resultCount") else None


def check_game(listings):
    """listings: {국가: 등록정보 dict 또는 None} → (국가별 행, 관찰 목록)"""
    rows, notes = {}, []
    for c, r in listings.items():
        if r is None:
            rows[c] = None
            continue
        notes_script = script_of(r.get("releaseNotes", ""))
        langs = r.get("languageCodesISO2A", [])
        rows[c] = {
            "trackName": r.get("trackName", ""),
            "version": r.get("version", ""),
            "date": (r.get("currentVersionReleaseDate") or "")[:10],
            "notes_script": notes_script,
            "lang_ok": STORE_LANG[c] in langs,
            "langs": len(langs),
            "rating": r.get("contentAdvisoryRating", ""),
            "price": r.get("formattedPrice", ""),
            "currency": r.get("currency", ""),
            "min_os": r.get("minimumOsVersion", ""),
        }
    live = {c: v for c, v in rows.items() if v}
    missing = [c for c, v in rows.items() if v is None]
    if missing:
        notes.append(("C1", f"미출시(조회 결과 없음): {', '.join(missing)}"))
    for field, cid, label in (("version", "C2", "버전"), ("date", "C2", "버전 출시일"), ("rating", "C5", "연령 등급"), ("min_os", "C7", "최소 OS")):
        values = {v[field] for v in live.values()}
        if len(values) > 1:
            notes.append((cid, f"{label} 국가별 차이: " + ", ".join(f"{c} {v[field]}" for c, v in live.items())))
    for c, v in live.items():
        if v["notes_script"] and v["notes_script"] != STORE_SCRIPT[c]:
            notes.append(("C3", f"{c} 릴리스 노트 문자 체계 {v['notes_script']} (스토어 언어 {STORE_SCRIPT[c]})"))
        if not v["lang_ok"]:
            notes.append(("C4", f"{c} 지원 언어 목록에 {STORE_LANG[c]} 없음"))
        if v["currency"] != STORE_CURRENCY[c]:
            notes.append(("C6", f"{c} 통화 {v['currency']} (기대 {STORE_CURRENCY[c]})"))
    return rows, notes


def run_checks(fixture_dir=FIXTURE_DIR):
    ids = load(fixture_dir, "track_ids.json")
    results = {}
    for key, term, *_ in GAMES:
        if ids.get(key) is None:
            results[key] = (term, None, {}, [("C1", "검색 결과에서 판매자가 맞는 앱을 찾지 못함")])
            continue
        listings = {c: listing(load(fixture_dir, f"lookup_{key}_{c}.json")) for c in COUNTRIES}
        rows, notes = check_game(listings)
        results[key] = (term, ids[key], rows, notes)
    return results


# ---------- 리포트 ----------
def main():
    if "--fetch" in sys.argv:
        print("[수집] iTunes Search/Lookup API (요청 간격 3초 이상)")
        fetch_all()
    print("[점검] 저장본 day91_fixtures/ 기준")
    results = run_checks()
    lines = ["# Day 91 App Store 공개 등록정보 다국어 점검 리포트", "",
             "> Apple 공개 iTunes Search/Lookup API 응답(day91_fixtures/)에서 관찰한 사실만 기록. 품질 평가는 하지 않음. 구글 플레이는 공개 API가 없어 제외", ""]
    total = {}
    for key, (term, track_id, rows, notes) in results.items():
        print(f"[{term}] trackId {track_id}")
        lines += [f"## {term}", "", f"- trackId: {track_id}", ""]
        if rows:
            lines += ["| 국가 | 앱 이름 | 버전 | 버전 출시일 | 노트 문자 | 스토어 언어 지원 | 지원 언어 수 | 연령 | 가격 | 통화 | 최소 OS |",
                      "|---|---|---|---|---|---|---|---|---|---|---|"]
            for c, v in rows.items():
                if v is None:
                    print(f"  {c}: 조회 결과 없음")
                    lines.append(f"| {c} | (조회 결과 없음) | | | | | | | | | |")
                    continue
                print(f"  {c}: {v['trackName']} | v{v['version']} {v['date']} | 노트 {v['notes_script']} | "
                      f"{STORE_LANG[c]} {'O' if v['lang_ok'] else 'X'} (언어 {v['langs']}개) | {v['rating']} | {v['price']} {v['currency']} | iOS {v['min_os']}")
                lines.append(f"| {c} | {v['trackName']} | {v['version']} | {v['date']} | {v['notes_script']} | "
                             f"{'O' if v['lang_ok'] else 'X'} | {v['langs']} | {v['rating']} | {v['price']} | {v['currency']} | {v['min_os']} |")
        lines += ["", "### 관찰", ""]
        if not notes:
            lines.append("- 국가별 차이 없음")
        for cid, msg in notes:
            total[cid] = total.get(cid, 0) + 1
            print(f"  [{cid}] {msg}")
            lines.append(f"- [{cid}] {msg}")
        lines.append("")
    summary = ", ".join(f"{k} {total[k]}건" for k in sorted(total))
    print(f"[결과] 게임 {len(results)}종 x 국가 {len(COUNTRIES)}개, 관찰 {sum(total.values())}건 ({summary}) → {os.path.basename(REPORT)}")
    lines += ["## 점검 항목", "",
              "- C1 국가별 출시 여부, C2 버전과 버전 출시일 차이(단계 출시), C3 릴리스 노트 문자 체계와 스토어 언어",
              "- C4 지원 언어 목록(languageCodesISO2A)에 스토어 국가 언어 포함 여부, C5 연령 등급(contentAdvisoryRating)",
              "- C6 가격 표기(formattedPrice)와 통화, C7 최소 OS(minimumOsVersion)", "",
              f"- 관찰 합계: {sum(total.values())}건 ({summary})"]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
