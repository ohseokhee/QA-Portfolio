"""
Day 66 : 프록시 실습 공용 도구 (Day 66~70에서 재사용)
- 서버·mitmdump 하위 프로세스 기동/종료
- 시스템 프록시(Fiddler 등)를 무시하는 requests 세션
"""

import os
import subprocess
import sys
import sysconfig
import time

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MITM_CONFDIR = os.path.join(BASE_DIR, "day66_mitm")
MITM_CA = os.path.join(MITM_CONFDIR, "mitmproxy-ca-cert.pem")
MITMDUMP = os.path.join(sysconfig.get_path("scripts"), "mitmdump.exe")
PROXY_PORT = 8889  # Fiddler 기본 8888과 겹치지 않게


def new_session(proxy=None, verify=True):
    """trust_env=False: Windows 시스템 프록시를 따르지 않고 지정한 프록시만 사용."""
    session = requests.Session()
    session.trust_env = False
    session.verify = verify
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session


def wait_until(url, verify=True, timeout=20):
    session = new_session(verify=verify)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if session.get(url, timeout=1).status_code < 500:
                return
        except requests.RequestException:
            time.sleep(0.3)
    raise RuntimeError(f"기동 확인 실패: {url}")


def start_server(script_args, check_url, verify=True):
    proc = subprocess.Popen([sys.executable, *script_args], cwd=BASE_DIR,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_until(check_url, verify=verify)
    except Exception:
        stop(proc)
        raise
    return proc


def start_mitm(addon, options=None, port=PROXY_PORT, upstream_ca=None):
    """mitmdump을 애드온과 함께 기동. upstream_ca를 주면 서버 인증서를 그 CA로 검증한다."""
    cmd = [MITMDUMP, "-q", "-p", str(port), "--set", f"confdir={MITM_CONFDIR}",
           "--set", "allow_hosts=127.0.0.1", "-s", addon]
    if upstream_ca:
        cmd += ["--set", f"ssl_verify_upstream_trusted_ca={upstream_ca}"]
    for key, value in (options or {}).items():
        cmd += ["--set", f"{key}={value}"]
    proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        # CA 파일 생성 + 포트 수신 대기까지 확인
        if os.path.exists(MITM_CA):
            try:
                new_session(proxy=f"http://127.0.0.1:{port}").get(f"http://127.0.0.1:{port}/", timeout=1)
                return proc
            except requests.RequestException:
                pass
        time.sleep(0.3)
    stop(proc)
    raise RuntimeError("mitmdump 기동 실패")


def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
