"""
Day 89 : LQA 점검 규칙별 pytest
- 결함 없는 원본 데이터는 탐지 0건이어야 함 (오탐 확인)
- 규칙마다 결함 1개를 직접 넣어 해당 규칙만 잡히는지 확인
실행: py -m pytest day89_test_lqa_lint.py -v
"""

import copy

import pytest

import day89_lqa_lint as lint
import day89_make_strings as mk

GLOSSARY = [{"term_ko": t, "lang": l, "required": r, "forbidden": f} for t, l, r, f in mk.GLOSSARY]


@pytest.fixture
def clean():
    return mk.build_clean()


def run(data):
    return {(d["lang"], d["key"], d["rule"]) for d in lint.lint(data, mk.BUDGET, GLOSSARY)}


def test_clean_data_has_no_findings(clean):
    assert run(clean) == set()


def test_display_width_rules():
    assert lint.display_width("구매") == 4                      # 전각 2칸
    assert lint.display_width("Buy") == 3
    assert lint.display_width("ซื้อ") == 2                       # 태국어 결합 문자 0칸
    assert lint.display_width("<b>A</b>{count}") == 1 + 6       # 태그 제외, 자리표시자 6칸


@pytest.mark.parametrize("value,label", [(None, "missing"), ("btn.login", "id")])
def test_r1_missing_or_id_exposed(clean, value, label):
    if value is None:
        del clean["en"]["btn.login"]
    else:
        clean["en"]["btn.login"] = value
    assert run(clean) == {("en", "btn.login", "R1")}


def test_r2_untranslated(clean):
    clean["es"]["status.empty"] = mk.KO["status.empty"]
    assert run(clean) == {("es", "status.empty", "R2")}


def test_r3_placeholder_and_tag(clean):
    clean["en"]["msg.buy_done"] = "Purchased {count} of {itme}!"
    clean["ja"]["msg.limit"] = "<b>所持上限の999個を超えることはできません。"
    assert run(clean) == {("en", "msg.buy_done", "R3"), ("ja", "msg.limit", "R3")}


def test_r4_number_mismatch(clean):
    clean["zh-TW"]["item.103.desc"] = clean["zh-TW"]["item.103.desc"].replace("20%", "25%")
    assert run(clean) == {("zh-TW", "item.103.desc", "R4")}


def test_r4_ignores_color_code_digits(clean):
    assert "#FFD700" in clean["en"]["item.103.desc"]
    assert ("en", "item.103.desc", "R4") not in run(clean)


def test_r5_forbidden_and_missing_term(clean):
    clean["en"]["btn.inventory"] = "View Bag"
    clean["th"]["item.101.name"] = "แพ็คนักเตะพรีเมียม"
    assert run(clean) == {("en", "btn.inventory", "R5"), ("th", "item.101.name", "R5")}


def test_r6_length_budget(clean):
    clean["es"]["btn.buy"] = "Comprar ahora mismo"
    assert run(clean) == {("es", "btn.buy", "R6")}


def test_r7_script_mixing(clean):
    clean["ja"]["msg.buy_done"] = "{item}を{count}個구매しました！"
    clean["zh-TW"]["table.qty"] = "数量"
    clean["th"]["status.empty"] = "Empty"
    assert run(clean) == {("ja", "msg.buy_done", "R7"), ("zh-TW", "table.qty", "R7"), ("th", "status.empty", "R7")}


def test_r8_punctuation_and_spacing(clean):
    clean["es"]["msg.buy_confirm"] = "Comprar {count} de {item}?"
    clean["en"]["status.need_login"] = "Please log  in first"
    clean["zh-TW"]["msg.buy_done"] = "已購買{count}個{item}!"
    assert run(clean) == {("es", "msg.buy_confirm", "R8"), ("en", "status.need_login", "R8"),
                          ("zh-TW", "msg.buy_done", "R8")}


def test_r9_inconsistent_translation(clean):
    clean["en"]["menu.buy"] = "Purchase"
    assert run(clean) == {("en", "menu.buy", "R9")}


def test_seeding_is_deterministic_and_within_range():
    a = mk.seed_defects(mk.build_clean())
    b = mk.seed_defects(mk.build_clean())
    assert a == b
    assert 10 <= len(a) <= 12
    assert {d["rule"] for d in a} == set(mk.RULES)


def test_score_counts(tmp_path):
    key = tmp_path / "key.json"
    key.write_text('{"defects": [{"lang": "en", "key": "a", "rule": "R1"}, {"lang": "ja", "key": "b", "rule": "R2"}]}',
                   encoding="utf-8")
    sc = lint.score([{"lang": "en", "key": "a", "rule": "R1"}, {"lang": "th", "key": "c", "rule": "R6"}], str(key))
    assert (sc["tp"], sc["precision"], sc["recall"]) == (1, 0.5, 0.5)
