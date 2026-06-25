# -*- coding: UTF-8 -*-
"""WorldState — 统一 Agent 世界状态数据模型

所有 Agent 模块共享的单一状态源（Single Source of Truth）。
JSON 可序列化，Redis 可持久化，支持乐观锁版本控制。
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    """Agent 世界状态 — 描述当前任务上下文、领域状态、执行元信息的统一模型。

    所有 Agent 组件（Planner、Executor、Memory、Reflexion）读写同一份 WorldState，
    避免状态在不同模块间漂移。

    Usage::

        ws = WorldState(user_id="user_1", goal="画一个流程图")
        ws.canvas["pen_count"] = 5
        d = ws.to_dict()
        ws2 = WorldState.from_dict(d)
    """

    # ── 标识 ──
    user_id: str
    session_id: str = ""

    # ── 画布领域状态 ──
    canvas: dict = field(default_factory=dict)  # {pen_id: pen_props, ...}
    pen_count: int = 0
    selected_pen_ids: list = field(default_factory=list)

    # ── 蓝图领域状态 ──
    blueprints: dict = field(default_factory=dict)  # {blueprint_id: {...}}
    current_blueprint_id: str = ""

    # ── 文件领域状态 ──
    recent_files: list = field(default_factory=list)  # [{name, url, type}, ...]

    # ── 任务执行元信息 ──
    goal: str = ""
    tasks: list = field(default_factory=list)  # 全部任务 [{id, desc, status}]
    completed: list = field(default_factory=list)  # 已完成任务 ID
    pending: list = field(default_factory=list)  # 待执行任务 ID
    artifacts: dict = field(default_factory=dict)  # 中间产物 {task_id: artifact}
    risks: list = field(default_factory=list)  # 风险 [{desc, severity}]

    # ── 规划反馈 ──
    last_plan_goal: str = ""
    last_plan_domains: list = field(default_factory=list)
    working_goal: str = ""
    pending_confirmations: list = field(default_factory=list)

    # ── 质量 / 置信度 ──
    confidence: float = 1.0  # 0.0 ~ 1.0，当前计划置信度
    recent_errors: list = field(default_factory=list)  # [{message, tool, ts}, ...]

    # ── 版本控制 ──
    updated_at: float = field(default_factory=time.time)
    version: int = 1  # 单调递增版本号，用于乐观锁冲突检测

    # ── 扩展 ──
    extra: dict = field(default_factory=dict)  # 未来领域扩展

    # ── 序列化 ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """序列化为 JSON 兼容 dict。"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "canvas": self.canvas,
            "pen_count": self.pen_count,
            "selected_pen_ids": self.selected_pen_ids,
            "blueprints": self.blueprints,
            "current_blueprint_id": self.current_blueprint_id,
            "recent_files": self.recent_files,
            "goal": self.goal,
            "tasks": self.tasks,
            "completed": self.completed,
            "pending": self.pending,
            "artifacts": self.artifacts,
            "risks": self.risks,
            "last_plan_goal": self.last_plan_goal,
            "last_plan_domains": self.last_plan_domains,
            "working_goal": self.working_goal,
            "pending_confirmations": self.pending_confirmations,
            "confidence": self.confidence,
            "recent_errors": self.recent_errors,
            "updated_at": self.updated_at,
            "version": self.version,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        """从 dict 反序列化。"""
        return cls(
            user_id=d.get("user_id", ""),
            session_id=d.get("session_id", ""),
            canvas=d.get("canvas", {}),
            pen_count=d.get("pen_count", 0),
            selected_pen_ids=d.get("selected_pen_ids", []),
            blueprints=d.get("blueprints", {}),
            current_blueprint_id=d.get("current_blueprint_id", ""),
            recent_files=d.get("recent_files", []),
            goal=d.get("goal", ""),
            tasks=d.get("tasks", []),
            completed=d.get("completed", []),
            pending=d.get("pending", []),
            artifacts=d.get("artifacts", {}),
            risks=d.get("risks", []),
            last_plan_goal=d.get("last_plan_goal", ""),
            last_plan_domains=d.get("last_plan_domains", []),
            working_goal=d.get("working_goal", ""),
            pending_confirmations=d.get("pending_confirmations", []),
            confidence=d.get("confidence", 1.0),
            recent_errors=d.get("recent_errors", []),
            updated_at=d.get("updated_at", time.time()),
            version=d.get("version", 1),
            extra=d.get("extra", {}),
        )

    # ── 工具方法 ────────────────────────────────────────────────────────

    def bump_version(self) -> int:
        """递增版本号，返回新版本。"""
        self.version += 1
        self.updated_at = time.time()
        return self.version

    def add_error(self, message: str, tool: str = "") -> None:
        """记录最近错误（最多保留 10 条）。"""
        self.recent_errors.append({"message": message, "tool": tool, "ts": time.time()})
        if len(self.recent_errors) > 10:
            self.recent_errors = self.recent_errors[-10:]

    def mark_task_completed(self, task_id: str) -> None:
        """标记任务完成 — 从 pending 移到 completed。"""
        if task_id in self.pending:
            self.pending.remove(task_id)
        if task_id not in self.completed:
            self.completed.append(task_id)

    def mark_task_failed(self, task_id: str) -> None:
        """标记任务失败。"""
        if task_id in self.pending:
            self.pending.remove(task_id)

    def add_artifact(self, task_id: str, artifact: Any) -> None:
        """记录中间产物。"""
        self.artifacts[task_id] = artifact

    def add_risk(self, desc: str, severity: str = "medium") -> None:
        """添加风险标记。"""
        self.risks.append({"desc": desc, "severity": severity, "ts": time.time()})

    def update_confidence(self, delta: float) -> None:
        """更新置信度（delta 可为负）。"""
        self.confidence = max(0.0, min(1.0, self.confidence + delta))

    def get_task_summary(self) -> str:
        """生成任务进度摘要文本。"""
        total = len(self.tasks)
        done = len(self.completed)
        return f"任务进度: {done}/{total} 完成, {len(self.pending)} 待处理, 置信度 {self.confidence:.0%}"

    def __repr__(self) -> str:
        return (
            f"WorldState(user={self.user_id}, v{self.version}, "
            f"goal='{self.goal[:30]}', confidence={self.confidence:.0%})"
        )
