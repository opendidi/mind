# -*- coding: UTF-8 -*-
"""AgentAdaptive — minimal stub for adaptive re-planning (disabled by default)."""

import logging


def replan_node(
    llm_client=None,
    model: str = "deepseek-chat",
    plan_goal: str = "",
    failed_node_id: str = "",
    failed_step_desc: str = "",
    tool_hint: str = "",
    error_msg: str = "",
    completed_steps: list = None,
    remaining_steps: list = None,
    shared_context_sniff: str = "",
) -> list | None:
    """Generate replacement steps for a failed DAG node.

    Currently returns None (adaptive re-plan disabled).
    Future: LLM-based re-planning that analyzes the failure and proposes
    alternative steps to achieve the original goal.
    """
    logging.debug(
        "Adaptive re-plan requested for node %s (disabled), error: %s",
        failed_node_id, error_msg[:100],
    )
    return None
