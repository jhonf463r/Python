"""Tests for canonical work queue: critical stalls and non-resolved consultations.

Validates:
- Critical stalls (>5000ms) appear in OSES findings.
- Non-resolved external consultations appear in OSES findings.
- These are surfaced for another AI to reconstruct the history.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from iabv_v15.services.evolution.operational_self_examination_service import (
    OperationalSelfExaminationService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_audit_events(workspace: Path, events: list[dict]) -> None:
    audit_dir = workspace / 'data' / 'logs'
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / 'runtime_audit.jsonl'
    with audit_path.open('w', encoding='utf-8') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')


def _make_oses(workspace: Path) -> OperationalSelfExaminationService:
    oses = OperationalSelfExaminationService.__new__(OperationalSelfExaminationService)
    oses.workspace_root = str(workspace)
    oses._freeze_incident_reporter = None
    oses._ui_heartbeat_watchdog = None
    return oses


# ---------------------------------------------------------------------------
# Critical stalls
# ---------------------------------------------------------------------------

class TestCriticalStallsInQueue:
    def test_stall_episodes_generate_findings(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-stall1',
                    'message_preview': 'que herramientas tengo',
                    'outcome': 'resolved',
                    'provider': 'local',
                    'total_duration_ms': 15000,
                    'stalls_during': [{'duration_ms': 8000, 'cause': 'startup_freeze'}],
                    'had_early_technical_response': False,
                    'window_went_inactive': False,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        stall_findings = [f for f in findings if f.category == 'interaction_episode_stalls']
        assert len(stall_findings) == 1
        assert stall_findings[0].metadata['stall_episode_count'] == 1


# ---------------------------------------------------------------------------
# Non-resolved external consultations
# ---------------------------------------------------------------------------

class TestNonResolvedConsultationsInQueue:
    def test_prepared_outcome_generates_pending_finding(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-ext1',
                    'message_preview': 'haz una consulta a chatgpt',
                    'outcome': 'prepared',
                    'provider': 'ChatGPT web asistido',
                    'total_duration_ms': 650,
                    'is_final': False,
                    'had_early_technical_response': False,
                    'window_went_inactive': False,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        pending_findings = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending_findings) == 1
        assert pending_findings[0].metadata['pending_count'] == 1

    def test_reused_context_generates_pending_finding(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-reuse',
                    'message_preview': 'ya tenia consulta equivalente',
                    'outcome': 'reused_context',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 300,
                    'is_final': False,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        pending_findings = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending_findings) == 1

    def test_awaiting_response_generates_pending_finding(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-await',
                    'message_preview': 'consulta esperando respuesta',
                    'outcome': 'awaiting_external_response',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 0,
                    'is_final': False,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        pending_findings = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending_findings) == 1

    def test_resolved_does_not_generate_pending_finding(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-ok',
                    'message_preview': 'consulta exitosa',
                    'outcome': 'resolved',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 3500,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        pending_findings = [f for f in findings if f.category == 'interaction_episode_pending']
        assert len(pending_findings) == 0

    def test_mixed_findings_report_correct_counts(self, tmp_path):
        workspace = tmp_path / 'workspace'
        _write_audit_events(workspace, [
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-p1',
                    'outcome': 'prepared',
                    'message_preview': 'preparada',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 500,
                    'is_final': False,
                },
            },
            {
                'kind': 'interaction_resolved',
                'data': {
                    'interaction_id': 'chat-r1',
                    'outcome': 'resolved',
                    'message_preview': 'resuelta',
                    'provider': 'local',
                    'total_duration_ms': 2000,
                    'stalls_during': [{'duration_ms': 3000}],
                },
            },
            {
                'kind': 'interaction_outcome',
                'data': {
                    'interaction_id': 'chat-b1',
                    'outcome': 'blocked',
                    'message_preview': 'bloqueada',
                    'provider': 'ChatGPT',
                    'total_duration_ms': 100,
                    'is_final': False,
                },
            },
        ])
        oses = _make_oses(workspace)
        findings = oses._interaction_episode_findings()
        pending = [f for f in findings if f.category == 'interaction_episode_pending']
        stalls = [f for f in findings if f.category == 'interaction_episode_stalls']
        assert len(pending) == 1
        assert pending[0].metadata['pending_count'] == 2  # prepared + blocked
        assert len(stalls) == 1
        assert stalls[0].metadata['stall_episode_count'] == 1
