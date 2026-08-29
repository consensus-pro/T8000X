from flask import Blueprint, request, jsonify
import io
import random
import hashlib
import time
import base64
from PIL import Image, ImageDraw, ImageFont

captcha_bp = Blueprint('captcha', __name__)

captcha_store = {}

@captcha_bp.route('/api/captcha', methods=['GET'])
def get_captcha():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    text = ''.join(random.choices(chars, k=5))
    token = hashlib.md5(f"{text}{time.time()}{random.random()}".encode()).hexdigest()
    captcha_store[token] = text

    width, height = 200, 80
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
        except:
            try:
                font = ImageFont.truetype("comic.ttf", 44)
            except:
                font = ImageFont.load_default()

    colors = [(220, 50, 50), (30, 120, 210), (40, 180, 80), (160, 50, 200), (220, 160, 20)]

    char_widths = []
    for ch in text:
        try:
            bbox = font.getbbox(ch)
            char_widths.append(bbox[2] - bbox[0])
        except:
            char_widths.append(30)

    spacing = 8
    total_width = sum(char_widths) + spacing * (len(text) - 1)
    start_x = (width - total_width) // 2

    for i, ch in enumerate(text):
        x = start_x + sum(char_widths[:i]) + spacing * i
        y = 20 + random.randint(-6, 6)
        draw.text((x, y), ch, font=font, fill=colors[i % len(colors)])

    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200, 100), width=1)

    for _ in range(40):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(180, 180, 180))

    for i in range(0, width, 10):
        draw.line([(i, 0), (i + 5, height)], fill=(245, 245, 245), width=1)

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