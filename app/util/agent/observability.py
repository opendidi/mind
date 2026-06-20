# -*- coding: UTF-8 -*-
"""Agent Observability — structured logging + metrics + health checks.

Builds on AgentTracer's span tree. Each span flushed to JSON log.
Redis metrics aggregated for dashboards/alerting.
"""

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ── Structured Trace Logger ─────────────────────────────────────────────

@dataclass
class TraceEvent:
    trace_id: str
    span_name: str
    user_id: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: float = 0.0
    status: str = "ok"
    attempt: int = 1
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""

    def to_json(self) -> str:
        d = {k: v for k, v in self.__dict__.items() if v not in ("", 0, 0.0, {}, [], 1)}
        return json.dumps(d, ensure_ascii=False)


class TraceLogger:
    """Emit structured JSON log events for each span."""

    _logger = logging.getLogger("agent.trace")

    @staticmethod
    def emit(event: TraceEvent):
        event.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        TraceLogger._logger.info(event.to_json())

    @staticmethod
    def from_tracer(tracer, span_name: str, model: str = "",
                    tokens_in: int = 0, tokens_out: int = 0,
                    attempt: int = 1, **meta) -> TraceEvent:
        """Build TraceEvent from an AgentTracer instance."""
        return TraceEvent(
            trace_id=tracer.trace_id if tracer else "",
            span_name=span_name,
            user_id=tracer.user_id if tracer else "",
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            attempt=attempt,
            metadata=meta,
        )


# ── Metrics Collector ───────────────────────────────────────────────────

_METRICS_TTL = 300
_metrics_lock = threading.Lock()


class MetricsCollector:
    """In-memory rolling window metrics with optional Redis persistence."""

    # Rolling window buckets (5min granularity, keep 1 hour)
    _buckets: dict = defaultdict(lambda: defaultdict(int))
    _bucket_ts: dict = {}  # bucket_key -> timestamp

    @classmethod
    def record(cls, metric: str, value: int = 1, labels: dict = None):
        """Record a counter metric."""
        with _metrics_lock:
            now = int(time.time() / _METRICS_TTL) * _METRICS_TTL
            labels = labels or {}
            for bucket_key, counter_key in cls._expand_keys(metric, labels):
                cls._buckets[bucket_key][counter_key] += value
                cls._bucket_ts[bucket_key] = now
        cls._try_flush_redis(metric, value, labels)

    @classmethod
    def snapshot(cls) -> dict:
        """Return current metrics snapshot."""
        with _metrics_lock:
            now = int(time.time() / _METRICS_TTL) * _METRICS_TTL
            result = {}
            stale = []
            for bucket_key, counters in cls._buckets.items():
                if cls._bucket_ts.get(bucket_key, 0) < now - _METRICS_TTL * 2:
                    stale.append(bucket_key)
                    continue
                prefix = bucket_key.split(":", 1)[0]
                if prefix not in result:
                    result[prefix] = {}
                for k, v in counters.items():
                    result[prefix][k] = v
            for bk in stale:
                cls._buckets.pop(bk, None)
            return result

    @staticmethod
    def _expand_keys(metric: str, labels: dict) -> list:
        """Expand metric + labels into bucket/counter keys."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        bucket = f"{metric}:{label_str}" if label_str else metric
        return [(bucket, "count")]

    @classmethod
    def _try_flush_redis(cls, metric: str, value: int, labels: dict = None):
        """Persist counter to Redis if available."""
        try:
            from app.util.redis_utils import get_redis
            r = get_redis(db=5)
            if r:
                key = f"agent:metrics:{metric}"
                r.incrby(key, value)
                r.expire(key, 3600)
        except Exception:
            pass


# ── Health Checker ──────────────────────────────────────────────────────

class HealthChecker:
    """Check health of each layer in the Agent pipeline."""

    @staticmethod
    def check_all() -> dict:
        return {
            "guard": HealthChecker._check_guard(),
            "memory": HealthChecker._check_memory(),
            "router": HealthChecker._check_router(),
            "executor": HealthChecker._check_executor(),
            "tools": HealthChecker._check_tools(),
            "timestamp": time.time(),
        }

    @staticmethod
    def _check_guard() -> dict:
        return {"status": "ok"}

    @staticmethod
    def _check_memory() -> dict:
        try:
            from app.util.redis_utils import get_redis
            r = get_redis(db=5)
            if r:
                r.ping()
                return {"status": "ok", "backend": "redis"}
        except Exception:
            pass
        return {"status": "degraded", "backend": "in-memory"}

    @staticmethod
    def _check_router() -> dict:
        return {"status": "ok"}

    @staticmethod
    def _check_executor() -> dict:
        status = "ok"
        try:
            from app.util.agent.tools import ToolRegistry
            tools = ToolRegistry.list_tools()
            enabled = sum(1 for _, e in tools if e)
            if enabled == 0:
                status = "degraded"
        except Exception:
            status = "error"
        return {"status": status}

    @staticmethod
    def _check_tools() -> dict:
        try:
            from app.util.agent.tools import ToolRegistry
            tools = ToolRegistry.list_tools()
            enabled = [n for n, e in tools if e]
            disabled = [n for n, e in tools if not e]
            return {
                "status": "ok" if enabled else "degraded",
                "enabled": enabled,
                "disabled": disabled,
            }
        except Exception:
            return {"status": "error", "enabled": [], "disabled": []}


# ── Convenience ─────────────────────────────────────────────────────────

_obs_instance: Optional["AgentObservability"] = None


class AgentObservability:
    """Per-request observability context.

    Usage:
        obs = AgentObservability(user_id="u1")
        obs.trace("guard", status="ok", duration_ms=1.2)
        obs.metric("llm_call", tokens_in=1200)
        obs.flush()
    """

    def __init__(self, user_id: str = "", trace_id: str = ""):
        import uuid
        self.trace_id = trace_id or str(uuid.uuid4())[:12]
        self.user_id = user_id
        self._events: list[TraceEvent] = []
        self._start_ts = time.time()

    def trace(self, span_name: str, model: str = "", tokens_in: int = 0,
              tokens_out: int = 0, duration_ms: float = 0.0, status: str = "ok",
              attempt: int = 1, **meta):
        event = TraceEvent(
            trace_id=self.trace_id, span_name=span_name, user_id=self.user_id,
            model=model, tokens_in=tokens_in, tokens_out=tokens_out,
            duration_ms=duration_ms, status=status, attempt=attempt, metadata=meta,
        )
        self._events.append(event)
        TraceLogger.emit(event)

    def metric(self, name: str, value: int = 1, **labels):
        MetricsCollector.record(name, value, labels if labels else None)

    def flush(self):
        total_ms = round((time.time() - self._start_ts) * 1000, 1)
        self.metric("request", 1, route="total")
        self.metric("request_duration_ms", total_ms)
        return {"trace_id": self.trace_id, "events": len(self._events), "total_ms": total_ms}
