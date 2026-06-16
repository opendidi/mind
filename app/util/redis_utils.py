# -*- coding: UTF-8 -*-
"""共享 Redis 连接池管理 — 统一管理 host/port/connection 参数。

用法:
    from app.util.redis_utils import get_redis

    r = get_redis(db=3)        # agent 流式队列
    r = get_redis(db=4)        # 搜索缓存
    r = get_redis(db=5)        # 速率限制
"""

import redis

from app.config import redis_config

# 不同 DB 号复用同一批连接池参数（按 DB 号缓存 ConnectionPool 实例）
_pools: dict[int, redis.ConnectionPool] = {}
_pool_lock = None  # lazy-init


def _get_lock():
    import threading

    global _pool_lock
    if _pool_lock is None:
        _pool_lock = threading.Lock()
    return _pool_lock


def get_redis(db: int = 0, max_connections: int = 30) -> redis.Redis:
    """获取指定 DB 号的 Redis 客户端（线程安全，连接池复用）。

    Args:
        db: Redis 数据库编号（0-15）
        max_connections: 连接池最大连接数（默认 30）
    """
    pool = _pools.get(db)
    if pool is None:
        with _get_lock():
            pool = _pools.get(db)
            if pool is None:
                pool = redis.ConnectionPool(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    password=redis_config.get("password") or None,
                    db=db,
                    decode_responses=True,
                    max_connections=max_connections,
                )
                _pools[db] = pool
    return redis.Redis(connection_pool=pool)
