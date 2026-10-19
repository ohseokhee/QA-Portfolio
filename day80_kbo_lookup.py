"""
Day 80 : KBO 선수 조회 (파이썬 공개판)
- 공개 데이터: Wikidata SPARQL (KBO 공식 홈페이지는 robots.txt에서 자동 수집을 금지해 사용하지 않음)
- 요청 간격 제한: 외부 요청 사이 최소 1초 (RateLimiter, 테스트에서 가짜 시계로 검증)
- 동명이인 판별: 이름으로 후보 조회 → 팀(소속 이력 부분 일치) → 생년월일(YYYY 또는 YYYY-MM-DD) 순서로 좁힘
실행: py day80_kbo_lookup.py 김현수 [--team LG] [--birth 1988-01-12]
      py day80_kbo_lookup.py --demo
"""

import argparse
import sys
import time
from dataclasses import dataclass, field

import requests

sys.stdout.reconfigure(encoding="utf-8")

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "QA-Portfolio-kbo-lookup/1.0 (https://github.com/ohseokhee/QA-Portfolio)"
BASEBALL_PLAYER = "Q10871364"
QUERY = """
SELECT ?p ?birth ?st ?teamLabel ?start ?end WHERE {{
  ?p rdfs:label "{name}"@ko ; wdt:P106 wd:{occupation} .
  OPTIONAL {{ ?p wdt:P569 ?birth }}
  OPTIONAL {{ ?p p:P54 ?st . ?st ps:P54 ?team .
             OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }} }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ko,en". }}
}}
"""
DEMO_QUERIES = [
    ("김현수", None, None),
    ("김현수", "LG", None),
    ("김현수", None, "1973"),
    ("김현수", "롯데", None),
    ("이대호", None, None),
    ("존재하지않는선수", None, None),
]


class RateLimiter:
    """마지막 요청 시각부터 min_interval초가 지나기 전이면 남은 시간만큼 기다린다"""

    def __init__(self, min_interval=1.0, clock=time.monotonic, sleep=time.sleep):
        self.min_interval = min_interval
        self.clock = clock
        self.sleep = sleep
        self.last = None

    def wait(self):
        now = self.clock()
        if self.last is not None:
            remaining = self.min_interval - (now - self.last)
            if remaining > 0:
                self.sleep(remaining)
                now = self.clock()
        self.last = now


@dataclass
class Player:
    qid: str
    name: str
    birth: str = ""  # YYYY-MM-DD
    teams: list = field(default_factory=list)  # [(팀 이름, 시작 연도, 종료 연도)]


def normalize(text):
    return "".join((text or "").split()).lower()


def matches_team(player, team):
    key = normalize(team)
    return any(key in normalize(name) for name, _, _ in player.teams)


def matches_birth(player, birth):
    return bool(player.birth) and player.birth.startswith(birth.strip())


def disambiguate(candidates, team=None, birth=None):
    """후보를 팀 → 생년월일 순으로 좁힌다. status: unique / ambiguous / not_found"""
    steps = [f"이름 일치 {len(candidates)}명"]
    current = list(candidates)
    if not current:
        return {"status": "not_found", "players": [], "steps": steps}
    if len(current) > 1 or team:
        if team:
            current = [p for p in current if matches_team(p, team)]
            steps.append(f"팀 '{team}' 일치 {len(current)}명")
    if (len(current) > 1 or birth) and current:
        if birth:
            current = [p for p in current if matches_birth(p, birth)]
            steps.append(f"생년월일 '{birth}' 일치 {len(current)}명")
    status = "unique" if len(current) == 1 else ("not_found" if not current else "ambiguous")
    if status == "ambiguous":
        steps.append("추가 정보 필요 (팀 또는 생년월일)" if not (team and birth) else "동일 조건 후보 여러 명")
    return {"status": status, "players": current, "steps": steps}


class WikidataClient:
    def __init__(self, limiter=None, session=None):
        self.limiter = limiter or RateLimiter(1.0)
        self.session = session or requests.Session()
        self.session.trust_env = False  # 시스템 프록시(Fiddler 등) 미사용
        self.session.headers["User-Agent"] = USER_AGENT
        self.requests = 0
        self.sent_at = []  # 요청 시작 시각 (간격 확인용)

    def search(self, name):
        self.limiter.wait()
        self.requests += 1
        self.sent_at.append(time.monotonic())
        res = self.session.get(SPARQL_URL, timeout=30, headers={"Accept": "application/sparql-results+json"},
                               params={"query": QUERY.format(name=name.replace('"', ""), occupation=BASEBALL_PLAYER)})
        res.raise_for_status()
        players, stints = {}, {}
        for b in res.json()["results"]["bindings"]:
            qid = b["p"]["value"].rsplit("/", 1)[-1]
            players.setdefault(qid, Player(qid=qid, name=name, birth=b.get("birth", {}).get("value", "")[:10]))
            if "teamLabel" in b:
                # 소속 기록(statement) 하나에 시작·종료 값이 여러 개면 조합 행이 늘어나므로 기록 단위로 묶음
                st = stints.setdefault(b["st"]["value"], {"qid": qid, "team": b["teamLabel"]["value"],
                                                         "starts": set(), "ends": set()})
                if "start" in b:
                    st["starts"].add(b["start"]["value"][:4])
                if "end" in b:
                    st["ends"].add(b["end"]["value"][:4])
        for st in stints.values():
            players[st["qid"]].teams.append((st["team"], min(st["starts"], default=""), max(st["ends"], default="")))
        for p in players.values():
            p.teams.sort(key=lambda t: t[1] or "9999")
        return list(players.values())


def describe(p):
    teams = ", ".join(f"{n}({s or '?'}~{e})" if s or e else n for n, s, e in p.teams) or "소속 정보 없음"
    return f"{p.name} [{p.qid}] 생년월일 {p.birth or '정보 없음'} / {teams}"


def lookup(client, name, team=None, birth=None):
    started = time.monotonic()
    candidates = client.search(name)
    result = disambiguate(candidates, team, birth)
    cond = " ".join(x for x in [f"팀={team}" if team else "", f"생년={birth}" if birth else ""] if x) or "조건 없음"
    print(f"\n▶ {name} ({cond}) → {result['status']}  [{' → '.join(result['steps'])}]  "
          f"(간격 대기+요청 {time.monotonic() - started:.1f}초)")
    for p in result["players"] if result["status"] != "not_found" else candidates:
        print(f"    - {describe(p)}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("--team")
    parser.add_argument("--birth")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    client = WikidataClient()
    queries = DEMO_QUERIES if args.demo else [(args.name, args.team, args.birth)]
    print(f"[조회] Wikidata SPARQL, 요청 간격 최소 {client.limiter.min_interval}초, 질의 {len(queries)}건")
    started = time.monotonic()
    summary = {}
    for name, team, birth in queries:
        status = lookup(client, name, team, birth)["status"]
        summary[status] = summary.get(status, 0) + 1
    elapsed = time.monotonic() - started
    gaps = [b - a for a, b in zip(client.sent_at, client.sent_at[1:])]
    print(f"\n[결과] 질의 {len(queries)}건, 외부 요청 {client.requests}회, {elapsed:.1f}초, "
          f"요청 시작 간격 최소 {min(gaps, default=0):.2f}초 / 판별 결과 {summary}")


if __name__ == "__main__":
    main()
