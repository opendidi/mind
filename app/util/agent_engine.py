# -*- coding: UTF-8 -*-
"""AgentEngine — unified V3 entry point that ties DAG + Multi-Agent + Tracing together."""

from typing import Generator

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent_dag import DAGExecutor, DAGPlan, DAGNode
from app.util.agent_dispatcher import AgentDispatcher
import app.util.search  # noqa: F401 — registers web_search tool via ToolRegistry
from app.util.agent_tools import TOOL_SCHEMAS, _rebuild_schemas
from app.util.agent_tracer import AgentTracer

# Rebuild after search module registers additional tools
_rebuild_schemas()


class AgentEngine:
    """V3 unified execution engine.

    1. Intent + plan from unified_intent_and_plan() (called upstream in AgentSession)
    2. Simple chat → single-round ReAct; Complex → DAGExecutor (parallel steps)
    3. Sub-agents dispatched via AgentDispatcher as a tool
    4. Full lifecycle traced via AgentTracer
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
        """Unified V3 chat entry point.

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

        with tracer.span("agent_chat", user_id=self.user_id):
            # Inject dispatch_agent tool schema alongside existing tools
            full_tools = list(TOOL_SCHEMAS)
            dispatch_schema = self.dispatcher.get_dispatch_tool_schema()
            if dispatch_schema:
                full_tools.append(dispatch_schema)

            tool_ctx = {"user_id": self.user_id}
            if redis_client:
                tool_ctx["_redis"] = redis_client
                tool_ctx["_task_id"] = task_id

            # Use precomputed plan from unified_intent_and_plan() if available
            if precomputed_plan:
                plan_mode = precomputed_plan.get("mode", "simple")
                if plan_mode == "simple":
                    with tracer.span("simple_chat"):
                        executor = DAGExecutor(
                            self.llm,
                            full_tools,
                            messages,
                            tool_context=tool_ctx,
                            user_id=self.user_id,
                            model=self.model,
                            dispatcher=self.dispatcher,
                            stream=stream,
                            tracer=tracer,
                        )
                        for event in executor.execute(DAGPlan(mode="simple")):
                            yield event
                else:
                    with tracer.span("execute_dag") as sid:
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
                            mode="dag",
                            goal=precomputed_plan.get("goal", ""),
                            nodes=nodes,
                            risk=precomputed_plan.get("risk", "low"),
                        )
                        executor = DAGExecutor(
                            self.llm,
                            full_tools,
                            messages,
                            tool_context=tool_ctx,
                            user_id=self.user_id,
                            model=self.model,
                            confirm_handler=confirm_handler,
                            dispatcher=self.dispatcher,
                            stream=stream,
                            tracer=tracer,
                            redis_client=redis_client,
                            task_id=task_id,
                        )
                        for event in executor.execute(plan):
                            yield event
                        tracer.end_span(sid, "ok")
        tracer.flush()
        yield ("trace", {"trace_id": tracer.trace_id})
