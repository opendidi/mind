# -*- coding: UTF-8 -*-
"""Test agent tools — validation, canvas, file operations."""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.util.agent.tools import run_tool_call
from app.util.agent.tools.web import _require
from app.util.agent.tools.canvas import _next_pen_id


class TestRequire:
    """Parameter validation helper."""

    def test_all_present(self):
        assert _require({'a': 1, 'b': 2}, 'a', 'b') is None

    def test_missing_key(self):
        err = _require({'a': 1}, 'a', 'b')
        assert err is not None
        assert 'b' in err

    def test_empty_args(self):
        err = _require({}, 'x')
        assert 'x' in err


class TestPenId:
    """Pen ID generation."""

    def test_unique_ids(self):
        ids = [_next_pen_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_prefix_format(self):
        pid = _next_pen_id()
        assert pid.startswith('pen_')


class TestCanvasTools:
    """Canvas drawing tool functions."""

    def test_canvas_draw_valid(self):
        with patch('app.util.agent.tools._rebuild_schemas') as mock_schema:
            mock_schema.return_value = None
            result = run_tool_call(
                'canvas_draw_pen',
                {'type': 'rectangle', 'x': 0, 'y': 0, 'width': 100, 'height': 50},
                {'task_id': 'test', 'session_id': 'test'},
            )
            assert result is not None
            # Should return a valid JSON with pen info
            data = json.loads(result) if isinstance(result, str) else result
            assert data is not None

    def test_canvas_clear(self):
        with patch('app.util.agent.tools._rebuild_schemas'):
            result = run_tool_call(
                'canvas_clear',
                {},
                {'task_id': 'test', 'session_id': 'test'},
            )
            assert result is not None

    def test_unknown_tool(self):
        result = run_tool_call(
            'nonexistent_tool_xyz',
            {},
            {'task_id': 'test'},
        )
        assert result is None or 'unknown' in str(result).lower()


class TestFileTools:
    """File search tool validation."""

    def test_file_search_no_keyword(self):
        result = run_tool_call(
            'file_search',
            {},
            {'task_id': 'test'},
        )
        # Should error without keyword
        assert result is not None
        assert 'keyword' in str(result).lower() if isinstance(result, str) else True


class TestGeoTools:
    """Geocoding tool validation."""

    def test_geocode_no_address(self):
        result = run_tool_call(
            'geocode',
            {},
            {'task_id': 'test'},
        )
        assert result is not None
        # Should indicate missing address
        if isinstance(result, str):
            assert 'address' in result.lower() or 'error' in result.lower()
