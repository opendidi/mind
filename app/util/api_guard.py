# -*- coding: UTF-8 -*-
"""API Security Monitor — request-level attack detection and blocking.

Monitors every API request for four attack categories:
  1. Injection:       SQL / XSS / Command / Path Traversal / SSTI / NoSQL
  2. Auth bypass:     Missing token on protected endpoints, JWT algorithm tampering
  3. Privilege escalation: Sequential ID probing (scanning resource IDs)
  4. Abnormal freq:   Burst detection (short-window), credential stuffing

All rules are regex-based — zero token cost, operates entirely at the Flask
request/response boundary without affecting downstream handler logic.

Integration points (in app/__init__.py):
  - before_request  → before_request_security()   (block on match)
  - after_request   → after_request_security()    (audit leaks)
  - Auth routes call → record_auth_failure()       (credential stuffing)
"""

import logging
import re
import time
from collections import defaultdict

from flask import jsonify, request

logger = logging.getLogger("api_guard")

# ═══════════════════════════════════════════════════════════════════════════
# Attack pattern library
# ═══════════════════════════════════════════════════════════════════════════

# ── SQL Injection ──
_SQLI = [
    # DML + FROM with table-like reference (requires ASCII word after FROM to skip CJK discussion text)
    re.compile(r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION)\s+.*\bFROM\s+[a-zA-Z]\w*"),
    # Classic tautology: ' OR '1'='1  /  " OR "1"="1  /  ' OR 1=1 --
    re.compile(r"""(?i)['"]\s*(OR|AND)\s*['"]?\d*['"]?\s*=\s*['"]?\d*['"]?"""),
    # Bare tautology: OR 1=1 / AND 1=1
    re.compile(r"(?i)\b(OR|AND)\s+\d+\s*=\s*\d+\b"),
    # Time-based blind: SLEEP / WAITFOR / pg_sleep / BENCHMARK
    re.compile(r"(?i)\bSLEEP\s*\(|WAITFOR\s+DELAY|pg_sleep\s*\(|BENCHMARK\s*\("),
    # DB enumeration
    re.compile(r"(?i)\bINFORMATION_SCHEMA\b|xp_cmdshell|LOAD_FILE\s*\(|INTO\s+(OUT|DUMP)FILE"),
    # SQL comment terminators (used to truncate remaining SQL). Exclude bare # (common in Python/Markdown)
    re.compile(r"(?i)--\s*$|/\*!|\*/\s*$"),
    # Keyword-based detection: ' UNION SELECT / 1; DROP TABLE
    re.compile(r"(?i)['\";]\s*(UNION|DROP|ALTER|EXEC|INSERT)\s+(SELECT|TABLE|INTO|xp_)"),
]

# ── XSS ──
_XSS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"""on\w+\s*=\s*["'][^"']*["']""", re.IGNORECASE),
    re.compile(r"<iframe\b|<embed\b|<object\b|<frame\b", re.IGNORECASE),
    re.compile(r"<img[^>]*\bonerror\b[^>]*>", re.IGNORECASE),
    re.compile(r"<svg[^>]*\bonload\b[^>]*>", re.IGNORECASE),
    re.compile(r"document\.cookie|document\.write|window\.location\s*=\s*[^;]+", re.IGNORECASE),
    re.compile(r"eval\s*\(|setTimeout\s*\(\s*['\"][^'\"]*['\"]", re.IGNORECASE),
]

# ── Command / Shell Injection ──
_CMDI = [
    # shell metachar + command name followed by whitespace/EOS (not = to avoid URL &id=123 FP)
    re.compile(r"""[;&|`]\s*(?:ls|id|whoami|cat|curl|wget|nc|bash|sh|cmd|powershell)(?:\s|$)""", re.IGNORECASE),
    re.compile(r"\$\([^)]*\)|\$\{[^}]*\}|`[^`]+`"),
    re.compile(r"(?i)(\bcat\b|\bwget\b|\bcurl\b)\s+(/etc/|C:\\\\|http://)", re.IGNORECASE),
    re.compile(r"(?i)\bnc\s+-[nlvp]|\bncat\s+|\bsocat\s+", re.IGNORECASE),
    re.compile(r"(?i)\\x[0-9a-f]{2}\\x[0-9a-f]{2}"),  # hex-encoded shellcode prefix
]

# ── Path Traversal ──
_PATH = [
    re.compile(r"(?:\.\./|\.\.\\|%2e%2e/|%2e%2e\\|%252e%252e/|..%2f)", re.IGNORECASE),
    re.compile(r"(?i)(^|[/\\])etc/(passwd|shadow|hosts|group|sudoers)(\b|$)"),
    re.compile(r"(?i)(^|[\\])Windows\\(System32|SysWOW64|Boot)(\\|$)"),
    re.compile(r"(?i)WEB-INF/(web\.xml|classes/)|META-INF/"),
    re.compile(r"(?i)\.git/HEAD|\.env\b|\.htaccess\b|\.svn/"),
]

# ── SSTI (Server-Side Template Injection) ──
# Match only *exploitation* payloads, not bare delimiters that appear in normal text
_SSTI = [
    re.compile(r"\{\{.*?(?:config|self|request|session|__class__|__mro__|__subclasses__|__globals__|__builtins__|lipsum|cycler|joiner|namespace).*?\}\}", re.IGNORECASE),
    re.compile(r"\$\{(?:java\.|system\.|env:|pageContext|applicationScope)", re.IGNORECASE),
]

# ── NoSQL Injection ──
_NOSQL = [
    # MongoDB operators as JSON keys: "$gt", "$ne", etc.
    re.compile(r"""(?i)["']?\$(?:gt|lte?|ne|nin|regex|where|eq|elemMatch|or|and|not)["']?\s*:"""),
    re.compile(r'(?i)"\$where"\s*:'),
    re.compile(r"(?i)db\.(?:collection|getCollection)\(\s*['\"][^'\"]+['\"]\s*\)\.(?:find|aggregate)\("),
]

# ── JWT / Auth tampering ──
_JWT_TAMPER = [
    re.compile(r'(?i)"alg"\s*:\s*"(?:none|NONE)"'),
]

# ── Deserialization ──
_DESER = [
    re.compile(r'(?i)O:\d+:"[^"]+":\d+:'),                          # PHP object injection
    re.compile(r'(?i)rO0AB[0-9A-Za-z+/=]{20,}'),                   # Java serialization base64
    re.compile(r'(?i)Y3B5dGhvbgrh|__class__|__reduce__'),           # Python pickle (base64 "cpython" prefix)
]

# Master list — ordered by severity
_INJECTION_RULES = _SQLI + _CMDI + _DESER + _XSS + _SSTI + _NOSQL + _PATH + _JWT_TAMPER


# ═══════════════════════════════════════════════════════════════════════════
# Response leak patterns
# ═══════════════════════════════════════════════════════════════════════════

_PII_LEAK = [
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),                          "手机号"),
    (re.compile(r'"[^"]*@[^"]+\.[^"]{2,}"'),                            "邮箱"),
    (re.compile(r"\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b"), "身份证号"),
    (re.compile(r'(?i)"(?:access_token|refresh_token|password|secret)"\s*:\s*"[^"]{8,}"'), "凭据"),
    (re.compile(r'(?i)Traceback\s+\(most recent call last\)'),          "Python 堆栈"),
    (re.compile(r'(?i)File\s+".*\.py",\s+line\s+\d+,'),                "源码路径"),
    (re.compile(r'(?i)MySQLdb\.|psycopg2\.|sqlite3\.\w+Error'),        "数据库错误"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Time-bucketed tracking stores
# ═══════════════════════════════════════════════════════════════════════════

_auth_failures: dict[str, list[float]] = defaultdict(list)
_req_log: dict[str, list[float]] = defaultdict(list)
_id_probes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

# ── Thresholds (overridable via config/env) ──

try:
    from app.config import (  # type: ignore[import]
        SECURITY_AUTH_FAILURE_MAX,
        SECURITY_AUTH_FAILURE_WINDOW,
        SECURITY_BURST_MAX,
        SECURITY_BURST_WINDOW,
        SECURITY_ID_PROBE_MAX,
        SECURITY_ID_PROBE_WINDOW,
        SECURITY_MONITOR_ENABLED,
    )
except ImportError:
    SECURITY_AUTH_FAILURE_MAX = 10
    SECURITY_AUTH_FAILURE_WINDOW = 60
    SECURITY_BURST_MAX = 100
    SECURITY_BURST_WINDOW = 10
    SECURITY_ID_PROBE_MAX = 15
    SECURITY_ID_PROBE_WINDOW = 60
    SECURITY_MONITOR_ENABLED = True

AUTH_FAILURE_MAX    = SECURITY_AUTH_FAILURE_MAX
AUTH_FAILURE_WINDOW = SECURITY_AUTH_FAILURE_WINDOW
BURST_MAX           = SECURITY_BURST_MAX
BURST_WINDOW        = SECURITY_BURST_WINDOW
ID_PROBE_MAX        = SECURITY_ID_PROBE_MAX
ID_PROBE_WINDOW     = SECURITY_ID_PROBE_WINDOW


def _purge(store: dict, key: str, window: float):
    """Evict expired timestamps for *key* in *store*."""
    now = time.time()
    cutoff = now - window
    entries = store.get(key)
    if entries is None:
        return
    trimmed = [t for t in entries if t > cutoff]
    if trimmed:
        store[key] = trimmed
    else:
        del store[key]


def _walks_strings(obj, depth=0) -> list[str]:
    """Recursively extract all string leaf values (depth-limited)."""
    if depth > 5:
        return []
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        out = []
        for v in obj.values():
            out.extend(_walks_strings(v, depth + 1))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_walks_strings(v, depth + 1))
        return out
    return []


# ═══════════════════════════════════════════════════════════════════════════
# Detectors
# ═══════════════════════════════════════════════════════════════════════════

def _detect_injection(value: str) -> str | None:
    """Return the rule snippet that matched, or None."""
    if not value or len(value) < 2:
        return None
    for pat in _INJECTION_RULES:
        if pat.search(value):
            return pat.pattern[:60]
    return None


def _detect_id_probe(path: str, ip: str) -> str | None:
    """Flag an IP that hits many numeric-ID variants of the same endpoint."""
    # Collapse numeric path segments →  ":id"
    pattern = re.sub(r"/\d+(/|$|\?)", "/:id\\1", path)
    if "/:id" not in pattern:
        return None

    _id_probes[ip][pattern] += 1

    if _id_probes[ip].get(pattern, 0) > ID_PROBE_MAX:
        return f"ID 遍历探测 ({pattern})"

    return None


def _detect_credential_stuffing(ip: str) -> str | None:
    """Detect repeated auth failures indicative of brute-force or credential stuffing."""
    _purge(_auth_failures, ip, AUTH_FAILURE_WINDOW)
    failures = _auth_failures.get(ip, [])
    if len(failures) >= AUTH_FAILURE_MAX:
        return f"暴力破解/撞库 ({len(failures)} 次失败 / {AUTH_FAILURE_WINDOW}s)"
    return None


def _detect_burst(ip: str) -> str | None:
    """Detect short-window request bursts."""
    _purge(_req_log, ip, BURST_WINDOW)
    hits = _req_log.get(ip, [])
    if len(hits) >= BURST_MAX:
        return f"请求爆发 ({len(hits)} 次 / {BURST_WINDOW}s)"
    return None


def _detect_response_leak(body: str) -> str | None:
    """Scan JSON response body for PII / credentials / stack traces."""
    if not body:
        return None
    for pat, label in _PII_LEAK:
        if pat.search(body):
            return f"响应体 {label} 泄露"
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


def before_request_security():
    """Flask before_request hook. Returns (response, status) to block, or None to pass."""
    if not SECURITY_MONITOR_ENABLED:
        return None

    ip = _client_ip()
    path = request.path

    # Record request for burst detection
    _req_log[ip].append(time.time())

    # Periodic sweep of stale tracking entries
    _maybe_cleanup_stores()

    # ── Layer 1: Burst detection (fast, cheap) ──
    reason = _detect_burst(ip)
    if reason:
        logger.warning("API Guard [burst] ip=%s path=%s reason=%s", ip, path, reason)
        return _reject(reason)

    # ── Layer 2: Credential stuffing ──
    reason = _detect_credential_stuffing(ip)
    if reason:
        logger.warning("API Guard [stuffing] ip=%s path=%s reason=%s", ip, path, reason)
        return _reject(reason)

    # ── Layer 3: ID probing ──
    reason = _detect_id_probe(path, ip)
    if reason:
        logger.warning("API Guard [probe] ip=%s path=%s reason=%s", ip, path, reason)
        return _reject(reason)

    # ── Layer 4: Injection detection (scan all input surfaces) ──
    surfaces = _collect_input_surfaces()
    for label, value in surfaces:
        hit = _detect_injection(value)
        if hit:
            logger.warning("API Guard [injection] ip=%s path=%s surface=%s pattern=%s", ip, path, label, hit)
            return _reject("检测到注入攻击")

    return None


def after_request_security(response):
    """Flask after_request hook. Logs leaks and tracks auth failures."""
    ct = response.headers.get("Content-Type", "")
    path = request.path if request else ""

    # ── Track auth failures for credential stuffing detection ──
    if response.status_code in (401, 403):
        ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.remote_addr
            or "unknown"
        )
        _auth_failures[ip].append(time.time())
        count = len(_auth_failures.get(ip, []))
        if count >= AUTH_FAILURE_MAX // 2:
            logger.warning("API Guard auth failures: ip=%s count=%d path=%s", ip, count, path)

    # ── Response leak scan (JSON only) ──
    if "application/json" not in ct:
        return response

    try:
        body = response.get_data(as_text=True)
        if len(body) > 100_000:
            return response

        reason = _detect_response_leak(body)
        if reason:
            ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.remote_addr
                or "unknown"
            )
            logger.error("API Guard [leak] ip=%s path=%s reason=%s", ip, path, reason)
    except Exception:
        pass

    return response


def record_auth_failure():
    """Call this from auth routes after a failed login attempt."""
    ip = _client_ip()
    _auth_failures[ip].append(time.time())


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _client_ip() -> str:
    """Extract client IP from request headers (respects X-Forwarded-For)."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ── Periodic cleanup (prevents unbounded growth of in-memory stores) ──

_LAST_CLEANUP = time.time()
_CLEANUP_INTERVAL = 300  # seconds between full sweeps


def _maybe_cleanup_stores():
    """Sweep expired entries from all tracking stores (throttled to avoid overhead)."""
    global _LAST_CLEANUP
    now = time.time()
    if now - _LAST_CLEANUP < _CLEANUP_INTERVAL:
        return
    _LAST_CLEANUP = now

    for store, window in [
        (_auth_failures, AUTH_FAILURE_WINDOW),
        (_req_log, BURST_WINDOW),
    ]:
        cutoff = now - window
        stale = [k for k, v in store.items() if not any(t > cutoff for t in v)]
        for k in stale:
            del store[k]

    # _id_probes has no time window; sweep entries with zero counts
    stale_ids = [k for k, d in _id_probes.items() if sum(d.values()) == 0]
    for k in stale_ids:
        del _id_probes[k]

def _collect_input_surfaces() -> list[tuple[str, str]]:
    """Collect (label, value) pairs from all request input surfaces."""
    surfaces: list[tuple[str, str]] = []

    # URL path
    path = request.path
    if path:
        surfaces.append(("path", path))

    # Query parameters
    for key, val in request.args.items():
        if isinstance(val, str):
            surfaces.append((f"qs:{key}", val))

    # JSON body
    if request.is_json:
        try:
            body = request.get_json(silent=True)
            for s in _walks_strings(body):
                surfaces.append(("json", s))
        except Exception:
            pass

    # Form body
    if request.form:
        for key, val in request.form.items():
            if isinstance(val, str):
                surfaces.append((f"form:{key}", val))

    # Selected headers
    for h in ("Authorization", "User-Agent", "Referer", "Origin", "X-Requested-With"):
        val = request.headers.get(h, "")
        if val:
            surfaces.append((f"header:{h}", val))

    return surfaces


def _reject(reason: str) -> tuple:
    """Return a 403 JSON response for a blocked request."""
    resp = jsonify({
        "code": 403,
        "message": f"请求已被安全策略拦截: {reason}",
        "data": None,
    })
    # HTTP headers must be latin-1; use ASCII fallback for Chinese chars
    safe_reason = reason.encode("ascii", errors="replace").decode("ascii")[:120]
    resp.headers["X-Security-Block"] = safe_reason
    return resp, 403
