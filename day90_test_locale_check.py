"""
Day 90 : 로캘·시간대·폰트 점검 로직 테스트
- 폰트 테스트는 fontTools FontBuilder로 만든 작은 테스트 폰트 사용 (기기와 OS에 상관없이 재현)
실행: py -m pytest day90_test_locale_check.py -v
"""

from datetime import datetime

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

import day90_locale_check as lc


def build_test_font(path, family="Day90 Test", chars="AB"):
    """chars 글자만 가진 작은 TrueType 폰트"""
    glyphs = [".notdef"] + [f"g{ord(c)}" for c in chars]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyphs)
    fb.setupCharacterMap({ord(c): f"g{ord(c)}" for c in chars})
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0)); pen.lineTo((0, 500)); pen.lineTo((500, 500)); pen.closePath()
    glyph = pen.glyph()
    fb.setupGlyf({g: glyph for g in glyphs})
    fb.setupHorizontalMetrics({g: (600, 0) for g in glyphs})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    fb.save(str(path))


def test_font_found_by_family_name_and_missing_glyphs(tmp_path):
    build_test_font(tmp_path / "zz_random_file_name.ttf")
    index = lc.family_index(str(tmp_path))
    assert "Day90 Test" in index                      # 파일명이 아니라 패밀리 이름으로 찾음
    cmap, label = lc.load_cmap(index["Day90 Test"])
    assert lc.missing_glyphs("ABC 가", cmap) == ["C", "가"]
    assert lc.missing_glyphs("{count}<b>AB</b>", cmap) == []   # 자리표시자·태그는 글리프 점검 대상 아님


def test_babel_cldr_formats():
    assert lc.format_decimal(1234.5, locale="de_DE") == "1.234,5"
    assert lc.format_decimal(1234.5, locale="en_US") == "1,234.5"
    rows = {r["locale"]: r for r in lc.locale_table()}
    assert set(rows) == set(lc.LOCALES)


def test_scan_text_hardcoded_formats():
    hits = lc.scan_text("가격 1,000 FC, 종료 2026-10-25 05:00", "de_DE")
    kinds = [h[0] for h in hits]
    assert kinds == ["쉼표 숫자 리터럴", "날짜·시각 리터럴"]
    assert hits[0][2] == "1.000"
    assert lc.scan_text("1회 최대 10개", "ko_KR") == []


def test_percent_against_cldr():
    assert lc.scan_text("+20%", "en_US") == []
    assert [h[0] for h in lc.scan_text("+20%", "de_DE")] == ["CLDR과 다른 퍼센트 표기"]
    assert lc.scan_text("<color=#FFD700>20%</color>", "ja_JP") == []


def test_unformatted_number_interpolation():
    src = "a = `${item.currency} ${item.price}`;\nb = `${item.price.toLocaleString()}`;"
    hits = lc.scan_js(src, "t.html")
    assert [(h["where"], h["kind"]) for h in hits] == [("1행", "서식 없는 숫자 보간")]
    assert lc.scan_js("s = `account_id ${accountId}`;", "t.html") == []   # accountId 안의 count는 숫자 필드 아님


def test_dst_shift_on_reset():
    table = lc.reset_local_times(["Europe/Berlin", "Asia/Tokyo"], ["2026-10-25", "2026-10-26"])
    assert table["2026-10-25"]["Europe/Berlin"].strftime("%H:%M") == "22:00"
    assert table["2026-10-26"]["Europe/Berlin"].strftime("%H:%M") == "21:00"
    assert lc.shifts(table) == [("Europe/Berlin", "2026-10-25", "2026-10-26", "22:00 CEST", "21:00 CET")]


def test_fold_and_gap():
    assert lc.classify_local(datetime(2026, 11, 1, 1, 30), "America/New_York")[0] == "fold"
    assert lc.classify_local(datetime(2027, 3, 14, 2, 30), "America/New_York")[0] == "gap"
    assert lc.classify_local(datetime(2026, 11, 1, 1, 30), "Asia/Tokyo")[0] == "normal"
    kind, cands = lc.classify_local(datetime(2026, 11, 1, 1, 30), "America/New_York")
    assert [c.utcoffset().total_seconds() / 3600 for c in cands] == [-4, -5]


def test_fixed_offset_errors():
    table = lc.reset_local_times(["America/New_York"], ["2026-10-24", "2026-11-02"])
    assert lc.fixed_offset_errors(table) == [("2026-11-02", "America/New_York", "16:00", "15:00")]
