# -*- coding: UTF-8 -*-
"""搜索结果排序与格式化 — BM25 评分 + 去重 + 统一输出格式。

提供:
    _score_results() — BM25-inspired 关键词相关性排序
    _dedup_results() — URL 去重
    _format_search_results() — 统一标准响应格式
    _has_year() / _inject_year() — 年份注入辅助
"""

import math
import re
import time
from datetime import datetime

_RECENCY_PATTERNS = [
    r"最新",
    r"今年",
    r"最近",
    r"近期",
    r"刚刚",
    r"今天",
    r"本周",
    r"本月",
    r"latest",
    r"current",
    r"recent",
    r"today",
    r"this week",
    r"this month",
    r"新闻",
    r"news",
    r"头条",
    r"热点",
    r"快讯",
    r"实时",
    r"动态",
    r"updates",
    r"breaking",
    r"trending",
    r"this year",
    r"now",
    r"new(ly)?",
    r"breaking",
    r"\b20\d\d\b",  # explicit year mention
    r"新闻",
    r"news",
    r"实时",
    r"live",
]


def _has_year(keyword: str) -> bool:
    m = re.search(r"\b(19\d\d|20\d\d)\b", keyword)
    if m:
        year = int(m.group(0))
        return year <= datetime.now().year
    return False


def _is_recency_query(keyword: str) -> bool:
    """Check if query indicates need for time-sensitive results."""
    lower = keyword.lower()
    return any(re.search(p, lower) for p in _RECENCY_PATTERNS)


def _inject_year(keyword: str) -> str:
    if _has_year(keyword):
        return keyword
    if not _is_recency_query(keyword):
        return keyword
    now = datetime.now()
    if re.search(r"[一-鿿]", keyword):
        return f"{keyword} {now.year} 最新"
    return f"{keyword} {now.year}"


def _dedup_results(results: list) -> list:
    seen = set()
    deduped = []
    for r in results:
        url = r.get("url") or r.get("href", "")
        if url and url in seen:
            continue
        seen.add(url)
        deduped.append(r)
    return deduped


def _score_results(results: list, keyword: str) -> list:
    """BM25-inspired 关键词相关性排序。

    标题匹配权重 ×3，摘要匹配权重 ×1。
    有日期的结果获得小幅加分作为 tiebreaker。
    """
    if not results or not keyword or len(results) <= 1:
        return results

    k1 = 1.2
    b = 0.75
    keywords = keyword.lower().split()
    N = len(results)

    df = {}
    for kw in keywords:
        df[kw] = sum(1 for r in results if kw in (r.get("title", "") + " " + r.get("snippet", "")).lower())

    avg_title_len = max(sum(len(r.get("title", "")) for r in results) / N, 1)
    avg_snippet_len = max(sum(len(r.get("snippet", "")) for r in results) / N, 1)

    scored = []
    for r in results:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        title_len = max(len(title), 1)
        snippet_len = max(len(snippet), 1)

        score = 0.0
        for kw in keywords:
            if df[kw] == 0:
                continue
            idf = max(0.0, math.log((N - df[kw] + 0.5) / (df[kw] + 0.5) + 1))

            tf_t = title_lower.count(kw)
            score += idf * ((tf_t * (k1 + 1)) / (tf_t + k1 * (1 - b + b * title_len / avg_title_len))) * 3.0

            tf_s = snippet_lower.count(kw)
            score += idf * ((tf_s * (k1 + 1)) / (tf_s + k1 * (1 - b + b * snippet_len / avg_snippet_len)))

        if r.get("date"):
            score += 0.5

        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc
        return netloc.removeprefix("www.") if netloc else ""
    except Exception:
        return ""


def format_search_results(
    raw_results: list,
    keyword: str,
    source: str,
    t_start: float,
    search_type: str = "web",
    total: int = 0,
) -> dict:
    """统一格式化搜索结果为标准响应格式。"""
    elapsed = int((time.time() - t_start) * 1000)

    if search_type == "image":
        results = []
        for r in raw_results:
            img_url = r.get("image") or r.get("thumbnail") or ""
            title = (r.get("title") or "").strip()[:200]
            src_url = (r.get("url") or r.get("source") or "").strip()
            if img_url and src_url:
                results.append(
                    {
                        "title": title,
                        "url": src_url,
                        "image": img_url,
                        "snippet": title,
                        "date": "",
                    }
                )
        results = results[: max(1, len(results))]
    else:
        results = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("snippet", r.get("body", "")),
                "url": r.get("url", r.get("href", "")),
                "date": r.get("date", ""),
                "domain": _extract_domain(r.get("url", r.get("href", ""))),
            }
            for r in raw_results
        ]
        results = _dedup_results(results)
        results = _score_results(results, keyword)

    if not results:
        return {
            "success": True,
            "data": {
                "query": keyword,
                "results": [],
                "hint": "未找到相关结果，请尝试更换关键词",
            },
            "meta": {
                "elapsed_ms": elapsed,
                "source": source,
                "cached": False,
                "total": total,
                "search_type": search_type,
            },
        }
    return {
        "success": True,
        "data": {"query": keyword, "results": results},
        "meta": {
            "elapsed_ms": elapsed,
            "source": source,
            "cached": False,
            "total": total,
            "search_type": search_type,
        },
    }
