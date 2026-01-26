# [Day 3] 조건문을 활용한 데이터 판별 실습
user_level = 25
required_level = 20

print("--- 콘텐츠 입장 조건 검토 ---")

# 만약(if) 유저 레벨이 요구 레벨보다 크거나 같다면
if user_level >= required_level:
    print("결과 : 입장 성공 (테스트 패스)")
# 그렇지 않다면(else)
else:
    print(f"결과 : 입장 실패 (레벨 {required_level - user_level} 더 필요함)")

# 불리언(True/False)을 활용한 점검
is_server_open = True

if is_server_open:
    print("상태 : 서버 정상 작동 중")
else:
    print("상태 : 점검 중")