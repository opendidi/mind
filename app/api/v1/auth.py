# -*- coding: UTF-8 -*-
"""
Auth API — login / register / logout / refresh / profile / captcha
"""
import re
import logging
import time
from flask import Blueprint, request, jsonify, make_response, g
from app.plugin.auth import (
    create_access_token, create_refresh_token, decode_token
)
from app.plugin.auth.utils import generate_captcha_text, generate_captcha_image
from app.package.module.user_mysql import UserMysqlHandler
from app.util.decorators import token_required

auth_api = Blueprint("auth_api", __name__)

# In-memory captcha store: {captcha_id: {'text': ..., 'expires': ...}}
_captcha_store = {}
CAPTCHA_TTL = 300  # 5 minutes


def _clean_expired_captchas():
    now = time.time()
    expired = [k for k, v in _captcha_store.items() if v['expires'] < now]
    for k in expired:
        del _captcha_store[k]


def _is_valid_password(password: str) -> tuple:
    """Validate password strength. Returns (valid: bool, message: str)."""
    if len(password) < 8 or len(password) > 128:
        return False, '密码长度应为 8-128 个字符'
    if not re.search(r'[a-z]', password):
        return False, '密码需包含小写字母'
    if not re.search(r'[A-Z]', password):
        return False, '密码需包含大写字母'
    if not re.search(r'\d', password):
        return False, '密码需包含数字'
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>\/?~`]', password):
        return False, '密码需包含特殊字符'
    if re.search(r'\s', password):
        return False, '密码不能包含空格'
    return True, ''


# ── GET /captcha ──────────────────────────────────────────────────

@auth_api.route('/captcha', methods=['GET'])
def get_captcha():
    _clean_expired_captchas()
    captcha_id = str(int(time.time() * 1000))
    text = generate_captcha_text(4)
    image_data = generate_captcha_image(text)
    _captcha_store[captcha_id] = {'text': text.upper(), 'expires': time.time() + CAPTCHA_TTL}
    return jsonify({
        'code': 200,
        'data': {'captcha_id': captcha_id, 'captcha_image': image_data},
        'message': 'ok',
    })


# ── POST /login ───────────────────────────────────────────────────

@auth_api.route('/login', methods=['POST'])
def login():
    _clean_expired_captchas()

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    captcha_text = (request.form.get('captcha') or '').strip()
    captcha_id = request.form.get('captcha_id') or ''

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空', 'data': None}), 400

    # Verify captcha
    captcha_data = _captcha_store.pop(captcha_id, None)
    if captcha_data and captcha_data['expires'] < time.time():
        captcha_data = None
    if not captcha_data or captcha_text.upper() != captcha_data['text']:
        return jsonify({'code': 400, 'message': '验证码错误或已过期', 'data': None}), 400

    # Check username format
    if len(username) < 3 or len(username) > 20:
        return jsonify({'code': 400, 'message': '用户名长度应为 3-20 个字符', 'data': None}), 400

    success, result = UserMysqlHandler.verify_user(username, password)
    if not success:
        return jsonify({'code': 400, 'message': result, 'data': None}), 400

    access_token = create_access_token(result['id'])
    refresh_token = create_refresh_token(result['id'])

    resp = make_response(jsonify({
        'code': 200,
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'id': result['id'],
            'username': result['username'],
            'email': result.get('email'),
        },
        'message': '登录成功',
    }))
    resp.set_cookie('access_token', access_token, httponly=True, samesite='Strict')
    return resp


# ── POST /register ────────────────────────────────────────────────

@auth_api.route('/register', methods=['POST'])
def register():
    _clean_expired_captchas()

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    captcha_text = (request.form.get('captcha') or '').strip()
    captcha_id = request.form.get('captcha_id') or ''

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空', 'data': None}), 400

    # Verify captcha
    captcha_data = _captcha_store.pop(captcha_id, None)
    if captcha_data and captcha_data['expires'] < time.time():
        captcha_data = None
    if not captcha_data or captcha_text.upper() != captcha_data['text']:
        return jsonify({'code': 400, 'message': '验证码错误或已过期', 'data': None}), 400

    # Validate username
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return jsonify({'code': 400, 'message': '用户名只能包含字母、数字和下划线，长度 3-20', 'data': None}), 400

    # Validate password
    valid, msg = _is_valid_password(password)
    if not valid:
        return jsonify({'code': 400, 'message': msg, 'data': None}), 400

    success, result = UserMysqlHandler.create_user(username, password)
    if not success:
        return jsonify({'code': 400, 'message': result, 'data': None}), 400

    return jsonify({'code': 200, 'data': {'id': result}, 'message': '注册成功'})


# ── POST /logout ──────────────────────────────────────────────────

@auth_api.route('/logout', methods=['POST'])
@token_required
def logout():
    resp = make_response(jsonify({'code': 200, 'data': None, 'message': '已退出登录'}))
    resp.delete_cookie('access_token')
    return resp


# ── POST /refresh ─────────────────────────────────────────────────

@auth_api.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json(silent=True) or {}
    refresh_str = data.get('refresh_token', '')
    if not refresh_str:
        return jsonify({'code': 400, 'message': '缺少 refresh_token', 'data': None}), 400

    try:
        payload = decode_token(refresh_str)
        if payload.get('type') != 'refresh':
            return jsonify({'code': 401, 'message': '令牌类型错误', 'data': None}), 401

        user_id = payload['sub']
        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)

        resp = make_response(jsonify({
            'code': 200,
            'data': {'access_token': new_access, 'refresh_token': new_refresh},
            'message': 'ok',
        }))
        resp.set_cookie('access_token', new_access, httponly=True, samesite='Strict')
        return resp
    except Exception:
        return jsonify({'code': 401, 'message': 'refresh_token 无效或已过期', 'data': None}), 401


# ── GET /profile ──────────────────────────────────────────────────

@auth_api.route('/profile', methods=['GET'])
@token_required
def get_profile():
    user = UserMysqlHandler.get_user_profile(g.user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在', 'data': None}), 404
    return jsonify({'code': 200, 'data': user, 'message': 'ok'})


# ── PUT /profile ──────────────────────────────────────────────────

@auth_api.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    email = request.form.get('email', '').strip()
    success, msg = UserMysqlHandler.update_profile(g.user_id, email if email else None)
    if not success:
        return jsonify({'code': 400, 'message': msg, 'data': None}), 400

    user = UserMysqlHandler.get_user_profile(g.user_id)
    return jsonify({'code': 200, 'data': user, 'message': '更新成功'})


# ── POST /change-password ────────────────────────────────────────

@auth_api.route('/change-password', methods=['POST'])
@token_required
def change_password():
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '密码不能为空', 'data': None}), 400

    valid, msg = _is_valid_password(new_password)
    if not valid:
        return jsonify({'code': 400, 'message': msg, 'data': None}), 400

    success, msg = UserMysqlHandler.change_password(g.user_id, old_password, new_password)
    if not success:
        return jsonify({'code': 400, 'message': msg, 'data': None}), 400

    return jsonify({'code': 200, 'data': None, 'message': msg})
