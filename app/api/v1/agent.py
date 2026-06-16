# -*- coding: UTF-8 -*-
"""Agent API — SSE streaming chat endpoint."""

import json
import logging
import queue
import threading
import uuid

from flask import Blueprint, Response, request, stream_with_context

agent_api = Blueprint("agent", __name__)


@agent_api.route("/chat", methods=["POST"])
def agent_chat():
    """SSE 流式 Agent 对话端点。

    Request body:
        {
            "message": "用户输入",
            "user_id": "用户标识（可选）",
            "canvas_context": { ... }  // 当前画布状态（可选）
        }

    Response: text/event-stream
        event types: token, thinking, tool_call, tool_result, plan,
                     step_start, step_end, step_fail, progress, message,
                     trace, error, done
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return {"code": 400, "message": "message is required"}, 400
    if len(message) > 4096:
        return {"code": 400, "message": f"message too long ({len(message)} > 4096)"}, 400

    user_id = data.get("user_id", request.headers.get("X-User-ID", "anonymous"))
    canvas_context = data.get("canvas_context")

    def generate():
        event_queue = queue.Queue()
        task_id = str(uuid.uuid4())[:8]

        def run_agent():
            try:
                from app.util.agent_core import AgentSession
                from app.util.llm_client import get_llm_client

                session = AgentSession(user_id)

                for event in session.chat_v3(
                    user_message=message,
                    canvas_context=canvas_context,
                    task_id=task_id,
                ):
                    event_queue.put(event)
                event_queue.put({"type": "done", "data": {"status": "completed"}})
            except Exception:
                logging.exception("Agent chat error: %s", task_id)
                event_queue.put({"type": "error", "data": {"message": "处理请求时发生内部错误"}})
                event_queue.put({"type": "done", "data": {"status": "error"}})

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        while True:
            try:
                event = event_queue.get(timeout=120)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") == "done":
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': '请求超时'}})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'data': {'status': 'timeout'}})}\n\n"
                break

        thread.join(timeout=5)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@agent_api.route("/mcp", methods=["POST"])
def agent_mcp():
    """MCP (Model Context Protocol) 端点。

    支持 JSON-RPC 风格请求：
        tools/list  — 列出所有工具
        tools/call  — 调用指定工具
    """
    data = request.get_json(silent=True) or {}
    try:
        from app.util.agent_mcp import get_mcp_server
        server = get_mcp_server()
        result = server.handle_request(data)
        return result
    except Exception:
        logging.exception("MCP request failed")
        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {"code": -32603, "message": "Internal server error"},
        }
