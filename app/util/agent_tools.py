# -*- coding: UTF-8 -*-
"""Agent tools for mind — canvas operations, blueprint management, layout, file search, code generation."""

import json
import logging
from app.util.tool_registry import ToolRegistry

# ══════════════════════════════════════════════════════════════════════════════
# Canvas Tools
# ══════════════════════════════════════════════════════════════════════════════

@ToolRegistry.register(
    "canvas_add_pen",
    "在画布上创建一个新的图形/节点。支持矩形、圆形、三角形、菱形、五边形、星形、文本、图片等。",
    {"type": "object", "properties": {
        "type": {"type": "string", "description": "图形类型: rectangle/circle/triangle/diamond/pentagon/star/text/image"},
        "text": {"type": "string", "description": "图形上显示的文字"},
        "x": {"type": "number", "description": "X坐标(画布中心为原点)", "default": 0},
        "y": {"type": "number", "description": "Y坐标(画布中心为原点)", "default": 0},
        "width": {"type": "number", "description": "宽度(像素)", "default": 100},
        "height": {"type": "number", "description": "高度(像素)", "default": 60},
        "background": {"type": "string", "description": "背景颜色(#RRGGBB格式)"},
        "color": {"type": "string", "description": "文字颜色(#RRGGBB格式)"},
        "fontSize": {"type": "number", "description": "文字大小(px)"},
        "borderWidth": {"type": "number", "description": "边框宽度(px)"},
        "borderColor": {"type": "string", "description": "边框颜色(#RRGGBB格式)"},
    }, "required": ["type", "x", "y"]}
)
def _tool_canvas_add_pen(args):
    return {"success": True, "data": args, "message": f"已创建{args.get('type', '图形')}节点"}


@ToolRegistry.register(
    "canvas_update_pen",
    "修改画布上现有图形的属性（位置、大小、样式、文字等）。",
    {"type": "object", "properties": {
        "pen_id": {"type": "string", "description": "要修改的图形ID"},
        "props": {"type": "object", "description": "要修改的属性键值对，如{\"x\": 100, \"text\": \"新文字\"}"},
    }, "required": ["pen_id", "props"]}
)
def _tool_canvas_update_pen(args):
    return {"success": True, "data": args, "message": f"已更新图形 {args.get('pen_id')}"}


@ToolRegistry.register(
    "canvas_delete_pen",
    "从画布上删除指定的图形/节点。",
    {"type": "object", "properties": {
        "pen_id": {"type": "string", "description": "要删除的图形ID"},
        "pen_ids": {"type": "array", "items": {"type": "string"}, "description": "批量删除的图形ID列表"},
    }, "required": []}
)
def _tool_canvas_delete_pen(args):
    count = 1
    if args.get("pen_ids"):
        count = len(args["pen_ids"])
    return {"success": True, "data": args, "message": f"已删除{count}个图形"}


@ToolRegistry.register(
    "canvas_add_line",
    "在两个图形之间创建连线。支持直线、曲线、折线、思维导图线。",
    {"type": "object", "properties": {
        "from_pen": {"type": "string", "description": "起始图形的ID"},
        "to_pen": {"type": "string", "description": "目标图形的ID"},
        "line_type": {"type": "string", "enum": ["straight", "curve", "polyline", "mind"], "description": "连线类型", "default": "straight"},
        "text": {"type": "string", "description": "连线上的文字标签"},
        "arrow": {"type": "string", "enum": ["start", "end", "both", "none"], "description": "箭头方向", "default": "end"},
        "color": {"type": "string", "description": "连线颜色(#RRGGBB)"},
        "lineWidth": {"type": "number", "description": "连线宽度(px)"},
    }, "required": ["from_pen", "to_pen"]}
)
def _tool_canvas_add_line(args):
    return {"success": True, "data": args, "message": f"已创建从 {args.get('from_pen')} 到 {args.get('to_pen')} 的连线"}


@ToolRegistry.register(
    "canvas_get_state",
    "获取当前画布的完整状态，包括所有图形(pens)和连线(lines)的列表。操作前应先调用此工具了解画布现状。",
    {"type": "object", "properties": {}, "required": []}
)
def _tool_canvas_get_state(args):
    return {"success": True, "data": {"pens": [], "lines": []}, "message": "当前画布状态（由前端填充实际数据）"}


@ToolRegistry.register(
    "canvas_clear",
    "清空画布上的所有图形和连线。此操作不可撤销，需要用户确认。",
    {"type": "object", "properties": {
        "confirm": {"type": "boolean", "description": "确认清空画布"},
    }, "required": ["confirm"]}
)
def _tool_canvas_clear(args):
    if not args.get("confirm"):
        return {"success": False, "error": "请确认清空画布操作"}
    return {"success": True, "data": {}, "message": "画布已清空"}


@ToolRegistry.register(
    "canvas_undo",
    "撤销画布上最近一次操作。",
    {"type": "object", "properties": {}, "required": []}
)
def _tool_canvas_undo(args):
    return {"success": True, "data": {}, "message": "已撤销"}


@ToolRegistry.register(
    "canvas_redo",
    "重做画布上最近一次被撤销的操作。",
    {"type": "object", "properties": {}, "required": []}
)
def _tool_canvas_redo(args):
    return {"success": True, "data": {}, "message": "已重做"}


# ══════════════════════════════════════════════════════════════════════════════
# Blueprint Management Tools
# ══════════════════════════════════════════════════════════════════════════════

@ToolRegistry.register(
    "blueprint_list",
    "列出所有已保存的蓝图，支持分页和筛选。",
    {"type": "object", "properties": {
        "page": {"type": "integer", "description": "页码", "default": 1},
        "page_size": {"type": "integer", "description": "每页数量", "default": 20},
        "keyword": {"type": "string", "description": "搜索关键词"},
    }, "required": []}
)
def _tool_blueprint_list(args):
    return {"success": True, "data": {"items": [], "total": 0}, "message": "蓝图列表（需连接数据库）"}


@ToolRegistry.register(
    "blueprint_load",
    "加载指定的蓝图到画布上，替换当前画布内容。",
    {"type": "object", "properties": {
        "blueprint_id": {"type": "string", "description": "要加载的蓝图ID"},
    }, "required": ["blueprint_id"]}
)
def _tool_blueprint_load(args):
    return {"success": True, "data": {"blueprint_id": args.get("blueprint_id")}, "message": f"已加载蓝图 {args.get('blueprint_id')}"}


@ToolRegistry.register(
    "blueprint_save",
    "将当前画布内容保存为蓝图。",
    {"type": "object", "properties": {
        "name": {"type": "string", "description": "蓝图名称"},
        "description": {"type": "string", "description": "蓝图描述"},
        "category": {"type": "string", "description": "分类"},
    }, "required": ["name"]}
)
def _tool_blueprint_save(args):
    return {"success": True, "data": {"name": args.get("name")}, "message": f"已保存蓝图「{args.get('name')}」"}


@ToolRegistry.register(
    "blueprint_search",
    "按关键词搜索蓝图。",
    {"type": "object", "properties": {
        "keyword": {"type": "string", "description": "搜索关键词"},
        "limit": {"type": "integer", "description": "返回数量上限", "default": 10},
    }, "required": ["keyword"]}
)
def _tool_blueprint_search(args):
    return {"success": True, "data": {"items": [], "keyword": args.get("keyword")}, "message": f"搜索「{args.get('keyword')}」结果"}


@ToolRegistry.register(
    "blueprint_export",
    "将当前画布导出为指定格式。",
    {"type": "object", "properties": {
        "format": {"type": "string", "enum": ["png", "svg", "json"], "description": "导出格式"},
        "scale": {"type": "number", "description": "缩放比例(PNG导出)", "default": 2},
    }, "required": ["format"]}
)
def _tool_blueprint_export(args):
    return {"success": True, "data": {"format": args.get("format")}, "message": f"已导出为 {args.get('format').upper()} 格式"}


# ══════════════════════════════════════════════════════════════════════════════
# Layout Tools
# ══════════════════════════════════════════════════════════════════════════════

@ToolRegistry.register(
    "layout_auto_arrange",
    "对画布上选中的图形进行自动排版布局。",
    {"type": "object", "properties": {
        "direction": {"type": "string", "enum": ["horizontal", "vertical", "grid"], "description": "排列方向", "default": "vertical"},
        "spacing": {"type": "number", "description": "间距(px)", "default": 40},
        "columns": {"type": "integer", "description": "网格列数(grid模式)", "default": 3},
    }, "required": []}
)
def _tool_layout_auto_arrange(args):
    return {"success": True, "data": args, "message": f"已按{args.get('direction', 'vertical')}方向自动排列"}


@ToolRegistry.register(
    "layout_align",
    "将选中的多个图形对齐。",
    {"type": "object", "properties": {
        "align": {"type": "string", "enum": ["left", "center", "right", "top", "middle", "bottom"], "description": "对齐方式"},
    }, "required": ["align"]}
)
def _tool_layout_align(args):
    return {"success": True, "data": args, "message": f"已按{args.get('align')}对齐"}


# ══════════════════════════════════════════════════════════════════════════════
# Auxiliary Tools
# ══════════════════════════════════════════════════════════════════════════════

@ToolRegistry.register(
    "file_search",
    "搜索文件管理器中的素材/文件。",
    {"type": "object", "properties": {
        "keyword": {"type": "string", "description": "文件名关键词"},
        "type": {"type": "string", "description": "文件类型筛选: image/svg/document"},
        "limit": {"type": "integer", "description": "返回数量", "default": 20},
    }, "required": []}
)
def _tool_file_search(args):
    return {"success": True, "data": {"items": []}, "message": "文件搜索结果（需连接存储）"}


@ToolRegistry.register(
    "code_generate",
    "根据描述生成JavaScript或JSON代码片段，可用于Monaco编辑器中。",
    {"type": "object", "properties": {
        "language": {"type": "string", "enum": ["javascript", "json"], "description": "代码语言"},
        "description": {"type": "string", "description": "代码需求描述"},
    }, "required": ["language", "description"]}
)
def _tool_code_generate(args):
    return {"success": True, "data": {"language": args.get("language"), "code": "// Generated code"}, "message": "代码已生成"}


# ══════════════════════════════════════════════════════════════════════════════
# Populate TOOL_SCHEMAS and run_tool_call
# ══════════════════════════════════════════════════════════════════════════════

TOOL_SCHEMAS = []  # populated below after all registrations


def _rebuild_schemas():
    """Rebuild TOOL_SCHEMAS from ToolRegistry."""
    global TOOL_SCHEMAS
    TOOL_SCHEMAS = ToolRegistry.get_schemas()


_rebuild_schemas()


def run_tool_call(tool_name, tool_args, tool_context, dispatcher=None,
                  llm_client=None, model=None, tracer=None, pheromone_sniff=""):
    """Execute a tool by name, dispatching sub-agents when needed.

    Returns (result_dict, cached_bool).
    """
    # Handle dispatch_agent — route to sub-agent system
    if tool_name == "dispatch_agent" and dispatcher:
        agent_name = tool_args.get("agent_name", "")
        task = tool_args.get("task", "")
        if agent_name and task:
            ctx = {**tool_context, "_pheromone": pheromone_sniff}
            result = dispatcher.dispatch(llm_client, agent_name, task, ctx, model=model, tracer=tracer)
            return result, False

    # Handle ask_peer — lightweight sub-agent query
    if tool_name == "ask_peer" and dispatcher:
        agent_name = tool_args.get("agent_name", "")
        question = tool_args.get("question", "")
        if agent_name and question:
            ctx = {**tool_context, "_pheromone": pheromone_sniff}
            result = dispatcher.handle_peer_query(llm_client, agent_name, question, ctx, model=model, tracer=tracer)
            return result, False

    # Normal tool execution via ToolRegistry
    result = ToolRegistry.execute(tool_name, tool_args, tool_context)
    return result, False
