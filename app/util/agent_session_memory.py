# -*- coding: UTF-8 -*-
"""SessionMemory — cross-session entity persistence and restoration (simplified for mind)."""

import json
import logging
import time

MEMORY_TTL_REDIS = 3600
MEMORY_MAX_SUMMARY_CHARS = 500
MEMORY_MAX_ENTRIES = 100  # max entries in in-memory fallback store


class SessionMemory:
    """Manage cross-session conversation memory using Redis with in-memory fallback."""

    # In-memory fallback storage (LRU: oldest entry evicted when full)
    _mem_store: dict[str, dict] = {}
    _mem_access_order: list[str] = []

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
            # LRU: move to end on access
            if user_id in SessionMemory._mem_access_order:
                SessionMemory._mem_access_order.remove(user_id)
            SessionMemory._mem_access_order.append(user_id)
            return SessionMemory._format_prompt(data.get("entities", {}), data.get("summary", ""))
        return ""

    @staticmethod
    def _extract_entities(messages: list) -> dict:
        """Extract key entities from messages (blueprint IDs, tool args, etc.)."""
        import re
        entities = {}
        for msg in messages:
            content = str(msg.get("content", "") or "")
            # Extract blueprint_id from tool calls or text
            for key in ("blueprint_id", "pen_id", "name"):
                m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', content)
                if m and key not in entities:
                    entities[key] = m.group(1)
        return entities

    @staticmethod
    def persist(user_id: str, session_id: str, messages: list, summary: str = ""):
        """Persist session memory after a chat completes."""
        entities = SessionMemory._extract_entities(messages)
        summary = (summary or "")[:MEMORY_MAX_SUMMARY_CHARS]
        if not entities and not summary:
            return

        data = {"entities": entities, "summary": summary, "updated_at": time.time()}

        # Redis cache
        try:
            from app.util.redis_utils import get_redis
            r = get_redis(db=5)
            if r:
                r.setex(f"agent:memory:{user_id}", MEMORY_TTL_REDIS, json.dumps(data, ensure_ascii=False))
        except Exception:
            logging.debug("SessionMemory Redis cache set failed for %s", user_id)

        # In-memory fallback with LRU eviction
        if user_id in SessionMemory._mem_store:
            SessionMemory._mem_access_order.remove(user_id)
        elif len(SessionMemory._mem_store) >= MEMORY_MAX_ENTRIES:
            evicted = SessionMemory._mem_access_order.pop(0) if SessionMemory._mem_access_order else None
            if evicted:
                SessionMemory._mem_store.pop(evicted, None)
                logging.debug("SessionMemory evicted: %s (max entries %d)", evicted, MEMORY_MAX_ENTRIES)
        SessionMemory._mem_store[user_id] = data
        SessionMemory._mem_access_order.append(user_id)

    @staticmethod
    def _format_prompt(entities: dict, summary: str) -> str:
        if not entities and not summary:
            return ""
        parts = ["## 上次会话记忆"]
        for k, v in entities.items():
            parts.append(f"- {k}: {v}")
        if summary:
            parts.append(f"会话摘要: {summary}")
        return "\n".join(parts)
