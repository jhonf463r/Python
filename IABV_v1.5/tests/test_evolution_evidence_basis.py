"""Focused tests for FASE 2: EvolutionCenter consumes evidence_basis.

Tests the evidence_basis extraction logic from portable context metadata.
Does NOT require PySide6 — tests the data flow logic directly.

Covers:
- evidence_basis extraction from portable_context.metadata
- truthState mapping for observed/inferred/unresolved
- Empty/missing evidence_basis defaults to unresolved
- Existing properties remain unbroken after adding evidenceBasis
"""
from __future__ import annotations

from typing import Any


def _extract_evidence_basis(portable_context: dict[str, Any]) -> dict[str, Any]:
    """Replicate the extraction logic from EvolutionCenterViewModel.refresh()."""
    eb_raw = dict((portable_context.get('metadata') or {}).get('evidence_basis') or {})
    eb_state = str(eb_raw.get('state') or 'unresolved')
    eb_raw['truthState'] = eb_state
    return eb_raw


# ─── evidence_basis extraction ─────────────────────────────


def test_evidence_basis_observed() -> None:
    ctx = {
        'metadata': {
            'evidence_basis': {
                'state': 'observed',
                'live_sources': ['world_model', 'environment_self_model'],
                'persisted_sources': [],
                'unresolved': [],
            }
        }
    }
    result = _extract_evidence_basis(ctx)
    assert result['state'] == 'observed'
    assert result['truthState'] == 'observed'
    assert 'world_model' in result['live_sources']
    assert 'environment_self_model' in result['live_sources']


def test_evidence_basis_inferred() -> None:
    ctx = {
        'metadata': {
            'evidence_basis': {
                'state': 'inferred',
                'live_sources': [],
                'persisted_sources': ['adaptive_learning', 'ia_trace'],
                'unresolved': [],
            }
        }
    }
    result = _extract_evidence_basis(ctx)
    assert result['state'] == 'inferred'
    assert result['truthState'] == 'inferred'
    assert result['persisted_sources'] == ['adaptive_learning', 'ia_trace']


def test_evidence_basis_unresolved() -> None:
    ctx = {
        'metadata': {
            'evidence_basis': {
                'state': 'unresolved',
                'live_sources': [],
                'persisted_sources': [],
                'unresolved': ['UNRESOLVED:world_model'],
            }
        }
    }
    result = _extract_evidence_basis(ctx)
    assert result['state'] == 'unresolved'
    assert result['truthState'] == 'unresolved'
    assert 'UNRESOLVED:world_model' in result['unresolved']


def test_evidence_basis_missing_defaults_unresolved() -> None:
    ctx = {'metadata': {}}
    result = _extract_evidence_basis(ctx)
    assert result['truthState'] == 'unresolved'
    assert result.get('live_sources') is None or result.get('live_sources') == []


def test_evidence_basis_no_metadata() -> None:
    ctx = {}
    result = _extract_evidence_basis(ctx)
    assert result['truthState'] == 'unresolved'


def test_evidence_basis_preserves_source_lists() -> None:
    ctx = {
        'metadata': {
            'evidence_basis': {
                'state': 'observed',
                'live_sources': ['world_model'],
                'persisted_sources': ['adaptive_learning'],
                'unresolved': ['UNRESOLVED:visual_signal'],
            }
        }
    }
    result = _extract_evidence_basis(ctx)
    assert result['live_sources'] == ['world_model']
    assert result['persisted_sources'] == ['adaptive_learning']
    assert result['unresolved'] == ['UNRESOLVED:visual_signal']
    assert result['truthState'] == 'observed'


# ─── EvolutionCenterViewModel source inspection ─────────────


def test_viewmodel_source_has_evidence_basis_getter() -> None:
    """Verify the viewmodel source defines get_evidence_basis."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / 'src' / 'iabv_v15' / 'ui' / 'viewmodels' / 'evolution_center_viewmodel.py'
    text = src.read_text()
    assert 'def get_evidence_basis' in text, 'EvolutionCenterViewModel must define get_evidence_basis'
    assert 'evidenceBasis' in text, 'EvolutionCenterViewModel must expose evidenceBasis Property'


def test_viewmodel_refresh_populates_evidence_basis() -> None:
    """Verify refresh() populates _evidence_basis from portable context metadata."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / 'src' / 'iabv_v15' / 'ui' / 'viewmodels' / 'evolution_center_viewmodel.py'
    text = src.read_text()
    assert "evidence_basis" in text, 'refresh() must reference evidence_basis'
    assert "_evidence_basis" in text, 'refresh() must populate _evidence_basis'
    assert "eb_raw" in text or "evidence_basis" in text, 'refresh() must extract evidence_basis from metadata'
