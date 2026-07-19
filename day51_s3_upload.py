"""
Day 51 : Allure 리포트 생성 → S3 버킷 생성 → 정적 웹호스팅 업로드
의존성: py -m pip install boto3
사전 준비: Allure CLI (allure-results → allure-report 생성용)
⚠️ 버킷 이름은 전역 유니크해야 함 (AWS 계정 ID 일부를 접미사로 사용)
"""

import subprocess
import sys

import boto3
from botocore.exceptions import ClientError

# ── 설정 ─────────────────────────────────────────────────────────────────
BUCKET_NAME = "qa-portfolio-allure-950992722874"
REGION = "ap-southeast-2"
ALLURE_RESULTS_DIR = "allure-results"
ALLURE_REPORT_DIR = "allure-report"
ALLURE_BIN = r"C:\Users\USER\allure\bin\allure.bat"
# ─────────────────────────────────────────────────────────────────────────

s3 = boto3.client("s3", region_name=REGION)


def generate_allure_report():
    """allure-results → allure-report HTML 생성"""
    print("[1/4] Allure HTML 리포트 생성")
    result = subprocess.run(
        [ALLURE_BIN, "generate", ALLURE_RESULTS_DIR, "--clean", "-o", ALLURE_REPORT_DIR],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    print(f"  생성 완료: {ALLURE_REPORT_DIR}/index.html\n")


def create_bucket():
    """S3 버킷 생성 (이미 있으면 스킵)"""
    print("[2/4] S3 버킷 생성")
    try:
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        print(f"  생성 완료: {BUCKET_NAME}\n")
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print(f"  이미 존재함 (스킵): {BUCKET_NAME}\n")
        else:
            raise


def enable_static_website():
    """퍼블릭 액세스 차단 해제 + 정적 웹호스팅 활성화 + 퍼블릭 읽기 정책 적용"""
    print("[3/4] 정적 웹호스팅 설정")

    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    s3.put_bucket_website(
        Bucket=BUCKET_NAME,
        WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}},
    )

    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{BUCKET_NAME}/*",
        }],
    }
    import json
    s3.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(policy))
    print("  퍼블릭 읽기 정책 적용 완료\n")


def upload_report():
    """allure-report 디렉토리 전체 업로드"""
    print("[4/4] 리포트 업로드")
    import os
    uploaded = 0
    for root, _, files in os.walk(ALLURE_REPORT_DIR):
        for filename in files:
            local_path = os.path.join(root, filename)
            key = os.path.relpath(local_path, ALLURE_REPORT_DIR).replace("\\", "/")
            s3.upload_file(local_path, BUCKET_NAME, key)
            uploaded += 1
    print(f"  업로드 완료: {uploaded}개 파일\n")


def website_url():
    return f"http://{BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"


def run():
    print("=" * 55)
    print("  Day 51 S3 Allure 리포트 호스팅")
    print("=" * 55 + "\n")

    generate_allure_report()
    create_bucket()
    enable_static_website()
    upload_report()

    print("=" * 55)
    print(f"  리포트 URL: {website_url()}")
    print("=" * 55)


if __name__ == "__main__":
    run()
