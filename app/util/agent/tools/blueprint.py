# -*- coding: UTF-8 -*-
"""Blueprint management tools — load, save, and manipulate blueprint diagrams."""

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
# Template loading helper
# ══════════════════════════════════════════════════════════════════════════════

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "blueprint_templates")


def _get_template_path(template_name):
    """Resolve the path to a blueprint template JSON file."""
    return os.path.normpath(os.path.join(_TEMPLATES_DIR, f"{template_name}.json"))


def _load_template(name, user_id):
    """Load a template JSON file and return its dict representation."""
    path = _get_template_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Blueprint 模板加载失败 {name}: {e}")
        return None


def _parse_pens(raw_pens):
    """Parse pens from a blueprint record — handles both string and list inputs."""
    if isinstance(raw_pens, list):
        return raw_pens
    if isinstance(raw_pens, str):
        try:
            parsed = json.loads(raw_pens)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _load_blueprint_pens(blueprint_id, user_id):
    """Load a blueprint's parsed pen list from the DB."""
    data = BlueprintMysqlHandler.find(blueprint_id, user_id)
    if not data:
        return None, f"未找到蓝图: {blueprint_id}"
    pens = _parse_pens(data.get("pens", []))
    return data, pens

# ══════════════════════════════════════════════════════════════════════════════
# Blueprint Management Tools
# ══════════════════════════════════════════════════════════════════════════════


@ToolRegistry.register(
    "blueprint_list",
    "列出所有已保存的蓝图，支持分页和筛选。",
    {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "description": "页码", "default": 1},
            "page_size": {"type": "integer", "description": "每页数量", "default": 20},
            "keyword": {"type": "string", "description": "搜索关键词"},
        },
        "required": [],
    },
)
def _tool_blueprint_list(args):
    user_id = args.get("user_id", "")
    if not user_id:
        return {"success": False, "error": "缺少用户ID，无法查询图纸"}
    data = BlueprintMysqlHandler.query_list(
        {
            "current": args.get("page", 1),
            "page_size": args.get("page_size", 20),
            "keyword": args.get("keyword"),
        },
        user_id,
    )
    if data:
        return {"success": True, "data": data, "message": f"共 {data.get('total', 0)} 条图纸"}
    return {"success": True, "data": {"list": [], "total": 0}, "message": "暂无图纸"}


@ToolRegistry.register(
    "blueprint_load",
    "加载指定的蓝图到画布上，替换当前画布内容。",
    {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string", "description": "要加载的蓝图ID"},
        },
        "required": ["blueprint_id"],
    },
)
def _tool_blueprint_load(args):
    user_id = args.get("user_id", "")
    blueprint_id = args.get("blueprint_id")
    if not blueprint_id:
        return {"success": False, "error": "缺少 blueprint_id"}
    data = BlueprintMysqlHandler.find(blueprint_id, user_id)
    if data:
        return {"success": True, "data": data, "message": f"已加载图纸: {data.get('name', '')}"}
    return {"success": False, "error": f"未找到图纸: {blueprint_id}"}


@ToolRegistry.register(
    "blueprint_save",
    "将当前画布内容保存为蓝图。",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "蓝图名称"},
            "description": {"type": "string", "description": "蓝图描述"},
            "category": {"type": "string", "description": "分类"},
        },
        "required": ["name"],
    },
)
def _tool_blueprint_save(args):
    user_id = args.get("user_id", "")
    name = args.get("name", "").strip()
    if not name:
        return {"success": False, "error": "图纸名称不能为空"}

    # Use canvas_snapshot from tool_ctx (injected by AgentSession) for atomic save
    canvas_snapshot = args.get("canvas_snapshot")
    pens = ""
    if canvas_snapshot and isinstance(canvas_snapshot, list):
        pens = json.dumps(canvas_snapshot, ensure_ascii=False)
    else:
        # Fallback: use pens arg if provided directly (legacy path)
        pens = args.get("pens", "")

    ok, result = BlueprintMysqlHandler.add(
        {
            "name": name,
            "color": args.get("color", ""),
            "penBackground": args.get("penBackground", ""),
            "background": args.get("background", ""),
            "bkImage": args.get("bkImage", ""),
            "grid": args.get("grid", ""),
            "gridColor": args.get("gridColor", ""),
            "gridSize": args.get("gridSize", ""),
            "gridRotate": args.get("gridRotate", ""),
            "rule": args.get("rule", ""),
            "ruleColor": args.get("ruleColor", ""),
            "initJs": args.get("initJs", ""),
            "pens": pens,
            "https": args.get("https", ""),
            "thumbnail": args.get("thumbnail", ""),
        },
        user_id,
    )
    if ok:
        return {"success": True, "data": {"id": result, "name": name}, "message": f"已保存图纸「{name}」"}
    return {"success": False, "error": f"保存失败: {result}"}


@ToolRegistry.register(
    "blueprint_search",
    "按关键词搜索蓝图。",
    {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回数量上限", "default": 10},
        },
        "required": ["keyword"],
    },
)
def _tool_blueprint_search(args):
    user_id = args.get("user_id", "")
    keyword = args.get("keyword")
    if not keyword:
        return {"success": False, "error": "缺少搜索关键词"}
    data = BlueprintMysqlHandler.query_list(
        {
            "current": 1,
            "page_size": args.get("limit", 10),
            "keyword": keyword,
        },
        user_id,
    )
    if data:
        return {"success": True, "data": data, "message": f"搜索「{keyword}」找到 {data.get('total', 0)} 条结果"}
    return {"success": True, "data": {"list": [], "total": 0}, "message": f"搜索「{keyword}」无结果"}


@ToolRegistry.register(
    "blueprint_export",
    "将当前画布导出为指定格式。",
    {
        "type": "object",
        "properties": {
            "format": {"type": "string", "enum": ["png", "svg", "json"], "description": "导出格式"},
            "scale": {"type": "number", "description": "缩放比例(PNG导出)", "default": 2},
        },
        "required": ["format"],
    },
)
def _tool_blueprint_export(args):
    return {
        "success": True,
        "data": {"format": args.get("format")},
        "message": f"已导出为 {args.get('format').upper()} 格式",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Cross-blueprint operation tools
# ══════════════════════════════════════════════════════════════════════════════


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
    """Compare two blueprints, returning added, removed, modified, and unchanged pens."""
    user_id = args.get("user_id", "")
    source_id = args.get("source_id")
    target_id = args.get("target_id")

    if not source_id or not target_id:
        return {"success": False, "error": "缺少 source_id 或 target_id"}

    # Load both blueprints
    source_data, source_pens = _load_blueprint_pens(str(source_id), user_id)
    if source_data is None:
        return {"success": False, "error": source_pens}

    target_data, target_pens = _load_blueprint_pens(str(target_id), user_id)
    if target_data is None:
        return {"success": False, "error": target_pens}

    # Build lookup maps by pen ID
    source_map = {p.get("id"): p for p in source_pens if p.get("id")}
    target_map = {p.get("id"): p for p in target_pens if p.get("id")}

    source_ids = set(source_map.keys())
    target_ids = set(target_map.keys())

    added_ids = target_ids - source_ids
    removed_ids = source_ids - target_ids
    common_ids = source_ids & target_ids

    added = [target_map[pid] for pid in sorted(added_ids)]
    removed = [source_map[pid] for pid in sorted(removed_ids)]

    modified = []
    unchanged = []
    for pid in sorted(common_ids):
        if json.dumps(source_map[pid], sort_keys=True, ensure_ascii=False) != json.dumps(
            target_map[pid], sort_keys=True, ensure_ascii=False
        ):
            modified.append({"id": pid, "source": source_map[pid], "target": target_map[pid]})
        else:
            unchanged.append({"id": pid})

    return {
        "success": True,
        "data": {
            "source": {"id": source_id, "name": source_data.get("name", "")},
            "target": {"id": target_id, "name": target_data.get("name", "")},
            "added": {"count": len(added), "pens": added},
            "removed": {"count": len(removed), "pens": removed},
            "modified": {"count": len(modified), "pens": modified},
            "unchanged": {"count": len(unchanged), "ids": [u["id"] for u in unchanged]},
        },
        "message": f"对比完成：新增 {len(added)}，删除 {len(removed)}，修改 {len(modified)}，不变 {len(unchanged)}",
    }


@ToolRegistry.register(
    "blueprint_merge",
    "合并两个蓝图。mode: add(只追加新节点), replace(同名覆盖), preview(仅预览)。",
    {
        "type": "object",
        "properties": {
            "source_id": {"type": "integer", "description": "源蓝图ID"},
            "target_id": {"type": "integer", "description": "目标蓝图ID"},
            "mode": {
                "type": "string",
                "enum": ["add", "replace", "preview"],
                "description": "合并模式",
                "default": "add",
            },
        },
        "required": ["source_id", "target_id"],
    },
)
def _tool_blueprint_merge(args):
    """Merge two blueprints with preview, add-only, or replace semantics."""
    user_id = args.get("user_id", "")
    source_id = args.get("source_id")
    target_id = args.get("target_id")
    mode = args.get("mode", "add")

    if not source_id or not target_id:
        return {"success": False, "error": "缺少 source_id 或 target_id"}

    # Load both blueprints
    source_data, source_pens = _load_blueprint_pens(str(source_id), user_id)
    if source_data is None:
        return {"success": False, "error": source_pens}

    _, target_pens = _load_blueprint_pens(str(target_id), user_id)
    if _ is None:
        return {"success": False, "error": target_pens}

    source_map = {p.get("id"): p for p in source_pens if p.get("id")}
    target_map = {p.get("id"): p for p in target_pens if p.get("id")}

    source_ids = set(source_map.keys())
    target_ids = set(target_map.keys())

    new_ids = source_ids - target_ids
    overlap_ids = source_ids & target_ids

    result_pens = list(target_pens)  # start with target pens

    if mode == "preview":
        added = [source_map[pid] for pid in sorted(new_ids)]
        replaced = []
        if overlap_ids:
            replaced = [
                {"id": pid, "before": target_map[pid], "after": source_map[pid]}
                for pid in sorted(overlap_ids)
            ]
        return {
            "success": True,
            "data": {
                "mode": "preview",
                "new_pens": {"count": len(added), "pens": added},
                "overwrite_pens": {"count": len(replaced), "pens": replaced},
            },
            "message": f"预览：将新增 {len(added)} 个节点，覆盖 {len(replaced)} 个节点",
        }

    if mode == "add":
        # Append only new pens (not present in target)
        for pid in sorted(new_ids):
            result_pens.append(source_map[pid])
        changed = len(new_ids)

    elif mode == "replace":
        # Overwrite matching pens by ID; append new ones
        result_map = {p.get("id"): p for p in result_pens if p.get("id")}
        result_map.update(source_map)  # source pens win on conflict
        result_pens = list(result_map.values())
        changed = len(source_ids)

    # Serialize merged pens for DB update
    merged_pens_json = json.dumps(result_pens, ensure_ascii=False)
    ok, err = BlueprintMysqlHandler.modify(
        str(target_id),
        user_id,
        pens=merged_pens_json,
    )
    if not ok:
        return {"success": False, "error": f"合并保存失败: {err}"}

    return {
        "success": True,
        "data": {
            "mode": mode,
            "target_id": target_id,
            "pens_count": len(result_pens),
            "changed": changed,
        },
        "message": f"合并完成（{mode}模式）：共 {len(result_pens)} 个节点，变更 {changed} 个",
    }


@ToolRegistry.register(
    "blueprint_from_template",
    "从预置模板创建新蓝图。",
    {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "enum": [
                    "three-tier-architecture",
                    "microservices-mesh",
                    "data-pipeline",
                    "class-hierarchy",
                    "swot-analysis",
                ],
                "description": "模板名称",
            },
            "name": {"type": "string", "description": "新蓝图名称"},
            "description": {"type": "string", "description": "新蓝图描述"},
        },
        "required": ["template", "name"],
    },
)
def _tool_blueprint_from_template(args):
    """Create a new blueprint from a predefined template."""
    user_id = args.get("user_id", "")
    template_name = args.get("template")
    name = args.get("name", "").strip()
    description = args.get("description", "").strip()

    if not user_id:
        return {"success": False, "error": "缺少用户ID"}
    if not template_name:
        return {"success": False, "error": "缺少模板名称"}
    if not name:
        return {"success": False, "error": "蓝图名称不能为空"}

    template = _load_template(template_name, user_id)
    if template is None:
        available = [
            "three-tier-architecture",
            "microservices-mesh",
            "data-pipeline",
            "class-hierarchy",
            "swot-analysis",
        ]
        return {
            "success": False,
            "error": f"未找到模板: {template_name}，可用模板: {', '.join(available)}",
        }

    pens = template.get("pens", [])
    lines = template.get("lines", [])

    # Merge lines into pens as connection data if the canvas format expects it,
    # or store lines alongside pens. The blueprint model stores everything as 'pens' JSON.
    blueprint_pens = json.dumps(pens, ensure_ascii=False)
    blueprint_lines = json.dumps(lines, ensure_ascii=False)

    ok, result = BlueprintMysqlHandler.add(
        {
            "name": name,
            "description": description,
            "background": template.get("background", "#ffffff"),
            "grid": template.get("grid", False),
            "pens": blueprint_pens,
            "https": blueprint_lines,
            "color": "",
            "penBackground": "",
            "bkImage": "",
            "gridColor": "",
            "gridSize": "",
            "gridRotate": "",
            "rule": "",
            "ruleColor": "",
            "initJs": "",
            "thumbnail": "",
        },
        user_id,
    )
    if not ok:
        return {"success": False, "error": f"模板创建失败: {result}"}

    return {
        "success": True,
        "data": {"id": result, "name": name, "template": template_name},
        "message": f"已从模板「{template_name}」创建蓝图「{name}」",
    }
