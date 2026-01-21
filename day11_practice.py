# [Day 11] 파일 입출력을 활용한 테스트 로그 관리

# 1. 파일 쓰기 (w: write 모드)
# with를 쓰면 파일을 다 쓴 후 자동으로 close(닫기) 해줌
with open("test_report.txt", "w", encoding="utf-8") as file:
    file.write("--- QA 자동화 테스트 리포트 ---\n")
    file.write("1. 로그인 테스트 : PASS\n")
    file.write("2. 결제 테스트 : FAIL\n")
    print("리포트 파일 생성 완료!")

# 2. 파일 읽기 (r: read 모드)
print("\n[파일 내용 읽기 시작]")
try:
    with open("test_report.txt", "r", encoding="utf-8") as file:
        content = file.read()
        print(content)
except FileNotFoundError as e:
    print(f"에러 발생: 파일을 찾을 수 없음 ({e})")

# 3. 내용 추가하기 (a: append 모드)
with open("test_report.txt", "a", encoding="utf-8") as file:
    file.write("3. 로그아웃 테스트 : PASS\n")
    print("리포트 내용 업데이트 완료!")