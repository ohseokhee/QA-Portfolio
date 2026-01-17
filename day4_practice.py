# [Day 4] 복합 조건문 및 논리 연산자 실습
user_level = 35
has_ticket = True

print("--- 유저 등급 및 입장 권한 상세 점검 ---")

# 1. 여러 단계로 등급 나누기 (elif 활용)
if user_level >= 50:
    user_grade = "VIP"
elif user_level >= 30:
    user_grade = "일반"
else:
    user_grade = "신규"

print(f"결과 : 유저 등급은 '{user_grade}'입니다.")

# 2. 복합 조건 검사 (and 활용)
# 레벨이 30 이상 '이고' 티켓을 보유하고 있어야 함
if user_level >= 30 and has_ticket == True:
    print("검증 : 특수 던전 입장 가능 (Pass)")
else:
    print("검증 : 입장 불가 (조건 미충족)")