# -*- coding: UTF-8 -*-
"""Agent Tool Result Cache — read-heavy tool results cached in Redis."""

import hashlib
import json
import logging

from app.util.redis_utils import get_redis

CACHE_TTL = 30
CACHE_DB = 5

READ_TOOLS = {
    "canvas",
    "blueprint_list",
    "blueprint_search",
    "file_search",
}

WRITE_INVALIDATION_MAP = {
    "canvas": ["canvas"],
    "blueprint_save": ["blueprint_list", "blueprint_search"],
    "blueprint_load": ["canvas"],
    "layout_auto_arrange": ["canvas"],
    "layout_align": ["canvas"],
}


def _get_cache_redis():
    return get_redis(db=CACHE_DB)


def _cache_key(tool_name: str, tool_args: dict, user_id: str = "") -> str:
    args_str = json.dumps(tool_args, ensure_ascii=False, sort_keys=True)
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
    return f"agent:toolcache:{tool_name}:{args_hash}:{user_id}"


def cache_get(tool_name: str, tool_args: dict, user_id: str = "") -> dict | None:
    if tool_name not in READ_TOOLS:
        return None
    try:
        r = _get_cache_redis()
        version_key = f"agent:toolcache:v:{tool_name}"
        cached_version = r.get(version_key)
        data = r.get(_cache_key(tool_name, tool_args, user_id))
        if data:
            if cached_version:
                r.delete(_cache_key(tool_name, tool_args, user_id))
                return None
            parsed = json.loads(data)
            parsed.setdefault("meta", {})["cached"] = True
            return parsed
    except Exception:
        logging.warning("Tool cache get failed: %s", tool_name, exc_info=True)
    return None


def cache_set(tool_name: str, tool_args: dict, result: dict, user_id: str = ""):
    if tool_name not in READ_TOOLS:
        return
    if not result.get("success"):
        return
    try:
        r = _get_cache_redis()
        r.setex(_cache_key(tool_name, tool_args, user_id), CACHE_TTL, json.dumps(result, ensure_ascii=False))
    except Exception:
        logging.warning("Tool cache set failed: %s(%s)", tool_name, tool_args, exc_info=True)


def cache_invalidate(tool_name: str, tool_args: dict = None):
    targets = WRITE_INVALIDATION_MAP.get(tool_name, [])
    if not targets:
        return
    try:
        r = _get_cache_redis()
        for target in targets:
            version_key = f"agent:toolcache:v:{target}"
            r.incr(version_key)
            r.expire(version_key, CACHE_TTL * 2)
    except Exception:
        logging.warning("Cache invalidate failed: %s", tool_name, exc_info=True)
