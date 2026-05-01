"""FASE 2 — Tests for task_packet pattern findings in OSES.

Covers:
- finding por unresolved alto
- finding por approvals repetidos
- finding por no_worker repetido
- no emitir findings con evidencia insuficiente
"""
import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
)


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _seed_runs(bootstrap: AppBootstrap, runs_data: list[dict]) -> None:
    for rd in runs_data:
        meta = {
            'evidence_basis': rd.get('evidence_basis', {}),
            'governance_flags': rd.get('governance_flags', {}),
            'selected_worker': rd.get('selected_worker', {}),
            'ranked_worker_count': rd.get('ranked_worker_count', 1),
            'task_unresolved': rd.get('task_unresolved', []),
            'assistant_kind': 'ollama',
            'comparison_scope_key': 'general',
        }
        bootstrap.experiment_lab.record_outcome(
            domain=ExperimentDomain.LANGUAGE,
            objective='test objective',
            subject_key='general',
            route=EvaluationRoute.LOCAL,
            candidate_label='ollama',
            success=rd.get('success', True),
            observed_summary='test run',
            precision=0.8,
            robustness=0.8,
            execution_ms=100,
            metadata=meta,
        )


def test_oses_finding_high_unresolved() -> None:
    """OSES emits a finding when unresolved ratio exceeds threshold."""
    root = _workspace('oses_tp_unresolved')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'selected_worker': {'name': 'ollama'}},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {'name': 'ollama'}},
        ] * 2
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.build_review()

        tp_findings = [
            f for f in review.findings
            if f.category == 'task_packet_high_unresolved'
        ]
        assert len(tp_findings) >= 1
        finding = tp_findings[0]
        assert 'unresolved' in finding.title.lower()
        assert finding.metadata.get('pattern') == 'high_unresolved'
        assert finding.metadata.get('unresolved_count', 0) >= 4
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_finding_recurring_approvals() -> None:
    """OSES emits a finding when approval_required is repeatedly true."""
    root = _workspace('oses_tp_approvals')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'governance_flags': {'approval_required': True},
             'selected_worker': {'name': 'ollama'}},
        ] * 5 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'governance_flags': {'approval_required': False},
             'selected_worker': {'name': 'ollama'}},
        ]
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.build_review()

        tp_findings = [
            f for f in review.findings
            if f.category == 'task_packet_recurring_approval'
        ]
        assert len(tp_findings) >= 1
        finding = tp_findings[0]
        assert 'approval' in finding.title.lower()
        assert finding.metadata.get('pattern') == 'recurring_approval'
        assert finding.metadata.get('approval_count', 0) >= 5
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_finding_no_worker_repeated() -> None:
    """OSES emits a finding when selected_worker is empty repeatedly."""
    root = _workspace('oses_tp_no_worker')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {},
             'ranked_worker_count': 0},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {'name': 'ollama'},
             'ranked_worker_count': 2},
        ] * 2
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.build_review()

        no_worker_findings = [
            f for f in review.findings
            if f.category == 'task_packet_no_worker'
        ]
        assert len(no_worker_findings) >= 1
        finding = no_worker_findings[0]
        assert 'worker' in finding.title.lower()
        assert finding.metadata.get('pattern') == 'no_worker'
        assert finding.metadata.get('no_worker_count', 0) >= 4
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_no_findings_with_insufficient_evidence() -> None:
    """OSES must NOT emit task_packet findings when there are fewer than
    _TP_MIN_RUNS runs with evidence_basis metadata."""
    root = _workspace('oses_tp_insufficient')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'selected_worker': {},
             'governance_flags': {'approval_required': True}},
        ] * 3
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.build_review()

        tp_categories = {
            'task_packet_high_unresolved',
            'task_packet_recurring_approval',
            'task_packet_no_worker',
            'task_packet_gate_unusable',
        }
        tp_findings = [
            f for f in review.findings
            if f.category in tp_categories
        ]
        assert len(tp_findings) == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
