# -*- coding: UTF-8 -*-
"""Shared helper utilities for the Agent system — JSON extraction, repair, etc."""

import re


def extract_json(text: str) -> str:
    """Extract JSON from LLM response (handles markdown fences, stray text)."""
    if not text or not text.strip():
        return ""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{") or text.startswith("["):
        return text
    m = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}", text, re.DOTALL)
    if m:
        start = m.start()
        depth = 0
        end = start
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            return text[start:end]
    return ""


def repair_json(text: str) -> str:
    """Repair common JSON issues from truncated/malformed LLM output.

    Handles: trailing commas, unclosed strings, unclosed braces/brackets.
    Closes structures in correct nested order (LIFO).
    """
    if not text or not text.strip():
        return text
    text = text.strip()

    # 1. Remove trailing commas
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r",\s*$", "", text)

    # 2. Detect and close unterminated string
    in_string = False
    for i, ch in enumerate(text):
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
    if in_string:
        text += '"'

    # 3. Close unclosed braces/brackets in correct LIFO order
    stack = []
    in_str = False
    for i, ch in enumerate(text):
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_str = not in_str
        elif not in_str:
            if ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch == "}" or ch == "]":
                if stack and stack[-1] == ch:
                    stack.pop()
    text += "".join(reversed(stack))

    return text


# ── Token Estimation ─────────────────────────────────────────────────────

_CJK_WEIGHT = 1.0 / 1.5
_ASCII_WEIGHT = 1.0 / 4.0
_OTHER_WEIGHT = 1.0 / 2.5


def estimate_tokens_from_str(text: str) -> int:
    """Estimate token count from a single string (CJK-aware)."""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿")
    ascii_chars = sum(1 for ch in text if ord(ch) < 128 and ch != " ")
    other = len(text) - cjk - ascii_chars
    return max(1, int(cjk * _CJK_WEIGHT + ascii_chars * _ASCII_WEIGHT + other * _OTHER_WEIGHT))


def estimate_tokens_from_messages(messages: list, chars_per_token: float = 2.5) -> int:
    """Estimate token count from a list of message dicts (content + tool_calls)."""
    total = 0
    for m in messages:
        content = m.get("content", "") or ""
        total += len(content) / chars_per_token
        for tc in m.get("tool_calls", []) or []:
            args = tc.get("function", {}).get("arguments", "")
            total += len(args) / chars_per_token
    return int(total)
