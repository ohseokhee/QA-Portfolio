"""
Day 55 : Phase 4(EC2+RDS+Grid+S3) 포트폴리오 아키텍처 다이어그램 생성
의존성: 없음 (Pillow 기존 설치분 사용)
"""

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1300, 560
BG = (255, 255, 255)
BOX_FILL = (235, 245, 255)
BOX_LINE = (60, 90, 160)
TEXT_COLOR = (30, 30, 30)
ARROW_COLOR = (90, 90, 90)

OUTPUT_FILE = "day55_architecture.png"

BOXES = [
    # (x, y, w, h, title, subtitle)
    (40,  220, 200, 130, "Local (Windows)", "day54_integration.py\nSSH / SFTP"),
    (320, 220, 200, 130, "EC2", "Selenium Grid\n(Hub + Chrome)"),
    (600, 220, 200, 130, "RDS", "MariaDB\nsearch_results"),
    (880, 60,  200, 130, "S3", "Allure Report\n(index.html)"),
    (880, 380, 200, 130, "CloudFront", "HTTPS CDN\n캐시 무효화"),
    (1140-60, 220, 200, 130, "End User", "리포트 열람\n(HTTPS)"),
]

# 화살표는 박스 테두리 바깥 점끼리만 연결 (겹침 방지), 라벨은 선 아래쪽에 별도 배치
ARROWS = [
    # (x1, y1, x2, y2, label, label_x, label_y)
    (240, 285, 320, 285, "SSH pytest 실행", 245, 295),
    (520, 285, 600, 285, "저장 / 조회", 530, 295),
    (420, 220, 880, 130, "Allure 결과 회수 후 업로드", 560, 155),
    (980, 190, 980, 380, "Origin", 990, 275),
    (1080, 440, 1140-40, 300, "무효화 후 서빙", 1010, 355),
]


def draw_box(draw, box, font_title, font_sub):
    x, y, w, h, title, subtitle = box
    draw.rectangle([x, y, x + w, y + h], fill=BOX_FILL, outline=BOX_LINE, width=2)
    draw.text((x + 10, y + 10), title, fill=TEXT_COLOR, font=font_title)
    draw.multiline_text((x + 10, y + 42), subtitle, fill=TEXT_COLOR, font=font_sub, spacing=6)


def run():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("malgun.ttf", 18)
        font_sub = ImageFont.truetype("malgun.ttf", 14)
        font_caption = ImageFont.truetype("malgun.ttf", 22)
    except OSError:
        font_title = font_sub = font_caption = ImageFont.load_default()

    draw.text((40, 20), "Phase 4 통합 아키텍처 : EC2 + RDS + Grid + S3 + CloudFront", fill=TEXT_COLOR, font=font_caption)

    for x1, y1, x2, y2, label, lx, ly in ARROWS:
        draw.line([x1, y1, x2, y2], fill=ARROW_COLOR, width=2)
        draw.text((lx, ly), label, fill=ARROW_COLOR, font=font_sub)

    for box in BOXES:
        draw_box(draw, box, font_title, font_sub)

    img.save(OUTPUT_FILE)
    print(f"[완료] 아키텍처 다이어그램 생성: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
