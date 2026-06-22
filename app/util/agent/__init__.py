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

# ── Core ──────────────────────────────────────────────────────────────────
from .core import AgentSession

# ── Engine ────────────────────────────────────────────────────────────────
from .engine import AgentEngine

# ── Guard ─────────────────────────────────────────────────────────────────
from .guard import InputGuard, OutputGuard, ToolGuard

# ── Helpers ───────────────────────────────────────────────────────────────
from .helpers import (
    extract_json,
    repair_json,
    sanitize_for_json,
    estimate_tokens_from_str,
    truncate_tool_result,
    loop_key,
)

# ── Tools ─────────────────────────────────────────────────────────────────
from .tools import run_tool_call, TOOL_SCHEMAS, _rebuild_schemas

# ── Intent / Executor ─────────────────────────────────────────────────────
from .intent import classify_domain, unified_intent_and_plan
from .executor import AgentExecutor
from .dispatcher import AgentDispatcher
from .supervisor import Supervisor

# ── Memory ────────────────────────────────────────────────────────────────
from .memory import MemoryManager
from .session_memory import SessionMemory
from .plan_eval import PlanMemory, evaluate_plan

# ── Observability & Trace ─────────────────────────────────────────────────
from .observability import AgentObservability, HealthChecker, MetricsCollector
from .tracer import AgentTracer

# ── Skills ────────────────────────────────────────────────────────────────
from .skills import get_skills_for_intent

# ── Sub-agents ────────────────────────────────────────────────────────────
from .agents import AgentBase, CanvasAgent, BlueprintAgent, FileAgent, CodeAgent

# ── Circuit / Fallback / Adaptive / Reflexion ─────────────────────────────
from .circuit import circuit_allow, circuit_record
from .fallback import AgentFallback
from .adaptive import replan_node
from .reflexion import AgentReflexion

# ── DAG ───────────────────────────────────────────────────────────────────
from .dag import DAGPlan, DAGNode, DAGExecutor

# ── Cache / MCP / Pheromone ───────────────────────────────────────────────
from .cache import AgentCache
from .mcp import get_mcp_server
from .pheromone import SharedContext, extract_discoveries

# ── TTS ───────────────────────────────────────────────────────────────────
from .tts import AgentTTS

# ── Eval ───────────────────────────────────────────────────────────────────
from .evaluator import AgentEvaluator


# ── Backward-compatible re-export warnings ────────────────────────────────

def __getattr__(name):
    """Legacy import support: maps old flat module names to new sub-modules.

    Example: agent.from app.util.agent_core import AgentSession' still works.
    """
    _LEGACY_MAP = {
        'agent_core': 'core',
        'agent_engine': 'engine',
        'agent_guard': 'guard',
        'agent_helpers': 'helpers',
        'agent_tools': 'tools',
        'agent_intent': 'intent',
        'agent_executor': 'executor',
        'agent_dispatcher': 'dispatcher',
        'agent_supervisor': 'supervisor',
        'agent_memory': 'memory',
        'agent_session_memory': 'session_memory',
        'agent_plan_eval': 'plan_eval',
        'agent_observability': 'observability',
        'agent_tracer': 'tracer',
        'agent_skills': 'skills',
        'agents': 'agents',
        'agent_circuit': 'circuit',
        'agent_fallback': 'fallback',
        'agent_adaptive': 'adaptive',
        'agent_reflexion': 'reflexion',
        'agent_dag': 'dag',
        'agent_cache': 'cache',
        'agent_mcp': 'mcp',
        'agent_pheromone': 'pheromone',
        'agent_tts': 'tts',
        'agent_evaluator': 'evaluator',
    }
    if name in _LEGACY_MAP:
        warnings.warn(
            f"import '{name}' is deprecated, use 'from app.util.agent.{_LEGACY_MAP[name]}' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib
        return importlib.import_module(f'.{_LEGACY_MAP[name]}', __name__)
    raise AttributeError(f"module 'app.util.agent' has no attribute '{name}'")
