# -*- coding: UTF-8 -*-
"""
Vision API handler — analyze images using OpenAI-compatible vision models.
DeepSeek 已原生支持视觉识别，默认复用 DEEPSEEK_API_KEY，无需额外配置。
"""
import base64
import json
import logging
import requests
from openai import OpenAI
from app.config import LLM_TIMEOUT, vision_config, deepseek_config

# ── Vision client 初始化 ──────────────────────────────────────────────────
# 优先使用 vision_config，未单独配置时自动回退使用 deepseek_config
_vision_api_key = vision_config["key"] or deepseek_config["key"]
_vision_base_url = vision_config["base_url"] or deepseek_config["base_url"]
_vision_model = vision_config["model"]

_vision_client = (
    OpenAI(api_key=_vision_api_key, base_url=_vision_base_url, timeout=LLM_TIMEOUT)
    if _vision_api_key and _vision_base_url
    else None
)


def _ensure_client():
    """Lazy re-check in case config was loaded before env vars were set."""
    global _vision_client, _vision_api_key, _vision_base_url
    if _vision_client is not None:
        return True
    _vision_api_key = vision_config["key"] or deepseek_config["key"]
    _vision_base_url = vision_config["base_url"] or deepseek_config["base_url"]
    if _vision_api_key and _vision_base_url:
        _vision_client = OpenAI(api_key=_vision_api_key, base_url=_vision_base_url, timeout=LLM_TIMEOUT)
        return True
    return False


class VisionHandler:

    @staticmethod
    def _image_to_base64(image_url):
        """Download an image from URL and convert to data URL format."""
        try:
            resp = requests.get(image_url, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return f"data:{content_type};base64,{b64}"
        except Exception as ex:
            logging.warning("图片下载失败, 尝试直接使用URL: %s", ex)
            return None

    @staticmethod
    def _is_data_url(src: str) -> bool:
        """Check if a string is already a data URL (e.g. data:image/png;base64,...)."""
        return isinstance(src, str) and src.startswith("data:")

    @staticmethod
    def analyze_image(image_url, prompt, task_type="describe"):
        """分析一张图片（通过 URL）。先下载转 base64，再发送给视觉模型。"""
        if not _vision_client and not _ensure_client():
            return False, "Vision API 未配置，请设置 DEEPSEEK_API_KEY 或 VISION_API_KEY"

        img_src = VisionHandler._image_to_base64(image_url) or image_url
        return VisionHandler._call_vision(img_src, prompt, task_type)

    @staticmethod
    def analyze_base64(image_data, prompt, task_type="describe"):
        """直接分析 base64 格式的图片（data URL），跳过下载步骤。"""
        if not _vision_client and not _ensure_client():
            return False, "Vision API 未配置，请设置 DEEPSEEK_API_KEY 或 VISION_API_KEY"

        if not VisionHandler._is_data_url(image_data):
            return False, "image_data 必须是 data:image/...;base64,... 格式"
        return VisionHandler._call_vision(image_data, prompt, task_type)

    @staticmethod
    def analyze_images(image_list, prompt, task_type="describe"):
        """批量分析多张图片 — 所有图片 + 一个 prompt 一起发送给视觉模型。"""
        if not _vision_client and not _ensure_client():
            return False, "Vision API 未配置，请设置 DEEPSEEK_API_KEY 或 VISION_API_KEY"

        if not image_list:
            return False, "image_list 不能为空"

        # Build multimodal content: text + multiple images
        content = [{"type": "text", "text": prompt}]
        for src in image_list:
            if VisionHandler._is_data_url(src):
                content.append({"type": "image_url", "image_url": {"url": src}})
            else:
                # Try to download URL → base64
                b64 = VisionHandler._image_to_base64(src)
                content.append({"type": "image_url", "image_url": {"url": b64 or src}})

        messages = [{"role": "user", "content": content}]

        try:
            response = _vision_client.chat.completions.create(
                model=_vision_model,
                messages=messages,
                stream=False,
                timeout=60,
            )
            raw = response.choices[0].message.content
            return VisionHandler._parse_result(raw, task_type)
        except Exception as ex:
            logging.warning("Vision API 批量分析失败: %s", ex)
            return False, str(ex)

    @staticmethod
    def _call_vision(img_src, prompt, task_type):
        """Core vision API call with a single image."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": img_src}},
            ],
        }]

        try:
            response = _vision_client.chat.completions.create(
                model=_vision_model,
                messages=messages,
                stream=False,
                timeout=60,
            )
            content = response.choices[0].message.content
            return VisionHandler._parse_result(content, task_type)
        except Exception as ex:
            logging.warning("Vision API 调用失败: %s", ex)
            return False, str(ex)

    @staticmethod
    def _parse_result(content, task_type):
        """Parse vision response based on task type."""
        if task_type == "describe":
            return VisionHandler._parse_describe(content)
        elif task_type == "classify":
            return VisionHandler._parse_classify(content)
        elif task_type == "detect":
            return VisionHandler._parse_detect(content)
        return True, {"raw": content}

    # ── Prompt builders ──────────────────────────────────────────────────

    @staticmethod
    def build_describe_prompt():
        return json.dumps({
            "task": "describe",
            "instructions": "描述这张图片的内容、主要物体、场景类型和关键词。",
            "output_format": '{"scene_type":"","description":"","keywords":[]}',
        }, ensure_ascii=False)

    @staticmethod
    def build_classify_prompt(categories):
        cat_names = [c.get("name", "") for c in categories] if categories else []
        return json.dumps({
            "task": "classify",
            "categories": cat_names,
            "instructions": "将图片分类到最匹配的类别。",
            "output_format": '{"category":"","confidence":0.0}',
        }, ensure_ascii=False)

    @staticmethod
    def build_detect_prompt():
        return json.dumps({
            "task": "detect",
            "instructions": "检测图片中的物体，给出物体名称、位置描述和建议标注区域。",
            "output_format": '{"objects":[{"name":"","position":"","suggestion":""}]}',
        }, ensure_ascii=False)

    # ── Parsers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_describe(content):
        try:
            data = json.loads(content)
            return True, data
        except (json.JSONDecodeError, TypeError):
            return True, {"raw": content, "scene_type": "", "description": content, "keywords": []}

    @staticmethod
    def _parse_classify(content):
        try:
            data = json.loads(content)
            return True, data
        except (json.JSONDecodeError, TypeError):
            return True, {"raw": content, "category": "", "confidence": 0.0}

    @staticmethod
    def _parse_detect(content):
        try:
            data = json.loads(content)
            return True, data
        except (json.JSONDecodeError, TypeError):
            return True, {"raw": content, "objects": []}
