# -*- coding: UTF-8 -*-
"""
User auth utilities — JWT token creation + captcha generation + password hashing
"""
import os
import io
import uuid
import random
import string
import bcrypt
import jwt
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter


SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
JWT_ACCESS_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 30 * 60))  # 30 min
JWT_REFRESH_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 7 * 86400))  # 7 days
JWT_ALGORITHM = 'HS256'


def create_access_token(user_id: str) -> str:
    payload = {
        'sub': user_id,
        'type': 'access',
        'jti': str(uuid.uuid4()),
        'exp': datetime.utcnow() + timedelta(seconds=JWT_ACCESS_EXPIRES),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        'sub': user_id,
        'type': 'refresh',
        'jti': str(uuid.uuid4()),
        'exp': datetime.utcnow() + timedelta(seconds=JWT_REFRESH_EXPIRES),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(input_password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash.encode('utf-8'))


def generate_captcha_text(length: int = 4) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_captcha_image(text: str) -> str:
    """Generate a captcha image, return base64 JPEG data URL."""
    import base64
    width, height = 152, 48
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Background noise
    for x in range(width):
        for y in range(height):
            if random.random() < 0.05:
                draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    # Draw characters — try multiple font paths (Docker 容器通常没有 Arial)
    font = None
    _font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ]
    for fp in _font_paths:
        try:
            font = ImageFont.truetype(fp, 32)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    for i, ch in enumerate(text):
        x = 14 + i * 32 + random.randint(-3, 3)
        y = random.randint(3, 10)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), ch, font=font, fill=color)

    # Interference lines
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), width=1)

    image = image.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=75)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
