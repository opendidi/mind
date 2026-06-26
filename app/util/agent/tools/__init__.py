# -*- coding: UTF-8 -*-
"""Agent tools — modular domain tool collection.

Each sub-module registers its tools with ToolRegistry on import.
This package re-exports the shared run_tool_call() and TOOL_SCHEMAS
from the previous monolithic tools.py, so existing importers work unchanged.
"""

import logging

from app.util.tool_registry import ToolRegistry

# Import all sub-modules to trigger @ToolRegistry.register decorators
from . import blueprint  # noqa: F401  — blueprint CRUD
from . import canvas  # noqa: F401  — canvas + layout tools
from . import code  # noqa: F401  — code_generate
from . import file_ops  # noqa: F401  — file search + document analysis
from . import geo  # noqa: F401  — geocode + regeocode
from . import translate  # noqa: F401  — translate_text
from . import web  # noqa: F401  — web_fetch + analyze_image

# Re-export _require for backward compat (used by engine_chain.py)
from .web import _require  # noqa: F401

TOOL_SCHEMAS = []  # populated below


def _rebuild_schemas():
    """Rebuild TOOL_SCHEMAS from ToolRegistry."""
    global TOOL_SCHEMAS
    TOOL_SCHEMAS = ToolRegistry.get_schemas()


_rebuild_schemas()


def run_tool_call(
    tool_name,
    tool_args,
    tool_context,
    dispatcher=None,
    llm_client=None,
    model=None,
    tracer=None,
    pheromone_sniff="",
    event_queue=None,
):
    """Execute a tool by name, dispatching sub-agents when needed.

    Returns (result_dict, cached_bool).
    """
    # Handle dispatch_agent — route to sub-agent system with event relay
    if tool_name == "dispatch_agent" and dispatcher:
        agent_name = tool_args.get("agent_name", "")
        task = tool_args.get("task", "")
        if agent_name and task:
            ctx = {**tool_context, "_pheromone": pheromone_sniff}
            # Pass canvas context to canvas_agent so it can see pen IDs
            if agent_name == "canvas_agent" and tool_context.get("_canvas_context"):
                ctx["_canvas_context"] = tool_context["_canvas_context"]

            # Wrap event_queue to translate sub-agent tuple events → SSE-compatible dicts
            relay_queue = event_queue
            if event_queue is not None:
                import queue as _queue

                relay_queue = _queue.Queue()

                worker_ready = _threading.Event()

                def _relay_worker():
                    """Forward sub-agent events to main SSE queue with translation."""
                    worker_ready.set()  # signal readiness before entering loop
                    while True:
                        try:
                            evt = relay_queue.get(timeout=0.5)
                        except _queue.Empty:
                            continue
                        if evt is None:  # sentinel
                            break
                        kind = evt[0]
                        if kind == "token":
                            event_queue.put({"type": "sub_agent_token", "data": {"agent": agent_name, "text": evt[1]}})
                        elif kind == "tool_call":
                            event_queue.put({"type": "tool_call", "data": {"tool": evt[1], "args": evt[2]}})
                        elif kind == "tool_result":
                            safe_result = evt[3]
                            try:
                                json.dumps(safe_result)
                            except (TypeError, ValueError):
                                safe_result = str(safe_result)
                            event_queue.put(
                                {
                                    "type": "tool_result",
                                    "data": {"tool": evt[1], "success": evt[2], "result": safe_result},
                                }
                            )

                import threading as _threading

                relay_thread = _threading.Thread(target=_relay_worker, daemon=True)
                relay_thread.start()
                worker_ready.wait(timeout=5)  # ensure worker is ready before dispatch

            # Signal sub-agent start to frontend
            if event_queue is not None:
                event_queue.put({"type": "sub_agent_start", "data": {"agent": agent_name, "task": task[:200]}})

            result = dispatcher.dispatch(
                llm_client,
                agent_name,
                task,
                ctx,
                model=model,
                tracer=tracer,
                event_queue=relay_queue,
                stream=(event_queue is not None),
            )

            # Signal sub-agent end + stop relay
            if event_queue is not None:
                event_queue.put(
                    {"type": "sub_agent_end", "data": {"agent": agent_name, "success": result.get("success", False)}}
                )
                relay_queue.put(None)  # sentinel to stop relay thread
                relay_thread.join(timeout=2)

            return result, False

    # Handle ask_peer — lightweight sub-agent query
    if tool_name == "ask_peer" and dispatcher:
        agent_name = tool_args.get("agent_name", "")
        question = tool_args.get("question", "")
        if agent_name and question:
            ctx = {**tool_context, "_pheromone": pheromone_sniff}
            result = dispatcher.handle_peer_query(llm_client, agent_name, question, ctx, model=model, tracer=tracer)
            return result, False

    # Normal tool execution via ToolRegistry
    result = ToolRegistry.execute(tool_name, tool_args, tool_context)
    return result, False
