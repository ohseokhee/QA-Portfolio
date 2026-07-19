"""
Day 52 : S3 정적 웹호스팅 버킷을 origin으로 CloudFront distribution 생성
의존성: py -m pip install boto3
사전 준비: Day 51에서 생성한 S3 정적 웹호스팅 버킷
⚠️ CallerReference는 매 실행마다 달라야 하므로 최초 1회만 생성하고, 이후에는 기존 distribution을 재사용
"""

import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

# ── 설정 ─────────────────────────────────────────────────────────────────
BUCKET_NAME = "qa-portfolio-allure-950992722874"
REGION = "ap-southeast-2"
ORIGIN_DOMAIN = f"{BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"
DIST_ID_FILE = "day52_distribution_id.txt"
# ─────────────────────────────────────────────────────────────────────────

cf = boto3.client("cloudfront")


def load_existing_distribution_id():
    if os.path.exists(DIST_ID_FILE):
        with open(DIST_ID_FILE, "r") as f:
            return f.read().strip()
    return None


def save_distribution_id(dist_id):
    with open(DIST_ID_FILE, "w") as f:
        f.write(dist_id)


def create_distribution():
    """CloudFront distribution 생성 (이미 있으면 재사용)"""
    print("[1/2] CloudFront distribution 생성")

    existing_id = load_existing_distribution_id()
    if existing_id:
        print(f"  기존 distribution 재사용 (스킵): {existing_id}\n")
        return existing_id

    caller_reference = f"qa-portfolio-allure-{int(time.time())}"

    distribution_config = {
        "CallerReference": caller_reference,
        "Comment": "QA Portfolio Allure Report CDN",
        "Enabled": True,
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "S3-Website-Origin",
                    "DomainName": ORIGIN_DOMAIN,
                    "CustomOriginConfig": {
                        "HTTPPort": 80,
                        "HTTPSPort": 443,
                        "OriginProtocolPolicy": "http-only",
                    },
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "S3-Website-Origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"],
            },
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
            },
            "MinTTL": 0,
            "DefaultTTL": 86400,
            "MaxTTL": 31536000,
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
        },
    }

    try:
        response = cf.create_distribution(DistributionConfig=distribution_config)
        dist = response["Distribution"]
        dist_id = dist["Id"]
        save_distribution_id(dist_id)
        print(f"  생성 완료: {dist_id}")
        print(f"  도메인: {dist['DomainName']}")
        print(f"  상태: {dist['Status']}\n")
        return dist_id
    except ClientError as e:
        print(f"  생성 실패: {e}")
        sys.exit(1)


def show_status(dist_id):
    """distribution 상태 및 도메인 출력"""
    print("[2/2] Distribution 상태 확인")
    resp = cf.get_distribution(Id=dist_id)
    dist = resp["Distribution"]
    print(f"  ID: {dist['Id']}")
    print(f"  도메인: {dist['DomainName']}")
    print(f"  상태: {dist['Status']}")
    print(f"  Enabled: {dist['DistributionConfig']['Enabled']}\n")
    return dist


def run():
    print("=" * 55)
    print("  Day 52 CloudFront Allure 리포트 CDN 배포")
    print("=" * 55 + "\n")

    dist_id = create_distribution()
    dist = show_status(dist_id)

    print("=" * 55)
    print(f"  CloudFront URL: https://{dist['DomainName']}")
    print("  (배포 완료까지 최대 15~20분 소요, 상태가 Deployed로 바뀌면 접근 가능)")
    print("=" * 55)


if __name__ == "__main__":
    run()
