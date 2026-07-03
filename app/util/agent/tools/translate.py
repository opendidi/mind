# -*- coding: UTF-8 -*-
"""Translate text tool for Agent system — registered via ToolRegistry decorator."""

import logging

from app.util.tool_registry import ToolRegistry

TRANSLATE_PARAMS = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "要翻译的文本内容",
        },
        "target_lang": {
            "type": "string",
            "description": "目标语言代码，如 zh/en/ja/ko/fr/de/es。不填则自动判断：中文→英文，英文→中文。",
        },
        "source_lang": {
            "type": "string",
            "description": "源语言代码，不填则自动检测。常用: zh/en/ja/ko",
        },
        "style": {
            "type": "string",
            "description": "翻译风格: general(通用), formal(正式), technical(技术文档)",
            "enum": ["general", "formal", "technical"],
        },
    },
    "required": ["text"],
}


@ToolRegistry.register(
    "translate_text",
    "翻译文本。将一段文本翻译为指定语言。支持自动检测源语言和智能选择目标语言，可选择通用/正式/技术文档风格。",
    TRANSLATE_PARAMS,
)
def _translate_tool_handler(
    text: str, target_lang: str = "", source_lang: str = "auto", style: str = "general"
) -> dict:
    """Translate text using Argos (primary) or LLM (fallback)."""
    from app.util.translate import TranslationEngine, detect_target_language

    if not target_lang:
        target_lang = detect_target_language(text, source_lang if source_lang != "auto" else "")

    return TranslationEngine.translate(
        text=text,
        target_lang=target_lang,
        source_lang=source_lang,
        style=style,
    )


logging.info("translate_text tool registered")
