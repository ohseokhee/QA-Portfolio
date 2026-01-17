# [자료형 종합] QA 엔지니어가 알아야 할 4대 핵심 자료형

# 1. 문자열 (String) : 유저의 이름이나 상태 메시지
user_name = "석희_테스터"

# 2. 정수/실수 (Number) : 레벨이나 승률
user_level = 25
win_rate = 75.5

# 3. 불리언 (Boolean) : 특정 조건의 충족 여부
is_online = True
has_hidden_title = False

# 4. 리스트 (List) : 보유 중인 아이템 목록
inventory = ["물약", "강철검", "가죽 갑옷"]

print("--- 유저 데이터 종합 검증 ---")
print(f"1. 타입 확인(문자열) : {user_name} (형태: {type(user_name)})")
print(f"2. 타입 확인(숫자) : 레벨 {user_level}, 승률 {win_rate}%")
print(f"3. 타입 확인(논리) : 접속 상태 {is_online}")
print(f"4. 타입 확인(리스트) : 첫 번째 아이템 - {inventory[0]}")

# QA의 시각 : 리스트에 데이터가 잘 들어있는지 개수 확인
print(f"검증 : 현재 인벤토리에 {len(inventory)}개의 아이템이 존재합니다. (Pass)")
