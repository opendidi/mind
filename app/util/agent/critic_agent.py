# -*- coding: UTF-8 -*-
"""CriticAgent — 独立质量审查 Agent

在 DAG 执行完成后，从正确性、完整性、一致性、安全性四个维度
独立审查执行结果。不参与主执行流程，不增加主链路延迟。
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.constants import CRITIC_MAX_RETRIES, CRITIC_QUALITY_THRESHOLD, CRITIC_TIMEOUT

# ── Prompt 模板 ──────────────────────────────────────────────────────────

CRITIC_SYSTEM_PROMPT = """你是独立审查专家（Critic Agent）。你的职责是无偏见地审查 AI 执行结果。

审查维度：
1. **正确性 (Correctness)**: 结果是否准确？有没有事实错误？
2. **完整性 (Completeness)**: 用户的所有需求是否都被覆盖？
3. **一致性 (Consistency)**: 结果是否与之前的执行决策一致？有没有矛盾？
4. **安全性 (Security)**: 是否存在安全风险？是否有未经确认的破坏性操作？

输出格式（严格 JSON）：
{
  "overall_score": 0.0-1.0,
  "passes": true/false,
  "issues": [
    {"severity": "critical|major|minor", "domain": "correctness|completeness|consistency|security", "description": "...", "suggestion": "..."}
  ],
  "missing_requirements": ["需求1", "需求2"],
  "safety_concerns": ["关注点1"],
  "suggested_improvements": ["改进建议1"],
  "needs_replan": true/false
}"""

CRITIC_PLAN_PROMPT = """请审查以下执行计划：

## 用户需求
{user_message}

## 执行计划
模式: {plan_mode}
目标: {goal}
风险等级: {risk}
步骤数: {node_count}
步骤:
{nodes_summary}

## 领域
{domains}

请评估此计划是否合理，是否存在遗漏或风险。"""

CRITIC_RESULT_PROMPT = """请审查以下执行结果：

## 用户需求
{user_message}

## 执行计划
目标: {goal}
步骤数: {total_steps}

## 执行结果
成功: {completed_count}/{total_steps}
失败: {failed_count}/{total_steps}
耗时: {duration_seconds:.1f}s
反思次数: {reflection_count}

## 步骤详情
{step_details}

## 当前世界状态
{world_state_summary}

请评估执行结果是否满足用户需求。"""


# ── 数据模型 ────────────────────────────────────────────────────────────


@dataclass
class CriticReview:
    """审查结果。"""

    overall_score: float = 0.0  # 0.0-1.0
    passes: bool = True  # 是否通过质量门禁
    issues: list = field(default_factory=list)  # [{severity, domain, description, suggestion}]
    missing_requirements: list = field(default_factory=list)
    safety_concerns: list = field(default_factory=list)
    suggested_improvements: list = field(default_factory=list)
    needs_replan: bool = False
    review_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "passes": self.passes,
            "issues": self.issues,
            "missing_requirements": self.missing_requirements,
            "safety_concerns": self.safety_concerns,
            "suggested_improvements": self.suggested_improvements,
            "needs_replan": self.needs_replan,
            "review_duration_ms": self.review_duration_ms,
        }

    @classmethod
    def empty(cls) -> "CriticReview":
        """返回一个空的通过审查（用于 LLM 不可用时的降级）。"""
        return cls(overall_score=1.0, passes=True)

    def get_quality_hints(self) -> str:
        """生成用于注入执行指令的质量提示。"""
        if not self.issues and not self.missing_requirements:
            return ""
        parts = ["## 质量要求（Critic 建议）"]
        for issue in self.issues[:3]:
            parts.append(f"- [{issue.get('severity', 'minor')}] {issue.get('description', '')}")
        for req in self.missing_requirements[:3]:
            parts.append(f"- 缺失需求: {req}")
        return "\n".join(parts)


# ── Critic Agent ─────────────────────────────────────────────────────────


class CriticAgent:
    """独立审查 Agent — 评估计划和执行结果质量。

    遵循 AgentReflexion 的模式：LLM 驱动、熔断保护、优雅降级。
    审查失败时默认返回通过（不阻塞正常流程）。
    """

    def __init__(
        self,
        llm_client=None,
        model: str = AGENT_DEFAULT_MODEL,
        quality_threshold: float = CRITIC_QUALITY_THRESHOLD,
    ):
        self.llm = llm_client
        self.model = model
        self.quality_threshold = quality_threshold
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

    # ── 公共 API ─────────────────────────────────────────────────────────

    def review_plan(self, plan, user_message: str = "", domains: list = None) -> CriticReview:
        """审查执行计划（执行前）."""
        if not self.llm:
            return CriticReview.empty()

        nodes_summary = self._summarize_nodes(plan)
        prompt = CRITIC_PLAN_PROMPT.format(
            user_message=user_message[:1000],
            plan_mode=plan.mode if hasattr(plan, "mode") else "simple",
            goal=plan.goal if hasattr(plan, "goal") else user_message[:200],
            risk=plan.risk if hasattr(plan, "risk") else "low",
            node_count=len(plan.nodes) if hasattr(plan, "nodes") else 0,
            nodes_summary=nodes_summary,
            domains=", ".join(domains or ["general"]),
        )
        return self._call_critic(prompt)

    def review_execution(
        self,
        plan,
        execution_state,
        world_state=None,
        user_message: str = "",
    ) -> CriticReview:
        """审查执行结果（执行后）."""
        if not self.llm:
            return CriticReview.empty()

        # 提取步骤详情
        step_details = self._summarize_step_results(execution_state)
        total = len(execution_state.results) if hasattr(execution_state, "results") else 0
        completed = len(execution_state.completed) if hasattr(execution_state, "completed") else 0
        failed = len(execution_state.failed) if hasattr(execution_state, "failed") else 0
        goal = plan.goal if hasattr(plan, "goal") else ""

        # 世界状态摘要
        world_summary = ""
        if world_state:
            world_summary = (
                world_state.get_task_summary()
                if hasattr(world_state, "get_task_summary")
                else str(world_state.to_dict())[:500]
            )

        prompt = CRITIC_RESULT_PROMPT.format(
            user_message=user_message[:1000],
            goal=goal[:300],
            total_steps=max(total, 1),
            completed_count=completed,
            failed_count=failed,
            duration_seconds=0,
            reflection_count=0,
            step_details=step_details,
            world_state_summary=world_summary,
        )
        return self._call_critic(prompt)

    def review_final_output(self, output_text: str, user_intent: str = "", plan=None) -> CriticReview:
        """审查最终输出文本."""
        if not self.llm or not output_text:
            return CriticReview.empty()

        prompt = f"""请审查以下 AI 输出：

## 用户意图
{user_intent[:500]}

## AI 输出
{output_text[:2000]}

请从正确性、完整性、一致性、安全性四个维度评估。"""
        return self._call_critic(prompt)

    # ── 内部实现 ─────────────────────────────────────────────────────────

    def _call_critic(self, prompt: str) -> CriticReview:
        """执行一次审查 LLM 调用。"""
        from app.util.agent.circuit import circuit_allow, circuit_record

        t0 = time.time()

        # 连续失败过多则跳过
        if self._consecutive_failures >= self._max_consecutive_failures:
            logging.warning("CriticAgent: too many consecutive failures, skipping review")
            return CriticReview.empty()

        # 熔断检查
        service = f"critic:{self.model}"
        if not circuit_allow(service=service):
            return CriticReview.empty()

        try:
            from app.util.agent.retry import retry_llm_call

            messages = [
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt[:4000]},
            ]

            resp = retry_llm_call(
                lambda: self.llm.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=512,
                    timeout=CRITIC_TIMEOUT,
                ),
                max_retries=CRITIC_MAX_RETRIES,
            )
            circuit_record(True, service=service)
            self._consecutive_failures = 0
            return self._parse_review(resp.choices[0].message.content or "")

        except Exception as e:
            circuit_record(False, service=service)
            self._consecutive_failures += 1
            logging.warning("CriticAgent review failed: %s", e)
            return CriticReview.empty()

    @staticmethod
    def _parse_review(raw: str) -> CriticReview:
        """解析 LLM 审查输出为 CriticReview。"""
        try:
            from app.util.agent.helpers import extract_json

            data = extract_json(raw)
            if data is None:
                return CriticReview.empty()

            if isinstance(data, str):
                data = json.loads(data)

            review = CriticReview(
                overall_score=float(data.get("overall_score", 0.8)),
                passes=bool(data.get("passes", True)),
                issues=data.get("issues", []),
                missing_requirements=data.get("missing_requirements", []),
                safety_concerns=data.get("safety_concerns", []),
                suggested_improvements=data.get("suggested_improvements", []),
                needs_replan=bool(data.get("needs_replan", False)),
            )

            # 应用质量门禁
            if review.overall_score < CRITIC_QUALITY_THRESHOLD:
                review.passes = False

            return review

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logging.debug("CriticAgent parse failed: %s", e)
            return CriticReview.empty()

    @staticmethod
    def _summarize_nodes(plan) -> str:
        """生成计划节点摘要文本。"""
        if not hasattr(plan, "nodes") or not plan.nodes:
            return "（无步骤）"
        lines = []
        for i, node in enumerate(plan.nodes[:10], 1):
            desc = node.desc if hasattr(node, "desc") else str(node)
            tool = node.tool_hint if hasattr(node, "tool_hint") and node.tool_hint else ""
            agent = node.agent_name if hasattr(node, "agent_name") and node.agent_name else ""
            extra = f" [tool={tool}]" if tool else ""
            extra += f" [agent={agent}]" if agent else ""
            deps = f" (依赖: {', '.join(node.depends_on)})" if hasattr(node, "depends_on") and node.depends_on else ""
            lines.append(f"  {i}. {desc}{extra}{deps}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_step_results(execution_state) -> str:
        """生成执行结果摘要。"""
        if not hasattr(execution_state, "results"):
            return "（无结果）"
        lines = []
        for nid, result in execution_state.results.items():
            status = "✅" if result.success else "❌"
            output_preview = ""
            if hasattr(result, "output") and result.output:
                output_preview = str(result.output.get("text", ""))[:100]
            lines.append(f"  {status} {nid}: {output_preview}")
        return "\n".join(lines) if lines else "（无结果）"
