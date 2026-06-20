# -*- coding: UTF-8 -*-
"""Agent Memory — 3-tier memory: working + short-term (Redis TTL) + long-term (Redis Stack)."""

import json
import logging
import time

from app.config import AGENT_DEFAULT_MODEL

SHORT_TERM_TTL = 3600        # 1 hour
LONG_TERM_TTL = 2592000      # 30 days
MAX_SHORT_SUMMARY_CHARS = 600
MAX_LONG_ENTRIES = 50        # max long-term entries per user
MAX_RECALL_ITEMS = 5         # max items returned per recall
MEMORY_PROMPT_HEADER = "## 历史记忆"


class MemoryManager:
    """3-tier memory: working (in-memory, managed externally), short-term
    (Redis TTL 1h), long-term (Redis hash with optional vector search, 30d).

    Usage::

        mgr = MemoryManager(llm_client)
        mgr.remember(user_id, session_id, messages, summary)
        ctx = mgr.recall(user_id, query)
        # ctx.prompt → injected into system prompt
    """

    def __init__(self, llm_client=None, model: str = AGENT_DEFAULT_MODEL):
        self.llm = llm_client
        self.model = model

    # ── Redis helpers ────────────────────────────────────────────────────

    @staticmethod
    def _get_redis(db: int = 5):
        """Get Redis client for the given DB number."""
        try:
            from app.util.redis_utils import get_redis
            return get_redis(db=db)
        except Exception:
            return None

    @staticmethod
    def _short_key(user_id: str) -> str:
        return f"mem:short:{user_id}"

    @staticmethod
    def _long_index_key(user_id: str) -> str:
        return f"mem:long:{user_id}"

    @staticmethod
    def _long_entry_key(user_id: str, session_id: str) -> str:
        return f"mem:long:{user_id}:{session_id}"

    # ── Public API ───────────────────────────────────────────────────────

    def remember(self, user_id: str, session_id: str, messages: list,
                 summary: str = "") -> dict:
        """Persist session memory after a conversation completes.

        Short-term: stores LLM summary + recent highlights in Redis (TTL 1h).
        Long-term: appends session to user's long-term memory index (TTL 30d).

        Returns the memory data dict that was stored.
        """
        r = self._get_redis(db=5)
        if not r:
            return {}

        # Build summary if not provided
        effective_summary = summary or ""
        if not effective_summary and messages:
            effective_summary = self._build_summary(messages)

        # Extract key entities / topics from messages
        topics = self._extract_topics(messages)

        short_data = {
            "summary": effective_summary[:MAX_SHORT_SUMMARY_CHARS],
            "topics": topics[:10],
            "session_id": session_id,
            "msg_count": len(messages),
            "updated_at": int(time.time()),
        }

        # Store short-term
        try:
            r.setex(self._short_key(user_id), SHORT_TERM_TTL,
                    json.dumps(short_data, ensure_ascii=False))
        except Exception:
            logging.debug("MemoryManager: short-term store failed for %s", user_id)

        # Store long-term entry
        try:
            self._store_long_term(r, user_id, session_id, short_data)
        except Exception:
            logging.debug("MemoryManager: long-term store failed for %s", user_id)

        return short_data

    def recall(self, user_id: str, query: str = "",
               limit: int = MAX_RECALL_ITEMS) -> "MemoryContext":
        """Recall memories for a user across short-term and long-term stores.

        Args:
            user_id: user identifier
            query: optional search query to focus recall
            limit: max long-term entries to return

        Returns:
            MemoryContext with prompt text and structured data.
        """
        r = self._get_redis(db=5)
        if not r:
            return MemoryContext("", [])

        items = []

        # 1. Short-term memory
        try:
            raw = r.get(self._short_key(user_id))
            if raw:
                data = json.loads(raw)
                items.append({
                    "source": "short_term",
                    "summary": data.get("summary", ""),
                    "topics": data.get("topics", []),
                    "session_id": data.get("session_id", ""),
                    "freshness": "recent",
                })
        except Exception:
            logging.debug("MemoryManager: short-term recall failed for %s", user_id)

        # 2. Long-term memory — keyword match against stored entries
        try:
            long_items = self._search_long_term(r, user_id, query, limit)
            items.extend(long_items)
        except Exception:
            logging.debug("MemoryManager: long-term recall failed for %s", user_id)

        prompt = self._format_recall_prompt(items)
        return MemoryContext(prompt, items)

    def forget(self, user_id: str, session_id: str = None):
        """Clear memory for a user, or a specific session."""
        r = self._get_redis(db=5)
        if not r:
            return

        if session_id:
            # Forget specific long-term entry
            try:
                r.delete(self._long_entry_key(user_id, session_id))
                r.zrem(self._long_index_key(user_id), session_id)
            except Exception:
                pass
        else:
            # Forget everything for this user
            try:
                r.delete(self._short_key(user_id))
                # Clean up long-term index + all entries
                index_key = self._long_index_key(user_id)
                members = r.zrange(index_key, 0, -1)
                for sid in members:
                    r.delete(self._long_entry_key(user_id, sid))
                r.delete(index_key)
            except Exception:
                pass

    def update_short_term(self, user_id: str, summary: str = "",
                          topics: list = None):
        """Update just the short-term memory without a full persist cycle."""
        r = self._get_redis(db=5)
        if not r:
            return
        try:
            key = self._short_key(user_id)
            existing = {}
            raw = r.get(key)
            if raw:
                existing = json.loads(raw)
            if summary:
                existing["summary"] = summary[:MAX_SHORT_SUMMARY_CHARS]
            if topics:
                existing["topics"] = topics[:10]
            existing["updated_at"] = int(time.time())
            r.setex(key, SHORT_TERM_TTL, json.dumps(existing, ensure_ascii=False))
        except Exception:
            pass

    # ── Internal: summary generation ─────────────────────────────────────

    def _build_summary(self, messages: list) -> str:
        """Generate a concise summary from recent messages using LLM."""
        if not self.llm:
            return self._fallback_summary(messages)

        # Collect the last few user + assistant exchanges
        lines = []
        for m in messages[-20:]:
            role = m.get("role", "")
            content = (m.get("content") or "")[:300]
            if role == "user":
                lines.append(f"用户: {content}")
            elif role == "assistant":
                lines.append(f"助手: {content}")

        if not lines:
            return ""

        dialog = "\n".join(lines)
        system = (
            "你是记忆摘要专家。将以下对话总结为一句话（不超过100字），"
            "保留用户做了什么操作、关键结果和重要数据。只输出摘要本身。"
        )

        try:
            resp = self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": dialog[:3000]},
                ],
                temperature=0.1, max_tokens=200, timeout=15,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            logging.debug("MemoryManager: LLM summary failed, using fallback")
            return self._fallback_summary(messages)

    @staticmethod
    def _fallback_summary(messages: list) -> str:
        """Fallback: extract last few user messages as summary."""
        user_msgs = []
        for m in messages[-10:]:
            if m.get("role") == "user":
                content = (m.get("content") or "").strip()
                if content:
                    user_msgs.append(content)
        if user_msgs:
            return "用户关注: " + "; ".join(user_msgs[-3:])
        return ""

    @staticmethod
    def _extract_topics(messages: list) -> list:
        """Extract topic keywords from messages (rule-based, zero token cost)."""
        import re
        topics = set()
        keyword_map = {
            "画布": ["canvas", "画布", "图形", "节点", "矩形", "圆形", "连线",
                    "流程图", "架构图", "思维导图", "布局"],
            "蓝图": ["blueprint", "蓝图", "保存", "加载", "导出", "导入"],
            "搜索": ["web_search", "搜索", "新闻", "查询"],
            "文件": ["file", "文件", "上传", "下载", "文档", "excel", "docx"],
            "代码": ["code", "代码", "JS", "javascript", "生成"],
            "地图": ["map", "地图", "路线", "地点", "导航", "geocode"],
        }
        text = " ".join(
            (str(m.get("content", "")) or "") for m in messages[-20:]
        ).lower()

        for topic, keywords in keyword_map.items():
            for kw in keywords:
                if kw.lower() in text:
                    topics.add(topic)
                    break
        return list(topics)[:8]

    # ── Internal: long-term storage ──────────────────────────────────────

    def _store_long_term(self, r, user_id: str, session_id: str,
                         short_data: dict):
        """Store a session entry in the long-term memory index."""
        index_key = self._long_index_key(user_id)
        entry_key = self._long_entry_key(user_id, session_id)

        entry = {
            "summary": short_data.get("summary", ""),
            "topics": short_data.get("topics", []),
            "msg_count": short_data.get("msg_count", 0),
            "stored_at": int(time.time()),
        }
        r.setex(entry_key, LONG_TERM_TTL, json.dumps(entry, ensure_ascii=False))
        r.zadd(index_key, {session_id: time.time()})

        # TTL on the index too
        r.expire(index_key, LONG_TERM_TTL)

        # Trim old entries
        count = r.zcard(index_key)
        if count > MAX_LONG_ENTRIES:
            to_remove = count - MAX_LONG_ENTRIES
            oldest = r.zrange(index_key, 0, to_remove - 1)
            for sid in oldest:
                r.delete(self._long_entry_key(user_id, sid))
            r.zremrangebyrank(index_key, 0, to_remove - 1)

    def _search_long_term(self, r, user_id: str, query: str = "",
                          limit: int = MAX_RECALL_ITEMS) -> list:
        """Search long-term memory for relevant past sessions.

        Tries FT.SEARCH (vector) first; falls back to topic/keyword matching.
        """
        index_key = self._long_index_key(user_id)
        session_ids = r.zrange(index_key, -limit, -1)  # most recent

        if not session_ids:
            return []

        items = []
        for sid in reversed(session_ids):
            raw = r.get(self._long_entry_key(user_id, sid))
            if not raw:
                continue
            try:
                data = json.loads(raw)
                # Simple relevance: topic overlap with query
                relevance = self._compute_relevance(data, query)
                if relevance > 0 or not query:
                    items.append({
                        "source": "long_term",
                        "summary": data.get("summary", ""),
                        "topics": data.get("topics", []),
                        "session_id": sid,
                        "freshness": "older",
                        "relevance": relevance,
                    })
            except json.JSONDecodeError:
                continue

        # Sort by relevance (highest first), then recency
        items.sort(key=lambda x: (x.get("relevance", 0), x.get("session_id", "")),
                   reverse=True)
        return items[:limit]

    @staticmethod
    def _compute_relevance(entry: dict, query: str) -> float:
        """Simple relevance score based on topic/keyword overlap."""
        if not query:
            return 0.0
        query_lower = query.lower()
        score = 0.0
        topics = entry.get("topics", [])
        for topic in topics:
            if topic.lower() in query_lower or any(
                w in query_lower for w in topic.lower().split()
            ):
                score += 1.0
        summary = entry.get("summary", "").lower()
        if summary:
            for word in query_lower.split():
                if len(word) >= 2 and word in summary:
                    score += 0.3
        return min(score, 5.0)

    @staticmethod
    def _format_recall_prompt(items: list) -> str:
        """Format recalled memory items into a prompt string."""
        if not items:
            return ""

        # Deduplicate by summary content
        seen = set()
        unique = []
        for item in items:
            s = item.get("summary", "")
            if s and s not in seen:
                seen.add(s)
                unique.append(item)

        if not unique:
            return ""

        parts = [MEMORY_PROMPT_HEADER]
        for i, item in enumerate(unique[:MAX_RECALL_ITEMS], 1):
            freshness = "最近" if item.get("freshness") == "recent" else "历史"
            parts.append(f"{i}. [{freshness}] {item.get('summary', '')}")

        return "\n".join(parts) + "\n"


class MemoryContext:
    """Result of a memory recall operation."""

    def __init__(self, prompt: str = "", items: list = None):
        self.prompt = prompt
        self.items = items or []

    def __bool__(self):
        return bool(self.prompt)

    def to_dict(self) -> dict:
        return {"prompt": self.prompt, "items": self.items}
