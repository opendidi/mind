# -*- coding: UTF-8 -*-

import logging
import os
import sys
import time
from collections import defaultdict
from contextlib import suppress

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS


def _init_logging():
    """Patch StreamHandler to survive UnicodeEncodeError on Windows GBK systems."""
    _orig_emit = logging.StreamHandler.emit

    def _safe_emit(self, record):
        try:
            _orig_emit(self, record)
        except (UnicodeEncodeError, TypeError, ValueError):
            try:
                stream = self.stream
            except AttributeError:
                return
            msg = self.format(record)
            # If stream is binary or encoding-challenged, safely write
            try:
                stream.write(msg + self.terminator)
            except (UnicodeEncodeError, TypeError):
                safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
                with suppress(Exception):
                    stream.write((safe_msg + self.terminator).encode("utf-8"))

    logging.StreamHandler.emit = _safe_emit

    # Ensure a usable root handler exists
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        )
        root.addHandler(h)
        root.setLevel(logging.DEBUG)

    # Suppress overly verbose third-party debug logs
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


_init_logging()

load_dotenv()

# ── Rate limiter (simple in-memory, per-IP) ──────────────────────────────

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # 窗口秒数
_RATE_LIMIT_MAX = 60  # 每窗口最大请求数
_RATE_LIMIT_AGENT_MAX = 60  # Agent 端点（含 SSE 长连接/重连）


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
    app = Flask(__name__, static_folder="static", static_url_path="/v1/static")

    # Security: restrict CORS to known frontend origins
    frontend_url = os.environ.get("APP_URL", "http://localhost:3100")
    allowed_origins = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS",
            f"http://localhost:3100,http://127.0.0.1:3100,{frontend_url}",
        ).split(",")
        if o.strip()
    ]
    CORS(app, origins=allowed_origins, supports_credentials=True)

    # Security: set SECRET_KEY
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    # Security: add HTTP security headers
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Rate limiting middleware
    @app.before_request
    def rate_limit():
        # Skip static files and CORS preflight
        if request.path.startswith("/v1/static"):
            return None
        if request.method == "OPTIONS":
            return None

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")

        # Stricter limits for Agent endpoints
        if "/agent/" in request.path:
            max_req = _RATE_LIMIT_AGENT_MAX
        else:
            max_req = _RATE_LIMIT_MAX

        if not _rate_limit_check(client_ip, max_req):
            resp = jsonify(
                {
                    "code": 429,
                    "message": "请求过于频繁，请稍后重试",
                    "data": None,
                }
            )
            resp.headers["Retry-After"] = str(_RATE_LIMIT_WINDOW)
            return resp, 429

        return None

    register_blueprints(app)

    # ── SPA fallback for HTML5 history mode ──────────────────────────────
    # In production, Flask serves the built frontend. All non-API routes
    # return index.html so Vue Router can handle client-side routing.
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        # API routes are handled by blueprints — never intercept them
        if path.startswith("v1/"):
            from flask import abort

            abort(404)
        import os as _os

        from flask import send_from_directory

        static_dir = _os.path.join(app.root_path, "static")
        file_path = _os.path.join(static_dir, path)
        if path and _os.path.isfile(file_path):
            return send_from_directory(static_dir, path)
        index_path = _os.path.join(static_dir, "index.html")
        if _os.path.isfile(index_path):
            return send_from_directory(static_dir, "index.html")
        return {"code": 404, "message": "Not found"}, 404

    return app
