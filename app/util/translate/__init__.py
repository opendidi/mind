# -*- coding: UTF-8 -*-
"""TranslationEngine — Argos Translate (primary) + LLM fallback."""

import hashlib
import logging
import time as _time

from app.util.translate.models import (
    ARGOS_LANGUAGES,
    LANG_NAMES_CN,
    STYLE_LABELS,
    _build_supported_pairs,
    detect_language,
)
from app.util.translate.models import (
    detect_target_language as detect_target_language,  # noqa: F401 — re-exported
)

# Discover installed Argos packages at import time
_ARGOS_PAIRS: set[tuple[str, str]] = _build_supported_pairs()

# ── Translation result cache ───────────────────────────────────────────────
# Avoids re-translating the same (text, target, source, style) within a session.
# LLM translation is expensive; Argos is cheap but still not free.

_CACHE_TTL = 1800  # 30 minutes
_CACHE_MAX_SIZE = 256
_translation_cache: dict[str, tuple[float, dict]] = {}


def _cache_key(text: str, target_lang: str, source_lang: str, style: str) -> str:
    return hashlib.md5(f"{text}|{target_lang}|{source_lang}|{style}".encode()).hexdigest()


def _cache_get(text: str, target_lang: str, source_lang: str, style: str) -> dict | None:
    key = _cache_key(text, target_lang, source_lang, style)
    entry = _translation_cache.get(key)
    if entry is None:
        return None
    expires, result = entry
    if _time.time() > expires:
        _translation_cache.pop(key, None)
        return None
    return dict(result)  # shallow copy so callers can't mutate cached value

# LLM translate prompt template
_TRANSLATE_PROMPT = """You are a professional {style_label} translator. Translate the {src_label} text to {tgt_label} accurately.
Preserve the original formatting. Return ONLY the translation, no explanations.

Source text:
{text}"""


def _llm_translate(text: str, target_lang: str, source_lang: str, style: str) -> dict:
    """Translate via LLM (DeepSeek). Used as fallback for unsupported language pairs."""
    from app.util.llm_client import get_llm_client

    src_label = LANG_NAMES_CN.get(source_lang, source_lang)
    tgt_label = LANG_NAMES_CN.get(target_lang, target_lang)
    style_label = STYLE_LABELS.get(style, "通用")

    prompt = _TRANSLATE_PROMPT.format(
        style_label=style_label,
        src_label=src_label,
        tgt_label=tgt_label,
        text=text,
    )

    try:
        llm = get_llm_client()
        resp = llm.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=min(len(text) * 3 + 200, 4096),
            timeout=30,
        )
        translated = resp.choices[0].message.content or ""
        return {
            "ok": True,
            "translated": translated.strip(),
            "engine": "llm",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    except Exception:
        logging.warning("LLM translate failed", exc_info=True)
        return {"ok": False, "translated": "", "engine": "llm", "source_lang": source_lang, "target_lang": target_lang}


def _argos_translate(text: str, target_lang: str, source_lang: str) -> dict:
    """Translate via Argos Translate local engine."""
    try:
        import argostranslate.translate

        translation = argostranslate.translate.translate(text, source_lang, target_lang)
        return {
            "ok": True,
            "translated": str(translation),
            "engine": "argos",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    except Exception:
        logging.warning("Argos translate failed, falling back to LLM", exc_info=True)
        return _llm_translate(text, target_lang, source_lang, "general")


class TranslationEngine:
    """Unified translation engine with Argos (fast/free) + LLM (quality/coverage) fallback."""

    @staticmethod
    def translate(
        text: str,
        target_lang: str,
        source_lang: str = "auto",
        style: str = "general",
    ) -> dict:
        """Translate text. Returns {"ok": True/False, "translated": str, "engine": str, ...}."""
        if not text or not text.strip():
            return {"ok": False, "translated": "", "engine": "none", "source_lang": source_lang, "target_lang": target_lang}

        text = text.strip()

        # Resolve source language
        if source_lang == "auto":
            source_lang = detect_language(text)

        # Check cache
        cached = _cache_get(text, target_lang, source_lang, style)
        if cached is not None:
            cached["engine"] = cached.get("engine", "argos") + ":cached"
            return cached

        # Route
        use_argos = (
            style == "general"
            and (source_lang, target_lang) in _ARGOS_PAIRS
            and text
        )

        result = _argos_translate(text, target_lang, source_lang) if use_argos else _llm_translate(text, target_lang, source_lang, style)

        # Store in cache (only on success)
        if result.get("ok"):
            key = _cache_key(text, target_lang, source_lang, style)
            if len(_translation_cache) >= _CACHE_MAX_SIZE:
                # Evict oldest entry
                oldest = min(_translation_cache, key=lambda k: _translation_cache[k][0])
                _translation_cache.pop(oldest, None)
            _translation_cache[key] = (_time.time() + _CACHE_TTL, dict(result))

        return result

    @staticmethod
    def supported_languages() -> dict:
        """Return language info for frontend/agent use."""
        return {
            "languages": ARGOS_LANGUAGES,
            "pairs_count": len(_ARGOS_PAIRS),
            "engine": "argos" if _ARGOS_PAIRS else "llm",
        }
