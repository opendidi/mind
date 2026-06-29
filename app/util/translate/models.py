# -*- coding: UTF-8 -*-
"""Language code mappings and Argos model management."""

import logging
import re

# ── Language codes supported by Argos Translate ─────────────────────────
# Argos uses ISO 639-1 codes.
# Full list: https://www.argosopentech.com/

ARGOS_LANGUAGES: dict[str, str] = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "ar": "Arabic",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "hi": "Hindi",
    "he": "Hebrew",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "nb": "Norwegian",
    "cs": "Czech",
    "ro": "Romanian",
    "uk": "Ukrainian",
    "el": "Greek",
    "hu": "Hungarian",
    "bg": "Bulgarian",
    "sk": "Slovak",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "sl": "Slovenian",
}

# Language-to-language name (simplified subset for LLM prompt context)
LANG_NAMES_CN: dict[str, str] = {
    "zh": "中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ru": "俄语",
    "ar": "阿拉伯语",
    "nl": "荷兰语",
    "pl": "波兰语",
    "tr": "土耳其语",
    "vi": "越南语",
    "th": "泰语",
    "id": "印尼语",
    "hi": "印地语",
    "he": "希伯来语",
    "sv": "瑞典语",
    "da": "丹麦语",
    "fi": "芬兰语",
    "nb": "挪威语",
    "cs": "捷克语",
    "ro": "罗马尼亚语",
    "uk": "乌克兰语",
    "el": "希腊语",
    "hu": "匈牙利语",
    "bg": "保加利亚语",
    "sk": "斯洛伐克语",
    "lt": "立陶宛语",
    "lv": "拉脱维亚语",
    "et": "爱沙尼亚语",
    "sl": "斯洛文尼亚语",
}

STYLE_LABELS: dict[str, str] = {
    "general": "通用",
    "formal": "正式",
    "technical": "技术文档",
}


def _build_supported_pairs() -> set[tuple[str, str]]:
    """Discover installed Argos language pairs. Returns empty set if not installed."""
    pairs: set[tuple[str, str]] = set()
    try:
        import argostranslate.package
        import argostranslate.translate

        installed = argostranslate.package.get_installed_packages()
        for pkg in installed:
            pairs.add((pkg.from_code, pkg.to_code))
        logging.info("Argos: %d installed language pairs", len(pairs))
    except ImportError:
        logging.info("Argos Translate not installed — will use LLM for all translations")
    except Exception:
        logging.warning("Argos: failed to enumerate packages", exc_info=True)
    return pairs


# CJK character range covering Basic + Extension A blocks
_CJK_RE = re.compile(r"[一-鿿㐀-䶿]")
_JAPANESE_RE = re.compile(r"[ぁ-ゟァ-ヿｦ-ﾟ]")
_KOREAN_RE = re.compile(r"[가-힯]")


def detect_language(text: str) -> str:
    """Detect source language via character-set ratio heuristics. Fallback to 'en'.

    Uses the same CJK range and ratio threshold as the frontend so
    detection is consistent across the whole pipeline.
    """
    stripped = re.sub(r"\s", "", text)
    total = len(stripped)
    if total == 0:
        return "en"

    cjk = len(_CJK_RE.findall(text))
    japanese = len(_JAPANESE_RE.findall(text))
    korean = len(_KOREAN_RE.findall(text))

    if korean > total * 0.3:
        return "ko"
    if japanese > total * 0.3:
        return "ja"
    if cjk > total * 0.3:
        return "zh"
    return "en"


def detect_target_language(text: str, source_lang: str = "") -> str:
    """Auto-select a sensible target language.

    - Chinese text → English
    - Japanese / Korean → English
    - Everything else → Chinese

    When *source_lang* is already known the heuristics are applied directly;
    otherwise the text is scanned first.
    """
    src = source_lang or detect_language(text)
    if src in ("zh", "ja", "ko"):
        return "en"
    return "zh"
