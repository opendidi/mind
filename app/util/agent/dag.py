# -*- coding: UTF-8 -*-
"""DAG Executor — topological sort, parallel execution with ReAct loop.
Adapted from pypano for mind project."""

import atexit as _atexit
import json
import logging
import queue
import time
from collections import defaultdict
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Generator

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.executor import BaseExecutor
from app.util.agent.helpers import loop_key as _loop_key
from app.util.agent.pheromone import SharedContext
from app.util.executor import ExecutorTimeout, ManagedPool

_dag_pool = ManagedPool(max_workers=8, prefix="dag-")


@_atexit.register
def _shutdown_dag_pool():
    """Clean up DAG thread pool on application exit."""
    pool = _dag_pool._pool
    if pool and not getattr(pool, "_shutdown", 0):
        pool.shutdown(wait=False)


# ── Data Structures ────────────────────────────────────────────────────────


@dataclass
class DAGNode:
    id: str
    desc: str
    tool_hint: str | None = None
    agent_name: str | None = None
    confirm: bool = False
    depends_on: list = field(default_factory=list)
    parallel_group: str | None = None


@dataclass
class StateDAGNode(DAGNode):
    """Phase 2: State-aware DAGNode — 支持前置条件、后置条件、条件分支。

    向后兼容 DAGNode，所有新字段默认为空/无操作。
    """

    preconditions: dict = field(default_factory=dict)  # {state_path: expected_value}
    postconditions: dict = field(default_factory=dict)  # {state_path: expected_value_after}
    conditional_edges: dict = field(default_factory=dict)  # {state_path: {value: next_node_id}}
    retry_on_state_mismatch: bool = False

    def check_preconditions(self, world_state_dict: dict) -> bool:
        """验证前置条件是否满足。"""
        if not self.preconditions:
            return True
        for path, expected in self.preconditions.items():
            actual = world_state_dict.get(path)
            if actual != expected:
                return False
        return True

    def get_conditional_target(self, world_state_dict: dict) -> str | None:
        """根据条件边决定下一个节点。"""
        if not self.conditional_edges:
            return None
        for path, mapping in self.conditional_edges.items():
            actual = world_state_dict.get(path)
            if actual in mapping:
                return mapping[actual]
        return None


@dataclass
class DAGPlan:
    mode: str = "simple"
    goal: str = ""
    nodes: list = field(default_factory=list)
    risk: str = "low"


@dataclass
class StepResult:
    step_id: str
    success: bool
    output: dict = field(default_factory=dict)
    reflection: dict | None = None
    duration_ms: float = 0.0
    retries: int = 0


@dataclass
class ExecutionState:
    plan: DAGPlan
    node_map: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    pending: set = field(default_factory=set)
    running: set = field(default_factory=set)
    completed: set = field(default_factory=set)
    failed: set = field(default_factory=set)
    cancelled: bool = False

    @classmethod
    def from_plan(cls, plan: DAGPlan) -> "ExecutionState":
        node_map = {n.id: n for n in plan.nodes}
        return cls(plan=plan, node_map=node_map, pending={n.id for n in plan.nodes})


def _has_cycle(nodes) -> bool:
    """DFS-based cycle detection for DAG dependency graph."""
    graph = {n.id: set(n.depends_on) for n in nodes}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in graph}

    def dfs(nid):
        color[nid] = GRAY
        for dep in graph.get(nid, set()):
            if color.get(dep) == GRAY:
                return True
            if color.get(dep) == WHITE and dfs(dep):
                return True
        color[nid] = BLACK
        return False

    for nid in graph:
        if color[nid] == WHITE and dfs(nid):
            return True
    return False


# ── Constants ──────────────────────────────────────────────────────────────

from app.util.agent.constants import MAX_DAG_TOTAL_SECONDS, MAX_LOOP_REPEAT, MAX_NODE_SECONDS, MAX_REFLECT_RETRIES

# ── MODELS ──────────────────────────────────────────────────────────────────


class DAGExecutor(BaseExecutor):
    """Executes a DAGPlan using topological sort + parallel ThreadPoolExecutor."""

    def __init__(
        self,
        llm_client,
        tools_schemas: list,
        messages: list,
        hooks: list = None,
        tool_context: dict = None,
        user_id: str = "",
        model: str = AGENT_DEFAULT_MODEL,
        confirm_handler=None,
        dispatcher=None,
        tracer=None,
        stream: bool = False,
        redis_client=None,
        task_id: str = "",
    ):
        super().__init__(
            llm_client,
            tools_schemas,
            messages,
            tool_context=tool_context,
            user_id=user_id,
            model=model,
            confirm_handler=confirm_handler,
            dispatcher=dispatcher,
            tracer=tracer,
            stream=stream,
            redis_client=redis_client,
            task_id=task_id,
            session_id=(task_id or user_id),
        )
        self.hooks = hooks or []
        self.shared_context = SharedContext(
            redis_client=redis_client, task_id=task_id
        )
        self._replan_used = False
        self._reflection_count = 0
        self._dag_start_ts = 0.0
        self._critic_hints = ""  # 质量要求，由 CriticAgent 注入
        self._world_state = None  # WorldState 引用，由 engine 注入
        from app.util.agent.reflexion import AgentReflexion

        self.reflexion = AgentReflexion(llm_client, model)

    @property
    def tool_call_count(self):
        return self._tool_call_count

    def _get_state(self):
        """返回最近的 ExecutionState（供 CriticAgent 审查使用）。"""
        return getattr(self, '_last_execution_state', None)

    def execute(self, plan: DAGPlan) -> Generator:
        if plan.mode == "simple" or not plan.nodes:
            yield from self._execute_simple()
            return

        state = ExecutionState.from_plan(plan)
        self._last_execution_state = state  # 保存引用供 CriticAgent 使用
        self._replan_used = False

        yield (
            "plan",
            {
                "goal": plan.goal,
                "nodes": [
                    {
                        "id": n.id,
                        "desc": n.desc,
                        "depends_on": n.depends_on,
                        "parallel_group": n.parallel_group,
                        "confirm": n.confirm,
                    }
                    for n in plan.nodes
                ],
                "risk": plan.risk,
                "mode": "dag",
            },
        )

        # Phase 1: Confirmation check
        destructive = [n for n in plan.nodes if n.confirm]
        if destructive and self.confirm_handler:
            approved = self.confirm_handler(
                "destructive_ops",
                {
                    "steps": [{"id": n.id, "desc": n.desc} for n in destructive],
                    "goal": plan.goal,
                },
            )
            if not approved:
                yield ("error", "用户取消了操作")
                yield ("done", {"status": "cancelled", "reason": "用户取消"})
                return

        self._dag_start_ts = time.time()

        # Phase 2: Execute nodes via topological sort
        dag_start = self._dag_start_ts
        while state.pending or state.running:
            if time.time() - dag_start > MAX_DAG_TOTAL_SECONDS:
                logging.error("DAG 执行超时 (%ds)，force aborting", MAX_DAG_TOTAL_SECONDS)
                for node_id in list(state.running) + list(state.pending):
                    state.failed.add(node_id)
                yield ("error", f"DAG 执行超时（{MAX_DAG_TOTAL_SECONDS}秒），已中止")
                yield ("done", {"status": "timeout", "completed": list(state.completed)})
                return
            ready = self._get_ready_nodes(state)
            if ready:
                yield from self._execute_parallel(ready, state)

            yield from self._handle_failures(state)

            if not ready and not state.running:
                if state.pending:
                    logging.error("DAG deadlock detected, pending: %s", state.pending)
                    for nid in list(state.pending):
                        state.failed.add(nid)
                break

        # Phase 3: Final summary
        yield from self._summarize(state)

    def _get_ready_nodes(self, state: ExecutionState) -> list:
        ready = []
        for nid in list(state.pending):
            node = state.node_map[nid]
            if all(d in state.completed for d in node.depends_on):
                if any(d in state.failed for d in node.depends_on):
                    state.pending.discard(nid)
                    state.failed.add(nid)
                    continue
                ready.append(node)
        for n in ready:
            state.pending.discard(n.id)
            state.running.add(n.id)
        return ready

    def _build_progress_prompt(self, state: ExecutionState, current_node_id: str = "") -> str:
        """Build a todo-style progress tracker for injection into LLM context.

        Manus-inspired: a continuously updated todo list pushes the global objective
        into the model's recent attention span, combating lost-in-the-middle drift.
        """
        lines = ["## 当前任务进度"]
        for node in state.plan.nodes:
            nid = node.id
            desc = node.desc
            if nid in state.completed:
                lines.append(f"- [x] {desc}")
            elif nid == current_node_id:
                lines.append(f"- [ ] **{desc}** ← 当前步骤")
            elif nid in state.failed:
                lines.append(f"- [!] {desc} (失败)")
            elif nid in state.running:
                lines.append(f"- [ ] {desc} (进行中)")
            else:
                lines.append(f"- [ ] {desc}")
        total = len(state.plan.nodes)
        done = len(state.completed)
        lines.append(f"\n进度: {done}/{total} 已完成")
        return "\n".join(lines)

    def _execute_parallel(self, nodes: list, state: ExecutionState) -> Generator:
        pool = _dag_pool.get()
        split = next((i for i, m in enumerate(self.messages) if m.get("role") != "system"), 0)
        sys_prefix = self.messages[:split]
        conv_suffix = self.messages[split:]

        node_queues: dict[str, queue.Queue] = {}
        futures: dict = {}
        pending_nodes: set = set()

        for node in nodes:
            yield ("step_start", {"step_id": node.id, "desc": node.desc, "index": 0, "total": len(state.node_map)})
            node_msgs = sys_prefix + list(conv_suffix)
            eq: queue.Queue = queue.Queue()
            node_queues[node.id] = eq
            pending_nodes.add(node.id)
            f = pool.submit(self._execute_single_node, node, state, node_msgs, eq)
            futures[f] = node

        while pending_nodes:
            for nid, eq in list(node_queues.items()):
                if nid not in pending_nodes:
                    continue
                try:
                    event = eq.get(timeout=0.05)
                    yield event
                    while True:
                        event = eq.get_nowait()
                        yield event
                except queue.Empty:
                    pass

            newly_done = []
            for f, node in list(futures.items()):
                if f.done() and node.id in pending_nodes:
                    newly_done.append((f, node))

            for f, node in newly_done:
                pending_nodes.discard(node.id)
                try:
                    success, result = f.result(timeout=1)
                except ExecutorTimeout:
                    success = False
                    result = {"error": "步骤执行超时"}
                except Exception as ex:
                    logging.exception("agent_dag: DAG node execution failed: %s", ex)
                    success = False
                    result = {"error": str(ex)}

                eq = node_queues.get(node.id)
                if eq:
                    try:
                        while True:
                            event = eq.get_nowait()
                            yield event
                    except queue.Empty:
                        pass

                state.running.discard(node.id)
                if success:
                    state.completed.add(node.id)
                    state.results[node.id] = StepResult(step_id=node.id, success=True, output=result)
                    yield ("step_end", {"step_id": node.id, "success": True, "desc": node.desc, "result": result})
                else:
                    state.failed.add(node.id)
                    state.results[node.id] = StepResult(step_id=node.id, success=False, output=result)
                    yield (
                        "step_fail",
                        {
                            "step_id": node.id,
                            "desc": node.desc,
                            "error": result.get("error", "未知错误"),
                            "reflection": result.get("reflection"),
                        },
                    )

    def _execute_single_node(
        self, node: DAGNode, state: ExecutionState, messages: list = None, event_queue: queue.Queue = None
    ) -> tuple:
        msgs = messages if messages is not None else self.messages

        if self.tracer:
            step_sid = self.tracer.start_span(f"step:{node.id}", input={"desc": node.desc, "tool_hint": node.tool_hint})

        ctx_hint = self.shared_context.sniff()
        progress = self._build_progress_prompt(state, node.id)
        instruction = (
            f"{progress}\n\n{ctx_hint}现在执行计划步骤: {node.desc}\n请仅执行这一步需要的工具调用，完成后简要用文字描述结果。"
        )
        # ── Critic 质量提示注入 ──
        if self._critic_hints:
            instruction += f"\n\n{self._critic_hints}"
        msgs.append({"role": "user", "content": instruction})

        loop_counter = defaultdict(int)
        retries = 0

        def _finish_step(success, result):
            if self.tracer:
                status = "ok" if success else "error"
                self.tracer.end_span(step_sid, status, {"result": result.get("text", "") or result.get("error", "")})
            return success, result

        node_start = time.time()
        while retries <= MAX_REFLECT_RETRIES:
            if time.time() - node_start > MAX_NODE_SECONDS:
                return _finish_step(False, {"error": f"节点超时（{MAX_NODE_SECONDS}秒）"})
            self._trim_step_messages(msgs)
            iteration = 0
            while iteration < 50:
                if time.time() - node_start > MAX_NODE_SECONDS:
                    return _finish_step(False, {"error": f"节点超时（{MAX_NODE_SECONDS}秒）"})
                iteration += 1

                # Unified path: always use streaming LLM; tokens only emitted when self.stream
                tool_calls_received = []
                full_text = ""
                stream_error = None

                for se in self._call_llm_stream_with_msgs(msgs):
                    skind = se[0]
                    if skind == "token":
                        if self.stream and event_queue is not None:
                            event_queue.put(("token", se[1], node.id))
                    elif skind == "llm_tool_call":
                        tool_calls_received.append(se[1:])
                    elif skind == "text_complete":
                        full_text = se[1]
                    elif skind == "error":
                        stream_error = se[1]

                if stream_error:
                    return _finish_step(False, {"error": stream_error})

                if tool_calls_received:
                    msgs.append(self._format_stream_tool_msg(tool_calls_received))

                    tool_retry = False
                    for tc_name, tc_id, tc_args_str in tool_calls_received:
                        try:
                            tool_args = json.loads(tc_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}

                        lk = _loop_key(tc_name, tool_args)
                        loop_counter[lk] += 1
                        if loop_counter[lk] > MAX_LOOP_REPEAT:
                            return _finish_step(False, {"error": f"操作 {tc_name} 重复多次仍失败"})

                        result = self._run_dag_tool(tc_name, tool_args, tc_id, msgs, event_queue, node.id)
                        if not result.get("success"):
                            reflection = self._reflect(node, tc_name, tool_args, result, state)
                            if reflection.get("recovery") == "retry" and retries < MAX_REFLECT_RETRIES:
                                retries += 1
                                adjusted = reflection.get("adjusted_args") or {}
                                raw_error = result.get("error", "") or _json.dumps(result, ensure_ascii=False)
                                msgs.append(
                                    {
                                        "role": "user",
                                        "content": (
                                            f"[!] 工具 {tc_name} 执行失败（第 {retries}/{MAX_REFLECT_RETRIES} 次重试）\n"
                                            f"错误信息: {raw_error[:500]}\n"
                                            f"原因分析: {reflection.get('cause', '未知')}\n"
                                            f"修复建议: {reflection.get('suggestion', '请重试')}\n"
                                            f"调整参数: {_json.dumps(adjusted, ensure_ascii=False) if adjusted else '请自行判断并调整参数，不要重复相同的错误参数'}"
                                        ),
                                    }
                                )
                                tool_retry = True
                                break
                            else:
                                return _finish_step(
                                    False, {"error": result.get("error", "未知错误"), "reflection": reflection}
                                )

                    if tool_retry:
                        break
                    continue

                if full_text:
                    if event_queue is not None:
                        event_queue.put(("think", full_text, node.id))
                return _finish_step(True, {"text": full_text})

            if retries > MAX_REFLECT_RETRIES:
                return _finish_step(False, {"error": f"重试 {MAX_REFLECT_RETRIES} 次后仍然失败"})

        return _finish_step(False, {"error": "步骤执行异常"})

    def _run_simple_tool_batch(self, tool_calls: list, loop_counter: defaultdict) -> Generator:
        """Execute a batch of tool calls, yielding tool_call / tool_result events.

        Returns (any_failure, search_missing_keyword) via StopIteration, or
        yields ("error", ...) and returns None on a fatal loop-guard hit.
        """
        any_failure = False
        search_missing_keyword = False
        for tc_name, tc_id, tc_args_str in tool_calls:
            try:
                tool_args = json.loads(tc_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            lk = _loop_key(tc_name, tool_args)
            loop_counter[lk] += 1
            if loop_counter[lk] > MAX_LOOP_REPEAT:
                yield ("error", f"操作 {tc_name} 重复多次仍失败")
                return None

            yield ("tool_call", tc_name, tool_args)
            result = self._run_simple_tool(tc_name, tool_args, tc_id)
            yield ("tool_result", tc_name, result.get("success", False), result)
            if not result.get("success"):
                any_failure = True
                if tc_name in ("web_search", "web_fetch") and "keyword" in str(result.get("error", "")):
                    search_missing_keyword = True

        return (any_failure, search_missing_keyword)

    def _execute_simple(self) -> Generator:
        """Simple single-round ReAct for non-tool queries. Both paths share _run_simple_tool_batch."""
        iteration = 0
        loop_counter = defaultdict(int)
        retries = 0
        accumulated_text = ""
        consecutive_tool_calls = 0

        while iteration < 50:
            iteration += 1

            if self.stream:
                tool_calls_received = []
                full_text = ""
                stream_error = None

                for event in self._call_llm_stream():
                    kind = event[0]
                    if kind == "token":
                        yield event
                    elif kind == "llm_tool_call":
                        tool_calls_received.append(event[1:])
                    elif kind == "text_complete":
                        full_text = event[1]
                    elif kind == "error":
                        stream_error = event[1]

                if stream_error:
                    yield ("error", stream_error)
                    return

                if not tool_calls_received:
                    if full_text:
                        accumulated_text += full_text
                    llm_response = SimpleNamespace(message=SimpleNamespace(content=full_text), finish_reason="stop")
                    yield ("llm_response", llm_response, self._tool_call_count)
                    return

                self.messages.append(self._format_stream_tool_msg(tool_calls_received))
                tool_calls = tool_calls_received
            else:
                try:
                    response = self._call_llm()
                except Exception as e:
                    msg = str(e)
                    if not msg or len(msg) < 5:
                        msg = repr(e)
                    yield ("error", f"AI 服务不可用: {msg[:200]}")
                    return
                if response is None:
                    yield ("error", "AI 服务不可用（熔断保护中，请稍后再试）")
                    return
                if not response.choices:
                    yield ("error", "AI 返回异常")
                    return

                choice = response.choices[0]
                if choice.finish_reason != "tool_calls":
                    yield ("llm_response", choice, self._tool_call_count)
                    return

                msg = choice.message
                self.messages.append(self._format_assistant_msg(msg))
                tool_calls = [(tc.function.name, tc.id, tc.function.arguments) for tc in msg.tool_calls]

            # ── Shared tool execution ──
            batch_result = yield from self._run_simple_tool_batch(tool_calls, loop_counter)
            if batch_result is None:
                return
            any_failure, search_missing_keyword = batch_result

            if any_failure and retries < MAX_REFLECT_RETRIES:
                retries += 1
                self._append_simple_retry_msg(tool_calls, retries, search_missing_keyword)
                loop_counter.clear()
                continue

            consecutive_tool_calls += len(tool_calls)
            if consecutive_tool_calls >= 5:
                self.messages.append(
                    {
                        "role": "user",
                        "content": "已完成足够多的工具调用，请直接根据已有结果给出最终文字回复，不要再调用工具。",
                    }
                )
                consecutive_tool_calls = 0
            continue

        if accumulated_text.strip():
            llm_response = SimpleNamespace(
                message=SimpleNamespace(content=accumulated_text.strip()), finish_reason="stop"
            )
            yield ("llm_response", llm_response, self._tool_call_count)
        else:
            yield ("error", "推理步数已达上限")

    # ── DAG Execution ────────────────────────────────────────────────────

    def _reflect(
        self, node: DAGNode, tool_name: str, tool_args: dict, error_result: dict, state: ExecutionState
    ) -> dict:
        self._reflection_count += 1
        completed = [state.node_map[nid].desc for nid in state.completed]
        remaining = [state.node_map[nid].desc for nid in state.pending]
        return self.reflexion.analyze_failure(
            tool_name=tool_name,
            tool_args=tool_args,
            error_result=error_result,
            goal=state.plan.goal,
            step_desc=node.desc,
            completed_steps=completed,
            remaining_steps=remaining,
        )

    def _handle_failures(self, state: ExecutionState) -> Generator:
        if self._should_replan(state):
            yield from self._execute_replan(state)

        cascaded = []
        for nid in list(state.failed):
            for other_nid in list(state.pending):
                other = state.node_map[other_nid]
                if nid in other.depends_on:
                    state.pending.discard(other_nid)
                    state.failed.add(other_nid)
                    cascaded.append((other_nid, other.desc, nid))
        if cascaded:
            yield (
                "cascade",
                {"root": cascaded[0][2], "skipped": [{"id": nid, "desc": desc} for nid, desc, _ in cascaded]},
            )

    def _should_replan(self, state: ExecutionState) -> bool:
        if self._replan_used:
            return False
        if not state.pending:
            return False
        if not state.failed:
            return False
        return True

    def _execute_replan(self, state: ExecutionState) -> Generator:
        self._replan_used = True
        from app.util.agent.adaptive import replan_node

        failed_ids = list(state.failed)
        failed_nid = failed_ids[0]
        failed_node = state.node_map.get(failed_nid)
        if not failed_node:
            return

        result = state.results.get(failed_nid)
        error_msg = ""
        if result and result.output:
            error_msg = str(result.output.get("error", result.output.get("text", "")))

        completed_steps = []
        for nid in state.completed:
            node = state.node_map.get(nid)
            r = state.results.get(nid)
            desc = node.desc if node else nid
            brief = ""
            if r and r.output:
                brief = str(r.output.get("text", ""))[:200]
            completed_steps.append((nid, desc, brief))

        remaining_steps = []
        for nid in state.pending:
            node = state.node_map.get(nid)
            if node:
                remaining_steps.append((nid, node.desc, node.tool_hint))

        yield ("progress", f"步骤 {failed_nid} 失败，正在尝试重新规划...")

        replacement = replan_node(
            llm_client=self.llm,
            model=self.model,
            plan_goal=state.plan.goal,
            failed_node_id=failed_nid,
            failed_step_desc=failed_node.desc,
            tool_hint=failed_node.tool_hint or "无",
            error_msg=error_msg,
            completed_steps=completed_steps,
            remaining_steps=remaining_steps,
            shared_context_sniff=self.shared_context.sniff(),
        )

        if not replacement:
            yield ("progress", "无法生成替代方案，将跳过失败步骤继续执行")
            return

        for rn in replacement:
            new_node = DAGNode(
                id=rn["id"],
                desc=rn["desc"],
                tool_hint=rn.get("tool_hint"),
                agent_name=rn.get("agent_name"),
                confirm=rn.get("confirm", False),
                depends_on=rn.get("depends_on", []),
                parallel_group=rn.get("parallel_group"),
            )
            state.node_map[new_node.id] = new_node
            state.pending.add(new_node.id)

        yield ("progress", f"已生成 {len(replacement)} 个替代步骤，继续执行")

    def _summarize(self, state: ExecutionState) -> Generator:
        all_done = len(state.completed) == len(state.node_map)
        self._record_plan_feedback(state, all_done)

        if all_done:
            lines = []
            for i, n in enumerate(state.plan.nodes, 1):
                r = state.results.get(n.id)
                text = (r.output.get("text") if r else "") or ""
                lines.append(f"{i}. {n.desc}" + (f" — {text}" if text else " — 完成"))
            summary = "任务已全部完成：\n" + "\n".join(lines)
            yield ("llm_response", SimpleNamespace(message=SimpleNamespace(content=summary)), 0)
        else:
            completed_desc = [state.node_map[nid].desc for nid in state.completed]
            failed_desc = [state.node_map[nid].desc for nid in state.failed]
            verification = self.reflexion.verify_overall_goal(state.plan.goal, completed_desc, failed_desc)
            result_lines = []
            for nid in state.completed:
                result_lines.append(f"✓ {state.node_map[nid].desc}")
            for nid in state.failed:
                result_lines.append(f"✗ {state.node_map[nid].desc}")
            summary = f"{verification.get('summary', '')}\n" + "\n".join(result_lines)
            if verification.get("missing"):
                summary += f"\n\n未完成要点: {', '.join(verification['missing'])}"
            yield ("llm_response", SimpleNamespace(message=SimpleNamespace(content=summary)), 0)

        yield (
            "done",
            {
                "status": "completed" if all_done else "partial",
                "completed": len(state.completed),
                "total": len(state.node_map),
            },
        )

    def _record_plan_feedback(self, state: ExecutionState, all_done: bool):
        try:
            from app.util.agent.plan_eval import PlanMemory, evaluate_plan

            completed_desc = [state.node_map[nid].desc for nid in state.completed]
            failed_desc = [state.node_map[nid].desc for nid in state.failed]
            duration_ms = (time.time() - self._dag_start_ts) * 1000 if self._dag_start_ts else 0
            domains = []
            try:
                from app.util.agent.intent import classify_domain

                domains = classify_domain(state.plan.goal)
                if domains == ["general"]:
                    domains = []
            except Exception:
                pass
            feedback = evaluate_plan(
                goal=state.plan.goal,
                domains=domains,
                completed=completed_desc,
                failed=failed_desc,
                reflections=self._reflection_count,
                duration_ms=duration_ms,
            )
            PlanMemory.record(feedback)
            logging.info(
                "Plan-Feedback recorded: score=%.2f, %d/%d steps succeeded, %d reflections",
                feedback.score,
                len(state.completed),
                len(state.node_map),
                self._reflection_count,
            )
        except Exception:
            logging.debug("Plan-Feedback recording skipped (non-critical)", exc_info=True)
