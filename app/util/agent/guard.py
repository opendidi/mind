# -*- coding: UTF-8 -*-
"""Agent Guard — input/tool/output safety checks (rule-based, zero token cost)."""

import json
import logging
import os
import re
import threading
import time

# ── Sensitive Word Loader ───────────────────────────────────────────────


def _load_word_list(filename: str) -> set:
    """Load a word list from file, one word per line, skip empty/comments."""
    words = set()
    try:
        path = os.path.join(os.path.dirname(__file__), "agent_eval", filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        words.add(line.lower())
        else:
            logging.debug("Guard word list not found: %s", path)
    except Exception:
        logging.warning("Failed to load word list: %s", filename)
    return words


_SENSITIVE_WORDS = _load_word_list("sensitive_words.txt")

# Built-in fallback
if not _SENSITIVE_WORDS:
    _SENSITIVE_WORDS = {
        # Basic sensitive words as fallback
    }

# ── PII Patterns ────────────────────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"1[3-9]\d{9}"), r"手机号***"),  # Chinese mobile
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), r"***@***.***"),  # Email
    (
        re.compile(r"\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b"),
        r"身份证号***",
    ),  # Chinese ID
    (re.compile(r"\b\d{3}-\d{4}-\d{4}\b"), r"电话***"),  # Phone format
    (re.compile(r"\b\d{15,19}\b"), r"银行卡号***"),  # Credit card length
]


# ── Input Guard ─────────────────────────────────────────────────────────

# Max input length (characters)
from app.util.agent.constants import MAX_INPUT_LENGTH

# Simple injection patterns to reject immediately
_INJECTION_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r'on\w+\s*=\s*"[^"]*"', re.IGNORECASE),
    re.compile(r"SELECT\s+.*\s+FROM\s+", re.IGNORECASE),
    re.compile(r"DROP\s+TABLE", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
]


class InputGuard:
    """Validate and sanitize user input before processing."""

    @staticmethod
    def check(text: str) -> dict:
        """Check input safety. Returns {"ok": True} or {"ok": False, "reason": ...}."""
        if not text or not text.strip():
            return {"ok": False, "reason": "输入为空"}

        # Length check
        if len(text) > MAX_INPUT_LENGTH:
            return {"ok": False, "reason": f"输入过长 (>{MAX_INPUT_LENGTH})"}

        # Injection check
        for pat in _INJECTION_PATTERNS:
            if pat.search(text):
                return {"ok": False, "reason": "检测到可疑输入"}

        # Sensitive word check
        lower = text.lower()
        for word in _SENSITIVE_WORDS:
            if word in lower:
                return {"ok": False, "reason": "输入包含敏感内容，请修改后重试"}

        return {"ok": True}

    @staticmethod
    def sanitize(text: str) -> str:
        """Strip HTML tags and null bytes. Returns cleaned text."""
        text = text.replace("\x00", "")
        text = re.sub(r"<[^>]*>", "", text)
        return text.strip()


# ── Tool Guard ──────────────────────────────────────────────────────────


class ToolGuard:
    """Validate tool calls and enforce safety limits."""

    # Tools requiring user confirmation
    DESTRUCTIVE_TOOLS = {"canvas_delete_pen", "canvas_clear", "delete_conversation"}

    # Max calls per tool per session
    _tool_call_counts: dict = {}
    _lock = threading.Lock()
    from app.util.agent.constants import MAX_CALLS_PER_TOOL

    @classmethod
    def check_tool_call(cls, tool_name: str, tool_args: dict, session_id: str = "") -> dict:
        """Check a tool call before execution.

        Returns {"ok": True} or {"ok": False, "reason": str, "confirm_required": bool}.
        """
        # Rate limit
        with cls._lock:
            key = f"{session_id}:{tool_name}"
            count = cls._tool_call_counts.get(key, 0) + 1
            cls._tool_call_counts[key] = count
        if count > cls.MAX_CALLS_PER_TOOL:
            return {
                "ok": False,
                "reason": f"工具 {tool_name} 调用次数过多 ({count})，已限制",
                "confirm_required": False,
            }

        # Parameter safety: prevent path traversal in file tools
        if tool_name in ("file_search", "read_text", "parse_json", "extract_excel", "analyze_doc"):
            for param in ("object_name", "path", "keyword"):
                val = tool_args.get(param, "")
                if isinstance(val, str) and (".." in val or val.startswith("/")):
                    return {
                        "ok": False,
                        "reason": "参数包含非法路径",
                        "confirm_required": False,
                    }

        # Destructive operations require confirmation
        destructive = any(tool_name.startswith(t) or tool_name == t for t in cls.DESTRUCTIVE_TOOLS)
        if destructive:
            return {"ok": True, "confirm_required": True}

        return {"ok": True, "confirm_required": False}

    @classmethod
    def reset_session(cls, session_id: str):
        """Clear call counts for a session."""
        with cls._lock:
            keys = [k for k in cls._tool_call_counts if k.startswith(session_id)]
            for k in keys:
                del cls._tool_call_counts[k]


# ── Output Guard ────────────────────────────────────────────────────────


class OutputGuard:
    """Sanitize agent output before sending to user."""

    @staticmethod
    def redact_pii(text: str) -> str:
        """Redact personally identifiable information."""
        for pattern, replacement in _PII_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    @staticmethod
    def check_harmful(text: str) -> dict:
        """Check for harmful content in agent response.

        Matching rules:
        - ASCII/English words: must appear as a standalone token (surrounded by
          non-alphanumeric chars, CJK chars, or text boundaries). This avoids
          substring false positives like 'VPN' inside 'freeVPNproxy'.
        - CJK words: simple substring match (Chinese has no natural word
          boundaries, so boundary detection is unreliable without NLP).

        Returns {"ok": True} or {"ok": False, "reason": ...}.
        """
        if not text:
            return {"ok": True}

        lower = text.lower()
        for word in _SENSITIVE_WORDS:
            if not word:
                continue
            if word.isascii():
                # Match as standalone token: bounded by non-alnum, CJK, or text edge
                escaped = re.escape(word)
                pattern = re.compile(
                    r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])",
                    re.IGNORECASE,
                )
                if pattern.search(text):
                    return {"ok": False, "reason": "响应包含不适当内容"}
            else:
                # CJK — simple substring match
                if word in lower:
                    return {"ok": False, "reason": "响应包含不适当内容"}

        return {"ok": True}

    @staticmethod
    def validate_code_block(text: str, block_type: str) -> bool:
        """Check if a ```map or ```route code block has valid JSON."""
        if block_type not in ("map", "route"):
            return True
        pattern = rf"```{block_type}\s*\n(.*?)\n```"
        for m in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            try:
                data = json.loads(m.group(1))
                if block_type == "map" and "center" not in data:
                    return False
                if block_type == "route" and "from" not in data and "to" not in data:
                    return False
            except (json.JSONDecodeError, ValueError):
                return False
        return True

    @staticmethod
    def process(text: str) -> dict:
        """Full output pipeline: PII redact + harmful check + format validate.

        Returns {"ok": True, "text": sanitized_text}
                or {"ok": False, "reason": ...}.
        """
        harmful = OutputGuard.check_harmful(text)
        if not harmful["ok"]:
            return harmful

        cleaned = OutputGuard.redact_pii(text)

        # Validate code blocks
        for bt in ("map", "route"):
            if f"```{bt}" in cleaned:
                if not OutputGuard.validate_code_block(cleaned, bt):
                    logging.warning("OutputGuard: invalid %s block in response", bt)
                    return {"ok": False, "reason": f"invalid {bt} code block", "text": cleaned}

        return {"ok": True, "text": cleaned}
