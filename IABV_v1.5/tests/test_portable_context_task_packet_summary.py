"""FASE 1 — Tests for task_packet_summary section in PortableContextService.

Covers:
- summary with observed predominant evidence
- summary with high unresolved ratio
- summary with recurring approvals
- metadata/section consistency
- insufficient data → UNRESOLVED
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
    """Seed ExperimentLab with runs carrying task_packet metadata."""
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


def test_task_packet_summary_observed_predominant() -> None:
    """When most runs have evidence_basis.state == 'observed', the summary
    section should reflect observed as predominant."""
    root = _workspace('tp_summary_observed')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {'name': 'ollama'},
             'governance_flags': {'approval_required': False}},
        ] * 5 + [
            {'evidence_basis': {'state': 'inferred'},
             'selected_worker': {'name': 'ollama'}},
        ]
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        tp_section = next(
            s for s in package.sections if s.section_id == 'task_packet_summary'
        )
        assert 'observed' in tp_section.summary.lower()
        assert tp_section.confidence > 0.0
        assert not tp_section.unresolved_fields

        meta = package.metadata.get('task_packet_summary', {})
        assert meta['status'] == 'ok'
        assert meta['evidence_state_distribution']['observed'] == 5
        assert meta['run_count'] == 6

        dist_item = next(
            i for i in tp_section.items if i.get('label') == 'evidence_state_distribution'
        )
        assert 'observed' in str(dist_item.get('value', ''))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_packet_summary_high_unresolved() -> None:
    """When most runs have evidence_basis.state == 'unresolved', the summary
    flags the high unresolved ratio."""
    root = _workspace('tp_summary_unresolved')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'unresolved'},
             'task_unresolved': ['cpu_temperature', 'battery_status'],
             'selected_worker': {}},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {'name': 'ollama'}},
        ]
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        tp_section = next(
            s for s in package.sections if s.section_id == 'task_packet_summary'
        )
        assert 'unresolved' in tp_section.summary.lower()

        meta = package.metadata.get('task_packet_summary', {})
        assert meta['status'] == 'ok'
        assert meta['evidence_state_distribution'].get('unresolved', 0) >= 4
        hotspots = meta.get('unresolved_hotspots', [])
        assert any(h['field'] == 'cpu_temperature' for h in hotspots)
        assert any(h['field'] == 'battery_status' for h in hotspots)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_packet_summary_recurring_approvals() -> None:
    """When approval_required is True in many runs, the summary reflects it."""
    root = _workspace('tp_summary_approvals')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'governance_flags': {'approval_required': True},
             'selected_worker': {'name': 'ollama'}},
        ] * 4 + [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'governance_flags': {'approval_required': False},
             'selected_worker': {'name': 'ollama'}},
        ]
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        meta = package.metadata.get('task_packet_summary', {})
        assert meta['status'] == 'ok'
        assert meta['approval_required_count'] == 4
        assert meta['approval_required_rate'] > 0.5

        tp_section = next(
            s for s in package.sections if s.section_id == 'task_packet_summary'
        )
        approval_item = next(
            i for i in tp_section.items if i.get('label') == 'approval_required'
        )
        assert '4' in str(approval_item.get('value', ''))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_packet_summary_metadata_and_section_consistency() -> None:
    """Metadata and section fields must be consistent and well-formed."""
    root = _workspace('tp_summary_consistency')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed', 'live_sources': ['world_model']},
             'selected_worker': {'name': 'ollama'},
             'governance_flags': {'approval_required': False},
             'ranked_worker_count': 2,
             'task_unresolved': ['field_a']},
            {'evidence_basis': {'state': 'inferred'},
             'selected_worker': {'name': 'codex'},
             'governance_flags': {'approval_required': True},
             'ranked_worker_count': 0,
             'task_unresolved': ['field_a', 'field_b']},
            {'evidence_basis': {'state': 'observed', 'live_sources': ['env']},
             'selected_worker': {'assistant_kind': 'claude'},
             'governance_flags': {'approval_required': False},
             'ranked_worker_count': 1},
        ]
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        section_ids = {s.section_id for s in package.sections}
        assert 'task_packet_summary' in section_ids

        tp_section = next(
            s for s in package.sections if s.section_id == 'task_packet_summary'
        )
        assert tp_section.source_kind == 'experiment_lab_repository'
        assert 'ExperimentLab' in tp_section.source_refs

        meta = package.metadata.get('task_packet_summary', {})
        assert meta['status'] == 'ok'
        assert meta['run_count'] == 3
        assert isinstance(meta['evidence_state_distribution'], dict)
        assert isinstance(meta['worker_tendencies'], list)
        assert isinstance(meta['unresolved_hotspots'], list)

        workers = {w['worker'] for w in meta['worker_tendencies']}
        assert 'ollama' in workers
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_task_packet_summary_insufficient_data_marks_unresolved() -> None:
    """With fewer than _TASK_PACKET_MIN_RUNS runs with evidence_basis,
    the section should mark UNRESOLVED."""
    root = _workspace('tp_summary_insufficient')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed'},
             'selected_worker': {'name': 'ollama'}},
        ]
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)

        tp_section = next(
            s for s in package.sections if s.section_id == 'task_packet_summary'
        )
        assert tp_section.confidence == 0.0
        assert any('UNRESOLVED' in u for u in tp_section.unresolved_fields)
        assert 'insuficiente' in tp_section.summary.lower() or 'insufficient' in tp_section.summary.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)
