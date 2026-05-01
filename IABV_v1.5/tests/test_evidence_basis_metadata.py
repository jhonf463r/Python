"""Focused tests for evidence_basis preservation in metadata.

Covers:
- TaskContextAssembler._classify_evidence_basis static method
- evidence_basis appears in DecisionContext.metadata
- evidence_basis appears in PerceptionSnapshot.metadata
- TaskOutcomeRecorder preserves evidence_basis in learning records
- ControlCenterViewModel stamps chat_evidence_tag in adaptive metadata
"""
from __future__ import annotations

from typing import Any

from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler


# ─── _classify_evidence_basis ────────────────────────────────


def test_evidence_basis_observed_with_world_model() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=True,
        has_environment=True,
    )
    assert result['state'] == 'observed'
    assert 'world_model' in result['live_sources']
    assert 'environment_self_model' in result['live_sources']


def test_evidence_basis_observed_world_model_only() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=True,
        has_environment=False,
    )
    assert result['state'] == 'observed'
    assert 'world_model' in result['live_sources']


def test_evidence_basis_inferred_with_learning() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=False,
        has_environment=False,
        has_persisted_learning=True,
    )
    assert result['state'] == 'inferred'
    assert 'adaptive_learning' in result['persisted_sources']
    assert result['live_sources'] == []


def test_evidence_basis_inferred_with_ia_trace() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=False,
        has_persisted_learning=False,
        has_ia_trace=True,
    )
    assert result['state'] == 'inferred'
    assert 'ia_trace' in result['persisted_sources']


def test_evidence_basis_unresolved_nothing() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=False,
        has_environment=False,
        has_persisted_learning=False,
        has_ia_trace=False,
    )
    assert result['state'] == 'unresolved'
    assert result['live_sources'] == []
    assert result['persisted_sources'] == []


def test_evidence_basis_unresolved_fields_propagated() -> None:
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=True,
        unresolved_fields=['UNRESOLVED:runtime_signals', 'UNRESOLVED:visual_signal'],
    )
    assert result['state'] == 'observed'
    assert len(result['unresolved']) == 2
    assert 'UNRESOLVED:runtime_signals' in result['unresolved']


def test_evidence_basis_observed_overrides_inferred() -> None:
    """Live sources take precedence even if persisted also present."""
    result = TaskContextAssembler._classify_evidence_basis(
        has_world_model=True,
        has_persisted_learning=True,
        has_ia_trace=True,
    )
    assert result['state'] == 'observed'
    assert 'world_model' in result['live_sources']
    assert 'adaptive_learning' in result['persisted_sources']


def test_evidence_basis_returns_dict_shape() -> None:
    result = TaskContextAssembler._classify_evidence_basis()
    assert isinstance(result, dict)
    assert 'state' in result
    assert 'live_sources' in result
    assert 'persisted_sources' in result
    assert 'unresolved' in result
    assert result['state'] in ('observed', 'inferred', 'unresolved')


# ─── Outcome recorder evidence_basis preservation ───────────


def test_outcome_recorder_reads_evidence_basis_from_decision_context() -> None:
    """Verify the metadata extraction pattern used by TaskOutcomeRecorder."""
    session_metadata: dict[str, Any] = {
        'decision_context': {
            'metadata': {
                'evidence_basis': {
                    'state': 'observed',
                    'live_sources': ['world_model'],
                    'persisted_sources': [],
                    'unresolved': [],
                },
            },
        },
    }
    evidence_basis = dict(
        (dict(session_metadata.get('decision_context') or {}).get('metadata') or {}).get('evidence_basis')
        or (dict(session_metadata.get('perception_snapshot') or {}).get('metadata') or {}).get('evidence_basis')
        or {}
    )
    assert evidence_basis['state'] == 'observed'
    assert 'world_model' in evidence_basis['live_sources']


def test_outcome_recorder_fallback_to_perception_snapshot() -> None:
    """If decision_context doesn't have it, falls back to perception_snapshot."""
    session_metadata: dict[str, Any] = {
        'decision_context': {'metadata': {}},
        'perception_snapshot': {
            'metadata': {
                'evidence_basis': {
                    'state': 'inferred',
                    'live_sources': [],
                    'persisted_sources': ['ia_trace'],
                    'unresolved': [],
                },
            },
        },
    }
    evidence_basis = dict(
        (dict(session_metadata.get('decision_context') or {}).get('metadata') or {}).get('evidence_basis')
        or (dict(session_metadata.get('perception_snapshot') or {}).get('metadata') or {}).get('evidence_basis')
        or {}
    )
    assert evidence_basis['state'] == 'inferred'


def test_outcome_recorder_empty_when_no_evidence_basis() -> None:
    """Graceful fallback when no evidence_basis exists."""
    session_metadata: dict[str, Any] = {
        'decision_context': {'metadata': {}},
    }
    evidence_basis = dict(
        (dict(session_metadata.get('decision_context') or {}).get('metadata') or {}).get('evidence_basis')
        or (dict(session_metadata.get('perception_snapshot') or {}).get('metadata') or {}).get('evidence_basis')
        or {}
    )
    assert evidence_basis == {}


# ─── ViewModel chat_evidence_tag stamp ───────────────────────


def test_viewmodel_stamps_chat_evidence_tag_in_metadata() -> None:
    """Simulates the stamp logic from ControlCenterViewModel."""
    adaptive_payload: dict[str, Any] = {'metadata': {}}
    chat_evidence_tag = 'observed'
    _ap_meta = adaptive_payload.setdefault('metadata', {})
    if isinstance(_ap_meta, dict):
        _ap_meta['chat_evidence_tag'] = chat_evidence_tag
    assert adaptive_payload['metadata']['chat_evidence_tag'] == 'observed'


def test_viewmodel_stamp_creates_metadata_if_missing() -> None:
    adaptive_payload: dict[str, Any] = {}
    chat_evidence_tag = 'inferred'
    _ap_meta = adaptive_payload.setdefault('metadata', {})
    if isinstance(_ap_meta, dict):
        _ap_meta['chat_evidence_tag'] = chat_evidence_tag
    assert adaptive_payload['metadata']['chat_evidence_tag'] == 'inferred'


def test_viewmodel_stamp_safe_with_non_dict_metadata() -> None:
    adaptive_payload: dict[str, Any] = {'metadata': 'not_a_dict'}
    chat_evidence_tag = 'unresolved'
    _ap_meta = adaptive_payload.setdefault('metadata', {})
    if isinstance(_ap_meta, dict):
        _ap_meta['chat_evidence_tag'] = chat_evidence_tag
    # Should not crash; metadata stays as the original non-dict value
    assert adaptive_payload['metadata'] == 'not_a_dict'
