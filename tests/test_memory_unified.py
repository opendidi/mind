"""Test unified memory — session persistence + semantic recall.

Imports MemoryManager directly via importlib to bypass the package __init__.py
chain (which has a pre-existing circular import issue unrelated to this module).
"""

import importlib.util
import os
import sys


def _load_memory_manager():
    """Load MemoryManager directly, bypassing package __init__.py."""
    path = os.path.join(os.path.dirname(__file__), '..',
                        'app', 'util', 'agent', 'memory.py')
    spec = importlib.util.spec_from_file_location(
        'memory_module', os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    # Clear any cached version
    for k in list(sys.modules.keys()):
        if k.endswith('agent.memory') or k == 'memory_module':
            del sys.modules[k]
    sys.modules['memory_module'] = mod
    spec.loader.exec_module(mod)
    return mod.MemoryManager


class TestMemoryUnified:
    """Test suite for unified MemoryManager (session + semantic recall)."""

    def setup_method(self):
        self.MemoryManager = _load_memory_manager()

    def test_memory_manager_has_restore_session(self):
        """MemoryManager should expose restore_session."""
        mgr = self.MemoryManager()
        assert hasattr(mgr, 'restore_session')

    def test_memory_manager_has_persist_session(self):
        """MemoryManager should expose persist_session."""
        mgr = self.MemoryManager()
        assert hasattr(mgr, 'persist_session')

    def test_restore_session_returns_dict(self):
        """restore_session should return a dict."""
        mgr = self.MemoryManager()
        result = mgr.restore_session('test_user')
        assert isinstance(result, dict)

    def test_restore_session_has_expected_keys(self):
        """restore_session result should have messages, summary, memory_prompt."""
        mgr = self.MemoryManager()
        result = mgr.restore_session('test_user')
        assert 'messages' in result
        assert 'summary' in result
        assert 'memory_prompt' in result

    def test_restore_session_empty_for_new_user(self):
        """restore_session should return empty state for unknown user."""
        mgr = self.MemoryManager()
        result = mgr.restore_session('nonexistent_user_12345')
        assert result['messages'] == []
        assert result['summary'] == ''
        assert result['memory_prompt'] == ''

    def test_memory_manager_has_load_raw(self):
        """MemoryManager should expose _load_raw."""
        mgr = self.MemoryManager()
        assert hasattr(mgr, '_load_raw')
