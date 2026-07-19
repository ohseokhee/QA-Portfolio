"""
Day 53 : CloudFront 캐시 무효화(Invalidation) 및 S3-CloudFront 콘텐츠 정합성 검증
의존성: py -m pip install boto3
사전 준비: Day 51 S3 버킷, Day 52 CloudFront distribution
"""

import os
import sys
import time

import boto3

DIST_ID_FILE = "day52_distribution_id.txt"


def load_distribution_id():
    if not os.path.exists(DIST_ID_FILE):
        print(f"[오류] {DIST_ID_FILE} 없음 - day52_cloudfront.py를 먼저 실행하세요")
        sys.exit(1)
    with open(DIST_ID_FILE, "r") as f:
        return f.read().strip()


def create_invalidation(cf, dist_id):
    """전체 경로(/*) 캐시 무효화 요청"""
    print("[1/2] CloudFront 캐시 무효화 요청")
    resp = cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": f"day53-invalidate-{int(time.time())}",
        },
    )
    invalidation_id = resp["Invalidation"]["Id"]
    print(f"  요청 완료: {invalidation_id}")
    print(f"  상태: {resp['Invalidation']['Status']}\n")
    return invalidation_id


def poll_invalidation(cf, dist_id, invalidation_id, interval=10, max_wait=300):
    """무효화 완료(Completed)까지 폴링"""
    print("[2/2] 무효화 완료 대기")
    elapsed = 0
    while elapsed <= max_wait:
        resp = cf.get_invalidation(DistributionId=dist_id, Id=invalidation_id)
        status = resp["Invalidation"]["Status"]
        print(f"[{elapsed}s] 상태: {status}")
        if status == "Completed":
            return True
        time.sleep(interval)
        elapsed += interval
    return False


def run():
    print("=" * 55)
    print("  Day 53 CloudFront 캐시 무효화")
    print("=" * 55 + "\n")

    dist_id = load_distribution_id()
    cf = boto3.client("cloudfront")

    invalidation_id = create_invalidation(cf, dist_id)
    completed = poll_invalidation(cf, dist_id, invalidation_id)

    print("\n" + "=" * 55)
    if completed:
        print("  무효화 완료: Completed")
    else:
        print("  [안내] 제한 시간 내 Completed 미확인 (정상 - day53_verify.py로 재확인)")
    print("=" * 55)


if __name__ == "__main__":
    run()
