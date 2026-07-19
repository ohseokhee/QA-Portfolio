"""
Day 52 : CloudFront distribution 배포 상태 폴링 및 HTTPS 접근 검증
의존성: py -m pip install boto3
"""

import os
import sys
import time
import urllib.request

import boto3

DIST_ID_FILE = "day52_distribution_id.txt"
POLL_INTERVAL_SEC = 30
MAX_WAIT_SEC = 540  # 9분 (도구 타임아웃 10분 내 안전 마진)


def load_distribution_id():
    if not os.path.exists(DIST_ID_FILE):
        print(f"[오류] {DIST_ID_FILE} 없음 - day52_cloudfront.py를 먼저 실행하세요")
        sys.exit(1)
    with open(DIST_ID_FILE, "r") as f:
        return f.read().strip()


def poll_until_deployed(cf, dist_id):
    """Deployed 상태가 될 때까지 폴링 (최대 MAX_WAIT_SEC)"""
    elapsed = 0
    while elapsed <= MAX_WAIT_SEC:
        resp = cf.get_distribution(Id=dist_id)
        dist = resp["Distribution"]
        status = dist["Status"]
        print(f"[{elapsed}s] 상태: {status}")
        if status == "Deployed":
            return dist
        time.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC
    return dist


def verify_https_access(domain_name):
    """CloudFront 도메인 HTTPS 접근 및 Allure 콘텐츠 확인"""
    url = f"https://{domain_name}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.status
        body = resp.read().decode("utf-8", errors="ignore")
    print(f"[HTTP 상태] {status}")
    print(f"[Allure 콘텐츠 포함 여부] {'Allure' in body}")
    return status, body


def run():
    print("=" * 55)
    print("  Day 52 CloudFront 배포 상태 검증")
    print("=" * 55 + "\n")

    dist_id = load_distribution_id()
    cf = boto3.client("cloudfront")

    dist = poll_until_deployed(cf, dist_id)
    domain_name = dist["DomainName"]
    status = dist["Status"]

    print(f"\n[최종 상태] {status}")
    print(f"[도메인] {domain_name}\n")

    if status != "Deployed":
        print(f"[안내] {MAX_WAIT_SEC}초 내에 Deployed 상태가 되지 않음 (정상 - 보통 15~20분 소요)")
        print("  잠시 후 day52_verify.py를 다시 실행해 재확인하세요")
        return

    try:
        http_status, body = verify_https_access(domain_name)
        assert http_status == 200, f"HTTPS 응답 실패: {http_status}"
        assert "Allure" in body, "Allure 리포트 콘텐츠 미확인"
        print("\n" + "=" * 55)
        print("  검증 완료: 정상")
        print("=" * 55)
    except Exception as e:
        print(f"\n[검증 실패] {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
