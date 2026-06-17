# -*- coding: UTF-8 -*-
"""
Auth decorators — token_required for protecting API endpoints
"""
from functools import wraps
from flask import request, g, jsonify
from app.plugin.auth import decode_token


def token_required(f):
    """Decorator: require valid JWT access token in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Extract from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        # Also check cookie
        if not token:
            token = request.cookies.get('access_token')

        if not token:
            return jsonify({'code': 401, 'message': '缺少认证令牌', 'data': None}), 401

        try:
            payload = decode_token(token)
            if payload.get('type') != 'access':
                return jsonify({'code': 401, 'message': '令牌类型错误', 'data': None}), 401
            g.jwt_payload = payload
            g.user_id = payload['sub']
        except Exception:
            return jsonify({'code': 401, 'message': '令牌无效或已过期', 'data': None}), 401

        return f(*args, **kwargs)
    return decorated
