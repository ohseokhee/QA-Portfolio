"""
Day 55 : Phase 4 통합 검증 (2/2) - Allure 리포트 + 아키텍처 다이어그램 S3 배포 및 CloudFront 최종 확인
의존성: py -m pip install boto3
사전 준비: Day 54(allure-results 회수) + Day 51(S3 버킷) + Day 52(CloudFront) + day55_architecture.py 실행 결과
"""

import hashlib
import os
import subprocess
import sys
import time
import urllib.request

import boto3

BUCKET_NAME = "qa-portfolio-allure-950992722874"
REGION = "ap-southeast-2"
CLOUDFRONT_DOMAIN = "d9k07ahl0figy.cloudfront.net"
DIST_ID_FILE = "day52_distribution_id.txt"

ALLURE_RESULTS_DIR = "allure-results"
ALLURE_REPORT_DIR = "allure-report"
ALLURE_BIN = r"C:\Users\USER\allure\bin\allure.bat"

ARCHITECTURE_FILE = "day55_architecture.png"
ARCHITECTURE_KEY = "architecture.png"

s3 = boto3.client("s3", region_name=REGION)


def generate_allure_report():
    print("[1/5] Allure HTML 리포트 생성 (Day 54 재검증 결과 기준)")
    result = subprocess.run(
        [ALLURE_BIN, "generate", ALLURE_RESULTS_DIR, "--clean", "-o", ALLURE_REPORT_DIR],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    print(f"  생성 완료: {ALLURE_REPORT_DIR}/index.html\n")


def upload_report():
    print("[2/5] Allure 리포트 S3 업로드")
    uploaded = 0
    for root, _, files in os.walk(ALLURE_REPORT_DIR):
        for filename in files:
            local_path = os.path.join(root, filename)
            key = os.path.relpath(local_path, ALLURE_REPORT_DIR).replace("\\", "/")
            s3.upload_file(local_path, BUCKET_NAME, key)
            uploaded += 1
    print(f"  업로드 완료: {uploaded}개 파일\n")


def upload_architecture_diagram():
    print("[3/5] 아키텍처 다이어그램 S3 업로드")
    s3.upload_file(ARCHITECTURE_FILE, BUCKET_NAME, ARCHITECTURE_KEY, ExtraArgs={"ContentType": "image/png"})
    print(f"  업로드 완료: {ARCHITECTURE_KEY}\n")


def invalidate_cloudfront():
    print("[4/5] CloudFront 캐시 무효화")
    if not os.path.exists(DIST_ID_FILE):
        print(f"  [오류] {DIST_ID_FILE} 없음 - day52_cloudfront.py를 먼저 실행하세요")
        sys.exit(1)
    with open(DIST_ID_FILE, "r") as f:
        dist_id = f.read().strip()

    cf = boto3.client("cloudfront")
    resp = cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": f"day55-deploy-{int(time.time())}",
        },
    )
    invalidation_id = resp["Invalidation"]["Id"]
    print(f"  요청 완료: {invalidation_id}")

    elapsed = 0
    while elapsed <= 300:
        status = cf.get_invalidation(DistributionId=dist_id, Id=invalidation_id)["Invalidation"]["Status"]
        print(f"  [{elapsed}s] 상태: {status}")
        if status == "Completed":
            break
        time.sleep(10)
        elapsed += 10
    print()


def verify_via_cloudfront():
    print("[5/5] CloudFront 배포 콘텐츠 정합성 최종 검증")

    s3_obj = s3.get_object(Bucket=BUCKET_NAME, Key="index.html")
    s3_hash = hashlib.md5(s3_obj["Body"].read()).hexdigest()

    url = f"https://{CLOUDFRONT_DOMAIN}/index.html"
    with urllib.request.urlopen(url, timeout=15) as resp:
        status = resp.status
        cf_body = resp.read()
    cf_hash = hashlib.md5(cf_body).hexdigest()

    print(f"  [S3 원본 해시] {s3_hash}")
    print(f"  [CloudFront 해시] {cf_hash} (HTTP {status})")

    assert status == 200, f"CloudFront 응답 실패: {status}"
    assert s3_hash == cf_hash, f"해시 불일치: S3={s3_hash} / CloudFront={cf_hash}"

    diagram_url = f"https://{CLOUDFRONT_DOMAIN}/{ARCHITECTURE_KEY}"
    with urllib.request.urlopen(diagram_url, timeout=15) as resp:
        diagram_status = resp.status
    print(f"  [아키텍처 다이어그램] {diagram_url} (HTTP {diagram_status})")
    assert diagram_status == 200, "아키텍처 다이어그램 접근 실패"

    print("\n  검증 완료: Day 51~55 Phase 4 전체 파이프라인 정상 동작")
    print(f"  최종 리포트 URL: {url}")
    print(f"  아키텍처 다이어그램 URL: {diagram_url}")


def run():
    print("=" * 55)
    print("  Day 55 Allure 리포트 + 아키텍처 다이어그램 배포")
    print("=" * 55 + "\n")

    generate_allure_report()
    upload_report()
    upload_architecture_diagram()
    invalidate_cloudfront()
    verify_via_cloudfront()

    print("\n" + "=" * 55)
    print("  Day 55 배포 및 최종 검증 완료")
    print("=" * 55)


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"\n[검증 실패] {e}")
        sys.exit(1)
