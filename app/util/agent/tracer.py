# -*- coding: UTF-8 -*-
"""AgentTracer — Span-tree tracing for full execution lifecycle observability."""

import contextlib
import glob
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

_TRACE_MAX_DIR_SIZE = 500 * 1024 * 1024  # 500 MB


def _enforce_trace_dir_limit(log_dir: str):
    """Remove oldest trace files if directory exceeds _TRACE_MAX_DIR_SIZE."""
    if not os.path.exists(log_dir):
        return
    files = sorted(glob.glob(os.path.join(log_dir, "trace_*.json")), key=os.path.getmtime)
    total = sum(os.path.getsize(f) for f in files)
    while total > _TRACE_MAX_DIR_SIZE and len(files) > 1:
        oldest = files.pop(0)
        total -= os.path.getsize(oldest)
        os.remove(oldest)
        logging.info(f"Tracer: removed old trace file {os.path.basename(oldest)} (dir size limit)")


@dataclass
class Span:
    span_id: str
    parent_id: Optional[str]
    name: str
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    status: str = "running"
    metadata: dict = field(default_factory=dict)
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "duration_ms": (round((self.end_ts - self.start_ts) * 1000, 1) if self.end_ts else None),
            "status": self.status,
            "metadata": self.metadata,
            "input_summary": _summarize(self.input),
            "output_summary": _summarize(self.output),
        }


def _summarize(d: dict, max_len: int = 200) -> str:
    s = json.dumps(d, ensure_ascii=False)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


class AgentTracer:
    def __init__(self, user_id: str = "", trace_id: str = ""):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.user_id = user_id
        self.spans: list[Span] = []
        self._lock = threading.Lock()
        self._tls = threading.local()

    @property
    def current_span_id(self) -> Optional[str]:
        stack = getattr(self._tls, "stack", None)
        return stack[-1] if stack else None

    def start_span(self, name: str, input: dict = None, parent_id: Optional[str] = None, **metadata) -> str:
        with self._lock:
            stack = getattr(self._tls, "stack", None)
            if stack is None:
                self._tls.stack = []
                stack = self._tls.stack
            effective_parent = parent_id if parent_id is not None else (stack[-1] if stack else None)
            span = Span(
                span_id=str(uuid.uuid4())[:8],
                parent_id=effective_parent,
                name=name,
                metadata=metadata,
                input=input or {},
            )
            self.spans.append(span)
            stack.append(span.span_id)
            return span.span_id

    def end_span(self, span_id: str, status: str = "ok", output: dict = None):
        with self._lock:
            for span in self.spans:
                if span.span_id == span_id:
                    span.end_ts = time.time()
                    span.status = status
                    span.output = output or {}
                    break
            stack = getattr(self._tls, "stack", None)
            if stack and stack[-1] == span_id:
                stack.pop()

    @contextlib.contextmanager
    def span(self, name: str, input: dict = None, **metadata):
        sid = self.start_span(name, input, **metadata)
        try:
            yield sid
            self.end_span(sid, "ok")
        except Exception:
            self.end_span(sid, "error")
            raise

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "spans": [s.to_dict() for s in self.spans],
            "total_duration_ms": (
                round((self.spans[-1].end_ts - self.spans[0].start_ts) * 1000, 1)
                if self.spans and self.spans[0].start_ts and self.spans[-1].end_ts
                else None
            ),
        }

    def flush(self):
        """Persist trace to local JSON file."""
        try:
            dump = json.dumps(self.to_dict(), ensure_ascii=False)
            log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
            os.makedirs(log_dir, exist_ok=True)
            existing = sorted(
                [f for f in os.listdir(log_dir) if f.startswith("trace_") and f.endswith(".json")],
                key=lambda f: os.path.getmtime(os.path.join(log_dir, f)),
            )
            for old in existing[:-49]:
                try:
                    os.remove(os.path.join(log_dir, old))
                except OSError:
                    pass
            fname = f"trace_{self.trace_id}.json"
            with open(os.path.join(log_dir, fname), "w", encoding="utf-8") as f:
                f.write(dump)
            _enforce_trace_dir_limit(log_dir)
            logging.info("AgentTracer trace saved to local file: logs/%s", fname)
        except Exception:
            logging.exception("AgentTracer local file flush failed")
