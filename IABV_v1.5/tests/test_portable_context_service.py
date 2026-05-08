"""Tests for PortableContext reconstruction of non-resolved episodes.

Validates:
- latest.md shows external_consultation episodes with outcome=prepared/
  reused_context/awaiting_external_response as NOT resolved.
- interaction_resolved and interaction_outcome audit events are both read.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.portable_context_service import (
    PortableContextService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_audit_events(workspace: Path, events: list[dict]) -> None:
    """Write audit events to runtime_audit.jsonl."""
    audit_dir = workspace / 'data' / 'logs'
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / 'runtime_audit.jsonl'
    with audit_path.open('w', encoding='utf-8') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')


def _make_pcs(workspace: Path) -> PortableContextService:
    """Create a minimal PortableContextService with the given workspace."""
    pcs = PortableContextService.__new__(PortableContextService)
    pcs.workspace_root = str(workspace)
    pcs.freeze_incident_reporter = None
    pcs.ui_heartbeat_watchdog = None
    pcs.chat_interaction_lifecycle = None
    return pcs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPortableContextNonResolved:
    def test_interaction_outcome_event_is_read(self, tmp_path):
        """interaction_outcome events (non-final) should be read from audit."""
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-abc123',
                    'message_preview': 'haz una consulta a chatgpt',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 650,
                    'is_final': False,
                    'had_early_technical_response': False,
                    'window_went_inactive': False,
                },
            },
        ])
        pcs = _make_pcs(workspace)
        episodes = pcs._interaction_episodes_from_audit(limit=5)
        assert len(episodes) == 1
        ep = episodes[0]
        assert ep['outcome'] == 'prepared'
        assert ep['resolved'] is False

    def test_interaction_resolved_event_is_read_as_final(self, tmp_path):
        """interaction_resolved events should be read as resolved=True."""
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-def456',
                    'message_preview': 'consulta exitosa',
                    'outcome': 'resolved',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 3500,
                    'had_early_technical_response': True,
                    'window_went_inactive': False,
                },
            },
        ])
        pcs = _make_pcs(workspace)
        episodes = pcs._interaction_episodes_from_audit(limit=5)
        assert len(episodes) == 1
        ep = episodes[0]
        assert ep['outcome'] == 'resolved'
        assert ep['resolved'] is True

    def test_mixed_events_preserve_semantics(self, tmp_path):
        """Mix of resolved and non-resolved episodes preserves is_final."""
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-111',
                    'message_preview': 'consulta preparada',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-222',
                    'message_preview': 'reutilizada',
                    'outcome': 'reused_context',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 300,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-333',
                    'message_preview': 'resuelta',
                    'outcome': 'resolved',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 4000,
                },
            },
        ])
        pcs = _make_pcs(workspace)
        episodes = pcs._interaction_episodes_from_audit(limit=5)
        assert len(episodes) == 3
        outcomes = {ep['interaction_id']: ep for ep in episodes}
        assert outcomes['chat-111']['resolved'] is False
        assert outcomes['chat-222']['resolved'] is False
        assert outcomes['chat-333']['resolved'] is True

    def test_lifecycle_section_shows_resolved_field(self, tmp_path):
        """_interaction_lifecycle_section should include resolved field."""
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-pending',
                    'message_preview': 'consulta pendiente',
                    'outcome': 'awaiting_external_response',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 0,
                    'is_final': False,
                },
            },
        ])
        pcs = _make_pcs(workspace)
        # Patch lifecycle summary to use audit-based data
        pcs.chat_interaction_lifecycle = None
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        section = pcs._interaction_lifecycle_section(now=now)
        items = section.items
        assert len(items) >= 1
        item = items[0]
        assert item['outcome'] == 'awaiting_external_response'
        assert item['resolved'] is False

    def test_reused_context_episode_not_shown_as_resolved(self, tmp_path):
        """reused_context episode should NOT appear as resolved in section."""
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-reused',
                    'message_preview': 'Ya tenia consulta equivalente',
                    'outcome': 'reused_context',
                    'provider': 'ChatGPT web asistido',
                    'total_duration_ms': 650,
                    'is_final': False,
                },
            },
        ])
        pcs = _make_pcs(workspace)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        section = pcs._interaction_lifecycle_section(now=now)
        items = section.items
        assert len(items) >= 1
        reused = [i for i in items if i['outcome'] == 'reused_context']
        assert len(reused) == 1
        assert reused[0]['resolved'] is False

    def test_no_events_produces_empty_section(self, tmp_path):
        """No audit events should produce empty section."""
        workspace = tmp_path / 'workspace'
        (workspace / 'data' / 'logs').mkdir(parents=True, exist_ok=True)
        (workspace / 'data' / 'logs' / 'runtime_audit.jsonl').write_text('', encoding='utf-8')
        pcs = _make_pcs(workspace)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        section = pcs._interaction_lifecycle_section(now=now)
        assert len(section.items) == 0
