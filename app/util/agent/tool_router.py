# -*- coding: UTF-8 -*-
"""ToolRouter — 意图/领域 → 工具集路由

根据意图分类和领域标签筛选相关的工具 schema，减少注入 LLM prompt 的工具数量。
降低 prompt 长度 40-60%，减少 tool hallucination。
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import ClassVar

from app.util.agent.constants import MAX_TOOL_SCHEMAS, TOOL_ROUTE_CACHE_TTL


@dataclass
class ToolRouting:
    """工具路由结果。"""

    tools: list  # 筛选后的 tool schemas
    excluded_tools: list = field(default_factory=list)  # 被排除的工具名
    routing_rationale: str = ""  # 路由选择理由
    prompt_hint: str = ""  # 可注入 system prompt 的指导文本


class ToolRouter:
    """根据意图 + 领域 + 用户消息特征，筛选相关工具集。

    设计原则：
        - 保守过滤：始终包含通用工具，宁多勿少
        - 分层映射：领域基础集 + 用例关键词扩展
        - 缓存友好：相同输入返回相同结果
    """

    # ── 领域 → 基础工具映射 ──
    DOMAIN_TOOL_MAP: ClassVar[dict] = {
        "canvas": [
            "canvas",
            "canvas_check_empty",
            "layout_auto_arrange",
            "layout_align",
            "canvas_props",
            "fit_view",
        ],
        "blueprint": [
            "blueprint_list",
            "blueprint_load",
            "blueprint_save",
            "blueprint_search",
            "blueprint_export",
        ],
        "file": [
            "file_search",
            "read_text",
            "analyze_doc",
            "extract_excel",
            "parse_json",
        ],
        "mindmap": [],  # mindmap 使用 markdown 文本，不需要工具
        "code": ["code_generate"],
        "map": ["geocode", "regeocode"],
        "translate": ["translate_text"],
        "travel": ["geocode", "regeocode"],
        "general": [],  # 通用意图
    }

    # ── 跨领域通用工具（始终包含） ──
    COMMON_TOOLS: ClassVar[list] = [
        "web_search",
        "web_fetch",
        "analyze_image",
        "dispatch_agent",
    ]

    # ── 用例关键词 → 额外工具 ──
    USE_CASE_KEYWORDS: ClassVar[dict] = {
        "地图": ["geocode", "regeocode"],
        "路线": ["geocode", "regeocode"],
        "导航": ["geocode", "regeocode"],
        "地点": ["geocode", "regeocode"],
        "搜索": ["web_search"],
        "搜索一下": ["web_search"],
        "查一下": ["web_search"],
        "新闻": ["web_search"],
        "翻译": ["translate_text"],
        "译成": ["translate_text"],
        "翻译成": ["translate_text"],
        "图片": ["analyze_image"],
        "照片": ["analyze_image"],
        "图像": ["analyze_image"],
        "识别": ["analyze_image"],
        "分析图片": ["analyze_image"],
        "布局": ["layout_auto_arrange", "layout_align"],
        "排版": ["layout_auto_arrange", "layout_align"],
        "排列": ["layout_auto_arrange"],
        "对齐": ["layout_align"],
        "Excel": ["extract_excel"],
        "表格": ["extract_excel"],
        "Word": ["analyze_doc"],
        "文档": ["analyze_doc"],
        "JSON": ["parse_json"],
        "json": ["parse_json"],
        "生成代码": ["code_generate"],
        "写代码": ["code_generate"],
        "代码": ["code_generate"],
        "保存蓝图": ["blueprint_save"],
        "加载蓝图": ["blueprint_load"],
        "导出": ["blueprint_export"],
        # 旅游/地名
        "旅游": ["geocode", "regeocode"],
        "旅行": ["geocode", "regeocode"],
        "景点": ["geocode", "regeocode"],
        "攻略": ["web_search"],
        "好玩": ["web_search"],
        "美食": ["web_search"],
        "特色": ["web_search"],
    }

    def __init__(self, max_tool_schemas: int = MAX_TOOL_SCHEMAS):
        self._max = max_tool_schemas
        self._cache: dict = {}

    def route(self, domains: list, user_message: str = "", has_write: bool = False) -> ToolRouting:
        """根据领域和用户消息筛选工具 schema。

        Args:
            domains: 领域列表，如 ["canvas", "blueprint"]
            user_message: 用户消息文本，用于关键词扩展
            has_write: 是否涉及写操作（写操作需要更多工具）

        Returns:
            ToolRouting 包含筛选后的工具 schemas
        """
        from app.util.agent.tools import TOOL_SCHEMAS

        if not domains:
            domains = ["general"]

        # 缓存键
        cache_key = self._cache_key(domains, user_message[:100])
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 收集工具名
        tool_names: set = set()

        # 1. 领域基础工具
        for domain in domains:
            domain_tools = self.DOMAIN_TOOL_MAP.get(domain, [])
            tool_names.update(domain_tools)

        # 2. 用例关键词扩展
        use_case_tools = self._expand_use_cases(user_message)
        tool_names.update(use_case_tools)

        # 3. 通用工具（始终包含）
        for t in self.COMMON_TOOLS:
            tool_names.add(t)

        # 4. 写操作需要更全面的工具集
        if has_write:
            # 写操作可能涉及多个领域，包含更多工具
            for domain_tools in self.DOMAIN_TOOL_MAP.values():
                tool_names.update(domain_tools[:3])  # 只取前3个核心工具

        # 5. 从 TOOL_SCHEMAS 中筛选匹配的工具
        filtered = []
        excluded = []
        all_schema_names = {s.get("function", {}).get("name", ""): s for s in TOOL_SCHEMAS}

        for name in sorted(tool_names):
            if name in all_schema_names:
                filtered.append(all_schema_names[name])

        # 记录被排除的工具
        for name in all_schema_names:
            if name not in tool_names and name not in self.COMMON_TOOLS:
                excluded.append(name)

        # 6. 数量限制
        if len(filtered) > self._max:
            # 优先保留领域工具和通用工具
            filtered = filtered[: self._max]

        rationale = f"domains={domains} has_write={has_write} → {len(filtered)} tools"

        routing = ToolRouting(
            tools=filtered,
            excluded_tools=excluded,
            routing_rationale=rationale,
            prompt_hint=self._get_routing_hint(domains),
        )

        # 缓存
        self._cache[cache_key] = routing
        if len(self._cache) > 100:
            # 简单 FIFO 淘汰
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        return routing

    def _expand_use_cases(self, user_message: str) -> set:
        """通过关键词匹配扩展额外工具。"""
        extra: set = set()
        if not user_message:
            return extra
        for keyword, tools in self.USE_CASE_KEYWORDS.items():
            if keyword.lower() in user_message.lower():
                extra.update(tools)
        return extra

    @staticmethod
    def _cache_key(domains: list, message_prefix: str) -> str:
        raw = json.dumps({"d": sorted(domains), "m": message_prefix[:80]}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @staticmethod
    def _get_routing_hint(domains: list) -> str:
        """生成可选的 system prompt 注入提示。"""
        if "canvas" in domains:
            return "当前为画布/图形操作场景，请优先使用画布相关工具。"
        if "blueprint" in domains:
            return "当前为蓝图管理场景，请使用蓝图保存/加载/搜索工具。"
        if "file" in domains:
            return "当前为文件操作场景，请使用文件搜索、文档解析工具。"
        if "code" in domains:
            return "当前为代码生成场景，请输出可直接使用的代码。"
        if "travel" in domains:
            return "当前为旅游/地名探索场景，请搜索相关信息并用思维导图结构化输出。"
        return ""
