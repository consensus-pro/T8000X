from flask import Blueprint, session, send_file
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

    width, height = 160, 60
    image = Image.new('RGB', (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    for i, ch in enumerate(text):
        x = 12 + i * 34 + random.randint(-4, 4)
        y = random.randint(6, 16)
        color = (random.randint(20, 180), random.randint(20, 180), random.randint(20, 180))
        draw.text((x, y), ch, font=font, fill=color)

    for _ in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(180, 180, 180), width=2)

    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')