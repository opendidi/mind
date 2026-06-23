# Agent ↔ Meta2D 完整集成优化 — 设计文档

**日期**: 2026-06-23
**分支**: dev
**目标**: 优化 AgentPanel 与 Meta2D 编辑器之间的双向通信，修复 bug、扩展能力、统一 ID 策略

---

## 改进概览

| # | 类型 | 描述 |
|---|------|------|
| 1 | 🐛 Bug | 修复 `buildCanvasContext()` 中 lines 序列化——使用 Meta2D 的 `source.id/connectTo` |
| 2 | 🔧 增强 | 扩展 `PenData` 接口和 `_addPen`，支持 ~30 个 Meta2D Pen 属性 |
| 3 | 🔧 增强 | 扩展后端 canvas 工具，新增 8 个操作 |
| 4 | 🔧 重构 | UUID Pen ID 策略——彻底使用 Meta2D 真实 ID，移除 penIdMap |
| 5 | 📋 增强 | 丰富 canvas context pen 序列化，发送关键样式/状态属性 |
| 6 | 📋 增强 | 丰富 selections.pen 自动注入上下文 |
| 7 | 🔧 增强 | 增强 Meta2D API 调用方式（批量 setValue、debounce 同步） |

---

## #1 修复 lines 序列化

**文件**: `web/src/composables/useAgentChat.ts` — `buildCanvasContext()`

**当前代码** (lines 163-167):
```typescript
const lines = (data.lines || []).map((l: any) => ({
  from: l.fromPen || l.from,
  to: l.toPen || l.to,
  text: (l.text || '').slice(0, 200),
}))
```

**问题**: Meta2D 的连线（`type: 1`）不使用 `fromPen`/`toPen` 属性。它的连接关系存储在：
- `source: { id: <起始节点ID>, connectTo: <目标节点ID> }` — 连接关系
- `anchors: [{x, y}, {x, y}]` — 连接锚点
- `lineName: 'line' | 'curve' | 'polyline' | 'mind'` — 线型
- `fromArrow: string`, `toArrow: string` — 箭头

`fromPen`/`toPen` 仅存在于 `canvasBridge.ts` 的 localStorage 数据中（前端自定义），不是 Meta2D 原生数据。

**修复后**:
```typescript
const lines = (data.lines || []).map((l: any) => ({
  from: l.source?.id || '',
  to: l.source?.connectTo || '',
  lineName: l.lineName || 'line',
  text: (l.text || '').slice(0, 200),
  fromArrow: l.fromArrow || '',
  toArrow: l.toArrow || '',
  color: l.color || '',
  lineWidth: l.lineWidth || 2,
}))
```

---

## #2 扩展 PenData 接口

**文件**: `web/src/utils/canvasBridge.ts`

### 当前 PenData (lines 14-27):

```typescript
export interface PenData {
  penId?: string; type: string; text?: string;
  x: number; y: number; width?: number; height?: number;
  background?: string; color?: string; fontSize?: number;
  borderWidth?: number; borderColor?: string;
}
```

### 扩展后 PenData:

```typescript
export interface PenData {
  // 基础
  penId?: string; type: string; text?: string;
  x: number; y: number; width?: number; height?: number;
  // 填充/边框
  background?: string; color?: string; borderColor?: string;
  borderWidth?: number; borderRadius?: number;
  lineDash?: number[]; globalAlpha?: number;
  // 阴影
  shadowColor?: string; shadowBlur?: number;
  shadowOffsetX?: number; shadowOffsetY?: number;
  // 渐变
  gradientColors?: string; lineGradientColors?: string;
  // 文字
  fontSize?: number; fontFamily?: string; fontWeight?: string;
  fontStyle?: string; textAlign?: string; textBaseline?: string;
  // 图标
  icon?: string; iconFamily?: string; iconSize?: number; iconColor?: string;
  // 图片
  image?: string; imageRatio?: boolean;
  // 内边距
  paddingTop?: number; paddingBottom?: number;
  paddingLeft?: number; paddingRight?: number;
  // 状态
  visible?: boolean; locked?: number; tags?: string[];
}
```

### 更新位置:

1. `_addPen()` — 构造 pen 对象时展开所有属性
2. `_updatePen()` — props 透传所有属性（无需改动，已用 spread）
3. `_addDiagram()` — nodes 创建时展开所有属性
4. `executeCanvasToolLocalStorage()` — localStorage 模式同步更新
5. `COLOR_DEFAULTS` — 无变化（仅用于无默认值的新 pen）

---

## #3 扩展后端 Canvas 工具

**文件**: `app/util/agent/tools/canvas.py`

### 3a. Unified `canvas` 工具 — 扩展 action enum

当前 actions: `add_pen`, `add_line`, `add_diagram`, `update_pen`, `delete_pen`, `clear`, `undo`, `redo`, `get_state`

新增 7 个:

| Action | 参数 | 返回 |
|--------|------|------|
| `lock` | `pen_ids: string[]` | `{success, data: {pen_ids, locked: true}}` |
| `unlock` | `pen_ids: string[]` | `{success, data: {pen_ids, locked: false}}` |
| `toggle_visibility` | `pen_ids: string[]`, `visible: boolean` | `{success, data: {pen_ids, visible}}` |
| `duplicate` | `pen_ids: string[]`, `offset_x?: number`, `offset_y?: number` | `{success, data: {original_ids, new_ids}}` |
| `move_pen` | `moves: [{pen_id, x, y}]` | `{success, data: {moves}}` |
| `group` | `pen_ids: string[]` | `{success, data: {group_id}}` |
| `ungroup` | `pen_id: string` | `{success, data: {pen_id, child_ids}}` |

### 3b. 新增独立工具

| 工具名 | 参数 | 功能 |
|--------|------|------|
| `canvas_props` | `background?`, `grid?`, `gridColor?`, `gridSize?`, `rule?`, `ruleColor?` | 设置画布级属性 |
| `fit_view` | `fit?: boolean`, `padding?: number` | 自适应视口 |

### 3c. 后端 Schema 定义

每个新 action 在 `@ToolRegistry.register` 的 JSON Schema 的 `properties.action.enum` 中添加，并在 `properties` 中添加对应参数定义。

---

## #4 UUID Pen ID 策略

### 核心变化

**之前**:
```python
# canvas.py
_pen_counter = 0
def _next_pen_id():
    global _pen_counter
    _pen_counter += 1
    return f"pen_{_pen_counter}"
```

**之后**:
```python
import uuid

def _new_pen_id():
    return uuid.uuid4().hex[:12]  # 12 位 hex = 48 bits 随机
```

### 前端变化

**之前** (`canvasBridge.ts`):
```typescript
const penIdMap: Map<string, string> = new Map()  // 逻辑ID → 真实ID

async function _addPen(...) {
  const p = await meta2d.addPen(pen)
  const realId = p?.id
  if (penId && realId) penIdMap.set(penId, realId)
}
```

**之后**:
```typescript
async function _addPen(...) {
  pen.id = penId  // 后端 UUID 直接用作 Meta2D pen ID
  await meta2d.addPen(pen)
  // penIdMap 不再需要
}
```

### 移除项

- `penIdMap`、`resolvePenId()`、`clearPenIdMap()` 从 `canvasBridge.ts` 中移除
- `_addLine`、`_updatePen`、`_deletePen` 中不再需要 `resolvePenId()` 调用
- `_addDiagram` 中不再需要 `logicalToActual` 映射——后端已在 nodes 的 `pen_id` 中使用 UUID

---

## #5 丰富 canvas context

**文件**: `web/src/composables/useAgentChat.ts` — `buildCanvasContext()`

### 当前 pen 序列化 (lines 152-158):

```typescript
truncatedPens.push({
  id: p.id || p.penId,
  type: p.name || p.type || 'rectangle',
  text: (p.text || '').slice(0, 200),
  x: p.x || 0, y: p.y || 0,
  width: p.width || 100, height: p.height || 60,
})
```

### 扩展后:

```typescript
truncatedPens.push({
  id: p.id || p.penId,
  type: p.name || p.type || 'rectangle',
  text: (p.text || '').slice(0, 200),
  x: p.x || 0, y: p.y || 0,
  width: p.width || 100, height: p.height || 60,
  // 样式 — 帮助 Agent 理解视觉状态
  background: p.background || '',
  color: p.color || '',
  borderColor: p.borderColor || '',
  borderRadius: p.borderRadius,
  fontSize: p.fontSize,
  fontFamily: p.fontFamily,
  fontWeight: p.fontWeight,
  textAlign: p.textAlign,
  // 图标/图片 — Agent 需知道是否有这些元素
  icon: p.icon || '',
  image: p.image || '',
  // 状态
  visible: p.visible !== false,
  locked: p.locked || 0,
  tags: p.tags || [],
  // 连线特有
  lineName: p.lineName || '',
  fromArrow: p.fromArrow || '',
  toArrow: p.toArrow || '',
})
```

Token 预算维持 ~2000 tokens，估算改为 `JSON.stringify(truncatedPens).length > TARGET_TOKENS * 2.5`（更精确）。

---

## #6 丰富 selection 上下文

**文件**: `web/src/components/AgentPanel/index.vue` — lines 90-96

### 当前:

```typescript
presetInput = `请帮我分析这个节点: ID=${pen.id}, 类型=${pen.name || 'unknown'}, 文字="${(pen.text || '').slice(0, 100)}", 位置=(${pen.x}, ${pen.y}), 大小=${pen.width}x${pen.height}`;
```

### 扩展后:

```typescript
function buildPenContext(pen: any): string {
  const parts: string[] = [
    `选中节点:`,
    `ID=${pen.id}`,
    `类型=${pen.name || 'unknown'}`,
  ]
  if (pen.text) parts.push(`文字="${pen.text.slice(0, 100)}"`)
  parts.push(
    `位置=(${pen.x}, ${pen.y})`,
    `大小=${pen.width}x${pen.height}`,
    `背景色=${pen.background || '默认'}`,
    `文字色=${pen.color || '默认'}`,
  )
  if (pen.fontFamily) parts.push(`字体=${pen.fontFamily} ${pen.fontSize || 14}px`)
  if (pen.fontWeight) parts.push(`粗细=${pen.fontWeight}`)
  if (pen.textAlign && pen.textAlign !== 'center') parts.push(`对齐=${pen.textAlign}`)
  if (pen.borderRadius) parts.push(`圆角=${pen.borderRadius}px`)
  if (pen.borderColor) parts.push(`边框色=${pen.borderColor}`)
  if (pen.lineDash) parts.push(`虚线=${pen.lineDash.join(',')}`)
  if (pen.icon) parts.push(`图标=${pen.icon}`)
  if (pen.image) parts.push(`图片=有`)
  if (pen.shadowColor) parts.push(`阴影=有`)
  if (pen.gradientColors) parts.push(`渐变=有`)
  if (pen.locked) parts.push('【已锁定】')
  if (pen.tags?.length) parts.push(`标签=${pen.tags.join(', ')}`)
  return parts.join('，')
}

presetInput = `请帮我分析这个节点: ${buildPenContext(pen)}`
```

---

## #7 增强 Meta2D API 调用

**文件**: `web/src/utils/canvasBridge.ts`

### 7a. Bulk setValue 支持

`_updatePen` 改为接受可选的多 pen 批量更新：

```typescript
function _updatePen(meta2d, args, success, _result): boolean {
  // 支持单 pen (pen_id) 或批量 (updates: [{pen_id, props}])
  const updates = args.updates || [{ pen_id: args.pen_id, props: args.props }]
  pushUndoState(meta2d)
  for (const u of updates) {
    meta2d.setValue({ id: u.pen_id, ...u.props }, { render: false })
  }
  meta2d.render()
  return true
}
```

### 7b. notifyCanvasMutation debounce

```typescript
let _mutationTimer: ReturnType<typeof setTimeout> | null = null

function notifyCanvasMutation(): void {
  if (_mutationTimer) clearTimeout(_mutationTimer)
  _mutationTimer = setTimeout(() => {
    const meta2d = getMeta2d()
    if (!meta2d) return
    try {
      const data = meta2d.data()
      if (data) localStorage.setItem('meta2d', JSON.stringify(data))
    } catch { /* ignore */ }
    window.dispatchEvent(new CustomEvent('meta2d:agent-mutation'))
    _mutationTimer = null
  }, 100)
}
```

### 7c. 新增操作的 Meta2D 实现

| Action | Meta2D API 调用 |
|--------|----------------|
| `lock` | `meta2d.setValue({id, locked: 2})` × N，批量 render |
| `unlock` | `meta2d.setValue({id, locked: 0})` × N，批量 render |
| `toggle_visibility` | `meta2d.setValue({id, visible})` × N，批量 render |
| `duplicate` | `meta2d.copy(pens)` + `meta2d.paste()` + setValue 偏移 |
| `move_pen` | `meta2d.setValue({id, x, y})` × N，批量 render |
| `group` | `meta2d.combine(pens)` |
| `ungroup` | `meta2d.uncombine(pen)` |
| `canvas_props` | `meta2d.setValue` 设置 data 级属性 |
| `fit_view` | `meta2d.fitView(fit, padding)` |

### 7d. 错误处理

所有操作添加统一的 try-catch 和 console.warn：

```typescript
try {
  // operation
  return true
} catch (e) {
  console.warn(`[canvasBridge] ${action} failed:`, e)
  return false
}
```

---

## 涉及文件清单

| 文件 | 改动类型 |
|------|---------|
| `web/src/composables/useAgentChat.ts` | #1 修复 lines, #5 扩展 context |
| `web/src/utils/canvasBridge.ts` | #2 扩展 PenData, #4 移除 penIdMap, #7 API 增强 |
| `app/util/agent/tools/canvas.py` | #3 扩展工具, #4 UUID |
| `web/src/components/AgentPanel/index.vue` | #6 扩展 selection 上下文 |

---

## 向后兼容性

- #4 UUID 策略：不再需要 `penIdMap`，但 localStorage 中已创建的图元使用 Meta2D 原 ID，不受影响
- #2 PenData 扩展：新增属性都是 optional，旧代码只传基础属性仍然工作
- #3 工具扩展：纯新增 action，不影响现有调用
- 不涉及 API 接口变更、数据库 schema 变更
