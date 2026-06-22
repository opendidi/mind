# -*- coding: UTF-8 -*-
"""AgentEngine — unified V3 entry point that ties DAG + Multi-Agent + Guard + Tracing together."""

from typing import Generator

import app.util.search  # noqa: F401 — registers web_search tool via ToolRegistry
from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.dag import DAGNode, DAGPlan
from app.util.agent.dispatcher import AgentDispatcher
from app.util.agent.executor import AgentExecutor
from app.util.agent.guard import InputGuard, OutputGuard
from app.util.agent.tools import TOOL_SCHEMAS, _rebuild_schemas
from app.util.agent.tracer import AgentTracer

# Rebuild after search module registers additional tools
_rebuild_schemas()


def _apply_output_guard(text):
    """Apply OutputGuard to text. Returns (guard_out_dict_or_None, sanitized_text_or_None)."""
    guard_out = OutputGuard.process(text)
    if not guard_out["ok"]:
        return guard_out, None
    return None, guard_out.get("text", text)


class AgentEngine:
    """V3 unified execution engine with guardrails.

    1. InputGuard validates user input at the boundary
    2. Intent + plan from unified_intent_and_plan() (called upstream in AgentSession)
    3. Simple chat → single-round ReAct; Complex → DAG parallel execution
    4. Sub-agents dispatched via AgentDispatcher as a tool
    5. OutputGuard sanitizes AI responses before user delivery
    6. Full lifecycle traced via AgentTracer
    """

    def __init__(self, llm_client, user_id: str, model: str = AGENT_DEFAULT_MODEL):
        self.llm = llm_client
        self.user_id = user_id
        self.model = model
        self.dispatcher = AgentDispatcher()

    def chat(
        self,
        user_message: str,
        messages: list,
        pano_id: str = None,
        memory_prompt: str = "",
        confirm_handler=None,
        redis_client=None,
        task_id: str = "",
        stream: bool = False,
        precomputed_plan: dict = None,
    ) -> Generator:
        """Unified V3 chat entry point with guardrails.

        Args:
            user_message: current user input
            messages: full message list (system prompts + history + user msg)
            pano_id: unused (kept for API compatibility)
            memory_prompt: injected memory context string
            confirm_handler: callable(action, details) → bool for human-in-the-loop
            redis_client: Redis client for tool context
            task_id: unique task ID for Redis key namespacing
            stream: if True, callers receive token events inline
            precomputed_plan: plan dict from unified_intent_and_plan(). Required.

        Yields:
            SSE-compatible event tuples: (type, data)
        """
        tracer = AgentTracer(user_id=self.user_id)
        session_id = task_id or self.user_id

        with tracer.span("agent_chat", user_id=self.user_id):
            # ── Input Guard ──
            guard_result = InputGuard.check(user_message)
            if not guard_result["ok"]:
                yield ("error", guard_result.get("reason", "输入被安全策略拦截"))
                yield ("done", {"status": "blocked"})
                return

            # Build tool list
            full_tools = list(TOOL_SCHEMAS)
            dispatch_schema = self.dispatcher.get_dispatch_tool_schema()
            if dispatch_schema:
                full_tools.append(dispatch_schema)

            tool_ctx = {"user_id": self.user_id}
            if redis_client:
                tool_ctx["_redis"] = redis_client
                tool_ctx["_task_id"] = task_id

            # Create guarded executor
            executor = AgentExecutor(
                self.llm,
                full_tools,
                messages,
                tool_context=tool_ctx,
                user_id=self.user_id,
                model=self.model,
                confirm_handler=confirm_handler,
                dispatcher=self.dispatcher,
                tracer=tracer,
                stream=stream,
                redis_client=redis_client,
                task_id=task_id,
                session_id=session_id,
            )

            if precomputed_plan:
                plan_mode = precomputed_plan.get("mode", "simple")
                nodes = []
                if plan_mode == "dag":
                    nodes = [
                        DAGNode(
                            id=n["id"],
                            desc=n["desc"],
                            tool_hint=n.get("tool_hint"),
                            agent_name=n.get("agent_name"),
                            confirm=n.get("confirm", False),
                            depends_on=n.get("depends_on", []),
                            parallel_group=n.get("parallel_group"),
                        )
                        for n in precomputed_plan.get("nodes", [])
                    ]

                plan = DAGPlan(
                    mode=plan_mode,
                    goal=precomputed_plan.get("goal", "") if plan_mode == "dag" else "",
                    nodes=nodes,
                    risk=precomputed_plan.get("risk", "low") if plan_mode == "dag" else "low",
                )

                with tracer.span("execute"):
                    for event in executor.execute(plan):
                        if event[0] == "llm_response":
                            choice = event[1]
                            text = choice.message.content or ""
                            guard_fail, safe_text = _apply_output_guard(text)
                            if guard_fail is not None:
                                yield ("error", guard_fail.get("reason", "响应被安全策略拦截"))
                                yield ("done", {"status": "blocked"})
                                return
                            choice.message.content = safe_text
                            yield event
                        else:
                            yield event
            else:
                # No plan → simple chat fallback
                plan = DAGPlan(mode="simple")
                with tracer.span("simple_fallback"):
                    for event in executor.execute(plan):
                        if event[0] == "llm_response":
                            choice = event[1]
                            text = choice.message.content or ""
                            guard_fail, safe_text = _apply_output_guard(text)
                            if guard_fail is not None:
                                yield ("error", guard_fail.get("reason", "响应被安全策略拦截"))
                                yield ("done", {"status": "blocked"})
                                return
                            choice.message.content = safe_text
                            yield event
                        else:
                            yield event

        tracer.flush()
        yield ("trace", {"trace_id": tracer.trace_id})
