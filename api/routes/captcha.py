from flask import Blueprint, request, jsonify
import io
import random
import hashlib
import time
import base64
import os
from PIL import Image, ImageDraw, ImageFont

captcha_bp = Blueprint('captcha', __name__)

# 存储结构：{token: {'text': 'ABC12', 'expire_at': 1234567890.0}}
captcha_store = {}

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
font_path = os.path.join(base_dir, 'api', 'Plus.ttf')
if not os.path.exists(font_path):
    font_path = os.path.join(base_dir, 'fonts', 'Plus.ttf')

try:
    test_font = ImageFont.truetype(font_path, 20)
    font_available = True
except:
    font_available = False


def check_captcha(token, user_input):
    """校验验证码，过期自动删除，返回 (bool, 错误信息)"""
    if not token or token not in captcha_store:
        return False, "验证码不存在或已过期"
    record = captcha_store[token]
    if record['expire_at'] < time.time():
        del captcha_store[token]
        return False, "验证码已过期，请刷新重试"
    if record['text'] != user_input.upper():
        return False, "验证码错误"
    return True, "验证通过"


@captcha_bp.route('/api/captcha', methods=['GET'])
def get_captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    text = ''.join(random.choices(chars, k=5))
    token = hashlib.md5(f"{text}{time.time()}{random.random()}".encode()).hexdigest()
    expire_at = time.time() + 600  # 10 分钟
    captcha_store[token] = {'text': text, 'expire_at': expire_at}

    width, height = 100, 42
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    colors = [(220, 50, 50), (30, 120, 210), (40, 180, 80), (160, 50, 200), (220, 160, 20)]

    char_data = []
    for ch in text:
        size = random.randint(14, 22)
        y_offset = random.randint(-2, 2)
        if font_available:
            try:
                font = ImageFont.truetype(font_path, size)
            except:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
        try:
            bbox = font.getbbox(ch)
            char_width = bbox[2] - bbox[0]
        except:
            char_width = 12
        char_data.append((ch, font, char_width, y_offset))

    spacing = 2
    total_width = sum([cd[2] for cd in char_data]) + spacing * (len(char_data) - 1)
    start_x = (width - total_width) // 2

    x = start_x
    for i, (ch, font, char_width, y_offset) in enumerate(char_data):
        y = 11 + y_offset
        draw.text((x, y), ch, font=font, fill=colors[i % len(colors)])
        x += char_width + spacing

    draw.line([(random.randint(0, width), random.randint(0, height)),
               (random.randint(0, width), random.randint(0, height))],
              fill=(220, 220, 220), width=1)

    for _ in range(8):
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