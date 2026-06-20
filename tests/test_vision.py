# -*- coding: UTF-8 -*-
"""Test VisionHandler — image analysis bridge."""

import pytest
from unittest.mock import patch, MagicMock

from app.util.vision import VisionHandler


class TestImageToBase64:
    """URL to base64 conversion."""

    @patch('app.util.vision.requests.get')
    def test_successful_download(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        mock_resp.headers = {'Content-Type': 'image/png'}
        mock_get.return_value = mock_resp

        result = VisionHandler._image_to_base64('http://example.com/img.png')
        assert result is not None
        assert result.startswith('data:image/png;base64,')

    @patch('app.util.vision.requests.get')
    def test_download_failure(self, mock_get):
        mock_get.side_effect = Exception('Connection refused')
        result = VisionHandler._image_to_base64('http://down.example.com/img.jpg')
        assert result is None


class TestDataURLDetection:
    """Data URL format detection."""

    def test_valid_data_url(self):
        assert VisionHandler._is_data_url('data:image/png;base64,abc123') is True

    def test_url_not_data_url(self):
        assert VisionHandler._is_data_url('http://example.com/img.png') is False

    def test_none_input(self):
        assert VisionHandler._is_data_url(None) is False


class TestAnalyzeBase64:
    """Direct base64 analysis."""

    def test_not_data_url_rejected(self):
        with patch('app.util.vision._ensure_client', return_value=True):
            ok, msg = VisionHandler.analyze_base64(
                'http://example.com/img.png', '描述图片'
            )
            assert not ok
            assert 'data:image' in msg


class TestAnalyzeImages:
    """Batch image analysis."""

    def test_empty_list_rejected(self):
        with patch('app.util.vision._ensure_client', return_value=True):
            ok, msg = VisionHandler.analyze_images([], '描述')
            assert not ok
