# Agent 架构改造设计

> 日期: 2026-06-17 | 方案: 基础层完整复刻 + 业务层重新设计

## 一、目标

将 mind 图形可视化编辑器改造为 Agent 架构项目，支持通过自然语言对话操控画布、生成蓝图、管理文件。

### 核心能力
- 自然语言操控画布（创建/编辑图形、连线、布局）
- 智能蓝图生成（根据描述生成流程图、架构图、思维导图等）
- 全面 AI 助手（文件管理、蓝图搜索、代码生成）

### 约束
- 现有编辑器功能零侵入，Agent 作为独立子系统
- 复用 pypano 的 LLM 配置（DeepSeek + fallback）
- 前端通过抽屉式面板集成，不影响现有编辑布局

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                          │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ 现有编辑器 │  │ Header   │  │ AgentPanel (新增)     │ │
│  │ (保持不动) │  │ (加入口) │  │  AI 对话抽屉          │ │
│  └───────────┘  └──────────┘  └──────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    API 层 (Flask)                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  POST /v1/agent/chat  (SSE 流式)                 │   │
│  │  POST /v1/agent/mcp   (MCP 协议，可选)           │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                  Agent 引擎层 (新增)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Session   │ │Engine    │ │DAG       │ │Intent    │  │
│  │          │ │          │ │Executor  │ │Classifier│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Dispatcher│ │Tracer    │ │Reflexion │ │Pheromone │  │
│  │          │ │          │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────┤
│                  业务层 (新增 + 适配)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Canvas    │ │Blueprint │ │File      │ │Code      │  │
│  │Agent     │ │Agent     │ │Agent     │ │Agent     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │~16 tools │ │Skills    │ │PlanMemory│               │
│  └──────────┘ └──────────┘ └──────────┘               │
├─────────────────────────────────────────────────────────┤
│              现有业务层 (保持不变)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │blueprint │ │material  │ │categories│               │
│  │MySQL     │ │MySQL     │ │MySQL     │               │
│  └──────────┘ └──────────┘ └──────────┘               │
│  ┌──────────┐                                        │
│  │MinIO     │                                        │
│  └──────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

### 请求流程

1. 前端 AgentPanel 发送 POST /v1/agent/chat
2. Flask 在后台线程中执行 AgentSession.chat_v3()，通过 queue → SSE 流返回
3. AgentSession 调用 Intent 分类 → 生成 Plan
4. AgentEngine 路由：simple（单轮 ReAct）或 dag（多节点并行）
5. DAGExecutor 拓扑排序 + 并行执行节点（使用 executor.py 的 ManagedPool）
6. 每个节点运行子 Agent 的 ReAct 循环
7. 工具调用事件通过 SSE 流返回前端
8. 对于 canvas/layout 类工具：后端只做参数校验并生成事件，前端桥接层接收事件后调用 meta2d API 实际操作画布
9. 对于 blueprint/file 类工具：后端直接操作数据库/MinIO，结果通过 SSE 返回

---

## 三、基础层设计（从 pypano 复刻）

基础层是通用 Agent 基础设施，与业务无关。从 pypano 直接复制或适配。

### 模块清单

| 模块 | 文件路径 (新增) | 迁移方式 |
|------|----------------|----------|
| LLM Client | `app/util/llm_client.py` | 直接复制 |
| Fallback LLM | `app/util/agent_fallback.py` | 直接复制 |
| Circuit Breaker | `app/util/agent_circuit.py` | 直接复制 |
| Executor | `app/util/executor.py` | 直接复制（去掉 eventlet 依赖） |
| Tool Registry | `app/util/tool_registry.py` | 直接复制 |
| Agent Base | `app/util/agents/base.py` | 直接复制 |
| Agent Dispatcher | `app/util/agent_dispatcher.py` | 直接复制 |
| Agent Core | `app/util/agent_core.py` | 复制 → 适配 context |
| Agent Engine | `app/util/agent_engine.py` | 直接复制 |
| Agent DAG | `app/util/agent_dag.py` | 直接复制 |
| Agent Intent | `app/util/agent_intent.py` | 复制 → 适配 domains |
| Agent Tracer | `app/util/agent_tracer.py` | 直接复制 |
| Agent Evaluator | `app/util/agent_evaluator.py` | 直接复制 |
| Agent Reflexion | `app/util/agent_reflexion.py` | 直接复制 |
| Agent Pheromone | `app/util/agent_pheromone.py` | 直接复制 |
| Agent Plan Eval | `app/util/agent_plan_eval.py` | 直接复制 |
| Agent Cache | `app/util/agent_cache.py` | 直接复制 |
| Agent MCP | `app/util/agent_mcp.py` | 直接复制 |
| Agent Session Memory | `app/util/agent_session_memory.py` | 复制 → 适配 |
| Agent Skills | `app/util/agent_skills/*.py` | 复制框架 → 重写 skill |
| Agent Helpers | `app/util/agent_helpers.py` | 直接复制 |

### 新增目录结构

```
app/util/
├── (现有文件保留: __init__.py, file.py, json_response.py, 
│                 log_config.py, protocol_handler.py)
├── agent_core.py              # 新增
├── agent_engine.py            # 新增
├── agent_dag.py               # 新增
├── agent_intent.py            # 新增
├── agent_tools.py             # 新增（业务 tools）
├── agent_tracer.py            # 新增
├── agent_evaluator.py         # 新增
├── agent_reflexion.py         # 新增
├── agent_pheromone.py         # 新增
├── agent_plan_eval.py         # 新增
├── agent_cache.py             # 新增
├── agent_circuit.py           # 新增
├── agent_fallback.py          # 新增
├── agent_dispatcher.py        # 新增
├── agent_session_memory.py    # 新增
├── agent_mcp.py               # 新增
├── agent_helpers.py           # 新增
├── tool_registry.py           # 新增
├── llm_client.py              # 新增
├── executor.py                # 新增
├── agents/                    # 新增目录
│   ├── __init__.py
│   ├── base.py
│   ├── canvas_agent.py
│   ├── blueprint_agent.py
│   ├── file_agent.py
│   └── code_agent.py
└── agent_skills/              # 新增目录
    ├── __init__.py
    ├── canvas_skill.py
    ├── blueprint_skill.py
    ├── file_skill.py
    ├── mindmap_skill.py
    └── code_skill.py
```

### 配置适配

`.env` 新增 LLM 配置（复用 pypano 格式）：

```env
DEEPSEEK_API_KEY=xxx
DEEPSEEK_BASE_URL=xxx
LLM_TIMEOUT=120
FALLBACK1_API_KEY=xxx
FALLBACK1_MODEL=xxx
FALLBACK1_BASE_URL=xxx
VISION_API_KEY=xxx
VISION_BASE_URL=xxx
VISION_MODEL=xxx
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

---

## 四、业务层设计

### 4.1 工具集 (Tools)

#### Canvas 操作工具（前端桥接执行）

Canvas/layout 工具采用**后端校验 + 前端执行**模式：
- 后端：参数校验、生成标准 tool_call/tool_result SSE 事件
- 前端：AgentPanel 接收事件 → 桥接层 emit → Editor 调用 meta2d API 实际执行
- 优点：LLM 能"看见"画布操作的完整生命周期，Agent 可以链式调用

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `canvas_add_pen` | 在画布上创建图形/节点 | type, text, x, y, width, height, style |
| `canvas_update_pen` | 修改现有图形属性 | pen_id, props |
| `canvas_delete_pen` | 删除图形 | pen_id / pen_ids[] |
| `canvas_add_line` | 创建连线 | from_pen, to_pen, line_type, text, style |
| `canvas_get_state` | 获取当前画布所有图形状态 | 无 → pens[], lines[] |
| `canvas_clear` | 清空画布 | confirm (bool) |
| `canvas_undo` | 撤销 | 无 |
| `canvas_redo` | 重做 | 无 |

#### 蓝图管理工具

| 工具名 | 功能 |
|--------|------|
| `blueprint_list` | 列出所有蓝图（分页、筛选） |
| `blueprint_load` | 加载指定蓝图到画布 |
| `blueprint_save` | 保存当前画布为蓝图 |
| `blueprint_search` | 按关键词搜索蓝图 |
| `blueprint_export` | 导出蓝图为 PNG/SVG/JSON |

#### 布局工具

| 工具名 | 功能 |
|--------|------|
| `layout_auto_arrange` | 自动排版（水平/垂直/网格） |
| `layout_align` | 对齐选中图形 |

#### 辅助工具

| 工具名 | 功能 |
|--------|------|
| `file_search` | 搜索素材/文件 |
| `code_generate` | 根据描述生成 JS/JSON 代码 |

### 4.2 子 Agent (Sub-Agents)

| Agent | 绑定工具 | 职责 |
|-------|----------|------|
| CanvasAgent | canvas_*, layout_* | 画布图形创建、编辑、布局 |
| BlueprintAgent | blueprint_* | 蓝图搜索、加载、保存 |
| FileAgent | file_search + material API | 文件/素材检索管理 |
| CodeAgent | code_generate | 代码片段生成 |

每个 Agent 继承 AgentBase，拥有独立 ReAct 循环，通过 AgentDispatcher 调度。

### 4.3 技能系统 (Skills)

| Skill | 触发域 | 注入内容 |
|-------|--------|----------|
| canvas_skill | canvas | meta2d API 规范、图形类型、连线类型、布局模式 |
| blueprint_skill | blueprint | 蓝图命名规范、分类体系 |
| mindmap_skill | mindmap | 思维导图节点结构、分支布局规则 |
| file_skill | file | 文件目录结构、素材格式支持 |
| code_skill | code | Monaco 编辑器 API、代码类型 |

### 4.4 意图分类

Domain 定义：`["canvas", "blueprint", "file", "mindmap", "code", "chat"]`

LLM 根据用户输入自动识别 intent（chat/tool）、domains、has_write → 生成 Plan（simple/dag）。

---

## 五、前端设计

### 5.1 布局

现有 3 列布局不变，Agent 面板以右侧抽屉形式出现。Header 工具栏新增 🤖 AI 按钮打开抽屉。

### 5.2 组件树

```
src/components/AgentPanel/
├── index.vue                 # 抽屉容器，管理聊天状态
├── AgentMessageList.vue      # 消息列表（自动滚动到底部）
├── AgentMessageItem.vue      # 单条消息（user/assistant/system）
├── AgentThinkCard.vue        # 思考过程卡片（可折叠）
├── AgentToolCard.vue         # 工具调用卡片（名称+参数+结果状态）
├── AgentPlanCard.vue         # DAG 计划可视化卡片
├── AgentInput.vue            # 输入框（Enter 发送，Shift+Enter 换行）
└── AgentStreamHandler.ts     # SSE 流式数据解析 + 事件分发
```

### 5.3 API 接口

```typescript
// src/api/agent.ts
function agentChat(messages: Message[], options: {
  onEvent?: (event: AgentEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}): AbortController

type AgentEvent =
  | { type: 'text_delta'; content: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; tool: string; args: object }
  | { type: 'tool_result'; tool: string; result: any }
  | { type: 'plan'; plan: DAGPlan }
  | { type: 'agent_dispatch'; agent: string }
  | { type: 'error'; message: string }
  | { type: 'done' }
```

### 5.4 画布双向通信

Agent 通过工具调用操作画布时，前端桥接层转发给 Editor：

```
LLM → tool_call(canvas_add_pen) → SSE → AgentPanel
  → emit('agent:canvas_add_pen', args)
  → Editor 监听 → meta2d.addPen(args) → 画布实时更新
```

使用 Vue `provide/inject` 实现 AgentPanel 与 Editor 的解耦通信。

### 5.5 SSE 流式处理

AgentPanel 通过 EventSource / fetch + ReadableStream 连接 `/v1/agent/chat`，解析 SSE 事件流，分发到对应卡片组件渲染。

---

## 六、实施策略

### Phase 1：基础设施层
1. 从 pypano 复制基础层模块到 mind
2. 适配配置（config/__init__.py 新增 LLM/Redis 配置项）
3. 安装依赖（openai, redis-py）
4. 验证：各模块可以 import 无报错

### Phase 2：工具注册 + Agent Core
1. 实现 ~16 个业务工具（agent_tools.py）
2. 实现 4 个子 Agent（canvas/blueprint/file/code）
3. 实现 Skills 提示词
4. 适配 AgentSession → canvas context
5. 验证：单元测试工具调用

### Phase 3：API 层
1. 新增 `/v1/agent/chat` SSE 端点
2. 注册 agent 蓝图
3. 使用 threading + queue 实现后台异步执行 + SSE 流式返回（不引入 Celery，mind 项目规模不需要）
4. 新增 `/v1/agent/mcp` 端点（可选）
5. 验证：curl 测试 SSE 流

### Phase 4：前端
1. 创建 AgentPanel 组件树
2. 实现 SSE 流式解析
3. 实现画布桥接层
4. Header 添加 AI 入口按钮
5. 验证：端到端对话测试

---

## 七、风险与注意事项

- **Redis 依赖**：mind 当前没有 Redis，Phase 1 需新增 Redis 配置和 redis-py 依赖（agent_cache、agent_plan_eval 需要）。如暂时无法部署 Redis，Cache 和 PlanMemory 模块可降级为内存实现
- **Canvas 上下文适配**：AgentSession 中的 context 构建需从 pypano 的 "pano context" 改为 mind 的 "canvas context"——即当前画布的图形列表、选中状态、蓝图 ID 等运行时信息，由前端在请求体中随消息一起发送
- **Canvas 工具桥接**：canvas/layout 工具后端只做参数校验并生成事件，实际操作由前端桥接层调用 meta2d API。前后端需要约定严格的事件格式（tool_call args 必须能直接映射为 meta2d API 参数）
- **pypano 硬编码清理**：从 pypano 复制的模块需 grep 检查是否有 pypano 特有的硬编码引用（如 pano_id、scene_id、热点相关数据库表名），替换为 mind 的对应概念或标记为适配项
- **依赖新增**：mind 目前 requirements.txt 较精简，需新增 openai、redis、eventlet（或直接用 threading）等依赖
