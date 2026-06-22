# -*- coding: UTF-8 -*-
"""MCP (Model Context Protocol) wrapper — exposes ToolRegistry tools as MCP-compatible interfaces."""

import json
import logging

_MCP_SAFE_CONTEXT_KEYS = frozenset({"user_id"})


def _sanitize_mcp_context(raw: dict) -> dict:
    if not raw:
        return {}
    return {k: v for k, v in raw.items() if k in _MCP_SAFE_CONTEXT_KEYS}


class MCPToolAdapter:
    def __init__(self, name: str, schema: dict, handler, validator=None):
        self.name = name
        self._schema = schema
        self._handler = handler
        self._validator = validator

    @property
    def description(self) -> str:
        fn = self._schema.get("function", {})
        return fn.get("description", "")

    @property
    def input_schema(self) -> dict:
        fn = self._schema.get("function", {})
        params = fn.get("parameters", {})
        return {"type": "object", "properties": params.get("properties", {}), "required": params.get("required", [])}

    def to_mcp_tool_def(self) -> dict:
        return {"name": self.name, "description": self.description, "inputSchema": self.input_schema}

    def validate(self, args: dict) -> str | None:
        if self._validator:
            try:
                return self._validator(args)
            except Exception as e:
                return f"Validation error: {e}"
        return None

    def execute(self, args: dict, context: dict = None) -> dict:
        from app.util.tool_registry import ToolRegistry

        try:
            return ToolRegistry.execute(self.name, args, context)
        except Exception as e:
            logging.exception("MCP tool '%s' execution failed", self.name)
            return {"success": False, "error": f"Tool execution error: {e}"}


class MCPServer:
    def __init__(self):
        self._tools: dict[str, MCPToolAdapter] = {}

    def register(self, adapter: MCPToolAdapter):
        self._tools[adapter.name] = adapter

    def register_from_registry(self, tool_registry=None):
        if tool_registry is None:
            from app.util.tool_registry import ToolRegistry

            tool_registry = ToolRegistry
        for name, tool_info in tool_registry._tools.items():
            schema = tool_registry.get_schema(name)
            if schema is None:
                continue
            adapter = MCPToolAdapter(
                name=name, schema=schema, handler=tool_info["func"], validator=tool_info.get("validator")
            )
            self._tools[name] = adapter
        logging.info("MCPServer loaded %d tools from ToolRegistry", len(self._tools))

    def list_tools(self) -> list[dict]:
        return [t.to_mcp_tool_def() for t in self._tools.values()]

    def get_tool(self, name: str) -> MCPToolAdapter | None:
        return self._tools.get(name)

    def call_tool(self, name: str, arguments: dict, context: dict = None) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
        err = tool.validate(arguments)
        if err:
            return {"content": [{"type": "text", "text": f"Invalid arguments: {err}"}], "isError": True}
        result = tool.execute(arguments, context)
        is_error = not result.get("success", False)
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": is_error}

    def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        req_id = request.get("id")
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            context = _sanitize_mcp_context(params.get("_context", {}))
            result = self.call_tool(tool_name, arguments, context)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


_mcp_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
        _mcp_server.register_from_registry()
    return _mcp_server
