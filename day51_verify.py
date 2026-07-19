"""
Day 51 : S3 정적 웹호스팅으로 배포된 Allure 리포트 접근 검증
의존성: py -m pip install boto3
"""

import sys
import urllib.request

import boto3

BUCKET_NAME = "qa-portfolio-allure-950992722874"
REGION = "ap-southeast-2"
WEBSITE_URL = f"http://{BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"


def verify_bucket_object_count():
    """S3 버킷에 업로드된 객체 수 확인"""
    s3 = boto3.client("s3", region_name=REGION)
    paginator = s3.get_paginator("list_objects_v2")
    count = 0
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        count += len(page.get("Contents", []))
    print(f"[S3 객체 수] {count}개")
    return count


def verify_website_response():
    """정적 웹사이트 URL 응답 및 index.html 접근 확인"""
    req = urllib.request.Request(WEBSITE_URL)
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.status
        body = resp.read().decode("utf-8", errors="ignore")
    print(f"[HTTP 상태] {status}")
    print(f"[Allure 콘텐츠 포함 여부] {'Allure' in body}")
    return status, body


def run():
    print("=" * 55)
    print("  Day 51 S3 Allure 리포트 검증")
    print(f"  URL : {WEBSITE_URL}")
    print("=" * 55 + "\n")

    count = verify_bucket_object_count()
    status, body = verify_website_response()

    assert count > 0, "S3 버킷에 업로드된 객체가 없음"
    assert status == 200, f"웹사이트 응답 실패: {status}"
    assert "Allure" in body, "Allure 리포트 콘텐츠 미확인"

    print("\n" + "=" * 55)
    print("  검증 완료: 정상")
    print("=" * 55)


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"\n[검증 실패] {e}")
        sys.exit(1)


