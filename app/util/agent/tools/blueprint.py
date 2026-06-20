# -*- coding: UTF-8 -*-
"""Blueprint management tools.

import json
import logging
import os
import re
import tempfile
import uuid
from html.parser import HTMLParser

import requests

from app.util.tool_registry import ToolRegistry
from app.util.vision import VisionHandler
from app.package.module.blueprint_mysql import BlueprintMysqlHandler

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
    user_id = args.get("user_id", "")
    if not user_id:
        return {"success": False, "error": "缺少用户ID，无法查询图纸"}
    data = BlueprintMysqlHandler.query_list({
        'current': args.get('page', 1),
        'page_size': args.get('page_size', 20),
        'keyword': args.get('keyword'),
    }, user_id)
    if data:
        return {"success": True, "data": data, "message": f"共 {data.get('total', 0)} 条图纸"}
    return {"success": True, "data": {"list": [], "total": 0}, "message": "暂无图纸"}


@ToolRegistry.register(
    "blueprint_load",
    "加载指定的蓝图到画布上，替换当前画布内容。",
    {"type": "object", "properties": {
        "blueprint_id": {"type": "string", "description": "要加载的蓝图ID"},
    }, "required": ["blueprint_id"]}
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
    {"type": "object", "properties": {
        "name": {"type": "string", "description": "蓝图名称"},
        "description": {"type": "string", "description": "蓝图描述"},
        "category": {"type": "string", "description": "分类"},
    }, "required": ["name"]}
)
def _tool_blueprint_save(args):
    user_id = args.get("user_id", "")
    name = args.get("name", "").strip()
    if not name:
        return {"success": False, "error": "图纸名称不能为空"}
    ok, result = BlueprintMysqlHandler.add({
        'name': name,
        'color': args.get('color', ''),
        'penBackground': args.get('penBackground', ''),
        'background': args.get('background', ''),
        'bkImage': args.get('bkImage', ''),
        'grid': args.get('grid', ''),
        'gridColor': args.get('gridColor', ''),
        'gridSize': args.get('gridSize', ''),
        'gridRotate': args.get('gridRotate', ''),
        'rule': args.get('rule', ''),
        'ruleColor': args.get('ruleColor', ''),
        'initJs': args.get('initJs', ''),
        'pens': args.get('pens', ''),
        'https': args.get('https', ''),
        'thumbnail': args.get('thumbnail', ''),
    }, user_id)
    if ok:
        return {"success": True, "data": {"id": result, "name": name}, "message": f"已保存图纸「{name}」"}
    return {"success": False, "error": f"保存失败: {result}"}


@ToolRegistry.register(
    "blueprint_search",
    "按关键词搜索蓝图。",
    {"type": "object", "properties": {
        "keyword": {"type": "string", "description": "搜索关键词"},
        "limit": {"type": "integer", "description": "返回数量上限", "default": 10},
    }, "required": ["keyword"]}
)
def _tool_blueprint_search(args):
    user_id = args.get("user_id", "")
    keyword = args.get("keyword")
    if not keyword:
        return {"success": False, "error": "缺少搜索关键词"}
    data = BlueprintMysqlHandler.query_list({
        'current': 1,
        'page_size': args.get('limit', 10),
        'keyword': keyword,
    }, user_id)
    if data:
        return {"success": True, "data": data, "message": f"搜索「{keyword}」找到 {data.get('total', 0)} 条结果"}
    return {"success": True, "data": {"list": [], "total": 0}, "message": f"搜索「{keyword}」无结果"}


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

