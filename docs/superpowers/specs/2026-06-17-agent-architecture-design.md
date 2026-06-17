# Agent 架构优化设计 — 主流分层架构改造

> 日期: 2026-06-17 | 分支: dev | 方案: 渐进式重构（Approach A）

## 一、目标

将当前单体 Agent 链路（`AgentSession → AgentEngine → DAGExecutor → Tool`）改造为符合主流 Agent 架构的六层分层系统，覆盖记忆、安全、路由、执行、多Agent协作、可观测性、评估。

## 二、约束

- 模型: deepseek-chat only（成本优先）
- 向量存储: Redis Stack（RediSearch 向量索引，复用现有 Redis）
- 安全护栏: 纯规则 + 正则（不消耗 token）
- 可观测性: 结构化日志 + Redis 指标（不引入 Prometheus/Grafana）
- Router 优先关键词匹配（零 token），不确定时降级 LLM

## 三、总体架构

```
                         ┌──────────────┐
                         │  Observability │  ← 全链路追踪（横切所有层）
                         └──────────────┘
    用户输入
      │
      ▼
┌──────────────┐
│   Guard       │  ← 输入过滤、敏感检测
└──────┬───────┘
       ▼
┌──────────────┐
│   Memory      │  ← 工作/短期/长期记忆 + 向量检索
└──────┬───────┘
       ▼
┌──────────────┐
│   Router      │  ← 意图 → chat / search / canvas / tool / dag
└──────┬───────┘
       ▼
┌──────────────┐
│   Planner     │  ← 仅 dag 模式，生成执行计划
└──────┬───────┘
       ▼
┌──────────────┐
│   Executor    │  ← ReAct + DAG + 子Agent调度
│  ┌─────────┐  │
│  │Supervisor│  │  ← 多Agent编排
│  └─────────┘  │
└──────┬───────┘
       ▼
┌──────────────┐
│   Post-Gate   │  ← 输出审查、PII脱敏、记忆存储
└──────┬───────┘
       ▼
    用户输出

┌──────────────┐
│  Evaluation   │  ← 离线：回归测试 + Prompt对比
└──────────────┘
```

## 四、各模块设计

### 4.1 记忆系统（Memory）

**文件**: `app/util/agent_memory.py` (~300行，新增)

三层记忆架构：

| 层级 | 存储 | TTL | 内容 |
|------|------|-----|------|
| 工作记忆 | 内存 | 会话生命周期 | 当前会话全量消息 |
| 短期记忆 | Redis | 1小时 | LLM 摘要 + 实体提取 |
| 长期记忆 | Redis Stack 向量 | 30天 | 关键对话 embedding → FT.SEARCH 检索 |

**流程**:
1. 会话中: 全量消息存工作记忆
2. 会话结束: `_persist_session()` → LLM 生成摘要 → 短期记忆
3. 摘要 embedding → deepseek embedding API（或本地模型） → Redis Stack `FT.SEARCH`
4. 新会话: `MemoryManager.recall()` 同时检索三层 → 注入 system prompt

**接口**:
```python
class MemoryManager:
    def remember(self, session_id, messages) -> None
    def recall(self, user_id, query) -> MemoryContext
    def forget(self, user_id, session_id) -> None
```

**重构**: `agent_session_memory.py` — 精简为调用 MemoryManager

### 4.2 安全护栏（Guard）

**文件**: `app/util/agent_guard.py` (~200行，新增)

三阶段把关，纯规则不消耗 token：

```
Input Guard:
  ├─ 敏感词过滤 (外部配置文件)
  ├─ 长度限制 (8K chars)
  └─ 语言检测

Tool Guard:
  ├─ 参数白名单校验
  ├─ 破坏性操作二次确认 (delete/clear)
  └─ 同工具调用频率限制

Output Guard:
  ├─ PII 脱敏 (手机/邮箱 → ***)
  ├─ 有害内容关键词检测
  └─ JSON/map/route 代码块格式完整性
```

Guard 失败统一返回错误格式，不暴露内部细节。

### 4.3 路由 + 规划 + 执行（Router/Planner/Executor）

**新增**: `agent_router.py` (~180行), `agent_planner.py` (~150行), `agent_executor.py` (~300行)  
**重构**: `agent_engine.py` (精简), `agent_dag.py` (拆出 Executor)

三层分离，各自独立 prompt：

```
Router: 只做意图分类
  输入: 用户消息 + 历史摘要
  输出: {route, domain, confidence}
  路由表: chat | search | canvas | tool | dag
  
  ★ 优先关键词匹配（零token），不确定时 LLM

Planner: 只在 route=dag 时执行
  输入: 用户消息 + 路由结果 + Memory 上下文
  输出: DAGPlan {goal, nodes, risk}
  
  优化: PlanMemory 失败反馈注入、工具可用性感知

Executor: 执行 ReAct + DAG
  SimpleExecutor: 单轮 ReAct + 工具调用
  DAGExecutor: 拓扑并行执行
  共享: LLM调用、工具执行、重试/熔断
```

### 4.4 多 Agent 协作（Supervisor）

**新增**: `agent_supervisor.py` (~250行)  
**重构**: `agent_dispatcher.py`

Supervisor 模式：

```
Supervisor
  ├─ 任务拆解: LLM 生成子任务 DAG
  ├─ 调度执行: 拓扑分发 → 子Agent
  └─ 汇总输出: 子结果合并

子Agent (独立 system prompt + 限定工具集):
  ├─ canvas_agent : 画布增删改查
  ├─ file_agent   : 文件搜索/上传/分析
  ├─ code_agent   : 代码生成/审查
  ├─ image_agent  : 图片分析
  └─ search_agent : 联网搜索+总结
```

子Agent 间通过 SharedContext（pheromone）传递信息。失败时 Supervisor 决定重试/替换/降级。

### 4.5 可观测性（Observability）

**文件**: `app/util/agent_observability.py` (~200行，新增)

每个请求 trace_id → 各层 Span 记录：

```
├─ Span: guard        (耗时, 通过/拒绝)
├─ Span: memory_recall (命中率, 检索条数)
├─ Span: router       (路由结果, 关键词/LLM)
├─ Span: planner      (plan节点数, 耗时)
├─ Span: executor
│   ├─ Span: llm_call  (model, tokens_in/out, 耗时, 重试)
│   ├─ Span: tool_call (工具名, 成功/失败, 耗时)
│   └─ Span: sub_agent (agent名, 耗时)
└─ Span: post_gate    (通过/拦截)
```

输出: 结构化 JSON 日志到 stdout，Redis 指标（计数器/成功率/P95延迟）。

### 4.6 评估体系（Evaluation）

**目录**: `app/util/agent_eval/` (~300行，新增)

```
agent_eval/
  ├── __init__.py
  ├── runner.py          # 评测运行器
  ├── cases/
  │   ├── chat_cases.json    (20条)
  │   ├── search_cases.json  (15条)
  │   ├── canvas_cases.json  (20条)
  │   └── dag_cases.json     (15条)
  └── sensitive_words.txt    # 敏感词库
```

每条 case:
```json
{
  "query": "画一个矩形",
  "expected_route": "canvas",
  "expected_tools": ["canvas"],
  "forbidden_tools": [],
  "min_tokens": 20
}
```

使用: `python -m app.util.agent_eval.runner`

评测维度: 路由准确率、工具准确率、幻觉检测、响应质量。

## 五、文件变更汇总

| # | 模块 | 新增文件 | 改动文件 | 预估行数 |
|---|------|---------|---------|---------|
| 1 | 记忆系统 | `agent_memory.py` | `agent_session_memory.py` | +300 |
| 2 | 安全护栏 | `agent_guard.py` | — | +200 |
| 3 | 路由+规划+执行 | `agent_router.py`, `agent_planner.py`, `agent_executor.py` | `agent_engine.py`, `agent_dag.py` | +400 |
| 4 | 多 Agent | `agent_supervisor.py` | `agent_dispatcher.py` | +250 |
| 5 | 可观测性 | `agent_observability.py` | — | +200 |
| 6 | 评估体系 | `agent_eval/` (3文件) | — | +300 |
| **合计** | | **9 新文件** | **4 重构** | **~1650行** |

## 六、实施顺序

按依赖关系排列（每个模块独立上线）：

1. **可观测性** — 无依赖，最先做，后续模块改造有 tracing 支撑
2. **安全护栏** — 无依赖，独立模块
3. **路由+规划+执行** — 依赖可观测性 tracing
4. **记忆系统** — 依赖可观测性 + 需部署 Redis Stack
5. **多 Agent** — 依赖 Executor 重构
6. **评估体系** — 最后做，依赖所有模块定型后收集 case
