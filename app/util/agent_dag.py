# -*- coding: UTF-8 -*-
"""DAG Executor — topological sort, parallel execution with ReAct loop.
Adapted from pypano for mind project."""

import hashlib
import json
import logging
import queue
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Generator

from app.config import LLM_TIMEOUT
from app.util.agent_pheromone import SharedContext, extract_discoveries
from app.util.executor import ExecutorTimeout, ManagedPool

_dag_pool = ManagedPool(max_workers=8, prefix="dag-")


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

MAX_REFLECT_RETRIES = 3
MAX_LOOP_REPEAT = 3
MAX_DAG_TOTAL_SECONDS = 300
MAX_NODE_SECONDS = 120
MAX_TOOL_RESULT_CHARS = 800


def _truncate_tool_result(result: dict) -> dict:
    truncated = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > MAX_TOOL_RESULT_CHARS:
            truncated[k] = v[:MAX_TOOL_RESULT_CHARS] + f"...(截断，原{len(v)}字符)"
        elif isinstance(v, list) and len(v) > 5:
            truncated[k] = v[:3] + [f"...(共{len(v)}项，已截断)"]
        elif isinstance(v, dict):
            s = json.dumps(v, ensure_ascii=False)
            if len(s) > MAX_TOOL_RESULT_CHARS:
                truncated[k] = {"_truncated": True, "preview": s[:MAX_TOOL_RESULT_CHARS]}
            else:
                truncated[k] = v
        else:
            truncated[k] = v
    return truncated


def _loop_key(tool_name: str, tool_args: dict) -> str:
    args_str = json.dumps(tool_args, ensure_ascii=False, sort_keys=True)
    return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()[:8]}"


class DAGExecutor:
    """Executes a DAGPlan using topological sort + parallel ThreadPoolExecutor."""

    MAX_STEP_MESSAGES = 30

    def __init__(self, llm_client, tools_schemas: list, messages: list,
                 hooks: list = None, tool_context: dict = None, user_id: str = "",
                 model: str = "deepseek-chat", confirm_handler=None, dispatcher=None,
                 tracer=None, stream: bool = False, redis_client=None, task_id: str = ""):
        self.llm = llm_client
        self.tools = tools_schemas
        self.messages = messages
        self.hooks = hooks or []
        self.tool_context = tool_context or {}
        if redis_client:
            self.tool_context["_redis"] = redis_client
            self.tool_context["_task_id"] = task_id
        self.user_id = user_id
        self.model = model
        self.confirm_handler = confirm_handler
        self.dispatcher = dispatcher
        self.tracer = tracer
        self.stream = stream
        self.shared_context = SharedContext()
        self._replan_used = False
        self._tool_call_count = 0
        self._reflection_count = 0
        self._dag_start_ts = 0.0
        from app.util.agent_reflexion import AgentReflexion
        self.reflexion = AgentReflexion(llm_client, model)

    @property
    def tool_call_count(self):
        return self._tool_call_count

    def execute(self, plan: DAGPlan) -> Generator:
        if plan.mode == "simple" or not plan.nodes:
            yield from self._execute_simple()
            return

        state = ExecutionState.from_plan(plan)
        self._replan_used = False

        yield ("plan", {
            "goal": plan.goal,
            "nodes": [{"id": n.id, "desc": n.desc, "depends_on": n.depends_on,
                        "parallel_group": n.parallel_group, "confirm": n.confirm} for n in plan.nodes],
            "risk": plan.risk, "mode": "dag",
        })

        # Phase 1: Confirmation check
        destructive = [n for n in plan.nodes if n.confirm]
        if destructive and self.confirm_handler:
            approved = self.confirm_handler("destructive_ops", {
                "steps": [{"id": n.id, "desc": n.desc} for n in destructive], "goal": plan.goal,
            })
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
                    yield ("step_fail", {"step_id": node.id, "desc": node.desc,
                                         "error": result.get("error", "未知错误"),
                                         "reflection": result.get("reflection")})

    def _execute_single_node(self, node: DAGNode, state: ExecutionState,
                             messages: list = None, event_queue: queue.Queue = None) -> tuple:
        msgs = messages if messages is not None else self.messages

        if self.tracer:
            step_sid = self.tracer.start_span(f"step:{node.id}", input={"desc": node.desc, "tool_hint": node.tool_hint})

        ctx_hint = self.shared_context.sniff()
        instruction = f"{ctx_hint}现在执行计划步骤: {node.desc}\n请仅执行这一步需要的工具调用，完成后简要用文字描述结果。"
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
            while iteration < 5:
                if time.time() - node_start > MAX_NODE_SECONDS:
                    return _finish_step(False, {"error": f"节点超时（{MAX_NODE_SECONDS}秒）"})
                iteration += 1
                response = self._call_llm(msgs)
                if response is None:
                    return _finish_step(False, {"error": "AI 服务不可用"})
                if not response.choices:
                    return _finish_step(False, {"error": "AI 返回异常"})

                choice = response.choices[0]
                finish = choice.finish_reason

                if finish == "tool_calls":
                    msg = choice.message
                    msgs.append(self._format_assistant_msg(msg))

                    tool_retry = False
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        try:
                            tool_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}

                        lk = _loop_key(tool_name, tool_args)
                        loop_counter[lk] += 1
                        if loop_counter[lk] > MAX_LOOP_REPEAT:
                            return _finish_step(False, {"error": f"操作 {tool_name} 重复多次仍失败"})

                        if self.tracer:
                            tool_sid = self.tracer.start_span(f"tool:{tool_name}", input=tool_args)
                        t0 = time.time()

                        if event_queue is not None:
                            event_queue.put(("tool_call", tool_name, tool_args, node.id))

                        from app.util.agent_tools import run_tool_call

                        result, _ = run_tool_call(tool_name, tool_args, self.tool_context,
                                                  self.dispatcher, self.llm, self.model, self.tracer,
                                                  self.shared_context.sniff())
                        if self.tracer:
                            self.tracer.end_span(tool_sid, "ok" if result.get("success") else "error",
                                                 {"duration_ms": int((time.time() - t0) * 1000)})

                        self._tool_call_count += 1

                        if event_queue is not None:
                            event_queue.put(("tool_result", tool_name, result.get("success", False), result, node.id))

                        result = _truncate_tool_result(result)
                        msgs.append({"role": "tool", "tool_call_id": tc.id,
                                      "content": json.dumps(result, ensure_ascii=False)})

                        discoveries = extract_discoveries(tool_name, tool_args, result)
                        for k, v in discoveries.items():
                            self.shared_context.deposit(k, v, source_node=node.id, source_tool=tool_name)

                        if not result.get("success"):
                            reflection = self._reflect(node, tool_name, tool_args, result, state)
                            if reflection.get("recovery") == "retry" and retries < MAX_REFLECT_RETRIES:
                                retries += 1
                                adjusted = reflection.get("adjusted_args") or {}
                                msgs.append({"role": "user", "content": (
                                    f"上一步失败了。原因: {reflection.get('cause', '未知')}\n"
                                    f"建议: {reflection.get('suggestion', '请重试')}\n"
                                    f"调整参数: {json.dumps(adjusted, ensure_ascii=False) if adjusted else '自行判断'}"
                                )})
                                tool_retry = True
                                break
                            else:
                                return _finish_step(False, {"error": result.get("error", "未知错误"),
                                                            "reflection": reflection})

                    if tool_retry:
                        break
                    continue

                # Text response → success
                content = choice.message.content or ""
                if event_queue is not None and content:
                    event_queue.put(("think", content, node.id))
                return _finish_step(True, {"text": content})

            if retries > MAX_REFLECT_RETRIES:
                return _finish_step(False, {"error": f"重试 {MAX_REFLECT_RETRIES} 次后仍然失败"})

        return _finish_step(False, {"error": "步骤执行异常"})

    def _execute_simple(self) -> Generator:
        """Simple single-round ReAct for non-tool queries."""
        if self.stream:
            yield from self._execute_simple_streaming()
            return

        iteration = 0
        loop_counter = defaultdict(int)
        retries = 0

        while iteration < 10:
            iteration += 1
            response = self._call_llm()
            if response is None:
                yield ("error", "AI 服务不可用")
                return
            if not response.choices:
                yield ("error", "AI 返回异常")
                return

            choice = response.choices[0]
            finish = choice.finish_reason

            if finish == "tool_calls":
                msg = choice.message
                self.messages.append(self._format_assistant_msg(msg))

                any_failure = False
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    lk = _loop_key(tool_name, tool_args)
                    loop_counter[lk] += 1
                    if loop_counter[lk] > MAX_LOOP_REPEAT:
                        yield ("error", f"操作 {tool_name} 重复多次仍失败")
                        return

                    yield ("tool_call", tool_name, tool_args)

                    if self.tracer:
                        tool_sid = self.tracer.start_span(f"tool:{tool_name}", input=tool_args)
                    t0 = time.time()
                    from app.util.agent_tools import run_tool_call

                    result, _ = run_tool_call(tool_name, tool_args, self.tool_context,
                                              self.dispatcher, self.llm, self.model, self.tracer,
                                              self.shared_context.sniff())
                    if self.tracer:
                        self.tracer.end_span(tool_sid, "ok" if result.get("success") else "error",
                                             {"duration_ms": int((time.time() - t0) * 1000)})

                    self._tool_call_count += 1
                    yield ("tool_result", tool_name, result.get("success", False), result)

                    result = _truncate_tool_result(result)
                    self.messages.append({"role": "tool", "tool_call_id": tc.id,
                                           "content": json.dumps(result, ensure_ascii=False)})

                    if not result.get("success"):
                        any_failure = True

                    discoveries = extract_discoveries(tool_name, tool_args, result)
                    for k, v in discoveries.items():
                        self.shared_context.deposit(k, v, source_node="simple", source_tool=tool_name)

                if any_failure and retries < MAX_REFLECT_RETRIES:
                    retries += 1
                    failed_names = {tc.function.name for tc in msg.tool_calls}
                    if failed_names & {"web_search", "web_fetch"}:
                        self.messages.append({"role": "user", "content": (
                            "搜索工具暂时不可用。请直接用你自身的知识回答用户的问题，不需要再尝试搜索。直接给出文字回复即可。"
                        )})
                    else:
                        self.messages.append({"role": "user", "content": (
                            f"上一步工具执行失败了。请分析错误原因，尝试用不同的参数或方法重试。（第 {retries}/{MAX_REFLECT_RETRIES} 次重试）"
                        )})
                    loop_counter.clear()
                    continue
                continue

            yield ("llm_response", choice, self._tool_call_count)
            return

        yield ("error", "推理步数已达上限")

    # ── LLM Call Methods ──────────────────────────────────────────────────

    @staticmethod
    def _llm_retry_sleep(attempt: int, is_rate_limit: bool = False):
        base = 2 ** attempt
        if is_rate_limit:
            time.sleep(base + random.uniform(0, 1))
        else:
            time.sleep(base * random.uniform(0.75, 1.25))

    @staticmethod
    def _should_retry_llm(error: Exception, attempt: int) -> bool:
        if attempt >= 2:
            return False
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        if isinstance(error, (RateLimitError, APITimeoutError, APIConnectionError)):
            return True
        if isinstance(error, APIError):
            status = getattr(error, "http_status", None) or getattr(error, "status_code", None) or 500
            return status >= 500
        return True

    def _call_llm(self, messages=None):
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        from app.util.agent_circuit import circuit_allow, circuit_record

        msgs = messages if messages is not None else self.messages
        if not circuit_allow(service=self.model):
            logging.warning("DAGExecutor LLM call blocked by circuit breaker [%s]", self.model)
            return None

        llm_span_id = None
        for attempt in range(3):
            if self.tracer:
                llm_span_id = self.tracer.start_span("llm_api_call", input={"model": self.model, "attempt": attempt + 1})
            try:
                result = self.llm.chat.completions.create(
                    model=self.model, messages=msgs, tools=self.tools,
                    tool_choice="auto", stream=False, timeout=LLM_TIMEOUT,
                )
                circuit_record(True, service=self.model)
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "ok")
                return result
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as ex:
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
                if isinstance(ex, APIError):
                    status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                    if status < 500:
                        circuit_record(False, service=self.model)
                        raise
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt, isinstance(ex, RateLimitError))
            except Exception as ex:
                logging.warning("LLM call attempt %d: %s", attempt + 1, ex)
                if self.tracer:
                    self.tracer.end_span(llm_span_id, "error", {"error": str(ex)[:100]})
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt)
        circuit_record(False, service=self.model)
        if self.tracer:
            self.tracer.end_span(llm_span_id, "error", {"error": "All retries exhausted"})
        return None

    def _call_llm_stream(self) -> Generator:
        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
        from app.util.agent_circuit import circuit_allow, circuit_record

        if not circuit_allow(service=self.model):
            yield ("error", "AI 服务不可用（熔断）")
            return

        for attempt in range(3):
            try:
                response = self.llm.chat.completions.create(
                    model=self.model, messages=self.messages, tools=self.tools,
                    tool_choice="auto", stream=True, timeout=90,
                )
                tool_calls_acc = {}
                full_text = ""
                finish_reason = None

                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason
                    if delta.content:
                        full_text += delta.content
                        yield ("token", delta.content)
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                            acc = tool_calls_acc[idx]
                            if tc_delta.id:
                                acc["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    acc["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    acc["arguments"] += tc_delta.function.arguments
                    if finish_reason:
                        break

                circuit_record(True, service=self.model)

                if finish_reason == "tool_calls" and tool_calls_acc:
                    for idx in sorted(tool_calls_acc.keys()):
                        acc = tool_calls_acc[idx]
                        yield ("llm_tool_call", acc["name"], acc["id"], acc["arguments"])
                    return

                yield ("text_complete", full_text)
                return

            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as ex:
                if isinstance(ex, APIError):
                    status = getattr(ex, "http_status", None) or getattr(ex, "status_code", None) or 500
                    if status < 500:
                        circuit_record(False, service=self.model)
                        yield ("error", f"API 错误: {ex}")
                        return
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt, isinstance(ex, RateLimitError))
            except Exception as ex:
                logging.exception("agent_dag: unexpected LLM streaming error: %s", ex)
                if self._should_retry_llm(ex, attempt):
                    self._llm_retry_sleep(attempt)

        circuit_record(False, service=self.model)
        yield ("error", "LLM 流式调用失败")

    def _execute_simple_streaming(self) -> Generator:
        iteration = 0
        loop_counter = defaultdict(int)

        while iteration < 10:
            iteration += 1
            tool_calls_received = []
            full_text = ""
            error_msg = None

            for event in self._call_llm_stream():
                kind = event[0]
                if kind == "token":
                    yield event
                elif kind == "llm_tool_call":
                    tool_calls_received.append(event[1:])
                elif kind == "text_complete":
                    full_text = event[1]
                elif kind == "error":
                    error_msg = event[1]

            if error_msg:
                yield ("error", error_msg)
                return

            if tool_calls_received:
                tool_msgs = []
                for tc_name, tc_id, tc_args_str in tool_calls_received:
                    try:
                        tc_args = json.loads(tc_args_str)
                    except json.JSONDecodeError:
                        tc_args = {}
                    tool_msgs.append({"id": tc_id, "type": "function", "function": {"name": tc_name, "arguments": tc_args_str}})

                self.messages.append({"role": "assistant", "content": "", "tool_calls": tool_msgs})

                for tc_name, tc_id, tc_args_str in tool_calls_received:
                    try:
                        tc_args = json.loads(tc_args_str)
                    except json.JSONDecodeError:
                        tc_args = {}

                    lk = _loop_key(tc_name, tc_args)
                    loop_counter[lk] += 1
                    if loop_counter[lk] > MAX_LOOP_REPEAT:
                        yield ("error", f"操作 {tc_name} 重复多次仍失败")
                        return

                    yield ("tool_call", tc_name, tc_args)

                    if self.tracer:
                        tool_sid = self.tracer.start_span(f"tool:{tc_name}", input=tc_args)
                    t0 = time.time()
                    from app.util.agent_tools import run_tool_call

                    result, _ = run_tool_call(tc_name, tc_args, self.tool_context,
                                              self.dispatcher, self.llm, self.model, self.tracer,
                                              self.shared_context.sniff())
                    if self.tracer:
                        self.tracer.end_span(tool_sid, "ok" if result.get("success") else "error",
                                             {"duration_ms": int((time.time() - t0) * 1000)})

                    self._tool_call_count += 1
                    yield ("tool_result", tc_name, result.get("success", False), result)

                    result = _truncate_tool_result(result)
                    self.messages.append({"role": "tool", "tool_call_id": tc_id,
                                           "content": json.dumps(result, ensure_ascii=False)})

                    discoveries = extract_discoveries(tc_name, tc_args, result)
                    for k, v in discoveries.items():
                        self.shared_context.deposit(k, v, source_node="simple", source_tool=tc_name)

                    if not result.get("success") and tc_name in ("web_search", "web_fetch"):
                        self.messages.append({"role": "user", "content": "搜索工具暂时不可用。请直接用你自身的知识回答用户的问题。"})
                continue

            if full_text:
                llm_response = SimpleNamespace(message=SimpleNamespace(content=full_text), finish_reason="stop")
                yield ("llm_response", llm_response, self._tool_call_count)
            return

        yield ("error", "推理步数已达上限")

    def _reflect(self, node: DAGNode, tool_name: str, tool_args: dict,
                 error_result: dict, state: ExecutionState) -> dict:
        self._reflection_count += 1
        completed = [state.node_map[nid].desc for nid in state.completed]
        remaining = [state.node_map[nid].desc for nid in state.pending]
        return self.reflexion.analyze_failure(
            tool_name=tool_name, tool_args=tool_args, error_result=error_result,
            goal=state.plan.goal, step_desc=node.desc,
            completed_steps=completed, remaining_steps=remaining,
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
            yield ("cascade", {"root": cascaded[0][2],
                               "skipped": [{"id": nid, "desc": desc} for nid, desc, _ in cascaded]})

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
        from app.util.agent_adaptive import replan_node

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
            llm_client=self.llm, model=self.model, plan_goal=state.plan.goal,
            failed_node_id=failed_nid, failed_step_desc=failed_node.desc,
            tool_hint=failed_node.tool_hint or "无", error_msg=error_msg,
            completed_steps=completed_steps, remaining_steps=remaining_steps,
            shared_context_sniff=self.shared_context.sniff(),
        )

        if not replacement:
            yield ("progress", "无法生成替代方案，将跳过失败步骤继续执行")
            return

        for rn in replacement:
            new_node = DAGNode(id=rn["id"], desc=rn["desc"], tool_hint=rn.get("tool_hint"),
                               agent_name=rn.get("agent_name"), confirm=rn.get("confirm", False),
                               depends_on=rn.get("depends_on", []), parallel_group=rn.get("parallel_group"))
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

        yield ("done", {"status": "completed" if all_done else "partial",
                        "completed": len(state.completed), "total": len(state.node_map)})

    def _record_plan_feedback(self, state: ExecutionState, all_done: bool):
        try:
            from app.util.agent_plan_eval import PlanMemory, evaluate_plan
            completed_desc = [state.node_map[nid].desc for nid in state.completed]
            failed_desc = [state.node_map[nid].desc for nid in state.failed]
            duration_ms = (time.time() - self._dag_start_ts) * 1000 if self._dag_start_ts else 0
            domains = []
            try:
                from app.util.agent_intent import classify_domain
                domains = classify_domain(state.plan.goal)
                if domains == ["general"]:
                    domains = []
            except Exception:
                pass
            feedback = evaluate_plan(goal=state.plan.goal, domains=domains,
                                     completed=completed_desc, failed=failed_desc,
                                     reflections=self._reflection_count, duration_ms=duration_ms)
            PlanMemory.record(feedback)
            logging.info("Plan-Feedback recorded: score=%.2f, %d/%d steps succeeded, %d reflections",
                         feedback.score, len(state.completed), len(state.node_map), self._reflection_count)
        except Exception:
            logging.debug("Plan-Feedback recording skipped (non-critical)", exc_info=True)

    def _trim_step_messages(self, messages=None):
        msgs = messages if messages is not None else self.messages
        if len(msgs) <= self.MAX_STEP_MESSAGES:
            return
        system_msgs = [m for m in msgs if m.get("role") == "system"]
        other_msgs = [m for m in msgs if m.get("role") != "system"]
        keep_other = self.MAX_STEP_MESSAGES - len(system_msgs)
        keep_other = max(keep_other, min(10, len(other_msgs)))
        msgs[:] = system_msgs + other_msgs[-keep_other:]

    @staticmethod
    def _format_assistant_msg(msg) -> dict:
        return {
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                           for tc in (msg.tool_calls or [])],
        }
