"""Unified LLM retry wrapper."""

import logging
import time

from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError)


def should_retry_llm(e: Exception) -> bool:
    """Check if an LLM error is transient and worth retrying."""
    if isinstance(e, _RETRYABLE):
        return True
    if isinstance(e, APIError) and getattr(e, "status_code", 500) >= 500:
        return True
    return False


def retry_llm_call(fn, *args, max_retries: int = 3, **kwargs):
    """Call fn() with exponential backoff retry for transient LLM errors."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except _RETRYABLE as e:
            last_exc = e
            if attempt < max_retries - 1:
                delay = 2**attempt
                logging.warning(f"LLM retry {attempt + 1}/{max_retries}: {e.__class__.__name__}, sleeping {delay}s")
                time.sleep(delay)
        except APIError as e:
            last_exc = e
            if getattr(e, "status_code", 0) >= 500 and attempt < max_retries - 1:
                delay = 2**attempt
                logging.warning(f"LLM server error retry {attempt + 1}/{max_retries}: HTTP {e.status_code}")
                time.sleep(delay)
            else:
                raise
    raise last_exc
