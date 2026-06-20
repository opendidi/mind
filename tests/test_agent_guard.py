# -*- coding: UTF-8 -*-
"""Test AgentGuard — InputGuard, ToolGuard, OutputGuard."""

import pytest
from unittest.mock import patch

from app.util.agent.guard import (
    InputGuard,
    ToolGuard,
    OutputGuard,
    MAX_INPUT_LENGTH,
)


class TestInputGuard:
    """Input sanitation and validation."""

    def test_empty_input(self):
        assert InputGuard.check('') == {'ok': False, 'reason': '输入为空'}
        assert InputGuard.check('   ') == {'ok': False, 'reason': '输入为空'}

    def test_normal_input(self):
        result = InputGuard.check('帮我在画布上画个矩形')
        assert result == {'ok': True}

    def test_too_long_input(self):
        long_text = 'x' * (MAX_INPUT_LENGTH + 1)
        result = InputGuard.check(long_text)
        assert not result['ok']
        assert '过长' in result['reason']

    def test_xss_injection(self):
        result = InputGuard.check('<script>alert("xss")</script>')
        assert not result['ok']
        assert '可疑' in result['reason']

    def test_sql_injection(self):
        result = InputGuard.check("SELECT * FROM users WHERE 1=1")
        assert not result['ok']
        assert '可疑' in result['reason']

    def test_drop_table(self):
        result = InputGuard.check('DROP TABLE users')
        assert not result['ok']
        assert '可疑' in result['reason']

    def test_sanitize_html(self):
        cleaned = InputGuard.sanitize('<p>Hello <b>World</b></p>')
        assert cleaned == 'Hello World'

    def test_sanitize_null_bytes(self):
        cleaned = InputGuard.sanitize('test\x00data')
        assert cleaned == 'testdata'


class TestToolGuard:
    """Tool call validation."""

    def test_normal_tool(self):
        result = ToolGuard.check_tool_call('canvas_draw_pen', {'type': 'rect'}, 'sess1')
        assert result == {'ok': True, 'confirm_required': False}

    def test_destructive_tool_requires_confirm(self):
        result = ToolGuard.check_tool_call('canvas_clear', {}, 'sess1')
        assert result['ok'] is True
        assert result['confirm_required'] is True

    def test_path_traversal_blocked(self):
        result = ToolGuard.check_tool_call('file_search', {'keyword': '../../../etc/passwd'}, 'sess1')
        assert not result['ok']
        assert '非法路径' in result['reason']

    def test_absolute_path_blocked(self):
        result = ToolGuard.check_tool_call('read_text', {'path': '/etc/shadow'}, 'sess1')
        assert not result['ok']
        assert '非法路径' in result['reason']

    @patch.object(ToolGuard, 'MAX_CALLS_PER_TOOL', 2)
    def test_rate_limit(self):
        sid = 'sess_ratelimit'
        ToolGuard.reset_session(sid)
        # First 2 calls OK
        assert ToolGuard.check_tool_call('canvas_draw_pen', {}, sid)['ok']
        assert ToolGuard.check_tool_call('canvas_draw_pen', {}, sid)['ok']
        # 3rd call throttled
        result = ToolGuard.check_tool_call('canvas_draw_pen', {}, sid)
        assert not result['ok']
        assert '次数过多' in result['reason']

    def test_reset_session(self):
        sid = 'sess_reset'
        ToolGuard.check_tool_call('canvas_draw_pen', {}, sid)
        ToolGuard.reset_session(sid)
        # After reset, count should be back to 0
        result = ToolGuard.check_tool_call('canvas_draw_pen', {}, sid)
        assert result['ok'] is True


class TestOutputGuard:
    """Output sanitation and validation."""

    def test_pii_redact_phone(self):
        text = '请联系我 13812345678'
        result = OutputGuard.redact_pii(text)
        assert '13812345678' not in result
        assert '手机号***' in result

    def test_pii_redact_email(self):
        result = OutputGuard.redact_pii('email: test@example.com')
        assert 'test@example.com' not in result

    def test_pii_redact_id_card(self):
        result = OutputGuard.redact_pii('身份证: 110101199001011234')
        assert '199001011234' not in result  # digits should be replaced

    def test_validate_map_code_block_valid(self):
        assert OutputGuard.validate_code_block(
            '```map\n{"center": [116, 39]}\n```', 'map'
        ) is True

    def test_validate_map_code_block_missing_center(self):
        assert OutputGuard.validate_code_block(
            '```map\n{"zoom": 10}\n```', 'map'
        ) is False

    def test_validate_route_code_block_valid(self):
        assert OutputGuard.validate_code_block(
            '```route\n{"from": "北京", "to": "上海"}\n```', 'route'
        ) is True

    def test_validate_route_code_block_invalid(self):
        assert OutputGuard.validate_code_block(
            '```route\n{"distance": 100}\n```', 'route'
        ) is False

    def test_process_pipeline(self):
        result = OutputGuard.process('Hello, my email is test@example.com')
        assert result['ok'] is True
        assert 'test@example.com' not in result['text']
