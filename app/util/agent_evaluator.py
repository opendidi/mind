# -*- coding: UTF-8 -*-
"""AgentEvaluator — compute quality metrics from traces."""

from dataclasses import dataclass


@dataclass
class EvalMetric:
    conversation_id: str = ""
    tool_success_rate: float = 0.0
    avg_tool_duration_ms: float = 0.0
    reflection_count: int = 0
    plan_steps_total: int = 0
    plan_steps_completed: int = 0
    llm_calls_total: int = 0
    total_duration_ms: float = 0.0
    user_feedback: str | None = None
    user_rating: int | None = None
    is_retry: bool = False


class AgentEvaluator:
    @staticmethod
    def from_trace(trace: dict, feedback: dict = None) -> EvalMetric:
        spans = trace.get("spans", [])
        tool_spans = [s for s in spans if s["name"].startswith("tool:")]
        reflect_spans = [s for s in spans if s["name"] == "reflect"]
        total_tools = len(tool_spans)
        successful_tools = len([s for s in tool_spans if s["status"] == "ok"])
        durations = [s.get("duration_ms", 0) or 0 for s in tool_spans]
        plan_steps_total = len([s for s in spans if s["name"].startswith("step:")])
        plan_steps_completed = len([s for s in spans if s["name"].startswith("step:") and s["status"] == "ok"])
        metric = EvalMetric(
            conversation_id=trace.get("trace_id", ""),
            tool_success_rate=(successful_tools / total_tools if total_tools > 0 else 1.0),
            avg_tool_duration_ms=sum(durations) / len(durations) if durations else 0.0,
            reflection_count=len(reflect_spans),
            plan_steps_total=plan_steps_total,
            plan_steps_completed=plan_steps_completed,
            llm_calls_total=len([s for s in spans if s["name"] in ("llm_api_call", "plan", "reflect")]),
            total_duration_ms=trace.get("total_duration_ms") or 0.0,
        )
        if feedback:
            metric.user_feedback = feedback.get("feedback")
            metric.user_rating = feedback.get("rating")
        return metric
