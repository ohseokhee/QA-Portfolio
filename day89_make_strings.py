"""
Day 89 : 다국어 문자열 리소스 생성 + LQA 결함 시딩
1) 모의 상점 화면 문자열(명세 1.4 아이템 이름, Day 65 상점 페이지 버튼·상태 문구)을
   기준어 한국어 + en, ja, zh-TW, th, es 리소스 JSON으로 만든다 (day89_strings/)
   - 번역문은 연습용으로 만든 데이터 (실제 게임 번역 아님)
2) 키별 표시 폭 예산(_budget.json)과 용어집(day89_glossary.csv)을 함께 저장
3) 고정 seed(89) 무작위로 LQA 결함 10~12개를 주입하고 정답표는 sealed/day89_answer_key.json에 저장
   - 콘솔에는 시딩 개수만 출력 (결함 위치는 출력하지 않음)
실행: py day89_make_strings.py
"""

import copy
import csv
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STRINGS_DIR = os.path.join(BASE_DIR, "day89_strings")
GLOSSARY_CSV = os.path.join(BASE_DIR, "day89_glossary.csv")
ANSWER_KEY = os.path.join(BASE_DIR, "sealed", "day89_answer_key.json")
SEED = 89
LANGS = ["en", "ja", "zh-TW", "th", "es"]
NOTE = "연습용으로 만든 번역 데이터 (실제 게임 번역 아님)"

# 기준어 한국어 (키: 문자열)
KO = {
    "shop.title": "모의 게임 상점",
    "btn.login": "로그인",
    "btn.currency": "재화 조회",
    "btn.inventory": "인벤토리 조회",
    "btn.buy": "구매",
    "dialog.buy.ok": "구매",
    "menu.buy": "구매",
    "table.item": "아이템",
    "table.price": "가격",
    "table.qty": "수량",
    "status.logged_in": "로그인됨: {account_id}",
    "status.login_failed": "로그인 실패: {error_code}",
    "status.empty": "비어 있음",
    "status.need_login": "먼저 로그인하세요",
    "item.101.name": "프리미엄 선수팩",
    "item.102.name": "일반 선수팩",
    "item.103.name": "훈련 부스터",
    "item.104.name": "클럽 유니폼 세트",
    "item.105.name": "이벤트 한정팩",
    "item.103.desc": "훈련 효과 <color=#FFD700>20%</color> 증가 (30분)",
    "msg.buy_confirm": "{item}을(를) {count}개 구매하시겠습니까?",
    "msg.buy_done": "{item} {count}개 구매 완료!",
    "msg.insufficient": "{currency}이(가) 부족합니다.",
    "msg.limit": "<b>보유 상한</b> 999개를 넘을 수 없습니다.",
    "msg.max_per_buy": "한 번에 최대 10개까지 구매할 수 있습니다.",
    "msg.event_ended": "이벤트 판매가 종료되었습니다.",
    "msg.inventory_title": "인벤토리",
}

# 키별 최대 표시 폭 (전각 2칸, 태국어 결합 문자 0칸, 자리표시자 6칸, 태그 제외)
BUDGET = {
    "shop.title": 28, "btn.login": 16, "btn.currency": 20, "btn.inventory": 24,
    "btn.buy": 12, "dialog.buy.ok": 12, "menu.buy": 12,
    "table.item": 14, "table.price": 12, "table.qty": 12,
    "status.logged_in": 32, "status.login_failed": 40, "status.empty": 20, "status.need_login": 28,
    "item.101.name": 30, "item.102.name": 30, "item.103.name": 30, "item.104.name": 30, "item.105.name": 30,
    "item.103.desc": 48, "msg.buy_confirm": 56, "msg.buy_done": 48, "msg.insufficient": 44,
    "msg.limit": 56, "msg.max_per_buy": 56, "msg.event_ended": 48, "msg.inventory_title": 16,
}

TR = {
    "en": {
        "shop.title": "Mock Game Shop",
        "btn.login": "Log In",
        "btn.currency": "Check Currency",
        "btn.inventory": "View Inventory",
        "btn.buy": "Buy", "dialog.buy.ok": "Buy", "menu.buy": "Buy",
        "table.item": "Item", "table.price": "Price", "table.qty": "Qty",
        "status.logged_in": "Logged in: {account_id}",
        "status.login_failed": "Login failed: {error_code}",
        "status.empty": "Empty",
        "status.need_login": "Please log in first",
        "item.101.name": "Premium Player Pack",
        "item.102.name": "Standard Player Pack",
        "item.103.name": "Training Booster",
        "item.104.name": "Club Uniform Set",
        "item.105.name": "Limited Event Pack",
        "item.103.desc": "Training effect +<color=#FFD700>20%</color> (30 min)",
        "msg.buy_confirm": "Buy {count} of {item}?",
        "msg.buy_done": "Purchased {count} of {item}!",
        "msg.insufficient": "Not enough {currency}.",
        "msg.limit": "Cannot exceed the <b>holding limit</b> of 999.",
        "msg.max_per_buy": "You can buy up to 10 at a time.",
        "msg.event_ended": "Event sales have ended.",
        "msg.inventory_title": "Inventory",
    },
    "ja": {
        "shop.title": "模擬ゲームショップ",
        "btn.login": "ログイン",
        "btn.currency": "通貨を確認",
        "btn.inventory": "インベントリを見る",
        "btn.buy": "購入", "dialog.buy.ok": "購入", "menu.buy": "購入",
        "table.item": "アイテム", "table.price": "価格", "table.qty": "数量",
        "status.logged_in": "ログイン中：{account_id}",
        "status.login_failed": "ログイン失敗：{error_code}",
        "status.empty": "なし",
        "status.need_login": "先にログインしてください",
        "item.101.name": "プレミアム選手パック",
        "item.102.name": "通常選手パック",
        "item.103.name": "トレーニングブースター",
        "item.104.name": "クラブユニフォームセット",
        "item.105.name": "イベント限定パック",
        "item.103.desc": "トレーニング効果<color=#FFD700>20%</color>アップ（30分）",
        "msg.buy_confirm": "{item}を{count}個購入しますか？",
        "msg.buy_done": "{item}を{count}個購入しました！",
        "msg.insufficient": "{currency}が不足しています。",
        "msg.limit": "<b>所持上限</b>の999個を超えることはできません。",
        "msg.max_per_buy": "一度に最大10個まで購入できます。",
        "msg.event_ended": "イベント販売は終了しました。",
        "msg.inventory_title": "インベントリ",
    },
    "zh-TW": {
        "shop.title": "模擬遊戲商店",
        "btn.login": "登入",
        "btn.currency": "查詢貨幣",
        "btn.inventory": "查看背包",
        "btn.buy": "購買", "dialog.buy.ok": "購買", "menu.buy": "購買",
        "table.item": "道具", "table.price": "價格", "table.qty": "數量",
        "status.logged_in": "已登入：{account_id}",
        "status.login_failed": "登入失敗：{error_code}",
        "status.empty": "空",
        "status.need_login": "請先登入",
        "item.101.name": "高級球員包",
        "item.102.name": "一般球員包",
        "item.103.name": "訓練加速器",
        "item.104.name": "俱樂部球衣組",
        "item.105.name": "活動限定包",
        "item.103.desc": "訓練效果提升<color=#FFD700>20%</color>（30分鐘）",
        "msg.buy_confirm": "確定購買{count}個{item}嗎？",
        "msg.buy_done": "已購買{count}個{item}！",
        "msg.insufficient": "{currency}不足。",
        "msg.limit": "無法超過<b>持有上限</b>999個。",
        "msg.max_per_buy": "每次最多可購買10個。",
        "msg.event_ended": "活動販售已結束。",
        "msg.inventory_title": "背包",
    },
    "th": {
        "shop.title": "ร้านค้าเกมจำลอง",
        "btn.login": "เข้าสู่ระบบ",
        "btn.currency": "ตรวจสอบสกุลเงิน",
        "btn.inventory": "ดูคลังไอเทม",
        "btn.buy": "ซื้อ", "dialog.buy.ok": "ซื้อ", "menu.buy": "ซื้อ",
        "table.item": "ไอเทม", "table.price": "ราคา", "table.qty": "จำนวน",
        "status.logged_in": "เข้าสู่ระบบแล้ว: {account_id}",
        "status.login_failed": "เข้าสู่ระบบไม่สำเร็จ: {error_code}",
        "status.empty": "ว่างเปล่า",
        "status.need_login": "กรุณาเข้าสู่ระบบก่อน",
        "item.101.name": "แพ็กนักเตะพรีเมียม",
        "item.102.name": "แพ็กนักเตะทั่วไป",
        "item.103.name": "บูสเตอร์ฝึกซ้อม",
        "item.104.name": "ชุดยูนิฟอร์มสโมสร",
        "item.105.name": "แพ็กลิมิเต็ดอีเวนต์",
        "item.103.desc": "เอฟเฟกต์การฝึกเพิ่มขึ้น <color=#FFD700>20%</color> (30 นาที)",
        "msg.buy_confirm": "ต้องการซื้อ {item} จำนวน {count} ชิ้นหรือไม่",
        "msg.buy_done": "ซื้อ {item} จำนวน {count} ชิ้นสำเร็จ!",
        "msg.insufficient": "{currency} ไม่เพียงพอ",
        "msg.limit": "ไม่สามารถเกิน<b>ขีดจำกัดการถือครอง</b> 999 ชิ้นได้",
        "msg.max_per_buy": "ซื้อได้สูงสุดครั้งละ 10 ชิ้น",
        "msg.event_ended": "การขายในอีเวนต์สิ้นสุดแล้ว",
        "msg.inventory_title": "คลังไอเทม",
    },
    "es": {
        "shop.title": "Tienda de juego simulada",
        "btn.login": "Iniciar sesión",
        "btn.currency": "Consultar moneda",
        "btn.inventory": "Ver inventario",
        "btn.buy": "Comprar", "dialog.buy.ok": "Comprar", "menu.buy": "Comprar",
        "table.item": "Objeto", "table.price": "Precio", "table.qty": "Cantidad",
        "status.logged_in": "Sesión iniciada: {account_id}",
        "status.login_failed": "Error al iniciar sesión: {error_code}",
        "status.empty": "Vacío",
        "status.need_login": "Inicia sesión primero",
        "item.101.name": "Sobre de jugadores prémium",
        "item.102.name": "Sobre de jugadores estándar",
        "item.103.name": "Potenciador de entrenamiento",
        "item.104.name": "Conjunto de uniforme del club",
        "item.105.name": "Sobre limitado del evento",
        "item.103.desc": "Efecto de entrenamiento +<color=#FFD700>20%</color> (30 min)",
        "msg.buy_confirm": "¿Comprar {count} de {item}?",
        "msg.buy_done": "¡Has comprado {count} de {item}!",
        "msg.insufficient": "No tienes suficiente {currency}.",
        "msg.limit": "No puedes superar el <b>límite de posesión</b> de 999.",
        "msg.max_per_buy": "Puedes comprar hasta 10 a la vez.",
        "msg.event_ended": "La venta del evento ha terminado.",
        "msg.inventory_title": "Inventario",
    },
}

# 용어집: (한국어 용어, 언어, 정해진 번역, 금지 번역)
GLOSSARY = [
    ("선수팩", "en", "Player Pack", "Player Card Pack"),
    ("선수팩", "ja", "選手パック", "選手ガチャ"),
    ("선수팩", "zh-TW", "球員包", "球員卡包"),
    ("선수팩", "th", "แพ็กนักเตะ", "แพ็คนักเตะ"),
    ("선수팩", "es", "Sobre de jugadores", "Pack de jugadores"),
    ("훈련 부스터", "en", "Training Booster", "Training Buff"),
    ("훈련 부스터", "ja", "トレーニングブースター", "練習ブースト"),
    ("훈련 부스터", "zh-TW", "訓練加速器", "訓練增益"),
    ("훈련 부스터", "th", "บูสเตอร์ฝึกซ้อม", "บัฟฝึกซ้อม"),
    ("훈련 부스터", "es", "Potenciador de entrenamiento", "Booster de entrenamiento"),
    ("인벤토리", "en", "Inventory", "Bag"),
    ("인벤토리", "ja", "インベントリ", "持ち物"),
    ("인벤토리", "zh-TW", "背包", "倉庫"),
    ("인벤토리", "th", "คลังไอเทม", "กระเป๋า"),
    ("인벤토리", "es", "inventario", "mochila"),
    ("재화", "en", "Currency", "Money"),
    ("재화", "ja", "通貨", "お金"),
    ("재화", "zh-TW", "貨幣", "金錢"),
    ("재화", "th", "สกุลเงิน", "เงินตรา"),
    ("재화", "es", "moneda", "dinero"),
]

# 결함 주입용 대체 문자열
ALT_BUY = {"en": "Purchase", "ja": "買う", "zh-TW": "購入", "th": "สั่งซื้อ", "es": "Adquirir"}
VERBOSE = {
    "en": " (tap to see the full details of this item)",
    "ja": "（詳しい内容はこちらをタップして確認してください）",
    "zh-TW": "（點擊這裡即可查看此道具的詳細內容與說明）",
    "th": " (แตะที่นี่เพื่อดูรายละเอียดทั้งหมดของไอเทมนี้)",
    "es": " (toca aquí para ver todos los detalles de este objeto)",
}
SIMPLIFY = {"購": "购", "買": "买", "個": "个", "遊": "游", "戲": "戏", "訓": "训", "練": "练",
            "價": "价", "數": "数", "結": "结", "動": "动", "無": "无", "過": "过", "員": "员"}
RULES = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]


def build_clean():
    data = {"ko": dict(KO)}
    for lang in LANGS:
        data[lang] = dict(TR[lang])
    return data


def candidates(rule, data, lang):
    """규칙별로 결함을 넣을 수 있는 키 목록"""
    import re
    keys = list(KO)
    if rule in ("R1", "R2", "R6"):
        return keys
    if rule == "R3":
        return [k for k in keys if re.search(r"\{\w+\}|<[^>]+>", KO[k])]
    if rule == "R4":
        return [k for k in keys if re.search(r"\d", re.sub(r"<[^>]+>", "", KO[k]))]
    if rule == "R5":
        return [k for k in keys for term, gl, req, _ in GLOSSARY
                if gl == lang and term in KO[k] and req.lower() in data[lang][k].lower()]
    if rule == "R7":
        if lang == "ja":
            return [k for k in keys if "購入" in data[lang][k]]
        if lang == "zh-TW":
            return [k for k in keys if any(c in data[lang][k] for c in SIMPLIFY)]
        if lang == "th":
            return [k for k in keys if re.search(r"[A-Za-z]{3,}", re.sub(r"\{\w+\}|<[^>]+>", "", TR["en"][k]))]
        return []
    if rule == "R8":
        if lang == "es":
            return [k for k in keys if data[lang][k].startswith(("¿", "¡"))] + keys
        if lang in ("ja", "zh-TW"):
            return [k for k in keys if data[lang][k].endswith(("！", "？"))] + keys
        return keys
    if rule == "R9":
        return ["dialog.buy.ok", "menu.buy"]
    return []


def inject(rule, data, lang, key, rng):
    import re
    v = data[lang][key]
    if rule == "R1":
        if rng.random() < 0.5:
            del data[lang][key]
            return "missing"
        data[lang][key] = key
        return "id_exposed"
    if rule == "R2":
        data[lang][key] = KO[key]
        return "untranslated"
    if rule == "R3":
        tokens = re.findall(r"\{\w+\}|</?\w+(?:=[^>]*)?>", v)
        t = rng.choice(tokens)
        data[lang][key] = v.replace(t, "", 1) if not t.startswith("{") or rng.random() < 0.5 \
            else v.replace(t, t[:-2] + "x}", 1)
        return "token_" + t
    if rule == "R4":
        plain = re.sub(r"<[^>]+>", "", v)
        num = rng.choice(re.findall(r"\d+", plain))
        data[lang][key] = v.replace(num, str(int(num) + 5), 1)
        return f"number_{num}"
    if rule == "R5":
        for term, gl, req, forb in GLOSSARY:
            if gl == lang and term in KO[key] and req.lower() in v.lower():
                idx = v.lower().index(req.lower())
                data[lang][key] = v[:idx] + forb + v[idx + len(req):]
                return f"glossary_{term}"
    if rule == "R6":
        data[lang][key] = v + VERBOSE[lang]
        return "too_long"
    if rule == "R7":
        if lang == "ja":
            data[lang][key] = v.replace("購入", "구매", 1)
        elif lang == "zh-TW":
            c = next(c for c in v if c in SIMPLIFY)
            data[lang][key] = v.replace(c, SIMPLIFY[c], 1)
        else:
            data[lang][key] = TR["en"][key]
        return "script_mix"
    if rule == "R8":
        if v.startswith(("¿", "¡")):
            data[lang][key] = v[1:]
            return "inverted_mark"
        if v.endswith("！"):
            data[lang][key] = v[:-1] + "!"
            return "halfwidth"
        if v.endswith("？"):
            data[lang][key] = v[:-1] + "?"
            return "halfwidth"
        if " " in v:
            data[lang][key] = v.replace(" ", "  ", 1)
            return "double_space"
        data[lang][key] = v + " "
        return "trailing_space"
    if rule == "R9":
        data[lang][key] = ALT_BUY[lang]
        return "inconsistent"
    raise ValueError(rule)


def seed_defects(data, seed=SEED):
    rng = random.Random(seed)
    n = rng.randint(10, 12)
    rules = RULES + [rng.choice(RULES) for _ in range(n - len(RULES))]
    used, answers = set(), []
    for rule in rules:
        langs = ["ja", "zh-TW", "th"] if rule == "R7" else list(LANGS)
        rng.shuffle(langs)
        for lang in langs:
            cands = [k for k in candidates(rule, data, lang) if (lang, k) not in used and k in data[lang]]
            if rule == "R9":
                cands = [k for k in cands if not any((lang, b) in used for b in ("btn.buy", "dialog.buy.ok", "menu.buy"))]
            if cands:
                key = rng.choice(sorted(set(cands)))
                op = inject(rule, data, lang, key, rng)
                used.add((lang, key))
                if rule == "R9":  # 같은 원문 묶음은 다른 결함과 겹치지 않게 잠금
                    used.update((lang, b) for b in ("btn.buy", "dialog.buy.ok", "menu.buy"))
                answers.append({"lang": lang, "key": key, "rule": rule, "op": op})
                break
    return answers


def write_all(data, answers):
    os.makedirs(STRINGS_DIR, exist_ok=True)
    for lang, table in data.items():
        out = {"_meta": {"lang": lang, "note": NOTE}}
        out.update(table)
        with open(os.path.join(STRINGS_DIR, f"{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    with open(os.path.join(STRINGS_DIR, "_budget.json"), "w", encoding="utf-8") as f:
        json.dump(BUDGET, f, ensure_ascii=False, indent=2)
    with open(GLOSSARY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["term_ko", "lang", "required", "forbidden"])
        w.writerows(GLOSSARY)
    os.makedirs(os.path.dirname(ANSWER_KEY), exist_ok=True)
    with open(ANSWER_KEY, "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "defects": answers}, f, ensure_ascii=False, indent=2)


def main():
    data = build_clean()
    clean = copy.deepcopy(data)
    answers = seed_defects(data)
    write_all(data, answers)
    total = sum(len(v) for k, v in clean.items() if k != "ko")
    print(f"[생성] 기준어 ko 키 {len(KO)}개, 대상 언어 {len(LANGS)}개 ({', '.join(LANGS)}), 번역 문자열 {total}개")
    print(f"[생성] 용어집 {len(GLOSSARY)}행 → {os.path.basename(GLOSSARY_CSV)}, 폭 예산 {len(BUDGET)}키 → day89_strings/_budget.json")
    print(f"[시딩] seed={SEED}, LQA 결함 {len(answers)}개 시딩 → 정답표 sealed/day89_answer_key.json (내용 비공개)")


if __name__ == "__main__":
    main()
