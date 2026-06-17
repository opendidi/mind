# -*- coding: UTF-8 -*-
"""Agent Reflexion — closed-loop self-correction beyond simple retry."""

import json
import logging
from dataclasses import dataclass, field

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent_helpers import extract_json

MAX_REFLECT_RETRIES = 3
MAX_LOOP_REPEAT = 3

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
        "connection", "timeout", "rate limit", "server error", "503",
        "502", "500", "unavailable", "circuit breaker", "AI service error",
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
        from app.util.agent_circuit import circuit_allow

        if self._consecutive_llm_failures >= 3:
            logging.warning("Reflexion: %d consecutive LLM failures, skipping", self._consecutive_llm_failures)
            return None
        if not circuit_allow(service=self.model):
            logging.warning("Reflexion: circuit breaker open for %s", self.model)
            self._consecutive_llm_failures += 1
            return None

        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

        for attempt in range(3):
            try:
                resp = self.llm.chat.completions.create(
                    model=self.model, messages=[{"role": "user", "content": prompt}],
                    temperature=0.1, max_tokens=512, timeout=timeout,
                )
                self._consecutive_llm_failures = 0
                return resp.choices[0].message.content or ""
            except (RateLimitError, APITimeoutError, APIConnectionError) as ex:
                if attempt >= 2:
                    self._consecutive_llm_failures += 1
                    logging.warning("Reflexion LLM call failed after retries (x%d): %s", self._consecutive_llm_failures, ex)
                    return None
                import time as _time
                _time.sleep((2 ** attempt) + __import__("random").uniform(0, 1))
            except APIError as ex:
                status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                if status < 500 or attempt >= 2:
                    self._consecutive_llm_failures += 1
                    logging.warning("Reflexion LLM call failed (x%d): %s", self._consecutive_llm_failures, ex)
                    return None
                import time as _time
                _time.sleep((2 ** attempt))
            except Exception:
                self._consecutive_llm_failures += 1
                logging.warning("Reflexion LLM call failed (x%d)", self._consecutive_llm_failures, exc_info=True)
                return None

    def analyze_failure(self, tool_name: str, tool_args: dict, error_result: dict,
                        goal: str, step_desc: str, completed_steps: list[str],
                        remaining_steps: list[str]) -> dict:
        error_msg = str(error_result)
        if self._is_infra_error(error_msg):
            logging.info("Reflexion: infra error detected, escalating: %s", error_msg[:80])
            return {"cause": "AI 服务或网络异常", "recovery": "escalate", "adjusted_args": None,
                    "suggestion": "请稍后重试或检查网络连接"}

        prompt = REFLECT_PROMPT.format(
            goal=goal, step_desc=step_desc, tool_name=tool_name,
            tool_args=json.dumps(tool_args, ensure_ascii=False), error_msg=error_msg,
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
        return {"cause": "分析失败", "recovery": "escalate", "adjusted_args": None,
                "suggestion": "工具执行失败，请尝试换一种方式描述需求"}

    def validate_result(self, tool_name: str, tool_args: dict, result: dict) -> dict:
        if not result.get("success"):
            return {"valid": False, "issue": "工具返回失败", "suggestion": ""}
        result_text = json.dumps(result, ensure_ascii=False)[:2000]
        if result.get("data") is not None and result.get("data") != [] and result.get("data") != {}:
            return {"valid": True, "issue": "", "suggestion": ""}
        raw = self._call_reflect_llm(
            RESULT_VALIDATE_PROMPT.format(tool_name=tool_name, tool_args=json.dumps(tool_args, ensure_ascii=False), result_text=result_text),
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
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

        for attempt in range(2):
            try:
                resp = self.llm.chat.completions.create(
                    model=self.model, messages=[{"role": "user", "content": prompt}],
                    temperature=0, max_tokens=256, timeout=10,
                )
                raw = resp.choices[0].message.content or ""
                text = self._extract_json(raw)
                if text:
                    return json.loads(text)
                break  # response ok but no valid JSON — don't retry
            except (RateLimitError, APITimeoutError, APIConnectionError) as ex:
                if attempt >= 1:
                    break
                import time as _t
                _t.sleep(1 + __import__("random").uniform(0, 0.5))
            except APIError as ex:
                status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                if status < 500 or attempt >= 1:
                    break
                import time as _t
                _t.sleep(1)
            except Exception:
                logging.warning("Overall goal verification failed", exc_info=True)
                break

        n_completed = len(completed_results)
        n_total = n_completed + len(failed_results)
        return {"overall_success": n_completed / max(n_total, 1) > 0.5,
                "summary": f"完成 {n_completed}/{n_total} 个步骤", "missing": failed_results}

    @staticmethod
    def _extract_json(text: str) -> str:
        return extract_json(text)
