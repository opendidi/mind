# -*- coding: UTF-8 -*-
"""搜索缓存 — Redis 查询结果缓存与频率限制。

缓存 TTL: 5 分钟（新鲜）
Stale TTL: 30 分钟（引擎全挂时兜底）
频率限制: 每 60 秒最多 10 次搜索
"""

import json
import logging
import time

from app.util.redis_utils import get_redis

_SEARCH_CACHE_DB = 4
_SEARCH_CACHE_TTL = 300  # 5 分钟（新鲜）
_SEARCH_STALE_TTL = 1800  # 30 分钟（引擎全挂时兜底）
_SEARCH_RATE_MAX = 10
_SEARCH_RATE_WINDOW = 60


def _get_cache_redis():
    return get_redis(db=_SEARCH_CACHE_DB)


def check_search_rate(user_id: str) -> bool:
    """Redis 滑动窗口频率限制。返回 True=放行, False=限流。"""
    if not user_id:
        return True
    try:
        r = _get_cache_redis()
        key = f"search:rate:{user_id}"
        current = r.get(key)
        if current and int(current) >= _SEARCH_RATE_MAX:
            return False
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _SEARCH_RATE_WINDOW)
        pipe.execute()
        return True
    except Exception:
        logging.warning("Search rate check Redis unavailable for: %s", user_id)
        return True  # fail-open: don't block users when monitoring is down


def cache_get(keyword: str, n: int) -> dict | None:
    """从缓存获取新鲜搜索结果。返回 dict 或 None。"""
    key = f"search:{keyword.lower().strip()}:{n}"
    try:
        r = _get_cache_redis()
        data = r.get(key)
        if data:
            cached = json.loads(data)
            cached["meta"] = {
                "cached": True,
                "stale": False,
                "source": cached.get("meta", {}).get("source", "cache"),
            }
            return cached
    except Exception:
        logging.warning("Search cache get failed for: %s", keyword, exc_info=True)
    return None


def cache_get_stale(keyword: str, n: int) -> dict | None:
    """当所有引擎失败时，尝试获取过期（但尚在 stale TTL 内）的缓存兜底。

    Uses a separate Redis key with longer TTL to persist stale entries.
    Fresh cache already returned by cache_get; this is the last-resort fallback.
    """
    stale_key = f"search:stale:{keyword.lower().strip()}:{n}"
    try:
        r = _get_cache_redis()
        data = r.get(stale_key)
        if data:
            cached = json.loads(data)
            age_sec = int(time.time() - cached.get("_ts", 0))
            cached["meta"] = {
                "cached": True,
                "stale": True,
                "stale_age_sec": age_sec,
                "source": cached.get("meta", {}).get("source", "cache"),
                "hint": f"结果可能已过期（缓存于 {age_sec} 秒前），请酌情参考",
            }
            return cached
    except Exception:
        logging.debug("Stale cache get failed for: %s", keyword, exc_info=True)
    return None


def cache_set(keyword: str, n: int, result: dict):
    """缓存非空搜索结果。同时写入新鲜缓存和 stale 缓存（长 TTL 兜底）。"""
    results = result.get("data", {}).get("results", [])
    if not results:
        return
    key = f"search:{keyword.lower().strip()}:{n}"
    stale_key = f"search:stale:{keyword.lower().strip()}:{n}"
    try:
        r = _get_cache_redis()
        data = json.dumps(result, ensure_ascii=False)
        pipe = r.pipeline()
        pipe.setex(key, _SEARCH_CACHE_TTL, data)
        # Stale: attach timestamp for age calculation
        stale_payload = dict(result)
        stale_payload["_ts"] = time.time()
        pipe.setex(stale_key, _SEARCH_STALE_TTL, json.dumps(stale_payload, ensure_ascii=False))
        pipe.execute()
    except Exception:
        logging.warning("Search cache set failed for: %s", keyword, exc_info=True)
