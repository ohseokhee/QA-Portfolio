"""
Day 73 : 의사 현지화(Pseudo-localization) 자동 점검
1) 상점 페이지(day65_shop_client.html)의 화면 문자열을 30~40% 늘리고 악센트·특수 문자로 바꾼 버전 생성
   → day73_shop_client_pseudo.html  (예: "구매" → "[구매 ẞŦ]", "Login" → "[Ĺóǵíñ ẞŦ]")
2) 서버(v3 app)에 /shop(원본)과 /shop-pseudo(의사 현지화)를 띄우고 Chrome(headless)으로 두 화면 크기에서 로그인 후 점검
   - 요소 넘침: 글자가 요소 폭을 넘음(scrollWidth > clientWidth) / 화면 밖으로 나감(오른쪽 끝 > 화면 폭)
   - 줄바꿈: 한 줄이어야 할 버튼·표 머리글·제목·아이템 이름 글자가 두 줄 이상으로 나뉨
   - 가로 스크롤 발생 여부
   - 넘친 요소에 빨간 테두리를 그려 스크린샷 저장 (day73_screenshots/)
3) 결과를 day73_pseudo_loc_report.md로 저장
실행: py day73_pseudo_loc.py
"""

import argparse
import contextlib
import io
import math
import os
import re
import socket
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_HTML = os.path.join(BASE_DIR, "day65_shop_client.html")
PSEUDO_HTML = os.path.join(BASE_DIR, "day73_shop_client_pseudo.html")
SHOT_DIR = os.path.join(BASE_DIR, "day73_screenshots")
REPORT = os.path.join(BASE_DIR, "day73_pseudo_loc_report.md")
BASE_URL = "http://127.0.0.1:8000"
EXPANSION = 0.35  # 30~40% 확장
ACCENTS = str.maketrans("aceinosuyACEINOSUYlgmrtLGMRT", "áçéíñóšúýÁÇÉÍÑÓŠÚÝĺǵḿŕťĹǴḾŔŤ")
PADDING = "ẞŦǾŴ"
VIEWPORTS = [("mobile", 360, 800), ("desktop", 1280, 900)]
# JS 안에서 화면에 표시되는 문자열 (명세 1.4 아이템 이름과 상태 문구)
JS_LITERALS = ["프리미엄 선수팩", "일반 선수팩", "훈련 부스터", "클럽 유니폼 세트", "이벤트 한정팩",
               "로그인됨: account_id ", "로그인 실패: ", "비어 있음", "로그인 먼저"]


def pseudo(text):
    """앞뒤 공백은 유지하고, 글자를 악센트 문자로 바꾼 뒤 길이의 35%만큼 채움 문자를 붙이고 [ ]로 감싼다"""
    core = text.strip()
    if not core:
        return text
    pad_len = max(1, math.ceil(len(core) * EXPANSION))
    pad = (PADDING * pad_len)[:pad_len]
    lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    return f"{lead}[{core.translate(ACCENTS)} {pad}]{trail}"


def build_pseudo_html():
    html = open(SOURCE_HTML, encoding="utf-8").read()
    head, rest = html.split("<body>", 1)
    body, script_tail = rest.split("<script>", 1)
    script, tail = script_tail.split("</script>", 1)
    changed = []

    def repl_text(m):
        text = m.group(1)
        if not text.strip():
            return m.group(0)
        changed.append(text.strip())
        return ">" + pseudo(text) + "<"

    body = re.sub(r">([^<>]+)<", repl_text, body)
    body = re.sub(r'placeholder="([^"]+)"', lambda m: f'placeholder="{pseudo(m.group(1))}"', body)
    for literal in JS_LITERALS:
        if literal in script:
            script = script.replace(f'"{literal}"', f'"{pseudo(literal)}"').replace(f"`{literal}", f"`{pseudo(literal)}")
            changed.append(literal.strip())
    script = script.replace(">구매</button>", f">{pseudo('구매')}</button>")
    changed.append("구매")
    title = head.replace("<title>모의 게임 상점</title>", f"<title>{pseudo('모의 게임 상점')}</title>")
    with open(PSEUDO_HTML, "w", encoding="utf-8") as f:
        f.write(title + "<body>" + body + "<script>" + script + "</script>" + tail)
    return changed


def serve():
    """하위 프로세스 모드: v3 app에 의사 현지화 페이지 경로만 추가해 HTTP 8000으로 실행"""
    import uvicorn
    from fastapi.responses import FileResponse

    from day70_server_v3 import app

    @app.get("/shop-pseudo", include_in_schema=False)
    def shop_pseudo():
        return FileResponse(PSEUDO_HTML, media_type="text/html; charset=utf-8")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


OVERFLOW_JS = """
const vw = window.innerWidth, found = [];
document.querySelectorAll('body *').forEach(el => {
  if (['SCRIPT', 'STYLE', 'TBODY', 'THEAD', 'TR'].includes(el.tagName) || el.id === 'log') return;
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return;
  const text = (el.innerText || el.value || el.placeholder || '').trim().slice(0, 40);
  const clipped = el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'visible';
  const textOverflow = el.children.length === 0 && el.scrollWidth > el.clientWidth + 1;
  const offscreen = r.right > vw + 1;
  let wrapped = false;
  if (el.children.length === 0 && text && ['BUTTON', 'TH', 'TD', 'H1', 'H2'].includes(el.tagName)) {
    const range = document.createRange();
    range.selectNodeContents(el);
    wrapped = new Set([...range.getClientRects()].map(rc => Math.round(rc.top))).size > 1;
  }
  if (clipped || textOverflow || offscreen || wrapped) {
    el.style.outline = wrapped && !(clipped || textOverflow || offscreen) ? '2px solid orange' : '2px solid red';
    found.push({tag: el.tagName, id: el.id, text: text,
                kind: offscreen ? 'offscreen' : (clipped || textOverflow) ? 'overflow' : 'wrap',
                right: Math.round(r.right), width: Math.round(r.width)});
  }
});
return {found: found, pageWidth: document.documentElement.scrollWidth, viewport: vw};
"""


def inspect(driver, path, label, vp_name, width, height):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    # 창 크기 대신 기기 에뮬레이션으로 화면 폭을 정확히 지정 (headless 창은 최소 폭 제한이 있음)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                           {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 600})
    driver.get(BASE_URL + path)
    driver.find_element(By.ID, "btn-login").click()
    # 재화 표시("FC 5000 / BP ...")는 변환 대상이 아니므로 원본·의사 현지화 모두 같은 조건으로 대기
    WebDriverWait(driver, 10).until(lambda d: "FC" in d.find_element(By.ID, "balances").text)
    result = driver.execute_script(OVERFLOW_JS)
    shot = os.path.join(SHOT_DIR, f"day73_{label}_{vp_name}.png")
    driver.save_screenshot(shot)
    result.update(label=label, viewport_name=vp_name, screenshot=os.path.relpath(shot, BASE_DIR))
    return result


def measure_expansion(changed):
    """변환한 문자열 전체 길이: 원본 / 채움 문자까지 / 괄호·공백까지"""
    before = sum(len(t) for t in changed)
    padded = sum(len(t) + max(1, math.ceil(len(t) * EXPANSION)) for t in changed)
    full = sum(len(pseudo(t)) for t in changed)
    return before, padded, full


def write_report(changed, lengths, results):
    before_len, padded_len, after_len = lengths
    lines = [
        "# Day 73 의사 현지화 점검 결과",
        "",
        f"- 대상: `day65_shop_client.html` → `day73_shop_client_pseudo.html` (문자열 {len(changed)}개 변환)",
        f"- 변환 문자열 길이 합계: {before_len}자 → 채움 문자 포함 {padded_len}자 "
        f"(+{(padded_len / before_len - 1) * 100:.0f}%) → 괄호·공백까지 {after_len}자 (+{(after_len / before_len - 1) * 100:.0f}%)",
        "- 변환 규칙: 라틴 문자 → 악센트 문자, 길이 35%만큼 채움 문자(ẞŦǾŴ) 추가, `[ ]`로 감싸 잘림 확인",
        "",
        "| 페이지 | 화면 | 페이지 폭 / 화면 폭 | 가로 스크롤 | 넘침·화면 밖 | 줄바꿈 | 스크린샷 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        wraps = sum(f["kind"] == "wrap" for f in r["found"])
        lines.append(f"| {r['label']} | {r['viewport_name']} | {r['pageWidth']} / {r['viewport']} | "
                     f"{'있음' if r['pageWidth'] > r['viewport'] else '없음'} | {len(r['found']) - wraps} | {wraps} | "
                     f"{r['screenshot']} |")
    lines += ["", "## 문제 요소 (의사 현지화 페이지, 빨강 = 넘침, 주황 = 줄바꿈)", "",
              "| 화면 | 요소 | 종류 | 오른쪽 끝(px) | 폭(px) | 텍스트 |", "|---|---|---|---|---|---|"]
    for r in results:
        if r["label"] != "pseudo":
            continue
        for f in r["found"]:
            lines.append(f"| {r['viewport_name']} | {f['tag']}{'#' + f['id'] if f['id'] else ''} | {f['kind']} | "
                         f"{f['right']} | {f['width']} | {f['text']} |")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    from selenium import webdriver

    from day59_apply_schema import apply_schema
    from day66_proxy_lab import start_server, stop

    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            sys.exit("[중단] 127.0.0.1:8000에 이미 실행 중인 프로세스가 있습니다. 종료 후 다시 실행하세요.")
    os.makedirs(SHOT_DIR, exist_ok=True)

    print("[1] 의사 현지화 페이지 생성")
    changed = build_pseudo_html()
    lengths = measure_expansion(changed)
    print(f"  변환 문자열 {len(changed)}개, 길이 {lengths[0]}자 → 채움 문자 포함 {lengths[1]}자 "
          f"(+{(lengths[1] / lengths[0] - 1) * 100:.0f}%) → 괄호·공백까지 {lengths[2]}자 "
          f"(+{(lengths[2] / lengths[0] - 1) * 100:.0f}%)")
    for sample in ["구매", "로그인", "프리미엄 선수팩", "Login"]:
        print(f"  예시: {sample} → {pseudo(sample)}")

    with contextlib.redirect_stdout(io.StringIO()):
        apply_schema()
    print("\n[2] 서버 기동: py day73_pseudo_loc.py --serve (v3 app + /shop-pseudo, 127.0.0.1:8000)")
    server = start_server(["day73_pseudo_loc.py", "--serve"], BASE_URL + "/openapi.json")
    driver = None
    results = []
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-proxy-server")
        driver = webdriver.Chrome(options=options)
        print("[3] Chrome(headless) 점검: 원본 / 의사 현지화 x 모바일(360px) / 데스크톱(1280px)\n")
        for label, path in (("original", "/shop"), ("pseudo", "/shop-pseudo")):
            for vp_name, w, h in VIEWPORTS:
                r = inspect(driver, path, label, vp_name, w, h)
                results.append(r)
                wraps = sum(f["kind"] == "wrap" for f in r["found"])
                print(f"  [{label} / {vp_name}] 페이지 폭 {r['pageWidth']}px (화면 {r['viewport']}px), "
                      f"넘침·화면 밖 {len(r['found']) - wraps}개, 줄바꿈 {wraps}개 → {r['screenshot']}")
                for f in r["found"]:
                    print(f"      - {f['tag']}{'#' + f['id'] if f['id'] else ''} {f['kind']} "
                          f"(오른쪽 끝 {f['right']}px, 폭 {f['width']}px) \"{f['text']}\"")
    finally:
        if driver:
            driver.quit()
        stop(server)
        with contextlib.redirect_stdout(io.StringIO()):
            apply_schema()

    write_report(changed, lengths, results)
    total = sum(len(r["found"]) for r in results if r["label"] == "pseudo")
    base = sum(len(r["found"]) for r in results if r["label"] == "original")
    print(f"\n[결과] 문제 요소(넘침+줄바꿈): 원본 {base}개 → 의사 현지화 {total}개 → {os.path.relpath(REPORT, BASE_DIR)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    if parser.parse_args().serve:
        serve()
    else:
        main()
