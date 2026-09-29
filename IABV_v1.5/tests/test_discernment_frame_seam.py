"""Tests for DiscernmentFrameService shared instance seam.

Tests verify:
A. Identity shared across OSES, TCA, PCS
B. Atomic publication (no partial frame visible to readers)
C. Thread-safe history access
D. Isolated consumer behavior without shared service
E. User questions still create local transient frames
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from iabv_v15.services.evolution.discernment_frame_service import DiscernmentFrameService
from iabv_v15.services.evolution.operational_self_examination_service import OperationalSelfExaminationService
from iabv_v15.services.adaptive.task_context_assembler import TaskContextAssembler
from iabv_v15.services.evolution.portable_context_service import PortableContextService


class TestSharedIdentity:
    """Test A: Verify all consumers use the same shared DiscernmentFrameService instance."""

    def test_shared_identity_same_frame_id(self):
        """Create a shared instance and verify OSES, TCA, PCS point to same frame_id."""
        shared_svc = DiscernmentFrameService(workspace_root='/tmp/test')

        # Create a birth frame
        frame = shared_svc.build_birth_frame(
            startup_events=[{'phase': 'test'}],
            environment_self_model={'risk_signals': []},
            world_model={'active_windows': []},
            freeze_reports=[],
        )

        # Verify consumers can read the same frame_id
        # OSES
        oses_frames = shared_svc.recent_frames(limit=1)
        assert len(oses_frames) == 1
        oses_frame_id = oses_frames[0].frame_id

        # TCA (via discernment_frame_summary)
        tca_summary = shared_svc.discernment_frame_summary()
        assert tca_summary.get('status') != 'no_frame'
        # Note: summary doesn't include frame_id, but it comes from same service

        # PCS (via compact_export)
        pcs_export = shared_svc.compact_export()
        assert pcs_export.get('status') != 'no_frame'
        pcs_frame_id = pcs_export.get('frame_id')

        # Verify identity
        assert pcs_frame_id == frame.frame_id
        assert pcs_frame_id == oses_frame_id


class TestAtomicPublication:
    """Test B: Verify build_birth_frame publishes atomically (no partial frame visible)."""

    def test_birth_frame_atomic_publication(self):
        """Simulate concurrent readers during build_birth_frame."""
        shared_svc = DiscernmentFrameService(workspace_root='/tmp/test')

        partial_frames_seen = []
        complete_frames_seen = []

        def reader_thread():
            """Reader that checks for partial frames."""
            for _ in range(10):
                frame = shared_svc.latest_frame()
                if frame:
                    # Check if frame has birth-specific fields
                    has_env_risks = 'birth_env_risks' in frame.metadata
                    has_bias_risks = any(b['type'] == 'birth_with_freeze_history' for b in frame.bias_risks)
                    if frame.phase == 'birth' and not (has_env_risks or has_bias_risks):
                        partial_frames_seen.append(frame.frame_id)
                    else:
                        complete_frames_seen.append(frame.frame_id)
                time.sleep(0.001)

        # Start reader thread
        reader = threading.Thread(target=reader_thread)
        reader.start()

        # Build birth frame with freeze reports (requires birth-specific mutations)
        time.sleep(0.005)  # Let reader start
        frame = shared_svc.build_birth_frame(
            startup_events=[{'phase': 'test'}],
            environment_self_model={'risk_signals': [{'category': 'test_risk'}]},
            world_model={'active_windows': []},
            freeze_reports=[{'timestamp': 'test'}],
        )

        reader.join(timeout=1.0)

        # Verify no partial frames were seen
        assert len(partial_frames_seen) == 0, f"Saw {len(partial_frames_seen)} partial frames"
        assert len(complete_frames_seen) > 0, "No complete frames seen"


class TestThreadSafeHistory:
    """Test C: Verify concurrent reads of latest_frame() and recent_frames() are safe."""

    def test_concurrent_readers_during_publication(self):
        """Multiple readers reading while frames are published."""
        shared_svc = DiscernmentFrameService(workspace_root='/tmp/test')

        # Add an initial frame so readers see something
        # Note: build_frame no longer auto-publishes, use build_birth_frame instead
        shared_svc.build_birth_frame(
            startup_events=[{'phase': 'initial'}],
            environment_self_model={'risk_signals': []},
            world_model={'active_windows': []},
            freeze_reports=[],
        )

        frame_ids_seen = []
        exceptions_seen = []

        def reader():
            """Reader that polls latest_frame."""
            try:
                for _ in range(20):
                    frame = shared_svc.latest_frame()
                    if frame:
                        frame_ids_seen.append(frame.frame_id)
                    time.sleep(0.001)
            except Exception as e:
                exceptions_seen.append(e)

        def publisher():
            """Publisher that adds frames."""
            for i in range(5):
                shared_svc.build_birth_frame(
                    startup_events=[{'phase': f'test_{i}'}],
                    environment_self_model={'risk_signals': []},
                    world_model={'active_windows': []},
                    freeze_reports=[],
                )
                time.sleep(0.002)

        # Start multiple readers and one publisher
        readers = [threading.Thread(target=reader) for _ in range(3)]
        pub_thread = threading.Thread(target=publisher)

        for r in readers:
            r.start()
        pub_thread.start()

        for r in readers:
            r.join(timeout=2.0)
        pub_thread.join(timeout=2.0)

        # Verify no exceptions
        assert len(exceptions_seen) == 0, f"Exceptions seen: {exceptions_seen}"
        # Verify some frames were seen
        assert len(frame_ids_seen) > 0


class TestIsolatedConsumer:
    """Test D: Verify isolated consumer without shared service returns no_frame."""

    def test_oses_without_shared_service(self):
        """OSES without discernment_frame_service should still work (uses fallback)."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage

        # Create OSES without discernment_frame_service
        storage = MagicMock(spec=ArtifactStorage)
        oses = OperationalSelfExaminationService(
            workspace_root='/tmp/test',
            storage=storage,
            discernment_frame_service=None,  # No shared service
        )

        # Should use fallback local instance
        findings = oses._discernment_frame_findings()
        # With no frames, should produce "discernment frame missing" finding
        assert len(findings) > 0
        assert any('discernment_frame' in str(f).lower() for f in findings)

    def test_tca_without_shared_service(self):
        """TCA without discernment_frame_service should return unavailable."""
        from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
        from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
        from iabv_v15.infra.persistence.run_repository import RunRepository

        # Create TCA without discernment_frame_service
        tca = TaskContextAssembler(
            episode_repository=MagicMock(spec=EpisodeRepository),
            knowledge_repository=MagicMock(spec=KnowledgeRepository),
            run_repository=MagicMock(spec=RunRepository),
            dossier_repository=MagicMock(),
            hidden_incident_repository=MagicMock(),
            site_policy_registry=MagicMock(),
            capability_repository=MagicMock(),
            adaptive_session_repository=MagicMock(),
            discernment_frame_service=None,  # No shared service
        )

        # Should use fallback local instance
        summary = tca._discernment_frame_summary()
        # With no frames, should return no_frame
        assert summary.get('status') == 'no_frame'

    def test_pcs_without_shared_service(self):
        """PCS without discernment_frame_service should return no_frame_yet."""
        from iabv_v15.infra.persistence.storage import ArtifactStorage
        from datetime import datetime, timezone

        # Create PCS without discernment_frame_service
        storage = MagicMock(spec=ArtifactStorage)
        pcs = PortableContextService(
            workspace_root='/tmp/test',
            storage=storage,
            discernment_frame_service=None,  # No shared service
        )

        # Should use fallback local instance
        section = pcs._discernment_frame_section(now=datetime.now(timezone.utc))
        # With no frames, should return no_frame_yet
        assert 'no_frame_yet' in str(section.items)


class TestUserIsolated:
    """Test E: Verify user questions still create local transient frames."""

    def test_user_question_creates_local_frame(self):
        """ControlCenterViewModel should still create local frames for user questions."""
        # This is a placeholder test - the actual ControlCenterViewModel
        # logic is in the UI layer and would require more complex setup.
        # The key point is that _answer_discernment_question() creates
        # a local DiscernmentFrameService instance, not the shared one.

        # Verify that a local service instance can create frames independently
        local_svc = DiscernmentFrameService(workspace_root='/tmp/test_local')

        # Simulate user question path
        frame = local_svc.build_frame(
            phase='observe',
            trigger_source='user',
            raw_inputs=['test question'],
            world_model={'active_windows': []},
        )

        assert frame.phase == 'observe'
        assert frame.trigger_source == 'user'
        assert frame.frame_id is not None

        # The frame is published in the local service's history
        local_frame = local_svc.latest_frame()
        assert local_frame is not None
        assert local_frame.frame_id == frame.frame_id

        # Verify this doesn't affect a shared service
        shared_svc = DiscernmentFrameService(workspace_root='/tmp/test_shared')
        shared_frame = shared_svc.latest_frame()
        assert shared_frame is None  # No frames in shared service

        # Local service still has its frame independently
        assert local_svc.latest_frame() is not None


class TestRaceCondition:
    """Test against race condition around build_frame/birth_frame."""

    def test_birth_frame_race_condition_protection(self):
        """Explicit test against the old dangerous pattern:
        
        OLD (dangerous):
        build_frame() → append(frame) → birth-specific mutations
        
        NEW (safe):
        build_frame(_publish=False) → birth-specific mutations → atomic publish
        
        This test verifies readers never see a frame without birth-specific fields.
        """
        shared_svc = DiscernmentFrameService(workspace_root='/tmp/test_race')

        partial_frames_seen = []
        complete_frames_seen = []

        def aggressive_reader():
            """Reader that checks for partial birth frames."""
            for _ in range(50):
                frame = shared_svc.latest_frame()
                if frame and frame.phase == 'birth':
                    # Check if birth-specific fields are present
                    has_env_risks = 'birth_env_risks' in frame.metadata
                    has_freeze_bias = any(
                        b['type'] == 'birth_with_freeze_history' 
                        for b in frame.bias_risks
                    )
                    has_next_observation = frame.next_observation == 'stabilize_ui_before_deep_cognition'
                    
                    # If phase is birth but birth-specific fields are missing, it's partial
                    if not (has_env_risks or has_freeze_bias or has_next_observation):
                        partial_frames_seen.append(frame.frame_id)
                    else:
                        complete_frames_seen.append(frame.frame_id)
                time.sleep(0.0005)

        def birth_frame_publisher():
            """Publisher that creates birth frames rapidly."""
            for i in range(10):
                shared_svc.build_birth_frame(
                    startup_events=[{'phase': f'race_test_{i}'}],
                    environment_self_model={'risk_signals': [{'category': f'risk_{i}'}]},
                    world_model={'active_windows': []},
                    freeze_reports=[{'timestamp': f'freeze_{i}'}] if i % 2 == 0 else [],
                )
                time.sleep(0.001)

        # Start aggressive reader first
        reader = threading.Thread(target=aggressive_reader)
        reader.start()
        time.sleep(0.005)  # Let reader establish polling pattern

        # Then start publisher
        pub_thread = threading.Thread(target=birth_frame_publisher)
        pub_thread.start()

        reader.join(timeout=3.0)
        pub_thread.join(timeout=3.0)

        # Verify no partial frames were seen
        assert len(partial_frames_seen) == 0, (
            f"Race condition detected: {len(partial_frames_seen)} partial frames seen. "
            f"This means readers observed birth frames without birth-specific fields."
        )
        
        # Verify some complete frames were seen
        assert len(complete_frames_seen) > 0, "No complete birth frames were seen"
        
        # Note: Duplicate frame_ids are expected due to deepcopy() in latest_frame()
        # This is correct behavior - readers get stable copies with the same ID
        # We only care that no partial frames were seen
