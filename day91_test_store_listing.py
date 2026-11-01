"""
Day 91 : App Store 등록정보 점검 로직 테스트
- 네트워크 없이 day91_fixtures/ 저장본과 직접 만든 등록정보로 판정 재현
실행: py -m pytest day91_test_store_listing.py -v
"""

import pytest
import requests

import day91_store_listing_check as sc


def base(**kw):
    r = {"trackName": "Game", "version": "1.0", "currentVersionReleaseDate": "2026-10-01T00:00:00Z",
         "releaseNotes": "Bug fixes", "languageCodesISO2A": ["EN", "KO", "JA", "ZH", "TH", "ES"],
         "contentAdvisoryRating": "12+", "formattedPrice": "Free", "currency": "USD", "minimumOsVersion": "15.0"}
    r.update(kw)
    return r


def all_countries(**overrides):
    cur = sc.STORE_CURRENCY
    out = {c: base(currency=cur[c], releaseNotes={"kr": "버그 수정", "jp": "不具合を修正しました", "tw": "修正錯誤", "th": "แก้ไขข้อบกพร่อง"}.get(c, "Bug fixes"))
           for c in sc.COUNTRIES}
    out.update(overrides)
    return out


@pytest.mark.parametrize("text, expected", [
    ("버그 수정", "Hangul"), ("不具合を修正しました", "Japanese"), ("修正錯誤", "Han"),
    ("แก้ไขข้อบกพร่อง", "Thai"), ("Bug fixes 1.2", "Latin"), ("", None), ("1.0.3 !!", None),
])
def test_script_of(text, expected):
    assert sc.script_of(text) == expected


def test_clean_listing_has_no_notes():
    rows, notes = sc.check_game(all_countries())
    assert notes == []
    assert all(v["lang_ok"] for v in rows.values())


def test_detects_each_rule():
    listings = all_countries(
        kr=None,                                                   # C1 미출시
        us=base(version="1.1", currency="USD"),                    # C2 버전 차이
        th=base(currency="THB", releaseNotes="Bug fixes"),         # C3 노트가 라틴 문자
        es=base(currency="USD", languageCodesISO2A=["EN"]),        # C4 언어 없음, C6 통화
        jp=base(currency="JPY", contentAdvisoryRating="17+", releaseNotes="不具合を修正しました"),  # C5
        tw=base(currency="TWD", minimumOsVersion="16.0", releaseNotes="修正錯誤"),            # C7
    )
    rows, notes = sc.check_game(listings)
    assert sorted({cid for cid, _ in notes}) == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert rows["kr"] is None


def test_rate_limiter_keeps_3_seconds():
    now = [0.0]
    slept = []
    lim = sc.RateLimiter(3.0, clock=lambda: now[0], sleep=lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)))
    lim.wait(); now[0] += 1.0; lim.wait(); now[0] += 5.0; lim.wait()
    assert slept == [2.0]
    assert [b - a for a, b in zip(lim.starts, lim.starts[1:])] == [3.0, 5.0]


def test_pick_track_from_saved_search():
    s = sc.load(sc.FIXTURE_DIR, "search_fcmobile.json")
    assert sc.pick_track(s, "Electronic Arts", ("FC Mobile", "FC Soccer Mobile")) == 1094930513   # Companion 앱 제외
    s = sc.load(sc.FIXTURE_DIR, "search_epicseven.json")
    assert sc.pick_track(s, "Smilegate", ("에픽세븐", "Epic Seven")) == 1322399438               # 같은 검색의 다른 판매자 앱 제외
    assert sc.pick_track(s, "Smilegate", ("없는 이름",)) is None


def test_run_checks_offline_from_fixtures(monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("네트워크 사용 금지")
    monkeypatch.setattr(requests.Session, "get", no_network)
    results = sc.run_checks()
    ids = {k: v[1] for k, v in results.items()}
    assert ids == {"epicseven": 1322399438, "fcmobile": 1094930513, "sevenknights_rebirth": 6479595079}
    notes = [cid for _, _, _, n in results.values() for cid, _ in n]
    assert notes.count("C3") == 3 and notes.count("C1") == 1 and notes.count("C4") == 1
    assert results["fcmobile"][2]["kr"] is None
