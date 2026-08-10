# -*- coding: UTF-8 -*-
"""Base Executor — shared LLM calling, tool execution with guard, retry/backoff, and message formatting.

Extracted from executor.py to break the circular dependency between executor.py and dag.py.
Both DAGExecutor (dag.py) and AgentExecutor (executor.py) depend on this module — neither imports
the other at module level, eliminating the fragile lazy-import ordering.
"""

import json
import logging
import time
from collections import defaultdict
from types import SimpleNamespace
from typing import Generator

from app.config import AGENT_DEFAULT_MODEL, LLM_TIMEOUT
from app.util.agent.constants import MAX_LOOP_REPEAT, MAX_REFLECT_RETRIES
from app.util.agent.guard import InputGuard, OutputGuard, ToolGuard
from app.util.agent.helpers import loop_key as _loop_key
from app.util.agent.helpers import truncate_tool_result as _truncate_tool_result
from app.util.agent.llm_stream import parse_stream_chunks, stream_llm_chat
from app.util.agent.pheromone import extract_discoveries


class BaseExecutor:
    """Shared LLM calling, tool execution, retry/backoff, and message formatting.

    Extracted from DAGExecutor in agent_dag.py so that both simple-ReAct and
    DAG-parallel paths share the same LLM + tool plumbing.  Guard hooks are
    injected via tool_context so ToolGuard runs before every tool invocation.
    """

    MAX_STEP_MESSAGES = 30

    def __init__(
        self,
        llm_client,
        tools_schemas: list,
        messages: list,
        *,
        tool_context: dict = None,
        user_id: str = "",
        model: str = AGENT_DEFAULT_MODEL,
        confirm_handler=None,
        dispatcher=None,
        tracer=None,
        stream: bool = False,
        redis_client=None,
        task_id: str = "",
        session_id: str = "",
    ):
        self.llm = llm_client
        self.tools = tools_schemas
        self.messages = messages
        self.user_id = user_id
        self.model = model
        self.tracer = tracer
        self.dispatcher = dispatcher
        self.stream = stream
        self.confirm_handler = confirm_handler

        ctx = dict(tool_context or {})
        if redis_client:
            ctx["_redis"] = redis_client
            ctx["_task_id"] = task_id
        ctx["_guard_check"] = self._guard_check_tool
        ctx["_session_id"] = session_id or task_id or user_id
        self.tool_context = ctx

        self._tool_call_count = 0
        self.shared_context = None  # set by DAGExecutor / pheromone system
        self._critic_hints = ""  # quality requirements injected by CriticAgent

    # ── Guard hook ───────────────────────────────────────────────────────

    def _guard_check_tool(self, tool_name: str, tool_args: dict) -> dict:
        """Called before every tool execution. Override in subclasses."""
        return {"ok": True, "confirm_required": False}

    # ── LLM Calling ──────────────────────────────────────────────────────

    def _call_llm(self, messages=None):
        from app.util.agent.circuit import circuit_allow, circuit_record
        from app.util.agent.retry import retry_llm_call

        msgs = messages if messages is not None else self.messages
        if not circuit_allow(service=self.model):
            logging.warning("BaseExecutor LLM call blocked by circuit breaker [%s]", self.model)
            return None

        llm_span_id = None
        if self.tracer:
            llm_span_id = self.tracer.start_span("llm_api_call", input={"model": self.model})
        try:
            result = retry_llm_call(
                lambda: self.llm.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    tools=self.tools,
                    tool_choice="auto",
                    stream=False,
                    timeout=LLM_TIMEOUT,
                ),
                max_retries=3,
            )
            circuit_record(True, service=self.model)
            if self.tracer:
                self.tracer.end_span(llm_span_id, "ok")
            return result
        except Exception as ex:
            circuit_record(False, service=self.model)
            if self.tracer:
                self.tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
            from app.util.agent.retry import should_retry_llm

            if should_retry_llm(ex):
                logging.error("LLM 调用最终失败（已重试 3 次）: %s", ex)
            else:
                logging.error("LLM 调用不可重试失败: %s", ex)
            raise  # Let caller decide how to present the error

    def _call_llm_stream(self) -> Generator:
        """Streaming LLM call using self.messages. Delegates to shared handler."""
        yield from self._call_llm_stream_with_msgs(self.messages)

    def _call_llm_stream_with_msgs(self, messages: list) -> Generator:
        """Streaming LLM call with custom messages. Uses shared stream handler."""
        # Adapt shared stream events to legacy event format for compatibility
        for event in stream_llm_chat(
            self.llm,
            model=self.model,
            messages=messages,
            tools=self.tools,
            circuit_service=self.model,
            tracer=self.tracer,
        ):
            kind = event[0]
            if kind == "token":
                yield ("token", event[1])
            elif kind == "tool_call":
                # stream_llm_chat: ("tool_call", name, id, args)
                # legacy format:  ("llm_tool_call", name, id, args)
                yield ("llm_tool_call", event[1], event[2], event[3])
            elif kind == "finish":
                yield ("text_complete", event[2])
            elif kind == "error":
                yield ("error", event[1])

    # ── Tool Execution ───────────────────────────────────────────────────

    def _overflow_store(self, full_text: str, label: str = "") -> str | None:
        """Store large tool result in Redis to prevent context bloat.

        Manus-inspired: file system as extended context.
        Returns a reference key that downstream tools can use to retrieve the data.
        """
        redis_client = self.tool_context.get("_redis")
        if not redis_client:
            return None
        try:
            import hashlib
            import random

            suffix = hashlib.md5(full_text[:200].encode()).hexdigest()[:8]
            key = f"overflow:{self.tool_context.get('_task_id', 'unknown')}:{suffix}:{random.randint(0, 9999)}"
            redis_client.setex(key, 1800, full_text)  # 30 min TTL
            label_str = f" ({label})" if label else ""
            return f"[数据已存档: {key}, 大小={len(full_text)}字符{label_str}。如需详细内容请告知系统。]"
        except Exception:
            return None

    def _overflow_truncated_result(self, original: dict, truncated: dict) -> dict:
        """Post-process truncation: store full values that were truncated, replace with refs."""
        result = dict(truncated)
        overflow_keys = []
        for k, v in result.items():
            if isinstance(v, str) and "…(截断/" in v:
                full = original.get(k)
                if full and isinstance(full, str):
                    ref = self._overflow_store(full, k)
                    if ref:
                        result[k] = ref
                        overflow_keys.append(k)
        if overflow_keys:
            result["_overflow_keys"] = overflow_keys
        return result

    def _run_simple_tool(self, tc_name: str, tool_args: dict, tc_id: str) -> dict:
        if self.tracer:
            tool_sid = self.tracer.start_span(f"tool:{tc_name}", input=tool_args)
        t0 = time.time()

        guard = self.tool_context.get("_guard_check")
        if guard:
            gr = guard(tc_name, tool_args)
            if not gr.get("ok", True):
                return {"success": False, "error": gr.get("reason", "工具调用被安全策略拦截")}

        # Inject canvas shadow into tool args for cross-turn ID validation
        if "_canvas_shadow" in self.tool_context:
            tool_args["_canvas_shadow"] = self.tool_context["_canvas_shadow"]

        from app.util.agent.tools import run_tool_call

        result, _ = run_tool_call(
            tc_name,
            tool_args,
            self.tool_context,
            self.dispatcher,
            self.llm,
            self.model,
            self.tracer,
            "",
            event_queue=None,
        )
        if self.tracer:
            self.tracer.end_span(
                tool_sid, "ok" if result.get("success") else "error", {"duration_ms": int((time.time() - t0) * 1000)}
            )

        self._tool_call_count += 1

        truncated = _truncate_tool_result(result)
        truncated = self._overflow_truncated_result(result, truncated)
        self.messages.append(
            {"role": "tool", "tool_call_id": tc_id, "content": json.dumps(truncated, ensure_ascii=False)}
        )

        if self.shared_context is not None:
            discoveries = extract_discoveries(tc_name, tool_args, result)
            for k, v in discoveries.items():
                self.shared_context.deposit(k, v, source_node="simple", source_tool=tc_name)

        return result

    def _run_dag_tool(
        self, tc_name: str, tool_args: dict, tc_id: str, messages: list, event_queue=None, node_id: str = ""
    ) -> dict:
        if self.tracer:
            tool_sid = self.tracer.start_span(f"tool:{tc_name}", input=tool_args)
        t0 = time.time()

        guard = self.tool_context.get("_guard_check")
        if guard:
            gr = guard(tc_name, tool_args)
            if not gr.get("ok", True):
                return {"success": False, "error": gr.get("reason", "工具调用被安全策略拦截")}

        if event_queue is not None:
            event_queue.put(("tool_call", tc_name, tool_args, node_id))

        # Inject canvas shadow into tool args for cross-turn ID validation
        if "_canvas_shadow" in self.tool_context:
            tool_args["_canvas_shadow"] = self.tool_context["_canvas_shadow"]

        from app.util.agent.tools import run_tool_call

        pheromone = ""
        if self.shared_context is not None:
            pheromone = self.shared_context.sniff()

        result, _ = run_tool_call(
            tc_name,
            tool_args,
            self.tool_context,
            self.dispatcher,
            self.llm,
            self.model,
            self.tracer,
            pheromone,
            event_queue=event_queue,
        )
        if self.tracer:
            self.tracer.end_span(
                tool_sid, "ok" if result.get("success") else "error", {"duration_ms": int((time.time() - t0) * 1000)}
            )

        self._tool_call_count += 1

        if event_queue is not None:
            event_queue.put(("tool_result", tc_name, result.get("success", False), result, node_id))

        truncated = _truncate_tool_result(result)
        truncated = self._overflow_truncated_result(result, truncated)
        messages.append({"role": "tool", "tool_call_id": tc_id, "content": json.dumps(truncated, ensure_ascii=False)})

        if self.shared_context is not None:
            discoveries = extract_discoveries(tc_name, tool_args, result)
            for k, v in discoveries.items():
                self.shared_context.deposit(k, v, source_node=node_id, source_tool=tc_name)

        return result

    # ── Message Formatting ───────────────────────────────────────────────

    @staticmethod
    def _format_stream_tool_msg(tool_calls_received: list) -> dict:
        tool_msgs = []
        for tc_name, tc_id, tc_args_str in tool_calls_received:
            tool_msgs.append(
                {
                    "id": tc_id,
                    "type": "function",
                    "function": {"name": tc_name, "arguments": tc_args_str},
                }
            )
        return {"role": "assistant", "content": "", "tool_calls": tool_msgs}

    @staticmethod
    def _format_assistant_msg(msg) -> dict:
        return {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in (msg.tool_calls or [])
            ],
        }

    def _append_simple_retry_msg(self, tool_calls_received: list, retries: int, search_missing_keyword: bool = False):
        failed_names = {tc[0] for tc in tool_calls_received}
        if failed_names & {"web_search", "web_fetch"}:
            if search_missing_keyword:
                self.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[!] web_search 需要 keyword 参数。请从用户的问题中提取搜索关键词，重新调用。"
                            '例如用户问"有什么新闻"，keyword 应填 "新闻" 或 "今日新闻"。不要传空参数。'
                        ),
                    }
                )
            else:
                self.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[!] 搜索工具暂时不可用。请直接用你自身的知识回答用户的问题，不需要再尝试搜索。直接给出文字回复即可。"
                        ),
                    }
                )
        else:
            # 错误保留原则（Manus-inspired）：保留失败详情在上下文中，
            # 让模型观察错误模式自我修正，而非仅靠外部 reflexion 分析。
            tc_names = ", ".join(sorted(failed_names))
            self.messages.append(
                {
                    "role": "user",
                    "content": (
                        f"[!] 工具 {tc_names} 执行失败（第 {retries}/{MAX_REFLECT_RETRIES} 次重试）\n"
                        f"请分析错误原因，尝试用不同的参数或方法重试。不要重复相同的失败调用。\n"
                        f"如果多次重试仍失败，请告知用户具体原因并建议替代方案。"
                    ),
                }
            )

    def _trim_step_messages(self, messages=None):
        msgs = messages if messages is not None else self.messages
        if len(msgs) <= self.MAX_STEP_MESSAGES:
            return
        system_msgs = [m for m in msgs if m.get("role") == "system"]
        other_msgs = [m for m in msgs if m.get("role") != "system"]
        keep_other = self.MAX_STEP_MESSAGES - len(system_msgs)
        keep_other = max(keep_other, min(10, len(other_msgs)))
        msgs[:] = system_msgs + other_msgs[-keep_other:]
