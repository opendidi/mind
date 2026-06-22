# -*- coding: UTF-8 -*-
"""Environment-aware executor — ThreadPoolExecutor with timeout support.

Simplified for mind project (no eventlet dependency).
"""

import threading as _threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError


class ExecutorTimeout(Exception):
    """Raised when a task exceeds its time limit."""

    pass


def get_pool(max_workers: int = 4, prefix: str = ""):
    """Return a ThreadPoolExecutor with the given parameters."""
    return ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=prefix)


def is_pool_shutdown(pool) -> bool:
    """Check whether a pool has been shut down."""
    return bool(getattr(pool, "_shutdown", 0))


# ── Managed Pool (auto-reset singleton) ─────────────────────────────────────


class ManagedPool:
    """Lazy-init executor pool with auto-reset on shutdown."""

    def __init__(self, max_workers: int = 4, prefix: str = ""):
        self._max_workers = max_workers
        self._prefix = prefix
        self._pool = None
        self._lock = _threading.Lock()

    def get(self):
        """Return a live pool, creating or recreating if shut down."""
        pool = self._pool
        if pool is None or is_pool_shutdown(pool):
            with self._lock:
                pool = self._pool
                if pool is None or is_pool_shutdown(pool):
                    pool = get_pool(max_workers=self._max_workers, prefix=self._prefix)
                    self._pool = pool
        return pool


def reset_pool_if_shutdown(pool_ref: list, lock, max_workers: int, prefix: str):
    """Check and recreate a singleton pool if it has been shut down."""
    pool = pool_ref[0]
    if pool is None or is_pool_shutdown(pool):
        with lock:
            pool = pool_ref[0]
            if pool is None or is_pool_shutdown(pool):
                pool = get_pool(max_workers=max_workers, prefix=prefix)
                pool_ref[0] = pool
    return pool


def run_with_timeout(func, timeout: float, *args, **kwargs):
    """Execute func(*args, **kwargs) with a timeout.

    Returns the function's return value, or raises ExecutorTimeout.
    """
    pool = get_pool(max_workers=16, prefix="agent-pool-")
    try:
        return pool.submit(func, *args, **kwargs).result(timeout=timeout)
    except FutureTimeoutError:
        raise ExecutorTimeout(f"Task timed out after {timeout}s")


def as_completed(futures: dict, timeout: float = None):
    """Yield (future, key) as each future completes."""
    from concurrent.futures import as_completed as cf_as_completed

    for f in cf_as_completed(futures):
        yield f, futures[f]


def is_eventlet() -> bool:
    """Always False for mind (no eventlet dependency)."""
    return False
