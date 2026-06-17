# -*- coding: UTF-8 -*-
"""搜索引擎链 — 自动回退 + 工具注册入口。

根据 engine 参数构建引擎链，依次尝试直到获得结果。
注册 web_search 工具到 ToolRegistry。

特性:
  - Race 竞速: auto 模式下并行所有引擎，先到先得
  - 超时预算: 全局 8s 硬截止，慢引擎自动放弃
  - 跨引擎去重: 短时间窗内多引擎结果合并、去重、择优
  - 关键词降级: 长查询全失败时自动拆成短词重试
  - 过期缓存兜底: 引擎全挂时返回 30 分钟内旧缓存（标记 stale）
  - 领域路由: 代码→GitHub/SO, 学术→Scholar, 百科→Wikipedia
  - 搜索深度: basic 返回摘要, deep 自动抓取全文
"""

import logging
import re
import time
from concurrent.futures import FIRST_COMPLETED, TimeoutError as FutureTimeoutError
from concurrent.futures import wait as cf_wait

from app.util.agent_tools import ToolRegistry, _require
from app.util.executor import get_pool, is_pool_shutdown
from app.util.search.cache import cache_get, cache_get_stale, cache_set, check_search_rate
from app.util.search.engines import (
    _ddg_api_search,
    _exa_configured,
    _fallback_search,
    _searxng_configured,
    search_baidu,
    search_bing,
    search_bing_image,
    search_exa,
    search_searxng,
    try_ddgs_search,
)
from app.util.search.monitor import (
    check_engine_alert,
    is_engine_degraded,
    record_search_attempt,
)
from app.util.search.ranking import (
    _dedup_results,
    _inject_year,
    _score_results,
    format_search_results,
)

# ── Race-mode pool singleton ───────────────────────────────────────────
import threading as _threading

_race_pool = [None]  # list-wrapped for auto-reset on shutdown
_race_pool_lock = _threading.Lock()


def _get_race_pool():
    """Lazy-init pool with auto-reset when shut down (Celery worker lifecycle)."""
    global _race_pool
    pool = _race_pool[0]
    if pool is None or is_pool_shutdown(pool):
        with _race_pool_lock:
            pool = _race_pool[0]
            if pool is None or is_pool_shutdown(pool):
                pool = get_pool(max_workers=5, prefix="search-race-")
                _race_pool[0] = pool
    return pool


# ── Verification constants ────────────────────────────────────────────

_VALID_REGIONS = {
    "cn", "us", "jp", "kr", "uk", "de", "fr",
    "wt-wt", "us-en", "cn-zh", "jp-jp", "kr-kr",
}
_VALID_ENGINES = {"auto", "ddg", "bing", "baidu", "exa", "searxng"}
_VALID_SAFE = {"off", "moderate", "strict"}
_VALID_TIMELIMIT = {"d", "w", "m", "y"}
_VALID_SEARCH_TYPE = {"web", "news", "image"}
_VALID_SEARCH_DEPTH = {"basic", "deep"}

# Timeout budget
_SEARCH_BUDGET_MS = 8000  # 8s hard deadline
_DEDUP_WINDOW_S = 1.0  # collect race results within 1s of first success
_DEEP_FETCH_LIMIT = 3  # max URLs to deep-fetch


# ── Domain routing ───────────────────────────────────────────────────

# Domain patterns → (engine_boost, site_keywords)
_DOMAIN_ROUTES = {
    "code": (["stackoverflow.com", "github.com"], "site:stackoverflow.com OR site:github.com"),
    "academic": (["arxiv.org", "scholar.google.com"], "site:arxiv.org OR site:scholar.google.com"),
    "wiki": (["wikipedia.org"], "site:wikipedia.org"),
    "news_cn": (["news.qq.com", "news.163.com"], None),
}

_DOMAIN_PATTERNS = {
    "code": [
        r"\b(代码|编程|bug|错误|报错|函数|API|接口|import|python|javascript|golang?|rust|java|typescript|react|vue|算法|数据结构|leetcode|github|git\s|commit|pull\s*request|stackoverflow|抛出|异常|exception|syntax|error|deprecate)\b",
    ],
    "academic": [
        r"\b(论文|研究|文献|学术|arxiv|doi|期刊|引用|citation|abstract|introduction|methodology|conclusion|survey)\b",
    ],
    "wiki": [
        r"\b(百科|维基|wikipedia|定义|什么是|谁[是叫]|哪个|哪些|历史|人物|概述|简介)\b",
    ],
    "news_cn": [
        r"\b(news|headlines?|breaking|today|新闻|今日|刚刚|突发|热点事件|头条|报道|快讯|直播|发布会|通报)\b",
    ],
}


def _detect_domain(keyword: str) -> tuple[str | None, str | None]:
    """Detect search domain from keyword patterns.

    Returns (domain_tag, site_query) or (None, None) if no domain detected.
    site_query is a "site:x OR site:y" clause to narrow search scope.

    Uses dual matching: \\b-based patterns for ASCII, substring matching for CJK.
    """
    lower = keyword.lower()
    has_cjk = bool(re.search(r'[一-鿿]', keyword))

    for domain, patterns in _DOMAIN_PATTERNS.items():
        for pat in patterns:
            matched = False
            if has_cjk:
                # Strip \\b for CJK — word boundaries don't work with Chinese chars
                cjk_pat = pat.replace('\\b', '')
                matched = bool(re.search(cjk_pat, lower))
            else:
                try:
                    matched = bool(re.search(pat, lower))
                except re.error:
                    matched = bool(re.search(pat.replace('\\b', ''), lower))
            if matched:
                route = _DOMAIN_ROUTES.get(domain)
                if route:
                    return domain, route[1]
    return None, None


# ── Keyword degrade ──────────────────────────────────────────────────


def _degrade_keyword(keyword: str) -> str | None:
    """Generate a shorter keyword for retry when long query fails.

    Chinese: strip known filler prefix phrases.
    English: drop stop words, keep first 5 content words.
    Returns None if keyword can't be meaningfully shortened.
    """
    has_cjk = bool(re.search(r"[一-鿿]", keyword))
    if has_cjk:
        # Chinese: remove common filler/phrase prefixes and punctuation
        # Only remove clear filler prefix phrases (not individual chars)
        filler_prefixes = [
            "帮我搜索一下", "帮我搜索", "帮我查找一下", "帮我查找",
            "帮我搜一下", "帮我搜", "帮我查一下", "帮我查",
            "帮我找一下", "帮我找", "帮我", "搜索一下", "搜索",
            "查找一下", "查找", "查一下", "搜一下",
        ]
        cleaned = keyword
        for prefix in sorted(filler_prefixes, key=len, reverse=True):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        # Remove punctuation-only chars
        cleaned = re.sub(r'[，。！？、；：""''（）【】《》]', '', cleaned).strip()
        if not cleaned or cleaned == keyword:
            return None
        if len(cleaned) < 2:
            return None
        return cleaned
    else:
        # English: drop stop words, keep first 5 content words
        en_stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                   "have", "has", "had", "do", "does", "did", "will", "would", "could",
                   "should", "may", "might", "can", "shall", "to", "of", "in", "for",
                   "on", "with", "at", "by", "from", "as", "into", "through", "during",
                   "and", "or", "but", "not", "no", "nor", "so", "yet", "both", "either",
                   "neither", "each", "every", "all", "any", "few", "more", "most",
                   "other", "some", "such", "only", "own", "same", "than", "too", "very",
                   "just", "about", "over", "also", "then", "now", "here", "there",
                   "find", "search", "look", "what", "why", "how", "who", "when", "where",
                   "please", "help", "list", "show", "tell", "give", "get", "want", "need"}
        words = [w for w in re.split(r'\s+', keyword) if w.lower() not in en_stop]
        if not words:
            return None
        shortened = " ".join(words[:5])
        if shortened == keyword or len(shortened) < 3:
            return None
        return shortened


# ── Deep fetch ───────────────────────────────────────────────────────


def _deep_fetch_results(results: list, keyword: str) -> list:
    """For deep search mode: fetch full text for top results via web_fetch.

    Appends extracted content to each result's snippet. Limits to
    first _DEEP_FETCH_LIMIT results to avoid excessive network calls.
    """
    if not results:
        return results

    from app.util.agent_tools import run_tool_call

    enriched = []
    for i, r in enumerate(results[: _DEEP_FETCH_LIMIT]):
        url = r.get("url", "")
        if not url:
            enriched.append(r)
            continue
        try:
            fetch_result, _ = run_tool_call(
                "web_fetch", {"url": url}, {}, None, None, None, None
            )
            if fetch_result.get("success"):
                content = fetch_result.get("data", {}).get("content", "")
                if content:
                    r = dict(r)
                    r["full_text"] = content[:4000]
                    r["snippet"] = (
                        r.get("snippet", "") + f"\n\n[全文摘要]\n{content[:1000]}"
                    )
        except Exception:
            logging.debug("Deep fetch failed for: %s", url, exc_info=True)
        enriched.append(r)

    # Append remaining unfetched results
    enriched.extend(results[_DEEP_FETCH_LIMIT:])
    return enriched


# ── Core search orchestrator ─────────────────────────────────────────


def _validate_web_search(args):
    err = _require(args, "keyword")
    if err:
        return err
    if "max_results" in args and args.get("max_results") is not None:
        try:
            val = int(args["max_results"])
            if val < 1 or val > 10:
                return f"max_results 应在 1~10 之间，收到: {val}"
            args["max_results"] = val
        except (ValueError, TypeError):
            return "max_results 必须是整数"
    if "region" in args and args.get("region") is not None:
        r = str(args["region"]).strip().lower()
        if r and r not in _VALID_REGIONS:
            return f"region 无效: {r}，支持: {', '.join(sorted(_VALID_REGIONS))}"
        args["region"] = r if r else None
    if "engine" in args and args.get("engine") is not None:
        eng = str(args["engine"]).strip().lower()
        if eng not in _VALID_ENGINES:
            return f"engine 无效: {eng}，支持: {', '.join(sorted(_VALID_ENGINES))}"
        args["engine"] = eng
    else:
        args["engine"] = "auto"
    if "safe" in args and args.get("safe") is not None:
        s = str(args["safe"]).strip().lower()
        if s not in _VALID_SAFE:
            return f"safe 无效: {s}，支持: {', '.join(sorted(_VALID_SAFE))}"
        args["safe"] = s
    else:
        args["safe"] = "moderate"
    if "timelimit" in args and args.get("timelimit") is not None:
        t = str(args["timelimit"]).strip().lower()
        if t not in _VALID_TIMELIMIT:
            return f"timelimit 无效: {t}，支持: {', '.join(sorted(_VALID_TIMELIMIT))}（d=天/w=周/m=月/y=年）"
        args["timelimit"] = t
    if "search_type" in args and args.get("search_type") is not None:
        st = str(args["search_type"]).strip().lower()
        if st not in _VALID_SEARCH_TYPE:
            return (
                f"search_type 无效: {st}，支持: {', '.join(sorted(_VALID_SEARCH_TYPE))}"
            )
        args["search_type"] = st
    else:
        args["search_type"] = "web"
    if "search_depth" in args and args.get("search_depth") is not None:
        sd = str(args["search_depth"]).strip().lower()
        if sd not in _VALID_SEARCH_DEPTH:
            return f"search_depth 无效: {sd}，支持: basic, deep"
        args["search_depth"] = sd
    else:
        args["search_depth"] = "basic"
    return None


def _engine_chain(engine: str, search_type: str):
    """Generator yielding engine source tags in fallback order.

    In auto mode, degraded engines (>=80% failure rate) are skipped.
    Explicit engine selection bypasses the degradation check.
    Last-resort: if ALL engines are degraded, DDGS is still yielded as a
    desperation fallback (it requires no API key and often self-recovers).
    """
    if search_type == "image":
        yield "ddg"
        yield "bing_img"
        return
    yielded = 0
    if engine == "auto":
        if _exa_configured() and not is_engine_degraded("exa"):
            yield "exa"; yielded += 1
        if _searxng_configured() and not is_engine_degraded("searxng"):
            yield "searxng"; yielded += 1
        if not is_engine_degraded("bing"):
            yield "bing"; yielded += 1
        if not is_engine_degraded("ddg"):
            yield "ddg"; yielded += 1
        if not is_engine_degraded("baidu"):
            yield "baidu"; yielded += 1
        # Last resort: if all engines are degraded, still try DDGS (no API key needed)
        if yielded == 0:
            logging.warning("All search engines degraded — falling back to DDGS as last resort")
            yield "ddg"
            yield "ddg_html"
            yield "ddg_api"
    elif engine == "exa":
        yield "exa"
    elif engine == "searxng":
        yield "searxng"
    elif engine == "ddg":
        yield "ddg"
        yield "ddg_html"
        yield "ddg_api"
    elif engine == "bing":
        yield "bing"
    elif engine == "baidu":
        yield "baidu"


def _try_engine(src, keyword, max_results, region, safe, timelimit, search_type):
    """Run a single search engine and return (raw_results, total, error_str).

    All engine calls are wrapped here for unified race-mode dispatch.
    Checks circuit breaker before making external API calls.
    """
    from app.util.agent_circuit import circuit_allow

    if not circuit_allow(service=f"search:{src}"):
        return None, 0, f"搜索引擎 {src} 暂不可用（熔断）"
    if src == "exa":
        raw, err = search_exa(
            keyword, max_results, search_type=search_type, timelimit=timelimit
        )
        return raw, 0, err
    elif src == "searxng":
        raw, err = search_searxng(keyword, max_results, search_type=search_type)
        return raw, 0, err
    elif src == "ddg":
        raw, err = try_ddgs_search(
            keyword,
            max_results,
            region,
            safesearch=safe,
            timelimit=timelimit,
            search_type=search_type,
        )
        return raw, 0, err
    elif src == "bing":
        raw, eng_total = search_bing(
            keyword,
            max_results,
            safe=safe,
            timelimit=timelimit,
            search_type=search_type,
        )
        return raw, eng_total, ""
    elif src == "bing_img":
        raw = search_bing_image(keyword, max_results)
        return raw, 0, ""
    elif src == "baidu":
        raw, total = search_baidu(keyword, max_results)
        return raw, total, ""
    elif src == "ddg_html":
        logging.info("搜索引擎链回退 → HTML: %s", keyword)
        fb = _fallback_search(keyword, max_results)
        return (fb["data"]["results"] if fb else None), 0, ""
    elif src == "ddg_api":
        logging.info("搜索引擎链回退 → API: %s", keyword)
        fb = _ddg_api_search(keyword, max_results)
        return (fb["data"]["results"] if fb else None), 0, ""
    return None, 0, "unknown engine"


@ToolRegistry.register(
    "web_search",
    "联网搜索互联网获取最新信息。支持多引擎自动回退（Exa → SearXNG → Bing → DDG → 百度），支持 web/news/image 三种搜索类型，支持 basic/deep 两种搜索深度。"
    "Exa 使用 AI 语义搜索；SearXNG 聚合70+引擎提供JSON API；配置 EXA_API_KEY 或 SEARXNG_URL 后 auto 模式自动优先使用。"
    "系统自动注入年份确保时效性，自动识别代码/学术/百科/新闻领域并优化引擎路由。"
    "deep 模式会抓取搜索结果全文内容。当所有引擎失败时自动降级关键词重试，并使用过期缓存兜底。"
    "当需要实时数据、新闻、技术文档或图片时使用此工具。",
    {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，支持中英文。无需手动添加年份，系统会自动注入",
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量，默认 5，最大 10",
            },
            "region": {
                "type": "string",
                "description": "搜索结果区域偏好，可选: cn/us/jp/kr/uk/de/fr/wt-wt。不填则全球搜索。仅 ddg/bing 引擎支持",
            },
            "engine": {
                "type": "string",
                "enum": ["auto", "ddg", "bing", "baidu", "exa", "searxng"],
                "description": "搜索引擎。auto=自动选择最优（已配置Exa时优先→searxng→bing→ddg→baidu），exa=AI语义搜索（需EXA_API_KEY），searxng=自建聚合搜索（需SEARXNG_URL），ddg=DuckDuckGo，bing=必应，baidu=百度。默认 auto",
            },
            "safe": {
                "type": "string",
                "enum": ["off", "moderate", "strict"],
                "description": "安全搜索等级。off=不过滤，moderate=适度过滤（默认），strict=严格过滤。仅 ddg/bing 引擎支持",
            },
            "timelimit": {
                "type": "string",
                "enum": ["d", "w", "m", "y"],
                "description": "时间范围过滤。d=最近一天，w=最近一周，m=最近一月，y=最近一年。不填则不限制。仅 ddg/bing 引擎支持",
            },
            "search_type": {
                "type": "string",
                "enum": ["web", "news", "image"],
                "description": "搜索类型。web=网页搜索（默认），news=新闻搜索（时效性强），image=图片搜索（按图片URL返回）。news/image 仅 ddg 引擎完整支持",
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "deep"],
                "description": "搜索深度。basic=返回标题+摘要（默认，速度快），deep=对前3条结果自动抓取全文内容拼入摘要（速度慢，适合需要详细内容的场景）",
            },
        },
        "required": ["keyword"],
    },
    validator=_validate_web_search,
)
def web_search(args):
    """Tool function for web_search — registered with ToolRegistry.

    Optimizations:
      1. Stale cache fallback — engines all dead → stale cache (30min)
      2. Keyword degrade — long query all-fail → retry with shorter keyword
      3. Cross-engine dedup — race mode collects results within 1s, dedups
      4. Timeout budget — 8s hard deadline, slow engines abandoned
      5. Search depth — "deep" mode web_fetch-es top 3 result URLs
      6. Domain routing — code/academic/wiki/news detected, query augmented
    """
    keyword = args.get("keyword", "").strip()
    if not keyword:
        return {"success": False, "error": "请输入搜索关键词"}

    user_id = str(args.get("user_id", "") or "").strip()
    max_results = max(1, min(int(args.get("max_results", 5)), 10))
    region = args.get("region") or None
    engine = args.get("engine", "auto")
    safe = args.get("safe", "moderate")
    timelimit = args.get("timelimit") or None
    search_type = args.get("search_type", "web")
    search_depth = args.get("search_depth", "basic")

    if search_type == "image":
        engine = "ddg"
        search_depth = "basic"  # images don't support deep fetch

    if not check_search_rate(user_id):
        return {"success": False, "error": "搜索请求过于频繁，请稍后再试"}

    if search_type == "web":
        keyword = _inject_year(keyword)

    t_start = time.time()

    def elapsed():
        return int((time.time() - t_start) * 1000)

    # ── Domain routing: detect domain, augment keyword ──────────────
    domain_tag, site_query = _detect_domain(keyword)
    routed_keyword = keyword
    if site_query:
        routed_keyword = f"{keyword} {site_query}"
        logging.info("Domain routing: %s → %s", domain_tag, routed_keyword)

    # ── Cache lookup ────────────────────────────────────────────────
    cache_key = f"{keyword}:{search_type}"
    cached = cache_get(cache_key, max_results)
    if cached is not None:
        cached["meta"]["elapsed_ms"] = elapsed()
        cached["meta"]["search_type"] = search_type
        if domain_tag:
            cached["meta"]["domain"] = domain_tag
        return cached

    deadline = time.time() + _SEARCH_BUDGET_MS / 1000.0

    # ── Engine chain execution ──────────────────────────────────────
    # Try with domain-routed keyword first
    payload = _run_engine_chain(
        routed_keyword, max_results, engine, region, safe, timelimit,
        search_type, t_start, deadline, cache_key,
    )
    if payload is not None:
        if search_depth == "deep" and search_type == "web":
            results = payload.get("data", {}).get("results", [])
            if results:
                results = _deep_fetch_results(results, keyword)
                payload["data"]["results"] = results
                payload["meta"]["search_depth"] = "deep"
        if domain_tag:
            payload["meta"]["domain"] = domain_tag
        return payload

    # ── Keyword degrade retry ───────────────────────────────────────
    degraded = _degrade_keyword(keyword)
    if degraded and degraded != keyword:
        logging.info("Keyword degrade: '%s' → '%s'", keyword, degraded)
        degraded_keyword = degraded
        if site_query:
            degraded_keyword = f"{degraded} {site_query}"
        deadline2 = time.time() + (_SEARCH_BUDGET_MS / 2000.0)  # half budget
        payload = _run_engine_chain(
            degraded_keyword, max_results, engine, region, safe, timelimit,
            search_type, t_start, deadline2, cache_key,
        )
        if payload is not None:
            payload["meta"]["degraded_keyword"] = True
            payload["meta"]["original_keyword"] = keyword
            if search_depth == "deep" and search_type == "web":
                results = payload.get("data", {}).get("results", [])
                if results:
                    results = _deep_fetch_results(results, keyword)
                    payload["data"]["results"] = results
            if domain_tag:
                payload["meta"]["domain"] = domain_tag
            return payload

    # ── Stale cache fallback ────────────────────────────────────────
    stale = cache_get_stale(cache_key, max_results)
    if stale is not None:
        stale["meta"]["elapsed_ms"] = elapsed()
        stale["meta"]["search_type"] = search_type
        stale["meta"]["degraded"] = True
        logging.info("Stale cache fallback for: %s", keyword)
        return stale

    return {
        "success": False,
        "error": f"所有搜索引擎均不可用，请稍后重试",
        "meta": {
            "elapsed_ms": elapsed(),
            "source": "none",
            "search_type": search_type,
            "degraded_tried": degraded is not None,
        },
    }


# ── Engine chain runner ─────────────────────────────────────────────


def _run_engine_chain(
    keyword: str,
    max_results: int,
    engine: str,
    region: str | None,
    safe: str,
    timelimit: str | None,
    search_type: str,
    t_start: float,
    deadline: float,
    cache_key: str,
) -> dict | None:
    """Run the engine chain with timeout budget. Returns payload dict or None.

    Auto mode: parallel race with 1s dedup window.
    Explicit mode: sequential fallback.
    """
    engine_tags = list(_engine_chain(engine, search_type))
    attempted_sources: list[str] = []

    if engine == "auto" and len(engine_tags) > 1:
        return _race_mode(
            engine_tags, keyword, max_results, region, safe, timelimit,
            search_type, t_start, deadline, cache_key, attempted_sources,
        )
    else:
        return _sequential_mode(
            engine_tags, keyword, max_results, region, safe, timelimit,
            search_type, t_start, deadline, cache_key, attempted_sources,
        )


def _race_mode(
    engine_tags: list[str],
    keyword: str,
    max_results: int,
    region: str | None,
    safe: str,
    timelimit: str | None,
    search_type: str,
    t_start: float,
    deadline: float,
    cache_key: str,
    attempted_sources: list[str],
) -> dict | None:
    """Parallel race with cross-engine dedup within a 1s window.

    Instead of returning the first success immediately, collects all results
    that arrive within _DEDUP_WINDOW_S of the first response, then deduplicates
    and scores across engines for the best merged result set.
    """
    pool = _get_race_pool()
    futures: dict = {}
    for src in engine_tags:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        f = pool.submit(
            _try_engine,
            src, keyword, max_results, region, safe, timelimit, search_type,
        )
        futures[f] = src

    if not futures:
        return None

    # Phase 1: Wait for first success or all fail
    all_results: list[dict] = []  # raw result dicts from all successful engines
    best_src: str = ""
    first_hit_at: float = 0.0
    all_failed = True

    while futures:
        remaining = deadline - time.time()
        if remaining <= 0:
            for f in futures:
                f.cancel()
            futures.clear()
            break

        done, _ = cf_wait(
            futures.keys(),
            timeout=min(1.0, max(0.1, remaining)),
            return_when=FIRST_COMPLETED,
        )
        for f in done:
            src = futures.pop(f)
            attempted_sources.append(src)
            try:
                raw, eng_total, _ = f.result(timeout=0)
            except Exception:
                raw, eng_total = None, 0

            record_search_attempt(src, bool(raw))

            if raw:
                all_failed = False
                if not best_src:
                    best_src = src
                    first_hit_at = time.time()

                    # Collect this engine's formatted results immediately
                    for item in raw:
                        item["_engine"] = src
                    all_results.extend(raw)

                    # Phase 2: brief window for more engines to finish
                    grace_deadline = first_hit_at + _DEDUP_WINDOW_S
                    grace = min(grace_deadline, deadline) - time.time()
                    if grace > 0 and futures:
                        try:
                            done2, _ = cf_wait(
                                list(futures.keys()),
                                timeout=grace,
                                return_when=FIRST_COMPLETED,
                            )
                            for f2 in done2:
                                src2 = futures.pop(f2)
                                attempted_sources.append(src2)
                                try:
                                    raw2, eng2_total, _ = f2.result(timeout=0)
                                except Exception:
                                    raw2, eng2_total = None, 0

                                record_search_attempt(src2, bool(raw2))
                                if raw2:
                                    for item in raw2:
                                        item["_engine"] = src2
                                    all_results.extend(raw2)
                        except Exception:
                            pass

                    # Cancel remaining futures
                    for rem in list(futures.keys()):
                        rem.cancel()
                    futures.clear()
                break
            else:
                check_engine_alert(src)

    if all_failed or not all_results:
        return None

    # Cross-engine dedup & score
    all_results = _dedup_results(all_results)
    all_results = _score_results(all_results, keyword)

    payload = format_search_results(
        all_results[:max_results],
        keyword,
        best_src,
        t_start,
        search_type=search_type,
        total=len(all_results),
    )
    if len(attempted_sources) > 1:
        payload["meta"]["merged_sources"] = attempted_sources
    cache_set(cache_key, max_results, payload)
    return payload


def _sequential_mode(
    engine_tags: list[str],
    keyword: str,
    max_results: int,
    region: str | None,
    safe: str,
    timelimit: str | None,
    search_type: str,
    t_start: float,
    deadline: float,
    cache_key: str,
    attempted_sources: list[str],
) -> dict | None:
    """Sequential engine fallback — each engine gets budget/len(engines) seconds."""
    n = len(engine_tags)
    per_engine_budget = (_SEARCH_BUDGET_MS / 1000.0) / max(n, 1)

    for src in engine_tags:
        if time.time() > deadline:
            break
        attempted_sources.append(src)
        raw, eng_total, _ = _try_engine(
            src, keyword, max_results, region, safe, timelimit, search_type,
        )
        record_search_attempt(src, bool(raw))

        if raw:
            payload = format_search_results(
                raw, keyword, src, t_start,
                search_type=search_type, total=eng_total,
            )
            cache_set(cache_key, max_results, payload)
            return payload
        check_engine_alert(src)

    return None
