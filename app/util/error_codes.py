# -*- coding: UTF-8 -*-
"""Structured error codes for programmatic error handling.

All API error responses should include an `error_code` field alongside
`code` (HTTP status) and `message` (human-readable). This lets frontend
and API consumers distinguish error types without parsing free-text messages.

Usage:
    from app.util.error_codes import ErrorCode
    return jsonify({
        "code": 429,
        "error_code": ErrorCode.RATE_LIMITED,
        "message": "请求过于频繁，请稍后再试",
    }), 429
"""


class ErrorCode:
    """Machine-readable error codes. Match the pattern: CATEGORY_REASON."""

    # ── Auth (AUTH_*) ─────────────────────────────────────────────
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_CAPTCHA_INVALID = "AUTH_CAPTCHA_INVALID"
    AUTH_USERNAME_TAKEN = "AUTH_USERNAME_TAKEN"
    AUTH_WEAK_PASSWORD = "AUTH_WEAK_PASSWORD"

    # ── Input validation (INPUT_*) ────────────────────────────────
    INPUT_MISSING_FIELD = "INPUT_MISSING_FIELD"
    INPUT_INVALID_FORMAT = "INPUT_INVALID_FORMAT"
    INPUT_VALUE_OUT_OF_RANGE = "INPUT_VALUE_OUT_OF_RANGE"
    INPUT_GUARD_REJECTED = "INPUT_GUARD_REJECTED"  # safety filter

    # ── Resource (RES_*) ──────────────────────────────────────────
    RES_NOT_FOUND = "RES_NOT_FOUND"
    RES_ALREADY_EXISTS = "RES_ALREADY_EXISTS"
    RES_DELETED = "RES_DELETED"

    # ── Rate / Quota (RATE_*) ─────────────────────────────────────
    RATE_LIMITED = "RATE_LIMITED"
    TOKEN_BUDGET_EXCEEDED = "TOKEN_BUDGET_EXCEEDED"

    # ── Agent (AGENT_*) ───────────────────────────────────────────
    AGENT_MODEL_UNAVAILABLE = "AGENT_MODEL_UNAVAILABLE"  # circuit open / all retries exhausted
    AGENT_TOOL_FAILED = "AGENT_TOOL_FAILED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_SUB_AGENT_FAILED = "AGENT_SUB_AGENT_FAILED"
    AGENT_PLAN_FAILED = "AGENT_PLAN_FAILED"

    # ── Internal (INTERNAL_*) ─────────────────────────────────────
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INTERNAL_DB_ERROR = "INTERNAL_DB_ERROR"
    INTERNAL_REDIS_ERROR = "INTERNAL_REDIS_ERROR"
    INTERNAL_STORAGE_ERROR = "INTERNAL_STORAGE_ERROR"


# ── HTTP status → error_code mapping for common cases ─────────────
# (used when we can infer the code from context)

_DEFAULT_MAP = {
    400: ErrorCode.INPUT_INVALID_FORMAT,
    401: ErrorCode.AUTH_TOKEN_INVALID,
    403: ErrorCode.INPUT_GUARD_REJECTED,
    404: ErrorCode.RES_NOT_FOUND,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}


def default_for_status(http_status: int) -> str:
    """Return a sensible default error_code for a given HTTP status."""
    return _DEFAULT_MAP.get(http_status, ErrorCode.INTERNAL_ERROR)
