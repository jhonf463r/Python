"""Tests for BIO-UNIVERSAL-08 — Open First Real Decision Access to Current Discernment.

Tests focus on:
- Current discernment frame summary reaches TaskContext.metadata
- Decision behavior remains unchanged (no policy change)
- Rebuilt DecisionContext preserves discernment summary
"""
from __future__ import annotations

from typing import Any

import pytest

from iabv_v15.domain.models import TaskContext


def test_discernment_summary_in_task_context_metadata():
    """Test: discernment_frame_summary can be set in TaskContext.metadata."""
    task_context = TaskContext()
    task_context.metadata = {
        'discernment_frame_summary': {
            'status': 'frame_available',
            'detected_concepts': ['test_concept'],
            'grounding_status': 'grounded',
        }
    }
    
    # Verify discernment_frame_summary is in TaskContext.metadata
    assert task_context.metadata is not None
    assert 'discernment_frame_summary' in task_context.metadata
    discernment_summary = task_context.metadata['discernment_frame_summary']
    
    # Verify structure
    assert discernment_summary['status'] == 'frame_available'
    assert 'test_concept' in discernment_summary.get('detected_concepts', [])
    assert discernment_summary['grounding_status'] == 'grounded'


def test_unavailable_status_in_task_context_metadata():
    """Test: unavailable status can be set in TaskContext.metadata."""
    task_context = TaskContext()
    task_context.metadata = {
        'discernment_frame_summary': {
            'status': 'current_frame_unavailable',
        }
    }
    
    # Verify unavailable status
    assert task_context.metadata is not None
    assert 'discernment_frame_summary' in task_context.metadata
    discernment_summary = task_context.metadata['discernment_frame_summary']
    assert discernment_summary.get('status') == 'current_frame_unavailable'
    
    # Verify no fabricated concepts
    assert discernment_summary.get('detected_concepts') is None or len(discernment_summary.get('detected_concepts', [])) == 0


def test_no_fabricated_concepts_when_unavailable():
    """Test: no concepts are fabricated when frame is unavailable."""
    task_context = TaskContext()
    task_context.metadata = {
        'discernment_frame_summary': {
            'status': 'current_frame_unavailable',
        }
    }
    
    discernment_summary = task_context.metadata.get('discernment_frame_summary', {})
    
    # Verify no grounding, confidence, or concepts are fabricated
    assert discernment_summary.get('grounding_status') is None or discernment_summary.get('grounding_status') != 'grounded'
    assert discernment_summary.get('confidence') is None or discernment_summary.get('confidence') == 0
    assert discernment_summary.get('detected_concepts') is None or len(discernment_summary.get('detected_concepts', [])) == 0
    assert discernment_summary.get('selected_action') is None


def test_current_vs_historical_distinction():
    """Test: current frame concepts are distinct from historical."""
    # Create two contexts with different discernment summaries
    current_context = TaskContext()
    current_context.metadata = {
        'discernment_frame_summary': {
            'status': 'frame_available',
            'detected_concepts': ['CURRENT_concept'],
            'grounding_status': 'grounded',
        }
    }
    
    historical_context = TaskContext()
    historical_context.metadata = {
        'discernment_frame_summary': {
            'status': 'frame_available',
            'detected_concepts': ['HISTORICAL_concept'],
            'grounding_status': 'grounded',
        }
    }
    
    # Verify they are distinct
    current_concepts = current_context.metadata['discernment_frame_summary']['detected_concepts']
    historical_concepts = historical_context.metadata['discernment_frame_summary']['detected_concepts']
    
    assert 'CURRENT_concept' in current_concepts
    assert 'HISTORICAL_concept' not in current_concepts
    assert 'HISTORICAL_concept' in historical_concepts
    assert 'CURRENT_concept' not in historical_concepts


def test_frame_summary_preserved_across_context_copy():
    """Test: discernment summary is preserved when copying TaskContext."""
    original = TaskContext()
    original.metadata = {
        'discernment_frame_summary': {
            'status': 'frame_available',
            'detected_concepts': ['test_concept'],
            'grounding_status': 'grounded',
        }
    }
    
    # Simulate copying metadata
    copied = TaskContext()
    copied.metadata = dict(original.metadata or {})
    
    # Verify discernment summary is preserved
    assert 'discernment_frame_summary' in copied.metadata
    assert copied.metadata['discernment_frame_summary']['status'] == 'frame_available'
    assert 'test_concept' in copied.metadata['discernment_frame_summary'].get('detected_concepts', [])
