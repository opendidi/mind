# -*- coding: UTF-8 -*-
"""Agent Executor — AgentExecutor facade with full guardrail integration.

Uses AgentEngine. Wraps DAGExecutor with:
- InputGuard: validates user messages at the boundary
- ToolGuard: validates every tool call before execution (via _guard_check_tool)
- OutputGuard: sanitizes AI text responses before they reach the user

BaseExecutor lives in base_executor.py (shared by dag.py without circular imports).
"""

import logging

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.base_executor import BaseExecutor  # noqa: F401 — re-export for backward compat
from app.util.agent.guard import ToolGuard


class AgentExecutor:
    """Public executor facade with full guardrail integration.

    Used by AgentEngine. Wraps DAGExecutor with:
    - InputGuard: validates user messages at the boundary
    - ToolGuard: validates every tool call before execution (via _guard_check_tool)
    - OutputGuard: sanitizes AI text responses before they reach the user
    """

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
        self._session_id = session_id or task_id or user_id

        # Inject guard hook into tool_context so DAGExecutor calls it per tool
        ctx = dict(tool_context or {})
        if redis_client:
            ctx["_redis"] = redis_client
            ctx["_task_id"] = task_id
        ctx["_guard_check"] = self._guard_check_tool
        ctx["_session_id"] = self._session_id

        # Lazy import: DAGExecutor imports BaseExecutor from base_executor (not from here).
        # This import is deferred to avoid any import-time side effects.
        from app.util.agent.dag import DAGExecutor

        self._dag = DAGExecutor(
            llm_client,
            tools_schemas,
            messages,
            tool_context=ctx,
            user_id=user_id,
            model=model,
            confirm_handler=confirm_handler,
            dispatcher=dispatcher,
            tracer=tracer,
            stream=stream,
            redis_client=redis_client,
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

    def set_critic_hints(self, hints: str):
        """注入 CriticAgent 的质量要求到 DAGExecutor 的节点指令中。"""
        if hasattr(self._dag, "_critic_hints"):
            self._dag._critic_hints = hints

    @classmethod
    def reset_guard(cls, session_id: str):
        """Reset ToolGuard counters for a session."""
        ToolGuard.reset_session(session_id)
