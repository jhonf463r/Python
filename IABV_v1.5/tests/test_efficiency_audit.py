"""Tests para efficiency_audit_mixin findings."""
from __future__ import annotations

from pathlib import Path

import pytest

from iabv_v15.services.evolution.efficiency_audit_mixin import (
    tool_efficiency_findings,
    needs_custom_model_findings,
    account_exhaustion_findings,
    external_tool_misdiagnosis_findings,
    heuristic_perturbation_findings,
)
from iabv_v15.services.evolution.account_ledger_service import AccountLedgerService


def _make_run(scope: str, ia: str, status: str = 'success', score: float = 0.8):
    return {
        'comparison_scope_key': scope,
        'config': {'assistant': ia},
        'status': status,
        'quality_score': score,
        'latency_seconds': 1.5,
    }


class TestToolEfficiencyFindings:
    def test_detects_ia_difference(self):
        runs = [
            _make_run('ocr', 'chatgpt', 'success', 0.9),
            _make_run('ocr', 'chatgpt', 'success', 0.85),
            _make_run('ocr', 'chatgpt', 'success', 0.88),
            _make_run('ocr', 'claude', 'failed', 0.2),
            _make_run('ocr', 'claude', 'failed', 0.15),
            _make_run('ocr', 'claude', 'failed', 0.1),
        ]
        findings = tool_efficiency_findings(runs)
        assert len(findings) >= 1
        f = findings[0]
        assert f.category == 'tool_efficiency'
        assert 'claude' in f.title or 'chatgpt' in f.title

    def test_no_finding_when_similar(self):
        runs = [
            _make_run('math', 'chatgpt', 'success', 0.8),
            _make_run('math', 'chatgpt', 'success', 0.75),
            _make_run('math', 'chatgpt', 'success', 0.78),
            _make_run('math', 'claude', 'success', 0.77),
            _make_run('math', 'claude', 'success', 0.79),
            _make_run('math', 'claude', 'success', 0.76),
        ]
        findings = tool_efficiency_findings(runs)
        assert len(findings) == 0

    def test_needs_minimum_runs(self):
        runs = [
            _make_run('code', 'chatgpt', 'success', 0.9),
            _make_run('code', 'claude', 'failed', 0.1),
        ]
        findings = tool_efficiency_findings(runs, min_runs_per_ia=3)
        assert len(findings) == 0


class TestNeedsCustomModelFindings:
    def test_detects_universal_failure(self):
        runs = []
        for ia in ['chatgpt', 'claude', 'codex']:
            for _ in range(5):
                runs.append(_make_run('exotic_task', ia, 'failed', 0.05))
        findings = needs_custom_model_findings(runs, min_runs=5)
        assert len(findings) >= 1
        assert findings[0].category == 'needs_custom_model'

    def test_no_finding_when_one_succeeds(self):
        runs = []
        for _ in range(5):
            runs.append(_make_run('task_x', 'chatgpt', 'failed', 0.1))
        for _ in range(5):
            runs.append(_make_run('task_x', 'claude', 'success', 0.9))
        findings = needs_custom_model_findings(runs, min_runs=5)
        assert len(findings) == 0


class TestAccountExhaustionFindings:
    def test_detects_low_quota(self, tmp_path: Path):
        ledger = AccountLedgerService(tmp_path)
        ledger.register_account('chatgpt', 'a@m.com', '$env:K', messages_limit=100)
        ledger.record_usage('chatgpt', messages_used=95, messages_limit=100)

        findings = account_exhaustion_findings(ledger)
        assert len(findings) >= 1
        assert findings[0].category == 'account_exhaustion'

    def test_no_finding_when_plenty(self, tmp_path: Path):
        ledger = AccountLedgerService(tmp_path)
        ledger.register_account('chatgpt', 'a@m.com', '$env:K', messages_limit=100)
        ledger.record_usage('chatgpt', messages_used=10, messages_limit=100)

        findings = account_exhaustion_findings(ledger)
        assert len(findings) == 0

    def test_none_ledger(self):
        findings = account_exhaustion_findings(None)
        assert findings == []


class TestExternalToolMisdiagnosisFindings:
    def test_detects_recurring_external_fault(self, tmp_path: Path):
        ledger = AccountLedgerService(tmp_path)
        for _ in range(3):
            ledger.record_external_tool_fault(
                'devin_proxy', '403_forbidden',
                our_credentials_ok=True,
                external_service_fault=True,
            )
        findings = external_tool_misdiagnosis_findings(ledger)
        assert len(findings) >= 1
        assert findings[0].category == 'external_tool_misdiagnosis'

    def test_no_finding_when_single_occurrence(self, tmp_path: Path):
        ledger = AccountLedgerService(tmp_path)
        ledger.record_external_tool_fault(
            'devin_proxy', '403_forbidden',
            our_credentials_ok=True,
            external_service_fault=True,
        )
        findings = external_tool_misdiagnosis_findings(ledger)
        assert len(findings) == 0


class TestHeuristicPerturbationFindings:
    def test_detects_dominant_failing_ia(self):
        runs = []
        # chatgpt domina con muchos fallos
        for _ in range(15):
            runs.append(_make_run('code', 'chatgpt', 'failed', 0.2))
        for _ in range(5):
            runs.append(_make_run('code', 'chatgpt', 'success', 0.7))
        # claude pocas veces
        for _ in range(3):
            runs.append(_make_run('code', 'claude', 'success', 0.9))
        for _ in range(2):
            runs.append(_make_run('code', 'ollama', 'success', 0.6))

        findings = heuristic_perturbation_findings(runs)
        assert len(findings) >= 1
        assert findings[0].category == 'heuristic_perturbation'

    def test_no_finding_when_balanced(self):
        runs = []
        for _ in range(10):
            runs.append(_make_run('code', 'chatgpt', 'success', 0.8))
        for _ in range(10):
            runs.append(_make_run('code', 'claude', 'success', 0.7))
        findings = heuristic_perturbation_findings(runs)
        assert len(findings) == 0
