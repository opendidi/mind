# -*- coding: UTF-8 -*-
"""CanvasShadow — 后端画布影子状态，支持跨轮次 ID 校验和状态追踪。

通过维护轻量后端画布模型，解决以下问题：
1. 跨轮次 pen ID 校验（Agent 知道哪些 pen 存在）
2. 每次请求同步时的状态 diff/merge
3. Redis 持久化（30 分钟 TTL）
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field


@dataclass
class PenShadow:
    """轻量 pen 影子记录。"""

    pen_id: str
    type: str = "rectangle"
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 60.0

    def to_dict(self) -> dict:
        return {
            "pen_id": self.pen_id,
            "type": self.type,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PenShadow":
        return cls(
            pen_id=d.get("pen_id", d.get("id", "")),
            type=d.get("type", "rectangle"),
            text=d.get("text", ""),
            x=d.get("x", 0),
            y=d.get("y", 0),
            width=d.get("width", 100),
            height=d.get("height", 60),
        )


@dataclass
class LineShadow:
    """轻量 line 影子记录。"""

    from_pen: str
    to_pen: str
    line_id: str = ""

    def to_dict(self) -> dict:
        return {"from_pen": self.from_pen, "to_pen": self.to_pen, "line_id": self.line_id}

    @classmethod
    def from_dict(cls, d: dict) -> "LineShadow":
        return cls(
            from_pen=d.get("from_pen", d.get("from", "")),
            to_pen=d.get("to_pen", d.get("to", "")),
            line_id=d.get("line_id", ""),
        )


@dataclass
class CanvasShadow:
    """画布影子状态 — 后端维护的轻量画布模型。"""

    pens: dict = field(default_factory=dict)  # pen_id -> PenShadow
    lines: dict = field(default_factory=dict)  # composite key -> LineShadow
    version: int = 0
    last_sync_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _dirty: bool = field(default=False, repr=False)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_clean(self):
        """Clear dirty flag after successful persistence."""
        self._dirty = False

    def _bump(self):
        """Increment version and mark dirty. Caller must hold _lock."""
        self._dirty = True
        self.version += 1

    def add_pen(self, pen_id: str, pen_data: dict):
        """Add or update a pen in the shadow."""
        with self._lock:
            self.pens[pen_id] = PenShadow(
                pen_id=pen_id,
                type=pen_data.get("type", "rectangle"),
                text=pen_data.get("text", ""),
                x=pen_data.get("x", 0),
                y=pen_data.get("y", 0),
                width=pen_data.get("width", 100),
                height=pen_data.get("height", 60),
            )
            self._bump()

    def has_pen(self, pen_id: str) -> bool:
        """Check if a pen exists in the shadow."""
        return pen_id in self.pens

    def get_pen(self, pen_id: str) -> "PenShadow | None":
        """Get a pen shadow by ID, or None if not found."""
        return self.pens.get(pen_id)

    def remove_pen(self, pen_id: str):
        """Remove a pen and its connected lines from the shadow."""
        with self._lock:
            if pen_id in self.pens:
                del self.pens[pen_id]
                # Also remove connected lines
                self.lines = {
                    k: v
                    for k, v in self.lines.items()
                    if v.from_pen != pen_id and v.to_pen != pen_id
                }
                self._bump()

    def clear(self):
        """Clear all pens and lines from the shadow."""
        with self._lock:
            self.pens.clear()
            self.lines.clear()
            self.version += 1

    def add_line(self, line_id: str, from_pen: str, to_pen: str):
        """Add a line to the shadow."""
        with self._lock:
            key = line_id or f"{from_pen}->{to_pen}"
            self.lines[key] = LineShadow(from_pen=from_pen, to_pen=to_pen, line_id=line_id)
            self.version += 1

    def sync_from_snapshot(self, snapshot: list[dict]):
        """全量同步：用前端快照更新 shadow。

        保留 agent 创建的 pen 同时移除用户手动删除的 pen。
        """
        if not snapshot:
            return
        with self._lock:
            incoming_ids = set()
            for p in snapshot:
                pid = p.get("id", p.get("pen_id", ""))
                if not pid:
                    continue
                incoming_ids.add(pid)
                if pid in self.pens:
                    existing = self.pens[pid]
                    existing.text = p.get("text", existing.text)
                    existing.x = p.get("x", existing.x)
                    existing.y = p.get("y", existing.y)
                    existing.width = p.get("width", existing.width)
                    existing.height = p.get("height", existing.height)
                else:
                    self.pens[pid] = PenShadow.from_dict(p)
            # Remove pens not in snapshot (user deleted them manually)
            removed = [pid for pid in self.pens if pid not in incoming_ids]
            for pid in removed:
                del self.pens[pid]
            if removed or not self.pens:
                self._bump()

    def to_dict(self) -> dict:
        """Serialize shadow to dict for Redis storage."""
        return {
            "pens": {k: v.to_dict() for k, v in self.pens.items()},
            "lines": {k: v.to_dict() for k, v in self.lines.items()},
            "version": self.version,
            "last_sync_at": self.last_sync_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CanvasShadow":
        """Deserialize shadow from dict (loaded from Redis)."""
        shadow = cls(version=d.get("version", 0), last_sync_at=d.get("last_sync_at", 0))
        for k, v in d.get("pens", {}).items():
            shadow.pens[k] = PenShadow.from_dict(v)
        for k, v in d.get("lines", {}).items():
            shadow.lines[k] = LineShadow.from_dict(v)
        return shadow


# ── Redis persistence ──

_CANVAS_SHADOW_TTL = 1800  # 30 minutes


def _get_shadow_redis():
    """Get Redis client for canvas shadow storage (db=5)."""
    try:
        from app.util.redis_utils import get_redis

        return get_redis(db=5)
    except Exception:
        return None


def load_canvas_shadow(session_id: str) -> CanvasShadow:
    """Load CanvasShadow from Redis, or return empty shadow."""
    r = _get_shadow_redis()
    if r:
        try:
            key = f"canvas_shadow:{session_id}"
            raw = r.get(key)
            if raw:
                data = json.loads(raw) if isinstance(raw, bytes) else json.loads(raw)
                logging.debug(
                    "CanvasShadow loaded for session %s, v%d",
                    session_id,
                    data.get("version", 0),
                )
                return CanvasShadow.from_dict(data)
        except Exception:
            logging.warning(
                "CanvasShadow load failed for session %s", session_id, exc_info=True
            )
    return CanvasShadow()


def save_canvas_shadow(session_id: str, shadow: CanvasShadow):
    """Persist CanvasShadow to Redis with 30-minute TTL."""
    shadow.last_sync_at = time.time()
    r = _get_shadow_redis()
    if r:
        try:
            key = f"canvas_shadow:{session_id}"
            r.setex(
                key, _CANVAS_SHADOW_TTL, json.dumps(shadow.to_dict(), ensure_ascii=False)
            )
        except Exception:
            logging.warning(
                "CanvasShadow save failed for session %s", session_id, exc_info=True
            )
