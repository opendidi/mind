# -*- coding: UTF-8 -*-
"""搜索监控 — 引擎成功率统计 + 告警。

滑动窗口: 最近 20 次请求
告警阈值: 失败率 ≥ 80%
告警冷却: 同引擎 30 分钟内不重复
"""

import logging

from app.util.redis_utils import get_redis

_SEARCH_CACHE_DB = 4
_SEARCH_MONITOR_WINDOW = 20
_SEARCH_MONITOR_THRESHOLD = 0.8
_SEARCH_MONITOR_MIN_SAMPLES = 5
_SEARCH_MONITOR_COOLDOWN = 1800


def _get_cache_redis():
    return get_redis(db=_SEARCH_CACHE_DB)


def record_search_attempt(engine: str, success: bool):
    """记录单次引擎抓取结果到 Redis 滑动窗口。"""
    try:
        r = _get_cache_redis()
        key = f"search:monitor:{engine}"
        r.lpush(key, "1" if success else "0")
        r.ltrim(key, 0, _SEARCH_MONITOR_WINDOW - 1)
        r.expire(key, 3600)
    except Exception:
        logging.debug("Search monitor record failed for: %s", engine)


def check_engine_alert(engine: str):
    """检查引擎失败率是否超过阈值。超过则写告警 key 并记 WARNING 日志。"""
    try:
        r = _get_cache_redis()
        key = f"search:monitor:{engine}"
        samples = r.lrange(key, 0, -1)
        if len(samples) < _SEARCH_MONITOR_MIN_SAMPLES:
            return
        failures = sum(1 for s in samples if s == "0")
        rate = failures / len(samples)
        if rate >= _SEARCH_MONITOR_THRESHOLD:
            alert_key = f"search:alert:{engine}"
            if not r.exists(alert_key):
                r.setex(alert_key, _SEARCH_MONITOR_COOLDOWN, str(rate))
                logging.warning(
                    "搜索引擎告警: %s 近 %d 次抓取失败率 %.0f%%（阈值 %.0f%%），可能引擎改版导致解析失效",
                    engine,
                    len(samples),
                    rate * 100,
                    _SEARCH_MONITOR_THRESHOLD * 100,
                )
    except Exception:
        logging.debug("Search engine alert check failed for: %s", engine)


def is_engine_degraded(engine: str) -> bool:
    """Check if an engine is currently in alert state (>=80% failure rate)."""
    try:
        r = _get_cache_redis()
        return bool(r.exists(f"search:alert:{engine}"))
    except Exception:
        return False


def get_search_alerts() -> dict:
    """获取当前所有活跃的搜索引擎告警（供健康检查调用）。"""
    alerts = {}
    try:
        r = _get_cache_redis()
        for engine in ("exa", "searxng", "bing", "ddg", "baidu", "ddg_html", "ddg_api"):
            key = f"search:alert:{engine}"
            val = r.get(key)
            if val:
                alerts[engine] = {"failure_rate": float(val), "status": "degraded"}
    except Exception:
        pass
    return alerts
