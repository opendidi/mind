# -*- coding: UTF-8 -*-
"""AgentAdaptive — LLM-based adaptive re-planning for failed DAG nodes."""

import json
import logging

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.helpers import extract_json, repair_json

ADAPTIVE_PROMPT = """你是任务重规划专家。一个 DAG 执行节点失败了，请分析原因并生成替代步骤。

## 输入
- 总目标: {plan_goal}
- 失败节点ID: {failed_node_id}
- 失败步骤描述: {failed_step_desc}
- 期望使用的工具: {tool_hint}
- 错误信息: {error_msg}
- 已完成步骤: {completed_steps}
- 剩余步骤: {remaining_steps}
- 已知上下文: {shared_context}

## 输出格式（严格 JSON）
{{
  "replacements": [
    {{
      "id": "r1",
      "desc": "替代步骤描述",
      "tool_hint": "工具名或 null",
      "agent_name": "子Agent名或 null",
      "depends_on": [],
      "confirm": false
    }}
  ]
}}

## 规则
- 生成 1~3 个替代步骤，id 用 r1、r2、r3
- depends_on 引用已完成步骤的原始 id
- 不要重复已经失败的操作，换一种方式
- 如果无法规划替代方案，返回 {{"replacements": []}}
"""


def replan_node(
    llm_client=None,
    model: str = AGENT_DEFAULT_MODEL,
    plan_goal: str = "",
    failed_node_id: str = "",
    failed_step_desc: str = "",
    tool_hint: str = "",
    error_msg: str = "",
    completed_steps: list = None,
    remaining_steps: list = None,
    shared_context_sniff: str = "",
) -> list | None:
    """Generate replacement steps for a failed DAG node using LLM.

    Args:
        llm_client: LLM client for API calls. Required.
        model: LLM model name.
        plan_goal: The overall plan goal.
        failed_node_id: ID of the failed node.
        failed_step_desc: Description of the failed step.
        tool_hint: Expected tool for the step.
        error_msg: Error message from the failure.
        completed_steps: List of (id, desc, brief) tuples for completed steps.
        remaining_steps: List of (id, desc, tool_hint) tuples for remaining steps.
        shared_context_sniff: Pheromone context from completed steps.

    Returns:
        List of replacement node dicts, or None if re-planning is unavailable.
    """
    if not llm_client:
        logging.warning("Adaptive re-plan: no LLM client available, skipping")
        return None

    completed_str = json.dumps(
        [{"id": c[0], "desc": c[1], "brief": c[2]} for c in (completed_steps or [])],
        ensure_ascii=False,
    )
    remaining_str = json.dumps(
        [{"id": r[0], "desc": r[1], "tool_hint": r[2]} for r in (remaining_steps or [])],
        ensure_ascii=False,
    )

    prompt = ADAPTIVE_PROMPT.format(
        plan_goal=plan_goal,
        failed_node_id=failed_node_id,
        failed_step_desc=failed_step_desc,
        tool_hint=tool_hint or "无",
        error_msg=error_msg[:500],
        completed_steps=completed_str,
        remaining_steps=remaining_str,
        shared_context=shared_context_sniff[:1500] or "无",
    )

    from app.util.agent.retry import retry_llm_call

    try:
        resp = retry_llm_call(
            lambda: llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512,
                timeout=20,
            ),
            max_retries=3,
        )
        raw = resp.choices[0].message.content or ""
        text = extract_json(raw)
        if not text:
            logging.warning("Adaptive re-plan: no JSON in response")
            return None

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            repaired = repair_json(text)
            if repaired != text:
                try:
                    data = json.loads(repaired)
                except (json.JSONDecodeError, ValueError):
                    logging.warning("Adaptive re-plan: JSON repair failed")
                    return None
            else:
                return None

        replacements = data.get("replacements", [])
        if not replacements:
            logging.info("Adaptive re-plan: LLM returned empty replacements for node %s", failed_node_id)
            return None

        logging.info("Adaptive re-plan: generated %d replacement steps for node %s", len(replacements), failed_node_id)
        return replacements

    except Exception:
        logging.exception("Adaptive re-plan LLM call failed for node %s", failed_node_id)
        return None
