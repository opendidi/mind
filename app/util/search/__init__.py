# -*- coding: UTF-8 -*-
"""搜索引擎模块 — 多引擎链 + 缓存 + 排序 + 监控

拆分自 agent_tools.py，模块化各职责。

Usage:
    from app.util.search import web_search  # re-exported for compatibility

组件:
    engines.py  — Bing / DDGS / Baidu / Exa / SearXNG 适配器
    ranking.py  — BM25 排序 + 去重 + 统一格式化
    cache.py    — Redis 查询缓存 (TTL 5min)
    monitor.py  — 成功率监控 + 告警 + 滑动窗口
"""

# Re-export for backward compatibility
from app.util.search.engine_chain import web_search
from app.util.search.monitor import get_search_alerts

__all__ = ["web_search", "get_search_alerts"]
