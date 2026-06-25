# -*- coding: UTF-8 -*-
"""Agent Reflexion — closed-loop self-correction beyond simple retry.

Phase 1: 新增 STRATEGY 反射类型 — 发现当前计划不合理时，直接重新规划。
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.constants import (
    MAX_LOOP_REPEAT,
    MAX_REFLECT_RETRIES,
    MAX_STRATEGIC_RETRIES,
    STRATEGIC_REFLECT_TIMEOUT,
)
from app.util.agent.helpers import extract_json


class ReflectionType(Enum):
    """反射类型。"""
    ERROR = "error"       # 工具调用失败，需要重试
    QUALITY = "quality"   # 结果质量不达标，需要补充
    STRATEGY = "strategy"  # 整体方案不合理，需要重新规划

REFLECT_PROMPT = """你是故障诊断专家。一个工具执行失败了，分析原因并提出恢复方案。

## 输入
- 目标: {goal}
- 当前步骤: {step_desc}
- 工具: {tool_name}
- 参数: {tool_args}
- 错误: {error_msg}
- 已完成步骤: {completed_steps}
- 剩余步骤: {remaining_steps}

## 输出格式（严格 JSON）
{{
  "cause": "失败原因分析（一句话）",
  "recovery": "retry/skip/escalate",
  "adjusted_args": {{"key": "修改后的参数值"}} 或 null,
  "suggestion": "给用户的建议"
}}

## 规则
- recovery=retry: 可调整参数重试，给出 adjusted_args
- recovery=skip: 这一步可跳过不影响目标，继续执行
- recovery=escalate: 无法自动修复，需用户介入
"""

RESULT_VALIDATE_PROMPT = """你是结果校验专家。检查工具返回结果是否合理。

## 输入
- 工具: {tool_name}
- 参数: {tool_args}
- 结果: {result_text}

## 输出格式（严格 JSON）
{{
  "valid": true/false,
  "issue": "问题描述（valid=false时填写）",
  "suggestion": "修复建议"
}}

常见问题:
- 空结果但应该返回数据
- 返回字段缺失关键信息
- 数据明显不合理（如负数数量）
- 错误信息模糊不清
"""

GOAL_CHECK_PROMPT = """你是目标验证专家。判断当前步骤是否达成了预期目标。

## 输入
- 步骤目标: {step_desc}
- 执行结果: {result_text}

## 输出格式（严格 JSON）
{{
  "achieved": true/false,
  "gap": "未达成的内容描述（achieved=false时填写）",
  "next_action": "完成/supplement/retry"
}}

若只完成了部分目标，next_action=supplement 表示需要补充操作。
"""

REFLECT_STRATEGY_PROMPT = """你是任务策略专家。执行计划整体出现了问题，请分析原因并重新设计计划结构。

## 输入
- 目标: {goal}
- 原始计划模式: {plan_mode}
- 已完成步骤: {completed_steps}
- 失败步骤: {failed_steps}
- 批评意见: {critic_feedback}
- 当前状态摘要: {state_summary}

## 输出格式（严格 JSON）
{{
  "root_cause": "根本原因分析（一句话）",
  "should_restructure": true/false,
  "restructured_plan": {{
    "mode": "dag",
    "goal": "修改后的目标（如需调整）",
    "risk": "low|medium|high",
    "nodes": [
      {{"id": "s1", "desc": "步骤描述", "tool_hint": "tool_name", "depends_on": []}}
    ]
  }},
  "changes_made": ["变化描述1", "变化描述2"],
  "confidence": 0.0-1.0
}}

## 规则
- should_restructure=true: 当前计划需要根本性重构
- 重构时应保留已完成步骤的成果
- 避免重复已知会失败的操作
- 新的计划应更简单、更直接
"""


@dataclass
class ReflexionResult:
    success: bool
    cause: str = ""
    recovery: str = "escalate"
    adjusted_args: dict = field(default_factory=dict)
    suggestion: str = ""
    validation_issue: str = ""
    goal_gap: str = ""


class AgentReflexion:
    INFRA_ERROR_PATTERNS = (
        "connection",
        "timeout",
        "rate limit",
        "server error",
        "503",
        "502",
        "500",
        "unavailable",
        "circuit breaker",
        "AI service error",
        "服务暂不可用",
    )

    def __init__(self, llm_client, model: str = AGENT_DEFAULT_MODEL):
        self.llm = llm_client
        self.model = model
        self._consecutive_llm_failures = 0

    def _is_infra_error(self, error_msg: str) -> bool:
        lower = error_msg.lower()
        return any(p in lower for p in self.INFRA_ERROR_PATTERNS)

    def _call_reflect_llm(self, prompt: str, timeout: int = 20) -> str | None:
        from app.util.agent.circuit import circuit_allow

        if self._consecutive_llm_failures >= 3:
            logging.warning("Reflexion: %d consecutive LLM failures, skipping", self._consecutive_llm_failures)
            return None
        if not circuit_allow(service=self.model):
            logging.warning("Reflexion: circuit breaker open for %s", self.model)
            self._consecutive_llm_failures += 1
            return None

        from app.util.agent.retry import retry_llm_call

        try:
            resp = retry_llm_call(
                lambda: self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=512,
                    timeout=timeout,
                ),
                max_retries=3,
            )
            self._consecutive_llm_failures = 0
            return resp.choices[0].message.content or ""
        except Exception:
            self._consecutive_llm_failures += 1
            logging.warning("Reflexion LLM call failed (x%d)", self._consecutive_llm_failures, exc_info=True)
            return None

    def analyze_failure(
        self,
        tool_name: str,
        tool_args: dict,
        error_result: dict,
        goal: str,
        step_desc: str,
        completed_steps: list[str],
        remaining_steps: list[str],
    ) -> dict:
        error_msg = str(error_result)
        if self._is_infra_error(error_msg):
            logging.info("Reflexion: infra error detected, escalating: %s", error_msg[:80])
            return {
                "cause": "AI 服务或网络异常",
                "recovery": "escalate",
                "adjusted_args": None,
                "suggestion": "请稍后重试或检查网络连接",
            }

        prompt = REFLECT_PROMPT.format(
            goal=goal,
            step_desc=step_desc,
            tool_name=tool_name,
            tool_args=json.dumps(tool_args, ensure_ascii=False),
            error_msg=error_msg,
            completed_steps=json.dumps(completed_steps, ensure_ascii=False),
            remaining_steps=json.dumps(remaining_steps, ensure_ascii=False),
        )
        raw = self._call_reflect_llm(prompt)
        if raw:
            text = self._extract_json(raw)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
        return {
            "cause": "分析失败",
            "recovery": "escalate",
            "adjusted_args": None,
            "suggestion": "工具执行失败，请尝试换一种方式描述需求",
        }

    def validate_result(self, tool_name: str, tool_args: dict, result: dict) -> dict:
        if not result.get("success"):
            return {"valid": False, "issue": "工具返回失败", "suggestion": ""}
        result_text = json.dumps(result, ensure_ascii=False)[:2000]
        if result.get("data") is not None and result.get("data") != [] and result.get("data") != {}:
            return {"valid": True, "issue": "", "suggestion": ""}
        raw = self._call_reflect_llm(
            RESULT_VALIDATE_PROMPT.format(
                tool_name=tool_name, tool_args=json.dumps(tool_args, ensure_ascii=False), result_text=result_text
            ),
            timeout=10,
        )
        if raw:
            text = self._extract_json(raw)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
        return {"valid": True, "issue": "", "suggestion": ""}

    def check_goal(self, step_desc: str, result_text: str) -> dict:
        raw = self._call_reflect_llm(
            GOAL_CHECK_PROMPT.format(step_desc=step_desc, result_text=result_text[:2000]),
            timeout=10,
        )
        if raw:
            text = self._extract_json(raw)
            if text:
                try:
                    result = json.loads(text)
                    if result.get("next_action") == "supplement":
                        logging.info("Goal check: step '%s' partially achieved: %s", step_desc, result.get("gap", ""))
                    return result
                except json.JSONDecodeError:
                    pass
        return {"achieved": True, "gap": "", "next_action": "完成"}

    def analyze_strategy(
        self,
        goal: str,
        plan_mode: str = "dag",
        completed_steps: list = None,
        failed_steps: list = None,
        critic_feedback: str = "",
        state_summary: str = "",
    ) -> dict:
        """Phase 1: 战略级反射 — 判断整体计划是否需要重构。

        当 CriticAgent 发现执行结果不合格，或多个节点连续失败时，
        调用此方法判断是否需要彻底重新规划（而非继续重试）。

        Returns:
            dict with keys: root_cause, should_restructure, restructured_plan, changes_made, confidence
        """
        if not self.llm:
            return {
                "root_cause": "LLM 不可用",
                "should_restructure": False,
                "restructured_plan": None,
                "changes_made": [],
                "confidence": 0.0,
            }

        prompt = REFLECT_STRATEGY_PROMPT.format(
            goal=goal,
            plan_mode=plan_mode,
            completed_steps=json.dumps(completed_steps or [], ensure_ascii=False),
            failed_steps=json.dumps(failed_steps or [], ensure_ascii=False),
            critic_feedback=critic_feedback[:1000],
            state_summary=state_summary[:500],
        )

        raw = self._call_reflect_llm(prompt, timeout=STRATEGIC_REFLECT_TIMEOUT)
        if raw:
            text = self._extract_json(raw)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    logging.warning("Reflexion: strategy analysis JSON parse failed")

        return {
            "root_cause": "分析失败",
            "should_restructure": False,
            "restructured_plan": None,
            "changes_made": [],
            "confidence": 0.0,
        }

    def verify_overall_goal(self, goal: str, completed_results: list[str], failed_results: list[str]) -> dict:
        if not failed_results:
            return {"overall_success": True, "summary": "所有步骤已完成", "missing": []}
        prompt = (
            f"总体目标: {goal}\n"
            f"已完成: {json.dumps(completed_results, ensure_ascii=False)}\n"
            f"未完成: {json.dumps(failed_results, ensure_ascii=False)}\n"
            f"请判断目标是否已基本达成（部分失败不影响核心目标）。"
            f'输出 JSON: {{"overall_success": true/false, "summary": "一句话总结", "missing": ["未完成的要点"]}}'
        )
        from app.util.agent.retry import retry_llm_call

        try:
            resp = retry_llm_call(
                lambda: self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=256,
                    timeout=10,
                ),
                max_retries=2,
            )
            raw = resp.choices[0].message.content or ""
            text = self._extract_json(raw)
            if text:
                return json.loads(text)
        except Exception:
            logging.warning("Overall goal verification failed", exc_info=True)

        n_completed = len(completed_results)
        n_total = n_completed + len(failed_results)
        return {
            "overall_success": n_completed / max(n_total, 1) > 0.5,
            "summary": f"完成 {n_completed}/{n_total} 个步骤",
            "missing": failed_results,
        }

    @staticmethod
    def _extract_json(text: str) -> str:
        return extract_json(text)
