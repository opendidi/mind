# -*- coding: UTF-8 -*-
"""AgentBase — shared sub-agent class with minimal ReAct loop."""

import hashlib
import json
import logging
import time
from collections import defaultdict

from app.config import LLM_TIMEOUT
from app.util.agent_helpers import estimate_tokens_from_messages as _estimate_tokens

# ── Context budget ────────────────────────────────────────────────────────
MAX_MSG_TOKENS_ESTIMATE = 8000   # soft cap on estimated message tokens
KEEP_LAST_N_ROUNDS = 3           # keep last N tool-interaction rounds on trim
MAX_TOOL_RESULT_CHARS = 800      # per-result truncation


def _truncate_result(result: dict) -> dict:
    """Truncate a tool result dict to prevent context bloat in sub-agents."""
    truncated = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > MAX_TOOL_RESULT_CHARS:
            truncated[k] = v[:MAX_TOOL_RESULT_CHARS] + f"…(截断/{len(v)}字符)"
        elif isinstance(v, list) and len(v) > 5:
            truncated[k] = v[:3] + [f"…(共{len(v)}项/已截断)"]
        elif isinstance(v, dict):
            s = json.dumps(v, ensure_ascii=False)
            if len(s) > MAX_TOOL_RESULT_CHARS:
                truncated[k] = {"_truncated": True, "preview": s[:MAX_TOOL_RESULT_CHARS]}
            else:
                truncated[k] = v
        else:
            truncated[k] = v
    return truncated


class AgentBase:
    """Sub-agent base class. Each sub-agent has its own system prompt and tool subset.

    Sub-agents use a minimal ReAct loop (max 5 iterations, max 3 same-tool repeats).
    """

    name: str = ""
    description: str = ""
    system_prompt: str = ""
    tools: list = []  # list of tool function-calling schema dicts

    MAX_ITERATIONS = 5
    MAX_LOOP_REPEAT = 3  # max consecutive calls to same tool with same args

    def run(
        self,
        llm_client,
        task: str,
        tool_context: dict,
        model: str = "deepseek-chat",
        tracer=None,
        dispatcher=None,
    ) -> dict:
        """Execute a sub-task using a mini ReAct loop with loop detection.

        Args:
            llm_client: LLM client for API calls.
            task: The sub-task description.
            tool_context: Shared context dict (pheromone, redis, etc.).
            model: LLM model name.
            tracer: Optional AgentTracer for span tracking.
            dispatcher: Optional AgentDispatcher for peer query support.

        Returns: {"success": bool, "result": str, "tool_calls_made": int}
        """
        cancel_event = tool_context.get("_cancel_event")

        if tracer:
            sub_sid = tracer.start_span(
                f"sub_agent:{self.name}", input={"task": task[:200]}
            )

        # Mark caller identity so peer queries can prevent self-query
        tool_context["_caller_agent"] = self.name

        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
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

        def _loop_key(tool_name: str, tool_args: dict) -> str:
            args_str = json.dumps(tool_args, ensure_ascii=False, sort_keys=True)
            return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()[:8]}"

        def _finish(success, result):
            if tracer:
                tracer.end_span(
                    sub_sid, "ok" if success else "error", {"result": result[:200]}
                )
            return {
                "success": success,
                "result": result,
                "tool_calls_made": tool_calls_made,
            }

        out_of_context = False

        for _ in range(self.MAX_ITERATIONS):
            # Check cancellation before each iteration
            if cancel_event and cancel_event.is_set():
                logging.warning("Sub-agent %s cancelled mid-execution", self.name)
                return _finish(False, "任务已被取消")

            # Trim context if approaching token budget
            est = _estimate_tokens(messages)
            if est > MAX_MSG_TOKENS_ESTIMATE - 2000 and not out_of_context:
                out_of_context = True
            if est > MAX_MSG_TOKENS_ESTIMATE:
                messages = self._trim_context(messages, KEEP_LAST_N_ROUNDS)
                logging.info(
                    "Sub-agent %s trimmed context: est=%d → %d tokens",
                    self.name, est, _estimate_tokens(messages),
                )

            if tracer:
                llm_sid = tracer.start_span(
                    "llm_call",
                    input={"agent": self.name, "iteration": tool_calls_made + 1},
                )
            try:
                response = llm_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=all_tools if all_tools else None,
                    tool_choice="auto" if all_tools else None,
                    stream=False,
                    timeout=LLM_TIMEOUT,
                )
            except Exception as ex:
                logging.warning("Sub-agent %s LLM call failed: %s", self.name, ex)
                if tracer:
                    tracer.end_span(llm_sid, "error", {"error": str(ex)})
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

                from app.util.agent_tools import run_tool_call

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    lk = _loop_key(tool_name, tool_args)
                    loop_counter[lk] += 1
                    if loop_counter[lk] > self.MAX_LOOP_REPEAT:
                        return _finish(
                            False, f"操作 {tool_name} 重复多次，已停止"
                        )

                    if tracer:
                        tool_sid = tracer.start_span(
                            f"tool:{tool_name}", input=tool_args
                        )
                    t0 = time.time()
                    result, _ = run_tool_call(
                        tool_name, tool_args, tool_context,
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
        first_user = next(
            (m for m in conv_msgs if m["role"] == "user"), None
        )
        if first_user and first_user not in kept:
            kept.insert(0, first_user)

        return system_msgs + kept
