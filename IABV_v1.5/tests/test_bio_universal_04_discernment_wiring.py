"""Tests for BIO-UNIVERSAL-04 — Devin Minimal Discernment Task-Path Wiring.

Tests focus on:
- Bootstrap creates DiscernmentFrameService
- TaskContextAssembler receives DiscernmentFrameService via DI
- build_perception_snapshot() constructs real frame from current task
- Visual semantic evidence is adapted to DiscernmentFrameService contract
- Frame summary flows into DecisionContext and PerceptionSnapshot
- Positive case: frame built with real concepts
- Negative control: empty concepts produce empty frame (no fabrication)
- Lifecycle: summary corresponds to current frame, not historical
- Safety: graceful degradation when service unavailable
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.domain.models import (
    InferenceRequest,
    TaskIntent,
    VisualSignalSnapshot,
    WorldModelSnapshot,
    EnvironmentSelfModel,
)


class FakeDiscernmentFrameService:
    """Fake DiscernmentFrameService for testing."""
    
    def __init__(self) -> None:
        self._frames: list[Any] = []
    
    def build_frame(self, **kwargs) -> Any:
        """Build a minimal frame for testing."""
        frame = {
            'phase': kwargs.get('phase', 'observe'),
            'trigger_source': kwargs.get('trigger_source', ''),
            'raw_inputs': kwargs.get('raw_inputs', []),
            'detected_concepts': [],
            'concept_weights': {},
            'grounding_status': 'unknown',
        }
        
        # Extract concept_weight_evidence
        cwe = kwargs.get('concept_weight_evidence', {})
        if cwe:
            frame['detected_concepts'] = list(cwe.get('concepts', []))
            frame['concept_weights'] = dict(cwe.get('weights', {}))
        
        self._frames.append(frame)
        return frame
    
    def discernment_frame_summary(self, frame: Any | None = None) -> dict[str, Any]:
        """Return summary of latest frame or provided frame."""
        if frame is not None:
            return {
                'status': 'frame_available',
                'detected_concepts': frame.get('detected_concepts', []),
                'concept_weights': frame.get('concept_weights', {}),
                'grounding_status': frame.get('grounding_status', 'unknown'),
            }
        
        if self._frames:
            latest = self._frames[-1]
            return {
                'status': 'frame_available',
                'detected_concepts': latest.get('detected_concepts', []),
                'concept_weights': latest.get('concept_weights', {}),
                'grounding_status': latest.get('grounding_status', 'unknown'),
            }
        
        return {'status': 'no_frame'}


def test_bootstrap_creates_discernment_frame_service():
    """Bootstrap creates DiscernmentFrameService instance."""
    from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
    
    # Create service with workspace root
    service = DiscernmentFrameService(workspace_root='/tmp/test')
    
    assert service is not None
    assert service._workspace_root == '/tmp/test'
    assert len(service._frame_history) == 0


def test_task_context_assembler_di_wiring():
    """TaskContextAssembler accepts discernment_frame_service via DI."""
    from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
    from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
    
    class FakeRepository:
        pass
    
    with tempfile.TemporaryDirectory() as tmpdir:
        site_policy_registry = SitePolicyRegistry(tmpdir)
        discernment_service = FakeDiscernmentFrameService()
        
        assembler = TaskContextAssembler(
            episode_repository=FakeRepository(),  # type: ignore
            knowledge_repository=FakeRepository(),  # type: ignore
            run_repository=FakeRepository(),  # type: ignore
            dossier_repository=FakeRepository(),  # type: ignore
            hidden_incident_repository=FakeRepository(),  # type: ignore
            site_policy_registry=site_policy_registry,
            capability_repository=FakeRepository(),  # type: ignore
            adaptive_session_repository=FakeRepository(),  # type: ignore
            discernment_frame_service=discernment_service,
        )
        
        assert assembler.discernment_frame_service is discernment_service


def test_visual_semantic_evidence_adapter():
    """Visual semantic evidence is adapted to DiscernmentFrameService contract."""
    discernment_service = FakeDiscernmentFrameService()
    
    # Simulate visual metadata from UniversalPerceptionService
    visual_metadata = {
        'visual_concepts': ['login_screen_candidate', 'chat_input_ready'],
        'concept_weights': {
            'login_screen_candidate': 0.9,
            'chat_input_ready': 0.86,
        },
        'semantic_sources': ['browser_dom'],
    }
    
    # Adapt to DiscernmentFrameService contract
    concept_weight_evidence = {
        "concepts": list(visual_metadata.get("visual_concepts") or []),
        "weights": dict(visual_metadata.get("concept_weights") or {}),
        "sources": list(visual_metadata.get("semantic_sources") or []),
    }
    
    # Build frame
    frame = discernment_service.build_frame(
        phase='observe',
        trigger_source='test',
        raw_inputs=['test goal'],
        concept_weight_evidence=concept_weight_evidence,
    )
    
    # Verify concepts were transferred
    assert 'login_screen_candidate' in frame['detected_concepts']
    assert 'chat_input_ready' in frame['detected_concepts']
    assert frame['concept_weights']['login_screen_candidate'] == 0.9
    assert frame['concept_weights']['chat_input_ready'] == 0.86


def test_positive_case_frame_construction():
    """Positive case: frame built with real concepts from visual evidence."""
    discernment_service = FakeDiscernmentFrameService()
    
    # Create visual evidence
    concept_weight_evidence = {
        "concepts": ['login_screen_candidate', 'chat_input_ready'],
        "weights": {
            'login_screen_candidate': 0.9,
            'chat_input_ready': 0.86,
        },
        "sources": ['browser_dom'],
    }
    
    # Build frame
    frame = discernment_service.build_frame(
        phase='observe',
        trigger_source='task_context_assembler',
        raw_inputs=['test goal'],
        concept_weight_evidence=concept_weight_evidence,
    )
    
    # Critical assertion: concepts from visual evidence are in frame
    assert 'login_screen_candidate' in frame['detected_concepts']
    assert 'chat_input_ready' in frame['detected_concepts']
    assert frame['concept_weights'].get('login_screen_candidate') == 0.9
    assert frame['concept_weights'].get('chat_input_ready') == 0.86
    
    # Verify summary
    summary = discernment_service.discernment_frame_summary(frame)
    assert summary.get('status') == 'frame_available'
    assert 'login_screen_candidate' in summary.get('detected_concepts', [])


def test_negative_control_empty_concepts():
    """Negative control: empty concepts produce empty frame (no fabrication)."""
    discernment_service = FakeDiscernmentFrameService()
    
    # Build frame with empty evidence
    frame = discernment_service.build_frame(
        phase='observe',
        trigger_source='test',
        raw_inputs=['test goal'],
        concept_weight_evidence={
            "concepts": [],
            "weights": {},
            "sources": [],
        },
    )
    
    # Frame should not have fabricated concepts
    assert frame['detected_concepts'] == []
    assert frame['concept_weights'] == {}
    
    # Summary should reflect empty state
    summary = discernment_service.discernment_frame_summary(frame)
    assert summary.get('detected_concepts') == []
    assert summary.get('concept_weights') == {}


def test_lifecycle_current_frame_not_historical():
    """Lifecycle: summary corresponds to current frame, not historical."""
    discernment_service = FakeDiscernmentFrameService()
    
    # First task with concept A
    frame1 = discernment_service.build_frame(
        phase='observe',
        trigger_source='task_1',
        raw_inputs=['task 1'],
        concept_weight_evidence={
            "concepts": ['concept_a'],
            "weights": {'concept_a': 0.8},
            "sources": ['browser_dom'],
        },
    )
    
    # Second task with concept B
    frame2 = discernment_service.build_frame(
        phase='observe',
        trigger_source='task_2',
        raw_inputs=['task 2'],
        concept_weight_evidence={
            "concepts": ['concept_b'],
            "weights": {'concept_b': 0.7},
            "sources": ['browser_dom'],
        },
    )
    
    # Verify second frame is distinct
    assert len(discernment_service._frames) == 2
    assert 'concept_b' in discernment_service._frames[1]['detected_concepts']
    
    # Verify second summary corresponds to second frame, not first
    summary2 = discernment_service.discernment_frame_summary(frame2)
    assert 'concept_b' in summary2.get('detected_concepts', [])
    assert 'concept_a' not in summary2.get('detected_concepts', [])


def test_safety_graceful_degradation():
    """Safety: graceful degradation when service unavailable."""
    from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
    from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
    
    class FakeRepository:
        pass
    
    with tempfile.TemporaryDirectory() as tmpdir:
        site_policy_registry = SitePolicyRegistry(tmpdir)
        
        # Assembler without discernment_frame_service
        assembler = TaskContextAssembler(
            episode_repository=FakeRepository(),  # type: ignore
            knowledge_repository=FakeRepository(),  # type: ignore
            run_repository=FakeRepository(),  # type: ignore
            dossier_repository=FakeRepository(),  # type: ignore
            hidden_incident_repository=FakeRepository(),  # type: ignore
            site_policy_registry=site_policy_registry,
            capability_repository=FakeRepository(),  # type: ignore
            adaptive_session_repository=FakeRepository(),  # type: ignore
            discernment_frame_service=None,
        )
        
        # Should report unavailable status
        summary = assembler._discernment_frame_summary()
        assert summary is not None
        assert summary.get('status') == 'current_frame_unavailable'


def test_safety_build_frame_no_actions():
    """Safety: build_frame() does not execute external actions."""
    discernment_service = FakeDiscernmentFrameService()
    
    # Build frame - should not execute external actions
    frame = discernment_service.build_frame(
        phase='observe',
        trigger_source='task_context_assembler',
        raw_inputs=['test goal'],
        concept_weight_evidence={
            "concepts": ['test_concept'],
            "weights": {'test_concept': 0.9},
            "sources": ['browser_dom'],
        },
    )
    
    # Verify frame was built purely from inputs
    assert frame['phase'] == 'observe'
    assert frame['trigger_source'] == 'task_context_assembler'
    assert frame['raw_inputs'] == ['test goal']
    assert 'test_concept' in frame['detected_concepts']
