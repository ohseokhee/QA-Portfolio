"""
Day 53 : S3 원본과 CloudFront 배포 콘텐츠의 정합성 최종 검증
의존성: py -m pip install boto3
Day 51(S3) + Day 52(CloudFront) + Day 53(무효화) 전체 파이프라인 통합 검증
"""

import hashlib
import sys
import urllib.request

import boto3

BUCKET_NAME = "qa-portfolio-allure-950992722874"
REGION = "ap-southeast-2"
CLOUDFRONT_DOMAIN = "d9k07ahl0figy.cloudfront.net"
KEY = "index.html"


def fetch_s3_object_hash():
    """S3 원본 객체의 MD5 해시"""
    s3 = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj["Body"].read()
    digest = hashlib.md5(body).hexdigest()
    print(f"[S3 원본 해시] {digest} ({len(body)} bytes)")
    return digest, body


def fetch_cloudfront_hash():
    """CloudFront 경유 콘텐츠의 MD5 해시"""
    url = f"https://{CLOUDFRONT_DOMAIN}/{KEY}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.status
        body = resp.read()
    digest = hashlib.md5(body).hexdigest()
    print(f"[HTTP 상태] {status}")
    print(f"[CloudFront 해시] {digest} ({len(body)} bytes)")
    return status, digest, body


def run():
    print("=" * 55)
    print("  Day 53 S3-CloudFront 콘텐츠 정합성 검증")
    print("=" * 55 + "\n")

    s3_hash, s3_body = fetch_s3_object_hash()
    status, cf_hash, cf_body = fetch_cloudfront_hash()

    assert status == 200, f"CloudFront 응답 실패: {status}"
    assert s3_hash == cf_hash, f"해시 불일치: S3={s3_hash} / CloudFront={cf_hash}"
    assert b"Allure" in cf_body, "Allure 리포트 콘텐츠 미확인"

    print("\n" + "=" * 55)
    print("  검증 완료: S3 원본과 CloudFront 배포 콘텐츠 일치")
    print(f"  최종 서비스 URL: https://{CLOUDFRONT_DOMAIN}")
    print("=" * 55)


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"\n[검증 실패] {e}")
        sys.exit(1)
