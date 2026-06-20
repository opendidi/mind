# -*- coding: UTF-8 -*-
"""Pytest fixtures — shared test infrastructure for mind project."""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Ensure app/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── App-level fixtures ────────────────────────────────────────────────────

@pytest.fixture
def app():
    """Create Flask app for API testing."""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ── Mock fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """Mock LLM client that returns a controlled response."""
    mock = MagicMock()
    mock.chat.return_value = {
        'choices': [{'message': {'content': '测试回复'}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
    }
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_db():
    """Mock database connection with cursor."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_conn


# ── Sample data fixtures ──────────────────────────────────────────────────

@pytest.fixture
def sample_canvas_context():
    """A minimal canvas context dict."""
    return {
        'nodes': [{'id': '1', 'type': 'rectangle', 'x': 100, 'y': 100}],
        'edges': [],
    }


@pytest.fixture
def sample_images():
    """Fake base64 image data URLs for testing vision bridge."""
    return [
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    ]


@pytest.fixture
def sample_user_message():
    """Standard user message for testing."""
    return '帮我在画布上画一个矩形'


@pytest.fixture
def sample_tool_args():
    """Sample tool call arguments."""
    return {
        'canvas_draw_pen': {
            'type': 'rectangle',
            'x': 100, 'y': 100,
            'width': 200, 'height': 100,
            'text': 'Hello',
        },
        'file_search': {
            'keyword': 'test.png',
        },
    }


# ── Environment fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env():
    """Ensure tests run with predictable environment."""
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret',
        'DB_HOST': 'localhost',
        'DB_USER': 'test',
        'DB_PASSWORD': 'test',
        'DB_NAME': 'test_db',
        'REDIS_HOST': 'localhost',
        'FLASK_DEBUG': 'false',
    }, clear=False):
        yield
