# -*- coding: UTF-8 -*-
"""AgentBase — shared sub-agent class with minimal ReAct loop."""

import json
import logging
import queue
import time
from collections import defaultdict

from app.config import AGENT_DEFAULT_MODEL, LLM_TIMEOUT
from app.util.agent.helpers import estimate_tokens_from_messages as _estimate_tokens
from app.util.agent.helpers import loop_key as _loop_key
from app.util.agent.helpers import truncate_tool_result as _truncate_result
from app.util.agent.llm_stream import parse_stream_chunks, stream_llm_chat

# ── Context budget ────────────────────────────────────────────────────────
MAX_MSG_TOKENS_ESTIMATE = 8000  # soft cap on estimated message tokens
KEEP_LAST_N_ROUNDS = 3  # keep last N tool-interaction rounds on trim


class AgentBase:
    """Sub-agent base class. Each sub-agent has its own system prompt and tool subset.

    Sub-agents use a minimal ReAct loop (max 5 iterations, max 3 same-tool repeats).
    """

    name: str = ""
    description: str = ""
    system_prompt: str = ""
    tools: list = []  # list of tool function-calling schema dicts

    from app.util.agent.constants import MAX_ITERATIONS, MAX_LOOP_REPEAT

    def run(
        self,
        llm_client,
        task: str,
        tool_context: dict,
        model: str = AGENT_DEFAULT_MODEL,
        tracer=None,
        dispatcher=None,
        event_queue: queue.Queue = None,
        stream: bool = False,
    ) -> dict:
        """Execute a sub-task using a mini ReAct loop with loop detection.

        Args:
            llm_client: LLM client for API calls.
            task: The sub-task description.
            tool_context: Shared context dict (pheromone, redis, etc.).
            model: LLM model name.
            tracer: Optional AgentTracer for span tracking.
            dispatcher: Optional AgentDispatcher for peer query support.
            event_queue: Optional Queue to push progress events.
            stream: If True and event_queue provided, stream tokens to event_queue.

        Returns: {"success": bool, "result": str, "tool_calls_made": int}
        """
        cancel_event = tool_context.get("_cancel_event")

        if tracer:
            sub_sid = tracer.start_span(f"sub_agent:{self.name}", input={"task": task[:200]})

        # Mark caller identity so peer queries can prevent self-query
        tool_context["_caller_agent"] = self.name

        import json as _json

        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        # Inject canvas context for canvas_agent
        canvas_ctx = tool_context.get("_canvas_context")
        if canvas_ctx:
            messages.append(
                {
                    "role": "system",
                    "content": f"## 当前画布状态\n{_json.dumps(canvas_ctx, ensure_ascii=False, indent=2)}",
                }
            )
        # Inject pheromone context (shared discoveries from parent DAG nodes)
        pheromone = tool_context.get("_pheromone", "")
        if pheromone:
            messages.append({"role": "system", "content": f"上下文发现:\n{pheromone}"})
        messages.append({"role": "user", "content": task})

        # Build full tool list: domain tools + peer query (if dispatcher available)
        all_tools = list(self.tools) if self.tools else []
        if dispatcher:
            peer_schema = dispatcher.get_peer_query_tool_schema()
            if peer_schema:
                all_tools.append(peer_schema)

        tool_calls_made = 0
        loop_counter = defaultdict(int)

        def _finish(success, result):
            if tracer:
                tracer.end_span(sub_sid, "ok" if success else "error", {"result": result[:200]})
            return {
                "success": success,
                "result": result,
                "tool_calls_made": tool_calls_made,
            }

        out_of_context = False
        _use_stream = stream and event_queue is not None

        for _ in range(self.MAX_ITERATIONS):
            if cancel_event and cancel_event.is_set():
                logging.warning("Sub-agent %s cancelled mid-execution", self.name)
                return _finish(False, "任务已被取消")

            est = _estimate_tokens(messages)
            if est > MAX_MSG_TOKENS_ESTIMATE - 2000 and not out_of_context:
                out_of_context = True
            if est > MAX_MSG_TOKENS_ESTIMATE:
                messages = self._trim_context(messages, KEEP_LAST_N_ROUNDS)
                logging.info(
                    "Sub-agent %s trimmed context: est=%d → %d tokens",
                    self.name,
                    est,
                    _estimate_tokens(messages),
                )

            if _use_stream:
                # ── Streaming path using shared stream handler ──
                full_text = ""
                has_tool_calls = False
                stream_error = None

                for event in stream_llm_chat(
                    llm_client,
                    model=model,
                    messages=messages,
                    tools=all_tools if all_tools else None,
                    circuit_service=f"{self.name}:{model}",
                    tracer=tracer,
                ):
                    kind = event[0]
                    if kind == "token":
                        full_text += event[1]
                        event_queue.put(("token", event[1]))
                    elif kind == "tool_call":
                        has_tool_calls = True
                        name, tc_id, args_str = event[1], event[2], event[3]
                        try:
                            tool_args = json.loads(args_str)
                        except json.JSONDecodeError:
                            tool_args = {}

                        lk = _loop_key(name, tool_args)
                        loop_counter[lk] += 1
                        if loop_counter[lk] > self.MAX_LOOP_REPEAT:
                            return _finish(False, f"操作 {name} 重复多次，已停止")

                        event_queue.put(("tool_call", name, tool_args))

                        from app.util.agent.tools import run_tool_call

                        if tracer:
                            tool_sid = tracer.start_span(f"tool:{name}", input=tool_args)
                        import time as _time

                        t0 = _time.time()
                        result, _ = run_tool_call(
                            name,
                            tool_args,
                            tool_context,
                            dispatcher=dispatcher,
                            llm_client=llm_client,
                            model=model,
                            tracer=tracer,
                            event_queue=event_queue,
                        )
                        result = _truncate_result(result)
                        duration_ms = (_time.time() - t0) * 1000
                        if tracer:
                            tracer.end_span(
                                tool_sid,
                                "ok" if result.get("success") else "error",
                                {"duration_ms": int(duration_ms)},
                            )
                        tool_calls_made += 1
                        event_queue.put(("tool_result", name, result.get("success", False), result))

                        messages.append(
                            {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": tc_id,
                                        "type": "function",
                                        "function": {"name": name, "arguments": args_str},
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )

                    elif kind == "error":
                        stream_error = event[1]

                if stream_error and not has_tool_calls and not full_text:
                    return _finish(False, f"AI service error: {stream_error}")

                if has_tool_calls:
                    continue  # loop back for next ReAct iteration

                return _finish(True, full_text)

            # ── Non-streaming path with retry ──
            from app.util.agent.retry import retry_llm_call

            llm_sid = None
            if tracer:
                llm_sid = tracer.start_span(
                    "llm_call",
                    input={"agent": self.name, "iteration": tool_calls_made + 1},
                )
            try:
                response = retry_llm_call(
                    lambda: llm_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=all_tools if all_tools else None,
                        tool_choice="auto" if all_tools else None,
                        stream=False,
                        timeout=LLM_TIMEOUT,
                    ),
                    max_retries=3,
                )
            except Exception as ex:
                logging.warning("Sub-agent %s LLM call failed after retries: %s", self.name, ex)
                if tracer:
                    tracer.end_span(llm_sid, "error", {"error": str(ex)[:100]})
                return _finish(False, f"AI service error: {ex}")

            if not response.choices:
                if tracer:
                    tracer.end_span(llm_sid, "error", {"error": "empty response"})
                return _finish(False, "AI returned empty response")

            if tracer:
                tracer.end_span(llm_sid, "ok")
            choice = response.choices[0]
            finish = choice.finish_reason

            if finish == "tool_calls":
                msg = choice.message
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                from app.util.agent.tools import run_tool_call

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    lk = _loop_key(tool_name, tool_args)
                    loop_counter[lk] += 1
                    if loop_counter[lk] > self.MAX_LOOP_REPEAT:
                        return _finish(False, f"操作 {tool_name} 重复多次，已停止")

                    if event_queue is not None:
                        event_queue.put(("tool_call", tool_name, tool_args))

                    if tracer:
                        tool_sid = tracer.start_span(f"tool:{tool_name}", input=tool_args)
                    t0 = time.time()
                    result, _ = run_tool_call(
                        tool_name,
                        tool_args,
                        tool_context,
                        dispatcher=dispatcher,
                        llm_client=llm_client,
                        model=model,
                        tracer=tracer,
                    )
                    result = _truncate_result(result)
                    duration_ms = (time.time() - t0) * 1000
                    if tracer:
                        tracer.end_span(
                            tool_sid,
                            "ok" if result.get("success") else "error",
                            {"duration_ms": int(duration_ms)},
                        )
                    tool_calls_made += 1

                    if event_queue is not None:
                        event_queue.put(("tool_result", tool_name, result.get("success", False), result))

                    logging.info(
                        "Sub-agent %s tool %s: success=%s, %.0fms",
                        self.name,
                        tool_name,
                        result.get("success"),
                        duration_ms,
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue

            # Text response — done
            content = choice.message.content or ""
            return _finish(True, content)

        return _finish(False, "Max iterations reached")

    @staticmethod
    def _trim_context(messages: list, keep_last_n: int = 3) -> list:
        """Trim message history to keep context within budget.

        Preserves: system messages, first user message, and the last N
        tool-interaction rounds (assistant + tool pairs). Drops the oldest
        tool result pairs first.
        """
        if len(messages) <= 4:
            return messages

        # Identify system vs. conversation messages
        system_msgs = [m for m in messages if m["role"] == "system"]
        conv_msgs = [m for m in messages if m["role"] != "system"]

        # Keep last N tool-interaction rounds + any trailing text
        kept = []
        round_count = 0
        for m in reversed(conv_msgs):
            kept.insert(0, m)
            if m["role"] == "tool":
                round_count += 1
                if round_count >= keep_last_n:
                    break

        # Ensure we still have the first user message
        first_user = next((m for m in conv_msgs if m["role"] == "user"), None)
        if first_user and first_user not in kept:
            kept.insert(0, first_user)

        return system_msgs + kept
