# Agent & Canvas 自动化优化 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 P0→P1→P2 顺序实施 11 项自动化优化，覆盖可靠性修复、智能度提升和新能力扩展。

**Architecture:** 从最小改动的 P0-3 热身开始，依次推进 Blueprint 保存原子化、CanvasShadow 状态追踪基础设施，然后基于 shadow 做工具统一化等 P1 改造，最后加 P2 新功能。

**Tech Stack:** Python 3 (Flask, Redis, MySQL), TypeScript (Vue 3, Meta2d)

---

## 执行顺序与依赖

```
Phase 0: P0-3 (独立, 15行) → 热身
Phase 1: P0-1 (80行) → 修保存链路
Phase 2: P0-2 (200行) → CanvasShadow 基础设施
Phase 3: P1-1 (350行) → 工具统一化 (依赖 shadow)
Phase 4: P1-2 (50行) → 上下文截断 (独立)
Phase 5: P1-3 (90行) → Feedback 隔离 (独立)
Phase 6: P1-4 (40行) → 缓存版本化 (依赖 shadow)
Phase 7: P2-2 (120行) → 版本回滚 (复用 shadow snapshot)
Phase 8: P2-3 (240行) → 布局增强 (独立)
Phase 9: P2-1 (350行) → 操作宏 (独立)
Phase 10: P2-4 (300行) → 跨蓝图 (独立)
```

---

### Task 1: P0-3 — CanvasAgent 工具补齐

**Files:**
- Modify: `app/util/agent/agents/canvas_agent.py`

- [ ] **Step 1: Update CANVAS_TOOLS list**

Replace line 7-13 in `canvas_agent.py`:

```python
CANVAS_TOOLS = [
    "canvas",
    "canvas_check_empty",
    "layout_auto_arrange",
    "layout_align",
    "canvas_props",
    "fit_view",
    "blueprint_save",
]
```

- [ ] **Step 2: Update system_prompt to describe new tools**

Replace the `## 核心工具` section (lines 35-46) in the system_prompt string:

```python
## 核心工具
- canvas: 统一画布操作工具，通过 action 参数切换：
  - action="add_pen": 创建图形 (需 type, x, y, text 等)
  - action="add_line": 创建连线 (需 from_pen, to_pen 等)
  - action="add_diagram": 批量创建完整图表 (推荐用于流程图/架构图/思维导图)
  - action="update_pen": 修改图形 (需 pen_id, props)
  - action="delete_pen": 删除图形 (需 pen_id 或 pen_ids)
  - action="get_state": 获取画布状态
  - action="undo"/"redo"/"clear": 撤销/重做/清空
  - action="duplicate"/"move_pen"/"group"/"ungroup"/"lock"/"unlock"/"toggle_visibility": 高级操作
- canvas_check_empty: 线程安全检查画布是否为空
- layout_auto_arrange: 自动排版
- layout_align: 对齐图形
- canvas_props: 设置画布属性（背景色/网格/标尺/默认样式等）
- fit_view: 自适应视口，将所有图形缩放到适合视窗的大小
- blueprint_save: 保存蓝图
```

- [ ] **Step 3: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.agents.canvas_agent import CanvasAgent; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/util/agent/agents/canvas_agent.py
git commit -m "fix: add canvas_props and fit_view to CanvasAgent tool set

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: P0-1 — Blueprint 保存原子化

**Files:**
- Modify: `web/src/composables/useAgentChat.ts`
- Modify: `web/src/api/agent.ts`
- Modify: `app/api/v1/agent.py`
- Modify: `app/util/agent/core.py`
- Modify: `app/util/agent/tools/blueprint.py`
- Modify: `web/src/views/chat/index.vue`

- [ ] **Step 1: Add canvas_snapshot to buildCanvasContext return value**

In `useAgentChat.ts`, after the `buildCanvasContext()` function (line 224), add a new exported function:

```typescript
/** Build a lightweight pens snapshot for blueprint_save atomicity. */
export function buildCanvasSnapshot(): any[] | null {
  try {
    const meta2d = (window as any).meta2d
    if (!meta2d || typeof meta2d.data !== 'function') return null
    const data = meta2d.data()
    if (!data) return null
    return (data.pens || []).map((p: any) => ({
      id: p.id || p.penId,
      type: p.name || p.type || 'rectangle',
      text: (p.text || '').slice(0, 500),
      x: p.x || 0, y: p.y || 0,
      width: p.width || 100, height: p.height || 60,
      background: p.background || '',
      color: p.color || '',
      borderColor: p.borderColor || '',
      borderRadius: p.borderRadius,
      fontSize: p.fontSize,
      fontFamily: p.fontFamily,
      fontWeight: p.fontWeight,
      textAlign: p.textAlign,
      icon: p.icon || '',
      image: p.image || '',
      visible: p.visible !== false,
      locked: p.locked || 0,
      tags: p.tags || [],
    }))
  } catch {
    return null
  }
}
```

- [ ] **Step 2: Call buildCanvasSnapshot and pass it in the send function**

In `useAgentChat.ts`, find the `send()` function's agentChat call (~line 706). Add canvasSnapshot:

```typescript
const canvasContext = options.getCanvasContext
  ? options.getCanvasContext()
  : buildCanvasContext()

const canvasSnapshot = options.getCanvasContext
  ? null  // custom getter doesn't support snapshot
  : buildCanvasSnapshot()

abortCtrl = agentChat({
  userMessage: apiText,
  user_id: options.userId,
  canvasContext,
  canvasSnapshot,  // ← new field
  images: images || undefined,
  // ...
})
```

- [ ] **Step 3: Update agentChat API function to accept canvasSnapshot**

In `web/src/api/agent.ts`, find the `AgentChatOptions` interface (~line 15-40) and add:

```typescript
export interface AgentChatOptions {
  // ... existing fields ...
  canvasContext?: any
  canvasSnapshot?: any[] | null  // ← new field
}
```

In the `agentChat` function body, add to the POST data:

```typescript
const postData: any = {
  // ... existing fields ...
  canvas_context: options.canvasContext,
  canvas_snapshot: options.canvasSnapshot || null,  // ← new field
}
```

- [ ] **Step 4: Pass canvas_snapshot through the API endpoint**

In `app/api/v1/agent.py`, find the `agent_chat()` function (~line 36). Add snapshot extraction:

```python
canvas_context = data.get("canvas_context")
canvas_snapshot = data.get("canvas_snapshot")  # ← new line
```

Then in the AgentSession.chat_v3() call (~line 79), add the parameter:

```python
canvas_context=canvas_context,
canvas_snapshot=canvas_snapshot,  # ← new line
```

- [ ] **Step 5: Thread canvas_snapshot through AgentSession**

In `app/util/agent/core.py`, find the `chat_v3()` method signature and add `canvas_snapshot` parameter. Then in the `tool_ctx` dict construction, add:

```python
tool_ctx = {
    # ... existing fields ...
    "canvas_snapshot": canvas_snapshot or [],  # ← new line
}
```

- [ ] **Step 6: Update _tool_blueprint_save to use canvas_snapshot**

In `app/util/agent/tools/blueprint.py`, find `_tool_blueprint_save`. Replace the pens handling logic. Read the file first to find the exact function, then update it to:

```python
def _tool_blueprint_save(args, tool_ctx=None):
    name = args.get("name", "")
    desc = args.get("description", "")
    category = args.get("category", "")
    blueprint_id = args.get("id")

    if not name:
        return {"success": False, "error": "name 不能为空，请提供图纸名称"}

    handler = BlueprintMysqlHandler()

    # Get pens from canvas_snapshot if available (atomic save)
    canvas_snapshot = (tool_ctx or {}).get("canvas_snapshot") or []
    pens_data = json.dumps(canvas_snapshot) if canvas_snapshot else None

    if blueprint_id:
        # Update existing
        result = handler.update(blueprint_id, name=name, description=desc,
                                category=category, pens=pens_data)
        return {"success": True, "data": {"id": blueprint_id, "name": name},
                "message": f"已更新图纸「{name}」"}
    else:
        # Create new
        new_id = handler.create(name=name, description=desc,
                                category=category, pens=pens_data or "[]")
        return {"success": True, "data": {"id": new_id, "name": name},
                "message": f"已保存图纸「{name}」(ID: {new_id})"}
```

- [ ] **Step 7: Remove post-hoc blueprint_save patch from chat view**

In `web/src/views/chat/index.vue`, search for `blueprint_save` in the handleSSEEvent or onToolResult handler. Remove the logic that reads `localStorage['meta2d']` and calls `apiBlueprintModify()` after a `blueprint_save` tool result.

- [ ] **Step 8: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools.blueprint import TOOL_SCHEMAS; print('OK')"
```

- [ ] **Step 9: Commit**

```bash
git add web/src/composables/useAgentChat.ts web/src/api/agent.ts app/api/v1/agent.py app/util/agent/core.py app/util/agent/tools/blueprint.py web/src/views/chat/index.vue
git commit -m "fix: make blueprint_save atomic with canvas_snapshot injection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: P0-2 — CanvasShadow 画布状态跨轮次追踪

**Files:**
- Create: `app/util/agent/canvas_shadow.py`
- Modify: `app/util/agent/tools/canvas.py` (later replaced in P1-1, but for now patch in shadow writes)
- Modify: `app/util/agent/core.py`
- Modify: `app/util/agent/state_store.py`

- [ ] **Step 1: Create CanvasShadow module**

Create `app/util/agent/canvas_shadow.py`:

```python
# -*- coding: UTF-8 -*-
"""CanvasShadow — 后端画布影子状态，支持跨轮次 ID 校验和状态追踪。"""

import json
import logging
import time
from dataclasses import dataclass, field


@dataclass
class PenShadow:
    """轻量 pen 影子记录。"""
    pen_id: str
    type: str = "rectangle"
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 60.0

    def to_dict(self) -> dict:
        return {
            "pen_id": self.pen_id, "type": self.type, "text": self.text,
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PenShadow":
        return cls(
            pen_id=d.get("pen_id", d.get("id", "")),
            type=d.get("type", "rectangle"),
            text=d.get("text", ""),
            x=d.get("x", 0), y=d.get("y", 0),
            width=d.get("width", 100), height=d.get("height", 60),
        )


@dataclass
class LineShadow:
    """轻量 line 影子记录。"""
    from_pen: str
    to_pen: str
    line_id: str = ""

    def to_dict(self) -> dict:
        return {"from_pen": self.from_pen, "to_pen": self.to_pen, "line_id": self.line_id}

    @classmethod
    def from_dict(cls, d: dict) -> "LineShadow":
        return cls(
            from_pen=d.get("from_pen", d.get("from", "")),
            to_pen=d.get("to_pen", d.get("to", "")),
            line_id=d.get("line_id", ""),
        )


@dataclass
class CanvasShadow:
    """画布影子状态 — 后端维护的轻量画布模型。"""
    pens: dict = field(default_factory=dict)    # pen_id → PenShadow
    lines: dict = field(default_factory=dict)   # line_id (or composite key) → LineShadow
    version: int = 0
    last_sync_at: float = 0.0

    # ── Pen 操作 ──

    def add_pen(self, pen_id: str, pen_data: dict):
        self.pens[pen_id] = PenShadow(
            pen_id=pen_id,
            type=pen_data.get("type", "rectangle"),
            text=pen_data.get("text", ""),
            x=pen_data.get("x", 0), y=pen_data.get("y", 0),
            width=pen_data.get("width", 100), height=pen_data.get("height", 60),
        )
        self.version += 1

    def has_pen(self, pen_id: str) -> bool:
        return pen_id in self.pens

    def remove_pen(self, pen_id: str):
        if pen_id in self.pens:
            del self.pens[pen_id]
            # Also remove lines connected to this pen
            self.lines = {k: v for k, v in self.lines.items()
                          if v.from_pen != pen_id and v.to_pen != pen_id}
            self.version += 1

    def clear(self):
        self.pens.clear()
        self.lines.clear()
        self.version += 1

    # ── Sync ──

    def sync_from_snapshot(self, snapshot: list[dict]):
        """全量同步：用前端快照替换 shadow 中的 pens/lines。保留 version 用于冲突检测。"""
        incoming_ids = set()
        for p in snapshot:
            pid = p.get("id", p.get("pen_id", ""))
            if not pid:
                continue
            incoming_ids.add(pid)
            if pid in self.pens:
                # Update existing
                existing = self.pens[pid]
                existing.text = p.get("text", existing.text)
                existing.x = p.get("x", existing.x)
                existing.y = p.get("y", existing.y)
                existing.width = p.get("width", existing.width)
                existing.height = p.get("height", existing.height)
            else:
                self.pens[pid] = PenShadow.from_dict(p)
        # Remove pens not in snapshot (user deleted them manually)
        removed = [pid for pid in self.pens if pid not in incoming_ids]
        for pid in removed:
            del self.pens[pid]
        if removed:
            self.version += 1

    def to_dict(self) -> dict:
        return {
            "pens": {k: v.to_dict() for k, v in self.pens.items()},
            "lines": {k: v.to_dict() for k, v in self.lines.items()},
            "version": self.version,
            "last_sync_at": self.last_sync_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CanvasShadow":
        shadow = cls(version=d.get("version", 0), last_sync_at=d.get("last_sync_at", 0))
        for k, v in d.get("pens", {}).items():
            shadow.pens[k] = PenShadow.from_dict(v)
        for k, v in d.get("lines", {}).items():
            shadow.lines[k] = LineShadow.from_dict(v)
        return shadow


# ── Redis persistence ──

_CANVAS_SHADOW_TTL = 1800  # 30 minutes


def _get_shadow_redis():
    try:
        from app.util.redis_utils import get_redis
        return get_redis(db=5)
    except Exception:
        return None


def load_canvas_shadow(session_id: str) -> CanvasShadow:
    """Load CanvasShadow from Redis, or return empty shadow."""
    r = _get_shadow_redis()
    if r:
        try:
            key = f"canvas_shadow:{session_id}"
            raw = r.get(key)
            if raw:
                data = json.loads(raw) if isinstance(raw, bytes) else json.loads(raw)
                return CanvasShadow.from_dict(data)
        except Exception:
            logging.warning("CanvasShadow load failed for session %s", session_id)
    return CanvasShadow()


def save_canvas_shadow(session_id: str, shadow: CanvasShadow):
    """Persist CanvasShadow to Redis."""
    shadow.last_sync_at = time.time()
    r = _get_shadow_redis()
    if r:
        try:
            key = f"canvas_shadow:{session_id}"
            r.setex(key, _CANVAS_SHADOW_TTL,
                    json.dumps(shadow.to_dict(), ensure_ascii=False))
        except Exception:
            logging.warning("CanvasShadow save failed for session %s", session_id)
```

- [ ] **Step 2: Integrate CanvasShadow into AgentSession.chat_v3**

In `app/util/agent/core.py`, find `chat_v3()`. After the existing state loading code, add:

```python
from app.util.agent.canvas_shadow import load_canvas_shadow, save_canvas_shadow

# Load canvas shadow for cross-turn state tracking
canvas_shadow = load_canvas_shadow(session_id)

# Sync from snapshot if available (frontend sent fresh state)
canvas_snapshot = kwargs.get("canvas_snapshot") or tool_ctx.get("canvas_snapshot") or []
if canvas_snapshot:
    canvas_shadow.sync_from_snapshot(canvas_snapshot)

# Inject into tool_ctx
tool_ctx["canvas_shadow"] = canvas_shadow
```

After the engine.chat() call completes, persist the shadow:

```python
# Save canvas shadow after execution
save_canvas_shadow(session_id, canvas_shadow)
```

- [ ] **Step 3: Patch canvas tool to update shadow on write operations**

In `app/util/agent/tools/canvas.py`, `_tool_canvas()`, add shadow writes at the end of each write action. After the existing `return` for `add_pen`:

```python
if action == "add_pen":
    pen_id = _new_pen_id()
    # ... existing logic ...
    # Update shadow
    shadow = args.get("_canvas_shadow")
    if shadow:
        shadow.add_pen(pen_id, args)
    return {...}
```

Similarly add for `delete_pen`, `clear`, `add_diagram`, `update_pen`, `duplicate`, `move_pen`, `group`, `ungroup`. Example for `delete_pen`:

```python
elif action == "delete_pen":
    pen_ids = _resolve_pen_ids(args)
    # ... existing validation ...
    shadow = args.get("_canvas_shadow")
    if shadow:
        for pid in pen_ids:
            shadow.remove_pen(pid)
    return {...}
```

Add ID validation for `add_line`:

```python
elif action == "add_line":
    from_pen = args.get("from_pen", "")
    to_pen = args.get("to_pen", "")
    shadow = args.get("_canvas_shadow")
    if shadow:
        if from_pen and not shadow.has_pen(from_pen):
            return {"success": False, "error": f"from_pen '{from_pen}' 不存在，可能已被删除"}
        if to_pen and not shadow.has_pen(to_pen):
            return {"success": False, "error": f"to_pen '{to_pen}' 不存在，可能已被删除"}
    # ... existing logic ...
```

- [ ] **Step 4: Thread canvas_shadow through tool_ctx to args in executor.py**

In `app/util/agent/executor.py`, find where tool args are prepared and inject `_canvas_shadow`:

```python
# In _run_simple_tool or equivalent, before calling tool function:
if "canvas_shadow" in tool_ctx:
    args["_canvas_shadow"] = tool_ctx["canvas_shadow"]
```

- [ ] **Step 5: Verify syntax and import**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.canvas_shadow import CanvasShadow, load_canvas_shadow, save_canvas_shadow; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add app/util/agent/canvas_shadow.py app/util/agent/core.py app/util/agent/tools/canvas.py app/util/agent/executor.py
git commit -m "feat: add CanvasShadow for cross-turn canvas state tracking

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: P1-1 — 画布工具统一化（方案 B）

**Files:**
- Create: `app/util/agent/tools/canvas/__init__.py`
- Create: `app/util/agent/tools/canvas/_base.py`
- Create: `app/util/agent/tools/canvas/edit.py`
- Create: `app/util/agent/tools/canvas/organize.py`
- Create: `app/util/agent/tools/canvas/view.py`
- Modify: `app/util/agent/tools/canvas.py` (mark deprecated)
- Modify: `app/util/agent/tools/__init__.py`
- Modify: `app/util/agent/tool_router.py`
- Modify: `web/src/utils/canvasBridge.ts`
- Modify: `app/util/agent/agents/canvas_agent.py`

- [ ] **Step 1: Create _base.py — shared utilities**

Create `app/util/agent/tools/canvas/_base.py`:

```python
# -*- coding: UTF-8 -*-
"""Shared utilities for canvas tool package."""
import uuid


def new_pen_id() -> str:
    """Generate a unique pen ID using UUID4 (12 hex chars)."""
    return uuid.uuid4().hex[:12]


def resolve_pen_ids(args: dict) -> list:
    """Extract pen_ids from args, supporting single pen_id or list of pen_ids."""
    pen_ids = args.get("pen_ids", [])
    if not pen_ids and args.get("pen_id"):
        pen_ids = [args.get("pen_id")]
    return pen_ids


def get_shadow(args: dict):
    """Get CanvasShadow from tool args if available."""
    return args.get("_canvas_shadow")
```

- [ ] **Step 2: Create edit.py — canvas_edit tool (11 actions)**

Create `app/util/agent/tools/canvas/edit.py`:

```python
# -*- coding: UTF-8 -*-
"""canvas_edit — 图形增删改操作。"""
from app.util.tool_registry import ToolRegistry
from app.util.agent.tools.canvas._base import new_pen_id, resolve_pen_ids, get_shadow

EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["add_pen", "add_line", "add_diagram", "update_pen",
                     "delete_pen", "duplicate", "move_pen", "undo", "redo",
                     "clear", "get_state"],
            "description": "操作类型",
        },
        # add_pen params
        "type": {"type": "string", "description": "[add_pen/add_diagram.nodes] 图形类型: rectangle/circle/triangle/diamond/pentagon/star/text/image"},
        "text": {"type": "string", "description": "[add_pen/add_line/update_pen] 文字内容"},
        "x": {"type": "number", "description": "[add_pen] X坐标", "default": 0},
        "y": {"type": "number", "description": "[add_pen] Y坐标", "default": 0},
        "width": {"type": "number", "description": "[add_pen] 宽度(px)", "default": 100},
        "height": {"type": "number", "description": "[add_pen] 高度(px)", "default": 60},
        "background": {"type": "string", "description": "[add_pen] 背景颜色(#RRGGBB)"},
        "color": {"type": "string", "description": "[add_pen/add_line] 颜色(#RRGGBB)"},
        "fontSize": {"type": "number", "description": "[add_pen] 文字大小(px)"},
        "borderWidth": {"type": "number", "description": "[add_pen] 边框宽度(px)"},
        "borderColor": {"type": "string", "description": "[add_pen] 边框颜色(#RRGGBB)"},
        "borderRadius": {"type": "number", "description": "[add_pen] 圆角半径(px)"},
        "icon": {"type": "string", "description": "[add_pen] 图标unicode或名称"},
        "iconFamily": {"type": "string", "description": "[add_pen] 图标字体家族"},
        "iconSize": {"type": "number", "description": "[add_pen] 图标大小(px)"},
        "iconColor": {"type": "string", "description": "[add_pen] 图标颜色(#RRGGBB)"},
        "image": {"type": "string", "description": "[add_pen] 图片URL"},
        "visible": {"type": "boolean", "description": "[add_pen] 是否可见"},
        "locked": {"type": "number", "description": "[add_pen] 锁定状态: 0=正常, 1=禁编辑, 2=禁移动"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "[add_pen] 标签列表"},
        # add_line params
        "from_pen": {"type": "string", "description": "[add_line/add_diagram.edges] 起始节点ID"},
        "to_pen": {"type": "string", "description": "[add_line/add_diagram.edges] 目标节点ID"},
        "line_type": {"type": "string", "enum": ["straight", "curve", "polyline", "mind"],
                      "description": "[add_line] 连线类型", "default": "straight"},
        "arrow": {"type": "string", "enum": ["start", "end", "both", "none"],
                  "description": "[add_line] 箭头方向", "default": "end"},
        "lineWidth": {"type": "number", "description": "[add_line] 连线宽度(px)"},
        # add_diagram params
        "diagram": {
            "type": "object",
            "description": "[add_diagram] 图表定义, 含 nodes 数组和 edges 数组",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object"},
                          "description": "节点列表, 每个节点有 id/type/text/x/y/width/height"},
                "edges": {"type": "array", "items": {"type": "object"},
                          "description": "连线列表, 每条线有 from/to/text/line_type/arrow"},
            },
        },
        # update_pen / delete_pen params
        "pen_id": {"type": "string", "description": "[update_pen/delete_pen] 图形ID"},
        "pen_ids": {"type": "array", "items": {"type": "string"},
                    "description": "[delete_pen] 批量删除的图形ID列表"},
        "props": {"type": "object", "description": '[update_pen] 要修改的属性键值对, 如 {"x":100,"text":"新文字"}'},
        # clear param
        "confirm": {"type": "boolean", "description": "[clear] 确认清空画布"},
        # duplicate params
        "offset_x": {"type": "number", "description": "[duplicate] 复制后的X偏移(px)", "default": 30},
        "offset_y": {"type": "number", "description": "[duplicate] 复制后的Y偏移(px)", "default": 30},
        # move_pen params
        "moves": {
            "type": "array",
            "items": {"type": "object", "properties": {
                "pen_id": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}
            }},
            "description": "[move_pen] 批量移动列表, 每项含 pen_id/x/y",
        },
    },
    "required": ["action"],
}


@ToolRegistry.register(
    "canvas_edit",
    "画布图形编辑: 创建、修改、删除图形和连线。"
    "action: add_pen(创建图形), add_line(连线), add_diagram(批量图表), "
    "update_pen(修改属性), delete_pen(删除), duplicate(复制), move_pen(移动), "
    "undo(撤销), redo(重做), clear(清空), get_state(查看画布状态)",
    EDIT_SCHEMA,
)
def _tool_canvas_edit(args):
    action = args.get("action", "")
    if not action:
        return {"success": False, "error": "缺少必填参数: action"}

    shadow = get_shadow(args)

    if action == "add_pen":
        pen_id = new_pen_id()
        pen_type = args.get("type", "rectangle")
        text = args.get("text", "")
        x, y = args.get("x", 0), args.get("y", 0)
        w, h = args.get("width", 100), args.get("height", 60)
        label = f"「{text}」" if text else ""
        if shadow:
            shadow.add_pen(pen_id, args)
        return {
            "success": True, "pen_id": pen_id,
            "data": {"pen_id": pen_id, "type": pen_type, "text": text, "x": x, "y": y, "width": w, "height": h},
            "message": f"已创建{pen_type}{label}，位置({x}, {y})，大小 {w}x{h}，ID: {pen_id}",
        }

    elif action == "add_line":
        from_pen = args.get("from_pen", "")
        to_pen = args.get("to_pen", "")
        if not from_pen or not to_pen:
            return {"success": False, "error": "from_pen 和 to_pen 不能为空"}
        if shadow:
            if not shadow.has_pen(from_pen):
                return {"success": False, "error": f"from_pen '{from_pen}' 不存在"}
            if not shadow.has_pen(to_pen):
                return {"success": False, "error": f"to_pen '{to_pen}' 不存在"}
        line_type = args.get("line_type", "straight")
        label = f"「{args.get('text')}」" if args.get("text") else ""
        return {
            "success": True,
            "data": {"from_pen": from_pen, "to_pen": to_pen, "line_type": line_type, "text": args.get("text", "")},
            "message": f"已创建从 {from_pen} 到 {to_pen} 的{line_type}连线{label}",
        }

    elif action == "add_diagram":
        diagram = args.get("diagram", {})
        nodes = diagram.get("nodes", [])
        edges = diagram.get("edges", [])
        if not nodes:
            return {"success": False, "error": "diagram.nodes 不能为空"}
        id_map = {}
        node_summaries = []
        for node in nodes:
            logical_id = node.get("id", "")
            pen_id = new_pen_id()
            node["pen_id"] = pen_id
            if logical_id:
                id_map[logical_id] = pen_id
            node_summaries.append(f"{node.get('type', 'rectangle')}({pen_id})")
            if shadow:
                shadow.add_pen(pen_id, node)
        for edge in edges:
            from_ref = edge.get("from", "")
            to_ref = edge.get("to", "")
            edge["_from_id"] = id_map.get(from_ref, from_ref)
            edge["_to_id"] = id_map.get(to_ref, to_ref)
        return {
            "success": True,
            "data": {"diagram": {"nodes": nodes, "edges": edges}},
            "message": f"已生成包含 {len(nodes)} 个节点和 {len(edges)} 条连线的图表",
        }

    elif action == "update_pen":
        pen_id = args.get("pen_id", "")
        if not pen_id:
            return {"success": False, "error": "pen_id 不能为空"}
        props = args.get("props", {})
        if not props:
            return {"success": False, "error": "props 不能为空"}
        if shadow and not shadow.has_pen(pen_id):
            return {"success": False, "error": f"pen '{pen_id}' 不存在"}
        props_desc = ", ".join(f"{k}={v}" for k, v in props.items())
        return {
            "success": True, "data": {"pen_id": pen_id, "props": props},
            "message": f"已更新图形 {pen_id}：{props_desc}",
        }

    elif action == "delete_pen":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        if shadow:
            for pid in pen_ids:
                shadow.remove_pen(pid)
        return {
            "success": True, "data": {"pen_ids": pen_ids},
            "message": f"已删除 {len(pen_ids)} 个图形",
        }

    elif action == "clear":
        if not args.get("confirm"):
            return {"success": False, "error": "清空画布不可逆，请设置 confirm=true 确认"}
        if shadow:
            shadow.clear()
        return {"success": True, "data": {}, "message": "画布已清空"}

    elif action == "undo":
        return {"success": True, "data": {}, "message": "已撤销上一步操作"}

    elif action == "redo":
        return {"success": True, "data": {}, "message": "已恢复撤销的操作"}

    elif action == "duplicate":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        ox, oy = args.get("offset_x", 30), args.get("offset_y", 30)
        new_ids = [new_pen_id() for _ in pen_ids]
        if shadow:
            for pid, nid in zip(pen_ids, new_ids):
                if shadow.has_pen(pid):
                    orig = shadow.pens[pid]
                    shadow.add_pen(nid, {"type": orig.type, "text": orig.text,
                                         "x": orig.x + ox, "y": orig.y + oy,
                                         "width": orig.width, "height": orig.height})
        return {
            "success": True, "data": {"original_ids": pen_ids, "new_ids": new_ids, "offset_x": ox, "offset_y": oy},
            "message": f"已复制 {len(pen_ids)} 个图形，新ID：{', '.join(new_ids)}",
        }

    elif action == "move_pen":
        moves = args.get("moves", [])
        if not moves:
            return {"success": False, "error": 'moves 不能为空'}
        return {"success": True, "data": {"moves": moves}, "message": f"已移动 {len(moves)} 个图形"}

    elif action == "get_state":
        ctx = args.get("_canvas_context") or {}
        pens = ctx.get("pens", [])
        lines = ctx.get("lines", [])
        if not ctx:
            return {
                "success": True,
                "data": {"pens": [], "lines": [], "empty": True, "canvas_available": False},
                "message": "无法获取画布状态（用户可能不在画布页面），画布视为空。直接调用 canvas_edit(action='clear', confirm=true) 清空画布后绘制。",
            }
        return {
            "success": True,
            "data": {
                "pens": [{"pen_id": p.get("id", p.get("penId", "")),
                          "type": p.get("name", p.get("type", "rectangle")),
                          "text": p.get("text", ""), "x": p.get("x", 0), "y": p.get("y", 0)}
                         for p in pens],
                "lines": [{"from": l.get("fromPen", l.get("source", "")),
                           "to": l.get("toPen", l.get("connectTo", "")), "text": l.get("text", "")}
                          for l in lines],
                "pen_count": len(pens), "line_count": len(lines),
                "empty": len(pens) == 0 and len(lines) == 0,
            },
            "message": f"画布当前有 {len(pens)} 个图形和 {len(lines)} 条连线",
        }

    return {"success": False, "error": f"未知的 action: {action}"}
```

- [ ] **Step 3: Create organize.py — canvas_organize tool (7 actions)**

Create `app/util/agent/tools/canvas/organize.py`:

```python
# -*- coding: UTF-8 -*-
"""canvas_organize — 图形组织与布局。"""
from app.util.tool_registry import ToolRegistry
from app.util.agent.tools.canvas._base import resolve_pen_ids, get_shadow

ORGANIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["group", "ungroup", "lock", "unlock", "toggle_visibility",
                     "auto_arrange", "align"],
            "description": "操作类型",
        },
        "pen_id": {"type": "string", "description": "[ungroup] 组合ID"},
        "pen_ids": {"type": "array", "items": {"type": "string"},
                    "description": "[group/lock/unlock/toggle_visibility] 图形ID列表"},
        "visible": {"type": "boolean", "description": "[toggle_visibility] 是否可见"},
        # auto_arrange params
        "direction": {"type": "string", "enum": ["horizontal", "vertical", "grid"],
                      "description": "[auto_arrange] 排列方向", "default": "vertical"},
        "spacing": {"type": "number", "description": "[auto_arrange] 间距(px)", "default": 40},
        "columns": {"type": "integer", "description": "[auto_arrange] 网格列数(grid模式)", "default": 3},
        # align params
        "align": {"type": "string", "enum": ["left", "center", "right", "top", "middle", "bottom"],
                  "description": "[align] 对齐方式"},
        # layout algorithm
        "algorithm": {"type": "string", "enum": ["grid", "tree", "force", "layered"],
                      "description": "[auto_arrange] 布局算法 (P2-3)", "default": "grid"},
        "root_pen_id": {"type": "string", "description": "[auto_arrange] tree布局的根节点ID"},
    },
    "required": ["action"],
}


@ToolRegistry.register(
    "canvas_organize",
    "画布图形组织: 编组、锁定、显隐、自动排列、对齐。"
    "action: group(组合), ungroup(取消组合), lock(锁定), unlock(解锁), "
    "toggle_visibility(显隐), auto_arrange(自动排列), align(对齐)",
    ORGANIZE_SCHEMA,
)
def _tool_canvas_organize(args):
    action = args.get("action", "")
    if not action:
        return {"success": False, "error": "缺少必填参数: action"}

    if action == "group":
        pen_ids = resolve_pen_ids(args)
        if len(pen_ids) < 2:
            return {"success": False, "error": "至少需要两个图形才能组合"}
        return {"success": True, "data": {"pen_ids": pen_ids},
                "message": f"已组合 {len(pen_ids)} 个图形"}

    elif action == "ungroup":
        pen_id = args.get("pen_id", "")
        if not pen_id:
            return {"success": False, "error": "pen_id 不能为空"}
        return {"success": True, "data": {"pen_id": pen_id}, "message": f"已取消组合：{pen_id}"}

    elif action == "lock":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {"success": True, "data": {"pen_ids": pen_ids, "locked": 2},
                "message": f"已锁定 {len(pen_ids)} 个图形"}

    elif action == "unlock":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {"success": True, "data": {"pen_ids": pen_ids, "locked": False},
                "message": f"已解锁 {len(pen_ids)} 个图形"}

    elif action == "toggle_visibility":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        visible = args.get("visible", False)
        label = "显示" if visible else "隐藏"
        return {"success": True, "data": {"pen_ids": pen_ids, "visible": visible},
                "message": f"已{label} {len(pen_ids)} 个图形"}

    elif action == "auto_arrange":
        direction = args.get("direction", "vertical")
        spacing = args.get("spacing", 40)
        algorithm = args.get("algorithm", "grid")
        algo_label = f"{algorithm}布局" if algorithm != "grid" else ""
        return {"success": True, "data": args,
                "message": f"已按{direction}方向{algo_label}自动排列，间距{spacing}px"}

    elif action == "align":
        align_mode = args.get("align", "")
        if not align_mode:
            return {"success": False, "error": "align 不能为空"}
        return {"success": True, "data": args, "message": f"已按{align_mode}对齐"}

    return {"success": False, "error": f"未知的 action: {action}"}
```

- [ ] **Step 4: Create view.py — canvas_view tool (3 actions)**

Create `app/util/agent/tools/canvas/view.py`:

```python
# -*- coding: UTF-8 -*-
"""canvas_view — 画布视图、属性与状态检查。"""
from app.util.tool_registry import ToolRegistry

VIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["set_props", "fit_view", "check_empty",
                     "list_snapshots", "restore_snapshot", "save_snapshot"],
            "description": "操作类型",
        },
        # set_props params
        "background": {"type": "string", "description": "[set_props] 画布背景颜色(#RRGGBB)"},
        "bkImage": {"type": "string", "description": "[set_props] 画布背景图片URL"},
        "grid": {"type": "boolean", "description": "[set_props] 是否显示网格"},
        "gridColor": {"type": "string", "description": "[set_props] 网格颜色(#RRGGBB)"},
        "gridSize": {"type": "number", "description": "[set_props] 网格大小(px)"},
        "rule": {"type": "boolean", "description": "[set_props] 是否显示标尺"},
        "ruleColor": {"type": "string", "description": "[set_props] 标尺颜色(#RRGGBB)"},
        "color": {"type": "string", "description": "[set_props] 画布默认文字颜色"},
        "penBackground": {"type": "string", "description": "[set_props] 画布默认图形背景色"},
        # fit_view params
        "fit": {"type": "boolean", "description": "[fit_view] 是否自适应(true=fitView, false=还原100%)", "default": True},
        "padding": {"type": "number", "description": "[fit_view] 内边距(px)", "default": 24},
        # snapshot params
        "version": {"type": "integer", "description": "[restore_snapshot] 要回滚到的版本号"},
        "label": {"type": "string", "description": "[save_snapshot] 快照标签/名称"},
    },
    "required": ["action"],
}


@ToolRegistry.register(
    "canvas_view",
    "画布视图与属性: 设置画布属性(背景/网格/标尺)、适配视口、检查画布状态、快照管理。"
    "action: set_props(设置画布属性), fit_view(适配视口), check_empty(检查是否为空), "
    "list_snapshots(列出快照), restore_snapshot(回滚快照), save_snapshot(保存快照)",
    VIEW_SCHEMA,
)
def _tool_canvas_view(args):
    action = args.get("action", "")
    if not action:
        return {"success": False, "error": "缺少必填参数: action"}

    if action == "set_props":
        props_desc = ", ".join(f"{k}={v}" for k, v in args.items() if k != "action")
        return {"success": True, "data": args, "message": f"画布属性已更新：{props_desc}"}

    elif action == "fit_view":
        fit = args.get("fit", True)
        padding = args.get("padding", 24)
        label = "自适应视口" if fit else "还原100%"
        return {"success": True, "data": {"fit": fit, "padding": padding}, "message": f"已{label}，内边距{padding}px"}

    elif action == "check_empty":
        ctx = args.get("_canvas_context") or {}
        pens = ctx.get("pens", [])
        lines = ctx.get("lines", [])
        if not ctx:
            return {
                "success": True,
                "data": {"empty": True, "pen_count": 0, "line_count": 0, "canvas_available": False},
                "message": "无法获取画布状态（用户可能不在画布页面），假设画布为空。直接绘制即可。",
            }
        empty = len(pens) == 0 and len(lines) == 0
        msg = "画布当前为空，可以自由绘制。" if empty else \
              f"画布当前有 {len(pens)} 个图形和 {len(lines)} 条连线。"
        return {"success": True,
                "data": {"empty": empty, "pen_count": len(pens), "line_count": len(lines), "canvas_available": True},
                "message": msg}

    elif action == "list_snapshots":
        # P2-2: stub for now, returns empty list
        return {"success": True, "data": {"snapshots": []},
                "message": "暂无可用快照。快照功能将在后续版本中启用。"}

    elif action == "restore_snapshot":
        version = args.get("version")
        if version is None:
            return {"success": False, "error": "version 不能为空"}
        # P2-2: stub for now
        return {"success": True, "data": {"version": version},
                "message": f"快照回滚功能将在后续版本中启用（请求版本: {version}）"}

    elif action == "save_snapshot":
        label = args.get("label", "")
        # P2-2: stub for now
        return {"success": True, "data": {"label": label},
                "message": f"快照保存功能将在后续版本中启用"}

    return {"success": False, "error": f"未知的 action: {action}"}
```

- [ ] **Step 5: Create __init__.py — package exports**

Create `app/util/agent/tools/canvas/__init__.py`:

```python
# -*- coding: UTF-8 -*-
"""Canvas tool package — edit, organize, view."""
from app.util.agent.tools.canvas.edit import _tool_canvas_edit
from app.util.agent.tools.canvas.organize import _tool_canvas_organize
from app.util.agent.tools.canvas.view import _tool_canvas_view

__all__ = ["_tool_canvas_edit", "_tool_canvas_organize", "_tool_canvas_view"]
```

- [ ] **Step 6: Update tools/__init__.py to import new package**

In `app/util/agent/tools/__init__.py`, add after existing imports:

```python
# New unified canvas tools (replaces deprecated canvas.py tools)
from app.util.agent.tools.canvas import (  # noqa: F401
    _tool_canvas_edit,
    _tool_canvas_organize,
    _tool_canvas_view,
)
```

- [ ] **Step 7: Mark old canvas.py tools as deprecated**

In `app/util/agent/tools/canvas.py`, add deprecation warnings to `_tool_canvas`, `_tool_layout_auto_arrange`, `_tool_layout_align`, `_tool_canvas_props`, `_tool_fit_view`, `_tool_canvas_check_empty`:

```python
import warnings

# At the top of each tool function:
warnings.warn("canvas tool is deprecated, use canvas_edit/canvas_organize/canvas_view instead",
              DeprecationWarning, stacklevel=2)
```

- [ ] **Step 8: Update tool_router.py domain mapping**

In `app/util/agent/tool_router.py`, replace the canvas domain entry (~line 38):

```python
"canvas": [
    "canvas_edit",
    "canvas_organize",
    "canvas_view",
],
```

- [ ] **Step 9: Update CanvasAgent CANVAS_TOOLS**

In `app/util/agent/agents/canvas_agent.py`, update:

```python
CANVAS_TOOLS = [
    "canvas_edit",
    "canvas_organize",
    "canvas_view",
    "blueprint_save",
]
```

Update the system_prompt's `## 核心工具` section to reference the new tool names.

- [ ] **Step 10: Update frontend canvasBridge.ts**

In `web/src/utils/canvasBridge.ts`, update `executeCanvasTool()` and `executeCanvasToolLocalStorage()` to accept the new tool names:

```typescript
// Add new tool names alongside existing ones
const canvasEditTools = ['canvas', 'canvas_edit']
const canvasOrganizeTools = ['layout_auto_arrange', 'layout_align', 'canvas_organize']
const canvasViewTools = ['canvas_props', 'fit_view', 'canvas_check_empty', 'canvas_view']

function executeCanvasTool(tool: string, args: any, meta2d: any): any {
  // Route all canvas tool names to their handlers
  if (canvasEditTools.includes(tool)) {
    return executeEditAction(args, meta2d)
  }
  if (canvasOrganizeTools.includes(tool)) {
    return executeOrganizeAction(args, meta2d)
  }
  if (canvasViewTools.includes(tool)) {
    return executeViewAction(args, meta2d)
  }
  return null  // not a canvas tool
}
```

- [ ] **Step 11: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools.canvas import _tool_canvas_edit, _tool_canvas_organize, _tool_canvas_view; print('OK')"
```

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools import TOOL_SCHEMAS; names = [s['function']['name'] for s in TOOL_SCHEMAS if 'canvas' in s['function']['name']]; print(names)"
```

Expected: `['canvas_edit', 'canvas_organize', 'canvas_view', 'canvas', 'canvas_check_empty', ...]`

- [ ] **Step 12: Commit**

```bash
git add app/util/agent/tools/canvas/ app/util/agent/tools/canvas.py app/util/agent/tools/__init__.py app/util/agent/tool_router.py app/util/agent/agents/canvas_agent.py web/src/utils/canvasBridge.ts
git commit -m "refactor: unify 6 canvas tools into 3 semantic tools (edit/organize/view)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: P1-2 — 画布上下文语义截断

**Files:**
- Modify: `web/src/composables/useAgentChat.ts`

- [ ] **Step 1: Replace buildCanvasContext with layered budget version**

In `useAgentChat.ts`, replace the `buildCanvasContext()` function (lines 120-224):

```typescript
export function buildCanvasContext(): CanvasContext | null {
  try {
    const meta2d = (window as any).meta2d
    if (!meta2d || typeof meta2d.data !== 'function') return null

    const data = meta2d.data()
    if (!data) return null

    const BUDGET = 2000  // token budget (chars ~= tokens * 2.5 for CJK)

    // Layer 0: Selected pens — MUST be preserved (no token limit)
    const selectedIds = new Set<string>(meta2d.active || [])
    const selectedPens = (data.pens || []).filter((p: any) => selectedIds.has(p.id))

    // Find neighbors of selected pens
    const neighborIds = new Set<string>()
    if (selectedIds.size > 0) {
      for (const line of (data.lines || [])) {
        if (selectedIds.has(line.source?.id)) neighborIds.add(line.source?.connectTo)
        if (selectedIds.has(line.target?.id)) neighborIds.add(line.target?.connectTo)
        if (line.source?.connectTo && selectedIds.has(line.source.connectTo)) neighborIds.add(line.source.id)
      }
    }

    // Layer 1: Neighbors of selected pens (max 40% of budget)
    const neighborPens = (data.pens || []).filter(
      (p: any) => neighborIds.has(p.id) && !selectedIds.has(p.id)
    )

    // Layer 2: Pens with meaningful text content (max 30% of budget)
    const withTextPens = (data.pens || []).filter(
      (p: any) => (p.text || '').trim().length > 0
        && !selectedIds.has(p.id) && !neighborIds.has(p.id)
    )

    // Layer 3: Rest of pens (fill remaining budget)
    const restPens = (data.pens || []).filter(
      (p: any) => !selectedIds.has(p.id) && !neighborIds.has(p.id)
        && !((p.text || '').trim().length > 0)
    )

    const collectedIds = new Set<string>()
    const collectedPens: any[] = []
    let used = 0

    function serialize(p: any) {
      return {
        id: p.id || p.penId, type: p.name || p.type || 'rectangle',
        text: (p.text || '').slice(0, 200), x: p.x || 0, y: p.y || 0,
        width: p.width || 100, height: p.height || 60,
        background: p.background || '', color: p.color || '',
        borderColor: p.borderColor || '', borderRadius: p.borderRadius,
        fontSize: p.fontSize, fontFamily: p.fontFamily,
        fontWeight: p.fontWeight, textAlign: p.textAlign,
        icon: p.icon || '', image: p.image || '',
        visible: p.visible !== false, locked: p.locked || 0, tags: p.tags || [],
      }
    }

    function addPens(pens: any[], limit: number | null = null) {
      for (const p of pens) {
        if (collectedIds.has(p.id)) continue
        if (limit !== null && used > limit) break
        collectedIds.add(p.id)
        collectedPens.push(serialize(p))
        used = JSON.stringify(collectedPens).length / 2.5  // approximate tokens
      }
    }

    // Layer 0: Selected (unlimited)
    addPens(selectedPens)

    // Layer 1: Neighbors (max 40%)
    addPens(neighborPens, BUDGET * 0.4)

    // Layer 2: With text (max 70% cumulative)
    addPens(withTextPens, BUDGET * 0.7)

    // Layer 3: Rest (fill to budget)
    addPens(restPens, BUDGET)

    // Lines: include ALL lines connected to collected pens
    const lines = (data.lines || [])
      .filter((l: any) =>
        collectedIds.has(l.source?.id) || collectedIds.has(l.source?.connectTo)
        || collectedIds.has(l.target?.id) || collectedIds.has(l.target?.connectTo)
      )
      .map((l: any) => ({
        from: l.source?.id || l.fromPen || '',
        to: l.source?.connectTo || l.toPen || '',
        lineName: l.lineName || 'line', text: (l.text || '').slice(0, 200),
        fromArrow: l.fromArrow || '', toArrow: l.toArrow || '',
        color: l.color || '', lineWidth: l.lineWidth || 2,
      }))

    // Viewport center
    const scale = meta2d.store?.data?.scale || 1
    const scrollX = meta2d.canvas?.scroll?.scrollX || 0
    const scrollY = meta2d.canvas?.scroll?.scrollY || 0
    const vw = meta2d.canvas?.parentElement?.clientWidth || 1200
    const vh = meta2d.canvas?.parentElement?.clientHeight || 800

    return {
      pens: collectedPens,
      lines,
      selectedIds: [...selectedIds],
      canvasInfo: { width: data.width || 1920, height: data.height || 1080 },
      viewportCenter: {
        x: Math.round((-scrollX + vw / 2) / scale),
        y: Math.round((-scrollY + vh / 2) / scale),
      },
      total_pens: (data.pens || []).length,
      total_lines: (data.lines || []).length,
      truncated: collectedPens.length < (data.pens || []).length,
    }
  } catch {
    return null
  }
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd F:/app/coding/mind/web && npx vue-tsc --noEmit --skipLibCheck 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add web/src/composables/useAgentChat.ts
git commit -m "perf: use semantic layered budget for canvas context truncation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: P1-3 — Plan-Feedback 用户隔离

**Files:**
- Modify: `app/util/agent/plan_eval.py`
- Modify: `app/util/agent/planner.py`
- Modify: `app/util/agent/engine.py`

- [ ] **Step 1: Refactor PlanMemory to be instance-based with user_id**

In `plan_eval.py`, add `user_id` parameter to PlanMemory methods. Replace the static methods with instance methods:

```python
class PlanMemory:
    """Cross-session plan quality memory, scoped per user. Uses Redis with in-memory fallback."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._mem_feedbacks: dict[str, PlanFeedback] = {}  # domain_key → feedback
        self._mem_recent: list[PlanFeedback] = []

    def _domain_key(self, domains: list[str]) -> str:
        domain_key = ":".join(sorted(domains)) if domains else "general"
        return f"plan:feedback:{self.user_id}:{domain_key}"

    def _recent_key(self) -> str:
        return f"plan:feedback:{self.user_id}:recent"

    def _pattern_key(self, domains: list[str]) -> str:
        domain_key = ":".join(sorted(domains)) if domains else "general"
        return f"plan:patterns:{domain_key}"  # cross-user, read-only

    def record(self, feedback: PlanFeedback):
        r = _get_plan_memory_redis()
        if r:
            try:
                data = json.dumps(feedback.to_dict(), ensure_ascii=False)
                r.setex(self._domain_key(feedback.domains), _PLAN_MEMORY_TTL, data)
                r.lpush(self._recent_key(), data)
                r.ltrim(self._recent_key(), 0, _PLAN_MEMORY_MAX_RECENT - 1)
                r.expire(self._recent_key(), _PLAN_MEMORY_TTL * 4)
            except Exception:
                logging.warning("PlanMemory Redis record failed", exc_info=True)
        # In-memory fallback
        dk = self._domain_key(feedback.domains)
        self._mem_feedbacks[dk] = feedback
        self._mem_recent.insert(0, feedback)
        if len(self._mem_recent) > _PLAN_MEMORY_MAX_RECENT:
            self._mem_recent.pop()

    def get_hints_for_domains(self, domains: list[str]) -> str:
        hints_parts: list[str] = []
        r = _get_plan_memory_redis()
        if r:
            try:
                # User-specific hints
                if domains:
                    raw = r.get(self._domain_key(domains))
                    if raw:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        hint = fb.to_planner_hint()
                        if hint:
                            hints_parts.append(hint)
                # User-specific recent
                recent_raws = r.lrange(self._recent_key(), 0, 2) or []
                seen_keys = {self._domain_key(domains)}
                for raw in recent_raws:
                    try:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        fb_key = self._domain_key(fb.domains)
                        if fb_key in seen_keys:
                            continue
                        seen_keys.add(fb_key)
                        hint = fb.to_planner_hint()
                        if hint:
                            hints_parts.append(hint)
                    except (json.JSONDecodeError, KeyError):
                        continue
                # Cross-user patterns (read-only, anonymized)
                pattern_raw = r.get(self._pattern_key(domains))
                if pattern_raw:
                    hints_parts.append(pattern_raw)
            except Exception:
                logging.warning("PlanMemory Redis get failed", exc_info=True)
        # In-memory fallback
        if not hints_parts:
            dk = self._domain_key(domains)
            if dk in self._mem_feedbacks:
                hint = self._mem_feedbacks[dk].to_planner_hint()
                if hint:
                    hints_parts.append(hint)
            for fb in self._mem_recent[:3]:
                if self._domain_key(fb.domains) != dk:
                    hint = fb.to_planner_hint()
                    if hint:
                        hints_parts.append(hint)
        return "\n\n".join(hints_parts) if hints_parts else ""

    def get_failure_summary(self, limit: int = 3) -> str:
        # Same logic but scoped to self.user_id
        failures: list[str] = []
        r = _get_plan_memory_redis()
        if r:
            try:
                recent_raws = r.lrange(self._recent_key(), 0, _PLAN_MEMORY_MAX_RECENT - 1) or []
                for raw in recent_raws:
                    try:
                        fb = PlanFeedback.from_dict(json.loads(raw))
                        if fb.steps_failed > 0:
                            failures.append(
                                f"目标「{fb.goal[:60]}」: {fb.steps_failed}/{fb.steps_total} 步骤失败，评分 {fb.score:.2f}"
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception:
                logging.warning("PlanMemory Redis failure_summary failed", exc_info=True)
        if not failures:
            for fb in self._mem_recent:
                if fb.steps_failed > 0:
                    failures.append(f"目标「{fb.goal[:60]}」: {fb.steps_failed}/{fb.steps_total} 步骤失败，评分 {fb.score:.2f}")
        if not failures:
            return ""
        lines = ["## 历史失败记录（请避免重复以下模式）"]
        for f in failures[:limit]:
            lines.append(f"- {f}")
        if len(failures) > limit:
            lines.append(f"- …还有 {len(failures) - limit} 条失败记录")
        return "\n".join(lines)
```

- [ ] **Step 2: Remove module-level globals**

Delete lines 133-135 in `plan_eval.py` (the old `_mem_feedbacks` and `_mem_recent` globals).

- [ ] **Step 3: Update callers in engine.py and planner.py**

In `engine.py`, where `PlanMemory.record()` is called, change to:

```python
plan_memory = PlanMemory(user_id=user_id)
plan_memory.record(feedback)
```

In `planner.py`, where `PlanMemory.get_hints_for_domains()` is called, change to:

```python
plan_memory = PlanMemory(user_id=user_id)
hints = plan_memory.get_hints_for_domains(domains)
```

Similarly update `get_failure_summary()` callers.

- [ ] **Step 4: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.plan_eval import PlanMemory; pm = PlanMemory('test_user'); print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/util/agent/plan_eval.py app/util/agent/planner.py app/util/agent/engine.py
git commit -m "fix: isolate PlanFeedback per user to prevent cross-user leakage

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: P1-4 — LLM 缓存感知失效

**Files:**
- Modify: `app/util/agent/cache.py`
- Modify: `app/util/agent/intent.py`
- Modify: `app/util/agent/core.py`

- [ ] **Step 1: Update llm_cache_get/set to accept state_version**

In `app/util/agent/cache.py`, modify `llm_cache_get` and `llm_cache_set`:

```python
def llm_cache_get(func_name: str, inputs: dict, state_version: int = 0) -> str | None:
    """Get cached LLM response for deterministic calls.
    
    Args:
        func_name: Name of the calling function (e.g. 'unified_intent')
        inputs: Serialized inputs dict for cache keying
        state_version: Monotonic version of dependent state (canvas, blueprint, etc.)
    """
    try:
        r = _get_cache_redis()
        inp_str = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
        key = f"agent:llmcache:{func_name}:{hashlib.md5(inp_str.encode()).hexdigest()}:v{state_version}"
        data = r.get(key)
        if data:
            logging.debug("LLMCache HIT: %s (v%d)", func_name, state_version)
            return data.decode("utf-8") if isinstance(data, bytes) else data
    except Exception:
        logging.warning("LLM cache get failed: %s", func_name)
    return None


def llm_cache_set(func_name: str, inputs: dict, response: str, state_version: int = 0, ttl: int = LLM_CACHE_TTL):
    """Cache LLM response for deterministic calls."""
    try:
        r = _get_cache_redis()
        inp_str = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
        key = f"agent:llmcache:{func_name}:{hashlib.md5(inp_str.encode()).hexdigest()}:v{state_version}"
        r.setex(key, ttl, response)
        logging.debug("LLMCache SET: %s (v%d, TTL=%ds)", func_name, state_version, ttl)
    except Exception:
        logging.warning("LLM cache set failed: %s", func_name)


def get_state_version(tool_ctx: dict) -> int:
    """Compute state version for cache invalidation."""
    version = 0
    try:
        shadow = tool_ctx.get("canvas_shadow")
        if shadow:
            version ^= shadow.version
        r = _get_cache_redis()
        if r:
            bp_ver = r.get("blueprint:version:" + str(tool_ctx.get("user_id", "")))
            if bp_ver:
                version ^= int(bp_ver)
    except Exception:
        pass
    return version
```

- [ ] **Step 2: Update unified_intent_and_plan to use state_version**

In `app/util/agent/intent.py`, find `unified_intent_and_plan()`. Add `tool_ctx` parameter and use it for caching:

```python
def unified_intent_and_plan(user_message: str, history: list, tool_ctx: dict = None) -> dict:
    # ... existing setup ...
    tool_ctx = tool_ctx or {}
    
    # Check cache with state version
    state_version = 0
    try:
        from app.util.agent.cache import get_state_version
        state_version = get_state_version(tool_ctx)
    except Exception:
        pass
    
    cache_inputs = {"msg": user_message, "history_len": len(history)}
    cached = llm_cache_get("unified_intent", cache_inputs, state_version)
    if cached:
        return json.loads(cached)
    
    # ... existing LLM call ...
    
    # Cache result
    llm_cache_set("unified_intent", cache_inputs, json.dumps(result, ensure_ascii=False), state_version)
    return result
```

- [ ] **Step 3: Update callers to pass tool_ctx**

In `core.py`, `chat_v3()`, ensure `tool_ctx` is passed to `unified_intent_and_plan()`.

- [ ] **Step 4: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.cache import get_state_version; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/util/agent/cache.py app/util/agent/intent.py app/util/agent/core.py
git commit -m "perf: add state-versioned LLM cache invalidation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: P2-2 — 画布状态版本回滚

**Files:**
- Modify: `app/util/agent/tools/canvas/view.py`
- Modify: `app/util/agent/state_snapshot.py`
- Modify: `web/src/utils/canvasBridge.ts`

- [ ] **Step 1: Implement snapshot actions in canvas_view**

Update `view.py` to implement the stub snapshot actions. Read existing `SnapshotManager` for integration:

```python
elif action == "list_snapshots":
    try:
        from app.util.agent.state_snapshot import SnapshotManager
        session_id = args.get("_session_id", "")
        snapshots = SnapshotManager.list_snapshots(session_id)
        return {"success": True, "data": {"snapshots": snapshots},
                "message": f"共 {len(snapshots)} 个快照" if snapshots else "暂无快照"}
    except Exception as e:
        return {"success": True, "data": {"snapshots": []},
                "message": "快照功能暂不可用"}

elif action == "restore_snapshot":
    version = args.get("version")
    try:
        from app.util.agent.state_snapshot import SnapshotManager
        session_id = args.get("_session_id", "")
        data = SnapshotManager.restore(session_id, version)
        return {"success": True, "data": data,
                "message": f"已回滚到版本 {version}，前端将应用画布状态"}
    except Exception as e:
        return {"success": False, "error": f"回滚失败: {e}"}

elif action == "save_snapshot":
    label = args.get("label", "")
    try:
        from app.util.agent.state_snapshot import SnapshotManager
        session_id = args.get("_session_id", "")
        # Get current canvas state from context
        ctx = args.get("_canvas_context") or {}
        SnapshotManager.save(session_id, ctx, description=label)
        return {"success": True, "data": {"label": label},
                "message": f"已保存快照「{label}」"}
    except Exception as e:
        return {"success": False, "error": f"保存快照失败: {e}"}
```

- [ ] **Step 2: Add auto-snapshot trigger in executor.py**

In `app/util/agent/executor.py`, before each `canvas_edit` write action (add_pen, delete_pen, clear, add_diagram, update_pen, duplicate, move_pen), auto-save a snapshot:

```python
# Before executing canvas write operations:
if tool_name == "canvas_edit" and args.get("action") in ("add_pen", "delete_pen", "clear", "add_diagram", "update_pen", "duplicate", "move_pen"):
    try:
        from app.util.agent.state_snapshot import SnapshotManager
        SnapshotManager.save(session_id, tool_ctx.get("_canvas_context", {}),
                            description=f"auto: before {tool_name} {args.get('action')}")
    except Exception:
        pass
```

- [ ] **Step 3: Add restore handler in frontend canvasBridge.ts**

```typescript
function executeRestoreSnapshot(data: any, meta2d: any) {
  const pens = data.pens || []
  const lines = data.lines || []

  // Save current state to undo stack before restoring
  pushUndoState(meta2d)

  // Clear and restore
  meta2d.store.data.pens = []
  meta2d.store.data.lines = []
  meta2d.store.data.pens.push(...pens)
  meta2d.store.data.lines.push(...lines)
  meta2d.render()

  notifyCanvasMutation()
  return { success: true, message: `已回滚画布状态` }
}
```

- [ ] **Step 4: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools.canvas.view import _tool_canvas_view; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/util/agent/tools/canvas/view.py app/util/agent/state_snapshot.py app/util/agent/executor.py web/src/utils/canvasBridge.ts
git commit -m "feat: add canvas snapshot list/restore/save via canvas_view tool

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: P2-3 — 智能布局增强

**Files:**
- Create: `web/src/utils/layoutEngine.ts`
- Modify: `web/src/utils/canvasBridge.ts`

- [ ] **Step 1: Create layoutEngine.ts**

Create `web/src/utils/layoutEngine.ts`:

```typescript
// Layout engine for canvas auto-arrangement
// Algorithms: grid, tree, force, layered

interface Pen {
  id: string; x: number; y: number; width: number; height: number;
}

interface Line {
  from: string; to: string;
}

interface LayoutOpts {
  direction?: 'horizontal' | 'vertical';
  spacing?: number;
  rootPenId?: string;
  width?: number;   // canvas width for centering
}

interface LayoutResult {
  positions: { id: string; x: number; y: number }[];
}

/** Grid layout — simple row/column arrangement. */
export function gridLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const direction = opts.direction || 'vertical'
  const spacing = opts.spacing || 40
  const positions: LayoutResult['positions'] = []

  let cx = 100, cy = 100
  let maxH = 0

  pens.forEach((p, i) => {
    positions.push({ id: p.id, x: cx, y: cy })
    if (direction === 'vertical') {
      cy += p.height + spacing
      maxH = Math.max(maxH, p.width)
    } else {
      cx += p.width + spacing
      maxH = Math.max(maxH, p.height)
    }
  })

  return { positions }
}

/** Tree layout — BFS from root. */
export function treeLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const spacing = opts.spacing || 60
  const rootId = opts.rootPenId || pens[0]?.id
  const positions: LayoutResult['positions'] = []

  // Build adjacency
  const children = new Map<string, string[]>()
  for (const l of lines) {
    if (!children.has(l.from)) children.set(l.from, [])
    children.get(l.from)!.push(l.to)
  }

  const penMap = new Map(pens.map(p => [p.id, p]))
  const visited = new Set<string>()
  const queue: { id: string; depth: number }[] = [{ id: rootId, depth: 0 }]
  const depthNodes: Map<number, string[]> = new Map()

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    if (visited.has(id)) continue
    visited.add(id)

    if (!depthNodes.has(depth)) depthNodes.set(depth, [])
    depthNodes.get(depth)!.push(id)

    for (const childId of (children.get(id) || [])) {
      if (!visited.has(childId)) queue.push({ id: childId, depth: depth + 1 })
    }
  }

  // Position by depth
  const maxDepth = Math.max(...depthNodes.keys(), 0)
  for (let d = 0; d <= maxDepth; d++) {
    const nodes = depthNodes.get(d) || []
    const totalWidth = nodes.reduce((sum, id) => sum + (penMap.get(id)?.width || 100) + spacing, -spacing)
    let cx = (opts.width || 1200) / 2 - totalWidth / 2
    const cy = 100 + d * 160
    for (const id of nodes) {
      const pen = penMap.get(id)
      positions.push({ id, x: cx, y: cy })
      cx += (pen?.width || 100) + spacing
    }
  }

  return { positions }
}

/** Force-directed layout — simple iterative repulsion/attraction. */
export function forceLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const ITERATIONS = 100
  const DAMPING = 0.9
  const REPULSION = 5000
  const ATTRACTION = 0.01

  const positions = new Map<string, { x: number; y: number; vx: number; vy: number }>()
  const penMap = new Map(pens.map(p => [p.id, p]))

  // Init positions in a circle
  const cx = (opts.width || 1200) / 2
  const cy = 400
  const radius = Math.min(400, pens.length * 20)
  pens.forEach((p, i) => {
    const angle = (2 * Math.PI * i) / pens.length
    positions.set(p.id, { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle), vx: 0, vy: 0 })
  })

  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Repulsion between all pairs
    const ids = [...positions.keys()]
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions.get(ids[i])!
        const b = positions.get(ids[j])!
        let dx = a.x - b.x, dy = a.y - b.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = REPULSION / (dist * dist)
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        a.vx += fx; a.vy += fy
        b.vx -= fx; b.vy -= fy
      }
    }

    // Attraction along edges
    for (const l of lines) {
      const a = positions.get(l.from), b = positions.get(l.to)
      if (!a || !b) continue
      let dx = b.x - a.x, dy = b.y - a.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      const force = dist * ATTRACTION
      const fx = (dx / dist) * force, fy = (dy / dist) * force
      a.vx += fx; a.vy += fy
      b.vx -= fx; b.vy -= fy
    }

    // Apply velocities with damping
    for (const p of positions.values()) {
      p.vx *= DAMPING; p.vy *= DAMPING
      p.x += p.vx; p.y += p.vy
    }
  }

  return {
    positions: [...positions.entries()].map(([id, p]) => ({ id, x: Math.round(p.x), y: Math.round(p.y) }))
  }
}

/** Layered (Sugiyama-style) layout — for DAGs/flowcharts. */
export function layeredLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const direction = opts.direction || 'vertical'
  const spacing = opts.spacing || 80
  const positions: LayoutResult['positions'] = []
  const penMap = new Map(pens.map(p => [p.id, p]))

  // Topological layering (longest-path)
  const inDegree = new Map<string, number>()
  const outEdges = new Map<string, string[]>()
  for (const p of pens) { inDegree.set(p.id, 0); outEdges.set(p.id, []) }
  for (const l of lines) {
    inDegree.set(l.to, (inDegree.get(l.to) || 0) + 1)
    outEdges.get(l.from)?.push(l.to)
    if (!inDegree.has(l.from)) inDegree.set(l.from, 0)
  }

  const layers: string[][] = []
  const layerMap = new Map<string, number>()
  const queue: string[] = [...inDegree.entries()].filter(([, d]) => d === 0).map(([id]) => id)

  for (const id of queue) {
    const maxParentLayer = lines
      .filter(l => l.to === id)
      .reduce((max, l) => Math.max(max, layerMap.get(l.from) ?? 0), -1)
    const layer = maxParentLayer + 1
    layerMap.set(id, layer)
    while (layers.length <= layer) layers.push([])
    layers[layer].push(id)

    for (const childId of (outEdges.get(id) || [])) {
      const deg = (inDegree.get(childId) || 1) - 1
      inDegree.set(childId, deg)
      if (deg === 0) queue.push(childId)
    }
  }

  // Position by layer
  for (let l = 0; l < layers.length; l++) {
    const nodes = layers[l]
    const totalW = nodes.reduce((sum, id) => sum + (penMap.get(id)?.width || 100) + spacing, -spacing)
    let cx = (opts.width || 1200) / 2 - totalW / 2
    const cy = 100 + l * 150
    for (const id of nodes) {
      const pen = penMap.get(id)
      positions.push({ id, x: cx, y: cy })
      cx += (pen?.width || 100) + spacing
    }
  }

  return { positions }
}

/** Main entry: dispatch to algorithm. */
export function autoLayout(
  pens: Pen[], lines: Line[], opts: LayoutOpts & { algorithm?: string }
): LayoutResult {
  const algo = opts.algorithm || 'grid'
  switch (algo) {
    case 'tree': return treeLayout(pens, lines, opts)
    case 'force': return forceLayout(pens, lines, opts)
    case 'layered': return layeredLayout(pens, lines, opts)
    default: return gridLayout(pens, lines, opts)
  }
}
```

- [ ] **Step 2: Integrate with canvasBridge.ts**

In `canvasBridge.ts`, update the `auto_arrange` handler:

```typescript
import { autoLayout } from './layoutEngine'

// In the auto_arrange handler:
function executeAutoArrange(args: any, meta2d: any) {
  const pens = meta2d.store.data.pens || []
  const lines = meta2d.store.data.lines || []
  const penIds = args.pen_ids || pens.map((p: any) => p.id || p.penId)

  const targetPens = pens
    .filter((p: any) => penIds.includes(p.id || p.penId))
    .map((p: any) => ({
      id: p.id || p.penId, x: p.x || 0, y: p.y || 0,
      width: p.width || 100, height: p.height || 60,
    }))

  const targetLines = lines
    .filter((l: any) => {
      const from = l.source?.id || l.fromPen || ''
      const to = l.source?.connectTo || l.toPen || ''
      return penIds.includes(from) || penIds.includes(to)
    })
    .map((l: any) => ({
      from: l.source?.id || l.fromPen || '',
      to: l.source?.connectTo || l.toPen || '',
    }))

  const result = autoLayout(targetPens, targetLines, {
    algorithm: args.algorithm || 'grid',
    direction: args.direction || 'vertical',
    spacing: args.spacing || 40,
    rootPenId: args.root_pen_id,
    width: meta2d.store.data.width || 1920,
  })

  // Apply positions in batch
  for (const { id, x, y } of result.positions) {
    meta2d.setValue({ id, x, y }, { render: false })
  }
  meta2d.render()
  notifyCanvasMutation()

  return { success: true, message: `已按${args.algorithm || 'grid'}布局排列 ${result.positions.length} 个图形` }
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd F:/app/coding/mind/web && npx vue-tsc --noEmit --skipLibCheck 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add web/src/utils/layoutEngine.ts web/src/utils/canvasBridge.ts
git commit -m "feat: add tree/force/layered layout algorithms to auto_arrange

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: P2-1 — 操作宏/模板

**Files:**
- Create: `app/util/agent/tools/macro.py`
- Modify: `app/util/agent/tool_router.py`

- [ ] **Step 1: Create macro tool**

Create `app/util/agent/tools/macro.py`:

```python
# -*- coding: UTF-8 -*-
"""Macro — 可复用的画布操作宏/模板。"""
import json
import logging
import time
from app.util.tool_registry import ToolRegistry

MACRO_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list", "run", "save"],
            "description": "list(列出所有宏), run(执行宏), save(保存当前操作序列为宏)",
        },
        "name": {"type": "string", "description": "[run/save] 宏名称"},
        "description": {"type": "string", "description": "[save] 宏描述"},
        "steps": {
            "type": "array", "items": {"type": "object"},
            "description": "[save] 操作步骤列表, 每步含 tool/action/args",
        },
    },
    "required": ["action"],
}


def _get_macro_redis():
    try:
        from app.util.redis_utils import get_redis
        return get_redis(db=5)
    except Exception:
        return None


def _macro_key(user_id: str) -> str:
    return f"macros:{user_id}"


@ToolRegistry.register(
    "macro",
    "操作宏管理: 保存、列出、执行画布操作宏。action: list(列出所有宏), run(执行指定宏), save(保存宏)",
    MACRO_SCHEMA,
)
def _tool_macro(args):
    action = args.get("action", "")
    user_id = args.get("_user_id", "default")
    r = _get_macro_redis()
    key = _macro_key(user_id)

    if action == "list":
        macros = {}
        if r:
            try:
                macros = {k.decode(): json.loads(v.decode()) for k, v in r.hgetall(key).items()}
            except Exception:
                pass
        if not macros:
            return {"success": True, "data": {"macros": []},
                    "message": "暂无保存的操作宏。创建宏：在画布上完成操作后，使用 macro(action='save', name='宏名称', steps=[...])"}
        items = [{"name": k, "description": v.get("description", ""), "steps_count": len(v.get("steps", []))}
                 for k, v in macros.items()]
        return {"success": True, "data": {"macros": items},
                "message": f"共 {len(items)} 个操作宏：{', '.join(i['name'] for i in items)}"}

    elif action == "run":
        name = args.get("name", "")
        if not name:
            return {"success": False, "error": "name 不能为空"}
        macro = None
        if r:
            try:
                raw = r.hget(key, name)
                if raw:
                    macro = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            except Exception:
                pass
        if not macro:
            return {"success": False, "error": f"未找到宏「{name}」"}
        return {
            "success": True,
            "data": {"name": name, "steps": macro.get("steps", [])},
            "message": f"执行宏「{name}」: {macro.get('description', '')}，共 {len(macro.get('steps', []))} 步。"
                       f"请按 steps 顺序依次调用对应工具。",
        }

    elif action == "save":
        name = args.get("name", "")
        if not name:
            return {"success": False, "error": "name 不能为空"}
        steps = args.get("steps", [])
        if not steps:
            return {"success": False, "error": "steps 不能为空"}
        macro_data = {
            "name": name,
            "description": args.get("description", ""),
            "steps": steps,
            "created_at": time.time(),
        }
        if r:
            try:
                r.hset(key, name, json.dumps(macro_data, ensure_ascii=False))
            except Exception:
                logging.warning("Macro save failed for user %s", user_id)
        return {"success": True, "data": macro_data,
                "message": f"已保存宏「{name}」，共 {len(steps)} 步操作。使用 macro(action='run', name='{name}') 执行。"}

    return {"success": False, "error": f"未知的 action: {action}"}
```

- [ ] **Step 2: Register macro in tool_router.py**

In `app/util/agent/tool_router.py`, add macro to USE_CASE_KEYWORDS and COMMON_TOOLS or canvas domain tools.

- [ ] **Step 3: Import macro tool in tools/__init__.py**

```python
from app.util.agent.tools.macro import _tool_macro  # noqa: F401
```

- [ ] **Step 4: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools.macro import _tool_macro; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/util/agent/tools/macro.py app/util/agent/tools/__init__.py app/util/agent/tool_router.py
git commit -m "feat: add macro tool for reusable canvas operation templates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: P2-4 — 跨 Blueprint 操作

**Files:**
- Modify: `app/util/agent/tools/blueprint.py`
- Modify: `app/package/module/blueprint_mysql.py`
- Create: `app/data/blueprint_templates/` (5 template JSON files)
- Modify: `app/util/agent/skills/blueprint_skill.py`

- [ ] **Step 1: Add diff/merge/create_from_template tools to blueprint.py**

In `app/util/agent/tools/blueprint.py`, add three new tool registrations:

```python
@ToolRegistry.register(
    "blueprint_diff",
    "对比两个蓝图的差异。返回新增、删除、修改的节点列表。",
    {
        "type": "object",
        "properties": {
            "source_id": {"type": "integer", "description": "源蓝图ID"},
            "target_id": {"type": "integer", "description": "目标蓝图ID"},
        },
        "required": ["source_id", "target_id"],
    },
)
def _tool_blueprint_diff(args):
    source_id = args.get("source_id")
    target_id = args.get("target_id")
    if not source_id or not target_id:
        return {"success": False, "error": "source_id 和 target_id 不能为空"}
    try:
        handler = BlueprintMysqlHandler()
        source = handler.load(source_id)
        target = handler.load(target_id)
        if not source or not target:
            return {"success": False, "error": "蓝图不存在"}
        
        src_pens = {p.get("id", p.get("pen_id", "")): p for p in (source.get("pens") or [])}
        tgt_pens = {p.get("id", p.get("pen_id", "")): p for p in (target.get("pens") or [])}
        
        src_ids = set(src_pens.keys())
        tgt_ids = set(tgt_pens.keys())
        
        added = [{"pen_id": pid, "type": tgt_pens[pid].get("type"), "text": tgt_pens[pid].get("text", "")}
                 for pid in (tgt_ids - src_ids)]
        removed = [{"pen_id": pid, "type": src_pens[pid].get("type"), "text": src_pens[pid].get("text", "")}
                   for pid in (src_ids - tgt_ids)]
        
        modified = []
        for pid in (src_ids & tgt_ids):
            changes = {}
            for key in ("text", "x", "y", "width", "height", "background", "color"):
                if src_pens[pid].get(key) != tgt_pens[pid].get(key):
                    changes[key] = f"{src_pens[pid].get(key)} → {tgt_pens[pid].get(key)}"
            if changes:
                modified.append({"pen_id": pid, "changes": changes})
        
        unchanged = len(src_ids & tgt_ids) - len(modified)
        summary = f"新增 {len(added)} 个节点，删除 {len(removed)} 个节点，修改 {len(modified)} 个节点，{unchanged} 个节点无变化"
        
        return {"success": True, "data": {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged},
                "message": summary}
    except Exception as e:
        logging.warning("blueprint_diff failed: %s", e)
        return {"success": False, "error": str(e)}


@ToolRegistry.register(
    "blueprint_merge",
    "合并两个蓝图。mode: add(只追加新节点), replace(同名覆盖), preview(仅预览不实际合并)。",
    {
        "type": "object",
        "properties": {
            "source_id": {"type": "integer", "description": "源蓝图ID（从中取节点）"},
            "target_id": {"type": "integer", "description": "目标蓝图ID（合并到此处）"},
            "mode": {"type": "string", "enum": ["add", "replace", "preview"], "description": "合并模式", "default": "add"},
        },
        "required": ["source_id", "target_id"],
    },
)
def _tool_blueprint_merge(args):
    source_id = args.get("source_id")
    target_id = args.get("target_id")
    mode = args.get("mode", "add")
    if not source_id or not target_id:
        return {"success": False, "error": "source_id 和 target_id 不能为空"}
    try:
        handler = BlueprintMysqlHandler()
        source = handler.load(source_id)
        target = handler.load(target_id)
        if not source or not target:
            return {"success": False, "error": "蓝图不存在"}
        
        src_pens = source.get("pens") or []
        tgt_pens = target.get("pens") or []
        tgt_ids = {p.get("id", p.get("pen_id", "")) for p in tgt_pens}
        
        merged = list(tgt_pens)
        added_count = 0
        replaced_count = 0
        
        for sp in src_pens:
            sp_id = sp.get("id", sp.get("pen_id", ""))
            if sp_id in tgt_ids:
                if mode == "replace":
                    merged = [p for p in merged if p.get("id", p.get("pen_id", "")) != sp_id]
                    merged.append(sp)
                    replaced_count += 1
            else:
                merged.append(sp)
                added_count += 1
        
        if mode == "preview":
            return {"success": True, "data": {"would_add": added_count, "would_replace": replaced_count},
                    "message": f"预览：将新增 {added_count} 个节点，替换 {replaced_count} 个节点（未实际修改）"}
        
        # Apply merge
        target["pens"] = merged
        handler.update(target_id, pens=json.dumps(merged))
        
        return {"success": True, "data": {"added": added_count, "replaced": replaced_count, "total": len(merged)},
                "message": f"已合并：新增 {added_count} 个节点，替换 {replaced_count} 个节点，共 {len(merged)} 个节点"}
    except Exception as e:
        logging.warning("blueprint_merge failed: %s", e)
        return {"success": False, "error": str(e)}


@ToolRegistry.register(
    "blueprint_from_template",
    "从预置模板创建新蓝图。",
    {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "enum": ["three-tier-architecture", "microservices-mesh", "data-pipeline",
                         "class-hierarchy", "swot-analysis"],
                "description": "模板名称",
            },
            "name": {"type": "string", "description": "新蓝图名称"},
            "description": {"type": "string", "description": "新蓝图描述"},
        },
        "required": ["template", "name"],
    },
)
def _tool_blueprint_from_template(args):
    import os
    template_name = args.get("template", "")
    bp_name = args.get("name", "")
    bp_desc = args.get("description", "")
    
    template_path = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                 "data", "blueprint_templates", f"{template_name}.json")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)
    except FileNotFoundError:
        return {"success": False, "error": f"模板「{template_name}」不存在"}
    
    handler = BlueprintMysqlHandler()
    new_id = handler.create(
        name=bp_name, description=bp_desc or template_data.get("description", ""),
        pens=json.dumps(template_data.get("pens", [])),
        background=template_data.get("background", ""),
        grid=template_data.get("grid", True),
    )
    
    return {"success": True, "data": {"id": new_id, "name": bp_name, "template": template_name},
            "message": f"已从模板「{template_name}」创建蓝图「{bp_name}」(ID: {new_id})"}
```

- [ ] **Step 2: Create template JSON files**

Create `app/data/blueprint_templates/` directory with 5 template files. Each is a JSON file with `pens`, `lines`, and metadata. Start with `three-tier-architecture.json`:

```json
{
  "name": "三层架构",
  "description": "标准三层架构图：Web层 → 应用层 → 数据库层",
  "background": "#ffffff",
  "grid": true,
  "pens": [
    {"id": "web", "type": "rectangle", "text": "Web 层\nNginx / CDN", "x": 300, "y": 80, "width": 200, "height": 80, "background": "#E3F2FD"},
    {"id": "app", "type": "rectangle", "text": "应用层\nAPI / Service", "x": 300, "y": 220, "width": 200, "height": 80, "background": "#E8F5E9"},
    {"id": "db", "type": "rectangle", "text": "数据层\nMySQL / Redis", "x": 300, "y": 360, "width": 200, "height": 80, "background": "#FFF3E0"}
  ],
  "lines": [
    {"from": "web", "to": "app", "lineName": "downstream", "text": "HTTP"},
    {"from": "app", "to": "db", "lineName": "downstream", "text": "SQL"}
  ]
}
```

Create similar files for `microservices-mesh.json`, `data-pipeline.json`, `class-hierarchy.json`, `swot-analysis.json`.

- [ ] **Step 3: Update blueprint_skill.py**

Add new tool descriptions to the blueprint skill text.

- [ ] **Step 4: Verify syntax**

```bash
cd F:/app/coding/mind && python -c "from app.util.agent.tools.blueprint import TOOL_SCHEMAS; print(len(TOOL_SCHEMAS))"
```

- [ ] **Step 5: Commit**

```bash
git add app/util/agent/tools/blueprint.py app/package/module/blueprint_mysql.py app/data/blueprint_templates/ app/util/agent/skills/blueprint_skill.py
git commit -m "feat: add blueprint_diff, blueprint_merge, blueprint_from_template tools

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 实施完成检查清单

- [ ] P0-3: CanvasAgent 工具补齐 ✓
- [ ] P0-1: Blueprint 保存原子化 ✓
- [ ] P0-2: CanvasShadow 跨轮次状态追踪 ✓
- [ ] P1-1: 画布工具统一化 (edit/organize/view) ✓
- [ ] P1-2: 画布上下文语义截断 ✓
- [ ] P1-3: Plan-Feedback 用户隔离 ✓
- [ ] P1-4: LLM 缓存感知失效 ✓
- [ ] P2-2: 画布状态版本回滚 ✓
- [ ] P2-3: 智能布局增强 ✓
- [ ] P2-1: 操作宏/模板 ✓
- [ ] P2-4: 跨蓝图操作 ✓

**主验证命令**：
```bash
# Backend syntax check
cd F:/app/coding/mind && python -c "
from app.util.agent.tools.canvas import _tool_canvas_edit, _tool_canvas_organize, _tool_canvas_view
from app.util.agent.tools.macro import _tool_macro
from app.util.agent.canvas_shadow import CanvasShadow, load_canvas_shadow
from app.util.agent.plan_eval import PlanMemory
from app.util.agent.cache import get_state_version
print('All imports OK')
"

# Frontend type check
cd F:/app/coding/mind/web && npx vue-tsc --noEmit --skipLibCheck
```
