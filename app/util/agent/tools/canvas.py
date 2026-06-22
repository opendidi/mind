# -*- coding: UTF-8 -*-
"""Agent tools for mind — canvas operations, blueprint management, layout, file search, code generation."""

import json
import logging
import os
import re
import tempfile
import uuid
from html.parser import HTMLParser

import requests

from app.package.module.blueprint_mysql import BlueprintMysqlHandler
from app.util.tool_registry import ToolRegistry
from app.util.vision import VisionHandler

# ══════════════════════════════════════════════════════════════════════════════
# Canvas Tools — unified single tool with action parameter
# ══════════════════════════════════════════════════════════════════════════════

_pen_counter = 0


def _next_pen_id():
    global _pen_counter
    _pen_counter += 1
    return f"pen_{_pen_counter}"


@ToolRegistry.register(
    "canvas",
    "画布操作。action: add_pen(创建图形), add_line(连线), add_diagram(批量生成图表), "
    "update_pen(修改), delete_pen(删除), clear(清空), undo(撤销), redo(重做), get_state(查看状态)",
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
        },
        "required": ["action"],
    },
)
def _tool_canvas(args):
    action = args.get("action", "")
    if action == "add_pen":
        pen_id = _next_pen_id()
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
        pen_ids = args.get("pen_ids", [])
        if not pen_ids and args.get("pen_id"):
            pen_ids = [args.get("pen_id")]
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
            pen_id = _next_pen_id()
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
    return {
        "success": False,
        "error": f"未知的 action: {action}，支持: add_pen/add_line/add_diagram/update_pen/delete_pen/clear/undo/redo/get_state",
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
