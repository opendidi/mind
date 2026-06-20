# -*- coding: UTF-8 -*-
"""Test MinIO controller — object operations, path parsing."""

import pytest
from unittest.mock import patch, MagicMock


@patch('app.plugin.minio.app.controller.minio_client')
class TestParseSourcePrefix:
    """URL to MinIO prefix parsing."""

    def test_normal_url(self, mock_client):
        from app.plugin.minio.app.controller import MinioUtil
        url = 'http://cdn.example.com/mind/123456/file.png'
        result = MinioUtil.parse_source_prefix(url)
        assert result == '123456/'

    def test_subdir_url(self, mock_client):
        from app.plugin.minio.app.controller import MinioUtil
        url = 'http://cdn.example.com/mind/123456/tiles/0.png'
        result = MinioUtil.parse_source_prefix(url)
        assert result == '123456/tiles/'

    def test_empty_url(self, mock_client):
        from app.plugin.minio.app.controller import MinioUtil
        result = MinioUtil.parse_source_prefix('')
        assert result is None

    def test_none_url(self, mock_client):
        from app.plugin.minio.app.controller import MinioUtil
        result = MinioUtil.parse_source_prefix(None)
        assert result is None


@patch('app.plugin.minio.app.controller.minio_client')
class TestCopyDirectoryPrefix:
    """Directory copy functionality."""

    def test_empty_source(self, mock_client):
        from app.plugin.minio.app.controller import MinioUtil
        mock_client.list_objects.return_value = []
        result = MinioUtil.copy_directory_prefix('source/', 'target/')
        assert result is False
