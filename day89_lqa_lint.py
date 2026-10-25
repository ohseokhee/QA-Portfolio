"""
Day 89 : 다국어 문자열 리소스 LQA 자동 점검
- 기준어(ko.json)와 언어별 리소스 JSON(day89_strings/)을 9개 규칙으로 점검하고
  언어 × 규칙 매트릭스 리포트(day89_lqa_report.md, day89_lqa_findings.csv) 저장
- 각 규칙은 Day 72 LQA 체크리스트(LQA-01~09) 항목에 매핑
- 정답표(sealed/day89_answer_key.json)가 있으면 스크립트가 대조해 정밀도·재현율 집계만 출력
  (정답표 내용과 놓친 결함 위치는 출력하지 않음)
실행: py day89_lqa_lint.py
"""

import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STRINGS_DIR = os.path.join(BASE_DIR, "day89_strings")
GLOSSARY_CSV = os.path.join(BASE_DIR, "day89_glossary.csv")
ANSWER_KEY = os.path.join(BASE_DIR, "sealed", "day89_answer_key.json")
REPORT_MD = os.path.join(BASE_DIR, "day89_lqa_report.md")
REPORT_CSV = os.path.join(BASE_DIR, "day89_lqa_findings.csv")
LANGS = ["en", "ja", "zh-TW", "th", "es"]

RULES = {
    "R1": ("키 누락·문자열 ID 노출", "LQA-07"),
    "R2": ("미번역", "LQA-07"),
    "R3": ("자리표시자·태그 불일치", "LQA-05"),
    "R4": ("숫자·% 불일치", "LQA-01"),
    "R5": ("용어집 위반", "LQA-02"),
    "R6": ("길이 예산 초과", "LQA-03"),
    "R7": ("문자 체계 혼입", "LQA-04"),
    "R8": ("문장 부호·공백", "LQA-05"),
    "R9": ("같은 원문 다른 번역", "LQA-02"),
}
UNTRANSLATED_ALLOW = {"FC", "BP"}
PLACEHOLDER_WIDTH = 6
TOKEN_RE = re.compile(r"\{\w+\}|</?\w+(?:=[^>]*)?>")
TAG_RE = re.compile(r"</?\w+(?:=[^>]*)?>")
PH_RE = re.compile(r"\{\w+\}")
KEY_ID_RE = re.compile(r"^[a-z]+(\.[a-z0-9_]+)+$")
HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
THAI_RE = re.compile(r"[฀-๿]")
# 번체 대신 쓰이면 간체로 보는 빈출 글자
SIMPLIFIED = set("购买个游戏训练价数结动无过员这们级时间务领礼宝选择励战队说话发现应该让页设置")


def display_width(text):
    """표시 폭: 태그 제외, 자리표시자 6칸, 전각 2칸, 결합 문자(태국어 성조·모음 부호) 0칸"""
    text = TAG_RE.sub("", text)
    width = PLACEHOLDER_WIDTH * len(PH_RE.findall(text))
    for ch in PH_RE.sub("", text):
        if unicodedata.combining(ch) or unicodedata.category(ch) == "Mn":
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def numbers(text):
    return Counter(re.findall(r"\d+", TOKEN_RE.sub("", text)))


def load(strings_dir=STRINGS_DIR):
    data = {}
    for lang in ["ko"] + LANGS:
        with open(os.path.join(strings_dir, f"{lang}.json"), encoding="utf-8") as f:
            data[lang] = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    with open(os.path.join(strings_dir, "_budget.json"), encoding="utf-8") as f:
        budget = json.load(f)
    return data, budget


def load_glossary(path=GLOSSARY_CSV):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_key(lang, key, src, text, budget, glossary):
    """한 문자열 점검. R1·R2에 걸리면 다른 규칙은 의미가 없어 건너뜀"""
    if text is None or text.strip() == "" or text == key or KEY_ID_RE.match(text.strip()):
        return [("R1", "키 누락" if text is None else f"ID 노출: {text!r}")]
    if text.strip() == src.strip() and text.strip() not in UNTRANSLATED_ALLOW:
        return [("R2", f"원문 그대로: {text!r}")]
    out = []
    if Counter(TOKEN_RE.findall(src)) != Counter(TOKEN_RE.findall(text)):
        out.append(("R3", f"원문 {sorted(TOKEN_RE.findall(src))} / 번역 {sorted(TOKEN_RE.findall(text))}"))
    if numbers(src) != numbers(text):
        out.append(("R4", f"원문 {sorted(numbers(src).elements())} / 번역 {sorted(numbers(text).elements())}"))
    for g in glossary:
        if g["lang"] != lang or g["term_ko"] not in src:
            continue
        low = text.lower()
        if g["forbidden"].lower() in low:
            out.append(("R5", f"'{g['term_ko']}' 금지 번역 '{g['forbidden']}' 사용"))
        elif g["required"].lower() not in low:
            out.append(("R5", f"'{g['term_ko']}' 정해진 번역 '{g['required']}' 없음"))
    w, limit = display_width(text), budget.get(key)
    if limit is not None and w > limit:
        out.append(("R6", f"폭 {w} > 예산 {limit}"))
    bare = TOKEN_RE.sub("", text)
    if lang == "ja" and HANGUL_RE.search(bare):
        out.append(("R7", "일본어에 한글 혼입"))
    elif lang == "zh-TW" and any(c in SIMPLIFIED for c in bare):
        out.append(("R7", f"번체에 간체 글자: {''.join(c for c in bare if c in SIMPLIFIED)}"))
    elif lang == "th" and not THAI_RE.search(bare) and re.search(r"[A-Za-z]{2,}", bare):
        out.append(("R7", "태국어 없이 라틴 문자만"))
    punct = []
    if "  " in text:
        punct.append("이중 공백")
    if text != text.strip():
        punct.append("앞뒤 공백")
    if lang == "es":
        if text.rstrip().endswith("?") and "¿" not in text:
            punct.append("¿ 누락")
        if text.rstrip().endswith("!") and "¡" not in text:
            punct.append("¡ 누락")
    if lang in ("ja", "zh-TW") and re.search(r"[!?]", bare):
        punct.append("반각 !? 사용 (전각 필요)")
    if punct:
        out.append(("R8", ", ".join(punct)))
    return out


def lint(data, budget, glossary):
    findings = []
    for lang in LANGS:
        flagged = set()
        for key, src in data["ko"].items():
            for rule, detail in check_key(lang, key, src, data[lang].get(key), budget, glossary):
                findings.append({"lang": lang, "key": key, "rule": rule, "detail": detail})
                flagged.add(key)
        # R9: 같은 원문을 가진 키끼리 번역 비교 (다른 규칙에 걸린 키 제외), 다수 번역과 다른 키를 표시
        groups = {}
        for key, src in data["ko"].items():
            if key in flagged or key not in data[lang]:
                continue
            groups.setdefault(src.strip(), []).append(key)
        for src, keys in groups.items():
            if len(keys) < 3:
                continue
            counts = Counter(data[lang][k].strip() for k in keys)
            major, n = counts.most_common(1)[0]
            if n == len(keys) or n * 2 <= len(keys):
                continue
            for k in keys:
                if data[lang][k].strip() != major:
                    findings.append({"lang": lang, "key": k, "rule": "R9",
                                     "detail": f"'{src}' 다수 번역 '{major}'와 다름: '{data[lang][k].strip()}'"})
    return findings


def score(findings, answer_path=ANSWER_KEY):
    """정답표와 (언어, 키, 규칙) 단위로 대조. 집계만 반환"""
    if not os.path.exists(answer_path):
        return None
    with open(answer_path, encoding="utf-8") as f:
        answers = {(d["lang"], d["key"], d["rule"]) for d in json.load(f)["defects"]}
    found = {(d["lang"], d["key"], d["rule"]) for d in findings}
    tp = found & answers
    per_rule = {r: (sum(1 for a in tp if a[2] == r), sum(1 for a in answers if a[2] == r)) for r in RULES}
    return {"answers": len(answers), "found": len(found), "tp": len(tp),
            "precision": len(tp) / len(found) if found else 0.0,
            "recall": len(tp) / len(answers) if answers else 0.0,
            "per_rule": per_rule, "fp": len(found - answers)}


def write_reports(findings, data, sc):
    with open(REPORT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lang", "key", "rule", "detail"])
        w.writeheader()
        w.writerows(findings)
    matrix = Counter((d["lang"], d["rule"]) for d in findings)
    lines = ["# Day 89 다국어 문자열 리소스 LQA 점검 리포트", "",
             "> 번역문은 연습용으로 만든 데이터이며 실제 게임 번역이 아님. 결함은 생성 스크립트가 고정 seed로 주입했고, "
             "같은 날 만들고 대조했으므로 블라인드 평가가 아님", "",
             f"- 기준어 ko 키 {len(data['ko'])}개, 대상 언어 {len(LANGS)}개 ({', '.join(LANGS)})",
             f"- 탐지 {len(findings)}건", "",
             "## 규칙과 LQA 체크리스트 매핑", "", "| 규칙 | 내용 | Day 72 항목 |", "|---|---|---|"]
    lines += [f"| {r} | {name} | {lqa} |" for r, (name, lqa) in RULES.items()]
    lines += ["", "## 언어 × 규칙 매트릭스 (탐지 건수)", "",
              "| 언어 | " + " | ".join(RULES) + " | 합계 |", "|---|" + "---|" * (len(RULES) + 1)]
    for lang in LANGS:
        row = [matrix[(lang, r)] for r in RULES]
        lines.append(f"| {lang} | " + " | ".join(str(c) for c in row) + f" | {sum(row)} |")
    lines += ["", "## 탐지 목록", "", "| # | 언어 | 키 | 규칙 | 내용 |", "|---|---|---|---|---|"]
    for i, d in enumerate(findings, 1):
        lines.append(f"| {i} | {d['lang']} | `{d['key']}` | {d['rule']} | {d['detail'].replace('|', '/')} |")
    if sc:
        lines += ["", "## 정답표 대조 (스크립트 집계)", "",
                  f"- 정답 {sc['answers']}개, 탐지 {sc['found']}개, 일치 {sc['tp']}개",
                  f"- 정밀도 {sc['precision']:.1%} (잡아낸 것 중 실제 결함), 재현율 {sc['recall']:.1%} (실제 결함 중 잡아낸 것)", "",
                  "| 규칙 | 일치 / 정답 |", "|---|---|"]
        lines += [f"| {r} | {tp} / {n} |" for r, (tp, n) in sc["per_rule"].items() if n]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    data, budget = load()
    glossary = load_glossary()
    findings = lint(data, budget, glossary)
    sc = score(findings)
    write_reports(findings, data, sc)
    print(f"[점검] 기준어 키 {len(data['ko'])}개 × 언어 {len(LANGS)}개, 규칙 {len(RULES)}개")
    matrix = Counter((d["lang"], d["rule"]) for d in findings)
    print("언어    " + " ".join(f"{r:>3}" for r in RULES) + "  합계")
    for lang in LANGS:
        row = [matrix[(lang, r)] for r in RULES]
        print(f"{lang:<7} " + " ".join(f"{c:>3}" for c in row) + f"  {sum(row):>3}")
    for d in findings:
        print(f"  • {d['lang']:<5} {d['key']:<20} {d['rule']} {d['detail']}")
    if sc:
        print(f"[대조] 정답 {sc['answers']}개, 탐지 {sc['found']}개, 일치 {sc['tp']}개, 오탐 {sc['fp']}개 "
              f"→ 정밀도 {sc['precision']:.1%}, 재현율 {sc['recall']:.1%}")
        print("[대조] 규칙별 일치/정답: " + ", ".join(f"{r} {tp}/{n}" for r, (tp, n) in sc["per_rule"].items() if n))
    print(f"[결과] 탐지 {len(findings)}건 → {os.path.basename(REPORT_MD)}, {os.path.basename(REPORT_CSV)}")


if __name__ == "__main__":
    main()
