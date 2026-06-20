# -*- coding: UTF-8 -*-
"""Agent Supervisor — multi-agent task decomposition, orchestration, and synthesis."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Generator

from app.config import AGENT_DEFAULT_MODEL

SUPERVISOR_PROMPT = """你是多Agent调度专家。将复杂任务拆解为子任务并分配给专业子Agent。

## 可用子Agent
{agent_list}

## 输出格式 (严格 JSON)
{{
  "goal": "一句话目标",
  "subtasks": [
    {{
      "id": "t1",
      "agent": "agent_name",
      "task": "给子Agent的详细指令",
      "depends_on": [],
      "parallel_group": null
    }}
  ]
}}

## 规则
- 2~5 个子任务，每个分配给最合适的 Agent
- depends_on: 前置子任务 id 列表，空数组=可立即执行
- 无依赖的子任务自动并行执行
- 每个子任务的任务描述必须具体、可执行
- 考虑子Agent之间的依赖关系：先收集信息、再加工、最后组合
"""

SYNTHESIS_PROMPT = """你是结果汇总专家。根据子任务执行结果，生成最终的用户回复。

## 原始用户需求
{goal}

## 子任务执行结果
{subtask_results}

## 规则
- 用中文回复，简洁专业
- 综合所有已完成子任务的结果
- 清晰标注哪些部分成功、哪些失败
- 失败部分说明原因并提供替代建议
- 不要重复原始指令
"""


@dataclass
class Subtask:
    id: str
    agent: str
    task: str
    depends_on: list = field(default_factory=list)
    parallel_group: str | None = None


@dataclass
class SupervisorPlan:
    goal: str = ""
    subtasks: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SupervisorPlan | None":
        subtasks_raw = data.get("subtasks", [])
        if not subtasks_raw:
            return None
        subtasks = []
        for s in subtasks_raw:
            subtasks.append(Subtask(
                id=s.get("id", ""),
                agent=s.get("agent", ""),
                task=s.get("task", ""),
                depends_on=s.get("depends_on", []),
                parallel_group=s.get("parallel_group"),
            ))
        return cls(goal=data.get("goal", ""), subtasks=subtasks)


@dataclass
class SubtaskResult:
    subtask_id: str
    agent: str
    success: bool
    output: str = ""
    duration_ms: float = 0.0


class Supervisor:
    """Multi-agent orchestration layer.

    Decomposes complex tasks, dispatches to sub-agents via AgentDispatcher,
    and synthesizes results into a coherent response.

    Usage::

        supervisor = Supervisor()
        plan = supervisor.decompose(llm_client, task, agent_names)
        for event in supervisor.execute(plan, dispatcher, llm_client, ctx):
            ...
        final = supervisor.synthesize(llm_client, plan.goal, results)
    """

    def __init__(self, model: str = AGENT_DEFAULT_MODEL):
        self.model = model
        self._results: dict[str, SubtaskResult] = {}

    # ── Task Decomposition ─────────────────────────────────────────────

    def decompose(self, llm_client, task: str, agent_list: str,
                  model: str = None) -> SupervisorPlan | None:
        """Use LLM to decompose a complex task into sub-agent subtasks.

        Args:
            llm_client: LLM client.
            task: User's complex task description.
            agent_list: Description of available sub-agents (name + description).
            model: Optional model override.

        Returns:
            SupervisorPlan or None if decomposition fails.
        """
        from app.util.agent.helpers import extract_json, repair_json

        system = SUPERVISOR_PROMPT.format(agent_list=agent_list)

        try:
            resp = llm_client.chat.completions.create(
                model=model or self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": task},
                ],
                temperature=0.1, max_tokens=1024, timeout=30,
            )
            raw = resp.choices[0].message.content or ""
        except Exception:
            logging.warning("Supervisor: decomposition LLM call failed")
            return None

        text = extract_json(raw)
        if not text:
            return None

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            repaired = repair_json(text)
            if repaired != text:
                try:
                    data = json.loads(repaired)
                except (json.JSONDecodeError, ValueError):
                    return None
            else:
                return None

        plan = SupervisorPlan.from_dict(data)
        if plan and 1 <= len(plan.subtasks) <= 8:
            return plan
        return None

    # ── Plan Execution ─────────────────────────────────────────────────

    def execute(self, plan: SupervisorPlan, dispatcher, llm_client,
                tool_context: dict, event_queue=None,
                model: str = None) -> Generator:
        """Execute a SupervisorPlan by dispatching subtasks to sub-agents.

        Handles topological ordering — subtasks with satisfied dependencies
        run in parallel batches. Results are collected and stored in self._results.

        Yields:
            ("subtask_start", subtask_id, agent_name)
            ("subtask_result", SubtaskResult)
            ("subtask_error", subtask_id, error_message)
        """
        self._results.clear()
        completed: set = set()
        failed: set = set()
        pending = {s.id for s in plan.subtasks}
        subtask_map = {s.id: s for s in plan.subtasks}

        total_start = time.time()
        max_duration = 180  # 3 min total

        while pending:
            if time.time() - total_start > max_duration:
                for sid in list(pending):
                    yield ("subtask_error", sid, "Supervisor execution timeout")
                    failed.add(sid)
                break

            # Find ready subtasks (all deps satisfied)
            ready = []
            for sid in list(pending):
                st = subtask_map[sid]
                if all(d in completed for d in st.depends_on):
                    if any(d in failed for d in st.depends_on):
                        pending.discard(sid)
                        failed.add(sid)
                        yield ("subtask_error", sid, "前置任务失败，跳过执行")
                    else:
                        ready.append(st)

            if not ready:
                if not pending:
                    break
                # Deadlock — fail remaining
                for sid in list(pending):
                    failed.add(sid)
                    yield ("subtask_error", sid, "依赖循环或死锁")
                break

            # Execute ready subtasks in parallel batch
            batch_results = {}
            for st in ready:
                pending.discard(st.id)
                yield ("subtask_start", st.id, st.agent)
                t0 = time.time()

                try:
                    result = dispatcher.dispatch(
                        llm_client, st.agent, st.task,
                        tool_context, model=model or self.model,
                        event_queue=event_queue,
                    )
                    duration = (time.time() - t0) * 1000
                    sr = SubtaskResult(
                        subtask_id=st.id, agent=st.agent,
                        success=result.get("success", False),
                        output=result.get("result", ""),
                        duration_ms=duration,
                    )
                    self._results[st.id] = sr
                    if sr.success:
                        completed.add(st.id)
                    else:
                        failed.add(st.id)
                    batch_results[st.id] = sr
                    yield ("subtask_result", sr)
                except Exception as ex:
                    duration = (time.time() - t0) * 1000
                    sr = SubtaskResult(
                        subtask_id=st.id, agent=st.agent,
                        success=False, output=str(ex),
                        duration_ms=duration,
                    )
                    self._results[st.id] = sr
                    failed.add(st.id)
                    yield ("subtask_error", st.id, str(ex))

    # ── Result Synthesis ───────────────────────────────────────────────

    def synthesize(self, llm_client, plan_goal: str,
                   results: dict[str, SubtaskResult] = None,
                   model: str = None) -> str:
        """Synthesize sub-agent results into a coherent final response.

        Args:
            llm_client: LLM client.
            plan_goal: Original task goal.
            results: Dict of subtask_id → SubtaskResult (uses self._results if None).
            model: Optional model override.

        Returns:
            Synthesized response text.
        """
        rmap = results or self._results
        if not rmap:
            return ""

        # Build subtask result descriptions
        lines = []
        for sid, sr in rmap.items():
            status = "成功" if sr.success else "失败"
            output = sr.output[:500] if sr.output else "(无输出)"
            lines.append(f"[{status}] {sr.agent}: {output}")
        subtask_text = "\n".join(lines)

        try:
            resp = llm_client.chat.completions.create(
                model=model or self.model,
                messages=[
                    {"role": "system", "content": SYNTHESIS_PROMPT.format(
                        goal=plan_goal, subtask_results=subtask_text)},
                ],
                temperature=0.3, max_tokens=800, timeout=30,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            logging.warning("Supervisor: synthesis LLM call failed")
            return self._fallback_synthesize(plan_goal, rmap)

    def _fallback_synthesize(self, goal: str,
                             results: dict[str, SubtaskResult]) -> str:
        """Fallback synthesis without LLM."""
        parts = [f"任务: {goal}\n"]
        for sid, sr in results.items():
            mark = "✓" if sr.success else "✗"
            parts.append(f"{mark} {sr.agent}: {sr.output[:300]}")
        return "\n".join(parts)

    @property
    def results(self) -> dict[str, SubtaskResult]:
        return dict(self._results)

    def clear(self):
        self._results.clear()
