# -*- coding: UTF-8 -*-
"""canvas_edit tool — graphics CRUD (add/update/delete/duplicate/move/undo/redo/clear/get_state)."""
from app.util.agent.tools.canvas._base import new_pen_id, resolve_pen_ids, get_shadow
from app.util.tool_registry import ToolRegistry


@ToolRegistry.register(
    "canvas_edit",
    "画布图形增删改操作。action: add_pen(创建图形), add_line(连线), add_diagram(批量图表), "
    "update_pen(修改,支持批量的updates), delete_pen(删除), duplicate(复制), "
    "move_pen(批量移动), undo(撤销), redo(重做), clear(清空), get_state(查看)",
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
                    "duplicate",
                    "move_pen",
                    "undo",
                    "redo",
                    "clear",
                    "get_state",
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
                "type": "array",
                "items": {"type": "number"},
                "description": "[add_pen]虚线模式,如[5,3]表示5px实线+3px空白",
            },
            "globalAlpha": {"type": "number", "description": "[add_pen]透明度(0-1)"},
            "shadowColor": {"type": "string", "description": "[add_pen]阴影颜色(#RRGGBB)"},
            "shadowBlur": {"type": "number", "description": "[add_pen]阴影模糊半径(px)"},
            "shadowOffsetX": {"type": "number", "description": "[add_pen]阴影X偏移(px)"},
            "shadowOffsetY": {"type": "number", "description": "[add_pen]阴影Y偏移(px)"},
            "gradientColors": {
                "type": "string",
                "description": '[add_pen]渐变填充色,JSON数组如\'["#ff0000","#0000ff"]\'',
            },
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
                "type": "array",
                "items": {"type": "string"},
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
            # duplicate params
            "offset_x": {"type": "number", "description": "[duplicate]复制后的X偏移(px)", "default": 30},
            "offset_y": {"type": "number", "description": "[duplicate]复制后的Y偏移(px)", "default": 30},
            # move_pen params
            "moves": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"pen_id": {"type": "string"}, "x": {"type": "number"}, "y": {"type": "number"}},
                },
                "description": "[move_pen]批量移动列表,每项含pen_id/x/y",
            },
        },
        "required": ["action"],
    },
)
def _tool_canvas_edit(args):
    action = args.get("action", "")
    if not action:
        return {
            "success": False,
            "error": "缺少必填参数: action，请指定画布操作类型。支持: add_pen/add_line/add_diagram/update_pen/delete_pen/duplicate/move_pen/undo/redo/clear/get_state",
        }
    if action == "add_pen":
        pen_id = new_pen_id()
        pen_type = args.get("type", "rectangle")
        text = args.get("text", "")
        x, y = args.get("x", 0), args.get("y", 0)
        w, h = args.get("width", 100), args.get("height", 60)
        label = f"「{text}」" if text else ""
        # Update canvas shadow
        shadow = get_shadow(args)
        if shadow:
            shadow.add_pen(pen_id, args)
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
        # Validate pen IDs against canvas shadow
        shadow = get_shadow(args)
        if shadow:
            if from_pen and not shadow.has_pen(from_pen):
                return {"success": False, "error": f"from_pen '{from_pen}' 不存在，可能已被删除"}
            if to_pen and not shadow.has_pen(to_pen):
                return {"success": False, "error": f"to_pen '{to_pen}' 不存在，可能已被删除"}
        line_type = args.get("line_type", "straight")
        label = f"「{args.get('text')}」" if args.get("text") else ""
        # Update canvas shadow
        if shadow:
            shadow.add_line("", from_pen, to_pen)
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
        # Update canvas shadow
        shadow = get_shadow(args)
        if shadow and shadow.has_pen(pen_id):
            existing = shadow.get_pen(pen_id)
            if existing is not None:
                if "text" in props:
                    existing.text = props["text"]
                if "x" in props:
                    existing.x = props["x"]
                if "y" in props:
                    existing.y = props["y"]
                if "width" in props:
                    existing.width = props["width"]
                if "height" in props:
                    existing.height = props["height"]
                if "type" in props:
                    existing.type = props["type"]
        props_desc = ", ".join(f"{k}={v}" for k, v in props.items())
        return {
            "success": True,
            "data": {"pen_id": pen_id, "props": props},
            "message": f"已更新图形 {pen_id}：{props_desc}",
        }
    elif action == "delete_pen":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空，请指定要删除的图形ID"}
        # Update canvas shadow
        shadow = get_shadow(args)
        if shadow:
            for pid in pen_ids:
                shadow.remove_pen(pid)
        return {
            "success": True,
            "data": {"pen_ids": pen_ids},
            "message": f"已删除 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "clear":
        if not args.get("confirm"):
            return {"success": False, "error": "清空画布不可逆，请设置 confirm=true 确认"}
        # Update canvas shadow
        shadow = get_shadow(args)
        if shadow:
            shadow.clear()
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
        shadow = get_shadow(args)
        for node in nodes:
            logical_id = node.get("id", "")
            pen_id = new_pen_id()
            node["pen_id"] = pen_id
            if logical_id:
                id_map[logical_id] = pen_id
            node_summaries.append(f"{node.get('type', 'rectangle')}({pen_id})")
            # Update canvas shadow
            if shadow:
                shadow.add_pen(pen_id, node)
        for edge in edges:
            from_ref = edge.get("from", "")
            to_ref = edge.get("to", "")
            edge["_from_id"] = id_map.get(from_ref, from_ref)
            edge["_to_id"] = id_map.get(to_ref, to_ref)
            # Update canvas shadow with edges
            if shadow:
                from_pen = id_map.get(from_ref, from_ref)
                to_pen = id_map.get(to_ref, to_ref)
                if from_pen and to_pen:
                    shadow.add_line("", from_pen, to_pen)
        return {
            "success": True,
            "data": {"diagram": {"nodes": nodes, "edges": edges}},
            "message": f"已生成包含 {len(nodes)} 个节点（{', '.join(node_summaries)}）和 {len(edges)} 条连线的图表",
        }
    elif action == "get_state":
        ctx = args.get("_canvas_context") or {}
        pens = ctx.get("pens", [])
        lines = ctx.get("lines", [])
        if not ctx:
            return {
                "success": True,
                "data": {"pens": [], "lines": [], "empty": True, "canvas_available": False},
                "message": "无法获取画布状态（用户可能不在画布页面），画布视为空。不要再查询——直接调用 canvas_edit(action='clear', confirm=true) 清空画布，然后用 add_diagram 创建图表。",
                "hint": "canvas_context not available — skip checking, just clear and draw",
            }
        return {
            "success": True,
            "data": {
                "pens": [
                    {
                        "pen_id": p.get("id", p.get("penId", "")),
                        "type": p.get("name", p.get("type", "rectangle")),
                        "text": p.get("text", ""),
                        "x": p.get("x", 0),
                        "y": p.get("y", 0),
                    }
                    for p in pens
                ],
                "lines": [
                    {
                        "from": l.get("fromPen", l.get("source", "")),
                        "to": l.get("toPen", l.get("connectTo", "")),
                        "text": l.get("text", ""),
                    }
                    for l in lines
                ],
                "pen_count": len(pens),
                "line_count": len(lines),
                "empty": len(pens) == 0 and len(lines) == 0,
            },
            "message": (
                f"画布当前有 {len(pens)} 个图形和 {len(lines)} 条连线。如需重新绘制，先调用 canvas_edit(action='clear', confirm=true) 清空。"
                if (pens or lines)
                else "画布当前为空，可以开始绘制"
            ),
        }
    elif action == "duplicate":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        ox = args.get("offset_x", 30)
        oy = args.get("offset_y", 30)
        new_ids = [new_pen_id() for _ in pen_ids]
        # Update canvas shadow: copy each original pen's shadow to new ID
        shadow = get_shadow(args)
        if shadow:
            for orig_id, new_id in zip(pen_ids, new_ids):
                orig_pen = shadow.get_pen(orig_id)
                if orig_pen is not None:
                    pen_data = {
                        "type": orig_pen.type,
                        "text": orig_pen.text,
                        "x": orig_pen.x + ox,
                        "y": orig_pen.y + oy,
                        "width": orig_pen.width,
                        "height": orig_pen.height,
                    }
                    shadow.add_pen(new_id, pen_data)
        return {
            "success": True,
            "data": {"original_ids": pen_ids, "new_ids": new_ids, "offset_x": ox, "offset_y": oy},
            "message": f"已复制 {len(pen_ids)} 个图形，新ID：{', '.join(new_ids)}，偏移({ox}, {oy})",
        }
    elif action == "move_pen":
        moves = args.get("moves", [])
        if not moves:
            return {"success": False, "error": 'moves 不能为空，格式: [{"pen_id": "...", "x": 100, "y": 200}]'}
        # Update canvas shadow
        shadow = get_shadow(args)
        if shadow:
            for move in moves:
                pid = move.get("pen_id", "")
                if pid and pid in shadow.pens:
                    shadow.pens[pid].x = move.get("x", shadow.pens[pid].x)
                    shadow.pens[pid].y = move.get("y", shadow.pens[pid].y)
        return {
            "success": True,
            "data": {"moves": moves},
            "message": f"已移动 {len(moves)} 个图形",
        }
    return {
        "success": False,
        "error": f"未知的 action: {action}，支持: add_pen/add_line/add_diagram/update_pen/delete_pen/duplicate/move_pen/undo/redo/clear/get_state",
    }
