# -*- coding: UTF-8 -*-
"""Web search tool — search the web and fetch page content."""

import json
import logging
import os
import re
import tempfile
import uuid
from html.parser import HTMLParser

import requests

from app.util.tool_registry import ToolRegistry
from app.util.vision import VisionHandler
from app.package.module.blueprint_mysql import BlueprintMysqlHandler

# ══════════════════════════════════════════════════════════════════════════════
# Search & Web Tools
# ══════════════════════════════════════════════════════════════════════════════

def _require(args: dict, *keys: str) -> str | None:
    for k in keys:
        val = args.get(k)
        if val is None or (isinstance(val, str) and not val.strip()):
            return f"缺少必填参数: {k}"
    return None


class _TextExtractor(HTMLParser):
    """Extract plain text from HTML, stripping all tags, skipping scripts/styles."""

    def __init__(self):
        super().__init__()
        self.text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "iframe", "head"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "iframe", "head"):
            self._skip = False
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self.text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.text.append(t)

    def get_text(self):
        return "\n".join(self.text)


# web_search tool is now in app.util.search.engine_chain (auto-registered on import)
# web_fetch tool kept below

@ToolRegistry.register(
    "web_fetch",
    "抓取指定URL的网页内容并提取正文。适用于用户提供链接要求分析、总结或提取页面信息时使用。",
    {"type": "object", "properties": {
        "url": {"type": "string", "description": "要抓取的网页链接（完整URL，如 https://example.com/article）"},
    }, "required": ["url"]},
)
def _tool_web_fetch(args):
    url = args.get("url", "").strip()
    if not url:
        return {"success": False, "error": "请提供要抓取的链接"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        if "text/html" not in ct.lower() and "text/plain" not in ct.lower():
            return {
                "success": False,
                "error": f"该链接不是HTML页面（Content-Type: {ct}），无法提取文本",
            }

        resp.encoding = resp.apparent_encoding or "utf-8"
        html_text = resp.text

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""

        extractor = _TextExtractor()
        extractor.feed(html_text)
        body = extractor.get_text()

        if len(body) > 8000:
            body = body[:8000] + "\n\n... [内容已截断，原文过长]"

        return {
            "success": True,
            "data": {
                "url": url,
                "title": title[:200],
                "content": body,
                "length": len(body),
            },
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": f"请求超时 (15s): {url}"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"请求失败 (HTTP {e.response.status_code}): {url}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"无法连接到该网站: {url}"}
    except Exception as e:
        logging.warning("web_fetch 失败: %s", e)
        return {"success": False, "error": f"抓取失败: {str(e)[:150]}"}

def _validate_analyze_image(args):
    url = args.get("image_url", "")
    b64 = args.get("image_base64", "")
    if not (url or b64):
        return "缺少参数: 需要 image_url 或 image_base64 之一"
    return None

@ToolRegistry.register(
    "analyze_image",
    "分析一张图片的内容。可进行场景描述(describe)、物体检测(detect)或智能分类(classify)。"
    "支持两种输入方式：1) image_url — 图片URL地址；2) image_base64 — base64格式的图片数据。二者选一即可。",
    {"type": "object", "properties": {
        "image_url": {"type": "string", "description": "图片URL地址（与 image_base64 二选一）"},
        "image_base64": {"type": "string", "description": "base64格式的图片数据，data:image/...;base64,... 格式（与 image_url 二选一）"},
        "task_type": {
            "type": "string",
            "enum": ["describe", "detect", "classify"],
            "description": "describe=场景描述(含关键词), detect=物体检测, classify=智能分类",
        },
    }, "required": ["task_type"]},
    validator=_validate_analyze_image,
)
def _tool_analyze_image(args):
    task_type = args["task_type"]
    image_base64 = args.get("image_base64", "")
    image_url = args.get("image_url", "")

    if task_type == "classify":
        prompt = VisionHandler.build_classify_prompt([])
    elif task_type == "detect":
        prompt = VisionHandler.build_detect_prompt()
    else:
        prompt = VisionHandler.build_describe_prompt()

    if image_base64:
        ok, result = VisionHandler.analyze_base64(image_base64, prompt, task_type)
    else:
        ok, result = VisionHandler.analyze_image(image_url, prompt, task_type)
    return {"success": ok, "data": result, "task_type": task_type}


def _validate_analyze_doc(args):
    obj = args.get("object_name", "")
    if not obj or not isinstance(obj, str) or not obj.strip():
        return "缺少必填参数: object_name"
    if not obj.lower().endswith(".docx"):
        return f"不支持的文件格式，仅支持 .docx: {obj}"
    return None


