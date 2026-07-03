"""Test unified LLM retry wrapper.

Imports retry module directly to avoid pre-existing package import chain
(app.util.agent.dispatcher references a non-existent app.util.agents module).
"""

import importlib.util
import sys
from unittest.mock import Mock

import httpx
import pytest

# Load retry module directly to avoid full package import chain
_spec = importlib.util.spec_from_file_location(
    "app.util.agent.retry",
    "app/util/agent/retry.py",
)
_retry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_retry)
retry_llm_call = _retry.retry_llm_call

_COMMON_REQUEST = httpx.Request("GET", "http://test.com")


def test_retry_llm_call_success_first_try():
    fn = Mock(return_value="ok")
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_llm_call_retries_on_rate_limit():
    from openai import RateLimitError

    resp = httpx.Response(429, request=_COMMON_REQUEST)
    err = RateLimitError("limit", response=resp, body=None)
    fn = Mock(side_effect=[err, "ok"])
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_llm_call_exhausted():
    from openai import RateLimitError

    resp = httpx.Response(429, request=_COMMON_REQUEST)
    err = RateLimitError("limit", response=resp, body=None)
    fn = Mock(side_effect=err)
    with pytest.raises(RateLimitError):
        retry_llm_call(fn, max_retries=2)
    assert fn.call_count == 2


def test_retry_llm_call_passes_args():
    fn = Mock(return_value="ok")
    retry_llm_call(fn, "arg1", key="val", max_retries=2)
    fn.assert_called_with("arg1", key="val")


def test_retry_llm_call_server_error_retry():
    from openai import InternalServerError

    resp = httpx.Response(500, request=_COMMON_REQUEST)
    err = InternalServerError("server error", response=resp, body=None)
    fn = Mock(side_effect=[err, "ok"])
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_llm_call_client_error_no_retry():
    from openai import BadRequestError

    resp = httpx.Response(400, request=_COMMON_REQUEST)
    err = BadRequestError("bad request", response=resp, body=None)
    fn = Mock(side_effect=err)
    with pytest.raises(BadRequestError):
        retry_llm_call(fn, max_retries=3)
    assert fn.call_count == 1


def test_retry_llm_call_timeout_retry():
    from openai import APITimeoutError

    err = APITimeoutError(request=_COMMON_REQUEST)
    fn = Mock(side_effect=[err, "ok"])
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_llm_call_connection_error_retry():
    from openai import APIConnectionError

    err = APIConnectionError(message="connection failed", request=_COMMON_REQUEST)
    fn = Mock(side_effect=[err, "ok"])
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2
