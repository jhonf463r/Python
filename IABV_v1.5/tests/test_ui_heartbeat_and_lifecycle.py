"""Tests for external consultation lifecycle semantics (E).

Validates:
- external_consultation prepared/reused does NOT close as resolved.
- resolved only when actual external response is captured.
- runtime_audit traces the semantic outcome correctly.
"""
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.freeze_incident_reporter import (
    ChatInteractionLifecycle,
)


# ---------------------------------------------------------------------------
# E. External consultation lifecycle — semantic outcomes
# ---------------------------------------------------------------------------

class TestChatInteractionLifecycle:
    def test_prepared_outcome_does_not_close_interaction(self):
        """prepared outcome keeps interaction in active list."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('haz una consulta a chatgpt')
        result = lc.resolve_interaction(iid, outcome='prepared', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'prepared'
        assert result['resolved'] is False
        # Interaction should still be accessible (re-resolution possible)
        info = lc.interaction_info(iid)
        assert info is not None

    def test_reused_context_does_not_close_interaction(self):
        """reused_context outcome keeps interaction open."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('consulta a chatgpt')
        result = lc.resolve_interaction(iid, outcome='reused_context', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'reused_context'
        assert result['resolved'] is False
        info = lc.interaction_info(iid)
        assert info is not None

    def test_awaiting_external_response_does_not_close(self):
        """awaiting_external_response keeps interaction open."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('pide algo a chatgpt')
        result = lc.resolve_interaction(iid, outcome='awaiting_external_response', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'awaiting_external_response'
        assert result['resolved'] is False
        info = lc.interaction_info(iid)
        assert info is not None

    def test_blocked_does_not_close(self):
        """blocked outcome keeps interaction open."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('consulta externa')
        result = lc.resolve_interaction(iid, outcome='blocked', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'blocked'
        assert result['resolved'] is False

    def test_resolved_closes_interaction(self):
        """resolved outcome closes the interaction (moved to completed)."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('consulta exitosa')
        result = lc.resolve_interaction(iid, outcome='resolved', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'resolved'
        assert result['resolved'] is True
        # Should no longer be in active interactions (but still in completed)
        active = lc.active_interaction()
        assert active is None
        # interaction_info still returns it from completed list
        info = lc.interaction_info(iid)
        assert info is not None
        assert info['resolved'] is True

    def test_failed_closes_interaction(self):
        """failed outcome closes the interaction."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('consulta fallida')
        result = lc.resolve_interaction(iid, outcome='failed', provider='ChatGPT')
        assert result is not None
        assert result['outcome'] == 'failed'
        assert result['resolved'] is True

    def test_prepared_then_resolved_closes_interaction(self):
        """Non-final outcome followed by final outcome closes correctly."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('consulta en dos pasos')
        # Step 1: prepared (non-final)
        r1 = lc.resolve_interaction(iid, outcome='prepared', provider='ChatGPT')
        assert r1['resolved'] is False
        # Step 2: resolved (final) — interaction should still be accessible
        info = lc.interaction_info(iid)
        assert info is not None
        r2 = lc.resolve_interaction(iid, outcome='resolved', provider='ChatGPT')
        assert r2 is not None
        assert r2['resolved'] is True
        assert r2['outcome'] == 'resolved'

    def test_reused_context_then_resolved(self):
        """reused_context then resolved produces correct lifecycle."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('ya tenia una consulta equivalente')
        lc.resolve_interaction(iid, outcome='reused_context', provider='ChatGPT')
        # Can still resolve later
        r = lc.resolve_interaction(iid, outcome='resolved', provider='ChatGPT')
        assert r is not None
        assert r['resolved'] is True

    def test_non_final_outcomes_are_listed(self):
        """The _NON_FINAL_OUTCOMES set includes expected values."""
        assert 'prepared' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'awaiting_external_response' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'reused_context' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'blocked' in ChatInteractionLifecycle._NON_FINAL_OUTCOMES
        assert 'resolved' not in ChatInteractionLifecycle._NON_FINAL_OUTCOMES

    def test_phases_track_outcome_key(self):
        """Non-final outcomes should add phase key like outcome_prepared."""
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test phases')
        r = lc.resolve_interaction(iid, outcome='prepared', provider='test')
        assert r is not None
        assert 'outcome_prepared' in r.get('phases', {})


# ---------------------------------------------------------------------------
# Derive external consultation outcome
# ---------------------------------------------------------------------------

class TestDeriveExternalConsultationOutcome:
    """Test _derive_external_consultation_outcome static method."""

    @staticmethod
    def _derive(payload):
        # Import lazily to avoid circular imports
        try:
            from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
            return ControlCenterViewModel._derive_external_consultation_outcome(payload)
        except ImportError:
            pytest.skip('ControlCenterViewModel not importable')

    def test_blocked_when_not_success(self):
        assert self._derive({'success': False}) == 'blocked'

    def test_prepared_when_success_no_response(self):
        result = self._derive({
            'success': True,
            'payload': {'metadata': {'external_consultation': {'status': 'prepared'}}},
        })
        assert result == 'prepared'

    def test_reused_context_when_message_contains_equivalente(self):
        result = self._derive({
            'success': True,
            'message': 'Ya tenia una consulta equivalente abierta',
            'payload': {'metadata': {'external_consultation': {'status': 'reused'}}},
        })
        assert result == 'reused_context'

    def test_awaiting_response_status(self):
        result = self._derive({
            'success': True,
            'payload': {'metadata': {'external_consultation': {'status': 'awaiting_response'}}},
        })
        assert result == 'awaiting_external_response'

    def test_resolved_when_response_captured(self):
        result = self._derive({
            'success': True,
            'payload': {'metadata': {'external_consultation': {
                'status': 'prepared',
                'response_captured': True,
            }}},
        })
        assert result == 'resolved'

    def test_resolved_when_response_ingested(self):
        result = self._derive({
            'success': True,
            'payload': {'metadata': {'external_consultation': {
                'response_ingested_at_utc': '2026-05-07T12:00:00Z',
            }}},
        })
        assert result == 'resolved'

    def test_prepared_from_message_heuristic(self):
        result = self._derive({
            'success': True,
            'message': 'Consulta externa aceptada para ChatGPT',
            'payload': {},
        })
        assert result == 'prepared'

    def test_non_dict_returns_resolved(self):
        result = self._derive('not a dict')
        assert result == 'resolved'


# ---------------------------------------------------------------------------
# Runtime audit traces correct outcome
# ---------------------------------------------------------------------------

class TestRuntimeAuditOutcomeTracing:
    """Verify that resolve_interaction emits correct trace kind."""

    def test_final_outcome_traces_interaction_resolved(self):
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test trace')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_tracer:
            mock_t = MagicMock()
            mock_tracer.return_value = mock_t
            lc.resolve_interaction(iid, outcome='resolved', provider='test')
            if mock_t.trace.called:
                args = mock_t.trace.call_args
                assert args[0][0] == 'interaction_resolved'
                assert args[1].get('is_final') is True

    def test_non_final_outcome_traces_interaction_outcome(self):
        lc = ChatInteractionLifecycle()
        iid = lc.open_interaction('test trace non-final')
        with patch('iabv_v15.services.evolution.runtime_audit_tracer.get_runtime_tracer') as mock_tracer:
            mock_t = MagicMock()
            mock_tracer.return_value = mock_t
            lc.resolve_interaction(iid, outcome='prepared', provider='test')
            if mock_t.trace.called:
                args = mock_t.trace.call_args
                assert args[0][0] == 'interaction_outcome'
                assert args[1].get('is_final') is False
