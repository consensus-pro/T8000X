from flask import Blueprint, request, jsonify
import io
import random
import hashlib
import time
import base64
import os
from PIL import Image, ImageDraw, ImageFont

captcha_bp = Blueprint('captcha', __name__)
captcha_store = {}

# 定位字体文件（优先使用 api/Plus.ttf）
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # 项目根目录
font_paths = [
    os.path.join(base_dir, 'api', 'Plus.ttf'),        # 您指定的位置
    os.path.join(base_dir, 'fonts', 'Plus.ttf'),      # 备用位置
]

font = None
for path in font_paths:
    if os.path.exists(path):
        try:
            font = ImageFont.truetype(path, 48)
            break
        except:
            continue

if font is None:
    font = ImageFont.load_default()

@captcha_bp.route('/api/captcha', methods=['GET'])
def get_captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    text = ''.join(random.choices(chars, k=5))
    token = hashlib.md5(f"{text}{time.time()}{random.random()}".encode()).hexdigest()
    captcha_store[token] = text

    width, height = 180, 70
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    colors = [(220, 50, 50), (30, 120, 210), (40, 180, 80), (160, 50, 200), (220, 160, 20)]

    try:
        char_widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    except:
        char_widths = [32] * len(text)
    spacing = 10
    total_width = sum(char_widths) + spacing * (len(text) - 1)
    start_x = (width - total_width) // 2

    for i, ch in enumerate(text):
        x = start_x + sum(char_widths[:i]) + spacing * i
        y = 14 + random.randint(-4, 4)
        draw.text((x, y), ch, font=font, fill=colors[i % len(colors)])

    for _ in range(2):
        draw.line([(random.randint(0, width), random.randint(0, height)),
                   (random.randint(0, width), random.randint(0, height))],
                  fill=(220, 220, 220), width=1)

    for _ in range(30):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(200, 200, 200))

    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    b64 = base64.b64encode(img_io.getvalue()).decode()

    return jsonify({
        "code": 0,
        "data": {
            "captcha_token": token,
            "image": f"data:image/png;base64,{b64}",
            "server_time": int(time.time())
        }
    })