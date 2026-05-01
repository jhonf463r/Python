"""Tests: task_packet patterns → pending issues (auto-improvement loop).

Covers:
- pending issue created for high unresolved
- pending issue created for recurring approval
- pending issue created for no_worker repeated
- no duplicate issues for same pattern
- no issues emitted with insufficient evidence
- existing OSES flow not broken
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


def test_pending_issue_created_for_high_unresolved() -> None:
    """When unresolved ratio exceeds threshold, a pending issue is created."""
    root = _workspace('tp_pi_unresolved')
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

        bootstrap.operational_self_examination_service.build_review()

        issues = bootstrap.pending_issue_repository.find_by_scenario_id(
            'task_packet:high_unresolved',
        )
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.scenario_id == 'task_packet:high_unresolved'
        assert 'unresolved' in issue.summary.lower()
        assert issue.metadata.get('source') == 'oses_task_packet_pattern'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pending_issue_created_for_recurring_approval() -> None:
    """When approval_required ratio exceeds threshold, a pending issue is created."""
    root = _workspace('tp_pi_approval')
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

        bootstrap.operational_self_examination_service.build_review()

        issues = bootstrap.pending_issue_repository.find_by_scenario_id(
            'task_packet:recurring_approval',
        )
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.scenario_id == 'task_packet:recurring_approval'
        assert 'approval' in issue.summary.lower() or 'aprobacion' in issue.summary.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pending_issue_created_for_no_worker() -> None:
    """When selected_worker is empty repeatedly, a pending issue is created."""
    root = _workspace('tp_pi_no_worker')
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

        bootstrap.operational_self_examination_service.build_review()

        issues = bootstrap.pending_issue_repository.find_by_scenario_id(
            'task_packet:no_worker',
        )
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.scenario_id == 'task_packet:no_worker'
        assert 'worker' in issue.summary.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_duplicate_issues_for_same_pattern() -> None:
    """Running build_review() twice must NOT create duplicate pending issues."""
    root = _workspace('tp_pi_no_dup')
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

        bootstrap.operational_self_examination_service.build_review()
        bootstrap.operational_self_examination_service.build_review()

        issues = bootstrap.pending_issue_repository.find_by_scenario_id(
            'task_packet:high_unresolved',
        )
        assert len(issues) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_issues_with_insufficient_evidence() -> None:
    """Fewer than _TP_MIN_RUNS must produce zero pending issues."""
    root = _workspace('tp_pi_insufficient')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'selected_worker': {},
             'governance_flags': {'approval_required': True}},
        ] * 3
        _seed_runs(bootstrap, runs)

        bootstrap.operational_self_examination_service.build_review()

        scenario_ids = [
            'task_packet:high_unresolved',
            'task_packet:recurring_approval',
            'task_packet:no_worker',
            'task_packet:gate_unusable',
        ]
        for sid in scenario_ids:
            issues = bootstrap.pending_issue_repository.find_by_scenario_id(sid)
            assert len(issues) == 0, f'unexpected issue for {sid}'
    finally:
        shutil.rmtree(root, ignore_errors=True)
