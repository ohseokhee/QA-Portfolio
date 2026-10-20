"""
Day 87 : 확률형 아이템 검증 로직 테스트 (통계 함수 정확도, 천장·10연차 규칙, 결함 빌드 탐지)
실행: py -m pytest day87_test_gacha.py -v
"""

import pytest

from day87_gacha import PITY, GachaMachine
from day87_gacha_verify import check_base_rate, check_multi, check_pity, chi2_sf, simulate, wilson


@pytest.mark.parametrize("stat, df, expected", [
    pytest.param(7.8147, 3, 0.05, id="GA-01 카이제곱 df=3 임계값 → p 0.05"),
    pytest.param(13.8155, 2, 0.001, id="GA-02 카이제곱 df=2 임계값 → p 0.001"),
    pytest.param(0.5, 2, 0.7788, id="GA-03 df=2 닫힌 식 exp(-x/2)과 일치"),
])
def test_chi2_sf(stat, df, expected):
    assert chi2_sf(stat, df) == pytest.approx(expected, abs=1e-4)


def test_wilson_interval_contains_rate():
    low, high = wilson(150, 10_000)
    assert low < 0.015 < high


class FixedRng:
    """항상 가장 큰 값(R 등급)만 나오게 하는 가짜 난수"""
    def randrange(self, total):
        return total - 1


def test_pity_triggers_exactly_on_80th_draw():
    machine = GachaMachine("v2")
    machine.rng = FixedRng()
    grades = [machine.single()["grade"] for _ in range(PITY)]
    assert grades[:PITY - 1] == ["R"] * (PITY - 1)
    assert grades[-1] == "SSR" and machine.log[-1]["forced"] == "pity"
    assert machine.since_ssr == 0


def test_pity_off_by_one_in_v1():
    machine = GachaMachine("v1")
    machine.rng = FixedRng()
    grades = [machine.single()["grade"] for _ in range(PITY + 1)]
    assert grades[PITY - 1] == "R" and grades[PITY] == "SSR"


def test_multi_guarantees_sr_or_better():
    machine = GachaMachine("v2")
    machine.rng = FixedRng()
    results = machine.multi()
    assert [r["grade"] for r in results[:9]] == ["R"] * 9
    assert results[9]["grade"] in ("SR", "SSR") and results[9]["forced"] == "multi"


def test_v2_passes_all_checks():
    log = simulate("v2", 100_000)
    assert check_base_rate(log)["ok"] and check_pity(log)["ok"] and check_multi(log)["ok"]


def test_v1_detected_by_base_rate_and_pity():
    log = simulate("v1", 100_000)
    assert not check_base_rate(log)["ok"]
    assert check_pity(log)["longest"] == PITY + 1
