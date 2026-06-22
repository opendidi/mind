# -*- coding: UTF-8 -*-
"""Agent intent classification — unified LLM-based intent+domain+plan + keyword fallback.
Adapted for mind: canvas/blueprint/file/mindmap/code domains."""

import json
import logging
from app.config import AGENT_DEFAULT_MODEL

# ═══════════════════════════════════════════════════════════
# Keyword lists — shared by _keyword_fallback and classify_domain
# ═══════════════════════════════════════════════════════════

_WRITE_KEYWORDS = [
    "创建", "新建", "添加", "增加", "加入", "加上",
    "删除", "移除", "去掉", "清空", "删掉",
    "修改", "更改", "更新", "编辑", "调整", "改成",
    "复制", "拷贝", "生成", "制作", "设置", "配置",
    "帮我加", "帮我做", "帮我创建", "帮我弄", "帮我搞",
    "加一个", "加个", "建一个", "做一个", "弄一个",
    "画", "画一个", "绘制", "画出", "添加节点", "添加连线",
    "保存", "导出", "加载", "打开",
]

_TOOL_KEYWORDS = _WRITE_KEYWORDS + [
    "查看", "列出", "搜索", "分析", "显示", "展示",
    "list", "show", "get", "search", "find", "view",
    "look", "describe", "analyze", "check", "read", "fetch",
    "create", "delete", "update", "modify", "remove", "add",
    "画布", "图形", "节点", "蓝图", "文件", "素材",
    "布局", "排列", "对齐", "导出", "保存", "加载",
]


# ── Domain Classification (for Skill-based prompt injection) ─────────────

_DOMAIN_KEYWORDS = {
    "canvas": [
        "图形", "画布", "节点", "连线", "箭头", "创建", "添加", "删除",
        "修改", "编辑", "绘制", "画", "流程图", "架构图", "思维导图",
        "布局", "对齐", "矩形", "圆形", "三角形", "菱形", "文本",
        "pen", "canvas", "形状", "线", "曲线", "折线",
        "排列", "移动", "调整", "大小", "颜色", "背景",
        "画一个", "画个", "加一个", "加个",
    ],
    "blueprint": [
        "蓝图", "保存", "加载", "打开", "导出", "下载",
        "PNG", "SVG", "JSON", "blueprint", "另存为",
        "保存为", "导出为", "下载为",
    ],
    "file": [
        "文件", "素材", "图片", "上传", "文件夹", "目录",
        "文件管理", "资源", "图库", "素材库",
        "excel", "xls", "xlsx", "表格", "数据", "图表", "chart",
        "分析数据", "数据分析", "统计", "报表", "csv",
    ],
    "mindmap": [
        "思维导图", "脑图", "导图", "mindmap", "mind map",
        "大纲", "分支", "子主题",
    ],
    "code": [
        "代码", "脚本", "JS", "JSON", "编辑器", "Monaco",
        "生成代码", "写代码", "JavaScript",
    ],
}


def classify_domain(message: str) -> list[str]:
    """Fast keyword-based domain classification for skill injection.

    Returns a list of domain tags like ["canvas", "blueprint"].
    Falls back to ["general"] when no keywords match.
    """
    msg = message.lower()
    tags = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in message or kw.lower() in msg for kw in keywords):
            tags.append(domain)
    return tags if tags else ["general"]


# ── Unified Intent + Plan (merged LLM call) ──────────────────────────────────

UNIFIED_INTENT_PLAN_PROMPT = """你是任务分类与规划专家。分析用户请求，一次性输出 intent 分类 + DAG 执行计划。

## [!!] 第一步：判断是否需要工具

| 用户意图 | 判断 | 输出 |
|---------|------|------|
| 实时信息查询（新闻/天气/最新） | 时效性问题，需要搜索 | `{"intent": "tool", "domains": [], "has_write": false, "plan": {"mode": "simple"}}` |
| 闲聊、问候、常识问答 | 不需要工具 | `{"intent": "chat", "domains": [], "has_write": false, "plan": {"mode": "simple"}}` |
| 查看画布状态 | 只需查询 | `{"intent": "tool", "domains": ["canvas"], "has_write": false, "plan": {"mode": "simple"}}` |
| 图形编辑/蓝图管理/文件操作 | 需要工具执行 | 输出完整 dag/tool 计划 |

典型的 **chat** 类问题（直接输出 simple）："你好""Python 怎么学""解释一下机器学习""推荐几本书"
典型的 **实时查询**（tool + simple）："有什么新闻""今天天气怎么样""最新 AI 进展""最近发生的XX"
典型的 **tool** 类问题（需要规划）："画一个流程图""删除那个矩形""保存当前画布"

## 输出格式（严格 JSON，不要输出其他文字）

对于纯对话/知识问答（不需要工具），返回:
{"intent": "chat", "domains": [], "has_write": false, "plan": {"mode": "simple"}}

对于需要工具操作的请求，返回:
{
  "intent": "tool",
  "domains": ["canvas", "blueprint", "file", "mindmap", "code"],
  "has_write": false,
  "plan": {
    "mode": "dag",
    "goal": "一句话目标描述",
    "risk": "low|medium|high",
    "nodes": [
      {
        "id": "s1",
        "desc": "这一步做什么",
        "tool_hint": "工具名、dispatch_agent、或 null",
        "agent_name": "子Agent名或null",
        "depends_on": [],
        "parallel_group": null,
        "confirm": false
      }
    ]
  }
}

## 规则
- intent: "chat"=纯对话无需工具, "tool"=需要调用工具
- [!] 用户问"新闻""天气""知识""推荐""教程""怎么学"等与图形编辑无关的内容 → 一定是 chat/simple
- domains: 涉及的领域标签，从 [canvas, blueprint, file, mindmap, code] 中选择
- has_write: 用户要求创建/修改/删除数据时为 true
- depends_on 为前置步骤 id 列表，空数组=可立即执行
- 无依赖关系的步骤自动并行执行
- 破坏性操作（删除、清空画布）: confirm=true
- tool_hint="dispatch_agent" 时，agent_name 必填（canvas_agent/blueprint_agent/file_agent/code_agent）
- 步骤 2~7 步，简洁明确
- 只有真正需要多步操作的才用 dag 模式，单步操作用 mode="simple"
- [!] 知识优先：历史/百科/常识等纯知识问答，模型自身知识已足够，优先用 mode="simple"
- [!] 画布状态已在上下文中提供，仅在确实需要确认状态变更时才查询
- [!] 如果历史教训中有相关反馈，优先参考并调整计划以避免重复已知错误
"""

# Dynamic suffix appended to the planner prompt when feedback hints are available
PLANNER_FEEDBACK_SUFFIX = """

{feedback_text}

请在规划时考虑以上历史教训，调整步骤设计以避免已知问题。"""


def _build_planner_prompt(plan_feedback_hints: str = "") -> str:
    """Build the full planner system prompt with optional feedback injection."""
    prompt = UNIFIED_INTENT_PLAN_PROMPT
    if plan_feedback_hints and plan_feedback_hints.strip():
        prompt += PLANNER_FEEDBACK_SUFFIX.format(feedback_text=plan_feedback_hints)
    return prompt


def unified_intent_and_plan(
    llm_client,
    user_message: str,
    history: list = None,
    model: str = AGENT_DEFAULT_MODEL,
    plan_feedback_hints: str = "",
) -> dict:
    """Single LLM call for intent classification + domain detection + DAG plan generation.

    Args:
        llm_client: LLM client for API calls.
        user_message: The user's current input.
        history: Recent conversation history for context.
        model: LLM model name.
        plan_feedback_hints: Optional feedback text from prior plan executions
                             to inject into the planner prompt (Plan-Feedback 闭环).

    Returns dict: {intent, domains, has_write, plan: {mode, goal?, nodes?, risk?}}
    Falls back to keyword matching on LLM failure.
    """
    import json as _json

    from app.util.agent.helpers import extract_json as _extract_json, repair_json as _repair_json
    from app.util.agent.retry import retry_llm_call

    # Build messages for single LLM call with optional feedback injection
    system_prompt = _build_planner_prompt(plan_feedback_hints)
    msgs = [{"role": "system", "content": system_prompt}]
    if history:
        msgs.extend(history[-6:])
    msgs.append({"role": "user", "content": user_message})

    try:
        resp = retry_llm_call(
            lambda: llm_client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=0.1,
                max_tokens=1024,
                timeout=30,
            ),
            max_retries=3,
        )
    except Exception:
        logging.warning("unified_intent: LLM call failed after retries, falling back to keyword")
        return _keyword_fallback(user_message)
    try:
        raw = resp.choices[0].message.content or ""
        text = _extract_json(raw)
        if not text:
            logging.warning("unified_intent: no JSON in response")
            return _keyword_fallback(user_message)

        try:
            data = _json.loads(text)
        except (_json.JSONDecodeError, ValueError):
            repaired = _repair_json(text)
            if repaired != text:
                try:
                    data = _json.loads(repaired)
                    logging.info("unified_intent: JSON repaired successfully")
                except (_json.JSONDecodeError, ValueError):
                    logging.warning("unified_intent: JSON repair failed, raw: %.200s", raw[:200])
                    return _keyword_fallback(user_message)
            else:
                logging.warning("unified_intent: JSON parse failed, raw: %.200s", raw[:200])
                return _keyword_fallback(user_message)
        out: dict = {
            "intent": data.get("intent", "chat"),
            "domains": data.get("domains") or [],
            "has_write": data.get("has_write", False),
            "plan": {
                "mode": "simple",
            },
        }

        plan_data = data.get("plan") or {}
        plan_mode = plan_data.get("mode", "simple")
        out["plan"]["mode"] = plan_mode

        if plan_mode == "dag":
            out["plan"]["goal"] = plan_data.get("goal", "")
            out["plan"]["risk"] = plan_data.get("risk", "low")
            nodes = []
            node_ids = set()
            for n in plan_data.get("nodes", []):
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

            # Validate deps（兼容 LLM 可能返回 null/None 的情况）
            for n in nodes:
                deps = n.get("depends_on") or []
                n["depends_on"] = [d for d in deps if d in node_ids]

            # Cycle check
            from app.util.agent.dag import _has_cycle
            temp_nodes = [
                type("TmpNode", (), {
                    "id": n["id"],
                    "depends_on": set(n["depends_on"]),
                })()
                for n in nodes
            ]
            if _has_cycle(temp_nodes):
                logging.warning("unified_intent: cycle detected, falling back to simple")
                out["plan"]["mode"] = "simple"
                return out

            out["plan"]["nodes"] = nodes

        return out

    except Exception:
        logging.warning("unified_intent failed, keyword fallback", exc_info=True)
        return _keyword_fallback(user_message)


def _keyword_fallback(user_message: str) -> dict:
    """Fast keyword-based fallback when LLM is unavailable."""
    tool = any(kw in user_message for kw in _TOOL_KEYWORDS)
    write = any(kw in user_message for kw in _WRITE_KEYWORDS)
    domains = classify_domain(user_message)
    if domains == ["general"]:
        domains = []
    return {
        "intent": "tool" if tool else "chat",
        "domains": domains,
        "has_write": write,
        "plan": {"mode": "simple"},
    }
