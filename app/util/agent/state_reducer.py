# -*- coding: UTF-8 -*-
"""StateReducer — 状态变更合并与冲突解决

DAG 并行节点可能同时修改 WorldState。
StateReducer 提供确定性的状态合并逻辑，基于乐观锁版本号检测冲突。
"""

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.util.agent.state import WorldState


@dataclass
class StateMutation:
    """单次状态变更 — 合并的基本单元。

    描述对 WorldState 中某个路径的一次修改操作。
    """

    user_id: str
    domain: str  # 领域: "canvas", "blueprint", "file", "meta", "extra"
    action: str  # 操作: "set", "merge", "delete_key", "append", "increment"
    path: str  # 点分隔路径, 如 "canvas.pen_count" 或 "recent_files"
    value: Any  # 新值 / 增量 / 合并 dict
    source: str = "tool"  # 来源: "tool", "user", "critic", "sub_agent", "reflexion"
    timestamp: float = field(default_factory=time.time)
    version: int = 0  # 期望的基础版本号（乐观锁）

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "domain": self.domain,
            "action": self.action,
            "path": self.path,
            "value": self.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "version": self.version,
        }


class StateReducer:
    """确定性的状态合并引擎。

    支持的操作类型：
        - set: 直接赋值
        - merge: 浅合并 dict（递归）
        - delete_key: 删除 key
        - append: 追加到 list
        - increment: 数值递增
    """

    @staticmethod
    def apply(base: WorldState, mutation: StateMutation) -> WorldState:
        """应用单个 mutation 到 WorldState 副本，返回新状态。"""
        state = copy.deepcopy(base)

        try:
            StateReducer._apply_inplace(state, mutation)
            state.bump_version()
        except Exception:
            logging.debug(
                "StateReducer apply failed: domain=%s action=%s path=%s",
                mutation.domain,
                mutation.action,
                mutation.path,
            )
        return state

    @staticmethod
    def _apply_inplace(state: WorldState, mutation: StateMutation) -> None:
        """原地应用 mutation。"""
        action = mutation.action
        path = mutation.path
        value = mutation.value

        # 解析顶层字段
        if "." not in path:
            # 直接访问 WorldState 顶层属性
            if hasattr(state, path):
                current = getattr(state, path)
                if action == "set":
                    setattr(state, path, value)
                elif action == "merge" and isinstance(current, dict) and isinstance(value, dict):
                    current.update(value)
                elif action == "delete_key":
                    setattr(state, path, type(current)())
                elif action == "append" and isinstance(current, list):
                    current.append(value)
                elif action == "increment" and isinstance(current, (int, float)):
                    setattr(state, path, current + value)
            return

        # 嵌套路径: "canvas.pen_count", "extra.sub.key"
        parts = path.split(".")
        root_field = parts[0]
        sub_path = parts[1:]

        if not hasattr(state, root_field):
            return

        container = getattr(state, root_field)

        if isinstance(container, dict):
            StateReducer._apply_to_dict(container, sub_path, action, value)
        elif isinstance(container, list):
            StateReducer._apply_to_list(container, sub_path, action, value)

    @staticmethod
    def _apply_to_dict(container: dict, path_parts: list, action: str, value: Any) -> None:
        """在嵌套 dict 中应用操作。"""
        if len(path_parts) == 1:
            key = path_parts[0]
            if action == "set":
                container[key] = value
            elif action == "merge" and key in container and isinstance(container[key], dict):
                container[key].update(value)
            elif action == "delete_key":
                container.pop(key, None)
            elif action == "append" and key in container and isinstance(container[key], list):
                container[key].append(value)
            elif action == "increment" and key in container and isinstance(container[key], (int, float)):
                container[key] += value
        else:
            # 递归进入嵌套 dict
            key = path_parts[0]
            if key in container and isinstance(container[key], dict):
                StateReducer._apply_to_dict(container[key], path_parts[1:], action, value)

    @staticmethod
    def _apply_to_list(container: list, path_parts: list, action: str, value: Any) -> None:
        """在 list 中应用操作（仅支持 append）。"""
        if action == "append":
            container.append(value)

    @staticmethod
    def merge(base: WorldState, mutations: list) -> WorldState:
        """按顺序合并多个 mutation，返回新状态。

        多个 mutation 按时间戳排序后依次应用。
        """
        state = copy.deepcopy(base)
        sorted_mutations = sorted(mutations, key=lambda m: m.timestamp)
        for m in sorted_mutations:
            try:
                StateReducer._apply_inplace(state, m)
            except Exception:
                logging.debug("StateReducer merge skip: %s.%s", m.domain, m.path)
        state.bump_version()
        return state

    @staticmethod
    def detect_conflict(m1: StateMutation, m2: StateMutation) -> bool:
        """检测两个 mutation 是否存在冲突（修改同一路径）。"""
        return m1.path == m2.path and m1.user_id == m2.user_id

    @staticmethod
    def resolve_conflict(
        m1: StateMutation,
        m2: StateMutation,
        resolution_policy: str = "last_write_wins",
    ) -> StateMutation:
        """解决两个冲突 mutation。

        策略:
            - last_write_wins: 保留时间戳较新的
            - first_write_wins: 保留时间戳较旧的
            - merge: 对于 dict merge 类型，合并 values
        """
        if not StateReducer.detect_conflict(m1, m2):
            return m1  # 无冲突

        if resolution_policy == "last_write_wins":
            return m1 if m1.timestamp >= m2.timestamp else m2
        elif resolution_policy == "first_write_wins":
            return m1 if m1.timestamp <= m2.timestamp else m2
        elif resolution_policy == "merge" and m1.action == "merge" and m2.action == "merge":
            merged = StateMutation(
                user_id=m1.user_id,
                domain=m1.domain,
                action="merge",
                path=m1.path,
                value={**m1.value, **m2.value},
                source="reducer",
                timestamp=max(m1.timestamp, m2.timestamp),
            )
            return merged

        return m1 if m1.timestamp >= m2.timestamp else m2
