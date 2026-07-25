# -*- coding: UTF-8 -*-
"""canvas_organize tool — group, ungroup, lock, unlock, toggle_visibility, auto_arrange, align."""
from app.util.agent.tools.canvas._base import new_pen_id, resolve_pen_ids, get_shadow
from app.util.tool_registry import ToolRegistry


@ToolRegistry.register(
    "canvas_organize",
    "画布图形组织布局操作。action: group(组合), ungroup(取消组合), lock(锁定), "
    "unlock(解锁), toggle_visibility(显隐), auto_arrange(自动排列), align(对齐)",
    {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "group",
                    "ungroup",
                    "lock",
                    "unlock",
                    "toggle_visibility",
                    "auto_arrange",
                    "align",
                ],
                "description": "操作类型",
            },
            # group / ungroup / lock / unlock / visibility params
            "pen_id": {"type": "string", "description": "图形ID"},
            "pen_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "批量操作的图形ID列表",
            },
            "visible": {"type": "boolean", "description": "[toggle_visibility]是否可见"},
            # auto_arrange params
            "direction": {
                "type": "string",
                "enum": ["horizontal", "vertical", "grid"],
                "description": "[auto_arrange]排列方向",
                "default": "vertical",
            },
            "spacing": {"type": "number", "description": "[auto_arrange]间距(px)", "default": 40},
            "columns": {"type": "integer", "description": "[auto_arrange]网格列数(grid模式)", "default": 3},
            "algorithm": {
                "type": "string",
                "enum": ["grid", "tree", "force", "layered"],
                "description": "[auto_arrange]布局算法",
                "default": "grid",
            },
            "root_pen_id": {
                "type": "string",
                "description": "[auto_arrange]根节点ID(tree/force模式)",
            },
            # align params
            "align": {
                "type": "string",
                "enum": ["left", "center", "right", "top", "middle", "bottom"],
                "description": "[align]对齐方式",
            },
        },
        "required": ["action"],
    },
)
def _tool_canvas_organize(args):
    action = args.get("action", "")
    if not action:
        return {
            "success": False,
            "error": "缺少必填参数: action，请指定画布组织操作类型。支持: group/ungroup/lock/unlock/toggle_visibility/auto_arrange/align",
        }
    if action == "group":
        pen_ids = resolve_pen_ids(args)
        if len(pen_ids) < 2:
            return {"success": False, "error": "至少需要两个图形才能组合"}
        # Update canvas shadow: add a group pen tracking component IDs
        shadow = get_shadow(args)
        if shadow:
            group_id = new_pen_id()
            pen_data = {"type": "group", "text": "group", "x": 0, "y": 0, "width": 0, "height": 0}
            shadow.add_pen(group_id, pen_data)
        return {
            "success": True,
            "data": {"pen_ids": pen_ids},
            "message": f"已组合 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "ungroup":
        pen_id = args.get("pen_id", "")
        if not pen_id:
            return {"success": False, "error": "pen_id 不能为空"}
        # Update canvas shadow: remove the group pen
        shadow = get_shadow(args)
        if shadow:
            shadow.remove_pen(pen_id)
        return {
            "success": True,
            "data": {"pen_id": pen_id},
            "message": f"已取消组合：{pen_id}",
        }
    elif action == "lock":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "locked": 2},
            "message": f"已锁定 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "unlock":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "locked": False},
            "message": f"已解锁 {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "toggle_visibility":
        pen_ids = resolve_pen_ids(args)
        if not pen_ids:
            return {"success": False, "error": "pen_id 或 pen_ids 不能为空"}
        visible = args.get("visible", False)
        label = "显示" if visible else "隐藏"
        return {
            "success": True,
            "data": {"pen_ids": pen_ids, "visible": visible},
            "message": f"已{label} {len(pen_ids)} 个图形：{', '.join(pen_ids)}",
        }
    elif action == "auto_arrange":
        direction = args.get("direction", "vertical")
        spacing = args.get("spacing", 40)
        algorithm = args.get("algorithm", "grid")
        return {
            "success": True,
            "data": {
                "direction": direction,
                "spacing": spacing,
                "columns": args.get("columns", 3),
                "algorithm": algorithm,
                "root_pen_id": args.get("root_pen_id", ""),
            },
            "message": f"已按{direction}方向自动排列（{algorithm}算法），间距{spacing}px",
        }
    elif action == "align":
        align = args.get("align", "")
        if not align:
            return {"success": False, "error": "align 不能为空，请指定对齐方式"}
        return {"success": True, "data": {"align": align}, "message": f"已按{align}对齐"}
    return {
        "success": False,
        "error": f"未知的 action: {action}，支持: group/ungroup/lock/unlock/toggle_visibility/auto_arrange/align",
    }
