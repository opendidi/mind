# -*- coding: UTF-8 -*-
"""
Agent 核心 — V3 统一入口: DAG + Multi-Agent + Tracing + Skills

用法:
  session = AgentSession(user_id)
  for event in session.chat_v3("帮我画一个登录流程图"):
      yield sse_format(event)

架构:
  AgentSession  ── 管理对话历史 + 上下文注入 + Skills 动态加载 + SSE 事件输出
  AgentEngine   ── V3 统一执行引擎（agent_engine.py）
  ToolRegistry  ── 装饰器式工具注册（agent_tools.py）
"""

import json
import logging
import time
from datetime import datetime

from app.util.agent_engine import AgentEngine
from app.util.agent_intent import classify_domain, unified_intent_and_plan
from app.util.agent_skills import get_skills_for_intent
from app.util.llm_client import get_llm_client
from app.util.agent_helpers import estimate_tokens_from_str as _estimate_tokens

MAX_HISTORY_TOKENS = 8000
MAX_HISTORY_COMPACT = 4000


# ── Base Prompt ───────────────────────────────────────────────────────────

BASE_PROMPT = """你是"小M"，一个图形编辑助手。通过工具帮助用户创建和编辑 2D 图表、蓝图和思维导图。

## [!!] 核心铁律（最高优先级）

1. **写操作必须调用工具！** 创建、修改、删除图形等操作绝对不能仅用文字回复。不调用工具就说"已完成"是欺骗用户，绝对禁止。
2. **只看工具结果！** 只有当工具返回 `success: true` 时才报告成功。失败时必须如实告知原因。
3. **没有捷径！** 不存在"告知系统""通知系统"等绕过工具的魔法方式。你唯一执行操作的方式就是调用工具函数。

## 行为准则

- **先看再动** — 操作前先查看当前画布状态（用 canvas_get_state）
- **先规划后执行** — 复杂任务用 `[思考]` 简述步骤（1~2句），再逐步执行
- **确认删除** — 删除图形或清空画布前向用户确认并说明后果
- **不要加戏** — 只执行用户明确要求的操作，不自行扩展
- **失败止损** — 同一操作连续失败 2 次即停止，向用户说明原因
- **主动建议** — 完成操作后可附带一条简短建议

## 回复格式

- 用中文回复，简洁专业，语气友好
- 操作成功 → 简明告知结果
- 操作失败 → 说明原因 + 替代方案

## 支持的图形类型

- rectangle（矩形）、circle（圆形）、triangle（三角形）、diamond（菱形）
- pentagon（五边形）、star（星形）、text（文本）、image（图片）
- 连线类型：straight（直线）、curve（曲线）、polyline（折线）、mind（思维导图线）
- 连线箭头：start/end/both/none

## 思维导图格式 (```mindmap)

输出标准 Markdown 无序列表，每行一项，缩进表示层级：
```mindmap
- 根主题
  - 子主题1
    - 细节A
  - 子主题2
```

## 常见图表类型

- **流程图**：矩形=步骤，菱形=判断，圆形=开始/结束，带箭头连线表示流向
- **架构图**：矩形=组件/服务，连线=依赖/数据流
- **思维导图**：中心主题→分支→细节，使用 mind 曲线连接
"""

# ── Compaction Prompt ────────────────────────────────────────────────────

COMPACT_PROMPT = """将以下对话历史压缩为关键要点摘要（中文，不超过 500 字）。
保留：用户做了什么操作、工具调用结果、重要数据和当前状态。
丢弃：闲聊、重复内容、纯确认性回复。

对话历史:
"""


def _msg_tokens(msg: dict) -> int:
    tokens = _estimate_tokens(msg.get("content", "") or "")
    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        tokens += _estimate_tokens((fn.get("name") or "") + (fn.get("arguments") or ""))
    return tokens


class AgentSession:
    """单次 Agent 会话，管理对话历史与上下文。"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.history: list = []
        self.created_at = time.time()
        self._compact_summary: str = ""

    def _compact_history(self, llm_client, model: str = "deepseek-chat"):
        """LLM-driven context compaction."""
        if not self.history:
            return

        total = sum(_msg_tokens(m) for m in self.history)
        if total <= MAX_HISTORY_COMPACT:
            return

        cumulative = 0
        split_at = 0
        for i, m in enumerate(self.history):
            cumulative += _msg_tokens(m)
            if cumulative >= total * 0.5:
                split_at = i + 1
                break

        if split_at < 2:
            return

        old_msgs = self.history[:split_at]
        recent_msgs = self.history[split_at:]

        compact_lines = []
        for m in old_msgs:
            role = m.get("role", "")
            content = (m.get("content") or "")[:300]
            if role == "user":
                compact_lines.append(f"用户: {content}")
            elif role == "assistant":
                compact_lines.append(f"助手: {content}")
            elif role == "tool":
                compact_lines.append(f"工具结果: {content[:200]}")

        compact_text = "\n".join(compact_lines)
        if not compact_text.strip():
            return

        try:
            resp = llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": COMPACT_PROMPT + compact_text[:3000]}],
                temperature=0.1, max_tokens=400, timeout=15,
            )
            summary = resp.choices[0].message.content or ""
            if summary.strip():
                prev = self._compact_summary
                if prev:
                    merged = f"{prev}\n---\n{summary.strip()}"
                    if len(merged) > 2000:
                        merged = f"...(较早对话已省略)\n{summary.strip()}"
                        if len(merged) > 2000:
                            merged = merged[-2000:]
                    self._compact_summary = merged
                else:
                    self._compact_summary = summary.strip()
                self.history = recent_msgs
                logging.info("Context compacted: %d msgs → summary (%d chars), kept %d recent",
                             len(old_msgs), len(self._compact_summary), len(recent_msgs))
        except Exception:
            logging.warning("Compaction LLM call failed, falling back to truncation", exc_info=True)
            self.history = recent_msgs

    def _trim_history(self):
        """Fallback truncation when compaction isn't possible."""
        if not self.history:
            return
        total = 0
        keep_from = len(self.history)
        for i in range(len(self.history) - 1, -1, -1):
            tokens = _msg_tokens(self.history[i])
            if total + tokens > MAX_HISTORY_TOKENS:
                keep_from = i + 1
                break
            total += tokens
        if keep_from > 0 and keep_from < len(self.history):
            trimmed = self.history[:keep_from]
            if trimmed and trimmed[0]["role"] == "assistant":
                keep_from = max(0, keep_from - 1)
            logging.info("Agent 历史截断：%d → %d 条", len(self.history), len(self.history) - keep_from)
            self.history = self.history[keep_from:]

    def _build_system_prompt(self, user_message: str, canvas_context: dict = None,
                             memory_prompt: str = "", unified_result: dict = None,
                             session_memory: str = "", skill_context: dict = None) -> str:
        """Build a single merged system prompt."""
        now = datetime.now()
        time_hint = (
            f"现在是 {now.year} 年 {now.month} 月 {now.day} 日，"
            f"星期{'一二三四五六日'[now.weekday()]}，北京时间 {now.strftime('%H:%M')}。"
        )

        sections = [BASE_PROMPT, time_hint]

        # Skills — dynamic per intent
        domains = (unified_result or {}).get("domains") or classify_domain(user_message)
        skills_text = get_skills_for_intent(domains, context=skill_context)
        if skills_text:
            sections.append(skills_text)

        # Session memory
        if session_memory:
            sections.append(session_memory)

        # Compaction summary
        if self._compact_summary:
            sections.append(f"## 历史摘要\n{self._compact_summary}")

        # Canvas context (current editor state from frontend)
        if canvas_context:
            sections.append(f"## 当前画布状态\n{json.dumps(canvas_context, ensure_ascii=False, indent=2)}")

        # User memory
        if memory_prompt:
            sections.append(memory_prompt)

        # Write guard
        has_write = (unified_result or {}).get("has_write", False)
        if has_write:
            sections.append("[!] 用户要求执行写操作（创建/修改/删除）。你必须调用工具函数实际完成，不能仅用文字回复。")

        return "\n\n".join(sections)

    def _prepare_messages(self, user_message: str, canvas_context: dict = None,
                          memory_prompt: str = "", llm_client=None,
                          unified_result: dict = None, session_memory: str = "",
                          skill_context: dict = None) -> list:
        """Build the full message list for LLM."""
        system_content = self._build_system_prompt(
            user_message, canvas_context, memory_prompt, unified_result,
            session_memory=session_memory, skill_context=skill_context,
        )
        messages = [{"role": "system", "content": system_content}]

        if llm_client:
            self._compact_history(llm_client)
        else:
            self._trim_history()
        messages.extend(self.history)

        return messages

    # ── V3 API ────────────────────────────────────────────────────────────

    @property
    def _engine(self):
        if not hasattr(self, "_engine_inst"):
            self._engine_inst = AgentEngine(get_llm_client(), self.user_id, "deepseek-chat")
        return self._engine_inst

    def chat_v3(self, user_message: str, canvas_context: dict = None,
                confirm_handler=None, model: str = "deepseek-chat",
                redis_client=None, task_id: str = "", stream: bool = False):
        """V3 unified agent chat — single LLM call for intent+plan, then execute."""
        self.history.append({"role": "user", "content": user_message})

        # ── Restore cross-session memory ──
        session_memory_prompt = ""
        try:
            from app.util.agent_session_memory import SessionMemory
            session_memory_prompt = SessionMemory.restore(self.user_id)
        except Exception:
            logging.debug("SessionMemory restore skipped", exc_info=True)

        # ── Plan-Feedback 闭环 ──
        plan_feedback_hints = ""
        try:
            from app.util.agent_plan_eval import PlanMemory
            tentative_domains = classify_domain(user_message)
            plan_feedback_hints = PlanMemory.get_hints_for_domains(tentative_domains)
            failure_hints = PlanMemory.get_failure_summary(limit=2)
            if failure_hints:
                plan_feedback_hints = plan_feedback_hints + "\n\n" + failure_hints if plan_feedback_hints else failure_hints
        except Exception:
            logging.debug("Plan feedback retrieval skipped", exc_info=True)

        # ── Unified LLM call: intent + domains + plan ──
        unified_result = unified_intent_and_plan(
            self._engine.llm, user_message, self.history[-6:], model,
            plan_feedback_hints=plan_feedback_hints,
        )

        skill_context = {"has_failures": False}

        messages = self._prepare_messages(
            user_message, canvas_context=canvas_context, llm_client=self._engine.llm,
            unified_result=unified_result, session_memory=session_memory_prompt,
            skill_context=skill_context,
        )

        # Delegate to engine
        for event in self._engine.chat(
            user_message=user_message, messages=messages, memory_prompt="",
            confirm_handler=confirm_handler, redis_client=redis_client,
            task_id=task_id, stream=stream,
            precomputed_plan=unified_result.get("plan"),
        ):
            if event[0] == "llm_response":
                choice = event[1]
                tool_count = event[2]
                content = choice.message.content or ""
                self.history.append({"role": "assistant", "content": content})
                if self._engine.llm:
                    self._compact_history(self._engine.llm)
                else:
                    self._trim_history()
                yield {"type": "message", "data": {"text": content, "tool_calls_made": tool_count}}
            else:
                evt = self._translate_event(event)
                if evt is not None:
                    yield evt

        # Persist session memory
        self._persist_session()

    def _translate_event(self, event: tuple) -> dict | None:
        """Translate V3 engine event tuple to SSE dict format."""
        kind = event[0]
        if kind == "token":
            return {"type": "token", "data": {"text": event[1]}}
        elif kind == "tool_call":
            return {"type": "tool_call", "data": {"tool": event[1], "args": event[2]}}
        elif kind == "tool_result":
            return {"type": "tool_result", "data": {"tool": event[1], "success": event[2], "result": event[3]}}
        elif kind == "plan":
            return {"type": "plan", "data": event[1]}
        elif kind == "step_start":
            return {"type": "step_start", "data": event[1]}
        elif kind == "step_end":
            return {"type": "step_end", "data": event[1]}
        elif kind == "step_fail":
            return {"type": "step_fail", "data": event[1]}
        elif kind == "confirm_required":
            return {"type": "confirm_required", "data": event[1]}
        elif kind == "progress":
            return {"type": "progress", "data": event[1]}
        elif kind == "done":
            return {"type": "done", "data": event[1]}
        elif kind == "error":
            return {"type": "error", "data": {"message": event[1]}}
        elif kind == "trace":
            return {"type": "trace", "data": event[1]}
        elif kind == "think":
            return {"type": "thinking", "data": {"content": event[1]}}
        return None

    def clear_history(self):
        self.history = []
        self._compact_summary = ""

    def _persist_session(self):
        """Persist session memory for cross-session continuity."""
        try:
            from app.util.agent_session_memory import SessionMemory
            import uuid
            session_id = str(uuid.uuid4())[:8]
            summary = self._compact_summary if self._compact_summary else ""
            SessionMemory.persist(self.user_id, session_id, self.history, summary)
        except Exception:
            logging.debug("SessionMemory persist skipped", exc_info=True)
