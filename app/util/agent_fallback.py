# -*- coding: UTF-8 -*-
"""Multi-tier LLM client with automatic fallback on transient errors."""

import logging

from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

TRANSIENT_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError, APIError)
NON_TRANSIENT_STATUSES = {400, 401, 402, 403, 404, 422}


class FallbackLLM:
    """Multi-tier LLM client. Behaves like an OpenAI client but retries
    transient failures on fallback tiers automatically."""

    def __init__(self, tiers):
        if not tiers:
            raise ValueError("At least one tier is required")
        self.tiers = tiers
        self._last_used_tier = None
        self.stats = {"total_calls": 0, "fallbacks": 0}

    @property
    def chat(self):
        return _FallbackCompletions(self)


class _FallbackCompletions:
    def __init__(self, fallback: FallbackLLM):
        self._fb = fallback

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        last_error = None
        call_kwargs = dict(kwargs)
        self._fb.stats["total_calls"] += 1

        for idx, tier in enumerate(self._fb.tiers):
            if idx > 0:
                self._fb.stats["fallbacks"] += 1
                logging.warning("Falling back to tier %d (model=%s) after: %s", idx, tier["model"], last_error)
                call_kwargs.pop("stream", None)

            try:
                call_kwargs["model"] = tier["model"]
                result = tier["client"].chat.completions.create(**call_kwargs)
                self._fb._last_used_tier = idx
                return result
            except TRANSIENT_EXCEPTIONS as e:
                last_error = e
                if isinstance(e, APIError):
                    status = _extract_http_status(e)
                    if status and status in NON_TRANSIENT_STATUSES:
                        raise
                continue

        raise last_error or RuntimeError("All LLM tiers failed")


def _extract_http_status(error: Exception) -> int | None:
    for attr in ("status_code", "http_status"):
        val = getattr(error, attr, None)
        if val is not None:
            return val
    resp = getattr(error, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return None
