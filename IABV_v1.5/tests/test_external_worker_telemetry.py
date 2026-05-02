"""Tests for ExternalWorkerTelemetry contract and integration.

Covers:
- Model instantiation with defaults and explicit values
- TaskOutcomeRecorder propagation of worker_telemetry to ExperimentRun.metadata
- PortableContextService aggregation of worker_telemetry_summary
- OSES detection of budget exhaustion and unresolved handoffs
"""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.bootstrap import AppBootstrap
from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExternalWorkerTelemetry,
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
            'evidence_basis': rd.get('evidence_basis', {'state': 'observed'}),
            'governance_flags': rd.get('governance_flags', {}),
            'selected_worker': rd.get('selected_worker', {}),
            'ranked_worker_count': rd.get('ranked_worker_count', 1),
            'task_unresolved': rd.get('task_unresolved', []),
            'assistant_kind': 'codex',
            'comparison_scope_key': 'general',
        }
        if 'worker_telemetry' in rd:
            meta['worker_telemetry'] = rd['worker_telemetry']
        bootstrap.experiment_lab.record_outcome(
            domain=ExperimentDomain.LANGUAGE,
            objective='test objective',
            subject_key='general',
            route=EvaluationRoute.LOCAL,
            candidate_label='codex',
            success=rd.get('success', True),
            observed_summary='test run',
            precision=0.8,
            robustness=0.8,
            execution_ms=100,
            metadata=meta,
        )


# ---- Model contract tests ----

def test_external_worker_telemetry_defaults() -> None:
    wt = ExternalWorkerTelemetry()
    assert wt.worker_kind == ''
    assert wt.budget_state == 'ok'
    assert wt.continuation_state == 'complete'
    assert wt.handoff_required is False
    assert wt.human_intervention_required is False
    assert wt.merge_success is None
    assert wt.files_touched_scope == []
    assert wt.correction_rounds == 0


def test_external_worker_telemetry_explicit_values() -> None:
    wt = ExternalWorkerTelemetry(
        worker_kind='codex',
        assistant_kind='codex',
        worker_id='session-abc',
        task_packet_id='tp-123',
        budget_state='exhausted',
        continuation_state='truncated',
        handoff_required=True,
        resume_hint='Continue OSES integration',
        human_intervention_required=False,
        result_status='partial',
        latency_ms=45000,
        correction_rounds=2,
        merge_success=False,
        files_touched_scope=['models.py', 'task_outcome_recorder.py'],
    )
    assert wt.worker_kind == 'codex'
    assert wt.budget_state == 'exhausted'
    assert wt.handoff_required is True
    assert wt.latency_ms == 45000
    assert len(wt.files_touched_scope) == 2


def test_external_worker_telemetry_serialization() -> None:
    wt = ExternalWorkerTelemetry(
        worker_kind='devin',
        budget_state='ok',
        merge_success=True,
    )
    data = wt.model_dump(mode='json')
    assert data['worker_kind'] == 'devin'
    assert data['merge_success'] is True
    restored = ExternalWorkerTelemetry.model_validate(data)
    assert restored.worker_kind == 'devin'


# ---- PortableContext aggregation tests ----

def test_portable_context_includes_worker_telemetry_summary() -> None:
    root = _workspace('wt_portable_context')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'exhausted',
                    'handoff_required': True,
                    'continuation_state': 'truncated',
                },
            },
        ] * 3 + [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'devin',
                    'budget_state': 'ok',
                    'handoff_required': False,
                },
            },
        ] * 3
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)
        tp_section = next(
            (s for s in package.sections if s.section_id == 'task_packet_summary'),
            None,
        )
        assert tp_section is not None
        wt_summary = tp_section.metadata.get('worker_telemetry_summary')
        assert wt_summary is not None, 'worker_telemetry_summary missing from snapshot'
        assert wt_summary['runs_with_telemetry'] == 6
        assert wt_summary['budget_exhausted_count'] == 3
        assert wt_summary['handoff_required_count'] == 3
        kinds = {d['kind'] for d in wt_summary['worker_kind_distribution']}
        assert 'codex' in kinds
        assert 'devin' in kinds
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_portable_context_no_telemetry_when_absent() -> None:
    root = _workspace('wt_no_telemetry')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {'evidence_basis': {'state': 'observed'}},
        ] * 6
        _seed_runs(bootstrap, runs)

        package = bootstrap.portable_context_service.current_package(refresh=True)
        tp_section = next(
            (s for s in package.sections if s.section_id == 'task_packet_summary'),
            None,
        )
        assert tp_section is not None
        assert 'worker_telemetry_summary' not in tp_section.metadata


    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- OSES pattern detection tests ----

def test_oses_detects_budget_exhaustion_pattern() -> None:
    root = _workspace('wt_oses_budget')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'budget_state': 'exhausted',
                },
            },
        ] * 4 + [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'devin',
                    'budget_state': 'ok',
                },
            },
        ] * 2
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_worker_budget_exhausted' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_detects_handoff_unresolved_pattern() -> None:
    root = _workspace('wt_oses_handoff')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'handoff_required': True,
                    'continuation_state': 'truncated',
                },
            },
        ] * 3 + [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'devin',
                    'handoff_required': False,
                    'continuation_state': 'complete',
                },
            },
        ] * 3
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_worker_handoff_unresolved' in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_oses_no_finding_when_handoffs_resolved() -> None:
    root = _workspace('wt_oses_resolved')
    try:
        bootstrap = AppBootstrap(str(root))
        runs = [
            {
                'evidence_basis': {'state': 'observed'},
                'worker_telemetry': {
                    'worker_kind': 'codex',
                    'handoff_required': True,
                    'continuation_state': 'resumed',
                },
            },
        ] * 4 + [
            {'evidence_basis': {'state': 'observed'}},
        ] * 2
        _seed_runs(bootstrap, runs)

        review = bootstrap.operational_self_examination_service.current_review(refresh=True)
        categories = [f.category for f in review.findings]
        assert 'task_packet_worker_handoff_unresolved' not in categories
    finally:
        shutil.rmtree(root, ignore_errors=True)
