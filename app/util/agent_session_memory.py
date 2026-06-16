# -*- coding: UTF-8 -*-
"""SessionMemory — cross-session entity persistence and restoration (simplified for mind)."""

import json
import logging
import time

MEMORY_TTL_REDIS = 3600
MEMORY_MAX_SUMMARY_CHARS = 500


class SessionMemory:
    """Manage cross-session conversation memory using Redis with in-memory fallback."""

    # In-memory fallback storage
    _mem_store: dict[str, dict] = {}

    @staticmethod
    def restore(user_id: str) -> str:
        """Restore session memory for a user. Returns a prompt string or empty string."""
        # Try Redis first
        try:
            from app.util.redis_utils import get_redis
            r = get_redis(db=5)
            cached = r.get(f"agent:memory:{user_id}")
            if cached:
                data = json.loads(cached)
                entities = data.get("entities", {})
                summary = data.get("summary", "")
                if entities or summary:
                    return SessionMemory._format_prompt(entities, summary)
        except Exception:
            logging.debug("SessionMemory Redis cache miss for %s", user_id)

        # Fall back to in-memory
        data = SessionMemory._mem_store.get(user_id)
        if data:
            return SessionMemory._format_prompt(data.get("entities", {}), data.get("summary", ""))
        return ""

    @staticmethod
    def persist(user_id: str, session_id: str, messages: list, summary: str = ""):
        """Persist session memory after a chat completes."""
        entities = {}
        summary = (summary or "")[:MEMORY_MAX_SUMMARY_CHARS]
        if not entities and not summary:
            return

        data = {"entities": entities, "summary": summary, "updated_at": time.time()}

        # Redis cache
        try:
            from app.util.redis_utils import get_redis
            r = get_redis(db=5)
            r.setex(f"agent:memory:{user_id}", MEMORY_TTL_REDIS, json.dumps(data, ensure_ascii=False))
        except Exception:
            logging.debug("SessionMemory Redis cache set failed for %s", user_id)

        # In-memory fallback
        SessionMemory._mem_store[user_id] = data

    @staticmethod
    def _format_prompt(entities: dict, summary: str) -> str:
        if not entities and not summary:
            return ""
        parts = ["## 上次会话记忆"]
        if summary:
            parts.append(f"会话摘要: {summary}")
        return "\n".join(parts)
