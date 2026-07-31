# -*- coding: UTF-8 -*-
"""Test Agent API endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestAgentChatEndpoint:
    """POST /v1/agent/chat"""

    def test_empty_message(self, client):
        resp = client.post("/v1/agent/chat", data=json.dumps({"message": ""}), content_type="application/json")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400

    def test_message_too_long(self, client):
        resp = client.post("/v1/agent/chat", data=json.dumps({"message": "x" * 10000}), content_type="application/json")
        assert resp.status_code == 400

    def test_valid_request(self, client):
        with patch("app.api.v1.agent.AgentSession") as MockSession:
            mock_session = MagicMock()
            mock_session.chat_v3.return_value = iter(
                [
                    {"type": "text", "data": {"content": "Hello"}},
                    {"type": "done", "data": {"status": "completed"}},
                ]
            )
            MockSession.return_value = mock_session

            resp = client.post(
                "/v1/agent/chat",
                data=json.dumps(
                    {
                        "message": "Hello",
                        "user_id": "test_user",
                    }
                ),
                content_type="application/json",
            )
            assert resp.status_code == 200
            assert resp.content_type == "text/event-stream"


class TestAgentTTSEndpoint:
    """POST /v1/agent/tts"""

    def test_empty_text(self, client):
        resp = client.post("/v1/agent/tts", data=json.dumps({"text": ""}), content_type="application/json")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_text_too_long(self, client):
        resp = client.post("/v1/agent/tts", data=json.dumps({"text": "x" * 10000}), content_type="application/json")
        assert resp.status_code == 400

    def test_missing_text(self, client):
        resp = client.post("/v1/agent/tts", data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 400

    def test_tts_not_loaded(self, client):
        """TTS model not available returns 503."""
        with patch("app.util.agent.tts.AgentTTS.instance") as mock_tts:
            mock_tts.side_effect = RuntimeError("TTS 功能已禁用")
            resp = client.post("/v1/agent/tts", data=json.dumps({"text": "测试文本"}), content_type="application/json")
            assert resp.status_code == 503
