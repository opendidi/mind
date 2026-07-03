# -*- coding: UTF-8 -*-
"""Test VisionHandler — image analysis bridge."""

from unittest.mock import MagicMock, patch

import pytest

from app.util.vision import VisionHandler


class TestImageToBase64:
    """URL to base64 conversion."""

    @patch("app.util.vision.requests.get")
    def test_successful_download(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_get.return_value = mock_resp

        result = VisionHandler._image_to_base64("http://example.com/img.png")
        assert result is not None
        assert result.startswith("data:image/png;base64,")

    @patch("app.util.vision.requests.get")
    def test_download_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        result = VisionHandler._image_to_base64("http://down.example.com/img.jpg")
        assert result is None


class TestDataURLDetection:
    """Data URL format detection."""

    def test_valid_data_url(self):
        assert VisionHandler._is_data_url("data:image/png;base64,abc123") is True

    def test_url_not_data_url(self):
        assert VisionHandler._is_data_url("http://example.com/img.png") is False

    def test_none_input(self):
        assert VisionHandler._is_data_url(None) is False


class TestAnalyzeBase64:
    """Direct base64 analysis."""

    def test_not_data_url_rejected(self):
        with patch("app.util.vision._ensure_client", return_value=True):
            ok, msg = VisionHandler.analyze_base64("http://example.com/img.png", "描述图片")
            assert not ok
            assert "data:image" in msg


class TestOCR:
    """OCR text extraction."""

    def test_build_ocr_prompt_returns_valid_json(self):
        import json

        prompt = VisionHandler.build_ocr_prompt()
        data = json.loads(prompt)
        assert data["task"] == "ocr"
        assert "instructions" in data
        assert "text" in data["output_format"]

    def test_parse_ocr_valid_json(self):
        ok, result = VisionHandler._parse_ocr('{"text":"Hello World","has_text":true,"language":"en"}')
        assert ok
        assert result["text"] == "Hello World"
        assert result["has_text"] is True
        assert result["language"] == "en"

    def test_parse_ocr_plain_text_fallback(self):
        ok, result = VisionHandler._parse_ocr("纯文本输出，没有JSON格式")
        assert ok
        assert result["text"] == "纯文本输出，没有JSON格式"
        assert result["has_text"] is True
        assert result["language"] == ""

    def test_parse_ocr_empty_text(self):
        ok, result = VisionHandler._parse_ocr("")
        assert ok
        assert result["has_text"] is False

    def test_parse_result_routes_ocr(self):
        ok, result = VisionHandler._parse_result('{"text":"测试","has_text":true,"language":"zh"}', "ocr")
        assert ok
        assert result["text"] == "测试"

    @patch("app.util.vision._ensure_client", return_value=True)
    @patch("app.util.vision._vision_client")
    def test_analyze_image_ocr_builds_correct_prompt(self, mock_client, _ensure):
        mock_choice = MagicMock()
        mock_choice.message.content = '{"text":"扫码结果","has_text":true,"language":"zh"}'
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        ok, result = VisionHandler.analyze_image(
            image_url="http://example.com/qr.png",
            prompt=VisionHandler.build_ocr_prompt(),
            task_type="ocr",
        )
        assert ok
        assert result["text"] == "扫码结果"


class TestAnalyzeImages:
    """Batch image analysis."""

    def test_empty_list_rejected(self):
        with patch("app.util.vision._ensure_client", return_value=True):
            ok, msg = VisionHandler.analyze_images([], "描述")
            assert not ok
