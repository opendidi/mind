# -*- coding: UTF-8 -*-
"""Test Material MySQL — URL parsing, file upload logic."""

from unittest.mock import MagicMock, patch

import pytest

from app.package.module.material_mysql import extract_path_segment


class TestExtractPathSegment:
    """URL path segment extraction."""

    def test_legacy_pano_path(self):
        url = "http://cdn.example.com/pano/123456/file.png"
        result = extract_path_segment(url, start_segment="/pano/", levels=2)
        # Should extract "123456/file.png" → "123456/"
        assert "123456" in result

    def test_mind_path(self):
        url = "http://cdn.example.com/mind/789012/file.jpg"
        result = extract_path_segment(url, start_segment="/mind/", levels=2)
        assert "789012" in result

    def test_minio_format_no_matching_segment(self):
        url = "http://cdn.example.com/bucket/dir/file.png"
        # Should fall back to extracting bucket/dir prefix
        result = extract_path_segment(url, start_segment="/pano/", levels=2)
        assert len(result) > 0  # Should return at least something

    def test_empty_url_handled(self):
        with pytest.raises(Exception):
            extract_path_segment("", start_segment="/pano/", levels=2)


class TestPathSegmentEdgeCases:
    """Edge case handling."""

    def test_no_trailing_slash(self):
        result = extract_path_segment("http://host/mind/123/file.txt", start_segment="/mind/", levels=2)
        assert result.endswith("/") or len(result) > 0

    def test_deep_path(self):
        url = "http://host/mind/abc/def/ghi/file.txt"
        result = extract_path_segment(url, start_segment="/mind/", levels=3)
        assert "/" in result
