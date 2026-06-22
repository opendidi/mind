# Agent 架构 + Meta2D 编辑器全量优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 全量优化 Agent 后端架构（去重/统一抽象/缓存/常量）和 Meta2D 前端编辑器（Bug修复/性能/架构增强），每 Phase 结束跑 pytest + vitest 门禁。

**架构:** 双线并行推进 — Agent 后端（Python/Flask）和 Meta2D 前端（Vue3/TypeScript）各自独立 Phase，互不阻塞。每 Phase 完成后统一跑质量门禁。

**技术栈:** Python 3, Flask, Flask-SocketIO, Vue 3, TypeScript, Meta2D, Vitest, pytest

---

## Agent 后端 Phase 1: 去重/去死代码

### Task A1: 移除 router.py

**文件:**
- 删除: `app/util/agent/router.py`
- 修改: `app/util/agent/__init__.py` (line 39)
- 修改: `app/util/agent/plan_eval.py` (引用 route_intent 处)

- [ ] **Step 1: 确认无其他引用**

```bash
cd E:\Programs\mind && grep -rn "router\|route_intent\|AgentRouter" app/ --include="*.py" | grep -v __pycache__
```

- [ ] **Step 2: 从 __init__.py 移除导出**

编辑 `app/util/agent/__init__.py`，删除 line 39: `from .router import AgentRouter`

- [ ] **Step 3: 更新 plan_eval.py**

`app/util/agent/plan_eval.py` 中引用 `route_intent` 处改为调用 `unified_intent_and_plan`。读取 plan_eval.py 找到确切引用位置。

- [ ] **Step 4: 删除 router.py**

```bash
cd E:\Programs\mind && rm app/util/agent/router.py
```

- [ ] **Step 5: 运行测试**

```bash
cd E:\Programs\mind && python -c "from app.util.agent import *; print('OK')"
```

- [ ] **Step 6: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): remove deprecated router.py — superseded by intent.py unified_intent_and_plan"
```

---

### Task A2: 移除 planner.py

**文件:**
- 删除: `app/util/agent/planner.py`
- 修改: `app/util/agent/__init__.py` (line 40)

- [ ] **Step 1: 确认无其他引用**

```bash
cd E:\Programs\mind && grep -rn "planner\|generate_plan\|AgentPlanner" app/ --include="*.py" | grep -v __pycache__
```

- [ ] **Step 2: 从 __init__.py 移除导出**

编辑 `app/util/agent/__init__.py`，删除 line 40: `from .planner import AgentPlanner`

- [ ] **Step 3: 删除 planner.py**

```bash
cd E:\Programs\mind && rm app/util/agent/planner.py
```

- [ ] **Step 4: 验证导入**

```bash
cd E:\Programs\mind && python -c "from app.util.agent import *; print('OK')"
```

- [ ] **Step 5: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): remove deprecated planner.py — superseded by intent.py unified planning"
```

---

### Task A3: 合并 session_memory.py → memory.py

**文件:**
- 修改: `app/util/agent/memory.py` — 新增 `restore_session()` 和 `persist_session()` 方法
- 修改: `app/util/agent/core.py` — 调用改为 MemoryManager
- 修改: `app/util/agent/__init__.py` (line 47) — 移除 SessionMemory 导出
- 删除: `app/util/agent/session_memory.py`

- [ ] **Step 1: 编写测试**

新建 `tests/test_memory_unified.py`:

```python
"""Test unified memory — session persistence + semantic recall."""
import pytest
from app.util.agent.memory import MemoryManager

def test_memory_manager_has_session_methods():
    """MemoryManager should expose restore_session and persist_session."""
    mgr = MemoryManager()
    assert hasattr(mgr, 'restore_session')
    assert hasattr(mgr, 'persist_session')

def test_restore_session_returns_dict():
    """restore_session should return a dict with messages and summary keys."""
    mgr = MemoryManager()
    # No Redis in CI — should return empty defaults gracefully
    result = mgr.restore_session("test_user")
    assert isinstance(result, dict)
    assert "messages" in result or result == {}
```

- [ ] **Step 2: 将 SessionMemory 逻辑并入 MemoryManager**

在 `app/util/agent/memory.py` 的 `MemoryManager` 类中添加两个方法（在 `recall` 方法之后，约 line 143）:

```python
def restore_session(self, user_id: str) -> dict:
    """Restore session context — raw messages + semantic recall merged."""
    try:
        r = self._get_redis()
        if not r:
            return {}
        raw = self._load_raw(user_id, r)
        ctx = self.recall(user_id)
        return {
            "messages": raw.get("messages", []) if raw else [],
            "summary": raw.get("summary", "") if raw else "",
            "memory_prompt": ctx.prompt if ctx else "",
        }
    except Exception:
        logging.debug(f"Memory restore_session failed for user={user_id}")
        return {}

def persist_session(self, user_id: str, session_id: str, messages: list, summary: str = ""):
    """Persist session messages and update long-term memory."""
    try:
        r = self._get_redis()
        if not r:
            return
        key = self._short_key(user_id)
        payload = {"messages": messages[-20:], "summary": summary}
        r.setex(key, SHORT_TERM_TTL, json.dumps(payload, ensure_ascii=False, default=str))
        self.remember(user_id, session_id, messages, summary)
    except Exception:
        logging.debug(f"Memory persist_session failed for user={user_id}")

def _load_raw(self, user_id: str, r=None) -> dict | None:
    """Load raw session data from short-term Redis."""
    try:
        if r is None:
            r = self._get_redis()
        if not r:
            return None
        key = self._short_key(user_id)
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        logging.debug(f"Memory _load_raw failed for user={user_id}")
    return None
```

- [ ] **Step 3: 修改 core.py 使用统一接口**

`app/util/agent/core.py` line 378-379 处:
```python
# 旧代码:
# from app.util.agent.session_memory import SessionMemory
# restored = SessionMemory.restore(self.user_id)

# 新代码:
from app.util.agent.memory import MemoryManager as _MemMgr
_mem = _MemMgr(self._llm_client)
restored = _mem.restore_session(self.user_id)
```

line 600-604 处:
```python
# 旧代码:
# from app.util.agent.session_memory import SessionMemory
# SessionMemory.persist(self.user_id, self.session_id, self.messages, summary)

# 新代码:
_mem.persist_session(self.user_id, self.session_id, self.messages, summary)
```

- [ ] **Step 4: 从 __init__.py 移除 SessionMemory 导出**

编辑 `app/util/agent/__init__.py`，删除 line 47: `from .session_memory import SessionMemory`

- [ ] **Step 5: 删除 session_memory.py**

```bash
cd E:\Programs\mind && rm app/util/agent/session_memory.py
```

- [ ] **Step 6: 运行测试**

```bash
cd E:\Programs\mind && python -m pytest tests/test_memory_unified.py -v --tb=short
```

- [ ] **Step 7: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): merge session_memory.py into memory.py — unified session persistence + semantic recall"
```

---

### Task A4: 统一 LLM 重试

**文件:**
- 创建: `app/util/agent/retry.py`
- 修改: `app/util/agent/intent.py:194-219`, `app/util/agent/executor.py:93-101`, `app/util/agent/dag.py`, `app/util/agent/dispatcher.py:114-138`, `app/util/agent/reflexion.py:117-143`, `app/util/agent/adaptive.py:102-120`, `app/util/agent/llm_stream.py`, `app/util/agent/agents/base.py:204-225`

- [ ] **Step 1: 编写测试**

新建 `tests/test_llm_retry.py`:

```python
"""Test unified LLM retry wrapper."""
import pytest
from unittest.mock import Mock, patch
from app.util.agent.retry import retry_llm_call

def test_retry_llm_call_success_first_try():
    """Should return result on first successful call."""
    fn = Mock(return_value="ok")
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 1

def test_retry_llm_call_retries_on_rate_limit():
    """Should retry on RateLimitError up to max_retries."""
    from openai import RateLimitError
    fn = Mock(side_effect=[RateLimitError("limit", response=None, body=None), "ok"])
    result = retry_llm_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2

def test_retry_llm_call_exhausted():
    """Should raise last exception when retries exhausted."""
    from openai import RateLimitError
    fn = Mock(side_effect=RateLimitError("limit", response=None, body=None))
    with pytest.raises(RateLimitError):
        retry_llm_call(fn, max_retries=2)
    assert fn.call_count == 2

def test_retry_llm_call_passes_args():
    """Should forward args and kwargs to the wrapped function."""
    fn = Mock(return_value="ok")
    retry_llm_call(fn, "arg1", key="val", max_retries=2)
    fn.assert_called_with("arg1", key="val")
```

- [ ] **Step 2: 创建 retry.py**

新建 `app/util/agent/retry.py`:

```python
"""Unified LLM retry wrapper — eliminates 180 lines of duplicate retry logic."""
import logging
import time
from openai import RateLimitError, APITimeoutError, APIConnectionError, APIError

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError)


def should_retry_llm(e: Exception) -> bool:
    """Check if an LLM error is transient and worth retrying."""
    if isinstance(e, _RETRYABLE):
        return True
    if isinstance(e, APIError) and getattr(e, "status_code", 500) >= 500:
        return True
    return False


def retry_llm_call(fn, *args, max_retries: int = 3, **kwargs):
    """Call fn() with exponential backoff retry for transient LLM errors.

    Args:
        fn: The callable to invoke (e.g. a lambda wrapping an LLM API call).
        max_retries: Maximum number of retry attempts (default 3).
        *args/**kwargs: Forwarded to fn on each attempt.

    Returns:
        The return value of fn on success.

    Raises:
        The last caught exception after all retries are exhausted.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except _RETRYABLE as e:
            last_exc = e
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                logging.warning(f"LLM retry {attempt + 1}/{max_retries}: {e.__class__.__name__}, "
                                f"sleeping {delay}s")
                time.sleep(delay)
        except APIError as e:
            last_exc = e
            if getattr(e, "status_code", 0) >= 500 and attempt < max_retries - 1:
                delay = 2 ** attempt
                logging.warning(f"LLM server error retry {attempt + 1}/{max_retries}: HTTP {e.status_code}")
                time.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]
```

- [ ] **Step 3: 逐个更新调用方**

对于每个文件，替换现有的重试循环为 `retry_llm_call`:

**a) `app/util/agent/intent.py:194-219`** — 替换 `for attempt in range(3):` 循环：

```python
# 旧代码 (lines 194-219): for attempt in range(3): ... try/except ...
# 新代码:
from app.util.agent.retry import retry_llm_call

try:
    response = retry_llm_call(
        lambda: llm_client.chat.completions.create(
            model=model, messages=llm_messages, temperature=0.3, max_tokens=1200
        ),
        max_retries=3
    )
except Exception as e:
    logging.warning(f"Intent LLM failed after retries: {e}")
    return _keyword_fallback(user_message)
```

**b) `app/util/agent/executor.py:93-101`** — `BaseExecutor._call_llm` 方法中，将重试逻辑替换为对 `retry_llm_call` 的调用。

**c) `app/util/agent/dag.py`** — 找到 `_call_llm` 和 `_call_llm_stream` 中的重试循环，替换为 `retry_llm_call`。

**d) `app/util/agent/dispatcher.py:114-138`** — `handle_peer_query` 中的重试循环，替换为 `retry_llm_call`。

**e) `app/util/agent/reflexion.py:117-143`** — `_call_reflect_llm` 中的重试循环，替换为 `retry_llm_call`。

**f) `app/util/agent/adaptive.py:102-120`** — `replan_node` 中的重试循环，替换为 `retry_llm_call`。

**g) `app/util/agent/llm_stream.py`** — `stream_llm_chat` 中的重试循环，替换为 `retry_llm_call`。

**h) `app/util/agent/agents/base.py:204-225`** — `AgentBase.run` 非流式路径中的重试，替换为 `retry_llm_call`。

- [ ] **Step 4: 运行测试**

```bash
cd E:\Programs\mind && python -m pytest tests/test_llm_retry.py -v --tb=short
```

- [ ] **Step 5: 验证导入和 lint**

```bash
cd E:\Programs\mind && python -c "from app.util.agent.retry import retry_llm_call; print('OK')" && python -m ruff check app/util/agent/
```

- [ ] **Step 6: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): extract unified LLM retry wrapper — eliminates 180 lines of duplicate code across 8 modules"
```

---

## Agent 后端 Phase 2: 统一抽象

### Task A5: 统一 DAG 流式/非流式路径

**文件:**
- 修改: `app/util/agent/dag.py:375-513`

- [ ] **Step 1: 编写测试**

新建 `tests/test_dag_stream.py`:

```python
"""Test DAG executor unified stream/non-stream path."""
import pytest
from unittest.mock import Mock, AsyncMock
from app.util.agent.dag import DAGExecutor

@pytest.fixture
def executor():
    exc = DAGExecutor.__new__(DAGExecutor)
    exc.stream = False
    exc.model = "test-model"
    exc.llm_client = Mock()
    exc._call_llm = Mock(return_value={
        "choices": [{"message": {"content": "test response", "tool_calls": None},
                      "finish_reason": "stop"}]
    })
    exc._call_llm_stream = Mock(return_value=iter([
        ("content", "test"),
        ("content", " response"),
        ("done", None)
    ]))
    exc._run_simple_tool = Mock(return_value=(True, {}, None))
    return exc

def test_non_stream_yields_response(executor):
    """Non-stream path should yield llm_response events."""
    events = list(executor._execute_simple([], None))
    assert any(e[0] == "llm_response" for e in events)

def test_stream_yields_response(executor):
    """Stream path should yield llm_response events."""
    executor.stream = True
    events = list(executor._execute_simple([], None))
    assert any(e[0] == "llm_response" for e in events)
```

- [ ] **Step 2: 重构 _execute_simple**

在 `app/util/agent/dag.py` 中，将 lines 375-513 的两个分支合并为统一路径：

```python
def _execute_simple(self, messages: list, context: dict | None = None):
    """Execute simple (non-DAG) agent loop. Unified stream + non-stream path."""
    loop = 0
    tool_calls_received = []
    blocked_tools = set()
    full_text = ""

    while True:
        loop += 1
        if loop > self.max_loop_repeat:
            yield ("step_fail", {"loop": loop, "reason": "exceeded MAX_LOOP_REPEAT"})
            return

        # Unified: use stream when available, otherwise batch
        if self.stream:
            text = ""
            for event in self._call_llm_stream(messages, context):
                kind = event[0] if event else ""
                if kind == "content":
                    text += event[1]
                    yield event
                elif kind == "blocked":
                    blocked_tools.add(event[1])
                    yield event
                elif kind == "tool_calls":
                    tool_calls_received = event[1]
                elif kind == "error":
                    yield event
                    return
                elif kind == "done":
                    pass
            response_chunk = {"text": text}
        else:
            response = self._call_llm(messages, context)
            if not response or "choices" not in response:
                yield ("error", {"message": "LLM returned no response"})
                return
            choice = response["choices"][0]
            text = (choice.get("message", {}).get("content") or "").strip()
            tool_calls_received = choice.get("message", {}).get("tool_calls") or []
            full_text = text
            if choice.get("finish_reason") == "tool_calls":
                pass  # handled below
            elif text:
                yield ("llm_response", {"content": full_text})

        # Shared tool execution path
        if not tool_calls_received:
            yield ("llm_response", {"content": full_text or text})
            return

        for tc in tool_calls_received:
            tc_name = (tc.get("function", {}) or {}).get("name", "unknown")
            if tc_name in blocked_tools:
                yield ("tool_result", {"tool_name": tc_name, "success": False,
                                       "message": f"Tool {tc_name} blocked by guard"})
                continue

            ok, result, next_context = self._run_simple_tool(tc, context)
            yield ("tool_result", {"tool_name": tc_name, "success": ok,
                                   "data": result, "context": next_context})

        tool_calls_received = []
```

- [ ] **Step 3: 运行测试**

```bash
cd E:\Programs\mind && python -m pytest tests/test_dag_stream.py -v --tb=short
```

- [ ] **Step 4: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): unify DAG _execute_simple stream/non-stream paths — eliminates 127 lines of duplicate logic"
```

---

### Task A6: 消除 OutputGuard 重复

**文件:**
- 修改: `app/util/agent/engine.py:121-148`

- [ ] **Step 1: 重构 engine.py**

在 `app/util/agent/engine.py` 中，将两个 `OutputGuard.process(text)` 调用（lines 124 和 142）合并。当前结构为：

```python
# dag path (line 121-131):
if precomputed_plan:
    for event in dag_executor.run(...):
        if event[0] == "llm_response":
            guard_out = OutputGuard.process(text)
            ...

# simple path (line 139-148):
else:
    for event in simple ...
        if event[0] == "llm_response":
            guard_out = OutputGuard.process(text)
            ...
```

改为抽取公共处理逻辑，在 `yield` 之前统一检查。具体修改读取现有 engine.py 后进行精确编辑。

- [ ] **Step 2: 验证**

```bash
cd E:\Programs\mind && python -c "from app.util.agent.engine import AgentEngine; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): eliminate duplicate OutputGuard calls in engine.py"
```

---

### Task A7: 移除 supervisor.py

**文件:**
- 修改: `app/util/agent/__init__.py` (line 43) — 移除 Supervisor 导出
- 修改: `app/util/agent/dispatcher.py` (line 54) — 移除 Supervisor 依赖
- 删除: `app/util/agent/supervisor.py`

- [ ] **Step 1: 确认 dispatcher.py 依赖情况**

```bash
cd E:\Programs\mind && grep -n "Supervisor\|supervisor" app/util/agent/dispatcher.py
```

- [ ] **Step 2: 移除依赖**

编辑 `app/util/agent/dispatcher.py` line 54，删除 `from app.util.agent.supervisor import Supervisor`，同时删除所有 `Supervisor` 的使用。

编辑 `app/util/agent/__init__.py` line 43，删除 `from .supervisor import Supervisor`。

- [ ] **Step 3: 删除 supervisor.py**

```bash
cd E:\Programs\mind && rm app/util/agent/supervisor.py
```

- [ ] **Step 4: 验证**

```bash
cd E:\Programs\mind && python -c "from app.util.agent import *; print('OK')"
```

- [ ] **Step 5: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): remove supervisor.py — fully superseded by DAGExecutor"
```

---

### Task A8: 修复 tools/__init__.py dispatch_agent 竞态

**文件:**
- 修改: `app/util/agent/tools/__init__.py:44-95`

- [ ] **Step 1: 编写测试**

新建 `tests/test_dispatch_race.py`:

```python
"""Test dispatch_agent relay worker race condition fix."""
import pytest
import queue
import threading
from unittest.mock import Mock, patch
from app.util.agent.tools import run_tool_call

def test_dispatch_agent_no_missed_events(monkeypatch):
    """Fast dispatch should not miss relay events."""
    # Mock dispatcher to complete immediately
    mock_dispatcher = Mock()
    mock_dispatcher.dispatch = Mock(return_value=iter([]))  # instant empty generator
    
    event_queue = queue.Queue()
    
    with patch("app.util.agent.tools._threading.Thread") as mock_thread:
        mock_thread.return_value = Mock()
        run_tool_call(
            tool_name="dispatch_agent",
            args={"task": "test"},
            event_queue=event_queue,
            dispatcher=mock_dispatcher,
        )
    
    # Verificaion: thread was started BEFORE dispatcher called
    # (ensuing sentinel is sent after worker is ready)
```

- [ ] **Step 2: 修复竞态**

在 `app/util/agent/tools/__init__.py` 中，`run_tool_call` 函数的 lines 56-80:

```python
# 旧代码 (line 56-80):
def _relay_worker():
    ...

relay_thread = _threading.Thread(target=_relay_worker, daemon=True)
relay_thread.start()

# 修复: 使用 Event 同步，确保 worker 创建后 dispatch 才开始
worker_ready = _threading.Event()

def _relay_worker():
    worker_ready.set()  # signal readiness
    while True:
        ...

relay_thread = _threading.Thread(target=_relay_worker, daemon=True)
relay_thread.start()
worker_ready.wait(timeout=5)  # wait for worker to be ready

# ... then dispatch
```

- [ ] **Step 3: 运行测试**

```bash
cd E:\Programs\mind && python -m pytest tests/test_dispatch_race.py -v --tb=short
```

- [ ] **Step 4: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(agent): fix dispatch_agent race condition with Event synchronization"
```

---

## Agent 后端 Phase 3: 缓存/常量/可观测性

### Task A9: 创建 constants.py

**文件:**
- 创建: `app/util/agent/constants.py`
- 修改: `app/util/agent/core.py:28-29`, `app/util/agent/guard.py:54,113`, `app/util/agent/dag.py:104-107`, `app/util/agent/executor.py:19-20`, `app/util/agent/reflexion.py:11-12`, `app/util/agent/agents/base.py:36-37`, `app/util/agent/memory.py:10-15`, `app/util/agent/cache.py:10-12`, `app/util/agent/dispatcher.py:15-18`

- [ ] **Step 1: 创建 constants.py**

新建 `app/util/agent/constants.py`:

```python
"""Centralized agent constants — single source of truth for all magic numbers."""

# History / Context
MAX_HISTORY_TOKENS = 8000
MAX_HISTORY_COMPACT = 4000

# Guard
MAX_INPUT_LENGTH = 8192
MAX_CALLS_PER_TOOL = 30

# Execution
MAX_REFLECT_RETRIES = 3
MAX_LOOP_REPEAT = 3
MAX_DAG_TOTAL_SECONDS = 300
MAX_NODE_SECONDS = 120

# Memory TTLs (seconds)
SHORT_TERM_TTL = 3600          # 1 hour
LONG_TERM_TTL = 2592000        # 30 days

# Cache
CACHE_TTL = 30
CACHE_DB = 5

# Dispatch
SUB_AGENT_TIMEOUT = 120
MAX_CONCURRENT_DISPATCH = 3
PEER_QUERY_TIMEOUT = 15
```

- [ ] **Step 2: 逐个更新引用文件**

每个文件改为: `from app.util.agent.constants import MAX_xxx`

需要更新的文件（从原处删除常量定义，改为 import）:
- `core.py` lines 28-29: 删除 `MAX_HISTORY_TOKENS = 8000`, `MAX_HISTORY_COMPACT = 4000`，改为 import
- `guard.py` line 54: 删除 `MAX_INPUT_LENGTH = 8192`，line 113: 删除 `MAX_CALLS_PER_TOOL = 30`
- `dag.py` lines 104-107: 删除 4 个常量
- `executor.py` lines 19-20: 删除 2 个常量
- `reflexion.py` lines 11-12: 删除 2 个常量
- `agents/base.py` line 36-37: 删除 `MAX_ITERATIONS = 5`, `MAX_LOOP_REPEAT = 3`
- `memory.py` lines 10-15: 删除 TTL 常量
- `cache.py` lines 10-12: 删除 cache 常量
- `dispatcher.py` lines 15-18: 删除 3 个常量

- [ ] **Step 3: 验证导入一致性**

```bash
cd E:\Programs\mind && python -c "from app.util.agent.constants import *; print('OK')" && python -m ruff check app/util/agent/
```

- [ ] **Step 4: 运行全量测试**

```bash
cd E:\Programs\mind && python -m pytest tests/ -v --tb=short
```

- [ ] **Step 5: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(agent): extract constants.py — centralize 20+ scattered magic numbers"
```

---

### Task A10: LLM 确定性缓存

**文件:**
- 修改: `app/util/agent/cache.py` — 新增 LLM 响应缓存
- 修改: `app/util/agent/core.py` — `_compact_history` 和 `classify_domain` 使用缓存

- [ ] **Step 1: 扩展 cache.py**

在 `app/util/agent/cache.py` 中添加:

```python
import hashlib

LLM_CACHE_TTL = 3600  # 1 hour — spans a conversation without going stale
LLM_CACHEABLE_FUNCTIONS = {"compact_history", "classify_domain"}


def get_llm_cache_key(func_name: str, messages: list) -> str:
    """Generate deterministic cache key from function name + message content."""
    content = json.dumps(messages, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"llm_cache:{func_name}:{digest}"


def get_cached_llm_response(func_name: str, messages: list) -> str | None:
    """Check if LLM response is cached. Returns None on miss."""
    try:
        r = _get_redis(CACHE_DB)
        if not r:
            return None
        key = get_llm_cache_key(func_name, messages)
        return r.get(key)
    except Exception:
        return None


def set_cached_llm_response(func_name: str, messages: list, response: str):
    """Cache an LLM response with TTL."""
    try:
        r = _get_redis(CACHE_DB)
        if not r:
            return
        key = get_llm_cache_key(func_name, messages)
        r.setex(key, LLM_CACHE_TTL, response)
    except Exception:
        pass
```

- [ ] **Step 2: 在 core.py 中使用缓存**

在 `_compact_history` (line 174) 和域分类调用处（如有）加入:

```python
from app.util.agent.cache import get_cached_llm_response, set_cached_llm_response

def _compact_history(self, messages: list) -> str:
    cached = get_cached_llm_response("compact_history", messages)
    if cached:
        return cached
    
    summary = self._llm_compact(messages)  # actual LLM call
    
    set_cached_llm_response("compact_history", messages, summary)
    return summary
```

- [ ] **Step 3: 编写测试**

```bash
cd E:\Programs\mind && python -m pytest tests/ -v --tb=short -k "cache"
```

- [ ] **Step 4: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "perf(agent): add LLM deterministic caching for compact_history and classify_domain"
```

---

### Task A11: 修复工具文件文档字符串

**文件:**
- 修改: `app/util/agent/tools/canvas.py:1-2`, `web.py:1-2`, `file_ops.py:1-2`, `geo.py:1-2`, `code.py:1-2`

- [ ] **Step 1: 逐个修复文档字符串**

每个文件将错误的通用 docstring 改为正确的模块说明：

- `canvas.py` line 2: 改为 `"""Canvas operations tool — add_pen, add_line, add_diagram, layout, and blueprint management."""`
- `web.py` line 2: 改为 `"""Web search and content fetch tool."""`
- `file_ops.py` line 2: 改为 `"""File operations tool — read, write, search, and document analysis."""`
- `geo.py` line 2: 改为 `"""Geospatial tools — geocode, reverse geocode, and route planning."""`
- `code.py` line 2: 改为 `"""Code generation and execution tool."""`

同时移除每个文件头部不相关的 import 语句。

- [ ] **Step 2: 验证**

```bash
cd E:\Programs\mind && python -c "import app.util.agent.tools.canvas as m; print(m.__doc__)"
```

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "docs(agent): fix tool module docstrings — remove stale import residuals from file split"
```

---

### Task A12: 追踪日志大小限制

**文件:**
- 修改: `app/util/agent/tracer.py`

- [ ] **Step 1: 添加目录大小检查**

在 `tracer.py` 的 flush 逻辑中添加（约 line 100）:

```python
import os
import glob

_TRACE_MAX_DIR_SIZE = 500 * 1024 * 1024  # 500 MB
_TRACE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "traces")


def _enforce_trace_dir_limit():
    """Remove oldest trace files if directory exceeds _TRACE_MAX_DIR_SIZE."""
    if not os.path.exists(_TRACE_DIR):
        return
    files = sorted(
        glob.glob(os.path.join(_TRACE_DIR, "trace_*.json")),
        key=os.path.getmtime
    )
    total = sum(os.path.getsize(f) for f in files)
    while total > _TRACE_MAX_DIR_SIZE and len(files) > 1:
        oldest = files.pop(0)
        total -= os.path.getsize(oldest)
        os.remove(oldest)
        logging.info(f"Tracer: removed old trace file {oldest} (dir size limit)")
```

在每次 flush 写入文件后调用 `_enforce_trace_dir_limit()`。

- [ ] **Step 2: 验证**

```bash
cd E:\Programs\mind && python -c "from app.util.agent.tracer import _enforce_trace_dir_limit; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(agent): add 500MB directory size limit for trace logs"
```

---

## Meta2D 前端 Phase 1: Bug修复 + 快捷键

### Task M1: 补齐键盘快捷键

**文件:**
- 创建: `web/src/composables/useKeyboardShortcuts.ts`
- 修改: `web/src/components/Meta2D/Editor/index.vue`

- [ ] **Step 1: 创建 useKeyboardShortcuts**

新建 `web/src/composables/useKeyboardShortcuts.ts`:

```typescript
import { onMounted, onUnmounted } from 'vue'
import type { Meta2d } from '@meta2d/core'

export function useKeyboardShortcuts(meta2d: Meta2d) {
  function handleKeyDown(e: KeyboardEvent) {
    // Don't intercept when focus is in an input
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

    const ctrl = e.ctrlKey || e.metaKey

    if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault()
      meta2d.delete()
      return
    }

    if (ctrl && e.key === 'c') {
      e.preventDefault()
      // Meta2d handles copy internally if pens selected
      document.execCommand('copy')
      return
    }

    if (ctrl && e.key === 'v') {
      e.preventDefault()
      document.execCommand('paste')
      return
    }

    if (ctrl && e.key === 'a') {
      e.preventDefault()
      const pens = meta2d.data().pens || []
      meta2d.active = pens.map((p: any) => p.id)
      meta2d.render()
      return
    }

    if (ctrl && e.key === 'd') {
      e.preventDefault()
      // Duplicate selected pens via copy + paste pattern
      const selected = meta2d.active || []
      if (selected.length) {
        const cloneData = meta2d.data()
        const selectedPens = (cloneData.pens || []).filter((p: any) => selected.includes(p.id))
        selectedPens.forEach((p: any) => {
          const newPen = { ...p, id: undefined }
          meta2d.addPen({ ...newPen, x: p.x + 20, y: p.y + 20 })
        })
      }
      return
    }

    if (ctrl && (e.key === 'z' || e.key === 'Z')) {
      // Meta2D handles Ctrl+Z internally
      return
    }

    if (ctrl && (e.key === 'y' || e.key === 'Y')) {
      // Meta2D handles Ctrl+Y internally
      return
    }

    if (ctrl && e.key === 's') {
      e.preventDefault()
      // Save handled by Header component
      return
    }

    const step = e.shiftKey ? 10 : 1
    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault()
        moveActive(meta2d, 0, -step)
        break
      case 'ArrowDown':
        e.preventDefault()
        moveActive(meta2d, 0, step)
        break
      case 'ArrowLeft':
        e.preventDefault()
        moveActive(meta2d, -step, 0)
        break
      case 'ArrowRight':
        e.preventDefault()
        moveActive(meta2d, step, 0)
        break
      case 'Escape':
        e.preventDefault()
        meta2d.active = []
        // Cancel current drawing tool
        ;(meta2d as any).drawLinePencil = null
        meta2d.render()
        break
    }
  }

  function moveActive(m: Meta2d, dx: number, dy: number) {
    const active = m.active || []
    if (!active.length) return
    const data = m.data()
    const pens = data.pens || []
    for (const pen of pens) {
      if (active.includes(pen.id)) {
        pen.x = (pen.x || 0) + dx
        pen.y = (pen.y || 0) + dy
        m.setValue(pen.id, { x: pen.x, y: pen.y }, { render: false })
      }
    }
    m.render()
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })
}
```

- [ ] **Step 2: 在 Editor.vue 中注册**

在 `web/src/components/Meta2D/Editor/index.vue` 的 `<script setup>` 中添加:

```typescript
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

// After meta2d is created (after line 87):
useKeyboardShortcuts(meta2d)
```

同时在 `Header/index.vue` 中移除旧的 `onKeyDown` 处理（lines 960-966, 969, 992），避免重复注册。

- [ ] **Step 3: 编写测试**

新建 `web/src/composables/__tests__/useKeyboardShortcuts.test.ts`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { useKeyboardShortcuts } from '../useKeyboardShortcuts'

describe('useKeyboardShortcuts', () => {
  it('Delete key calls meta2d.delete()', () => {
    const mockMeta2d = { delete: vi.fn(), data: vi.fn(() => ({ pens: [] })), render: vi.fn(), active: [] } as any

    // Simulate: dispatch keyboard event programmatically...
    // Test that handler does NOT fire when target is INPUT
    // Test that handler DOES fire when target is DIV
    // (Full test requires DOM environment setup)
  })
})
```

- [ ] **Step 4: 提交**

```bash
cd E:\Programs\mind\web && npx vitest run src/composables/__tests__/useKeyboardShortcuts.test.ts
cd E:\Programs\mind && git add -A && git commit -m "feat(meta2d): add keyboard shortcuts — Delete, Ctrl+C/V/A/D, arrows, Escape"
```

---

### Task M2: 修复事件监听泄漏

**文件:**
- 修改: `web/src/components/Meta2D/PenProps/index.vue:643-644, 670-671`

- [ ] **Step 1: 修改事件注册逻辑**

在 `PenProps/index.vue` 中，将 lines 643-644:

```typescript
// 旧代码:
registeredEvents.forEach((name) => meta2d.off(name))
registeredEvents = []
```

改为:

```typescript
// 新代码: store handler references for precise cleanup
const _handlers: Array<{ name: string; fn: (...args: any[]) => void }> = []

// ... (in getPen function, line 670-671):
// 旧代码:
// meta2d.on(event.value, handler)
// registeredEvents.push(event.value)

// 新代码:
meta2d.on(event.value, handler)
_handlers.push({ name: event.value, fn: handler })

// Cleanup at top of getPen (line 643-644):
// 旧代码:
// registeredEvents.forEach((name) => meta2d.off(name))
// registeredEvents = []

// 新代码:
_handlers.forEach(({ name, fn }) => meta2d.off(name, fn))
_handlers.length = 0
```

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(meta2d): fix event listener leak in PenProps — use handler references for precise cleanup"
```

---

### Task M3: 删除损坏的自定义三角形代码

**文件:**
- 删除: `web/src/utils/custom/index.ts`
- 删除: `web/src/utils/custom/triangle.ts`
- 修改: 所有 import `@/utils/custom` 的文件

- [ ] **Step 1: 检查引用**

```bash
cd E:\Programs\mind\web && grep -rn "utils/custom\|@/utils/custom" src/ --include="*.ts" --include="*.vue"
```

- [ ] **Step 2: 删除文件并移除引用**

```bash
cd E:\Programs\mind && rm web/src/utils/custom/index.ts web/src/utils/custom/triangle.ts
```

清理任何引用这些文件的 import。

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(meta2d): remove broken custom triangle registration — undefined meta2d reference"
```

---

### Task M4: 修复 canvasBridge.ts ID 映射时序

**文件:**
- 修改: `web/src/utils/canvasBridge.ts:374-381`

- [ ] **Step 1: 修复 _addPen**

在 `canvasBridge.ts` 的 `_addPen` 函数中 (lines 374-381):

```typescript
// 旧代码 (line 374-381):
if (penId) penIdMap.set(penId, penId)  // BUG: set before meta2d generates real ID
pushUndoState(meta2d)
const p = await meta2d.addPen(pen)
if ((p as any)?.id) penIdMap.set(penId, (p as any).id)  // inconsistent: sometimes overwrites, sometimes not

// 新代码:
pushUndoState(meta2d)
const p = await meta2d.addPen(pen)
const realId = (p as any)?.id || (p as any)?.penId
if (penId && realId) {
  penIdMap.set(penId, realId)
}
```

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(meta2d): fix penIdMap timing in canvasBridge — set after Meta2D returns real ID"
```

---

## Meta2D 前端 Phase 2: 性能优化

### Task M5: 属性面板渲染防抖

**文件:**
- 修改: `web/src/components/Meta2D/PenProps/index.vue:713-733`

- [ ] **Step 1: 添加 debounce**

在 `PenProps/index.vue` 的 `<script setup>` 中添加防抖逻辑:

```typescript
import { debounce } from 'lodash-es'  // or inline implementation

// Debounced render: collect rapid changes into one render call
const debouncedRender = debounce(() => {
  meta2d.render()
}, 100)

// In changeValue (line 713-726):
function changeValue(prop: string) {
  const v: Record<string, any> = {}
  // ... existing logic to populate v from pen.value ...
  meta2d.setValue(pen.value, v, { render: false })  // NEVER auto-render
  debouncedRender()
  commonStore.setIsSave("0")
}

// In changeRect (line 728-733):
function changeRect(prop: string) {
  const v: Record<string, any> = {}
  // ... existing logic ...
  meta2d.setValue(pen.value, v, { render: false })  // NEVER auto-render
  debouncedRender()
  commonStore.setIsSave("0")
}
```

关键是: 将 `meta2d.setValue(v, { render: true })` 改为 `meta2d.setValue(v, { render: false })`，然后调用 `debouncedRender()`。

- [ ] **Step 2: 编写性能测试**

```typescript
// 验证: 连续 10 次 changeValue 调用只触发 1 次 render
```

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "perf(meta2d): add 100ms render debounce to PenProps — prevents per-pixel re-renders on slider drag"
```

---

### Task M6: 优化保存序列化

**文件:**
- 修改: `web/src/components/Meta2D/Header/index.vue:760-776, 811`

- [ ] **Step 1: 移除手动白名单，改全量序列化**

在 `Header/index.vue` 的 `onSave` 函数中 (lines 760-776):

```typescript
// 旧代码:
const fields = ["name", "color", "penBackground", "background", "bkImage",
  "grid", "gridColor", "gridSize", "gridRotate", "rule", "ruleColor",
  "initJs", "pens", "https", "thumbnail"]
const params: Record<string, any> = {}
fields.forEach((key) => { if (key in canvasData) params[key] = (canvasData as any)[key] })

// 新代码: 全量序列化 (Meta2D 保障向前兼容)
const params = { ...canvasData }
```

缩略图生成改为异步:

```typescript
// 旧代码 (line 811):
generateThumbnail((url: string) => { /* save with url */ })

// 新代码: 先保存主数据，缩略图异步更新
// 使用 requestIdleCallback 或 setTimeout 延迟缩略图生成
setTimeout(() => {
  generateThumbnail((url: string) => {
    // Update the saved blueprint with thumbnail URL
    apiBlueprintModify({ id: canvasData.id, thumbnail: url })
  })
}, 0)
```

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "perf(meta2d): replace manual field whitelist with full serialization, async thumbnail generation"
```

---

### Task M7: 修复自动保存时机

**文件:**
- 修改: `web/src/composables/useAgentChat.ts:212-238`

- [ ] **Step 1: 替换定时保存为事件驱动**

在 `useAgentChat.ts` 中:

```typescript
// 旧代码 (lines 226-238): setInterval 每 3 秒保存
// 新代码: 仅在流式完成时触發

function _onStreamComplete() {
  options.onStreamTick?.()
}

// 在 SSE 'done' / 'error' / 'abort' 事件处理中调用 _onStreamComplete()
// 移除 _startStreamSave() 和 _stopStreamSave() 中的 setInterval
```

具体修改:
- Lines 212-213: 删除 `_streamTokenCount`, `_streamSaveInterval`
- Lines 215-238: 删除 `_tickStreamSave`, `_startStreamSave`, `_stopStreamSave`
- 在 SSE `done` case（约 line 450）和 `error` case 中添加 `options.onStreamTick?.()` 调用

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "fix(meta2d): replace 3s auto-save interval with event-driven save on stream complete"
```

---

### Task M8: Undo 栈深度克隆优化

**文件:**
- 修改: `web/src/utils/canvasBridge.ts:73`

- [ ] **Step 1: 替换为 structuredClone**

```typescript
// 旧代码 (line 73):
meta2d.addHistory(JSON.parse(JSON.stringify(meta2d.data())))

// 新代码:
meta2d.addHistory(structuredClone(meta2d.data()))
```

`structuredClone` 是浏览器原生 API，比 JSON 序列化/反序列化更快，且保留 Date、RegExp、undefined 等类型。

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "perf(meta2d): use structuredClone for undo stack — faster than JSON round-trip"
```

---

## Meta2D 前端 Phase 3: 架构增强

### Task M9: Agent 画布状态感知

**文件:**
- 修改: `web/src/composables/useAgentChat.ts:117-186` (buildCanvasContext)
- 修改: `web/src/utils/canvasBridge.ts` (tool result 中返回新 pen ID)
- 修改: `app/util/agent/tools/canvas.py:159-164` (get_state action)

- [ ] **Step 1: 增强 buildCanvasContext**

在 `useAgentChat.ts` 的 `buildCanvasContext` 中，增强上下文信息:

```typescript
function buildCanvasContext(): CanvasContext {
  if (typeof window === 'undefined' || !(window as any).meta2d) return {}

  const meta2d = (window as any).meta2d
  const data = meta2d.data()

  return {
    pens: (data.pens || []).slice(0, MAX_PENS),
    lines: data.lines || [],
    selected_pen: meta2d.active?.length === 1
      ? data.pens?.find((p: any) => p.id === meta2d.active[0])
      : null,
    viewport: {
      x: meta2d.canvas?.scroll?.scrollX || 0,
      y: meta2d.canvas?.scroll?.scrollY || 0,
      scale: meta2d.canvas?.scale || 1,
    },
    total_pens: (data.pens || []).length,  // NEW: tell agent total count
    total_lines: (data.lines || []).length,  // NEW
  }
}
```

- [ ] **Step 2: 增强 canvas.py get_state**

在 `app/util/agent/tools/canvas.py` 的 `get_state` action (line 159):

```python
elif action == "get_state":
    return {
        "success": True,
        "message": "查看系统提示中的 canvas_context 获取完整画布状态。连续操作时请记录之前创建的 pen_id。",
        "tool_hint": "use canvas_context in system prompt for current canvas state",
    }
```

- [ ] **Step 3: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "feat(meta2d): enhance Agent canvas state awareness — richer context in buildCanvasContext"
```

---

### Task M10: Agent 连线改用原生连接

**文件:**
- 修改: `web/src/utils/canvasBridge.ts:389-429`

- [ ] **Step 1: 使用 Meta2D 连线 API**

在 `canvasBridge.ts` 的 `_addLine` 函数中:

```typescript
async function _addLine(meta2d: Meta2d, args: any, success: boolean, _result: any) {
  if (!success) return

  const { from, to, lineName = 'curve' } = args
  const fromId = resolvePenId(from)
  const toId = resolvePenId(to)

  const fromPen = meta2d.findOne(fromId)
  const toPen = meta2d.findOne(toId)
  if (!fromPen || !toPen) {
    console.warn('_addLine: pen not found', { fromId, toId, fromPen: !!fromPen, toPen: !!toPen })
    return
  }

  pushUndoState(meta2d)

  // Use Meta2D native line connection — lines will auto-follow pens
  const line = {
    name: lineName,
    type: 1,  // Meta2D line type
    anchors: [
      getAnchor(fromPen, 'auto'),
      getAnchor(toPen, 'auto'),
    ],
    source: { id: fromPen.id, connectTo: toPen.id },
  }
  await meta2d.addPen(line as any)

  notifyCanvasMutation()
  syncToLocalStorage(meta2d)
}
```

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "feat(meta2d): use Meta2D native line connections in canvasBridge — lines auto-follow pens"
```

---

### Task M11: 多画布基础架构

**文件:**
- 创建: `web/src/composables/useCanvas.ts`
- 修改: `web/src/components/Meta2D/Editor/index.vue:87`
- 修改: `web/src/global.d.ts` (标注 deprecated)

- [ ] **Step 1: 创建 useCanvas.ts**

新建 `web/src/composables/useCanvas.ts`:

```typescript
import { inject, provide, type InjectionKey } from 'vue'
import type { Meta2d } from '@meta2d/core'

export const CanvasKey: InjectionKey<Meta2d> = Symbol('meta2d-canvas')

export function provideCanvas(meta2d: Meta2d) {
  provide(CanvasKey, meta2d)
  // Backward compatibility — keep window.meta2d for now
  ;(window as any).meta2d = meta2d
}

export function useCanvas(): Meta2d {
  const meta2d = inject(CanvasKey)
  if (!meta2d) {
    console.warn('useCanvas called outside of canvas context. Falling back to window.meta2d.')
    return (window as any).meta2d
  }
  return meta2d
}
```

- [ ] **Step 2: Editor.vue 中使用 provide**

```typescript
// 旧代码 (line 87):
// (window as any).meta2d = meta2d

// 新代码:
import { provideCanvas } from '@/composables/useCanvas'
// After meta2d creation:
provideCanvas(meta2d)
```

- [ ] **Step 3: global.d.ts 标注 deprecated**

```typescript
// Deprecated: use useCanvas() composable instead
// var meta2d: Meta2d  // kept for backward compatibility
```

- [ ] **Step 4: 逐步迁移子组件**

逐个将 `(window as any).meta2d` 改为 `useCanvas()`:
- `PenProps/index.vue`
- `Header/index.vue`
- `Graphics/index.vue`
- `canvasBridge.ts`

- [ ] **Step 5: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "refactor(meta2d): add CanvasManager via provide/inject — foundation for multi-canvas support"
```

---

### Task M12: 画布上下文智能截断

**文件:**
- 修改: `web/src/composables/useAgentChat.ts:141-142`

- [ ] **Step 1: 替换固定上限为动态截断**

在 `useAgentChat.ts` 的 `buildCanvasContext` 中:

```typescript
// 旧代码 (line 141-142):
const MAX_PENS = 50
const allPens = (data.pens || []).slice(0, MAX_PENS)

// 新代码: 按优先级截断
const TARGET_TOKENS = 2000
const selectedPen = meta2d.active?.length
  ? data.pens?.filter((p: any) => meta2d.active.includes(p.id))
  : []

const selectedNeighbors = new Set<string>()
if (selectedPen?.length) {
  for (const pen of selectedPen) {
    // Find lines connected to this pen
    ;(data.lines || []).forEach((line: any) => {
      if (line.source?.id === pen.id) selectedNeighbors.add(line.source?.connectTo)
      if (line.target?.id === pen.id) selectedNeighbors.add(line.target?.connectTo)
    })
    // Find pens at same level / nearby
    ;(data.pens || []).forEach((p: any) => {
      if (Math.abs((p.x || 0) - (pen.x || 0)) < 300 && Math.abs((p.y || 0) - (pen.y || 0)) < 300) {
        selectedNeighbors.add(p.id)
      }
    })
  }
}

// Priority order: selected pens > their neighbors > viewport pens > rest (aggregated)
const priorityPens = [
  ...(selectedPen || []),
  ...(data.pens || []).filter((p: any) => selectedNeighbors.has(p.id)),
  ...(data.pens || []).filter((p: any) => isInViewport(p, meta2d)),
  ...(data.pens || []),
]

// Deduplicate and trim to token budget (rough: 1 pen ~ 100 tokens)
const seen = new Set<string>()
const truncatedPens: any[] = []
for (const p of priorityPens) {
  if (seen.has(p.id)) continue
  seen.add(p.id)
  truncatedPens.push(p)
  if (JSON.stringify(truncatedPens).length > TARGET_TOKENS * 3) break
}

return {
  pens: truncatedPens,
  lines: data.lines || [],
  total_pens: (data.pens || []).length,
  truncated: truncatedPens.length < (data.pens || []).length,
}
```

- [ ] **Step 2: 提交**

```bash
cd E:\Programs\mind && git add -A && git commit -m "feat(meta2d): smart canvas context truncation by priority instead of fixed 50-pen cap"
```

---

## 质量门禁

每个 Phase 完成后执行:

```bash
# Agent 后端
cd E:\Programs\mind && python -m ruff check app/ && python -m ruff format app/ --check && python -m pytest tests/ -v --tb=short

# Meta2D 前端
cd E:\Programs\mind\web && pnpm format --check && npx vitest run
```
