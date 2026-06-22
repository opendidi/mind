# -*- coding: UTF-8 -*-
"""Geo tools — geocode, reverse geocode, and coordinate utilities."""

import json
import logging
import os
import re
import tempfile
import uuid
from html.parser import HTMLParser

import requests

from app.config import AMAP_KEY
from app.package.module.blueprint_mysql import BlueprintMysqlHandler
from app.util.tool_registry import ToolRegistry
from app.util.vision import VisionHandler

# ══════════════════════════════════════════════════════════════════════════════
# Map / Geo Tools — geocode, regeocode
# ══════════════════════════════════════════════════════════════════════════════


def _validate_geocode(args):
    addr = args.get("address")
    if not addr or not isinstance(addr, str) or not addr.strip():
        return "address 必须是非空字符串"
    return None


@ToolRegistry.register(
    "geocode",
    "将地名/地址转换为经纬度坐标。用于路线规划前获取准确的起点/终点坐标。"
    "例如用户说'从北京到上海'，先调用此工具查询'北京'和'上海'获取坐标。"
    "返回：匹配地点列表，每个含坐标(lng,lat)、地址名称、行政区划。",
    {
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "要查询的地点名称或地址，如'广州塔'、'北京市朝阳区'"},
            "city": {"type": "string", "description": "限定城市范围（可选），如'北京'、'广州'"},
        },
        "required": ["address"],
    },
    validator=_validate_geocode,
)
def _tool_geocode(args):
    address = args["address"].strip()
    city = args.get("city", "").strip() or None

    if not AMAP_KEY:
        return {"success": False, "error": "AMAP_KEY 未配置，请联系管理员在 .env 中设置"}

    params = {"key": AMAP_KEY, "address": address, "output": "JSON"}
    if city:
        params["city"] = city

    try:
        resp = requests.get("https://restapi.amap.com/v3/geocode/geo", params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "1":
            return {"success": False, "error": f"高德地理编码失败: {data.get('info', '未知错误')}"}

        geocodes = data.get("geocodes") or []
        if not geocodes:
            return {"success": False, "error": f"未找到'{address}'的地理位置，请检查地名是否正确"}

        results = []
        for g in geocodes[:5]:
            loc = g.get("location", "")
            lng, lat = (loc.split(",") + ["0", "0"])[:2]
            results.append(
                {
                    "lng": float(lng),
                    "lat": float(lat),
                    "address": g.get("formatted_address", address),
                    "city": g.get("city", ""),
                    "district": g.get("district", ""),
                    "level": g.get("level", ""),
                }
            )
        return {"success": True, "data": {"total": len(results), "locations": results}}

    except requests.RequestException as e:
        return {"success": False, "error": f"地理编码请求失败: {str(e)}"}


def _validate_regeocode(args):
    lng = args.get("lng")
    lat = args.get("lat")
    if lng is None or lat is None:
        return "lng 和 lat 是必填项"
    try:
        float(lng)
        float(lat)
    except (TypeError, ValueError):
        return "lng 和 lat 必须是有效数字"
    return None


@ToolRegistry.register(
    "regeocode",
    "将经纬度坐标逆地理编码为地址信息。用于：用户提供坐标想知道是哪里。"
    "返回：格式化地址、省份、城市、区县、附近地标。",
    {
        "type": "object",
        "properties": {
            "lng": {"type": "number", "description": "经度（十进制），如 113.175"},
            "lat": {"type": "number", "description": "纬度（十进制），如 22.793"},
        },
        "required": ["lng", "lat"],
    },
    validator=_validate_regeocode,
)
def _tool_regeocode(args):
    lng = float(args["lng"])
    lat = float(args["lat"])

    if not AMAP_KEY:
        return {"success": False, "error": "AMAP_KEY 未配置，请联系管理员在 .env 中设置"}

    params = {"key": AMAP_KEY, "location": f"{lng},{lat}", "output": "JSON", "extensions": "base"}

    try:
        resp = requests.get("https://restapi.amap.com/v3/geocode/regeo", params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "1":
            return {"success": False, "error": f"高德逆地理编码失败: {data.get('info', '未知错误')}"}

        regeocode = data.get("regeocode") or {}
        addr = regeocode.get("addressComponent") or {}
        return {
            "success": True,
            "data": {
                "address": regeocode.get("formatted_address", ""),
                "country": addr.get("country", ""),
                "province": addr.get("province", ""),
                "city": addr.get("city", ""),
                "district": addr.get("district", ""),
                "township": addr.get("township", ""),
                "road": addr.get("streetNumber", {}).get("street", ""),
                "pois": [{"name": p.get("name"), "type": p.get("type")} for p in (regeocode.get("pois") or [])[:5]],
            },
        }
    except requests.RequestException as e:
        return {"success": False, "error": f"逆地理编码请求失败: {str(e)}"}
