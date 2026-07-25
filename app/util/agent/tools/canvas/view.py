# -*- coding: UTF-8 -*-
"""canvas_view tool — viewport and canvas properties (set_props, fit_view, check_empty) + P2-2 snapshot stubs."""
from app.util.tool_registry import ToolRegistry


@ToolRegistry.register(
    "canvas_view",
    "画布视图与属性操作。action: set_props(设置画布级属性), fit_view(自适应视口), "
    "check_empty(检查画布是否为空), "
    "list_snapshots(快照列表,预留), restore_snapshot(恢复快照,预留), save_snapshot(保存快照,预留)",
    {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "set_props",
                    "fit_view",
                    "check_empty",
                    "list_snapshots",
                    "restore_snapshot",
                    "save_snapshot",
                ],
                "description": "操作类型",
            },
            # set_props params
            "background": {"type": "string", "description": "[set_props]画布背景颜色(#RRGGBB)"},
            "bkImage": {"type": "string", "description": "[set_props]画布背景图片URL"},
            "grid": {"type": "boolean", "description": "[set_props]是否显示网格"},
            "gridColor": {"type": "string", "description": "[set_props]网格颜色(#RRGGBB)"},
            "gridSize": {"type": "number", "description": "[set_props]网格大小(px)"},
            "rule": {"type": "boolean", "description": "[set_props]是否显示标尺"},
            "ruleColor": {"type": "string", "description": "[set_props]标尺颜色(#RRGGBB)"},
            "color": {"type": "string", "description": "[set_props]画布默认文字颜色"},
            "penBackground": {"type": "string", "description": "[set_props]画布默认图形背景色"},
            # fit_view params
            "fit": {"type": "boolean", "description": "[fit_view]是否自适应(true=fitView, false=还原100%)", "default": True},
            "padding": {"type": "number", "description": "[fit_view]内边距(px)", "default": 24},
            # save_snapshot params
            "snapshot_name": {"type": "string", "description": "[save_snapshot]快照名称"},
        },
        "required": ["action"],
    },
)
def _tool_canvas_view(args):
    action = args.get("action", "")
    if not action:
        return {
            "success": False,
            "error": "缺少必填参数: action，请指定画布视图操作类型。支持: set_props/fit_view/check_empty/list_snapshots/restore_snapshot/save_snapshot",
        }
    if action == "set_props":
        props_desc = ", ".join(f"{k}={v}" for k, v in args.items() if k != "action" and v is not None)
        return {
            "success": True,
            "data": {k: v for k, v in args.items() if k != "action"},
            "message": f"画布属性已更新：{props_desc}",
        }
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
                "message": "无法获取画布状态（用户可能不在画布页面），假设画布为空。不要再查询状态——立即调用 canvas_edit(action='clear', confirm=true) 清空画布，然后用 add_diagram 绘制图表。绘制完成后用 blueprint_save 保存。",
            }

        empty = len(pens) == 0 and len(lines) == 0
        if empty:
            msg = "画布当前为空，可以自由绘制。"
        else:
            msg = f"画布当前有 {len(pens)} 个图形和 {len(lines)} 条连线。调用 canvas_edit(action='clear', confirm=true) 清空后绘制即可。"

        return {
            "success": True,
            "data": {
                "empty": empty,
                "pen_count": len(pens),
                "line_count": len(lines),
                "canvas_available": True,
            },
            "message": msg,
        }
    elif action == "list_snapshots":
        try:
            from app.util.agent.state_snapshot import SnapshotManager

            session_id = args.get("_session_id", "")
            versions = SnapshotManager.list_versions(session_id)
            return {
                "success": True,
                "data": {"snapshots": versions},
                "message": f"共 {len(versions)} 个快照" if versions else "暂无可用快照",
            }
        except Exception as e:
            return {
                "success": True,
                "data": {"snapshots": []},
                "message": f"快照功能暂不可用: {e}",
            }

    elif action == "restore_snapshot":
        version = args.get("version")
        if version is None:
            return {"success": False, "error": "version 不能为空"}
        try:
            from app.util.agent.state_snapshot import SnapshotManager

            session_id = args.get("_session_id", "")
            data = SnapshotManager.restore(session_id, version)
            return {
                "success": True,
                "data": data,
                "message": f"已回滚到版本 {version}，前端将应用画布状态",
            }
        except Exception as e:
            return {"success": False, "error": f"回滚失败: {e}"}

    elif action == "save_snapshot":
        label = args.get("label", "")
        try:
            from app.util.agent.state_snapshot import SnapshotManager

            session_id = args.get("_session_id", "")
            ctx = args.get("_canvas_context") or {}
            SnapshotManager.save(session_id, ctx, description=label or "manual")
            return {
                "success": True,
                "data": {"label": label or "manual"},
                "message": f"已保存快照「{label or 'manual'}」",
            }
        except Exception as e:
            return {"success": False, "error": f"保存快照失败: {e}"}
    return {
        "success": False,
        "error": f"未知的 action: {action}，支持: set_props/fit_view/check_empty/list_snapshots/restore_snapshot/save_snapshot",
    }
