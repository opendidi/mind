# -*- coding: UTF-8 -*-
"""AgentEngine — unified V3 entry point that ties DAG + Multi-Agent + Guard + Tracing together.

Phase 0: State Manager, Snapshot Manager, Critic Agent integration.
Phase 1: Tool Router, Model Router integration.
"""

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
    3. StateManager loads/saves WorldState across executions
    4. ToolRouter filters tool schemas by intent domain (reduces prompt size)
    5. ModelRouter selects optimal model per task type
    6. Simple chat → single-round ReAct; Complex → DAG parallel execution
    7. Sub-agents dispatched via AgentDispatcher as a tool
    8. CriticAgent reviews execution quality post-hoc
    9. OutputGuard sanitizes AI responses before user delivery
    10. Full lifecycle traced via AgentTracer + SnapshotManager
    """

    def __init__(self, llm_client, user_id: str, model: str = AGENT_DEFAULT_MODEL):
        self.llm = llm_client
        self.user_id = user_id
        self.model = model
        self.dispatcher = AgentDispatcher()

        # ── Phase 0: State Manager ──
        from app.util.agent.state_snapshot import SnapshotManager
        from app.util.agent.state_store import StateStore

        self.state_store = StateStore()
        self.snapshot_mgr = SnapshotManager(self.state_store)

        # ── Phase 0: Critic Agent ──
        from app.util.agent.critic_agent import CriticAgent

        self.critic = CriticAgent(llm_client, model)

        # ── Phase 1: Routers (lazy init) ──
        self._tool_router = None
        self._model_router = None

    @property
    def tool_router(self):
        """Lazy-init ToolRouter."""
        if self._tool_router is None:
            from app.util.agent.tool_router import ToolRouter

            self._tool_router = ToolRouter()
        return self._tool_router

    @property
    def model_router(self):
        """Lazy-init ModelRouter."""
        if self._model_router is None:
            from app.util.agent.model_router import ModelRouter

            self._model_router = ModelRouter()
        return self._model_router

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
        canvas_context: dict = None,
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
        import logging

        tracer = AgentTracer(user_id=self.user_id)
        session_id = task_id or self.user_id

        with tracer.span("agent_chat", user_id=self.user_id):
            # ── Input Guard ──
            guard_result = InputGuard.check(user_message)
            if not guard_result["ok"]:
                yield ("error", guard_result.get("reason", "输入被安全策略拦截"))
                yield ("done", {"status": "blocked"})
                return

            # ── State Load (Phase 0) ──
            from app.util.agent.state import WorldState

            world_state = self.state_store.load(self.user_id)
            if world_state is None:
                world_state = WorldState(user_id=self.user_id, session_id=session_id)
            world_state.session_id = session_id

            # ── Tool Routing (Phase 1 / Quick Win 1) ──
            domains = precomputed_plan.get("domains", []) if precomputed_plan else []
            has_write = precomputed_plan.get("has_write", False) if precomputed_plan else False
            routing = self.tool_router.route(domains, user_message, has_write)
            full_tools = routing.tools

            # Always include dispatcher tool if sub-agents registered
            dispatch_schema = self.dispatcher.get_dispatch_tool_schema()
            if dispatch_schema and dispatch_schema not in full_tools:
                full_tools.append(dispatch_schema)

            logging.debug(
                "ToolRouter: %d tools selected for domains=%s (excluded: %s)",
                len(full_tools),
                domains,
                routing.excluded_tools[:5],
            )

            # ── Model Routing (Phase 1) ──
            plan_mode = precomputed_plan.get("mode", "simple") if precomputed_plan else "simple"
            node_count = len(precomputed_plan.get("nodes", [])) if precomputed_plan else 0
            task_type = self._determine_task_type(precomputed_plan)
            model_route = self.model_router.route(task_type, plan_mode, node_count)
            executor_model = model_route.primary_model if model_route else self.model

            tool_ctx = {"user_id": self.user_id}
            if canvas_context:
                tool_ctx["_canvas_context"] = canvas_context
            if redis_client:
                tool_ctx["_redis"] = redis_client
                tool_ctx["_task_id"] = task_id

            # ── Pre-execution Snapshot (Phase 0) ──
            if precomputed_plan and precomputed_plan.get("goal"):
                world_state.working_goal = precomputed_plan.get("goal", "")
                world_state.last_plan_domains = domains
                world_state.tasks = [
                    {"id": n.get("id", ""), "desc": n.get("desc", ""), "status": "pending"}
                    for n in precomputed_plan.get("nodes", [])
                ]
                world_state.pending = [t["id"] for t in world_state.tasks]
            self.snapshot_mgr.snapshot(world_state, "pre_execution")

            # Create guarded executor
            executor = AgentExecutor(
                self.llm,
                full_tools,
                messages,
                tool_context=tool_ctx,
                user_id=self.user_id,
                model=executor_model,
                confirm_handler=confirm_handler,
                dispatcher=self.dispatcher,
                tracer=tracer,
                stream=stream,
                redis_client=redis_client,
                task_id=task_id,
                session_id=session_id,
            )

            # ── Critic Hints (Quick Win 2) ──
            pre_critic = self.critic.review_plan(precomputed_plan, user_message, domains) if precomputed_plan else None
            if pre_critic and pre_critic.issues:
                executor.set_critic_hints(pre_critic.get_quality_hints())

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

                # ── Critic: Pre-execution Plan Review ──
                if pre_critic and pre_critic.needs_replan:
                    logging.warning(
                        "CriticAgent: pre-plan review suggests replan — score=%.2f",
                        pre_critic.overall_score,
                    )

                with tracer.span("execute"):
                    execution_state = None
                    for event in executor.execute(plan):
                        # Track execution state for critic
                        if event[0] == "step_end" or event[0] == "step_fail":
                            pass  # state tracked internally by DAGExecutor
                        if event[0] == "done":
                            # Capture execution state from last event
                            execution_state = event[1] if isinstance(event[1], dict) else None

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

            # ── Post-execution State Save (Phase 0) ──
            world_state.last_plan_goal = precomputed_plan.get("goal", "") if precomputed_plan else ""
            self.state_store.save(world_state)
            self.snapshot_mgr.snapshot(world_state, "post_execution")

            # ── Post-execution Critic Review (Phase 0) ──
            if precomputed_plan and precomputed_plan.get("mode") == "dag":
                try:
                    post_critic = self.critic.review_execution(
                        plan,
                        executor._dag._get_state() if hasattr(executor._dag, "_get_state") else None,
                        world_state,
                        user_message,
                    )
                    if post_critic and not post_critic.passes:
                        logging.warning(
                            "CriticAgent: post-execution review FAILED — score=%.2f issues=%d needs_replan=%s",
                            post_critic.overall_score,
                            len(post_critic.issues),
                            post_critic.needs_replan,
                        )
                        yield ("critic_review", post_critic.to_dict())
                    elif post_critic:
                        logging.info(
                            "CriticAgent: post-execution review PASSED — score=%.2f",
                            post_critic.overall_score,
                        )
                except Exception:
                    logging.debug("CriticAgent: post-execution review skipped (no execution state available)")

        tracer.flush()
        yield ("trace", {"trace_id": tracer.trace_id})

    def _determine_task_type(self, precomputed_plan: dict) -> str:
        """推断任务类型用于 ModelRouter 选择模型。"""
        if not precomputed_plan:
            return "simple_chat"

        plan_mode = precomputed_plan.get("mode", "simple")
        node_count = len(precomputed_plan.get("nodes", []))
        has_write = precomputed_plan.get("has_write", False)
        intent = precomputed_plan.get("intent", "chat")

        if intent == "chat":
            return "simple_chat"
        if plan_mode == "dag":
            if node_count > 3:
                return "dag_complex"
            return "dag_simple"
        if has_write:
            if node_count > 1:
                return "tool_multi"
            return "tool_single"
        return "simple_chat"
