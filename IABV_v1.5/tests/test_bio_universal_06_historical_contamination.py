"""Tests for BIO-UNIVERSAL-06 — Fix Current-Frame Historical Contamination.

Tests focus on:
- When current frame construction fails, current task receives explicit unavailable status
- Historical frame is NOT injected into current task metadata
- Positive path: successful current frame still propagates correctly
- Identity test: current frame vs historical frame concepts are distinct
"""
from __future__ import annotations

import tempfile
from typing import Any

import pytest

from iabv_v15.domain.models import (
    InferenceRequest,
    TaskIntent,
    VisualSignalSnapshot,
)


class SpyDiscernmentFrameService:
    """Spy DiscernmentFrameService that can force build_frame() to raise."""
    
    def __init__(self) -> None:
        self._frames: list[Any] = []
        self._should_raise_on_build = False
        self._build_count = 0
    
    def build_frame(self, **kwargs) -> Any:
        """Build a frame or raise if configured to fail."""
        self._build_count += 1
        
        if self._should_raise_on_build:
            raise RuntimeError("Simulated build_frame() failure")
        
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
        """Return summary of provided frame only. Do NOT fall back to latest."""
        if frame is not None:
            return {
                'status': 'frame_available',
                'detected_concepts': frame.get('detected_concepts', []),
                'concept_weights': frame.get('concept_weights', {}),
                'grounding_status': frame.get('grounding_status', 'unknown'),
            }
        
        # Explicit: if no frame provided, return unavailable
        # This matches the fixed semantics in TaskContextAssembler
        return {'status': 'no_frame'}
    
    def should_raise_on_build(self, should_raise: bool) -> None:
        """Configure whether build_frame() should raise."""
        self._should_raise_on_build = should_raise
    
    def latest_frame(self) -> Any | None:
        """Return latest historical frame (for test setup only)."""
        if self._frames:
            return self._frames[-1]
        return None


def test_negative_historical_contamination_blocked():
    """Negative test: historical frame NOT injected when current frame construction fails."""
    from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
    from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
    
    class FakeRepository:
        pass
    
    with tempfile.TemporaryDirectory() as tmpdir:
        site_policy_registry = SitePolicyRegistry(tmpdir)
        discernment_service = SpyDiscernmentFrameService()
        
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
        
        # TASK A: Create historical frame with unique concept
        discernment_service.build_frame(
            phase='observe',
            trigger_source='task_a',
            raw_inputs=['task a goal'],
            concept_weight_evidence={
                "concepts": ['HISTORICAL_A_concept'],
                "weights": {'HISTORICAL_A_concept': 0.9},
                "sources": ['browser_dom'],
            },
        )
        
        # Verify historical frame exists
        historical_frame = discernment_service.latest_frame()
        assert historical_frame is not None
        assert 'HISTORICAL_A_concept' in historical_frame['detected_concepts']
        
        # TASK B: Force current build_frame() to raise
        discernment_service.should_raise_on_build(True)
        
        # Verify the assembler helper returns explicit unavailable status
        summary = assembler._discernment_frame_summary(None)
        assert summary is not None
        assert summary.get('status') == 'current_frame_unavailable'
        
        # Critical: historical concept must NOT be present
        assert 'HISTORICAL_A_concept' not in summary.get('detected_concepts', [])
        assert summary.get('detected_concepts') is None or len(summary.get('detected_concepts', [])) == 0
        
        # No false grounded state inherited
        assert summary.get('grounding_status') is None or summary.get('grounding_status') != 'grounded'


def test_positive_current_frame_propagates():
    """Positive regression: successful current frame still propagates correctly."""
    from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
    from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
    
    class FakeRepository:
        pass
    
    with tempfile.TemporaryDirectory() as tmpdir:
        site_policy_registry = SitePolicyRegistry(tmpdir)
        discernment_service = SpyDiscernmentFrameService()
        
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
        
        # Create historical frame
        discernment_service.build_frame(
            phase='observe',
            trigger_source='task_a',
            raw_inputs=['task a goal'],
            concept_weight_evidence={
                "concepts": ['HISTORICAL_A_concept'],
                "weights": {'HISTORICAL_A_concept': 0.9},
                "sources": ['browser_dom'],
            },
        )
        
        # Build CURRENT frame with different concept
        current_frame = discernment_service.build_frame(
            phase='observe',
            trigger_source='task_b',
            raw_inputs=['task b goal'],
            concept_weight_evidence={
                "concepts": ['CURRENT_B_concept'],
                "weights": {'CURRENT_B_concept': 0.8},
                "sources": ['browser_dom'],
            },
        )
        
        # Verify current frame summary
        summary = assembler._discernment_frame_summary(current_frame)
        assert summary is not None
        assert summary.get('status') == 'frame_available'
        
        # Current concept must be present
        assert 'CURRENT_B_concept' in summary.get('detected_concepts', [])
        
        # Historical concept must NOT be present
        assert 'HISTORICAL_A_concept' not in summary.get('detected_concepts', [])


def test_identity_current_vs_historical():
    """Identity test: verifies CURRENT FRAME OR EXPLICIT UNAVAILABLE invariant."""
    from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
    from iabv_v15.services.capture.site_policy_registry import SitePolicyRegistry
    
    class FakeRepository:
        pass
    
    with tempfile.TemporaryDirectory() as tmpdir:
        site_policy_registry = SitePolicyRegistry(tmpdir)
        discernment_service = SpyDiscernmentFrameService()
        
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
        
        # Create historical frame
        discernment_service.build_frame(
            phase='observe',
            trigger_source='task_a',
            raw_inputs=['task a goal'],
            concept_weight_evidence={
                "concepts": ['HISTORICAL_A_concept'],
                "weights": {'HISTORICAL_A_concept': 0.9},
                "sources": ['browser_dom'],
            },
        )
        
        # SUCCESS PATH: current frame
        current_frame = discernment_service.build_frame(
            phase='observe',
            trigger_source='task_b',
            raw_inputs=['task b goal'],
            concept_weight_evidence={
                "concepts": ['CURRENT_B_concept'],
                "weights": {'CURRENT_B_concept': 0.8},
                "sources": ['browser_dom'],
            },
        )
        
        summary_success = assembler._discernment_frame_summary(current_frame)
        assert summary_success.get('status') == 'frame_available'
        assert 'CURRENT_B_concept' in summary_success.get('detected_concepts', [])
        assert 'HISTORICAL_A_concept' not in summary_success.get('detected_concepts', [])
        
        # FAILURE PATH: current frame construction fails
        discernment_service.should_raise_on_build(True)
        summary_failure = assembler._discernment_frame_summary(None)
        assert summary_failure.get('status') == 'current_frame_unavailable'
        assert 'CURRENT_B_concept' not in summary_failure.get('detected_concepts', [])
        assert 'HISTORICAL_A_concept' not in summary_failure.get('detected_concepts', [])
        
        # Invariant: CURRENT FRAME OR EXPLICIT UNAVAILABLE, NEVER SILENT HISTORICAL FALLBACK
        assert summary_failure.get('detected_concepts') is None or len(summary_failure.get('detected_concepts', [])) == 0


def test_service_unavailable_graceful_degradation():
    """Safety: graceful degradation when service is None."""
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
        
        # With frame provided but no service
        summary = assembler._discernment_frame_summary({'detected_concepts': ['test']})
        assert summary is not None
        assert summary.get('status') == 'frame_provided_but_service_unavailable'
        
        # Without frame and no service
        summary_none = assembler._discernment_frame_summary(None)
        assert summary_none is not None
        assert summary_none.get('status') == 'current_frame_unavailable'
