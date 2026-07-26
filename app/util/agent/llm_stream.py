# -*- coding: UTF-8 -*-
"""Shared LLM utilities — retry logic, backoff, and streaming chunk parser.

Used by BaseExecutor, AgentBase, and intent planner to avoid code duplication.
"""

import logging
import random
import time
from typing import Any, Generator

from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

# ── Retry / Backoff ──────────────────────────────────────────────────────


def should_retry_llm(error: Exception, attempt: int) -> bool:
    """Check if an LLM call error is retryable."""
    if attempt >= 2:
        return False

    if isinstance(error, (RateLimitError, APITimeoutError, APIConnectionError)):
        return True
    if isinstance(error, APIError):
        status = getattr(error, "http_status", None) or getattr(error, "status_code", None) or 500
        return status >= 500
    return True


def llm_retry_sleep(attempt: int, is_rate_limit: bool = False):
    """Exponential backoff with jitter."""
    base = 2**attempt
    sleep_s = base + random.uniform(0, 1) if is_rate_limit else base * random.uniform(0.75, 1.25)
    time.sleep(sleep_s)


# ── Streaming chunk parser ──────────────────────────────────────────────


def parse_stream_chunks(
    response,
) -> Generator[tuple, None, None]:
    """Parse OpenAI streaming response chunks into typed events.

    Yields:
        ("token", str)           — content token
        ("tool_call", name, id, arguments)  — completed tool call
        ("finish", finish_reason, full_text) — stream ended
        ("error", str)           — stream error

    Usage:
        for event in parse_stream_chunks(response):
            if event[0] == "token":
                print(event[1])
            elif event[0] == "tool_call":
                name, tc_id, args = event[1], event[2], event[3]
    """
    tool_calls_acc: dict[int, dict[str, str]] = {}
    full_text = ""
    finish_reason = None

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        finish_reason = chunk.choices[0].finish_reason

        if delta.content:
            full_text += delta.content
            yield ("token", delta.content)

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                acc = tool_calls_acc[idx]
                if tc_delta.id:
                    acc["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        acc["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        acc["arguments"] += tc_delta.function.arguments

        if finish_reason:
            break

    if finish_reason == "tool_calls" and tool_calls_acc:
        for idx in sorted(tool_calls_acc.keys()):
            acc = tool_calls_acc[idx]
            yield ("tool_call", acc["name"], acc["id"], acc["arguments"])
    else:
        yield ("finish", finish_reason or "stop", full_text)


# ── Unified streaming LLM call ──────────────────────────────────────────


def stream_llm_chat(
    llm_client,
    *,
    model: str,
    messages: list,
    tools: list = None,
    timeout: int = 90,
    circuit_service: str = None,
    tracer=None,
) -> Generator[tuple, None, None]:
    """Single entry point for streaming LLM calls with retry + circuit breaker.

    Yields the same tuple events as parse_stream_chunks(), plus:
        ("error", str) — non-retryable error or all retries exhausted

    Usage:
        for event in stream_llm_chat(llm, model="deepseek-chat", messages=msgs, tools=ts):
            dispatch(event)
    """
    from app.util.agent.circuit import circuit_allow, circuit_record
    from app.util.agent.retry import retry_llm_call

    service = circuit_service or model
    tools_list = tools or None
    tool_choice = "auto" if tools_list else None

    if not circuit_allow(service=service):
        yield ("error", "AI 服务不可用（熔断）")
        return

    llm_span_id = None
    if tracer:
        llm_span_id = tracer.start_span("llm_api_call", input={"model": model})
    try:
        response = retry_llm_call(
            lambda: llm_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_list,
                tool_choice=tool_choice,
                stream=True,
                timeout=timeout,
            ),
            max_retries=3,
        )
        circuit_record(True, service=service)
        if tracer:
            tracer.end_span(llm_span_id, "ok")
        yield from parse_stream_chunks(response)
    except APIError as ex:
        circuit_record(False, service=service)
        if tracer:
            tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
        status = getattr(ex, "status_code", 500) if hasattr(ex, "status_code") else 500
        yield ("error", f"API 错误 [{status}]: {ex}")
    except Exception as ex:
        circuit_record(False, service=service)
        if tracer:
            tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
        msg = str(ex)
        yield ("error", f"LLM 流式调用失败: {msg[:200]}")
