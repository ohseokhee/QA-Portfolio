"""
Day 80 : KBO 선수 조회 판별 로직·요청 간격 테스트 (외부 요청 없음)
실행: py -m pytest day80_test_kbo_lookup.py -v
"""

import pytest

from day80_kbo_lookup import Player, RateLimiter, disambiguate

KIM_LG = Player("Q1", "김현수", "1988-01-12", [("두산 베어스", "2006", "2015"), ("LG 트윈스", "2018", "")])
KIM_OLD = Player("Q2", "김현수", "1973-01-01", [])
KIM_LOTTE_A = Player("Q3", "김현수", "1995-03-02", [("롯데 자이언츠", "2014", "")])
KIM_LOTTE_B = Player("Q4", "김현수", "1999-07-21", [("롯데 자이언츠", "2018", "")])


@pytest.mark.parametrize("candidates, team, birth, status, expected", [
    pytest.param([KIM_LG], None, None, "unique", ["Q1"], id="KBO-01 후보 1명이면 바로 확정"),
    pytest.param([KIM_LG, KIM_OLD], None, None, "ambiguous", ["Q1", "Q2"], id="KBO-02 동명이인, 조건 없음 → 추가 정보 필요"),
    pytest.param([KIM_LG, KIM_OLD], "LG", None, "unique", ["Q1"], id="KBO-03 팀으로 확정"),
    pytest.param([KIM_LG, KIM_OLD], "두산", None, "unique", ["Q1"], id="KBO-04 과거 소속팀으로도 확정"),
    pytest.param([KIM_LOTTE_A, KIM_LOTTE_B], "롯데", None, "ambiguous", ["Q3", "Q4"], id="KBO-05 같은 팀 동명이인 → 아직 모호"),
    pytest.param([KIM_LOTTE_A, KIM_LOTTE_B], "롯데", "1999", "unique", ["Q4"], id="KBO-06 팀 다음 생년으로 확정"),
    pytest.param([KIM_LOTTE_A, KIM_LOTTE_B], "롯데", "1995-03-02", "unique", ["Q3"], id="KBO-07 생년월일 전체로 확정"),
    pytest.param([KIM_LG, KIM_OLD], "한화", None, "not_found", [], id="KBO-08 팀 불일치 → 없음"),
    pytest.param([KIM_LG, KIM_OLD], None, "1973", "unique", ["Q2"], id="KBO-09 팀 없이 생년만으로 확정"),
    pytest.param([KIM_LG], "NC", None, "not_found", [], id="KBO-10 후보 1명이어도 팀이 다르면 없음"),
    pytest.param([], None, None, "not_found", [], id="KBO-11 이름 일치 0명"),
    pytest.param([KIM_LG, KIM_OLD], "lg 트윈스", None, "unique", ["Q1"], id="KBO-12 팀 이름 공백·대소문자 무시"),
    pytest.param([KIM_LG, KIM_OLD], None, "1988-01-13", "not_found", [], id="KBO-13 생년월일 하루 차이 → 없음"),
])
def test_disambiguate(candidates, team, birth, status, expected):
    result = disambiguate(candidates, team, birth)
    assert result["status"] == status
    assert [p.qid for p in result["players"]] == expected


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 3))
        self.now += seconds


def test_rate_limiter_first_request_no_wait():
    fake = FakeClock()
    RateLimiter(1.0, fake.clock, fake.sleep).wait()
    assert fake.slept == []


def test_rate_limiter_waits_remaining_time():
    fake = FakeClock()
    limiter = RateLimiter(1.0, fake.clock, fake.sleep)
    limiter.wait()
    fake.now += 0.3  # 0.3초 뒤 다음 요청
    limiter.wait()
    assert fake.slept == [0.7]


def test_rate_limiter_no_wait_after_interval():
    fake = FakeClock()
    limiter = RateLimiter(1.0, fake.clock, fake.sleep)
    limiter.wait()
    fake.now += 1.5
    limiter.wait()
    assert fake.slept == []


def test_rate_limiter_consecutive_calls_spaced_one_second():
    fake = FakeClock()
    limiter = RateLimiter(1.0, fake.clock, fake.sleep)
    times = []
    for _ in range(4):
        limiter.wait()
        times.append(fake.now)
    gaps = [round(b - a, 3) for a, b in zip(times, times[1:])]
    assert gaps == [1.0, 1.0, 1.0]
