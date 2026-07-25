# -*- coding: UTF-8 -*-
"""StateSnapshot — WorldState 快照/回滚/diff

支持在执行前后拍摄状态快照，对比变更，以及在失败时回滚。
"""

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from app.util.agent.state import WorldState
from app.util.agent.state_reducer import StateMutation, StateReducer
from app.util.agent.state_store import StateStore


@dataclass
class StateSnapshot:
    """时间点状态快照。"""

    state: WorldState
    version: int
    created_at: float = field(default_factory=time.time)
    label: str = ""  # human-readable label

    def to_dict(self) -> dict:
        return {
            "state": self.state.to_dict(),
            "version": self.version,
            "created_at": self.created_at,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StateSnapshot":
        return cls(
            state=WorldState.from_dict(d["state"]),
            version=d.get("version", 0),
            created_at=d.get("created_at", time.time()),
            label=d.get("label", ""),
        )


class SnapshotManager:
    """WorldState 快照管理器。

    功能：
        - snapshot(): 拍摄当前状态快照
        - rollback(): 回滚到指定版本
        - diff(): 对比两个状态的变更
        - compare_versions(): 对比两个版本
    """

    def __init__(self, store: StateStore):
        self._store = store
        self._in_memory_snapshots: dict = {}  # {label: StateSnapshot}

    def snapshot(self, state: WorldState, label: str = "") -> StateSnapshot:
        """拍摄当前 WorldState 快照。

        同时保存到 Redis（版本快照）和进程内存（快速访问）。
        """
        snap = StateSnapshot(
            state=copy.deepcopy(state),
            version=state.version,
            label=label,
        )

        # 内存缓存
        if label:
            self._in_memory_snapshots[label] = snap

        # Redis 持久化
        try:
            self._store.save_snapshot(state)
        except Exception:
            logging.debug("SnapshotManager: Redis snapshot failed for label=%s", label)

        return snap

    def rollback(self, user_id: str, target_version: int) -> Optional[WorldState]:
        """回滚到指定版本。从 Redis 加载版本快照。"""
        state = self._store.load_version(user_id, target_version)
        if state is None:
            logging.warning("SnapshotManager: rollback failed — version %d not found", target_version)
            return None

        # 恢复为当前状态
        self._store.save(state)
        logging.info("SnapshotManager: rolled back user=%s to v%d", user_id, target_version)
        return state

    def get_snapshot(self, label: str) -> Optional[StateSnapshot]:
        """获取标记过的内存快照。"""
        return self._in_memory_snapshots.get(label)

    def diff(self, prev: WorldState, current: WorldState) -> list:
        """对比两个 WorldState，返回变更列表。

        Returns:
            list of dict: [{path, old_value, new_value, changed}]
        """
        changes = []
        prev_dict = prev.to_dict()
        curr_dict = current.to_dict()

        all_keys = set(prev_dict.keys()) | set(curr_dict.keys())
        for key in sorted(all_keys):
            old_val = prev_dict.get(key)
            new_val = curr_dict.get(key)
            if old_val != new_val:
                changes.append(
                    {
                        "path": key,
                        "old_value": old_val,
                        "new_value": new_val,
                        "changed": True,
                    }
                )
        return changes

    def compare_versions(self, user_id: str, v1: int, v2: int) -> list:
        """对比两个版本的状态差异。"""
        state_v1 = self._store.load_version(user_id, v1)
        state_v2 = self._store.load_version(user_id, v2)

        if state_v1 is None or state_v2 is None:
            return []

        return self.diff(state_v1, state_v2)

    def get_latest_snapshot(self, user_id: str) -> Optional[StateSnapshot]:
        """获取用户最新的持久化快照。"""
        versions = self._store.list_versions(user_id, limit=1)
        if not versions:
            return None

        state = self._store.load_version(user_id, versions[0])
        if state is None:
            return None

        return StateSnapshot(state=state, version=versions[0], label=f"restored_v{versions[0]}")

    def clear_in_memory(self) -> None:
        """清除内存快照缓存。"""
        self._in_memory_snapshots.clear()

    # ── 用户面向的静态便捷方法 ──

    @staticmethod
    def _make_store() -> StateStore:
        """创建默认的 StateStore 实例。"""
        return StateStore()

    @staticmethod
    def list_versions(session_id: str) -> list[dict]:
        """列出可用的快照版本及元数据。

        Returns:
            list[dict]: [{"version": N, "time": "...", "description": "..."}, ...]
        """
        store = SnapshotManager._make_store()
        versions = store.list_versions(session_id)
        result = []
        for v in versions:
            raw = store.load_version(session_id, v)
            if raw is not None:
                snap_meta = raw.extra.get("_snapshot", {})
                created_at = snap_meta.get("created_at", "")
                description = snap_meta.get("description", "")
                # 格式化时间戳为可读字符串
                time_str = ""
                if created_at:
                    try:
                        from datetime import datetime

                        time_str = datetime.fromtimestamp(float(created_at)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except Exception:
                        time_str = str(created_at)
                result.append(
                    {
                        "version": v,
                        "time": time_str,
                        "description": description,
                    }
                )
            else:
                result.append({"version": v, "time": "", "description": ""})
        return result

    @staticmethod
    def restore(session_id: str, target_version: int) -> dict | None:
        """回滚到指定版本的状态，返回恢复的世界状态数据字典。

        Returns:
            dict: 恢复后的 WorldState.to_dict() 或 None
        """
        store = SnapshotManager._make_store()
        manager = SnapshotManager(store)
        state = manager.rollback(session_id, target_version)
        if state is None:
            return None
        return state.to_dict()

    @staticmethod
    def save(session_id: str, context: dict, description: str = "manual") -> bool:
        """保存当前上下文作为快照。

        Args:
            session_id: 用户/会话 ID
            context: 画布上下文数据（pens, lines 等）
            description: 快照描述标签

        Returns:
            bool: 是否保存成功
        """
        store = SnapshotManager._make_store()

        # 尝试加载现有状态以保留版本历史；不存在则创建
        existing = store.load(session_id)
        if existing is not None:
            state = existing
            state.canvas = context
        else:
            state = WorldState(
                user_id=session_id,
                canvas=context,
            )

        # 将快照元信息存入 extra
        state.extra["_snapshot"] = {
            "created_at": str(time.time()),
            "description": description,
        }

        # 先通过 save 方法 bump version 并写入 current
        store.save(state)
        # 再保存为持久化快照
        store.save_snapshot(state)
        return True
