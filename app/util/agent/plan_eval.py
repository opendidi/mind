# -*- coding: UTF-8 -*-
"""Plan-Feedback 闭环 — 执行后即时评分 + PlanMemory 持久化 + Planner 注入。

三级反馈回路:
  Level 1 (即时): DAG 执行完成后，计算 PlanFeedback，注入到下一个 planner 调用的提示词中
  Level 2 (会话): 通过 Redis 存储在最近 N 个 plan 的反馈
  Level 3 (持久): 内存存储 plan_pattern → stats
"""

import json
import logging
import time
from dataclasses import dataclass, field


@dataclass
class PlanFeedback:
    """Post-execution plan quality feedback."""

    goal: str = ""
    domains: list = field(default_factory=list)
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    reflections_triggered: int = 0
    total_duration_ms: float = 0.0
    issues: list = field(default_factory=list)
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_planner_hint(self) -> str:
        if self.score >= 0.9 and not self.steps_failed:
            return ""
        lines = []
        if self.steps_failed > 0:
            lines.append(f"[!] 最近一次类似任务中，{self.steps_failed}/{self.steps_total} 个步骤失败。")
        if self.reflections_triggered > 0:
            lines.append(
                f"[!] 该任务触发了 {self.reflections_triggered} 次自省重试，说明初始计划可能需要更精确的工具选择或步骤拆分。"
            )
        for issue in self.issues:
            lines.append(f"[FIX] {issue}")
        if self.score < 0.5:
            lines.append("[!!] 该计划执行质量较差（评分<0.5），请重新思考步骤设计和依赖关系。")
        if lines:
            lines.insert(0, "## 历史教训（请参考以下反馈改进本次计划）")
            lines.append(
                "建议：优先使用更精确的 tool_hint，避免依赖需要多次重试的操作，确保 depends_on 正确反映步骤间的数据依赖。"
            )
        return "\n".join(lines) if len(lines) > 1 else ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "domains": self.domains,
            "steps_total": self.steps_total,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed": self.steps_failed,
            "reflections_triggered": self.reflections_triggered,
            "total_duration_ms": self.total_duration_ms,
            "issues": self.issues,
            "score": self.score,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlanFeedback":
        return cls(
            goal=d.get("goal", ""),
            domains=d.get("domains", []),
            steps_total=d.get("steps_total", 0),
            steps_succeeded=d.get("steps_succeeded", 0),
            steps_failed=d.get("steps_failed", 0),
            reflections_triggered=d.get("reflections_triggered", 0),
            total_duration_ms=d.get("total_duration_ms", 0.0),
            issues=d.get("issues", []),
            score=d.get("score", 0.0),
            timestamp=d.get("timestamp", time.time()),
        )


def _detect_issues(
    goal: str, completed: list[str], failed: list[str], reflections: int, duration_ms: float
) -> list[str]:
    issues: list[str] = []
    if failed and completed:
        issues.append("部分步骤失败但前序步骤成功 — 检查步骤间是否存在隐式数据依赖")
    if reflections >= 3:
        issues.append(f"触发 {reflections} 次自省重试 — 初始工具选择或参数可能需要调整")
    if len(completed) + len(failed) >= 5 and len(failed) >= 2:
        issues.append("步骤较多且失败率高 — 建议将目标拆分为更小的独立子任务")
    if duration_ms > 120_000:
        issues.append(f"执行耗时 {duration_ms/1000:.0f}s — 考虑减少步骤或合并冗余查询")
    if any(not desc.strip() for desc in completed + failed):
        issues.append("部分步骤描述为空 — 规划时需要为每一步提供明确的 desc")
    return issues


def evaluate_plan(
    goal: str, domains: list[str], completed: list[str], failed: list[str], reflections: int, duration_ms: float
) -> PlanFeedback:
    total = len(completed) + len(failed)
    if total == 0:
        return PlanFeedback(goal=goal, domains=domains, score=1.0)
    succeeded = len(completed)
    step_score = succeeded / total if total > 0 else 1.0
    score = step_score * 0.6
    retry_score = max(0.0, 1.0 - reflections * 0.15)
    score += retry_score * 0.25
    speed_score = max(0.0, 1.0 - duration_ms / 180_000.0)
    score += speed_score * 0.15
    score = round(min(1.0, max(0.0, score)), 3)
    issues = _detect_issues(goal, completed, failed, reflections, duration_ms)
    return PlanFeedback(
        goal=goal,
        domains=domains,
        steps_total=total,
        steps_succeeded=succeeded,
        steps_failed=len(failed),
        reflections_triggered=reflections,
        total_duration_ms=duration_ms,
        issues=issues,
        score=score,
    )


# ── Plan Memory ────────────────────────────────────────────────────────────

_PLAN_MEMORY_REDIS_DB = 5
_PLAN_MEMORY_TTL = 3600
_PLAN_MEMORY_MAX_RECENT = 20

# In-memory fallback storage
_mem_feedbacks: dict[str, PlanFeedback] = {}
_mem_recent: list[PlanFeedback] = []


def _get_plan_memory_redis():
    try:
        from app.util.redis_utils import get_redis

        return get_redis(db=_PLAN_MEMORY_REDIS_DB)
    except Exception:
        return None


def _plan_pattern_key(domains: list[str]) -> str:
    domain_key = ":".join(sorted(domains)) if domains else "general"
    return f"plan:feedback:{domain_key}"


def _plan_recent_key() -> str:
    return "plan:feedback:recent"


class PlanMemory:
    """Cross-session plan quality memory. Uses Redis with in-memory fallback."""

    @staticmethod
    def record(feedback: PlanFeedback):
        r = _get_plan_memory_redis()
        if r:
            try:
                data = json.dumps(feedback.to_dict(), ensure_ascii=False)
                domain_key = _plan_pattern_key(feedback.domains)
                r.setex(domain_key, _PLAN_MEMORY_TTL, data)
                recent_key = _plan_recent_key()
                r.lpush(recent_key, data)
                r.ltrim(recent_key, 0, _PLAN_MEMORY_MAX_RECENT - 1)
                r.expire(recent_key, _PLAN_MEMORY_TTL * 4)
                logging.debug("PlanMemory recorded: score=%.2f, domains=%s", feedback.score, feedback.domains)
            except Exception:
                logging.warning("PlanMemory Redis record failed", exc_info=True)
        # In-memory fallback
        domain_key = _plan_pattern_key(feedback.domains)
        _mem_feedbacks[domain_key] = feedback
        _mem_recent.insert(0, feedback)
        if len(_mem_recent) > _PLAN_MEMORY_MAX_RECENT:
            _mem_recent.pop()

    @staticmethod
    def get_hints_for_domains(domains: list[str]) -> str:
        hints_parts: list[str] = []
        r = _get_plan_memory_redis()
        if r:
            try:
                if domains:
                    domain_key = _plan_pattern_key(domains)
                    raw = r.get(domain_key)
                    if raw:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        hint = fb.to_planner_hint()
                        if hint:
                            hints_parts.append(hint)
                recent_key = _plan_recent_key()
                recent_raws = r.lrange(recent_key, 0, 2) or []
                seen_goals = {domains and _plan_pattern_key(domains)}
                for raw in recent_raws:
                    try:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        fb_key = _plan_pattern_key(fb.domains)
                        if fb_key in seen_goals:
                            continue
                        seen_goals.add(fb_key)
                        hint = fb.to_planner_hint()
                        if hint:
                            hints_parts.append(hint)
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception:
                logging.warning("PlanMemory Redis get failed", exc_info=True)
        # In-memory fallback
        if not hints_parts:
            domain_key = _plan_pattern_key(domains)
            if domain_key in _mem_feedbacks:
                hint = _mem_feedbacks[domain_key].to_planner_hint()
                if hint:
                    hints_parts.append(hint)
            for fb in _mem_recent[:3]:
                fb_key = _plan_pattern_key(fb.domains)
                if fb_key != domain_key:
                    hint = fb.to_planner_hint()
                    if hint:
                        hints_parts.append(hint)
        return "\n\n".join(hints_parts) if hints_parts else ""

    @staticmethod
    def get_failure_summary(limit: int = 3) -> str:
        """Return recent failure patterns as planner hints.

        Reads from Redis recent plan list (in-memory fallback).
        Returns empty string when no failures are recorded.
        """
        failures: list[str] = []
        r = _get_plan_memory_redis()
        if r:
            try:
                recent_key = _plan_recent_key()
                recent_raws = r.lrange(recent_key, 0, _PLAN_MEMORY_MAX_RECENT - 1) or []
                for raw in recent_raws:
                    try:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        if fb.steps_failed > 0:
                            failures.append(
                                f"目标「{fb.goal[:60]}」: {fb.steps_failed}/{fb.steps_total} 步骤失败，"
                                f"评分 {fb.score:.2f}"
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception:
                logging.warning("PlanMemory Redis failure_summary failed", exc_info=True)

        # In-memory fallback
        if not failures:
            for fb in _mem_recent:
                if fb.steps_failed > 0:
                    failures.append(
                        f"目标「{fb.goal[:60]}」: {fb.steps_failed}/{fb.steps_total} 步骤失败，" f"评分 {fb.score:.2f}"
                    )

        if not failures:
            return ""

        lines = ["## 历史失败记录（请避免重复以下模式）"]
        for f in failures[:limit]:
            lines.append(f"- {f}")
        if len(failures) > limit:
            lines.append(f"- …还有 {len(failures) - limit} 条失败记录")
        return "\n".join(lines)
