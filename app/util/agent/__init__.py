# -*- coding: UTF-8 -*-
"""Agent 系统包 — 统一入口，向后兼容旧版 from app.util.agent_xxx 导入。

Usage:
    from app.util.agent import AgentSession           # 新的推荐方式
    from app.util.agent.core import AgentSession       # 显式子模块
    from app.util.agent_xxx import AgentSession        # 旧式兼容（DeprecationWarning）

所有 agent_*.py → agent/*.py, agent_skills/ → agent/skills/,
agent_eval/ → agent/eval/, agents/ → agent/agents/
"""

import warnings

from .adaptive import replan_node

# ── Sub-agents ────────────────────────────────────────────────────────────
from .agents import AgentBase, BlueprintAgent, CanvasAgent, CodeAgent, FileAgent

# ── Circuit / Fallback / Adaptive / Reflexion ─────────────────────────────
from .circuit import circuit_allow, circuit_record

# ── State Management (Phase 0) ──────────────────────────────────────────
try:
    from .state import WorldState
except ImportError:
    WorldState = None  # type: ignore[assignment]

try:
    from .state_store import StateStore
except ImportError:
    StateStore = None  # type: ignore[assignment]

try:
    from .state_reducer import StateMutation, StateReducer
except ImportError:
    StateReducer = None  # type: ignore[assignment]
    StateMutation = None  # type: ignore[assignment]

try:
    from .state_snapshot import SnapshotManager, StateSnapshot
except ImportError:
    SnapshotManager = None  # type: ignore[assignment]
    StateSnapshot = None  # type: ignore[assignment]

# ── Critic Agent (Phase 0) ──────────────────────────────────────────────
try:
    from .critic_agent import CriticAgent, CriticReview
except ImportError:
    CriticAgent = None  # type: ignore[assignment]
    CriticReview = None  # type: ignore[assignment]

# ── Routers (Phase 1) ───────────────────────────────────────────────────
try:
    from .tool_router import ToolRouter, ToolRouting
except ImportError:
    ToolRouter = None  # type: ignore[assignment]
    ToolRouting = None  # type: ignore[assignment]

try:
    from .model_router import ModelRoute, ModelRouter
except ImportError:
    ModelRouter = None  # type: ignore[assignment]
    ModelRoute = None  # type: ignore[assignment]

# ── Core ──────────────────────────────────────────────────────────────────
from .core import AgentSession
from .dispatcher import AgentDispatcher

# ── Engine ────────────────────────────────────────────────────────────────
from .engine import AgentEngine
from .executor import AgentExecutor

# ── Guard ─────────────────────────────────────────────────────────────────
from .guard import InputGuard, OutputGuard, ToolGuard

# ── Helpers ───────────────────────────────────────────────────────────────
from .helpers import (
    estimate_tokens_from_str,
    extract_json,
    loop_key,
    repair_json,
    sanitize_for_json,
    truncate_tool_result,
)

# ── Intent / Executor ─────────────────────────────────────────────────────
from .intent import classify_domain, unified_intent_and_plan

# ── Memory ────────────────────────────────────────────────────────────────
from .memory import MemoryManager

# ── Observability & Trace ─────────────────────────────────────────────────
from .observability import AgentObservability, HealthChecker, MetricsCollector
from .plan_eval import PlanMemory, evaluate_plan

# ── Skills ────────────────────────────────────────────────────────────────
from .skills import get_skills_for_intent

# ── Tools ─────────────────────────────────────────────────────────────────
from .tools import TOOL_SCHEMAS, _rebuild_schemas, run_tool_call
from .tracer import AgentTracer

try:
    from .fallback import AgentFallback
except ImportError:
    AgentFallback = None  # type: ignore[assignment]

try:
    from .reflexion import AgentReflexion
except ImportError:
    AgentReflexion = None  # type: ignore[assignment]

# ── DAG ───────────────────────────────────────────────────────────────────
from .dag import DAGExecutor, DAGNode, DAGPlan

# ── Cache / MCP / Pheromone ───────────────────────────────────────────────
try:
    from .cache import AgentCache
except ImportError:
    AgentCache = None  # type: ignore[assignment]

try:
    from .mcp import get_mcp_server
except ImportError:
    get_mcp_server = None  # type: ignore[assignment]

# ── Eval ───────────────────────────────────────────────────────────────────
from .evaluator import AgentEvaluator
from .pheromone import SharedContext, extract_discoveries

# ── TTS ───────────────────────────────────────────────────────────────────
from .tts import AgentTTS

# ── Backward-compatible re-export warnings ────────────────────────────────


def __getattr__(name):
    """Legacy import support: maps old flat module names to new sub-modules.

    Example: agent.from app.util.agent_core import AgentSession' still works.
    """
    _LEGACY_MAP = {
        "agent_core": "core",
        "agent_engine": "engine",
        "agent_guard": "guard",
        "agent_helpers": "helpers",
        "agent_tools": "tools",
        "agent_intent": "intent",
        "agent_executor": "executor",
        "agent_dispatcher": "dispatcher",
        "agent_memory": "memory",
        "agent_session_memory": "session_memory",
        "agent_plan_eval": "plan_eval",
        "agent_observability": "observability",
        "agent_tracer": "tracer",
        "agent_skills": "skills",
        "agents": "agents",
        "agent_circuit": "circuit",
        "agent_fallback": "fallback",
        "agent_adaptive": "adaptive",
        "agent_reflexion": "reflexion",
        "agent_dag": "dag",
        "agent_cache": "cache",
        "agent_mcp": "mcp",
        "agent_pheromone": "pheromone",
        "agent_tts": "tts",
        "agent_evaluator": "evaluator",
        "agent_state": "state",
        "agent_state_store": "state_store",
        "agent_state_reducer": "state_reducer",
        "agent_state_snapshot": "state_snapshot",
        "agent_critic": "critic_agent",
        "agent_tool_router": "tool_router",
        "agent_model_router": "model_router",
    }
    if name in _LEGACY_MAP:
        warnings.warn(
            f"import '{name}' is deprecated, use 'from app.util.agent.{_LEGACY_MAP[name]}' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        return importlib.import_module(f".{_LEGACY_MAP[name]}", __name__)
    raise AttributeError(f"module 'app.util.agent' has no attribute '{name}'")
