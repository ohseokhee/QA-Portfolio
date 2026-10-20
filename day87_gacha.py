"""
Day 87 : 확률형 아이템(뽑기) 서버 로직 모의 구현
- 공시 확률표(ANNOUNCED)와 빌드별 서버 확률표(BUILDS)를 분리 → 공시값과 서버값이 어긋나는 상황을 재현
- 규칙
	R1 등급 기본 확률: SSR 1.5% / SR 13.5% / R 85%
	R2 천장: SSR 없이 79회 연속이면 80번째는 SSR 확정, SSR을 얻으면(확정·일반 모두) 카운터 0
	R3 10연차: 10회 중 앞 9회에 SR 이상이 없으면 10번째는 SR 이상 확정 (SR:SSR = 기본 확률 비율)
- 모든 뽑기는 로그(dict)로 남기고 확정 뽑기에는 forced 사유를 기록 → 검증 스크립트가 로그만으로 판정
"""

import random

GRADES = ["SSR", "SR", "R"]
ANNOUNCED = {"SSR": 0.015, "SR": 0.135, "R": 0.85}
PITY = 80
MULTI = 10

# 빌드별 서버 설정. v1은 운영 데이터 입력 실수(SSR 가중치)와 천장 판정 비교 연산 실수를 재현한 빌드
BUILDS = {
    "v1": {"weights": {"SSR": 12, "SR": 138, "R": 850}, "pity_check": "gt"},
    "v2": {"weights": {"SSR": 15, "SR": 135, "R": 850}, "pity_check": "ge"},
}


class GachaMachine:
    def __init__(self, build="v2", seed=None):
        cfg = BUILDS[build]
        self.build = build
        self.weights = cfg["weights"]
        self.pity_check = cfg["pity_check"]
        self.rng = random.Random(seed)
        self.since_ssr = 0  # 마지막 SSR 이후 뽑기 수
        self.multi_count = 0
        self.log = []

    def _roll(self, pool):
        total = sum(self.weights[g] for g in pool)
        pick = self.rng.randrange(total)
        for g in pool:
            pick -= self.weights[g]
            if pick < 0:
                return g
        return pool[-1]

    def _pity_reached(self):
        # since_ssr = 지금까지 SSR 없이 지나간 횟수. 79회가 지났으면 이번이 80번째
        if self.pity_check == "ge":
            return self.since_ssr >= PITY - 1
        return self.since_ssr > PITY - 1

    def _draw(self, multi_index=None, guarantee_sr=False):
        if self._pity_reached():
            grade, forced = "SSR", "pity"
        elif guarantee_sr:
            grade, forced = self._roll(["SSR", "SR"]), "multi"
        else:
            grade, forced = self._roll(GRADES), None
        self.since_ssr = 0 if grade == "SSR" else self.since_ssr + 1
        entry = {"n": len(self.log) + 1, "grade": grade, "forced": forced, "multi": multi_index}
        self.log.append(entry)
        return entry

    def single(self):
        return self._draw()

    def multi(self):
        """10연차 1회. multi 값은 몇 번째 10연차인지"""
        self.multi_count += 1
        results = []
        for i in range(MULTI):
            need_sr = i == MULTI - 1 and all(r["grade"] == "R" for r in results)
            results.append(self._draw(self.multi_count, need_sr))
        return results
