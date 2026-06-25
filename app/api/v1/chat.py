# -*- coding: UTF-8 -*-
"""
Chat API — conversation CRUD + document upload
"""

import logging
import os
import tempfile
import time
import uuid as _uuid

from flask import Blueprint, g, jsonify, request

from app.package.module.chat_mysql import ChatMysqlHandler
from app.plugin.minio.app.controller import MinioUtil
from app.util.decorators import token_required

chat_api = Blueprint("chat_api", __name__)


@chat_api.route("/conversations", methods=["GET"])
@token_required
def list_conversations():
    """GET /chat/conversations — list user's conversations."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    keyword = request.args.get("keyword")
    rows = ChatMysqlHandler.list_conversations(g.user_id, limit, offset, keyword)
    return jsonify({"code": 200, "data": rows, "message": "ok"})


@chat_api.route("/conversations/<conv_id>", methods=["GET"])
@token_required
def get_conversation(conv_id):
    """GET /chat/conversations/:id — load a conversation with messages."""
    row = ChatMysqlHandler.get_conversation(conv_id, g.user_id)
    if not row:
        return jsonify({"code": 404, "message": "对话不存在"}), 404
    return jsonify({"code": 200, "data": row, "message": "ok"})


@chat_api.route("/conversations", methods=["POST"])
@token_required
def save_conversation():
    """POST /chat/conversations — save or update a conversation."""
    data = request.get_json(silent=True) or {}
    success, result = ChatMysqlHandler.save_conversation(g.user_id, data)
    if not success:
        return jsonify({"code": 500, "message": result}), 500
    return jsonify({"code": 200, "data": {"id": result}, "message": "ok"})


@chat_api.route("/conversations/<conv_id>", methods=["DELETE"])
@token_required
def delete_conversation(conv_id):
    """DELETE /chat/conversations/:id — delete a conversation."""
    deleted = ChatMysqlHandler.delete_conversation(conv_id, g.user_id)
    if not deleted:
        return jsonify({"code": 404, "message": "对话不存在"}), 404
    return jsonify({"code": 200, "message": "ok"})


@chat_api.route("/conversations/<conv_id>/feedback", methods=["PATCH"])
@token_required
def update_feedback(conv_id):
    """PATCH /chat/conversations/:id/feedback — update message feedback."""
    data = request.get_json(silent=True) or {}
    msg_id = data.get("msg_id")
    feedback = data.get("feedback")
    if not msg_id or not feedback:
        return jsonify({"code": 400, "message": "缺少参数"}), 400
    ChatMysqlHandler.update_feedback(conv_id, g.user_id, msg_id, feedback)
    return jsonify({"code": 200, "message": "ok"})


@chat_api.route("/upload", methods=["POST"])
@token_required
def upload_file():
    """POST /chat/upload — upload document file to MinIO for agent analysis."""
    if "file" not in request.files:
        return jsonify({"code": 400, "message": "缺少文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"code": 400, "message": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".docx", ".xlsx", ".xls", ".txt", ".md", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        return (
            jsonify(
                {
                    "code": 400,
                    "message": "仅支持 .docx / .xlsx / .xls / .txt / .md / .json / .png / .jpg / .gif / .webp / .svg 格式",
                }
            ),
            400,
        )

    MAX_SIZE = 10 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        return jsonify({"code": 400, "message": f"文件过大，请控制在 10MB 以内"}), 400

    date_str = time.strftime("%Y%m%d")
    uid = str(_uuid.uuid4()).replace("-", "")
    object_name = f"documents/{date_str}/{uid}{ext}"

    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        file.save(tmp_path)
        url = MinioUtil.upload_pano_file(tmp_path, object_name)
        if not url:
            return jsonify({"code": 500, "message": "MinIO 上传失败"}), 500
        return jsonify(
            {
                "code": 200,
                "data": {
                    "object_name": object_name,
                    "url": url,
                    "filename": file.filename,
                    "size": size,
                },
                "message": "ok",
            }
        )
    except Exception:
        logging.exception("文档上传失败")
        return jsonify({"code": 500, "message": "上传失败"}), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
