"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-07-09 14:19:33
LastEditors: htang
LastEditTime: 2025-08-15 10:17:31
"""

# -*- coding: UTF-8 -*-

import os
import pathlib as _pathlib

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量

# 数据库连接参数
db_config = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "passwd": os.environ.get("DB_PASSWORD", ""),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "db": os.environ.get("DB_NAME", "mind"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
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
# DeepSeek 已原生支持视觉识别（vision/multimodal），不单独配置时自动复用 DEEPSEEK_API_KEY
# 如需使用其他视觉模型（如 gpt-4o），设置 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL 即可
vision_config = {
    "key": os.environ.get("VISION_API_KEY", ""),
    "base_url": os.environ.get("VISION_BASE_URL", ""),
    "model": os.environ.get("VISION_MODEL", "deepseek-chat"),
}

# LLM 统一超时（秒）
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", 120))

# Agent 默认模型
AGENT_DEFAULT_MODEL = os.environ.get("AGENT_DEFAULT_MODEL", "deepseek-chat")

# 前端站点地址
app_url = os.environ.get("APP_URL", "http://localhost:3100")

# 高德地图 Web API Key
AMAP_KEY = os.environ.get("AMAP_KEY", "")

# ══════════════════════════════════════════════════════════════════════════════
# OCR — 本地 OCR 模型路径（Vision LLM 不可用时的离线 fallback）
# ══════════════════════════════════════════════════════════════════════════════
_BASE_DIR = _pathlib.Path(__file__).resolve().parent.parent.parent  # mind/
OCR_MODEL_DIR = os.environ.get(
    "OCR_MODEL_DIR",
    str(_BASE_DIR / "models" / "ocr"),
)

# ══════════════════════════════════════════════════════════════════════════════
# TTS (Text-to-Speech) — ChatTTS 配置
# ══════════════════════════════════════════════════════════════════════════════
TTS_ENABLED = os.environ.get("TTS_ENABLED", "true").lower() == "true"
TTS_CACHE_DIR = os.environ.get("TTS_CACHE_DIR", os.path.join(os.path.dirname(__file__), "../../data/tts_cache"))
TTS_VOICE_SEED = int(os.environ.get("TTS_VOICE_SEED", 42))
TTS_MAX_TEXT_LENGTH = int(os.environ.get("TTS_MAX_TEXT_LENGTH", 5000))

# ══════════════════════════════════════════════════════════════════════════════
# API Security Monitor — api_guard.py 配置
# ══════════════════════════════════════════════════════════════════════════════
SECURITY_MONITOR_ENABLED = os.environ.get("SECURITY_MONITOR_ENABLED", "true").lower() == "true"
# 认证失败阈值 → 触发撞库封锁
SECURITY_AUTH_FAILURE_MAX = int(os.environ.get("SECURITY_AUTH_FAILURE_MAX", 10))
SECURITY_AUTH_FAILURE_WINDOW = int(os.environ.get("SECURITY_AUTH_FAILURE_WINDOW", 60))
# 短窗口突发阈值 → 触发高频封锁
SECURITY_BURST_MAX = int(os.environ.get("SECURITY_BURST_MAX", 30))
SECURITY_BURST_WINDOW = int(os.environ.get("SECURITY_BURST_WINDOW", 5))
# ID 遍历探测阈值
SECURITY_ID_PROBE_MAX = int(os.environ.get("SECURITY_ID_PROBE_MAX", 15))
SECURITY_ID_PROBE_WINDOW = int(os.environ.get("SECURITY_ID_PROBE_WINDOW", 60))
