# -*- coding: UTF-8 -*-
"""POST /v1/translate — lightweight translation endpoint (bypasses Agent pipeline)."""

import logging

from flask import Blueprint, g, jsonify, request

from app.util.decorators import token_required
from app.util.translate import TranslationEngine, detect_target_language

translate_api = Blueprint("translate", __name__)


@translate_api.route("/translate", methods=["POST"])
@token_required
def translate_text():
    """Translate text directly without going through the Agent pipeline."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    target_lang = (data.get("target_lang") or "").strip()
    source_lang = (data.get("source_lang") or "auto").strip()
    style = (data.get("style") or "general").strip()

    if not text:
        return jsonify({"code": 400, "message": "text 不能为空"}), 400
    if len(text) > 20000:
        return jsonify({"code": 400, "message": f"text too long ({len(text)} > 20000)"}), 400
    if style not in ("general", "formal", "technical"):
        return jsonify({"code": 400, "message": "style 必须为 general/formal/technical"}), 400

    # Auto-detect target language when not specified (same heuristic as Agent tool)
    if not target_lang:
        target_lang = detect_target_language(text, source_lang if source_lang != "auto" else "")

    try:
        result = TranslationEngine.translate(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang,
            style=style,
        )
        if result["ok"]:
            return jsonify({"code": 200, "data": result})
        else:
            return jsonify({"code": 500, "message": "翻译失败，请稍后重试"}), 500
    except Exception:
        logging.warning("translate API failed", exc_info=True)
        return jsonify({"code": 500, "message": "翻译服务异常"}), 500


@translate_api.route("/translate/languages", methods=["GET"])
@token_required
def get_languages():
    """Return supported languages and engine status."""
    info = TranslationEngine.supported_languages()
    return jsonify({"code": 200, "data": info})
