# -*- coding: UTF-8 -*-
"""TranslationEngine — Argos Translate (primary) + LLM fallback."""

import hashlib
import json
import logging
import re
import time as _time

from app.config import AGENT_DEFAULT_MODEL
from app.util.translate.models import (
    ARGOS_LANGUAGES,
    LANG_NAMES_CN,
    STYLE_LABELS,
    _build_supported_pairs,
    detect_language,
)
from app.util.translate.models import detect_target_language as detect_target_language  # noqa: F401 — re-exported

# Discover installed Argos packages at import time
_ARGOS_PAIRS: set[tuple[str, str]] = _build_supported_pairs()

# ── Translation result cache ───────────────────────────────────────────────
# Redis-backed with in-memory fallback. Shared across workers when Redis is available.

_CACHE_TTL = 1800  # 30 minutes
_CACHE_MAX_SIZE = 256
_CACHE_REDIS_DB = 8
_CACHE_REDIS_PREFIX = "translate:cache:"
_translation_cache: dict[str, tuple[float, dict]] = {}


def _get_redis_client():
    """Lazy-load Redis client for translation cache. Returns None if unavailable."""
    try:
        from app.util.redis_utils import get_redis

        return get_redis(db=_CACHE_REDIS_DB)
    except Exception:
        return None


def _cache_key(text: str, target_lang: str, source_lang: str, style: str) -> str:
    return hashlib.md5(f"{text}|{target_lang}|{source_lang}|{style}".encode()).hexdigest()


def _cache_get(text: str, target_lang: str, source_lang: str, style: str) -> dict | None:
    key = _cache_key(text, target_lang, source_lang, style)

    # Try Redis first
    r = _get_redis_client()
    if r is not None:
        try:
            raw = r.get(_CACHE_REDIS_PREFIX + key)
            if raw:
                return json.loads(raw)
        except Exception:
            logging.debug("translate cache: Redis read failed, falling back to memory")

    # In-memory fallback
    entry = _translation_cache.get(key)
    if entry is None:
        return None
    expires, result = entry
    if _time.time() > expires:
        _translation_cache.pop(key, None)
        return None
    return dict(result)


def _cache_set(text: str, target_lang: str, source_lang: str, style: str, result: dict):
    key = _cache_key(text, target_lang, source_lang, style)

    # Try Redis first
    r = _get_redis_client()
    if r is not None:
        try:
            r.setex(_CACHE_REDIS_PREFIX + key, _CACHE_TTL, json.dumps(result, ensure_ascii=False))
            return
        except Exception:
            logging.debug("translate cache: Redis write failed, falling back to memory")

    # In-memory fallback
    if len(_translation_cache) >= _CACHE_MAX_SIZE:
        oldest = min(_translation_cache, key=lambda k: _translation_cache[k][0])
        _translation_cache.pop(oldest, None)
    _translation_cache[key] = (_time.time() + _CACHE_TTL, dict(result))


# ── LLM translate ──────────────────────────────────────────────────────────

_TRANSLATE_PROMPT = """You are a professional {style_label} translator.

Translate the following {src_label} text to {tgt_label}.
{style_instruction}

Rules:
- Preserve original formatting: line breaks, indentation, markdown syntax, code blocks.
- Keep numbers, dates, URLs, and proper names unchanged.
- Maintain consistent terminology throughout.
- Return ONLY the translation, no explanations, no notes, no prefixes.

Source text:
{text}"""

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "general": "Aim for natural, fluent {tgt_label} that reads as if originally written in that language.",
    "formal": "Use polite, formal {tgt_label} suitable for business, academic, or official contexts. Avoid colloquialisms.",
    "technical": "Use precise technical terminology in {tgt_label}. Preserve technical terms, acronyms, and code identifiers exactly as-is.",
}

# Long-text chunking: split at sentence boundaries, keep chunks under ~2000 chars
_CHUNK_LIMIT = 2000
_SENTENCE_BREAK_RE = re.compile(r"([.。!！?？\n])(?!\d)")


def _chunk_text(text: str) -> list[str]:
    """Split long text at sentence boundaries for reliable translation."""
    if len(text) <= _CHUNK_LIMIT:
        return [text]

    chunks: list[str] = []
    buf = ""
    # Split while preserving delimiters
    parts = _SENTENCE_BREAK_RE.split(text)
    for part in parts:
        buf += part
        if len(buf) >= _CHUNK_LIMIT:
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        if chunks:
            chunks.append(buf.strip())
        else:
            chunks.append(buf.strip())
    return chunks or [text]


def _llm_translate(text: str, target_lang: str, source_lang: str, style: str) -> dict:
    """Translate via LLM. Uses the configured default model with fallback chain."""
    from app.util.llm_client import get_llm_client

    src_label = LANG_NAMES_CN.get(source_lang, source_lang)
    tgt_label = LANG_NAMES_CN.get(target_lang, target_lang)
    style_label = STYLE_LABELS.get(style, "通用")
    style_instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["general"]).format(tgt_label=tgt_label)

    try:
        llm = get_llm_client()
        translated = _translate_text(text, llm, src_label, tgt_label, style_label, style_instruction)
        return {
            "ok": True,
            "translated": translated,
            "engine": "llm",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    except Exception:
        logging.warning("LLM translate failed", exc_info=True)
        return {"ok": False, "translated": "", "engine": "llm", "source_lang": source_lang, "target_lang": target_lang}


def _translate_text(text: str, llm, src_label: str, tgt_label: str, style_label: str, style_instruction: str) -> str:
    """Translate a single piece of text, chunking if needed."""
    chunks = _chunk_text(text)

    if len(chunks) == 1:
        prompt = _TRANSLATE_PROMPT.format(
            style_label=style_label,
            src_label=src_label,
            tgt_label=tgt_label,
            style_instruction=style_instruction,
            text=text,
        )
        resp = llm.chat.completions.create(
            model=AGENT_DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=min(len(text) * 3 + 200, 4096),
            timeout=30,
        )
        return (resp.choices[0].message.content or "").strip()

    # Multi-chunk: translate each segment
    translations: list[str] = []
    for chunk in chunks:
        prompt = _TRANSLATE_PROMPT.format(
            style_label=style_label,
            src_label=src_label,
            tgt_label=tgt_label,
            style_instruction=style_instruction,
            text=chunk,
        )
        resp = llm.chat.completions.create(
            model=AGENT_DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=min(len(chunk) * 3 + 200, 4096),
            timeout=30,
        )
        translated = (resp.choices[0].message.content or "").strip()
        translations.append(translated)

    return "\n\n".join(translations)


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
            return {
                "ok": False,
                "translated": "",
                "engine": "none",
                "source_lang": source_lang,
                "target_lang": target_lang,
            }

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
        use_argos = style == "general" and (source_lang, target_lang) in _ARGOS_PAIRS and text

        result = (
            _argos_translate(text, target_lang, source_lang)
            if use_argos
            else _llm_translate(text, target_lang, source_lang, style)
        )

        # Store in cache (only on success)
        if result.get("ok"):
            _cache_set(text, target_lang, source_lang, style, result)

        return result

    @staticmethod
    def supported_languages() -> dict:
        """Return language info for frontend/agent use."""
        return {
            "languages": ARGOS_LANGUAGES,
            "pairs_count": len(_ARGOS_PAIRS),
            "engine": "argos" if _ARGOS_PAIRS else "llm",
        }
