# -*- coding: UTF-8 -*-
"""LLM client builder — lazy-init with fallback tiers."""

import threading

from openai import OpenAI

from app.config import LLM_TIMEOUT, deepseek_config, fallback1_config, fallback2_config


def _build_llm_client():
    """Build primary LLM client with optional fallback tiers from env config."""
    tiers = []
    if deepseek_config["key"]:
        tiers.append({
            "client": OpenAI(
                api_key=deepseek_config["key"],
                base_url=deepseek_config["base_url"],
                timeout=LLM_TIMEOUT,
            ),
            "model": "deepseek-chat",
        })
    for fb_cfg in [fallback1_config, fallback2_config]:
        if fb_cfg["key"] and fb_cfg["model"]:
            tiers.append({
                "client": OpenAI(
                    api_key=fb_cfg["key"],
                    base_url=fb_cfg["base_url"],
                    timeout=LLM_TIMEOUT,
                ),
                "model": fb_cfg["model"],
            })
    if not tiers:
        raise RuntimeError(
            "未配置任何 LLM API Key。请在 .env 中设置 DEEPSEEK_API_KEY，"
            "或设置 FALLBACK1_API_KEY / FALLBACK2_API_KEY 作为备用。"
        )
    if len(tiers) == 1:
        return tiers[0]["client"]
    from app.util.agent_fallback import FallbackLLM
    return FallbackLLM(tiers)


_llm_client = None
_llm_client_lock = threading.Lock()  # init at module level — no race


def get_llm_client():
    """Lazy-init LLM client singleton."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    with _llm_client_lock:
        if _llm_client is None:
            _llm_client = _build_llm_client()
        return _llm_client
