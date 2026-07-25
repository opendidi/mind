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
            "description": "list(列出所有宏), run(执行指定宏), save(保存为宏)",
        },
        "name": {"type": "string", "description": "[run/save] 宏名称"},
        "description": {"type": "string", "description": "[save] 宏描述"},
        "steps": {
            "type": "array", "items": {"type": "object"},
            "description": "[save] 操作步骤列表, 每步含 tool, action, args",
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
    "操作宏管理: 保存、列出、执行画布操作宏。action: list(列出所有), run(执行指定宏), save(保存宏)",
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
                macros = {k.decode() if isinstance(k, bytes) else k:
                         json.loads(v.decode() if isinstance(v, bytes) else v)
                         for k, v in r.hgetall(key).items()}
            except Exception:
                logging.warning("Macro list failed for user %s", user_id)
        if not macros:
            return {"success": True, "data": {"macros": []},
                    "message": "暂无保存的操作宏。创建宏：使用 macro(action='save', name='名称', steps=[...])"}
        items = [{"name": k, "description": v.get("description", ""),
                  "steps_count": len(v.get("steps", []))} for k, v in macros.items()]
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
            return {"success": False, "error": f"未找到宏「{name}」。使用 macro(action='list') 查看所有可用宏。"}
        return {
            "success": True,
            "data": {"name": name, "steps": macro.get("steps", [])},
            "message": f"执行宏「{name}」: {macro.get('description', '')}，共 {len(macro.get('steps', []))} 步。请按 steps 顺序依次调用对应工具。",
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
                "message": f"已保存宏「{name}」，共 {len(steps)} 步。使用 macro(action='run', name='{name}') 执行。"}

    return {"success": False, "error": f"未知的 action: {action}"}
