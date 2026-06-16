# -*- coding: UTF-8 -*-

import os
import time
from collections import defaultdict

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

# ── Rate limiter (simple in-memory, per-IP) ──────────────────────────────

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60       # 窗口秒数
_RATE_LIMIT_MAX = 60           # 每窗口最大请求数
_RATE_LIMIT_AGENT_MAX = 20     # Agent 端点更严格


def _rate_limit_check(key: str, max_req: int = _RATE_LIMIT_MAX) -> bool:
    """Return True if allowed, False if rate-limited."""
    now = time.time()
    window = now - _RATE_LIMIT_WINDOW
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > window]
    if len(_rate_limit_store[key]) >= max_req:
        return False
    _rate_limit_store[key].append(now)
    return True


def register_blueprints(app):
    from app.api.v1 import create_v1
    app.register_blueprint(create_v1(), url_prefix="/v1")


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/v1/static')

    # Security: restrict CORS to known frontend origins
    frontend_url = os.environ.get('APP_URL', 'http://localhost:3100')
    allowed_origins = [o.strip() for o in os.environ.get(
        'CORS_ORIGINS',
        f'http://localhost:3100,http://127.0.0.1:3100,{frontend_url}',
    ).split(',') if o.strip()]
    CORS(app, origins=allowed_origins, supports_credentials=True)

    # Security: set SECRET_KEY
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())

    # Security: add HTTP security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Rate limiting middleware
    @app.before_request
    def rate_limit():
        # Skip static files
        if request.path.startswith('/v1/static'):
            return None

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')

        # Stricter limits for Agent endpoints
        if '/agent/' in request.path:
            max_req = _RATE_LIMIT_AGENT_MAX
        else:
            max_req = _RATE_LIMIT_MAX

        if not _rate_limit_check(client_ip, max_req):
            return jsonify({
                'code': 429,
                'message': '请求过于频繁，请稍后重试',
                'data': None,
            }), 429

        return None

    register_blueprints(app)
    return app
