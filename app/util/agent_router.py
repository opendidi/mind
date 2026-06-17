# -*- coding: UTF-8 -*-
"""Agent Router — keyword-first intent classification with LLM fallback."""

import json
import logging
import random
import time

from app.config import AGENT_DEFAULT_MODEL

# ── Route definitions ──────────────────────────────────────────────────

_ROUTE_KEYWORDS = {
    "search": [
        "新闻", "天气", "最新", "热搜", "热点", "今天", "实时",
        "搜索", "查一下", "帮我查", "帮我找", "搜一下",
        "news", "weather", "latest", "search", "find", "today",
    ],
    "canvas": [
        "画", "画布", "图形", "节点", "矩形", "圆形", "三角形", "菱形",
        "连线", "箭头", "文本", "添加", "创建", "删除", "修改", "编辑",
        "流程图", "架构图", "思维导图", "导图", "布局", "排列", "对齐",
        "color", "背景", "大小", "移动", "撤销", "重做",
    ],
    "blueprint": [
        "保存", "加载", "打开", "导出", "导入", "蓝图",
        "PNG", "SVG", "JSON", "另存为",
    ],
    "file": [
        "上传", "上传文件", "素材", "图片", "文件夹", "目录", "文件管理",
        "搜索文件", "查找文件", "文件",
    ],
    "code": [
        "生成代码", "写代码", "脚本", "JS代码",
    ],
}

_CHAT_KEYWORDS = [
    "你好", "嗨", "谢谢", "再见", "拜拜", "好的", "嗯",
    "hello", "hi", "thanks", "bye",
]

_ROUTE_MAP = {
    "search":   {"route": "search", "domain": [], "has_write": False},
    "canvas":   {"route": "canvas", "domain": ["canvas"], "has_write": True},
    "blueprint":{"route": "blueprint", "domain": ["blueprint"], "has_write": False},
    "file":     {"route": "file", "domain": ["file"], "has_write": False},
    "code":     {"route": "code", "domain": ["code"], "has_write": False},
    "chat":     {"route": "chat", "domain": [], "has_write": False},
}


def _keyword_route(user_message: str) -> dict | None:
    """Fast keyword-based routing. Returns route dict or None."""
    msg = user_message

    # Chat detection first (simple greetings)
    for kw in _CHAT_KEYWORDS:
        if msg.strip().lower() == kw.lower():
            return _ROUTE_MAP["chat"]

    # Score each route by keyword matches
    scores = {}
    for route, keywords in _ROUTE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg)
        if score > 0:
            scores[route] = score

    if not scores:
        return None

    best = max(scores, key=scores.get)
    return _ROUTE_MAP[best]


# ── LLM-based routing prompt ────────────────────────────────────────────

ROUTER_PROMPT = """你是意图路由专家。分析用户输入，输出路由分类（严格 JSON）。

## 路由选项
- chat: 闲聊、问候、知识问答（不需要工具）
- search: 需要实时信息、联网搜索
- canvas: 画布操作（创建/修改/删除图形）
- blueprint: 蓝图管理（保存/加载/导出）
- file: 文件管理（上传/搜索文件）
- code: 代码生成

## 输出格式
{"route": "<路由名>", "domain": [], "has_write": false, "confidence": 0.9}

## 规则
- has_write: true 仅当用户要求创建/修改/删除数据
- domain: 涉及的领域标签
- confidence: 0~1 置信度
- 不确定时选 chat，不要强行匹配
"""


def _llm_route(llm_client, user_message: str, model: str = AGENT_DEFAULT_MODEL) -> dict:
    """LLM-based routing fallback."""
    from app.util.agent_helpers import extract_json

    try:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=128,
            timeout=10,
        )
        raw = resp.choices[0].message.content or ""
        text = extract_json(raw)
        if text:
            data = json.loads(text)
            route = data.get("route", "chat")
            if route not in _ROUTE_MAP:
                route = "chat"
            return {
                "route": route,
                "domain": data.get("domain", []),
                "has_write": data.get("has_write", False),
                "confidence": data.get("confidence", 0.5),
                "source": "llm",
            }
    except Exception:
        logging.warning("Router LLM call failed, falling back to chat")

    return {"route": "chat", "domain": [], "has_write": False, "confidence": 0.0, "source": "fallback"}


# ── Public API ──────────────────────────────────────────────────────────

def route_intent(llm_client, user_message: str, model: str = AGENT_DEFAULT_MODEL) -> dict:
    """Classify user intent into a route.

    Returns: {"route": str, "domain": list, "has_write": bool, "confidence": float}
    """
    # 1. Try keyword matching (zero token cost)
    result = _keyword_route(user_message)
    if result:
        result["confidence"] = 0.8
        result["source"] = "keyword"
        return result

    # 2. LLM fallback
    if llm_client:
        return _llm_route(llm_client, user_message, model)

    return {"route": "chat", "domain": [], "has_write": False, "confidence": 0.0, "source": "fallback"}
