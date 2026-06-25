# -*- coding: UTF-8 -*-
"""ModelRouter — 任务类型 → 模型路由

根据任务复杂度、成本预算、模型特性选择合适的 LLM 模型。
降低单模型依赖，优化成本和质量。
"""

import logging
import os
from dataclasses import dataclass, field
from typing import ClassVar

from app.config import AGENT_DEFAULT_MODEL


@dataclass
class ModelRoute:
    """模型路由结果。"""

    primary_model: str
    fallback_chain: list = field(default_factory=list)  # 备选模型列表
    cost_profile: str = "balanced"  # "cheap", "balanced", "quality"
    max_tokens: int = 2048
    reasoning_effort: str = "medium"  # "low", "medium", "high"

    def to_dict(self) -> dict:
        return {
            "primary_model": self.primary_model,
            "fallback_chain": self.fallback_chain,
            "cost_profile": self.cost_profile,
            "max_tokens": self.max_tokens,
            "reasoning_effort": self.reasoning_effort,
        }


class ModelRouter:
    """根据任务类型和复杂度选择最优模型。

    环境变量配置：
        MODEL_CHEAP: 低成本模型（默认 deepseek-chat）
        MODEL_BALANCED: 平衡模型（默认 deepseek-chat）
        MODEL_QUALITY: 高质量模型（默认 deepseek-chat）
        MODEL_REASONING: 推理增强模型（默认 deepseek-chat）
    """

    # ── 任务类型 → 模型配置 ──
    COMPLEXITY_HEURISTICS: ClassVar[dict] = {
        "simple_chat": {
            "cost_profile": "cheap",
            "max_tokens": 1024,
            "reasoning_effort": "low",
        },
        "tool_single": {
            "cost_profile": "balanced",
            "max_tokens": 2048,
            "reasoning_effort": "medium",
        },
        "tool_multi": {
            "cost_profile": "balanced",
            "max_tokens": 4096,
            "reasoning_effort": "medium",
        },
        "dag_simple": {
            "cost_profile": "balanced",
            "max_tokens": 4096,
            "reasoning_effort": "medium",
        },
        "dag_complex": {
            "cost_profile": "quality",
            "max_tokens": 8192,
            "reasoning_effort": "high",
        },
        "reflection": {
            "cost_profile": "balanced",
            "max_tokens": 1024,
            "reasoning_effort": "medium",
        },
        "critic": {
            "cost_profile": "balanced",
            "max_tokens": 2048,
            "reasoning_effort": "medium",
        },
        "planner": {
            "cost_profile": "balanced",
            "max_tokens": 1024,
            "reasoning_effort": "medium",
        },
        "vision": {
            "cost_profile": "quality",
            "max_tokens": 4096,
            "reasoning_effort": "high",
        },
        "code": {
            "cost_profile": "quality",
            "max_tokens": 8192,
            "reasoning_effort": "high",
        },
    }

    # ── Fallback 链 ──
    DEFAULT_FALLBACK_CHAIN: ClassVar[list] = ["deepseek-chat", "gpt-4o-mini"]

    def __init__(
        self,
        cheap_model: str = "",
        balanced_model: str = "",
        quality_model: str = "",
        reasoning_model: str = "",
    ):
        self._cheap = cheap_model or os.environ.get("MODEL_CHEAP", AGENT_DEFAULT_MODEL)
        self._balanced = balanced_model or os.environ.get("MODEL_BALANCED", AGENT_DEFAULT_MODEL)
        self._quality = quality_model or os.environ.get("MODEL_QUALITY", AGENT_DEFAULT_MODEL)
        self._reasoning = reasoning_model or os.environ.get("MODEL_REASONING", AGENT_DEFAULT_MODEL)

    def route(
        self,
        task_type: str,
        plan_mode: str = "simple",
        node_count: int = 0,
    ) -> ModelRoute:
        """根据任务类型选择模型。

        Args:
            task_type: 任务类型（simple_chat, tool_single, dag_complex, ...）
            plan_mode: "simple" 或 "dag"
            node_count: DAG 节点数（用于判断复杂度）

        Returns:
            ModelRoute 包含推荐的模型和参数
        """
        config = self.COMPLEXITY_HEURISTICS.get(task_type)
        if config is None:
            # 未知类型：默认 balanced
            config = self.COMPLEXITY_HEURISTICS["simple_chat"]
            logging.debug("ModelRouter: unknown task_type=%s, falling back to simple_chat", task_type)

        cost_profile = config["cost_profile"]
        model = self._model_for_profile(cost_profile)

        # DAG 复杂任务自动提级
        if task_type.startswith("dag") and node_count > 5:
            model = self._quality  # 超过 5 个节点，升级到 quality
            cost_profile = "quality"

        # 生成 fallback 链：去掉主模型，追加默认链
        fallback = [m for m in self.DEFAULT_FALLBACK_CHAIN if m != model]

        route = ModelRoute(
            primary_model=model,
            fallback_chain=fallback,
            cost_profile=cost_profile,
            max_tokens=config["max_tokens"],
            reasoning_effort=config["reasoning_effort"],
        )

        logging.debug(
            "ModelRouter: task=%s profile=%s model=%s tokens=%d",
            task_type,
            cost_profile,
            model,
            route.max_tokens,
        )
        return route

    def route_for_node(self, node_desc: str, tool_hint: str = "") -> ModelRoute:
        """为单个 DAG 节点选择模型。"""
        if "code" in (tool_hint or "").lower() or "代码" in node_desc or "生成" in node_desc:
            return self.route("code")
        if "搜索" in node_desc or "search" in (tool_hint or "").lower():
            return self.route("tool_single")
        if "分析" in node_desc or "analyze" in (tool_hint or "").lower():
            return self.route("vision")
        return self.route("tool_single")

    def get_fallback(self, route: ModelRoute, exhausted: list = None) -> str | None:
        """获取下一个可用 fallback 模型（排除已尝试的）。"""
        exhausted_set = set(exhausted or [])
        exhausted_set.add(route.primary_model)
        for m in route.fallback_chain:
            if m not in exhausted_set:
                return m
        return None

    def _model_for_profile(self, profile: str) -> str:
        """根据成本轮廓获取模型名。"""
        mapping = {
            "cheap": self._cheap,
            "balanced": self._balanced,
            "quality": self._quality,
        }
        return mapping.get(profile, self._balanced)
