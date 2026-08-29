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

# 定位字体文件（您放在 api/Plus.ttf）
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
font_paths = [
    os.path.join(base_dir, 'api', 'Plus.ttf'),
    os.path.join(base_dir, 'fonts', 'Plus.ttf'),
]

font = None
for path in font_paths:
    if os.path.exists(path):
        try:
            font = ImageFont.truetype(path, 32)  # 字体大小改为 32px
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

    width, height = 150, 50  # 缩小图片尺寸
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    colors = [(220, 50, 50), (30, 120, 210), (40, 180, 80), (160, 50, 200), (220, 160, 20)]

    try:
        char_widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    except:
        char_widths = [20] * len(text)
    spacing = 8  # 减小间距
    total_width = sum(char_widths) + spacing * (len(text) - 1)
    start_x = (width - total_width) // 2

    for i, ch in enumerate(text):
        x = start_x + sum(char_widths[:i]) + spacing * i
        y = 12  # 垂直居中，字体32px，图片高50，y=12左右
        draw.text((x, y), ch, font=font, fill=colors[i % len(colors)])

    # 干扰线（减淡）
    for _ in range(2):
        draw.line([(random.randint(0, width), random.randint(0, height)),
                   (random.randint(0, width), random.randint(0, height))],
                  fill=(220, 220, 220), width=1)

    # 噪点（减少）
    for _ in range(20):
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