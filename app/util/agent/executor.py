# -*- coding: UTF-8 -*-
"""Agent Executor — shared LLM calling, tool execution with guard, and unified execution facade."""

import json
import logging
import random
import time
from collections import defaultdict
from types import SimpleNamespace
from typing import Generator

from app.config import LLM_TIMEOUT, AGENT_DEFAULT_MODEL
from app.util.agent.guard import InputGuard, ToolGuard, OutputGuard
from app.util.agent.helpers import truncate_tool_result as _truncate_tool_result, loop_key as _loop_key
from app.util.agent.pheromone import extract_discoveries

MAX_LOOP_REPEAT = 3
MAX_REFLECT_RETRIES = 3


class BaseExecutor:
    """Shared LLM calling, tool execution, retry/backoff, and message formatting.

    Extracted from DAGExecutor in agent_dag.py so that both simple-ReAct and
    DAG-parallel paths share the same LLM + tool plumbing.  Guard hooks are
    injected via tool_context so ToolGuard runs before every tool invocation.
    """

    MAX_STEP_MESSAGES = 30

    def __init__(self, llm_client, tools_schemas: list, messages: list, *,
                 tool_context: dict = None, user_id: str = "",
                 model: str = AGENT_DEFAULT_MODEL, confirm_handler=None,
                 dispatcher=None, tracer=None, stream: bool = False,
                 redis_client=None, task_id: str = "", session_id: str = ""):
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

    # ── Guard hook ───────────────────────────────────────────────────────

    def _guard_check_tool(self, tool_name: str, tool_args: dict) -> dict:
        """Called before every tool execution. Override in subclasses."""
        return {"ok": True, "confirm_required": False}

    # ── LLM Calling ──────────────────────────────────────────────────────

    @staticmethod
    def _should_retry_llm(error: Exception, attempt: int) -> bool:
        if attempt >= 2:
            return False
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        if isinstance(error, (RateLimitError, APITimeoutError, APIConnectionError)):
            return True
        if isinstance(error, APIError):
            status = getattr(error, "http_status", None) or getattr(error, "status_code", None) or 500
            return status >= 500
        return True

    @staticmethod
    def _llm_retry_sleep(attempt: int, is_rate_limit: bool = False):
        base = 2 ** attempt
        sleep_s = base + random.uniform(0, 1) if is_rate_limit else base * random.uniform(0.75, 1.25)
        time.sleep(sleep_s)

    def _call_llm(self, messages=None):
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        from app.util.agent.circuit import circuit_allow, circuit_record

        msgs = messages if messages is not None else self.messages
        if not circuit_allow(service=self.model):
            logging.warning("BaseExecutor LLM call blocked by circuit breaker [%s]", self.model)
            return None

        llm_span_id = None
        for attempt in range(3):
            if self.tracer:
                llm_span_id = self.tracer.start_span("llm_api_call", input={"model": self.model, "attempt": attempt + 1})
            try:
                result = self.llm.chat.completions.create(
                    model=self.model, messages=msgs, tools=self.tools,
                    tool_choice="auto", stream=False, timeout=LLM_TIMEOUT,
                )
                circuit_record(True, service=self.model)
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "ok")
                return result
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as ex:
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
                if isinstance(ex, APIError):
                    status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                    if status < 500:
                        circuit_record(False, service=self.model)
                        raise
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt, isinstance(ex, RateLimitError))
            except Exception as ex:
                logging.warning("LLM call attempt %d: %s", attempt + 1, ex)
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt)
        circuit_record(False, service=self.model)
        if self.tracer:
            self.tracer.end_span(llm_span_id, "error", {"error": "All retries exhausted"})
        return None

    def _call_llm_stream(self) -> Generator:
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        from app.util.agent.circuit import circuit_allow, circuit_record

        if not circuit_allow(service=self.model):
            yield ("error", "AI 服务不可用（熔断）")
            return

        for attempt in range(3):
            try:
                response = self.llm.chat.completions.create(
                    model=self.model, messages=self.messages, tools=self.tools,
                    tool_choice="auto", stream=True, timeout=90,
                )
                tool_calls_acc = {}
                full_text = ""
                finish_reason = None

                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason
                    if delta.content:
                        full_text += delta.content
                        yield ("token", delta.content)
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                            acc = tool_calls_acc[idx]
                            if tc_delta.id:
                                acc["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    acc["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    acc["arguments"] += tc_delta.function.arguments
                    if finish_reason:
                        break

                circuit_record(True, service=self.model)

                if finish_reason == "tool_calls" and tool_calls_acc:
                    for idx in sorted(tool_calls_acc.keys()):
                        acc = tool_calls_acc[idx]
                        yield ("llm_tool_call", acc["name"], acc["id"], acc["arguments"])
                    return

                yield ("text_complete", full_text)
                return

            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as ex:
                if isinstance(ex, APIError):
                    status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                    if status < 500:
                        circuit_record(False, service=self.model)
                        yield ("error", f"API 错误: {ex}")
                        return
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt, isinstance(ex, RateLimitError))
            except Exception as ex:
                logging.exception("BaseExecutor: unexpected LLM streaming error: %s", ex)
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt)

        circuit_record(False, service=self.model)
        yield ("error", "LLM 流式调用失败")

    def _call_llm_stream_with_msgs(self, messages: list) -> Generator:
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        from app.util.agent.circuit import circuit_allow, circuit_record

        if not circuit_allow(service=self.model):
            yield ("error", "AI 服务不可用（熔断）")
            return

        for attempt in range(3):
            try:
                response = self.llm.chat.completions.create(
                    model=self.model, messages=messages, tools=self.tools,
                    tool_choice="auto", stream=True, timeout=90,
                )
                tool_calls_acc = {}
                full_text = ""
                finish_reason = None

                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason
                    if delta.content:
                        full_text += delta.content
                        yield ("token", delta.content)
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                            acc = tool_calls_acc[idx]
                            if tc_delta.id:
                                acc["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    acc["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    acc["arguments"] += tc_delta.function.arguments
                    if finish_reason:
                        break

                circuit_record(True, service=self.model)

                if finish_reason == "tool_calls" and tool_calls_acc:
                    for idx in sorted(tool_calls_acc.keys()):
                        acc = tool_calls_acc[idx]
                        yield ("llm_tool_call", acc["name"], acc["id"], acc["arguments"])
                    return

                yield ("text_complete", full_text)
                return

            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as ex:
                if isinstance(ex, APIError):
                    status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                    if status < 500:
                        circuit_record(False, service=self.model)
                        yield ("error", f"API 错误: {ex}")
                        return
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt, isinstance(ex, RateLimitError))
            except Exception as ex:
                logging.exception("BaseExecutor: unexpected LLM streaming error: %s", ex)
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt)

        circuit_record(False, service=self.model)
        yield ("error", "LLM 流式调用失败")

    # ── Tool Execution ───────────────────────────────────────────────────

    def _run_simple_tool(self, tc_name: str, tool_args: dict, tc_id: str) -> dict:
        if self.tracer:
            tool_sid = self.tracer.start_span(f"tool:{tc_name}", input=tool_args)
        t0 = time.time()

        guard = self.tool_context.get("_guard_check")
        if guard:
            gr = guard(tc_name, tool_args)
            if not gr.get("ok", True):
                return {"success": False, "error": gr.get("reason", "工具调用被安全策略拦截")}

        from app.util.agent.tools import run_tool_call

        result, _ = run_tool_call(tc_name, tool_args, self.tool_context,
                                  self.dispatcher, self.llm, self.model, self.tracer,
                                  "", event_queue=None)
        if self.tracer:
            self.tracer.end_span(tool_sid, "ok" if result.get("success") else "error",
                                 {"duration_ms": int((time.time() - t0) * 1000)})

        self._tool_call_count += 1

        truncated = _truncate_tool_result(result)
        self.messages.append({"role": "tool", "tool_call_id": tc_id,
                              "content": json.dumps(truncated, ensure_ascii=False)})

        if self.shared_context is not None:
            discoveries = extract_discoveries(tc_name, tool_args, result)
            for k, v in discoveries.items():
                self.shared_context.deposit(k, v, source_node="simple", source_tool=tc_name)

        return result

    def _run_dag_tool(self, tc_name: str, tool_args: dict, tc_id: str,
                      messages: list, event_queue=None, node_id: str = "") -> dict:
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

        from app.util.agent.tools import run_tool_call

        pheromone = ""
        if self.shared_context is not None:
            pheromone = self.shared_context.sniff()

        result, _ = run_tool_call(tc_name, tool_args, self.tool_context,
                                  self.dispatcher, self.llm, self.model, self.tracer,
                                  pheromone, event_queue=event_queue)
        if self.tracer:
            self.tracer.end_span(tool_sid, "ok" if result.get("success") else "error",
                                 {"duration_ms": int((time.time() - t0) * 1000)})

        self._tool_call_count += 1

        if event_queue is not None:
            event_queue.put(("tool_result", tc_name, result.get("success", False), result, node_id))

        truncated = _truncate_tool_result(result)
        messages.append({"role": "tool", "tool_call_id": tc_id,
                         "content": json.dumps(truncated, ensure_ascii=False)})

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
            tool_msgs.append({
                "id": tc_id, "type": "function",
                "function": {"name": tc_name, "arguments": tc_args_str},
            })
        return {"role": "assistant", "content": "", "tool_calls": tool_msgs}

    @staticmethod
    def _format_assistant_msg(msg) -> dict:
        return {
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                           for tc in (msg.tool_calls or [])],
        }

    def _append_simple_retry_msg(self, tool_calls_received: list, retries: int,
                                  search_missing_keyword: bool = False):
        failed_names = {tc[0] for tc in tool_calls_received}
        if failed_names & {"web_search", "web_fetch"}:
            if search_missing_keyword:
                self.messages.append({"role": "user", "content": (
                    "web_search 需要 keyword 参数。请从用户的问题中提取搜索关键词，重新调用 web_search。"
                    "例如用户问\"有什么新闻\"，keyword 应填 \"新闻\" 或 \"今日新闻\"。不要传空参数。"
                )})
            else:
                self.messages.append({"role": "user", "content": (
                    "搜索工具暂时不可用。请直接用你自身的知识回答用户的问题，不需要再尝试搜索。直接给出文字回复即可。"
                )})
        else:
            self.messages.append({"role": "user", "content": (
                f"上一步工具执行失败了。请分析错误原因，尝试用不同的参数或方法重试。（第 {retries}/{MAX_REFLECT_RETRIES} 次重试）"
            )})

    def _trim_step_messages(self, messages=None):
        msgs = messages if messages is not None else self.messages
        if len(msgs) <= self.MAX_STEP_MESSAGES:
            return
        system_msgs = [m for m in msgs if m.get("role") == "system"]
        other_msgs = [m for m in msgs if m.get("role") != "system"]
        keep_other = self.MAX_STEP_MESSAGES - len(system_msgs)
        keep_other = max(keep_other, min(10, len(other_msgs)))
        msgs[:] = system_msgs + other_msgs[-keep_other:]


class AgentExecutor:
    """Public executor facade with full guardrail integration.

    Used by AgentEngine. Wraps DAGExecutor with:
    - InputGuard: validates user messages at the boundary
    - ToolGuard: validates every tool call before execution (via _guard_check_tool)
    - OutputGuard: sanitizes AI text responses before they reach the user
    """

    def __init__(self, llm_client, tools_schemas: list, messages: list, *,
                 tool_context: dict = None, user_id: str = "",
                 model: str = AGENT_DEFAULT_MODEL, confirm_handler=None,
                 dispatcher=None, tracer=None, stream: bool = False,
                 redis_client=None, task_id: str = "", session_id: str = ""):
        self._session_id = session_id or task_id or user_id

        # Inject guard hook into tool_context so DAGExecutor calls it per tool
        ctx = dict(tool_context or {})
        if redis_client:
            ctx["_redis"] = redis_client
            ctx["_task_id"] = task_id
        ctx["_guard_check"] = self._guard_check_tool
        ctx["_session_id"] = self._session_id

        # Lazy import to avoid circular dependency (agent_dag imports BaseExecutor from here)
        from app.util.agent.dag import DAGExecutor
        self._dag = DAGExecutor(
            llm_client, tools_schemas, messages,
            tool_context=ctx, user_id=user_id, model=model,
            confirm_handler=confirm_handler, dispatcher=dispatcher,
            tracer=tracer, stream=stream, redis_client=redis_client,
            task_id=task_id,
        )

    def _guard_check_tool(self, tool_name: str, tool_args: dict) -> dict:
        return ToolGuard.check_tool_call(tool_name, tool_args, self._session_id)

    def execute(self, plan) -> Generator:
        """Execute a DAGPlan (simple or dag mode) with guardrails on tool calls."""
        yield from self._dag.execute(plan)

    @property
    def tool_call_count(self):
        return self._dag.tool_call_count

    @classmethod
    def reset_guard(cls, session_id: str):
        """Reset ToolGuard counters for a session."""
        ToolGuard.reset_session(session_id)
