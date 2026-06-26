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

from app.config import LLM_TIMEOUT, OCR_MODEL_DIR, deepseek_config, vision_config

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


def _vision_fallback_single(img_src: str, task_type: str):
    """Fallback for single-image vision methods when Vision LLM is unavailable."""
    if task_type == "ocr" and VisionHandler._is_data_url(img_src):
        r = LocalOCRHandler.extract_text(img_src)
        if r is not None:
            return True, r
    # For non-OCR or non-data-url images, report unavailability
    return False, "Vision API 未配置，请设置 DEEPSEEK_API_KEY 或 VISION_API_KEY"


# ── Local OCR（Vision LLM 不可用时的离线 fallback）──────────────────────

_LOCAL_OCR = None


def _get_local_ocr():
    """Lazy-init RapidOCR engine with explicit model directory."""
    global _LOCAL_OCR
    if _LOCAL_OCR is not None:
        return _LOCAL_OCR
    try:
        from pathlib import Path as _Path

        from rapidocr_onnxruntime import RapidOCR

        model_dir = _Path(OCR_MODEL_DIR)
        # Build explicit file paths per model
        kwargs: dict = {}
        kwargs = {
            "det_model_path": str(model_dir / "ch_PP-OCRv3_det_infer.onnx"),
            "rec_model_path": str(model_dir / "ch_PP-OCRv3_rec_infer.onnx"),
            "cls_model_path": str(model_dir / "ch_ppocr_mobile_v2.0_cls_infer.onnx"),
        }

        _LOCAL_OCR = RapidOCR(**kwargs)
        logging.info("Local OCR (RapidOCR) initialized, models in %s", model_dir)
    except ImportError:
        logging.info("rapidocr-onnxruntime not installed, local OCR unavailable")
        _LOCAL_OCR = False
    except Exception:
        logging.warning("Local OCR init failed", exc_info=True)
        _LOCAL_OCR = False
    return _LOCAL_OCR


# Max image dimension for local OCR (downscale if exceeded to prevent timeout)
_LOCAL_OCR_MAX_DIM = 2048
_LOCAL_OCR_TIMEOUT = 30  # seconds


class LocalOCRHandler:
    """Offline OCR engine using RapidOCR. Used as fallback when Vision LLM is unavailable."""

    @staticmethod
    def extract_text(image_data: str) -> dict:
        """Run local OCR on a base64 data URL image.

        Returns {"text": "...", "has_text": bool} or None on failure.
        """
        ocr = _get_local_ocr()
        if not ocr:
            return None
        try:
            import base64 as _b64
            import io as _io

            from PIL import Image

            # data:image/png;base64,xxx → raw bytes
            header, b64_part = image_data.split(",", 1)
            img_bytes = _b64.b64decode(b64_part)

            # Downscale large images to prevent OCR timeout
            img = Image.open(_io.BytesIO(img_bytes))
            w, h = img.size
            max_dim = max(w, h)
            if max_dim > _LOCAL_OCR_MAX_DIM:
                ratio = _LOCAL_OCR_MAX_DIM / max_dim
                new_size = (int(w * ratio), int(h * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                logging.debug("Local OCR: downscaled image %dx%d → %dx%d", w, h, new_size[0], new_size[1])
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Save as PNG (lossless) — JPEG artifacts kill OCR accuracy
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes_scaled = buf.getvalue()

            import threading as _threading

            result_holder: list = []
            exc_holder: list = []

            def _run_ocr():
                try:
                    result_holder.append(ocr(img_bytes_scaled))
                except Exception as e:
                    exc_holder.append(e)

            t = _threading.Thread(target=_run_ocr, daemon=True)
            t.start()
            t.join(timeout=_LOCAL_OCR_TIMEOUT)

            if t.is_alive():
                logging.warning("Local OCR timed out after %ds", _LOCAL_OCR_TIMEOUT)
                return None
            if exc_holder:
                logging.warning("Local OCR failed: %s", exc_holder[0])
                return None
            if not result_holder:
                return None

            result, _ = result_holder[0]
            if not result:
                return {"text": "", "has_text": False}

            # result is list of (box, text, confidence), sorted top-to-bottom
            lines: list[str] = []
            for _, text, _ in result:
                if text and text.strip():
                    lines.append(text.strip())

            text = "\n".join(lines)
            return {"text": text, "has_text": bool(text.strip())}
        except Exception:
            logging.warning("Local OCR failed", exc_info=True)
            return None

    @staticmethod
    def try_ocr_images(image_list: list) -> tuple[bool, dict] | None:
        """Try local OCR on a list of data-URL images.

        Returns (True, result_dict) when OCR ran, or None if OCR engine is unavailable.
        """
        if not image_list:
            return None
        ocr = _get_local_ocr()
        if not ocr:
            return None

        any_processed = False
        all_text: list[str] = []
        for src in image_list:
            if not VisionHandler._is_data_url(src):
                continue
            any_processed = True
            r = LocalOCRHandler.extract_text(src)
            if r and r.get("has_text"):
                all_text.append(r.get("text", ""))
        if not any_processed:
            return None  # No data URLs to process — caller should try other paths
        if all_text:
            return True, {"text": "\n---\n".join(all_text), "has_text": True, "language": ""}
        return True, {"text": "", "has_text": False, "language": ""}


class VisionHandler:

    @staticmethod
    def _image_to_base64(image_url):
        """Download an image from URL and convert to data URL format."""
        try:
            resp = requests.get(image_url, timeout=15)
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
            return _vision_fallback_single(image_url, task_type)

        img_src = VisionHandler._image_to_base64(image_url) or image_url
        ok, result = VisionHandler._call_vision(img_src, prompt, task_type)
        if not ok:
            return _vision_fallback_single(img_src, task_type)
        return True, result

    @staticmethod
    def analyze_base64(image_data, prompt, task_type="describe"):
        """直接分析 base64 格式的图片（data URL），跳过下载步骤。"""
        if not _vision_client and not _ensure_client():
            return _vision_fallback_single(image_data, task_type)

        if not VisionHandler._is_data_url(image_data):
            return False, "image_data 必须是 data:image/...;base64,... 格式"
        ok, result = VisionHandler._call_vision(image_data, prompt, task_type)
        if not ok:
            return _vision_fallback_single(image_data, task_type)
        return True, result

    @staticmethod
    def analyze_images(image_list, prompt, task_type="describe"):
        """批量分析多张图片 — 所有图片 + 一个 prompt 一起发送给视觉模型。"""
        if not image_list:
            return False, "image_list 不能为空"

        # ── Vision LLM unavailable → try local OCR fallback ─────────────────
        if not _vision_client and not _ensure_client():
            if task_type == "ocr":
                fallback = LocalOCRHandler.try_ocr_images(image_list)
                if fallback is not None:
                    return fallback
            # Non-OCR tasks without vision client — can't fallback
            return False, "Vision API 未配置，请设置 DEEPSEEK_API_KEY 或 VISION_API_KEY"

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
                timeout=LLM_TIMEOUT,
            )
            raw = response.choices[0].message.content
            return VisionHandler._parse_result(raw, task_type)
        except Exception as ex:
            err_msg = str(ex)
            if "image_url" in err_msg and ("unknown variant" in err_msg or "expected" in err_msg):
                logging.warning(
                    "当前配置的模型 %s 不支持图片分析。请设置 VISION_API_KEY/VISION_MODEL 为支持视觉的模型。",
                    _vision_model,
                )
                # Fallback to local OCR for vision-incapable models
                if task_type == "ocr":
                    fallback = LocalOCRHandler.try_ocr_images(image_list)
                    if fallback is not None:
                        logging.info("Using local OCR fallback after vision model rejection")
                        return fallback
                return (
                    False,
                    f"当前模型 {_vision_model} 不支持图片/视觉分析，请配置支持多模态的视觉模型（如 gpt-4o、qwen-vl 等）",
                )
            # Check for timeout
            if "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
                logging.warning("Vision API timed out after %ds", LLM_TIMEOUT)
                if task_type == "ocr":
                    fallback = LocalOCRHandler.try_ocr_images(image_list)
                    if fallback is not None:
                        logging.info("Using local OCR fallback after vision API timeout")
                        return fallback
            logging.warning("Vision API 批量分析失败: %s", ex)
            # Fallback to local OCR on any API failure for OCR tasks
            if task_type == "ocr":
                fallback = LocalOCRHandler.try_ocr_images(image_list)
                if fallback is not None:
                    logging.info("Using local OCR fallback after vision API failure")
                    return fallback
            return False, str(ex)[:500]

    @staticmethod
    def _call_vision(img_src, prompt, task_type):
        """Core vision API call with a single image."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_src}},
                ],
            }
        ]

        try:
            response = _vision_client.chat.completions.create(
                model=_vision_model,
                messages=messages,
                stream=False,
                timeout=LLM_TIMEOUT,
            )
            content = response.choices[0].message.content
            return VisionHandler._parse_result(content, task_type)
        except Exception as ex:
            err_msg = str(ex)
            # Detect API rejection of image_url (model doesn't support vision)
            if "image_url" in err_msg and ("unknown variant" in err_msg or "expected" in err_msg):
                logging.warning(
                    "当前配置的模型 %s 不支持图片分析。请设置 VISION_API_KEY/VISION_MODEL 为支持视觉的模型。",
                    _vision_model,
                )
                return (
                    False,
                    f"当前模型 {_vision_model} 不支持图片/视觉分析，请配置支持多模态的视觉模型（如 gpt-4o、qwen-vl 等）",
                )
            logging.warning("Vision API 调用失败: %s", ex)
            return False, err_msg[:500]

    @staticmethod
    def _parse_result(content, task_type):
        """Parse vision response based on task type."""
        if task_type == "describe":
            return VisionHandler._parse_describe(content)
        elif task_type == "classify":
            return VisionHandler._parse_classify(content)
        elif task_type == "detect":
            return VisionHandler._parse_detect(content)
        elif task_type == "ocr":
            return VisionHandler._parse_ocr(content)
        return True, {"raw": content}

    # ── Prompt builders ──────────────────────────────────────────────────

    @staticmethod
    def build_describe_prompt():
        return json.dumps(
            {
                "task": "describe",
                "instructions": "描述这张图片的内容、主要物体、场景类型和关键词。",
                "output_format": '{"scene_type":"","description":"","keywords":[]}',
            },
            ensure_ascii=False,
        )

    @staticmethod
    def build_classify_prompt(categories):
        cat_names = [c.get("name", "") for c in categories] if categories else []
        return json.dumps(
            {
                "task": "classify",
                "categories": cat_names,
                "instructions": "将图片分类到最匹配的类别。",
                "output_format": '{"category":"","confidence":0.0}',
            },
            ensure_ascii=False,
        )

    @staticmethod
    def build_detect_prompt():
        return json.dumps(
            {
                "task": "detect",
                "instructions": "检测图片中的物体，给出物体名称、位置描述和建议标注区域。",
                "output_format": '{"objects":[{"name":"","position":"","suggestion":""}]}',
            },
            ensure_ascii=False,
        )

    @staticmethod
    def build_ocr_prompt():
        return json.dumps(
            {
                "task": "ocr",
                "instructions": (
                    "提取图片中的所有文字，保持原文语言输出。"
                    "如有表格，用 Markdown 表格格式输出。"
                    "按从上到下、从左到右的顺序组织文本，保留段落结构。"
                    "如果图中没有文字，返回空字符串。"
                ),
                "output_format": '{"text":"<提取的文字>","has_text":true/false,"language":"<主要语言>"}',
            },
            ensure_ascii=False,
        )

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

    @staticmethod
    def _parse_ocr(content):
        try:
            data = json.loads(content)
            return True, data
        except (json.JSONDecodeError, TypeError):
            # Model returned plain text instead of JSON — wrap it
            return True, {"text": content, "has_text": bool(content.strip()), "language": ""}
