# Agent 架构 + Meta2D 编辑器全量优化 — 设计文档

**日期**: 2026-06-22  
**范围**: Agent 后端架构优化 + Meta2D 前端编辑器交互优化  
**策略**: 并行双线推进，每 Phase 结束跑自动化测试门禁（pytest + vitest）

---

## 一、Agent 后端优化

### Phase 1：去重 / 去死代码

#### 1.1 移除 `router.py`

- **原因**: `router.py` 的意图路由已被 `intent.py` 的 `unified_intent_and_plan()` 完全取代。主代码路径（`core.py` → `engine.py`）不使用 `router.py`。
- **操作**:
  - 删除 `app/util/agent/router.py`
  - `__init__.py` 移除 `AgentRouter` 导出
  - `plan_eval.py` 中对 `route_intent` 的引用改为调用 `unified_intent_and_plan`
- **测试**: 确认意图分类正确、`plan_eval` 反馈循环不中断

#### 1.2 移除 `planner.py`

- **原因**: `planner.py` 的独立规划逻辑已嵌入 `intent.py` 的 `unified_intent_and_plan()`。`core.py` 和 `engine.py` 均不引用。
- **操作**:
  - 删除 `app/util/agent/planner.py`
  - `__init__.py` 移除 `AgentPlanner` 导出
- **测试**: 确认 DAG 规划输出不受影响

#### 1.3 合并 `session_memory.py` → `memory.py`

- **原因**: `SessionMemory` 和 `MemoryManager` 操作同一 Redis DB，做重叠的事情（消息持久化 + 语义召回）。`core.py` 在 `chat_v3()` 中两个都调，造成两次 Redis 查询。
- **操作**:
  - 将 `SessionMemory` 的 LRU 内存存储 + 原始消息持久化逻辑并入 `MemoryManager`
  - `MemoryManager` 新增 `restore_session()` 和 `persist_session()` 方法
  - `core.py` 改为只调 `MemoryManager` 统一接口
  - 删除 `session_memory.py`
- **测试**: 会话恢复、消息持久化、LRU 淘汰

#### 1.4 统一 LLM 重试

- **原因**: LLM 重试逻辑在 8 个模块中复制粘贴（~180行重复代码），模式完全相同：捕获 `RateLimitError/APITimeoutError/APIConnectionError/APIError` → 指数退避 → 最多 3 次重试。
- **操作**:
  - 新建 `app/util/agent/retry.py`
  - 提供 `retry_llm_call(fn, *args, max_retries=3, **kwargs)` 封装
  - 修改 8 个调用方: `intent.py`, `executor.py`, `dag.py`, `dispatcher.py`, `reflexion.py`, `adaptive.py`, `llm_stream.py`, `agents/base.py`
- **测试**: Mock LLM 故障验证重试次数、退避间隔、最终抛出

---

### Phase 2：统一抽象

#### 2.1 统一 DAG 流式/非流式路径

- **原因**: `DAGExecutor._execute_simple()` 有流式（~60行）和非流式（~65行）两个完整实现，逻辑相同仅输出方式不同。
- **操作**:
  - 合并为单一路径：内部统一用事件队列
  - 流式时实时 `yield`，非流式时收集到 `list` 最后返回
- **测试**: SSE 流式事件顺序、非流式结果完整性

#### 2.2 消除 OutputGuard 重复

- **原因**: `engine.py` 中 dag 路径和 simple 路径各调一次 `OutputGuard.process()`，检查和内容完全相同。
- **操作**: 将 `OutputGuard.process()` 移到两条路径合并后的统一返回点
- **测试**: 输出安全检查覆盖 dag/simple 两种模式

#### 2.3 移除 `supervisor.py`

- **原因**: `Supervisor` 的 DAG 拓扑执行已被 `DAGExecutor` 完全覆盖，且不被主路径使用。
- **操作**:
  - 确认 `dispatcher.py` 不依赖 `supervisor.py`
  - 删除文件，`__init__.py` 移除导出
- **测试**: 多代理调度（`dispatcher`）不受影响

#### 2.4 修复 `tools/__init__.py` dispatch_agent 竞态

- **原因**: `relay_worker` 线程创建和 sentinel 发送之间存在窗口，快速完成的 dispatch 可能错过事件。
- **操作**: 使用 `threading.Event` 同步，确保 worker 创建后再发送
- **测试**: 快速 dispatch 场景不丢事件

---

### Phase 3：缓存 / 常量 / 可观测性

#### 3.1 创建 `constants.py`

- **操作**: 新建 `app/util/agent/constants.py`，集中以下常量：
  - `MAX_HISTORY_TOKENS`, `MAX_HISTORY_COMPACT`（从 `core.py`）
  - `MAX_INPUT_LENGTH`, `MAX_CALLS_PER_TOOL`（从 `guard.py`）
  - `MAX_REFLECT_RETRIES`, `MAX_LOOP_REPEAT`, `MAX_DAG_TOTAL_SECONDS`, `MAX_NODE_SECONDS`（从 `dag.py`, `executor.py`, `reflexion.py`, `agent_base.py`）
  - `SHORT_TERM_TTL`, `LONG_TERM_TTL` 等（从 `memory.py`）
  - `CACHE_TTL`, `CACHE_DB`（从 `cache.py`）
  - `SUB_AGENT_TIMEOUT`, `MAX_CONCURRENT_DISPATCH` 等（从 `dispatcher.py`）
- **测试**: 所有常量值与原值一致

#### 3.2 LLM 确定性缓存

- **原因**: `compact_history`、`classify_domain` 等确定性调用（相同输入 → 相同输出）每次调 LLM 浪费 token 和延迟。
- **操作**:
  - 扩展现有 `cache.py` 的 Redis 缓存模式支持 LLM 响应
  - 对 `compact_history` 和 `classify_domain` 加输入哈希 → 响应缓存
  - TTL 设为 1 小时（远超单次对话时长，但不过期永久）
- **测试**: 缓存命中/未命中、相同输入返回相同结果

#### 3.3 修复工具文件文档字符串

- **原因**: `tools/canvas.py`, `web.py`, `file_ops.py`, `geo.py`, `code.py` 的模块 docstring 含错误的 import 残留（从旧单文件拆分时遗留）。
- **操作**: 将每个文件的文档字符串改为正确的模块说明
- **测试**: `__doc__` 属性正确

#### 3.4 追踪日志大小限制

- **原因**: `tracer.py` 最多保留 50 个文件但没有总大小限制。
- **操作**: 加目录级别 500MB 上限，超出时按修改时间清理最旧文件
- **测试**: 模拟超限场景验证清理逻辑

---

## 二、Meta2D 前端优化

### Phase 1：Bug 修复 + 快捷键

#### 1.1 补齐键盘快捷键

- **操作**: 新建 `web/src/composables/useKeyboardShortcuts.ts`，在 `Editor/index.vue` 中注册
- **快捷键表**:

| 按键 | 操作 |
|------|------|
| `Delete` / `Backspace` | 删除选中 pens |
| `Ctrl+C` | 复制选中 pens 到剪贴板 |
| `Ctrl+V` | 粘贴剪贴板中的 pens |
| `Ctrl+A` | 全选所有 pens |
| `Ctrl+D` | 快速复制选中 |
| `↑ ↓ ← →` | 微调选中 pens 位置（1px，Shift+10px） |
| `Escape` | 取消当前绘制/取消选中/关闭面板 |

- **测试**: 每个快捷键触发正确操作、焦点在输入框时不触发画布快捷键

#### 1.2 修复事件监听泄漏

- **原因**: `PenProps.getPen()` 中 `registeredEvents.forEach((name) => meta2d.off(name))` 移除该事件名下的 **所有** 监听器，影响其他组件。
- **操作**: 保存 handler 引用，`off(name, handlerRef)` 精确移除
- **测试**: 多组件同时注册同事件不互相干扰

#### 1.3 删除损坏的自定义三角形代码

- **原因**: `utils/custom/index.ts` 第 14 行引用未定义的 `meta2d` 变量，运行时必定 `ReferenceError`。
- **操作**: 删除 `utils/custom/index.ts` 和 `utils/custom/triangle.ts`，及相关 import
- **测试**: 编辑器正常加载，无 console 报错

#### 1.4 修复 `canvasBridge.ts` ID 映射时序

- **原因**: `_addPen()` 在 `await meta2d.addPen()` **之前** 调 `penIdMap.set(penId, penId)`，如果 Meta2D 生成的 ID 不同，映射错误。
- **操作**: `penIdMap.set()` 移到 `await` 之后，使用 Meta2D 返回的实际 pen ID
- **测试**: Agent 创建 pen 后立即操作它（更新/删除）不报错

---

### Phase 2：性能优化

#### 2.1 属性面板渲染防抖

- **原因**: `PenProps.changeValue()` 每次属性变化调 `meta2d.setValue(v, { render: true })`，滑块拖动时每像素触发一次全量重渲染。
- **操作**: 加 100ms debounce，连续修改合并为一次渲染。使用 `lodash-es/debounce` 或手写。
- **测试**: 拖动滑块时渲染次数大幅下降，最终值正确

#### 2.2 保存序列化优化

- **原因**: `Header.vue` `onSave()` 手动白名单字段，Meta2D 升级新增字段会静默丢失。
- **操作**:
  - 改为 `meta2d.data()` 全量序列化（Meta2D 保障向前兼容）
  - 缩略图生成移至 `requestIdleCallback` 异步执行，不阻塞保存
- **测试**: 保存/加载往返数据完整性

#### 2.3 自动保存时机优化

- **原因**: `useAgentChat.ts` 每 3 秒自动保存一次，流式过程中频繁写入中间态。
- **操作**: 移除定时 tick，改为仅在 SSE `done` / `error` 事件时触发保存
- **测试**: 流式过程中不触发保存，流式完成后触发一次

#### 2.4 Undo 栈深度克隆优化

- **原因**: `canvasBridge.ts` `pushUndoState()` 每次 `JSON.parse(JSON.stringify(meta2d.data()))` 全量深度克隆，大画布CPU开销大。
- **操作**: 使用 `structuredClone()` 替代 JSON 序列化（浏览器原生，性能更好且保留 Date/RegExp 等类型）
- **测试**: Undo/Redo 功能正常，大画布性能改善

---

### Phase 3：架构增强

#### 3.1 Agent 画布状态感知

- **原因**: 后端 `canvas` 工具的 `get_state` action 返回空数据，Agent 操作时看不到当前画布真实状态。
- **操作**:
  - 前端 `useAgentChat.ts` 的 `buildCanvasContext` 已发送画布摘要，但只在消息发送时快照
  - 后端 `canvas.py` 的 `get_state` action 返回提示信息引导 LLM 查看 system prompt 中的 `canvas_context`
  - Agent 连续多步操作时，前端将前一步 `tool_result` 中携带新 pen ID，供后续步骤引用
- **测试**: Agent 连续操作画布（创建 pen → 修改 pen → 连线）不丢失上下文

#### 3.2 Agent 连线改用原生连接

- **原因**: `canvasBridge.ts` `_addLine` 使用手动 `anchors` 数组创建连线，不参与 Meta2D 内部的关系图追踪。pen 移动时连线不会自动跟随。
- **操作**: 改为使用 Meta2D 的连线 API（通过 `meta2d.addLine()` 或 `addPen()` 时指定 `connected` 关系）
- **测试**: 创建连线后移动源/目标 pen，连线自动跟随

#### 3.3 多画布基础架构

- **原因**: `window.meta2d` 全局单例，无法支持多 Tab 编辑或画布对比。
- **操作**:
  - 新建 `web/src/composables/useCanvas.ts`，封装画布实例管理（provide/inject 模式）
  - `Editor/index.vue` 中创建实例后通过 `provide` 下发
  - 子组件通过 `inject` 获取画布实例，取代 `window.meta2d`
  - `global.d.ts` 保留 `window.meta2d` 作为兼容但标注 deprecated
- **测试**: 单画布功能不受影响，`inject` 能正确获取实例

#### 3.4 画布上下文智能截断

- **原因**: `buildCanvasContext` 硬编码 `MAX_PENS = 50`，大图 AI 看不到完整信息，小图浪费上下文空间。
- **操作**:
  - 按 token 预算动态截断：总上限 ~2000 tokens
  - 优先包含：选中 pen 及其直接连线邻居
  - 其次：视口内可见 pen
  - 最后：其余 pen 按类型聚合统计
- **测试**: 大画布（100+ pens）上下文不超预算，小画布全量包含

---

## 三、测试策略

### Agent 后端（pytest）

- Phase 1: 意图分类、LLM 重试、会话记忆存取/恢复
- Phase 2: DAG 执行（含流式）、工具调度
- Phase 3: 常量一致性、缓存命中率、追踪滚动

### Meta2D 前端（vitest）

- Phase 1: 快捷键事件、事件监听清理、画布操作 ID 映射
- Phase 2: 渲染次数、保存数据完整性、undo 性能
- Phase 3: Agent 工具调用模拟、画布状态同步、多实例隔离

### 门禁流程

每 Phase 完成后执行:
```bash
# 后端
python -m ruff check app/ && python -m ruff format app/ --check && pytest tests/ -v --tb=short

# 前端
cd web && pnpm format --check && npx vitest run
```

---

## 四、风险与回滚

| 风险 | 缓解 |
|------|------|
| `router.py` / `planner.py` 有隐藏使用者 | git grep 全量搜索引用后再删除 |
| `session_memory.py` 合并影响会话恢复 | Phase 1 先补会话恢复测试 |
| LLM 重试统一后行为差异 | 保留各模块的特异性参数（如不同 max_retries） |
| 多画布架构改 `window.meta2d` 引用 | 渐进式迁移：先建 `useCanvas`，逐个组件改 inject，最后移除 global |
| 自动化测试覆盖不足 | 仅对修改文件的核心路径补测试，不全量重写 |
