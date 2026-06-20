# -*- coding: UTF-8 -*-
"""Agent API — SSE streaming chat endpoint."""

import json
import logging
import queue
import threading
import uuid

from flask import Blueprint, Response, request, stream_with_context

agent_api = Blueprint("agent", __name__)


def _safe_json_dumps(obj, **kwargs):
    """json.dumps with a fallback for non-serializable objects (bound methods, types, etc.)."""
    return json.dumps(obj, ensure_ascii=False, default=lambda o: f"<{type(o).__name__}>", **kwargs)


@agent_api.route("/health", methods=["GET"])
def agent_health():
    """Agent 健康检查端点 — 各层状态汇总."""
    from app.util.agent.observability import HealthChecker, MetricsCollector
    return {
        "code": 200,
        "data": {
            "layers": HealthChecker.check_all(),
            "metrics": MetricsCollector.snapshot(),
        },
        "message": "ok",
    }


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
    if len(message) > 8192:
        return {"code": 400, "message": f"message too long ({len(message)} > 8192)"}, 400

    user_id = data.get("user_id", request.headers.get("X-User-ID", "anonymous"))
    canvas_context = data.get("canvas_context")
    images = data.get("images")  # list of base64 data URL strings for multimodal vision

    from app.util.agent.observability import AgentObservability
    obs = AgentObservability(user_id=user_id)

    def generate():
        event_queue = queue.Queue()
        task_id = str(uuid.uuid4())[:8]

        def run_agent():
            try:
                from app.util.agent.core import AgentSession

                session = AgentSession(user_id)

                obs.trace("session_start", duration_ms=0.0)
                for event in session.chat_v3(
                    user_message=message,
                    canvas_context=canvas_context,
                    task_id=task_id,
                    images=images,
                ):
                    event_queue.put(event)
                event_queue.put({"type": "done", "data": {"status": "completed"}})
            except Exception:
                logging.exception("Agent chat error: %s", task_id)
                obs.trace("session_error", status="error")
                event_queue.put({"type": "error", "data": {"message": "处理请求时发生内部错误"}})
                event_queue.put({"type": "done", "data": {"status": "error"}})

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        while True:
            try:
                event = event_queue.get(timeout=120)
                yield f"data: {_safe_json_dumps(event)}\n\n"
                if event.get("type") == "done":
                    flush_result = obs.flush()
                    yield f"data: {_safe_json_dumps({'type': 'trace', 'data': flush_result})}\n\n"
                    break
            except queue.Empty:
                obs.trace("session_timeout", status="error")
                yield f"data: {_safe_json_dumps({'type': 'error', 'data': {'message': '请求超时'}})}\n\n"
                yield f"data: {_safe_json_dumps({'type': 'done', 'data': {'status': 'timeout'}})}\n\n"
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
        from app.util.agent.mcp import get_mcp_server
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


@agent_api.route("/tts", methods=["POST"])
def agent_tts():
    """TTS 语音合成端点。

    POST JSON: {"text": "要朗读的文本"}
    Response 200: {"audio_url": "/v1/static/tts/abc123.wav"}
    Response 400: {"error": "text is required"}
    Response 503: {"error": "TTS model not loaded yet"}
    Response 500: {"error": "TTS generation failed: ..."}
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return {"error": "text is required"}, 400
    if len(text) > 8000:
        return {"error": f"text too long ({len(text)} > 8000)"}, 400

    try:
        from app.util.agent.tts import AgentTTS

        tts = AgentTTS.instance()
        audio_path = tts.generate(text)
        audio_url = tts.url_for(audio_path)

        return {"audio_url": audio_url}
    except ValueError as e:
        return {"error": str(e)}, 400
    except RuntimeError as e:
        msg = str(e)
        if "未安装" in msg or "加载失败" in msg or "TTS 功能已禁用" in msg:
            return {"error": msg}, 503
        return {"error": msg}, 500


@agent_api.route("/tts/audio/<path:filename>", methods=["GET"])
def agent_tts_audio(filename):
    """提供 TTS 音频文件访问。"""
    import os as _os
    from flask import send_from_directory
    from app.config import TTS_CACHE_DIR

    # 安全检查：只允许 .wav 文件
    if not filename.endswith(".wav") or ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "invalid filename"}, 400

    cache_dir = _os.path.abspath(TTS_CACHE_DIR)
    return send_from_directory(cache_dir, filename, mimetype="audio/wav")
