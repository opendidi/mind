# -*- coding: UTF-8 -*-
"""Agent tools for mind — canvas operations, layout, canvas properties, viewport control."""

import uuid

from app.util.tool_registry import ToolRegistry

# ══════════════════════════════════════════════════════════════════════════════
# Canvas Tools — unified single tool with action parameter
# ══════════════════════════════════════════════════════════════════════════════

def _new_pen_id() -> str:
    """Generate a unique pen ID using UUID4 (12 hex chars = 48 bits random)."""
    return uuid.uuid4().hex[:12]


def _resolve_pen_ids(args: dict) -> list:
    """Extract pen_ids from args, supporting single pen_id or list of pen_ids."""
    pen_ids = args.get("pen_ids", [])
    if not pen_ids and args.get("pen_id"):
        pen_ids = [args.get("pen_id")]
    return pen_ids


@ToolRegistry.register(
    "canvas",
    "画布操作。action: add_pen(创建图形), add_line(连线), add_diagram(批量图表), "
    "update_pen(修改,支持批量的updates), delete_pen(删除), clear(清空), undo(撤销), redo(重做), "
    "get_state(查看), lock(锁定), unlock(解锁), toggle_visibility(显隐), duplicate(复制), "
    "move_pen(批量移动), group(组合), ungroup(取消组合)",
    {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "add_pen",
                    "add_line",
                    "add_diagram",
                    "update_pen",
                    "delete_pen",
                    "clear",
                    "undo",
                    "redo",
                    "get_state",
                    "lock",
                    "unlock",
                    "toggle_visibility",
                    "duplicate",
                    "move_pen",
                    "group",
                    "ungroup",
                ],
                "description": "操作类型。add_diagram用于批量创建完整图表(流程图/架构图/思维导图)",
            },
            # add_pen params
            "type": {
                "type": "string",
                "description": "[add_pen/add_diagram.nodes]图形类型:rectangle/circle/triangle/diamond/pentagon/star/text/image",
            },
            "text": {"type": "string", "description": "[add_pen/add_line/update_pen]文字"},
            "x": {"type": "number", "description": "[add_pen]X坐标(画布中心为原点)", "default": 0},
            "y": {"type": "number", "description": "[add_pen]Y坐标(画布中心为原点)", "default": 0},
            "width": {"type": "number", "description": "[add_pen]宽度(像素)", "default": 100},
            "height": {"type": "number", "description": "[add_pen]高度(像素)", "default": 60},
            "background": {"type": "string", "description": "[add_pen]背景颜色(#RRGGBB)"},
            "color": {"type": "string", "description": "[add_pen/add_line]颜色(#RRGGBB)"},
            "fontSize": {"type": "number", "description": "[add_pen]文字大小(px)"},
            "borderWidth": {"type": "number", "description": "[add_pen]边框宽度(px)"},
            "borderColor": {"type": "string", "description": "[add_pen]边框颜色(#RRGGBB)"},
            "borderRadius": {"type": "number", "description": "[add_pen]圆角半径(px)"},
            "lineDash": {
                "type": "array", "items": {"type": "number"},
                "description": "[add_pen]虚线模式,如[5,3]表示5px实线+3px空白",
            },
            "globalAlpha": {"type": "number", "description": "[add_pen]透明度(0-1)"},
            "shadowColor": {"type": "string", "description": "[add_pen]阴影颜色(#RRGGBB)"},
            "shadowBlur": {"type": "number", "description": "[add_pen]阴影模糊半径(px)"},
            "shadowOffsetX": {"type": "number", "description": "[add_pen]阴影X偏移(px)"},
            "shadowOffsetY": {"type": "number", "description": "[add_pen]阴影Y偏移(px)"},
            "gradientColors": {"type": "string", "description": "[add_pen]渐变填充色,JSON数组如'[\"#ff0000\",\"#0000ff\"]'"},
            "fontFamily": {"type": "string", "description": "[add_pen]字体家族"},
            "fontWeight": {"type": "string", "description": "[add_pen]字体粗细(normal/bold/100-900)"},
            "fontStyle": {"type": "string", "description": "[add_pen]字体样式(normal/italic)"},
            "textAlign": {"type": "string", "description": "[add_pen]文字水平对齐(left/center/right)"},
            "textBaseline": {"type": "string", "description": "[add_pen]文字垂直对齐(top/middle/bottom)"},
            "icon": {"type": "string", "description": "[add_pen]图标unicode或名称(如'\\ue600')"},
            "iconFamily": {"type": "string", "description": "[add_pen]图标字体家族"},
            "iconSize": {"type": "number", "description": "[add_pen]图标大小(px)"},
            "iconColor": {"type": "string", "description": "[add_pen]图标颜色(#RRGGBB)"},
            "image": {"type": "string", "description": "[add_pen]图片URL"},
            "paddingTop": {"type": "number", "description": "[add_pen]上内边距(px)"},
            "paddingBottom": {"type": "number", "description": "[add_pen]下内边距(px)"},
            "paddingLeft": {"type": "number", "description": "[add_pen]左内边距(px)"},
            "paddingRight": {"type": "number", "description": "[add_pen]右内边距(px)"},
            "visible": {"type": "boolean", "description": "[add_pen]是否可见"},
            "locked": {"type": "number", "description": "[add_pen]锁定状态:0=正常,1=禁编辑,2=禁移动"},
            "tags": {
                "type": "array", "items": {"type": "string"},
                "description": "[add_pen]标签列表",
            },
            # add_line params
            "from_pen": {"type": "string", "description": "[add_line/add_diagram.edges]起始节点ID"},
            "to_pen": {"type": "string", "description": "[add_line/add_diagram.edges]目标节点ID"},
            "line_type": {
                "type": "string",
                "enum": ["straight", "curve", "polyline", "mind"],
                "description": "[add_line]连线类型",
                "default": "straight",
            },
            "arrow": {
                "type": "string",
                "enum": ["start", "end", "both", "none"],
                "description": "[add_line]箭头方向",
                "default": "end",
            },
            "lineWidth": {"type": "number", "description": "[add_line]连线宽度(px)"},
            # add_diagram params
            "diagram": {
                "type": "object",
                "description": "[add_diagram]图表定义,含nodes数组和edges数组",
                "properties": {
                    "nodes": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "节点列表,每个节点有id/type/text/x/y/width/height",
                    },
                    "edges": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "连线列表,每条线有from/to/text/line_type/arrow",
                    },
                },
            },
            # update_pen / delete_pen params
            "pen_id": {"type": "string", "description": "[update_pen/delete_pen]图形ID"},
            "pen_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "[delete_pen]批量删除的图形ID列表",
            },
            "props": {"type": "object", "description": '[update_pen]要修改的属性键值对,如{"x":100,"text":"新文字"}'},
            # clear param
            "confirm": {"type": "boolean", "description": "[clear]确认清空画布"},
            # lock / unlock / visibility params
            "visible": {"type": "boolean", "description": "[toggle_visibility]是否可见"},
            # duplicate params
            "offset_x": {"type": "number", "description": "[duplicate]复制后的X偏移(px)", "default": 30},
            "offset_y": {"type": "number", "description": "[duplicate]复制后的Y偏移(px)", "default": 30},
            # move_pen params
            "moves": {
                "type": "array",
                "items": {"type": "object", "properties": {"pen_id": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}}},
                "description": "[move_pen]批量移动列表,每项含pen_id/x/y",
            },
        },
        "required": ["action"],
    },
)
def _tool_canvas(args):
    action = args.get("action", "")
    if action == "add_pen":
        pen_id = _new_pen_id()
        pen_type = args.get("type", "rectangle")
        text = args.get("text", "")
        x, y = args.get("x", 0), args.get("y", 0)
        w, h = args.get("width", 100), args.get("height", 60)
        label = f"「{text}」" if text else ""
        return {
            "success": True,
            "pen_id": pen_id,
            "data": {"pen_id": pen_id, "type": pen_type, "text": text, "x": x, "y": y, "width": w, "height": h},
            "message": f"已创建{pen_type}{label}，位置({x}, {y})，大小 {w}x{h}，ID: {pen_id}",
        }
    elif action == "add_line":
        from_pen = args.get("from_pen", "")
        to_pen = args.get("to_pen", "")
        if not from_pen or not to_pen:
            return {"success": False, "error": "from_pen 和 to_pen 不能为空，请先创建起始和目标节点"}
        line_type = args.get("line_type", "straight")
        label = f"「{args.get('text')}」" if args.get("text") else ""
        return {
            "success": True,
            "data": {"from_pen": from_pen, "to_pen": to_pen, "line_type": line_type, "text": args.get("text", "")},
            "message": f"已创建从 {from_pen} 到 {to_pen} 的{line_type}连线{label}",
        }
    elif action == "update_pen":
        pen_id = args.get("pen_id", "")
        if not pen_id:
            return {"success": False, "error": "pen_id 不能为空"}
        props = args.get("props", {})
        if not props:
            return {"success": False, "error": "props 不能为空，至少指定一个要修改的属性"}
        props_desc = ", ".join(f"{k}={v}" for k, v in props.items())
        return {
            "success": True,
            "data": {"pen_id": pen_id, "props": props},
            "message": f"已更新图形 {pen_id}：{props_desc}",
        }
    elif action == "delete_pen":
        pen_ids = _resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空，请指定要删除的图形ID"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids},
            "message": f"已删除 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "clear":
        if not args.get("confirm"):
            return {"success": False, "error": "清空画布不可逆，请设置 confirm=true 确认"}
        return {"success": True, "data": {}, "message": "画布已清空，所有图形和连线已删除"}
    elif action == "undo":
        return {"success": True, "data": {}, "message": "已撤销上一步操作"}
    elif action == "redo":
        return {"success": True, "data": {}, "message": "已恢复撤销的操作"}
    elif action == "add_diagram":
        diagram = args.get("diagram", {})
        nodes = diagram.get("nodes", [])
        edges = diagram.get("edges", [])
        if not nodes:
            return {"success": False, "error": "diagram.nodes 不能为空"}
        # Generate pen_ids for each node and resolve edge references
        id_map = {}
        node_summaries = []
        for node in nodes:
            logical_id = node.get("id", "")
            pen_id = _new_pen_id()
            node["pen_id"] = pen_id
            if logical_id:
                id_map[logical_id] = pen_id
            node_summaries.append(f"{node.get('type', 'rectangle')}({pen_id})")
        for edge in edges:
            from_ref = edge.get("from", "")
            to_ref = edge.get("to", "")
            edge["_from_id"] = id_map.get(from_ref, from_ref)
            edge["_to_id"] = id_map.get(to_ref, to_ref)
        return {
            "success": True,
            "data": {"diagram": {"nodes": nodes, "edges": edges}},
            "message": f"已生成包含 {len(nodes)} 个节点（{', '.join(node_summaries)}）和 {len(edges)} 条连线的图表",
        }
    elif action == "get_state":
        return {
            "success": True,
            "message": "查看系统提示中的 canvas_context 获取完整画布状态",
            "tool_hint": "use canvas_context in system prompt for current canvas state",
        }
    elif action == "lock":
        pen_ids = _resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "locked": 2},
            "message": f"已锁定 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "unlock":
        pen_ids = _resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "locked": False},
            "message": f"已解锁 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "toggle_visibility":
        pen_ids = _resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        visible = args.get("visible", False)
        label = "显示" if visible else "隐藏"
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "visible": visible},
            "message": f"已{label} {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "duplicate":
        pen_ids = _resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        ox = args.get("offset_x", 30)
        oy = args.get("offset_y", 30)
        new_ids = [_new_pen_id() for _ in pen_ids]
        return {
            "success": True,
            "data": {"original_ids": pen_ids, "new_ids": new_ids, "offset_x": ox, "offset_y": oy},
            "message": f"已复制 {len(pen_ids)} 个图形，新ID：{', '.join(new_ids)}，偏移({ox}, {oy})",
        }
    elif action == "move_pen":
        moves = args.get("moves", [])
        if not moves:
            return {"success": False, "error": "moves 不能为空，格式: [{\"pen_id\": \"...\", \"x\": 100, \"y\": 200}]"}
        return {
            "success": True,
            "data": {"moves": moves},
            "message": f"已移动 {len(moves)} 个图形",
        }
    elif action == "group":
        pen_ids = _resolve_pen_ids(args)
        if len(pen_ids) < 2:
            return {"success": False, "error": "至少需要两个图形才能组合"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids},
            "message": f"已组合 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "ungroup":
        pen_id = args.get("pen_id", "")
        if not pen_id:
            return {"success": False, "error": "pen_id 不能为空"}
        return {
            "success": True,
            "data": {"pen_id": pen_id},
            "message": f"已取消组合：{pen_id}",
        }
    return {
        "success": False,
        "error": f"未知的 action: {action}，支持: add_pen/add_line/add_diagram/update_pen/delete_pen/clear/undo/redo/get_state/lock/unlock/toggle_visibility/duplicate/move_pen/group/ungroup",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Layout Tools
# ══════════════════════════════════════════════════════════════════════════════


@ToolRegistry.register(
    "layout_auto_arrange",
    "对画布上选中的图形进行自动排版布局。",
    {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["horizontal", "vertical", "grid"],
                "description": "排列方向",
                "default": "vertical",
            },
            "spacing": {"type": "number", "description": "间距(px)", "default": 40},
            "columns": {"type": "integer", "description": "网格列数(grid模式)", "default": 3},
        },
        "required": [],
    },
)
def _tool_layout_auto_arrange(args):
    return {
        "success": True,
        "data": args,
        "message": f"已按{args.get('direction', 'vertical')}方向自动排列，间距{args.get('spacing', 40)}px",
    }


@ToolRegistry.register(
    "layout_align",
    "将选中的多个图形对齐。",
    {
        "type": "object",
        "properties": {
            "align": {
                "type": "string",
                "enum": ["left", "center", "right", "top", "middle", "bottom"],
                "description": "对齐方式",
            },
        },
        "required": ["align"],
    },
)
def _tool_layout_align(args):
    return {"success": True, "data": args, "message": f"已按{args.get('align')}对齐"}


# ══════════════════════════════════════════════════════════════════════════════
# Canvas Props Tool
# ══════════════════════════════════════════════════════════════════════════════


@ToolRegistry.register(
    "canvas_props",
    "设置画布级属性：背景色/图片、网格、标尺等。",
    {
        "type": "object",
        "properties": {
            "background": {"type": "string", "description": "画布背景颜色(#RRGGBB)"},
            "bkImage": {"type": "string", "description": "画布背景图片URL"},
            "grid": {"type": "boolean", "description": "是否显示网格"},
            "gridColor": {"type": "string", "description": "网格颜色(#RRGGBB)"},
            "gridSize": {"type": "number", "description": "网格大小(px)"},
            "rule": {"type": "boolean", "description": "是否显示标尺"},
            "ruleColor": {"type": "string", "description": "标尺颜色(#RRGGBB)"},
            "color": {"type": "string", "description": "画布默认文字颜色"},
            "penBackground": {"type": "string", "description": "画布默认图形背景色"},
        },
        "required": [],
    },
)
def _tool_canvas_props(args):
    props_desc = ", ".join(f"{k}={v}" for k, v in args.items())
    return {
        "success": True,
        "data": args,
        "message": f"画布属性已更新：{props_desc}",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Fit View Tool
# ══════════════════════════════════════════════════════════════════════════════


@ToolRegistry.register(
    "fit_view",
    "自适应视口——将所有图形缩放到适合视窗的大小。",
    {
        "type": "object",
        "properties": {
            "fit": {"type": "boolean", "description": "是否自适应(true=fitView, false=还原100%)", "default": True},
            "padding": {"type": "number", "description": "内边距(px)", "default": 24},
        },
        "required": [],
    },
)
def _tool_fit_view(args):
    fit = args.get("fit", True)
    padding = args.get("padding", 24)
    label = "自适应视口" if fit else "还原100%"
    return {"success": True, "data": {"fit": fit, "padding": padding}, "message": f"已{label}，内边距{padding}px"}
