from flask import Blueprint, session, send_file, request, jsonify
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter

captcha_bp = Blueprint('captcha', __name__)

@captcha_bp.route('/api/captcha')
def get_captcha():
    chars = string.ascii_uppercase + string.digits
    chars = ''.join(c for c in chars if c not in 'O0I1')
    text = ''.join(random.choices(chars, k=4))
    session['captcha'] = text

    width, height = 150, 50
    image = Image.new('RGB', (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()

    for i, ch in enumerate(text):
        x = 15 + i * 30 + random.randint(-3, 3)
        y = random.randint(5, 15)
        color = (random.randint(30, 100), random.randint(30, 100), random.randint(30, 100))
        draw.text((x, y), ch, font=font, fill=color)

    for _ in range(5):
        draw.line([
            (random.randint(0, width), random.randint(0, height)),
            (random.randint(0, width), random.randint(0, height))
        ], fill=(150, 150, 150), width=1)

    for _ in range(80):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(0, 0, 0))

    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')