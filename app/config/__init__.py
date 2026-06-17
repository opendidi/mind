'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-07-09 14:19:33
LastEditors: htang
LastEditTime: 2025-08-15 10:17:31
'''
# -*- coding: UTF-8 -*-

import os

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量

# 数据库连接参数
db_config = {
  'host': os.environ.get('DB_HOST', 'localhost'),
  'user': os.environ.get('DB_USER', 'root'),
  'passwd': os.environ.get('DB_PASSWORD', ''),
  'port': int(os.environ.get('DB_PORT', 3306)),
  'db': os.environ.get('DB_NAME', 'mind'),
  'cursorclass': pymysql.cursors.DictCursor
}

# Redis 配置（Agent 系统需要）
redis_config = {
    "host": os.environ.get("REDIS_HOST", "127.0.0.1"),
    "port": int(os.environ.get("REDIS_PORT", 6379)),
    "password": os.environ.get("REDIS_PASSWORD", ""),
}

# DeepSeek API 配置（主 LLM）
deepseek_config = {
    "key": os.environ.get("DEEPSEEK_API_KEY", ""),
    "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
}

# Fallback LLM tiers（可选 — 主 LLM 故障时自动切换）
fallback1_config = {
    "key": os.environ.get("FALLBACK1_API_KEY", ""),
    "base_url": os.environ.get("FALLBACK1_BASE_URL", ""),
    "model": os.environ.get("FALLBACK1_MODEL", ""),
}
fallback2_config = {
    "key": os.environ.get("FALLBACK2_API_KEY", ""),
    "base_url": os.environ.get("FALLBACK2_BASE_URL", ""),
    "model": os.environ.get("FALLBACK2_MODEL", ""),
}

# Vision API（图片分析，可选）
vision_config = {
    "key": os.environ.get("VISION_API_KEY", ""),
    "base_url": os.environ.get("VISION_BASE_URL", ""),
    "model": os.environ.get("VISION_MODEL", "gpt-4o"),
}

# LLM 统一超时（秒）
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", 120))

# Agent 默认模型
AGENT_DEFAULT_MODEL = os.environ.get("AGENT_DEFAULT_MODEL", "deepseek-chat")

# 前端站点地址
app_url = os.environ.get("APP_URL", "http://localhost:3100")

# 高德地图 Web API Key
AMAP_KEY = os.environ.get("AMAP_KEY", "")