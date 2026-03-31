#!/bin/bash
# Day 49 : 컨테이너 MariaDB → RDS 데이터 마이그레이션
# EC2 안에서 실행

set -e

# ── 설정 (실행 전 RDS 정보 입력) ─────────────────────────────────────────
RDS_HOST="${RDS_HOST:-YOUR_RDS_ENDPOINT}"
RDS_USER="${RDS_USER:-admin}"
RDS_PASSWORD="${RDS_PASSWORD:-YOUR_PASSWORD}"
RDS_DB="${RDS_DB:-qa_db}"
DUMP_FILE="/tmp/qa_db_dump.sql"
# ──────────────────────────────────────────────────────────────────────────

echo "============================================"
echo " [1/4] 컨테이너 DB에서 데이터 덤프"
echo "============================================"
docker exec qa-mariadb mariadb-dump \
    -u qa_user -pqa_pass qa_db \
    > "$DUMP_FILE"
echo "덤프 완료: $DUMP_FILE ($(wc -l < $DUMP_FILE)줄)"

echo "============================================"
echo " [2/4] RDS에 데이터베이스 생성"
echo "============================================"
mysql -h "$RDS_HOST" -P 3306 -u "$RDS_USER" -p"$RDS_PASSWORD" \
    -e "CREATE DATABASE IF NOT EXISTS $RDS_DB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "DB 생성 완료: $RDS_DB"

echo "============================================"
echo " [3/4] RDS에 덤프 파일 임포트"
echo "============================================"
mysql -h "$RDS_HOST" -P 3306 -u "$RDS_USER" -p"$RDS_PASSWORD" "$RDS_DB" < "$DUMP_FILE"
echo "임포트 완료"

echo "============================================"
echo " [4/4] 마이그레이션 결과 검증"
echo "============================================"
echo "[ 컨테이너 DB 데이터 건수 ]"
docker exec qa-mariadb mariadb \
    -u qa_user -pqa_pass qa_db \
    -e "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='qa_db';"

echo ""
echo "[ RDS 데이터 건수 ]"
mysql -h "$RDS_HOST" -P 3306 -u "$RDS_USER" -p"$RDS_PASSWORD" "$RDS_DB" \
    -e "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='$RDS_DB';"

echo ""
echo "마이그레이션 완료!"
