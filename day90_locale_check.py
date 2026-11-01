"""
Day 90 : 로캘 형식, 시간대, 폰트 글리프 점검
1) Babel(CLDR)로 7개 로캘의 숫자·통화·퍼센트·날짜 표기 기준표를 만들고,
   Day 89 문자열과 상점 페이지(day65_shop_client.html)에서 하드코딩 형식을 탐지
   - 쉼표 숫자 리터럴(1,000), 날짜·시각 리터럴(2026-10-25 05:00), CLDR과 다른 퍼센트 표기, 서식 없이 출력하는 숫자 보간(${price})
2) zoneinfo(tzdata)로 KST 기준 일일 초기화(05:00)와 이벤트 종료 시각을 지역 시간으로 변환하고 서머타임 경계 검증
   - 2026-10-25 유럽 서머타임 종료, 2026-11-01 미국 서머타임 종료 전후 현지 시각 변화
   - 현지 시각 기준 일정의 중복 시각(fold)과 없는 시각(gap) 판정, 고정 오프셋 표로 변환했을 때의 오차
3) fontTools로 Windows 기본 폰트의 글리프 보유 여부를 언어별 문자열로 점검 → 빠진 글자(두부 □)와 폴백 필요 여부
   - 폰트는 패밀리 이름으로 찾고 읽기만 함 (복사·커밋하지 않음)
결과: day90_locale_report.md
실행: py day90_locale_check.py
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from babel.dates import format_date, format_datetime, format_time
from babel.numbers import format_currency, format_decimal, format_percent
from fontTools.ttLib import TTCollection, TTFont

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STRINGS_DIR = os.path.join(BASE_DIR, "day89_strings")
SHOP_HTML = os.path.join(BASE_DIR, "day65_shop_client.html")
REPORT = os.path.join(BASE_DIR, "day90_locale_report.md")
FONT_DIR = r"C:\Windows\Fonts"

LOCALES = {"ko_KR": "KRW", "en_US": "USD", "ja_JP": "JPY", "zh_TW": "TWD", "th_TH": "THB", "es_ES": "EUR", "de_DE": "EUR"}
LANG_LOCALE = {"ko": "ko_KR", "en": "en_US", "ja": "ja_JP", "zh-TW": "zh_TW", "th": "th_TH", "es": "es_ES"}
SAMPLE_NUMBER = 1234567.891
SAMPLE_DT = datetime(2026, 10, 25, 5, 0)

KST = ZoneInfo("Asia/Seoul")
CITIES = ["America/Los_Angeles", "America/New_York", "Europe/London", "Europe/Berlin", "Europe/Madrid",
          "Asia/Tokyo", "Asia/Taipei", "Asia/Bangkok"]
RESET_DATES = ["2026-10-24", "2026-10-25", "2026-10-26", "2026-10-27", "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"]
EVENT_END_KST = datetime(2026, 11, 2, 5, 0, tzinfo=KST)
LOCAL_SCHEDULES = [  # (설명, 도시, 현지 시각)
    ("뉴욕 현지 2026-11-01 01:30 이벤트 종료", "America/New_York", datetime(2026, 11, 1, 1, 30)),
    ("베를린 현지 2026-10-25 02:30 점검 시작", "Europe/Berlin", datetime(2026, 10, 25, 2, 30)),
    ("뉴욕 현지 2027-03-14 02:30 점검 시작", "America/New_York", datetime(2027, 3, 14, 2, 30)),
    ("베를린 현지 2027-03-28 02:30 이벤트 시작", "Europe/Berlin", datetime(2027, 3, 28, 2, 30)),
    ("도쿄 현지 2026-11-01 01:30 이벤트 종료", "Asia/Tokyo", datetime(2026, 11, 1, 1, 30)),
]

FONT_FAMILIES = {"Malgun Gothic": None, "Yu Gothic": "Meiryo", "Microsoft JhengHei": None, "Leelawadee UI": None, "Segoe UI": None}
LANG_FONT = {"ko": "Malgun Gothic", "en": "Segoe UI", "es": "Segoe UI", "ja": "Yu Gothic", "zh-TW": "Microsoft JhengHei", "th": "Leelawadee UI"}
TOKEN_RE = re.compile(r"\{\w+\}|</?\w+(?:=[^>]*)?>")

GROUPED_RE = re.compile(r"(?<![\d.])\d{1,3}(?:,\d{3})+(?![\d,])")
DATETIME_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?\b")
PERCENT_RE = re.compile(r"(\d+)(\s?)%")
NUM_INTERP_RE = re.compile(r"\$\{([^}]*?(?<![A-Za-z_])(?:price|amount|balance|balances\.\w+|count|quantity)(?![A-Za-z_])[^}]*)\}")
LOCALE_FMT_RE = re.compile(r"toLocaleString|Intl\.NumberFormat|formatNumber")


# ---------- 1) 로캘 형식 ----------
def locale_table():
    rows = []
    for loc, cur in LOCALES.items():
        rows.append({
            "locale": loc,
            "number": format_decimal(SAMPLE_NUMBER, locale=loc),
            "currency": format_currency(1000, cur, locale=loc),
            "percent": format_percent(0.2, locale=loc),
            "date": format_date(SAMPLE_DT.date(), format="short", locale=loc),
            "datetime": format_datetime(SAMPLE_DT, format="medium", locale=loc),
        })
    return rows


def scan_text(text, locale):
    """문자열 하나에서 하드코딩 형식 탐지 → [(종류, 값, 기준)]"""
    hits = []
    bare = TOKEN_RE.sub("", text)
    for m in GROUPED_RE.finditer(bare):
        hits.append(("쉼표 숫자 리터럴", m.group(0), format_decimal(int(m.group(0).replace(",", "")), locale=locale)))
    for m in DATETIME_RE.finditer(bare):
        hits.append(("날짜·시각 리터럴", m.group(0), "로캘별 날짜 서식 필요"))
    for m in PERCENT_RE.finditer(bare):
        expect = format_percent(int(m.group(1)) / 100, locale=locale)
        if m.group(0).replace("\u00a0", " ") != expect.replace("\u00a0", " "):
            hits.append(("CLDR과 다른 퍼센트 표기", m.group(0), expect.replace("\u00a0", "(NBSP)")))
    return hits


def scan_strings(strings_dir=STRINGS_DIR):
    hits = []
    for lang, loc in LANG_LOCALE.items():
        with open(os.path.join(strings_dir, f"{lang}.json"), encoding="utf-8") as f:
            table = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        for key, text in table.items():
            for kind, value, expect in scan_text(text, loc):
                hits.append({"source": f"day89_strings/{lang}.json", "where": key, "kind": kind, "value": value, "expect": expect})
    return hits


def scan_js(source, name):
    hits = []
    for lineno, line in enumerate(source.splitlines(), 1):
        for kind, value, expect in scan_text(line, "ko_KR"):
            hits.append({"source": name, "where": f"{lineno}행", "kind": kind, "value": value, "expect": expect})
        for m in NUM_INTERP_RE.finditer(line):
            if not LOCALE_FMT_RE.search(m.group(1)):
                hits.append({"source": name, "where": f"{lineno}행", "kind": "서식 없는 숫자 보간",
                             "value": "${" + m.group(1) + "}",
                             "expect": "50000 → " + " / ".join(f"{l} {format_decimal(50000, locale=l)}" for l in ("en_US", "de_DE", "es_ES"))})
    return hits


# ---------- 2) 시간대 ----------
def reset_local_times(cities=CITIES, dates=RESET_DATES):
    """KST 날짜별 05:00 초기화의 현지 시각"""
    table = {}
    for d in dates:
        kst = datetime.fromisoformat(d + " 05:00").replace(tzinfo=KST)
        table[d] = {c: kst.astimezone(ZoneInfo(c)) for c in cities}
    return table


def shifts(table):
    """현지 벽시계 시각이 바뀐 지점 [(도시, 이전 KST 날짜, 다음 KST 날짜, 이전 현지, 다음 현지)]"""
    out, dates = [], list(table)
    for c in next(iter(table.values())):
        for a, b in zip(dates, dates[1:]):
            ta, tb = table[a][c], table[b][c]
            if (ta.hour, ta.minute) != (tb.hour, tb.minute):
                out.append((c, a, b, ta.strftime("%H:%M %Z"), tb.strftime("%H:%M %Z")))
    return out


def classify_local(naive, tz_name):
    """현지 시각 판정: normal / fold(두 번 나타남) / gap(존재하지 않음)"""
    tz = ZoneInfo(tz_name)
    a, b = naive.replace(tzinfo=tz, fold=0), naive.replace(tzinfo=tz, fold=1)
    if a.utcoffset() == b.utcoffset():
        return "normal", [a]
    back = a.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
    if back != naive:
        return "gap", [a, b]
    return "fold", [a, b]


def fixed_offset_errors(table, reference_date="2026-10-24"):
    """서머타임 종료 전 오프셋을 고정 표로 쓰면 틀리는 건수"""
    fixed = {c: t.utcoffset() for c, t in table[reference_date].items()}
    wrong = []
    for d, row in table.items():
        for c, t in row.items():
            naive_fixed = (t.astimezone(timezone.utc) + fixed[c]).replace(tzinfo=None)
            if naive_fixed != t.replace(tzinfo=None):
                wrong.append((d, c, naive_fixed.strftime("%H:%M"), t.strftime("%H:%M")))
    return wrong


# ---------- 3) 폰트 ----------
def family_index(font_dir=FONT_DIR):
    """{패밀리 이름: [(경로, ttc 번호, 서브패밀리)]} — name 테이블만 읽음"""
    index = {}
    for path in sorted(glob.glob(os.path.join(font_dir, "*.tt[fc]")) + glob.glob(os.path.join(font_dir, "*.otf"))):
        try:
            fonts = TTCollection(path, lazy=True).fonts if path.lower().endswith(".ttc") else [TTFont(path, lazy=True)]
        except Exception:
            continue
        for i, font in enumerate(fonts):
            try:
                name = font["name"]
                fam = name.getDebugName(16) or name.getDebugName(1)
                sub = name.getDebugName(17) or name.getDebugName(2)
            except Exception:
                continue
            if fam:
                index.setdefault(fam, []).append((path, i, sub))
    return index


def load_cmap(entries):
    """Regular 우선으로 한 개 골라 cmap(코드포인트 집합) 반환"""
    entries = sorted(entries, key=lambda e: (e[2] != "Regular", e[0]))
    path, i, sub = entries[0]
    font = TTCollection(path, lazy=True).fonts[i] if path.lower().endswith(".ttc") else TTFont(path, lazy=True)
    return set(font.getBestCmap().keys()), f"{os.path.basename(path)}#{i} {sub}"


def missing_glyphs(text, cmap):
    chars = sorted({c for c in TOKEN_RE.sub("", text) if not c.isspace()})
    return [c for c in chars if ord(c) not in cmap]


def lang_texts(strings_dir=STRINGS_DIR):
    texts = {}
    for lang in LANG_LOCALE:
        with open(os.path.join(strings_dir, f"{lang}.json"), encoding="utf-8") as f:
            texts[lang] = "".join(v for k, v in json.load(f).items() if not k.startswith("_"))
    return texts


# ---------- 리포트 ----------
def main():
    lines = ["# Day 90 로캘 형식, 시간대, 폰트 글리프 점검 리포트", "",
             "> 문자열은 Day 89 연습용 번역 데이터(실제 게임 번역 아님). 폰트는 이 PC의 C:\\Windows\\Fonts를 읽기만 함", ""]

    print("[1] 로캘 기준표 (Babel CLDR)")
    rows = locale_table()
    lines += ["## 1. 로캘 기준표 (Babel CLDR)", "", f"- 숫자 {SAMPLE_NUMBER}, 통화 1000, 퍼센트 0.2, 날짜 {SAMPLE_DT:%Y-%m-%d %H:%M}", "",
              "| 로캘 | 숫자 | 통화 | 퍼센트 | 날짜(short) | 날짜·시각(medium) |", "|---|---|---|---|---|---|"]
    for r in rows:
        cells = [r[k].replace("\u00a0", "(NBSP)").replace("\u202f", "(NNBSP)") for k in ("number", "currency", "percent", "date", "datetime")]
        print(f"  {r['locale']:<6} " + " | ".join(cells))
        lines.append(f"| {r['locale']} | " + " | ".join(cells) + " |")
    hits = scan_strings() + scan_js(open(SHOP_HTML, encoding="utf-8").read(), "day65_shop_client.html")
    counts = {}
    for h in hits:
        counts[h["kind"]] = counts.get(h["kind"], 0) + 1
    print(f"[1] 하드코딩 형식 탐지 {len(hits)}건 " + str(counts))
    lines += ["", f"### 하드코딩 형식 탐지 {len(hits)}건", "", "| # | 위치 | 종류 | 값 | CLDR 기준 |", "|---|---|---|---|---|"]
    for i, h in enumerate(hits, 1):
        print(f"  • {h['source']} {h['where']} {h['kind']}: {h['value']} → {h['expect']}")
        lines.append(f"| {i} | {h['source']} `{h['where']}` | {h['kind']} | `{h['value']}` | {h['expect']} |")

    print("[2] 시간대: KST 05:00 일일 초기화의 현지 시각")
    table = reset_local_times()
    lines += ["", "## 2. 시간대 (zoneinfo, tzdata)", "", "### KST 05:00 일일 초기화의 현지 시각", "",
              "| KST 날짜 | " + " | ".join(c.split("/")[1] for c in CITIES) + " |", "|---|" + "---|" * len(CITIES)]
    for d, row in table.items():
        cells = [row[c].strftime("%m-%d %H:%M") for c in CITIES]
        print(f"  {d} " + " ".join(f"{c.split('/')[1][:8]:>8}={v}" for c, v in zip(CITIES, cells)))
        lines.append(f"| {d} | " + " | ".join(cells) + " |")
    sh = shifts(table)
    lines += ["", "### 현지 시각이 바뀐 지점", "", "| 도시 | KST 초기화 | 현지 시각 |", "|---|---|---|"]
    for c, a, b, ta, tb in sh:
        print(f"  [변화] {c}: KST {a} 초기화 {ta} → KST {b} 초기화 {tb}")
        lines.append(f"| {c} | {a} → {b} | {ta} → {tb} |")
    no_dst = [c for c in CITIES if c not in {s[0] for s in sh}]
    print(f"  [고정] 현지 시각 변화 없음: {', '.join(no_dst)}")
    end_rows = [(c, EVENT_END_KST.astimezone(ZoneInfo(c))) for c in CITIES]
    lines += ["", f"### 이벤트 종료 KST {EVENT_END_KST:%Y-%m-%d %H:%M}의 현지 시각", "", "| 도시 | 현지 시각 | UTC 오프셋 |", "|---|---|---|"]
    lines += [f"| {c} | {t:%Y-%m-%d %H:%M %Z} | {t:%z} |" for c, t in end_rows]
    print("  [이벤트 종료] KST 2026-11-02 05:00 → " + ", ".join(f"{c.split('/')[1]} {t:%m-%d %H:%M %Z}" for c, t in end_rows))

    lines += ["", "### 현지 시각 기준 일정 판정", "", "| 일정 | 판정 | KST 환산 |", "|---|---|---|"]
    for desc, tz_name, naive in LOCAL_SCHEDULES:
        kind, cands = classify_local(naive, tz_name)
        kst = " / ".join(f"{c.astimezone(KST):%m-%d %H:%M}" + (f" (fold={c.fold})" if kind != "normal" else "") for c in cands)
        label = {"normal": "정상", "fold": "중복 시각(두 번 나타남)", "gap": "없는 시각(시계가 건너뜀)"}[kind]
        print(f"  [{kind}] {desc} → {label}, KST {kst}")
        lines.append(f"| {desc} | {label} | {kst} |")
    wrong = fixed_offset_errors(table)
    print(f"  [고정 오프셋] 2026-10-24 기준 오프셋 표로 변환하면 {len(table) * len(CITIES)}건 중 {len(wrong)}건이 1시간 틀림")
    lines += ["", f"- 고정 오프셋 표(2026-10-24 기준)로 변환하면 {len(table) * len(CITIES)}건 중 **{len(wrong)}건이 1시간 틀림** "
              "(서머타임 종료 후 유럽·미국 도시)"]

    print("[3] 폰트 글리프 (fontTools, 패밀리 이름으로 검색, 읽기만)")
    index = family_index()
    cmaps = {}
    lines += ["", "## 3. 폰트 글리프 (fontTools)", ""]
    for fam, alt in FONT_FAMILIES.items():
        use = fam if fam in index else (alt if alt in index else None)
        if use is None:
            print(f"  [없음] {fam}" + (f" / 대체 {alt}" if alt else ""))
            lines.append(f"- {fam}: 이 PC에 없음")
            continue
        cmaps[fam], label = load_cmap(index[use])
        print(f"  [폰트] {fam} → {label}, 글리프 {len(cmaps[fam])}개")
        lines.append(f"- {fam}: `{label}`, 글리프 {len(cmaps[fam])}개")
    texts = lang_texts()
    fams = list(cmaps)
    lines += ["", "### 언어 × 폰트 빠진 글자 수 (Day 89 문자열 기준)", "", "| 언어 | 글자 종류 | " + " | ".join(fams) + " | 지정 폰트 |",
              "|---|---|" + "---|" * (len(fams) + 1)]
    tofu_total = 0
    for lang, text in texts.items():
        uniq = len({c for c in TOKEN_RE.sub("", text) if not c.isspace()})
        miss = {f: missing_glyphs(text, cmaps[f]) for f in fams}
        own = LANG_FONT[lang]
        tofu_total += len(miss.get(own, []))
        print(f"  {lang:<6} 글자 {uniq:>3}종 | " + " ".join(f"{f.split()[0][:9]}={len(m)}" for f, m in miss.items())
              + f" | 지정 {own}: 빠짐 {len(miss.get(own, []))}")
        lines.append(f"| {lang} | {uniq} | " + " | ".join(str(len(m)) for m in miss.values()) + f" | {own} ({len(miss.get(own, []))}) |")
        if miss.get(own):
            print(f"         지정 폰트에 없는 글자: {''.join(miss[own])}")
        seg = miss.get("Segoe UI", [])
        if seg and lang not in ("en", "es"):
            print(f"         Segoe UI 하나로 표시하면 두부(□) {len(seg)}자 예: {''.join(seg[:10])} → 폴백 폰트 필요")
    lines += ["", f"- 언어별 지정 폰트에서 빠진 글자 합계: **{tofu_total}자**",
              "- Segoe UI 한 가지로 모든 언어를 표시하면 ko, ja, zh-TW, th 글자가 두부(□)로 나와 언어별 폴백 폰트 지정이 필요"]
    print(f"[결과] 하드코딩 형식 {len(hits)}건, 서머타임 현지 시각 변화 {len(sh)}개 도시, 고정 오프셋 오차 {len(wrong)}건, "
          f"지정 폰트 빠진 글자 {tofu_total}자 → {os.path.basename(REPORT)}")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
