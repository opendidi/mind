# -*- coding: UTF-8 -*-
"""StateStore — WorldState 的 Redis 持久化层

提供 state 的保存/加载/版本管理。
Redis 不可用时优雅降级为内存存储。
"""

import json
import logging
import time
from typing import Optional

from app.util.agent.state import WorldState
from app.util.agent.constants import SNAPSHOT_TTL, STATE_MAX_VERSIONS, STATE_TTL


class StateStore:
    """WorldState 的 Redis 持久化存储。

    Redis key 模式：
        state:current:{user_id}              — 当前 WorldState JSON (TTL 1h)
        state:snapshot:{user_id}:{version}   — 版本快照 (TTL 24h)
        state:log:{user_id}                  — 版本索引 ZSET

    若 Redis 不可用，回退到进程内内存 dict。
    """

    def __init__(self, ttl: int = STATE_TTL, snapshot_ttl: int = SNAPSHOT_TTL):
        self._ttl = ttl
        self._snapshot_ttl = snapshot_ttl
        self._mem_store: dict = {}  # 内存回退

    # ── Redis 连接 ──────────────────────────────────────────────────────

    @staticmethod
    def _get_redis(db: int = 5):
        """获取 Redis 客户端。"""
        try:
            from app.util.redis_utils import get_redis

            return get_redis(db=db)
        except Exception:
            return None

    # ── Redis key 工具 ──────────────────────────────────────────────────

    @staticmethod
    def _current_key(user_id: str) -> str:
        return f"state:current:{user_id}"

    @staticmethod
    def _snapshot_key(user_id: str, version: int) -> str:
        return f"state:snapshot:{user_id}:{version}"

    @staticmethod
    def _log_key(user_id: str) -> str:
        return f"state:log:{user_id}"

    # ── 公共 API ────────────────────────────────────────────────────────

    def save(self, state: WorldState) -> bool:
        """保存当前 WorldState 到 Redis。自动递增版本号。"""
        state.bump_version()
        data = json.dumps(state.to_dict(), ensure_ascii=False)

        r = self._get_redis()
        if not r:
            self._mem_store[state.user_id] = data
            return True

        try:
            r.setex(self._current_key(state.user_id), self._ttl, data)
            r.zadd(self._log_key(state.user_id), {str(state.version): time.time()})
            r.expire(self._log_key(state.user_id), self._snapshot_ttl)
            return True
        except Exception:
            logging.debug("StateStore save failed for user=%s", state.user_id)
            self._mem_store[state.user_id] = data
            return False

    def load(self, user_id: str) -> Optional[WorldState]:
        """加载用户当前 WorldState。不存在时返回 None。"""
        r = self._get_redis()
        if not r:
            if user_id in self._mem_store:
                return WorldState.from_dict(json.loads(self._mem_store[user_id]))
            return None

        try:
            raw = r.get(self._current_key(user_id))
            if raw:
                return WorldState.from_dict(json.loads(raw))
        except Exception:
            logging.debug("StateStore load failed for user=%s", user_id)

        # 回退到内存
        if user_id in self._mem_store:
            return WorldState.from_dict(json.loads(self._mem_store[user_id]))
        return None

    def load_version(self, user_id: str, version: int) -> Optional[WorldState]:
        """加载指定版本的 WorldState 快照。"""
        r = self._get_redis()
        if not r:
            return None

        try:
            raw = r.get(self._snapshot_key(user_id, version))
            if raw:
                return WorldState.from_dict(json.loads(raw))
        except Exception:
            logging.debug("StateStore load_version v=%d failed for user=%s", version, user_id)
        return None

    def save_snapshot(self, state: WorldState) -> bool:
        """保存 WorldState 版本快照（用于回滚/审计）。"""
        r = self._get_redis()
        if not r:
            return False

        try:
            key = self._snapshot_key(state.user_id, state.version)
            data = json.dumps(state.to_dict(), ensure_ascii=False)
            r.setex(key, self._snapshot_ttl, data)
            # 修剪旧快照
            log_key = self._log_key(state.user_id)
            count = r.zcard(log_key)
            if count > STATE_MAX_VERSIONS:
                to_remove = count - STATE_MAX_VERSIONS
                oldest = r.zrange(log_key, 0, to_remove - 1)
                for v in oldest:
                    r.delete(self._snapshot_key(state.user_id, v))
                r.zremrangebyrank(log_key, 0, to_remove - 1)
            return True
        except Exception:
            logging.debug("StateStore save_snapshot failed for user=%s v=%d", state.user_id, state.version)
            return False

    def list_versions(self, user_id: str, limit: int = 10) -> list:
        """列出用户最近的状态版本号。"""
        r = self._get_redis()
        if not r:
            return []
        try:
            versions = r.zrange(self._log_key(user_id), -limit, -1)
            return [int(v) for v in versions]
        except Exception:
            return []

    def delete(self, user_id: str) -> bool:
        """清除用户所有状态数据。"""
        r = self._get_redis()
        if not r:
            self._mem_store.pop(user_id, None)
            return True

        try:
            r.delete(self._current_key(user_id))
            # 清除所有快照
            log_key = self._log_key(user_id)
            versions = r.zrange(log_key, 0, -1)
            for v in versions:
                r.delete(self._snapshot_key(user_id, v))
            r.delete(log_key)
            self._mem_store.pop(user_id, None)
            return True
        except Exception:
            return False

    def exists(self, user_id: str) -> bool:
        """检查用户是否有已保存的状态。"""
        r = self._get_redis()
        if not r:
            return user_id in self._mem_store
        try:
            return bool(r.exists(self._current_key(user_id)))
        except Exception:
            return user_id in self._mem_store
