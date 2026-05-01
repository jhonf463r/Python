"""Tests: task_packet patterns → pending issues (auto-improvement loop).

Covers:
- pending issue created for high unresolved
- pending issue created for recurring approval
- pending issue created for no_worker (consultable runs only)
- no duplicate issues for same pattern
- no issues emitted with insufficient evidence
- local runs (should_consult=False) do NOT trigger no_worker / gate_unusable
- consultable runs with ranked_worker_count==0 DO trigger gate_unusable
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


# Real worker shapes from #294 (worker_health_gate)
_REAL_WORKER = {'tool': 'chatgpt', 'email': 'user@example.com', 'browser': 'chrome', 'profile': 'Profile 1', 'score': 0.92}


def test_pending_issue_created_for_high_unresolved() -> None:
    """When unresolved ratio exceeds threshold, a pending issue is created."""
    root = _workspace('tp_pi_unresolved')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True}},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True}},
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
             'governance_flags': {'approval_required': True, 'should_consult': True},
             'selected_worker': _REAL_WORKER},
        ] * 5 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'governance_flags': {'approval_required': False},
             'selected_worker': _REAL_WORKER},
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


def test_pending_issue_created_for_no_worker_consultable() -> None:
    """Consultable runs (should_consult=True) with empty selected_worker
    must produce a pending issue for no_worker."""
    root = _workspace('tp_pi_no_worker')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {},
             'governance_flags': {'should_consult': True},
             'ranked_worker_count': 0},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True},
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


def test_local_runs_do_not_trigger_no_worker_or_gate_unusable() -> None:
    """Local runs (should_consult=False) with empty selected_worker and
    ranked_worker_count==0 must NOT produce no_worker or gate_unusable
    pending issues."""
    root = _workspace('tp_pi_local_guard')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {},
             'governance_flags': {'should_consult': False},
             'ranked_worker_count': 0},
        ] * 6
        _seed_runs(bootstrap, runs)

        bootstrap.operational_self_examination_service.build_review()

        for sid in ('task_packet:no_worker', 'task_packet:gate_unusable'):
            issues = bootstrap.pending_issue_repository.find_by_scenario_id(sid)
            assert len(issues) == 0, f'unexpected issue for {sid} from local runs'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_consultable_gate_unusable_creates_issue() -> None:
    """Consultable runs with ranked_worker_count==0 must produce a
    gate_unusable pending issue."""
    root = _workspace('tp_pi_gate_unusable')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {},
             'governance_flags': {'should_consult': True},
             'ranked_worker_count': 0},
        ] * 3 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True},
             'ranked_worker_count': 2},
        ] * 3
        _seed_runs(bootstrap, runs)

        bootstrap.operational_self_examination_service.build_review()

        issues = bootstrap.pending_issue_repository.find_by_scenario_id(
            'task_packet:gate_unusable',
        )
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.scenario_id == 'task_packet:gate_unusable'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_duplicate_issues_for_same_pattern() -> None:
    """Running build_review() twice must NOT create duplicate pending issues."""
    root = _workspace('tp_pi_no_dup')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True}},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': _REAL_WORKER,
             'governance_flags': {'should_consult': True}},
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
             'governance_flags': {'approval_required': True, 'should_consult': True}},
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
