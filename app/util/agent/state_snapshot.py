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
