# -*- coding: UTF-8 -*-
"""Sub-agent registry — import to register all sub-agents."""

from app.util.agent.agents.base import AgentBase
from app.util.agent.agents.canvas_agent import CanvasAgent
from app.util.agent.agents.blueprint_agent import BlueprintAgent
from app.util.agent.agents.file_agent import FileAgent
from app.util.agent.agents.code_agent import CodeAgent

__all__ = ["AgentBase", "CanvasAgent", "BlueprintAgent", "FileAgent", "CodeAgent"]


def get_all_agents():
    """Return all registered sub-agent instances."""
    return [CanvasAgent(), BlueprintAgent(), FileAgent(), CodeAgent()]
