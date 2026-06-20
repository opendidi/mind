# -*- coding: UTF-8 -*-
"""Agent Planner — DAG plan generation for complex multi-step tasks."""

import json
import logging
import random
import time

from app.config import AGENT_DEFAULT_MODEL

PLANNER_PROMPT = """你是任务规划专家。为多步操作生成 DAG 执行计划。

## 输出格式（严格 JSON）
{
  "goal": "一句话目标描述",
  "risk": "low|medium|high",
  "nodes": [
    {
      "id": "s1",
      "desc": "这一步做什么",
      "tool_hint": "工具名或 null",
      "agent_name": "子Agent名或 null",
      "depends_on": [],
      "parallel_group": null,
      "confirm": false
    }
  ]
}

## 规则
- 步骤 2~7 步，简洁明确
- depends_on: 前置步骤 id 列表，空数组=可立即执行
- 无依赖的步骤自动并行执行
- 破坏性操作（删除、清空）: confirm=true
- tool_hint="dispatch_agent" 时 agent_name 必填
- 单步操作用 simple 模式，不需要到这里

## 可用工具
{tools_summary}

## 历史教训
{feedback}
"""


def _build_planner_prompt(tools_summary: str = "", plan_feedback: str = "") -> str:
    tools = tools_summary or "canvas, blueprint, file_search, web_search, code_generate 等"
    feedback = plan_feedback or "无"
    return PLANNER_PROMPT.format(tools_summary=tools, feedback=feedback)


def generate_plan(llm_client, user_message: str, route_result: dict,
                  history: list = None, model: str = AGENT_DEFAULT_MODEL,
                  plan_feedback: str = "", tools_summary: str = "") -> dict:
    """Generate a DAG execution plan for complex tasks.

    Args:
        llm_client: LLM client.
        user_message: User's input.
        route_result: From route_intent().
        history: Recent conversation history.
        model: LLM model name.
        plan_feedback: Feedback from prior plan executions.
        tools_summary: Summary of available tools.

    Returns:
        {"mode": "simple"|"dag", "goal"?: str, "nodes"?: list, "risk"?: str}
    """
    from app.util.agent.helpers import extract_json, repair_json

    # Simple routes don't need planning
    if route_result.get("route") in ("chat", "search"):
        return {"mode": "simple"}

    system_prompt = _build_planner_prompt(tools_summary, plan_feedback)
    msgs = [{"role": "system", "content": system_prompt}]
    if history:
        msgs.extend(history[-6:])
    msgs.append({"role": "user", "content": user_message})

    from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

    for attempt in range(3):
        try:
            resp = llm_client.chat.completions.create(
                model=model, messages=msgs,
                temperature=0.1, max_tokens=1024, timeout=30,
            )
            break
        except (RateLimitError, APITimeoutError, APIConnectionError):
            if attempt >= 2:
                return {"mode": "simple"}
            time.sleep((2 ** attempt) + random.uniform(0, 1))
        except APIError as ex:
            status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
            if status < 500 or attempt >= 2:
                return {"mode": "simple"}
            time.sleep(2 ** attempt)
        except Exception:
            return {"mode": "simple"}

    try:
        raw = resp.choices[0].message.content or ""
        text = extract_json(raw)
        if not text:
            return {"mode": "simple"}

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            repaired = repair_json(text)
            if repaired != text:
                try:
                    data = json.loads(repaired)
                except (json.JSONDecodeError, ValueError):
                    return {"mode": "simple"}
            else:
                return {"mode": "simple"}

        nodes_data = data.get("nodes", [])
        if not nodes_data or len(nodes_data) > 12:
            return {"mode": "simple"}

        nodes = []
        node_ids = set()
        for n in nodes_data:
            nid = n.get("id", f"s{len(nodes)}")
            node_ids.add(nid)
            nodes.append({
                "id": nid,
                "desc": n.get("desc", ""),
                "tool_hint": n.get("tool_hint"),
                "agent_name": n.get("agent_name"),
                "confirm": n.get("confirm", False),
                "depends_on": n.get("depends_on") or [],
                "parallel_group": n.get("parallel_group"),
            })

        # Validate deps
        for n in nodes:
            n["depends_on"] = [d for d in n.get("depends_on", []) if d in node_ids]

        # Cycle check
        from app.util.agent.dag import _has_cycle
        temp_nodes = [
            type("TmpNode", (), {"id": n["id"], "depends_on": set(n["depends_on"])})()
            for n in nodes
        ]
        if _has_cycle(temp_nodes):
            logging.warning("Planner: cycle detected, falling back to simple")
            return {"mode": "simple"}

        return {
            "mode": "dag",
            "goal": data.get("goal", ""),
            "risk": data.get("risk", "low"),
            "nodes": nodes,
        }
    except Exception:
        logging.exception("Planner failed")
        return {"mode": "simple"}
