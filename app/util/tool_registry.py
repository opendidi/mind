# -*- coding: UTF-8 -*-
"""ToolRegistry — decorator-based tool registration + function calling schema generation."""

import json
import logging
import threading
import time
from typing import Callable

from app.util.executor import run_with_timeout as _exec_run_with_timeout
from app.util.executor import ExecutorTimeout

TOOL_TIMEOUT = 60  # default tool execution timeout (seconds)


class ToolRegistry:
    """Decorator-based tool registry with auto schema generation.

    Usage:
        @ToolRegistry.register(
            name="my_tool",
            description="Does something useful.",
            parameters={"type": "object", "properties": {...}, "required": [...]},
            validator=_validate_my_tool,
        )
        def _tool_my_impl(args):
            return {"success": True, "data": ...}
    """

    _tools: dict = {}  # name -> {schema, validator, func, enabled}
    _exec_hook: Callable | None = None  # optional hook for execution wrapping
    _lock: threading.RLock = threading.RLock()  # guards concurrent access to _tools

    @classmethod
    def register(cls, name: str, description: str, parameters: dict,
                 validator: Callable = None):
        """Decorator: register a tool function."""
        def wrapper(func):
            with cls._lock:
                cls._tools[name] = {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                    "validator": validator,
                    "func": func,
                    "enabled": True,
                }
                logging.info("ToolRegistry registered: %s", name)
            return func
        return wrapper

    @classmethod
    def set_exec_hook(cls, hook: Callable):
        """Set a hook that wraps every tool execution. Used for timeout enforcement."""
        cls._exec_hook = hook

    @classmethod
    def execute(cls, name: str, args: dict, context: dict = None) -> dict:
        """Execute a registered tool by name.

        Returns:
            dict with at least {"success": bool}. On error: {"success": False, "error": str}.
        """
        with cls._lock:
            if name not in cls._tools:
                return {"success": False, "error": f"未知工具: {name}"}
            tool = dict(cls._tools[name])  # snapshot under lock
        if not tool["enabled"]:
            return {"success": False, "error": f"工具 {name} 已禁用"}

        # Merge context into args (context keys may be overridden by explicit args)
        merged_args = {**(context or {}), **args}

        # Validate arguments
        validator = tool.get("validator")
        if validator:
            try:
                err = validator(merged_args)
                if err:
                    return {"success": False, "error": err, "validation_error": True}
            except Exception as e:
                logging.warning("Tool %s validator raised exception: %s", name, e)

        start = time.time()
        try:
            func = tool["func"]
            if cls._exec_hook and context:
                result = cls._exec_hook(func, name, merged_args, context)
            else:
                try:
                    result = _exec_run_with_timeout(func, TOOL_TIMEOUT, merged_args)
                except ExecutorTimeout:
                    return {"success": False, "error": f"工具 {name} 执行超时 ({TOOL_TIMEOUT}s)"}
        except Exception as ex:
            logging.exception("Tool %s execution failed", name)
            return {"success": False, "error": str(ex)}
        elapsed = time.time() - start

        if isinstance(result, dict):
            result.setdefault("_tool_name", name)
            result.setdefault("_elapsed_ms", round(elapsed * 1000))
        return result

    @classmethod
    def get_schema(cls, name: str) -> dict | None:
        """Get the function-calling schema for a single tool."""
        with cls._lock:
            tool = cls._tools.get(name)
            if not tool or not tool["enabled"]:
                return None
            return {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }

    @classmethod
    def get_schemas(cls) -> list:
        """Get all enabled tool schemas in OpenAI function-calling format."""
        with cls._lock:
            return [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in cls._tools.values() if t["enabled"]
            ]

    @classmethod
    def disable(cls, name: str):
        """Disable a tool at runtime (e.g., circuit breaker open)."""
        with cls._lock:
            if name in cls._tools:
                cls._tools[name]["enabled"] = False

    @classmethod
    def enable(cls, name: str):
        """Re-enable a previously disabled tool."""
        with cls._lock:
            if name in cls._tools:
                cls._tools[name]["enabled"] = True

    @classmethod
    def list_tools(cls) -> list:
        """Return list of (name, enabled) tuples."""
        with cls._lock:
            return [(name, t["enabled"]) for name, t in cls._tools.items()]
