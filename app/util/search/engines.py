# -*- coding: UTF-8 -*-
"""搜索引擎适配器 — Bing / DDGS / Baidu / Exa / SearXNG 具体实现。

每个引擎封装为独立函数，统一返回 (results_or_None, metadata)。
"""

import json
import logging
import os
import re
import threading
import time

import requests
from ddgs import DDGS

from app.util.executor import ExecutorTimeout, ManagedPool

# ── 共享资源 ─────────────────────────────────────────────────────────

_ddgs_inst = None
_ddgs_lock = threading.Lock()
_search_executor = ManagedPool(max_workers=2, prefix="search-")


def _get_ddgs():
    global _ddgs_inst
    if _ddgs_inst is None:
        with _ddgs_lock:
            if _ddgs_inst is None:
                _ddgs_inst = DDGS()
    return _ddgs_inst



# ── 超时配置 ─────────────────────────────────────────────────────────

_SEARCH_DDGS_TIMEOUT = 8
_SEARCH_FALLBACK_TIMEOUT = 8
_SEARCH_DDGAPI_TIMEOUT = 6


# ── DuckDuckGo (DDGS) ─────────────────────────────────────────────────


def _ddgs_search(
    keyword,
    max_results,
    region=None,
    safesearch="moderate",
    timelimit=None,
    search_type="web",
):
    ddgs = _get_ddgs()
    kwargs = {"max_results": max_results, "region": region, "safesearch": safesearch}
    if timelimit:
        kwargs["timelimit"] = timelimit
    if search_type == "news":
        return list(ddgs.news(keyword, **kwargs))
    elif search_type == "image":
        kwargs.pop("safesearch", None)
        kwargs.pop("timelimit", None)
        return list(ddgs.images(keyword, max_results=max_results, region=region))
    else:
        return list(ddgs.text(keyword, **kwargs))


def try_ddgs_search(
    keyword,
    max_results,
    region,
    safesearch="moderate",
    timelimit=None,
    search_type="web",
) -> tuple:
    """DDGS with 2 retries + exponential backoff. Returns (results_or_None, error_str)."""
    last_err = ""
    executor = _search_executor.get()
    for attempt in range(2):
        try:
            future = executor.submit(
                _ddgs_search,
                keyword,
                max_results,
                region,
                safesearch,
                timelimit,
                search_type,
            )
            raw = future.result(timeout=_SEARCH_DDGS_TIMEOUT)
            return raw, ""
        except ExecutorTimeout:
            last_err = "搜索超时"
            logging.warning("DDGS 超时 (attempt %d/2): %s", attempt + 1, keyword)
        except Exception as e:
            last_err = str(e)[:80]
            logging.warning("DDGS 失败 (attempt %d/2): %s", attempt + 1, e)
        if attempt < 1:
            time.sleep(0.8 * (2**attempt))
    return None, last_err


# ── DuckDuckGo HTML Fallback ──────────────────────────────────────────


def _fallback_search(keyword, max_results) -> dict | None:
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(
            url,
            data={"q": keyword},
            timeout=_SEARCH_FALLBACK_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        resp.raise_for_status()
        html = resp.text
        results = []

        pattern_a = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        for m in pattern_a.finditer(html):
            r_url = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            if r_url and title:
                results.append({"title": title, "snippet": snippet, "url": r_url})
            if len(results) >= max_results:
                break

        if not results:
            pattern_b = re.compile(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</a>',
                re.DOTALL | re.IGNORECASE,
            )
            for m in pattern_b.finditer(html):
                r_url = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if r_url and title and "duckduckgo" not in r_url:
                    results.append({"title": title, "snippet": "", "url": r_url})
                if len(results) >= max_results:
                    break

        if not results:
            return None
        return {"success": True, "data": {"query": keyword, "results": results}}
    except Exception as e:
        logging.warning("DDG HTML fallback 失败: %s", e)
        return None


# ── DuckDuckGo Instant Answer API ─────────────────────────────────────


def _ddg_api_search(keyword, max_results) -> dict | None:
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": keyword, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=_SEARCH_DDGAPI_TIMEOUT,
            headers={"User-Agent": "mind-agent/2.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = []

        abstract = data.get("AbstractText", "").strip()
        abstract_url = data.get("AbstractURL", "").strip()
        if abstract and abstract_url:
            results.append(
                {
                    "title": data.get("AbstractSource", "")
                    or data.get("Heading", keyword),
                    "snippet": abstract[:600],
                    "url": abstract_url,
                    "date": "",
                }
            )

        for topic in data.get("RelatedTopics", []) or []:
            text = (topic.get("Text", "") or "").strip()
            url = (topic.get("FirstURL", "") or "").strip()
            if text and url:
                title = re.sub(r"\s*-.*$", "", text)[:200]
                snippet = re.sub(r"<[^>]+>", "", text)[:600]
                results.append(
                    {"title": title, "snippet": snippet, "url": url, "date": ""}
                )
            if len(results) >= max_results:
                break

        if not results:
            return None
        return {
            "success": True,
            "data": {"query": keyword, "results": results[:max_results]},
        }
    except Exception as e:
        logging.warning("DDG API fallback 失败: %s", e)
        return None


# ── Bing ──────────────────────────────────────────────────────────────


def _extract_bing_date(block: str) -> str:
    patterns = [
        r'<span[^>]*class="[^"]*news_dt[^"]*"[^>]*>(.*?)</span>',
        r"<span[^>]*>(?:(\d{1,2})\s*(?:小时|小时前|hours?\s*ago))</span>",
        r"<span[^>]*>(\d{1,2}\s*(?:天|days?)\s*(?:前|ago))</span>",
        r"<span[^>]*>(\d{4}-\d{2}-\d{2})</span>",
        r"<span[^>]*>(\d{1,2}/\d{1,2}/\d{4})</span>",
    ]
    for pat in patterns:
        m = re.search(pat, block, re.IGNORECASE)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def _extract_bing_total(html: str) -> int:
    m = re.search(
        r'<span[^>]*class="[^"]*sb_count[^"]*"[^>]*>([\d,]+)\s*(?:条|个)?\s*(?:结果|Results)',
        html,
        re.IGNORECASE,
    )
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return 0


def search_bing(
    keyword, max_results, safe="moderate", timelimit=None, search_type="web"
) -> tuple:
    try:
        url = (
            "https://www.bing.com/news/search"
            if search_type == "news"
            else "https://www.bing.com/search"
        )
        params = {"q": keyword, "count": max_results, "mkt": "zh-CN", "setLang": "zh-Hans"}
        if safe == "strict":
            params["adlt"] = "strict"
        if timelimit and search_type != "news":
            params["tbs"] = f"qdr:{timelimit}"

        resp = requests.get(
            url,
            params=params,
            timeout=8,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        resp.raise_for_status()
        html = resp.text
        total = _extract_bing_total(html)
        results = []

        # ── BS4 structured parse (primary) ──
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            for algo in soup.select("li.b_algo"):
                a_tag = algo.select_one("h2 a") or algo.select_one("a")
                if not a_tag or not a_tag.get("href"):
                    continue
                r_url = a_tag["href"]
                if "bing.com" in r_url:
                    continue
                title = a_tag.get_text(strip=True)[:200]
                if not title:
                    continue

                snippet = ""
                p_tag = algo.select_one(".b_caption p") or algo.select_one("p")
                if p_tag:
                    snippet = p_tag.get_text(strip=True)[:600]

                date = ""
                date_span = algo.select_one(".news_dt")
                if date_span:
                    date = date_span.get_text(strip=True)

                results.append(
                    {"title": title, "snippet": snippet, "url": r_url, "date": date}
                )
                if len(results) >= max_results:
                    break
        except ImportError:
            pass

        # ── Regex fallback (used when bs4 is unavailable) ──
        if not results:
            blocks = re.findall(
                r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>',
                html,
                re.DOTALL | re.IGNORECASE,
            )
            for block in blocks:
                # Bing HTML structure: each b_algo has multiple <a> tags.
                # The first one (in <h2>) has "domain + URL" as visible text.
                # The second one (often after the caption <div>) has the real title.
                # We extract ALL <a> texts and pick the best one as title.
                all_links = re.findall(
                    r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                    block, re.DOTALL | re.IGNORECASE,
                )
                if not all_links:
                    continue

                # Decode Bing tracking URL to get real URL
                real_url = ""
                for href, _link_text in all_links:
                    if "bing.com/ck/a" in href or "bing.com/ck/r" in href:
                        # Try to extract u= parameter (base64-encoded real URL)
                        u_m = re.search(r'[&?]u=(a1[^&]+)', href)
                        if u_m:
                            try:
                                import base64
                                decoded = base64.urlsafe_b64decode(
                                    u_m.group(1) + "=="
                                ).decode("utf-8", errors="replace")
                                real_url = decoded
                                break
                            except Exception:
                                pass
                if not real_url:
                    # Use first non-Bing href as the URL
                    for href, _link_text in all_links:
                        if "bing.com" not in href:
                            real_url = href
                            break
                if not real_url:
                    continue

                # Pick the best title: strip tags, find the longest text that is
                # NOT dominated by a URL/domain pattern.
                candidates = []
                for _href, raw_text in all_links:
                    text = re.sub(r"<[^>]+>", "", raw_text).strip()
                    if not text:
                        continue
                    # Skip texts that are mostly a domain + URL concatenation
                    url_like_ratio = len(re.findall(r'https?://|\.(com|org|net|cn|hk|tw)\b', text))
                    if url_like_ratio >= 1 and len(text) < 60:
                        continue
                    # Strip leading domain prefix (e.g. "wikipedia.org › ...")
                    cleaned = re.sub(
                        r'^[\w.-]+\.(com|org|net|cn|hk|tw|jp|kr|io|ai|dev)\s*[›»]\s*',
                        '', text,
                    ).strip()
                    if cleaned and len(cleaned) > 5:
                        candidates.append(cleaned)

                title = ""
                if candidates:
                    # Prefer the longest candidate (most likely the real title)
                    title = max(candidates, key=len)
                if not title:
                    continue

                # Snippet
                snippet = ""
                snippet_m = re.search(
                    r"<p[^>]*>(.*?)</p>", block, re.DOTALL | re.IGNORECASE,
                )
                if snippet_m:
                    snippet = re.sub(r"<[^>]+>", "", snippet_m.group(1)).strip()
                if not snippet:
                    meta_m = re.search(
                        r'<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>(.*?)</div>',
                        block, re.DOTALL | re.IGNORECASE,
                    )
                    if meta_m:
                        snippet = re.sub(r"<[^>]+>", "", meta_m.group(1)).strip()
                date = _extract_bing_date(block)
                results.append({
                    "title": title[:200],
                    "snippet": snippet[:600],
                    "url": real_url,
                    "date": date,
                })
                if len(results) >= max_results:
                    break

        return (results if results else None), total
    except Exception as e:
        logging.warning("Bing 抓取失败: %s", e)
        return None, 0


# ── Bing Image Search ──────────────────────────────────────────────────


def search_bing_image(keyword: str, max_results: int) -> list | None:
    """Scrape Bing image search results. Returns list of image result dicts or None."""
    try:
        resp = requests.get(
            "https://www.bing.com/images/search",
            params={"q": keyword, "count": max_results},
            timeout=8,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        resp.raise_for_status()
        html = resp.text
        results = []

        # BS4 structured parse (primary)
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            for img_link in soup.select("a.iusc"):
                m = img_link.get("m")
                if not m:
                    continue
                try:
                    meta = json.loads(m)
                    img_url = meta.get("murl") or meta.get("turl", "")
                    src_url = meta.get("purl") or meta.get("surl", "")
                    title = (meta.get("desc") or meta.get("t", "")).strip()[:200]
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
                    if len(results) >= max_results:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
        except ImportError:
            pass

        # Regex fallback
        if not results:
            img_pattern = re.compile(
                r'<a[^>]*class="[^"]*iusc[^"]*"[^>]*m="([^"]*)"[^>]*>',
                re.DOTALL | re.IGNORECASE,
            )
            for m in img_pattern.finditer(html):
                try:
                    meta = json.loads(m.group(1).replace("&quot;", '"'))
                    img_url = meta.get("murl") or meta.get("turl", "")
                    src_url = meta.get("purl") or meta.get("surl", "")
                    title = (meta.get("desc") or meta.get("t", "")).strip()[:200]
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
                    if len(results) >= max_results:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return results if results else None
    except Exception as e:
        logging.warning("Bing 图片搜索失败: %s", e)
        return None


# ── Baidu ─────────────────────────────────────────────────────────────
#
# Two-tier: 1) Mobile (m.baidu.com) — simpler DOM, fewer anti-bot measures
#            2) PC (www.baidu.com)  — fallback with full BS4 + regex


def _decode_baidu_url(encrypted_url: str) -> str:
    """Resolve Baidu's /link?url=... redirect to real URL.

    Baidu wraps external links through its own redirect server.
    Extracts the real URL from the `url` query parameter and URL-decodes it.
    Handles three forms:
      - Direct external URL (return as-is)
      - Full redirect: https://www.baidu.com/link?url=ENC%3A%2F%2F...
      - Relative redirect: /link?url=ENC%3A%2F%2F...&wd=...
    """
    if not encrypted_url:
        return ""
    encrypted_url = encrypted_url.strip()
    # Already a direct external URL (not a redirect)
    if encrypted_url.startswith(("http://", "https://")) and "baidu.com" not in encrypted_url:
        return encrypted_url

    import urllib.parse

    # Try to extract `url=` param from the query string regardless of hostname
    m = re.search(r'[?&]url=([^&]+)', encrypted_url)
    if m:
        return urllib.parse.unquote(m.group(1))

    # Also try urlparse (handles full URLs with baidu.com hostname)
    parsed = urllib.parse.urlparse(encrypted_url)
    if parsed.query:
        qs = urllib.parse.parse_qs(parsed.query)
        real = qs.get("url", [None])[0]
        if real:
            return urllib.parse.unquote(real)

    return encrypted_url  # give up, return as-is


def _extract_baidu_date(block: str) -> str:
    m = re.search(
        r"(?:(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})|(\d{1,2}\s*(?:小时|天|分钟)\s*(?:前)))",
        block,
    )
    if m:
        return (m.group(1) or m.group(2)).strip()
    return ""


_BAIDU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def _search_baidu_mobile(keyword: str, max_results: int) -> tuple:
    """Crawl Baidu mobile search (m.baidu.com) — simpler DOM, harder to block."""
    import urllib.parse

    url = f"https://m.baidu.com/s?word={urllib.parse.quote(keyword)}&pn=0&rn={max_results}"
    resp = requests.get(url, timeout=10, headers=_BAIDU_HEADERS)
    resp.raise_for_status()
    html = resp.text

    results: list[dict] = []

    # Baidu mobile wraps each result inside a <div class="result">
    # Each result has: <a class="c-title">, <div class="c-summary">, <span class="c-color-gray">
    # URL is inside a <a> that has data-url attribute (or a /link?... redirect)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        for container in soup.select("div.result, div[class*=result]"):
            # ── URL ──
            r_url = ""
            # Prefer data-url on any <a> inside result
            for a in container.select("a[data-url]"):
                raw = a.get("data-url", "")
                if raw:
                    r_url = _decode_baidu_url(raw)
                    break
            if not r_url:
                # Fallback to first external-looking <a>
                for a in container.select("a[href]"):
                    href = a.get("href", "")
                    r_url = _decode_baidu_url(href)
                    if r_url.startswith("http") and "baidu.com" not in r_url:
                        break
                    r_url = ""
            if not r_url:
                continue

            # ── Title ──
            title_tag = (
                container.select_one("a.c-title, a[class*=title], h3, .c-title-text")
                or container.select_one("a")
            )
            title = title_tag.get_text(strip=True)[:200] if title_tag else ""
            if not title:
                continue

            # ── Snippet ──
            snippet = ""
            snip_tag = container.select_one(
                "div.c-summary, div[class*=summary], div.c-abstract, "
                "span.c-abstract, div[class*=abstract], p[class*=content]"
            )
            if snip_tag:
                snippet = snip_tag.get_text(strip=True)[:600]

            # ── Date ──
            date = ""
            date_tag = container.select_one(
                "span.c-color-gray, span[class*=time], span[class*=date]"
            )
            if date_tag:
                date = date_tag.get_text(strip=True)

            results.append({
                "title": title,
                "snippet": snippet,
                "url": r_url,
                "date": date,
            })
            if len(results) >= max_results:
                break
    except ImportError:
        pass

    return (results if results else None), 0


def _search_baidu_pc(keyword: str, max_results: int) -> tuple:
    """Crawl Baidu PC search — full BS4 + regex pipeline, more aggressive parsing."""
    resp = requests.get(
        "https://www.baidu.com/s",
        params={"wd": keyword, "rn": max_results, "tn": "baiduwb"},
        timeout=10,
        headers={
            **_BAIDU_HEADERS,
            "Referer": "https://www.baidu.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    )
    resp.raise_for_status()
    html = resp.text

    total = 0
    total_m = re.search(r"(?:找到|约|百度为您找到)\s*([\d,]+)\s*(?:个|条|篇)", html)
    if total_m:
        try:
            total = int(total_m.group(1).replace(",", ""))
        except ValueError:
            pass

    results: list[dict] = []

    # ── BS4 structured parse ──
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        # Baidu PC uses various container classes over time
        selectors = [
            "div.c-container",
            "div.result",
            "div[class*=result]:not([class*=header])",
        ]
        for selector in selectors:
            for container in soup.select(selector):
                # URL — try data-mu first (real URL), then href
                r_url = container.get("data-mu", "") or container.get("mu", "")
                if r_url:
                    r_url = _decode_baidu_url(r_url)
                if not r_url:
                    a_tag = container.select_one("h3 a") or container.select_one("a")
                    if a_tag:
                        r_url = _decode_baidu_url(a_tag.get("href", ""))
                if not r_url or "baidu.com" in r_url:
                    continue

                # Title
                title_tag = container.select_one("h3 a, a[class*=title], h3")
                if not title_tag:
                    title_tag = container.select_one("a")
                title = title_tag.get_text(strip=True)[:200] if title_tag else ""
                if not title:
                    continue

                # Snippet — try known classes first, then longest text span
                snippet = ""
                for cls in [
                    "span.c-abstract", "div.c-abstract",
                    "span.c-span-last", "div.c-span-last",
                    "span.content-right_8Zs38", "div.content-right_8Zs38",
                    "span[class*=abstract]", "div[class*=summary]",
                ]:
                    snip_tag = container.select_one(cls)
                    if snip_tag:
                        snippet = snip_tag.get_text(strip=True)[:600]
                        if snippet:
                            break
                if not snippet:
                    # Heuristic: longest text span/div over 30 chars
                    for el in container.select("span, div"):
                        text = el.get_text(strip=True)
                        if len(text) > 30 and len(text) > len(snippet):
                            snippet = text[:600]

                # Date
                date = ""
                date_tag = container.select_one(
                    "span.c-color-gray2, span.c-color-gray, "
                    "span[class*=time], span[class*=date]"
                )
                if date_tag:
                    date = date_tag.get_text(strip=True)
                else:
                    date = _extract_baidu_date(str(container))

                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": r_url,
                    "date": date,
                })
                if len(results) >= max_results:
                    break
            if results:
                break
    except ImportError:
        pass

    # ── Regex fallback ──
    if not results:
        blocks = re.findall(
            r'<div[^>]*class="[^"]*(?:result|c-container)[^"]*"[^>]*>(.*?)'
            r'</div>\s*(?=<div[^>]*class="[^"]*(?:result|c-container)|$)',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if not blocks:
            blocks = re.findall(
                r'<div[^>]*class="[^"]*c-container[^"]*"[^>]*>(.*?)'
                r'(?=<div[^>]*class="[^"]*c-container[^"]*"|$)',
                html,
                re.DOTALL | re.IGNORECASE,
            )

        for block in blocks:
            href_m = re.search(
                r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                block, re.DOTALL | re.IGNORECASE,
            )
            if not href_m:
                continue
            raw_url = href_m.group(1)
            r_url = _decode_baidu_url(raw_url)
            title = re.sub(r"<[^>]+>", "", href_m.group(2)).strip()
            if not r_url or "baidu.com" in r_url or not title:
                continue

            snippet = ""
            for cls in [
                r"c-abstract", r'content-right_[^"]*', r"c-span-last",
                r'c-summary', r'abstract',
            ]:
                snip_m = re.search(
                    rf'<(?:span|div)[^>]*class="[^"]*{cls}[^"]*"[^>]*>(.*?)</(?:span|div)>',
                    block, re.DOTALL | re.IGNORECASE,
                )
                if snip_m:
                    snippet = re.sub(r"<[^>]+>", "", snip_m.group(1)).strip()
                    if snippet:
                        break
            if not snippet:
                spans = re.findall(
                    r"<(?:span|div)[^>]*>(.*?)</(?:span|div)>",
                    block, re.DOTALL | re.IGNORECASE,
                )
                for s in spans:
                    clean = re.sub(r"<[^>]+>", "", s).strip()
                    if len(clean) > 30:
                        snippet = clean[:600]
                        break
            date = _extract_baidu_date(block)
            results.append({
                "title": title[:200],
                "snippet": snippet[:600],
                "url": r_url,
                "date": date,
            })
            if len(results) >= max_results:
                break

    return (results if results else None), total


def search_baidu(keyword, max_results) -> tuple:
    """Baidu search: mobile-first, PC fallback.

    Mobile (m.baidu.com) is simpler HTML, less aggressively anti-bot.
    Falls back to PC (www.baidu.com) if mobile returns no results.
    """
    try:
        results, _ = _search_baidu_mobile(keyword, max_results)
        if results:
            logging.info("Baidu mobile: %d results for '%s'", len(results), keyword)
            return results, 0
        logging.info("Baidu mobile returned empty, trying PC fallback for '%s'", keyword)
    except Exception as e:
        logging.debug("Baidu mobile failed, trying PC fallback: %s", e)

    try:
        return _search_baidu_pc(keyword, max_results)
    except Exception as e:
        logging.warning("Baidu 抓取失败: %s (mobile+PC both failed)", e)
        return None, 0


# ── Exa ───────────────────────────────────────────────────────────────


def _exa_configured() -> bool:
    return bool(os.environ.get("EXA_API_KEY", "").strip())


def search_exa(keyword, max_results, search_type="web", timelimit=None) -> tuple:
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        return None, "EXA_API_KEY 未配置"

    try:
        body = {
            "query": keyword,
            "numResults": max_results,
            "useAutoprompt": True,
            "includeHighlights": True,
            "highlights": {"numSentences": 3, "highlightsPerUrl": 2, "query": keyword},
        }
        if search_type == "news":
            body["category"] = "news"
        elif search_type == "image":
            return None, "Exa 不支持图片搜索，请使用 engine=ddg 搜索图片"
        if timelimit:
            age_map = {"d": 24, "w": 168, "m": 720, "y": 8760}
            body["maxAgeHours"] = age_map.get(timelimit)

        resp = requests.post(
            "https://api.exa.ai/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=15,
        )
        if resp.status_code == 402:
            return None, "Exa API 额度已用完，请升级套餐"
        if resp.status_code == 429:
            return None, "Exa API 请求频率过高，请稍后重试"
        resp.raise_for_status()

        data = resp.json()
        results = []
        for r in data.get("results", []):
            highlights = r.get("highlights", []) or []
            snippet = (
                " ... ".join(highlights)
                if highlights
                else (r.get("text", "") or "")[:600]
            )
            results.append(
                {
                    "title": (r.get("title") or "").strip()[:200],
                    "snippet": snippet[:600],
                    "url": (r.get("url") or "").strip(),
                    "date": (r.get("publishedDate") or ""),
                    "domain": _extract_domain(r.get("url", "")),
                    "author": (r.get("author") or ""),
                    "score": r.get("score", 0),
                }
            )

        if not results:
            return None, "Exa 未找到相关结果"
        autoprompt = data.get("autopromptString", "")
        if autoprompt:
            logging.info("Exa autoprompt: %s → %s", keyword, autoprompt)
        return results, ""
    except requests.exceptions.Timeout:
        return None, "Exa 搜索超时 (15s)"
    except requests.exceptions.HTTPError as e:
        logging.warning("Exa HTTP 错误: %s", e)
        return None, (
            f"Exa HTTP {e.response.status_code}"
            if e.response is not None
            else str(e)[:80]
        )
    except Exception as e:
        logging.warning("Exa 搜索失败: %s", e)
        return None, str(e)[:80]


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc
        return netloc.removeprefix("www.") if netloc else ""
    except Exception:
        return ""


# ── SearXNG ─────────────────────────────────────────────────────────────


def _searxng_configured() -> bool:
    return bool(os.environ.get("SEARXNG_URL", "").strip())


def search_searxng(keyword, max_results, search_type="web") -> tuple:
    """Query a self-hosted SearXNG instance for aggregated search results.

    SearXNG is a privacy-respecting meta search engine that aggregates
    results from 70+ engines (Google, Bing, DDG, Wikipedia, Baidu, etc.)
    and provides a clean JSON API — no HTML scraping, no anti-bot wars.

    Requires SEARXNG_URL env var pointing to a running instance.
    Example: SEARXNG_URL=http://localhost:8080
    """
    base_url = os.environ.get("SEARXNG_URL", "").strip().rstrip("/")
    if not base_url:
        return None, "SEARXNG_URL 未配置"

    try:
        params = {"q": keyword, "format": "json", "categories": "general"}
        if search_type == "news":
            params["categories"] = "news"
        elif search_type == "image":
            params["categories"] = "images"

        resp = requests.get(
            f"{base_url}/search",
            params=params,
            timeout=12,
            headers={
                "User-Agent": "mind-agent/2.0",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", [])[:max_results]:
            url = r.get("url", "")
            if not url or not url.startswith("http"):
                continue
            results.append({
                "title": (r.get("title") or "").strip()[:200],
                "snippet": (r.get("content") or r.get("snippet", "") or "")[:600],
                "url": url,
                "date": (r.get("publishedDate") or r.get("engines", [""])[0] or ""),
                "domain": _extract_domain(url),
            })

        if not results:
            return None, "SearXNG 未返回结果"

        logging.info("SearXNG: %d results for '%s'", len(results), keyword)
        return results, ""
    except requests.exceptions.Timeout:
        return None, "SearXNG 搜索超时 (12s)"
    except requests.exceptions.ConnectionError:
        return None, f"无法连接到 SearXNG: {base_url}"
    except Exception as e:
        logging.warning("SearXNG 搜索失败: %s", e)
        return None, str(e)[:80]
