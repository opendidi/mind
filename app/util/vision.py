# -*- coding: UTF-8 -*-
"""
Vision API handler — analyze images using OpenAI-compatible vision models
"""
import base64
import json
import logging
import requests
from openai import OpenAI
from app.config import LLM_TIMEOUT, vision_config

api_key = vision_config["key"]
base_url = vision_config["base_url"]
model = vision_config["model"]
timeout = LLM_TIMEOUT

_vision_client = (
    OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    if api_key and base_url
    else None
)


class VisionHandler:

    @staticmethod
    def _image_to_base64(image_url):
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
    def analyze_image(image_url, prompt, task_type="describe"):
        if not _vision_client:
            return False, "Vision API 未配置，请设置 VISION_API_KEY 和 VISION_BASE_URL"

        img_src = VisionHandler._image_to_base64(image_url) or image_url

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": img_src}},
            ],
        }]

        try:
            response = _vision_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
                timeout=60,
            )
            content = response.choices[0].message.content

            if task_type == "describe":
                return VisionHandler._parse_describe(content)
            elif task_type == "classify":
                return VisionHandler._parse_classify(content)
            elif task_type == "detect":
                return VisionHandler._parse_detect(content)
            return True, {"raw": content}

        except Exception as ex:
            logging.warning("Vision API 调用失败: %s", ex)
            return False, str(ex)

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
