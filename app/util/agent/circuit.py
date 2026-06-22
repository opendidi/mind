# -*- coding: UTF-8 -*-
"""API circuit breaker — per-service isolation via Redis shared state.
Uses Redis INCR + EXPIRE with in-memory fallback when Redis is unavailable."""

import logging
import time
from collections import defaultdict

from app.util.redis_utils import get_redis

_CIRCUIT_FAIL_THRESHOLD = 5
_CIRCUIT_COOLDOWN_SECS = 30
_CIRCUIT_REDIS_DB = 6

_REDIS_KEY_PREFIX = "circuit"

_mem_failures: dict[str, float] = {}
_mem_fail_count: dict[str, int] = defaultdict(int)


def _circuit_redis():
    return get_redis(db=_CIRCUIT_REDIS_DB)


def _fail_key(service: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{service}:failures"


def _open_key(service: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{service}:opened_at"


def _mem_check(service: str) -> bool:
    count = _mem_fail_count.get(service, 0)
    if count >= _CIRCUIT_FAIL_THRESHOLD:
        opened = _mem_failures.get(service, 0)
        if opened and (time.time() - opened) < _CIRCUIT_COOLDOWN_SECS:
            return False
        _mem_fail_count[service] = 0
        _mem_failures.pop(service, None)
    return True


def _mem_record(success: bool, service: str):
    if success:
        _mem_fail_count[service] = 0
        _mem_failures.pop(service, None)
    else:
        _mem_fail_count[service] += 1
        if _mem_fail_count[service] >= _CIRCUIT_FAIL_THRESHOLD:
            _mem_failures[service] = time.time()
            logging.warning("Circuit OPEN (memory) [%s]: %d consecutive failures", service, _mem_fail_count[service])


def circuit_allow(service: str = "default") -> bool:
    try:
        r = _circuit_redis()
        failures = r.get(_fail_key(service))
        if failures and int(failures) >= _CIRCUIT_FAIL_THRESHOLD:
            opened_at = r.get(_open_key(service))
            if opened_at:
                elapsed = time.time() - float(opened_at)
                if elapsed < _CIRCUIT_COOLDOWN_SECS:
                    return False
                r.delete(_fail_key(service), _open_key(service))
        return True
    except Exception:
        logging.warning("Circuit Redis unavailable [%s], using in-memory fallback", service)
        return _mem_check(service)


def circuit_record(success: bool, status_code: int = 0, service: str = "default"):
    if status_code == 429:
        return
    _mem_record(success, service)
    try:
        r = _circuit_redis()
        if success:
            r.delete(_fail_key(service), _open_key(service))
        else:
            count = r.incr(_fail_key(service))
            r.expire(_fail_key(service), _CIRCUIT_COOLDOWN_SECS * 2)
            if count >= _CIRCUIT_FAIL_THRESHOLD:
                r.setex(_open_key(service), _CIRCUIT_COOLDOWN_SECS, str(time.time()))
                logging.warning(
                    "Circuit OPEN [%s]: %d consecutive failures, cooldown %ds", service, count, _CIRCUIT_COOLDOWN_SECS
                )
    except Exception:
        logging.warning("Circuit record Redis failed [%s], memory state updated", service)
