"""Tests for auto_correction_engine — Ronda 18 audit fixes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


# ── R18-1: _build_deductive_context must use injected tool_registry ──

def test_build_deductive_context_uses_injected_registry():
    """R18-1: _build_deductive_context called ToolRegistry(workspace_root=...)
    but ToolRegistry.__init__ requires (repository, adapters).  The wrong
    constructor always raised TypeError, silently swallowed by try/except,
    so the deductive reasoning engine never saw available tools.

    After the fix, _build_deductive_context accepts an optional
    tool_registry parameter and uses it directly when provided.
    """
    from iabv_v15.services.auto_correction_engine import _build_deductive_context

    fake_card = SimpleNamespace(tool_id='ollama_local', available=True)
    registry = MagicMock()
    registry.list_cards.return_value = [fake_card]

    context = _build_deductive_context(
        [{'category': 'test', 'title': 'test finding'}],
        tool_registry=registry,
    )

    registry.list_cards.assert_called_once()
    assert 'ollama_local' in context, (
        'Injected registry card should appear in deductive context'
    )
    assert 'available=True' in context


def test_build_deductive_context_without_registry_does_not_crash():
    """When tool_registry is None, the context should still be built
    without crashing (graceful fallback)."""
    from iabv_v15.services.auto_correction_engine import _build_deductive_context

    context = _build_deductive_context(
        [{'category': 'test', 'title': 'test finding'}],
    )

    assert 'PROBLEMAS DETECTADOS' in context
    assert 'ToolRegistry no inyectado' in context


def test_apply_deductive_corrections_forwards_registry():
    """apply_deductive_corrections should forward tool_registry to
    _build_deductive_context so the deductive engine sees tools."""
    from unittest.mock import patch
    from iabv_v15.services.auto_correction_engine import apply_deductive_corrections

    registry = MagicMock()
    registry.list_cards.return_value = []

    with patch(
        'iabv_v15.services.auto_correction_engine._query_ollama_for_deduction',
        return_value=None,
    ):
        result = apply_deductive_corrections(
            [{'category': 'test', 'title': 'demo'}],
            tool_registry=registry,
        )

    assert result['ollama_available'] is False
    assert result['corrections_count'] == 0


def test_deep_tool_probe_uses_injected_registry():
    """R18-1: _deep_tool_probe called ToolRegistry(workspace_root=...)
    which always crashed.  After the fix, it uses the injected registry."""
    from iabv_v15.services.auto_correction_engine import _deep_tool_probe

    fake_card = SimpleNamespace(
        title='Ollama',
        adapter_key='ollama',
        metadata={
            'launch_mode': 'api',
            'response_capture_mode': 'json',
            'background_capture_mode': '',
            'web_url': '',
            'command_name': 'ollama',
            'command_aliases': [],
            'windows_default_paths': [],
            'session_state_path': '',
            'session_rollouts_root': '',
        },
    )
    registry = MagicMock()
    registry.get_card.return_value = fake_card

    probe = _deep_tool_probe('ollama_local', tool_registry=registry)

    registry.get_card.assert_called()
    assert probe.get('card') is not None, (
        'card info should be populated from injected registry'
    )
    assert probe['card']['title'] == 'Ollama'


def test_deep_tool_probe_without_registry_still_works():
    """Without registry, _deep_tool_probe should still return a valid
    probe dict without crashing."""
    from iabv_v15.services.auto_correction_engine import _deep_tool_probe

    probe = _deep_tool_probe('ollama_local')

    assert probe['tool_id'] == 'ollama_local'
    assert probe['assistant_kind'] == 'ollama_local'
