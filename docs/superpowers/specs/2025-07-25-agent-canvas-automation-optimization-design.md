# Agent & Canvas 自动化优化 — 设计文档

> 日期：2025-07-25 | 状态：待实现

## 概览

对 Mind 项目的 Agent 系统和画布自动化功能进行三轮优化：P0（可靠性）、P1（智能度）、P2（新能力）。共 11 项改动。

---

## P0 — 可靠性（修地基）

### P0-1: Blueprint 保存原子化

**问题**：当前 `blueprint_save` 分两步执行——后端创建空 pens 记录，前端事后从 `localStorage['meta2d']` 读取 pens 数据 patch 回去。两步非原子，且 AgentPanel（画布编辑页）无 `localStorage` 依赖。

**方案**：改为后端一步完成。前端请求时携带 `canvas_snapshot`（精简 pens 快照），`blueprint_save` 工具直接从 `tool_ctx` 读取并写入完整记录。

**改动文件**：
- `web/src/composables/useAgentChat.ts` — `buildCanvasContext()` 额外收集 pens 快照放入请求 body
- `app/api/v1/agent.py` — 透传 `canvas_snapshot` 到 AgentSession
- `app/util/agent/core.py` — `AgentSession.chat_v3()` 将 snapshot 注入 `tool_ctx`
- `app/util/agent/tools/blueprint.py` — `_tool_blueprint_save` 直接写入完整 pens
- `web/src/views/chat/index.vue` — 删除 post-hoc patch 逻辑

**兼容性**：无 `canvas_snapshot` 时仅更新 name/desc，不覆盖已有 pens。

---

### P0-2: 后端画布状态跨轮次追踪

**问题**：后端不维护任何画布状态，每轮对话全量注入画布上下文。Agent 不知道上一轮自己创建了哪些 pen，ID 校验全为乐观假设。

**方案**：在 StateStore 中增加 `CanvasShadow`（画布影子状态），后端维护轻量画布模型。

**数据结构**：
```python
@dataclass
class CanvasShadow:
    pens: dict[str, PenShadow]    # pen_id → {type, text, x, y, width, height}
    lines: dict[str, LineShadow]  # line_id → {from, to}
    version: int                   # 单调递增，冲突检测
    last_sync_at: float
```

**同步机制**：请求到达时对比 `canvas_snapshot.version` vs `CanvasShadow.version`：
- 一致 → 直接用 shadow
- 用户手动编辑过 → diff 合并（用户手动改的保留，Agent 改的重放）
- shadow 不存在 → 全量初始化

**工具改造**：`canvas_edit` 的写操作同步更新 shadow；`add_line`/`delete_pen` 等操作基于 shadow 做真实 ID 校验。

**存储**：Redis `canvas_shadow:{session_id}`，TTL 30min。

**改动文件**：
- 新增 `app/util/agent/canvas_shadow.py` — CanvasShadow 类 + diff/合并逻辑
- `app/util/agent/tools/canvas/edit.py` — 写操作同步 shadow
- `app/util/agent/state_store.py` — 集成 CanvasShadow 持久化
- `app/util/agent/core.py` — chat_v3 初始化/加载 shadow

---

### P0-3: CanvasAgent 工具补齐

**问题**：CanvasAgent 的 `CANVAS_TOOLS` 缺少 `canvas_props` 和 `fit_view`。

**方案**：补齐工具列表为 3 个统一后的工具（canvas_edit / canvas_organize / canvas_view）+ blueprint_save。

**改动文件**：
- `app/util/agent/agents/canvas_agent.py` — 更新 `CANVAS_TOOLS` 列表和 system_prompt

---

## P1 — 智能度（让 Agent 更准、更少重试）

### P1-1: 画布工具统一化（方案 B）

**问题**：画布工具分裂为 1 个统一 `canvas` 工具 + 5 个独立工具（layout_auto_arrange, layout_align, canvas_props, fit_view, canvas_check_empty），LLM function-calling 看到 6 个 schema，容易选错。

**方案**：按语义重组为 3 个工具：
- `canvas_edit` — 图形增删改（11 action）
- `canvas_organize` — 组织布局（7 action）
- `canvas_view` — 视图属性（3 action）

**文件结构**：
```
app/util/agent/tools/canvas/
├── __init__.py     # re-export 3 个工具的 schema + run 函数
├── _base.py        # 共享：_new_pen_id(), CanvasShadow 引用
├── edit.py         # canvas_edit 工具
├── organize.py     # canvas_organize 工具
└── view.py         # canvas_view 工具
```

**迁移**：新建包，旧 `tools/canvas.py` 保留标记 `deprecated=True`，前端同时支持新旧工具名 1 个版本后删旧代码。

**改动文件**：
- 新增 `app/util/agent/tools/canvas/` 包（5 个文件）
- `web/src/utils/canvasBridge.ts` — 工具名路由适配
- `app/util/agent/tool_router.py` — 更新 domain mapping
- `app/util/agent/agents/canvas_agent.py` — 更新 CANVAS_TOOLS

---

### P1-2: 画布上下文语义截断

**问题**：`buildCanvasContext()` 按纯 token 数截断画布 pens，可能截掉选中节点、断开连线关系。

**方案**：预算分层 + 关键信息保证：
```
总预算 ~2000 tokens
├─ Layer 0: 选中节点（100% 保留，不限 token）
├─ Layer 1: 选中节点的 1 跳邻居（最多 40% 预算）
├─ Layer 2: 有文字内容的节点（最多 30% 预算）
├─ Layer 3: 其余节点（填充剩余预算）
└─ Lines: 涉及以上任意节点的连线全量保留
```

**改动文件**：
- `web/src/composables/useAgentChat.ts` — `buildCanvasContext()` 重构

---

### P1-3: Plan-Feedback 用户隔离

**问题**：`plan_eval.py` 的 PlanMemory 用模块级全局 dict/lists 存储 feedback，用户 A 的计划失败教训会泄露给用户 B。

**方案**：三层隔离：
```
plan_feedback:{user_id}:{domain}   ← 用户私有 feedback
plan_recent:{user_id}:{domain}     ← 用户私有 recent
plan_patterns:{domain}             ← 跨用户聚合模式（匿名化、只读）
```

**改动文件**：
- `app/util/agent/plan_eval.py` — PlanMemory 类重构，key 加入 user_id 维度
- `app/util/agent/planner.py` — 实例化传入 user_id
- `app/util/agent/engine.py` — 透传 user_id

---

### P1-4: LLM 缓存感知失效

**问题**：意图分类/历史压缩的 LLM 缓存用固定 300s TTL，画布状态变化后仍返回旧缓存。

**方案**：缓存 key 混入可变状态的 version 号：
```python
cache_key = f"llm:{fn_name}:{md5(prompt + tools)}:v{state_version}"
```
`state_version` = CanvasShadow.version XOR blueprint:version。

**改动文件**：
- `app/util/agent/cache.py` — `llm_cache_get/set` 增加 `tool_ctx` 参数
- `app/util/agent/intent.py` — 透传 `tool_ctx`
- `app/util/agent/core.py` — 透传
- `app/util/agent/tools/blueprint.py` — save 成功后 bump 版本号

---

## P2 — 新能力（锦上添花）

### P2-1: 操作宏/模板

**方案**：用户可将一组操作序列存为可复用 macro。支持自然语言创建、手动录制、Agent 自动匹配触发。

**存储**：MySQL 新表或 Redis hash。

**新增工具**：`macro`（list / run / save 三个 action）。

**改动文件**：
- 新增 `app/util/agent/tools/macro.py`
- `web/src/utils/canvasBridge.ts` — 录制/回放逻辑
- 前端：录制按钮 + 下拉选择器 UI

---

### P2-2: 画布状态版本回滚

**方案**：在 `canvas_view` 中增加 `list_snapshots`、`restore_snapshot`、`save_snapshot` 三个 action，暴露 StateStore 已有的快照能力。每次 canvas_edit 写操作前自动创建快照。

**改动文件**：
- `app/util/agent/tools/canvas/view.py` — 新增 3 个 action
- `app/util/agent/state_snapshot.py` — 增加命名快照接口
- `web/src/utils/canvasBridge.ts` — restore handler

---

### P2-3: 智能布局增强

**方案**：`auto_arrange` 增加 `algorithm` 参数，支持 grid / tree / force / layered 四种算法。布局计算全部在前端 `layoutEngine.ts` 中完成。

**改动文件**：
- 新增 `web/src/utils/layoutEngine.ts`
- `web/src/utils/canvasBridge.ts` — auto_arrange handler 改用 layoutEngine
- `app/util/agent/tools/canvas/organize.py` — 扩展参数 schema

---

### P2-4: 跨 Blueprint 操作

**方案**：新增 `blueprint_diff`、`blueprint_merge`、`blueprint_from_template` 三个工具。

**改动文件**：
- `app/util/agent/tools/blueprint.py` — 新增 3 个工具
- `app/package/module/blueprint_mysql.py` — diff/merge 辅助方法
- 新增 `app/data/blueprint_templates/` — 预置 5-8 个模板 JSON
- `app/util/agent/skills/blueprint_skill.py` — 补充使用说明

---

## 实施顺序

```
P0-3 (15行, 先热个身)
  → P0-1 (80行, 修保存链路)
    → P0-2 (200行, CanvasShadow 基础设施)

P1-1 (350行, 工具统一化, 依赖 P0-2 的 shadow)
  → P1-2 (50行, 上下文截断)
    → P1-3 (90行, Feedback 隔离)
      → P1-4 (40行, 缓存版本化)

P2-2 (120行, 版本回滚, 复用 P0-2 snapshot)
  → P2-3 (240行, 布局增强)
    → P2-1 (350行, 操作宏)
      → P2-4 (300行, 跨蓝图)
```

总计预估改动量：~1,835 行（含新建文件）。
