# [Day 12] CSV 파일을 활용한 테스트 데이터 관리
import csv

# 1. CSV 파일 생성 및 데이터 쓰기
test_data = [
    ["test_id", "user_id", "status"],
    ["TC001", "admin", "PASS"],
    ["TC002", "guest_01", "FAIL"],
    ["TC003", "guest_02", "PASS"]
]

with open("test_results.csv", "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerows(test_data)
    print("CSV 테스트 결과 보고서 생성 완료!")

# 2. CSV 파일 읽기 및 데이터 분석
print("\n[CSV 데이터 분석 결과]")
with open("test_results.csv", "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file) # 딕셔너리 형태로 읽기 (Key-Value)
    for row in reader:
        # 딕셔너리 지식을 활용해 'status'가 FAIL인 것만 출력
        if row["status"] == "FAIL":
            print(f"경고: {row['test_id']} (ID: {row['user_id']}) 시나리오 실패!")