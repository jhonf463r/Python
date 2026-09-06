"""Tests for canonical replan provenance in AdaptiveTaskOrchestrator."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from iabv_v15.domain.models import (
    AdaptiveSession,
    AdaptiveSessionStatus,
    InferenceRequest,
    SessionContinuationType,
    TaskIntent,
    TaskContext,
    StrategyPack,
    ExecutionPlaybook,
    CapabilityReadiness,
    StrategyCandidate,
    RunRecord,
    InferenceResult,
    RoleRoute,
    RunStatus,
    ExperimentDomain,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository


class TestCanonicalReplanProvenance:
    """Test canonical provenance as single source of truth with legacy mirror."""

    def test_external_request_provenance(self):
        """External requests should have EXTERNAL_REQUEST continuation type and no parent."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
        )

        # Verify canonical provenance defaults
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_auto_replan_provenance(self):
        """Auto-replan sessions should have AUTO_REPLAN continuation type and parent_session_id."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create original session with canonical provenance
        original_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"replan_count": 0, "governance": {"should_replan": True}},
        )
        session_repo.get.return_value = original_session

        # Mock _request_from_session
        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return a session with canonical provenance
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=original_session.session_id,
            replan_depth=1,
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(original_session.session_id)

        # Verify canonical provenance
        assert result is not None
        assert result.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert result.parent_session_id == original_session.session_id
        assert result.replan_depth == 1

    def test_canonical_guard_uses_typed_fields(self):
        """_should_auto_replan must use canonical fields, not metadata."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session with typed depth=2 but legacy metadata replan_count=0
        # Canonical source should block replan, not legacy metadata
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Canonical: at limit
            metadata={"replan_count": 0, "governance": {"should_replan": True}},  # Legacy: would allow
        )
        session_repo.get.return_value = session

        # _should_auto_replan must follow canonical field
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is False, "Canonical replan_depth=2 should block, ignoring legacy replan_count=0"

    def test_mirror_synchronization(self):
        """Legacy metadata mirror must stay synchronized with canonical fields."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session with canonical provenance
        original_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"governance": {"should_replan": True}},
        )
        session_repo.get.return_value = original_session

        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return session with canonical provenance
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=original_session.session_id,
            replan_depth=1,
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(original_session.session_id)

        # Verify mirror synchronization
        assert result.replan_depth == result.metadata["replan_count"]
        assert result.parent_session_id == result.metadata["replanned_from_session_id"]

    def test_explicit_external_with_stale_legacy_metadata(self):
        """REGRESSION TEST: Explicit EXTERNAL_REQUEST with stale legacy metadata must remain EXTERNAL.
        
        This is the critical bug fix: when typed provenance is explicitly set to EXTERNAL_REQUEST/None/0,
        even if legacy metadata contains stale parent/count values, the explicit typed values must prevail.
        """
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,  # Explicit typed
            parent_session_id=None,  # Explicit typed
            replan_depth=0,  # Explicit typed
            metadata={
                "replanned_from_session_id": "STALE-PARENT",
                "replan_count": 2,
            },
        )

        # Explicit typed provenance must NOT be overwritten by stale legacy metadata
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_historical_migration(self):
        """Historical sessions with legacy metadata but NO typed provenance must migrate."""
        # Create a session with legacy metadata but WITHOUT typed provenance fields
        # This simulates a historical session loaded from the database
        historical_data = {
            "user_goal": "test goal",
            "intent": {
                "intent_key": "test.intent",
                "title": "Test Intent",
                "detected_role": "training",
                "confidence": 1.0,
            },
            "context": {},
            "metadata": {
                "replanned_from_session_id": "legacy-parent-id",
                "replan_count": 1,
            },
            # NOTE: continuation_type, parent_session_id, replan_depth are NOT in the input
        }

        historical_session = AdaptiveSession(**historical_data)

        # Model validator should migrate legacy metadata to typed fields
        assert historical_session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert historical_session.parent_session_id == "legacy-parent-id"
        assert historical_session.replan_depth == 1

    def test_typed_auto_replan_wins_over_legacy(self):
        """Explicit typed AUTO_REPLAN must prevail over conflicting legacy metadata."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,  # Explicit typed
            parent_session_id="explicit-parent",  # Explicit typed
            replan_depth=1,  # Explicit typed
            metadata={
                "replanned_from_session_id": "legacy-parent-id",
                "replan_count": 0,
            },
        )

        # Typed fields should NOT be overwritten by legacy metadata
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "explicit-parent"
        assert session.replan_depth == 1

    def test_typed_external_wins_over_legacy(self):
        """Explicit typed EXTERNAL_REQUEST must prevail over conflicting legacy metadata."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,  # Explicit typed
            parent_session_id=None,  # Explicit typed
            replan_depth=0,  # Explicit typed
            metadata={
                "replanned_from_session_id": "STALE-PARENT",
                "replan_count": 2,
            },
        )

        # Explicit EXTERNAL_REQUEST must NOT be converted to AUTO_REPLAN by stale legacy metadata
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_default_without_legacy_metadata(self):
        """Default EXTERNAL_REQUEST without legacy metadata must remain default."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            metadata={},  # No legacy metadata
        )

        # Should remain at default EXTERNAL_REQUEST
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_bounded_replan_with_canonical_fields(self):
        """Bounded replan must use canonical fields, not metadata."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session at replan limit using canonical fields
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Canonical: at limit
            metadata={"governance": {"should_replan": True}},
        )
        session_repo.get.return_value = session

        # _should_auto_replan must block based on canonical replan_depth
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is False, "Canonical replan_depth=2 should block replan"

    def test_persistence_round_trip(self):
        """Canonical provenance must survive JSON serialization/deserialization round trip."""
        import json
        
        # Test AUTO_REPLAN session
        auto_replan_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=1,
        )

        # Serialize to JSON
        auto_json = auto_replan_session.model_dump(mode="json")
        auto_json_str = json.dumps(auto_json)
        
        # Deserialize
        auto_loaded_dict = json.loads(auto_json_str)
        auto_loaded = AdaptiveSession(**auto_loaded_dict)

        # Verify canonical provenance survived
        assert auto_loaded.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert auto_loaded.parent_session_id == "parent-id"
        assert auto_loaded.replan_depth == 1

        # Test EXTERNAL_REQUEST with stale legacy metadata (critical regression test)
        external_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={
                "replanned_from_session_id": "STALE-PARENT",
                "replan_count": 2,
            },
        )

        # Serialize to JSON
        external_json = external_session.model_dump(mode="json")
        external_json_str = json.dumps(external_json)
        
        # Deserialize
        external_loaded_dict = json.loads(external_json_str)
        external_loaded = AdaptiveSession(**external_loaded_dict)

        # Verify EXTERNAL_REQUEST with stale legacy remains EXTERNAL
        assert external_loaded.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert external_loaded.parent_session_id is None
        assert external_loaded.replan_depth == 0

    def test_guard_uses_only_typed_provenance_with_stale_legacy(self):
        """_should_auto_replan must use only typed provenance, ignoring stale legacy metadata."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Create session with typed EXTERNAL/None/0 but stale legacy metadata
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,  # Typed: allows replan
            metadata={
                "replanned_from_session_id": "STALE-PARENT",  # Legacy: would block
                "replan_count": 2,  # Legacy: would block
                "governance": {"should_replan": True},
            },
        )
        session_repo.get.return_value = session

        # Guard must use only typed provenance, ignoring legacy metadata
        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is True, "Typed depth=0 should allow replan, ignoring legacy count=2"

    def test_guard_depth_zero_vs_legacy_count_two(self):
        """Guard decision must depend on typed depth=0, not legacy count=2."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # typed depth=0, legacy count=2
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"replan_count": 2, "governance": {"should_replan": True}},
        )
        session_repo.get.return_value = session

        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is True, "Typed depth=0 must allow replan, ignoring legacy count=2"

    def test_guard_parent_none_vs_legacy_parent(self):
        """Guard decision must depend on typed parent=None, not legacy parent."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # typed parent=None, legacy parent=STALE
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={
                "replanned_from_session_id": "STALE-PARENT",
                "governance": {"should_replan": True},
            },
        )
        session_repo.get.return_value = session

        should_replan = orchestrator._should_auto_replan(session)
        assert should_replan is True, "Typed parent=None must allow replan, ignoring legacy parent"

    def test_replan_session_uses_only_typed_depth(self):
        """replan_session must use only typed replan_depth, not legacy count."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # typed depth=2, legacy count=0
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Typed: at limit
            metadata={"replan_count": 0, "governance": {"should_replan": True}},  # Legacy: would allow
        )
        session_repo.get.return_value = session

        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return a session
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=session.session_id,
            replan_depth=3,  # Should be 2 + 1 from typed depth, not 0 + 1 from legacy
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(session.session_id)

        # Verify replan_session used typed depth=2, not legacy count=0
        assert result is not None
        assert result.replan_depth == 3, "Should use typed depth=2 + 1, not legacy count=0 + 1"

    def test_mirror_synchronization_in_replan_session(self):
        """Legacy mirror must be synchronized with canonical typed state after replan."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        role_router = MagicMock()
        intent_service = MagicMock()
        context_assembler = MagicMock()
        capability_service = MagicMock()
        strategy_pack_registry = MagicMock()
        planner_service = MagicMock()
        approval_gate_service = MagicMock()
        execution_playbook_service = MagicMock()
        task_outcome_recorder = MagicMock()

        orchestrator = AdaptiveTaskOrchestrator(
            role_router=role_router,
            adaptive_session_repository=session_repo,
            intent_service=intent_service,
            context_assembler=context_assembler,
            capability_service=capability_service,
            strategy_pack_registry=strategy_pack_registry,
            planner_service=planner_service,
            approval_gate_service=approval_gate_service,
            execution_playbook_service=execution_playbook_service,
            task_outcome_recorder=task_outcome_recorder,
        )

        # Original session: typed depth=2, legacy count=0 (divergent)
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.FAILED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=2,  # Typed canonical
            metadata={"replan_count": 0, "governance": {"should_replan": True}},  # Legacy divergent
        )
        session_repo.get.return_value = session

        orchestrator._request_from_session = MagicMock(
            return_value=InferenceRequest(user_goal="test goal", metadata={})
        )

        # Mock handle_request to return a session
        replanned_session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            chosen_pack_id="test_pack",
            chosen_pack_title="Test Pack",
            status=AdaptiveSessionStatus.PLANNED,
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id=session.session_id,
            replan_depth=3,  # Canonical: 2 + 1
        )
        orchestrator.handle_request = MagicMock(return_value=(MagicMock(), MagicMock(), replanned_session))

        task_outcome_recorder.record.return_value = replanned_session

        # Execute replan
        result = orchestrator.replan_session(session.session_id)

        # Verify mirror is synchronized with canonical typed state
        assert result is not None
        assert result.replan_depth == 3, "Canonical typed depth should be 3"
        assert result.metadata.get('replan_count') == 3, "Legacy mirror should be 3 (synchronized), not 1 (from old legacy)"

    def test_partial_typed_provenance_completion_from_legacy(self):
        """Partial typed provenance should be completed from legacy without overwriting explicit values."""
        # Case: only continuation_type provided, parent and depth from legacy
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,  # Explicit typed
            # parent_session_id and replan_depth absent - should migrate from legacy
            metadata={
                "replanned_from_session_id": "legacy-parent",
                "replan_count": 2,
            },
        )

        # Verify: explicit continuation_type preserved, parent and depth migrated
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "legacy-parent"
        assert session.replan_depth == 2

    def test_partial_typed_parent_only(self):
        """Only parent_session_id provided, type and depth from legacy."""
        # When explicit parent differs from legacy parent, we should reject cross-lineage contamination
        # because we would be mixing lineage from different sources
        import pytest
        
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                parent_session_id="explicit-parent",  # Explicit typed
                # continuation_type and replan_depth absent - would migrate from legacy
                metadata={
                    "replanned_from_session_id": "legacy-parent",  # Different lineage
                    "replan_count": 2,
                },
            )

    def test_partial_typed_depth_only(self):
        """Only replan_depth provided, type and parent from legacy - requires matching lineage."""
        # When only depth is typed, we need legacy to match the depth to ensure same lineage
        # If legacy count differs, we reject to avoid cross-lineage contamination
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            replan_depth=2,  # Explicit typed matching legacy count
            # continuation_type and parent_session_id absent - should migrate from legacy
            metadata={
                "replanned_from_session_id": "legacy-parent",
                "replan_count": 2,  # Matches typed depth
            },
        )

        # Verify: explicit depth preserved, type and parent migrated (lineage compatible)
        assert session.replan_depth == 2
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "legacy-parent"

    def test_case_f_default_parent_with_legacy_parent_migrates(self):
        """Case F: parent=None (default) with legacy parent migrates to valid AUTO_REPLAN."""
        # Since None is the default, migration occurs and creates valid AUTO_REPLAN
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            # parent_session_id=None (default, cannot distinguish from explicit)
            metadata={
                "replanned_from_session_id": "legacy-parent",
                "replan_count": 2,
            },
        )
        # Migration occurred: parent from legacy, depth from legacy
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "legacy-parent"
        assert session.replan_depth == 2

    def test_case_g_default_depth_with_legacy_count_migrates(self):
        """Case G: depth=0 (default) with legacy count migrates to valid AUTO_REPLAN."""
        # Since 0 is the default, migration occurs and creates valid AUTO_REPLAN
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            # replan_depth=0 (default, cannot distinguish from explicit)
            metadata={
                "replanned_from_session_id": "legacy-parent",
                "replan_count": 2,
            },
        )
        # Migration occurred: parent from legacy, depth from legacy
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "legacy-parent"
        assert session.replan_depth == 2

    def test_case_e2_cross_lineage_contamination_rejected(self):
        """Case E2: explicit parent conflicts with legacy parent should be rejected."""
        import pytest
        
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                parent_session_id="typed-parent-A",  # Explicit parent A
                metadata={
                    "replanned_from_session_id": "legacy-parent-B",  # Legacy parent B
                    "replan_count": 2,
                },
            )

    def test_invariant_external_request_coherence(self):
        """EXTERNAL_REQUEST must have parent=None and depth=0."""
        import pytest
        
        # EXTERNAL_REQUEST with parent should fail
        with pytest.raises(ValueError, match="EXTERNAL_REQUEST requires parent_session_id=None"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
                parent_session_id="some-parent",
                replan_depth=0,
            )
        
        # EXTERNAL_REQUEST with depth>0 should fail
        with pytest.raises(ValueError, match="EXTERNAL_REQUEST requires replan_depth=0"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
                parent_session_id=None,
                replan_depth=1,
            )

    def test_invariant_auto_replan_coherence(self):
        """AUTO_REPLAN must have parent!=None and depth>=1."""
        import pytest
        
        # AUTO_REPLAN with parent=None should fail
        with pytest.raises(ValueError, match="AUTO_REPLAN requires parent_session_id"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id=None,
                replan_depth=1,
            )
        
        # AUTO_REPLAN with depth=0 should fail
        with pytest.raises(ValueError, match="AUTO_REPLAN requires replan_depth>=1"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id="some-parent",
                replan_depth=0,
            )

    def test_case_1_type_parent_matching_legacy(self):
        """Case 1: type+parent typed with matching legacy - accept and complete depth."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="A",
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 2,
            },
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "A"
        assert session.replan_depth == 2  # Completed from legacy

    def test_case_2_type_parent_conflicting_legacy(self):
        """Case 2: type+parent typed with conflicting legacy - reject."""
        import pytest
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                parent_session_id="A",
                metadata={
                    "replanned_from_session_id": "B",
                    "replan_count": 2,
                },
            )

    def test_case_3_type_depth_matching_legacy(self):
        """Case 3: type+depth typed with matching legacy - accept and complete parent."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            replan_depth=2,
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 2,
            },
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "A"  # Completed from legacy
        assert session.replan_depth == 2

    def test_case_4_type_depth_conflicting_legacy_count(self):
        """Case 4: type+depth typed with conflicting legacy count - reject."""
        import pytest
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                continuation_type=SessionContinuationType.AUTO_REPLAN,
                replan_depth=2,
                metadata={
                    "replanned_from_session_id": "A",
                    "replan_count": 3,
                },
            )

    def test_case_5_parent_depth_matching_legacy(self):
        """Case 5: parent+depth typed with matching legacy - accept and complete type."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            parent_session_id="A",
            replan_depth=2,
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 2,
            },
        )
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN  # Completed from legacy
        assert session.parent_session_id == "A"
        assert session.replan_depth == 2

    def test_case_6_parent_depth_conflicting_legacy(self):
        """Case 6: parent+depth typed with conflicting legacy - reject."""
        import pytest
        with pytest.raises(ValueError, match="Cross-lineage contamination"):
            AdaptiveSession(
                user_goal="test goal",
                intent=TaskIntent(
                    intent_key="test.intent",
                    title="Test Intent",
                    detected_role="training",
                    confidence=1.0,
                ),
                context=TaskContext(),
                parent_session_id="A",
                replan_depth=2,
                metadata={
                    "replanned_from_session_id": "B",
                    "replan_count": 2,
                },
            )

    def test_case_7_external_with_stale_legacy(self):
        """Case 7: EXTERNAL_REQUEST with stale legacy - remain EXTERNAL."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 2,
            },
        )
        assert session.continuation_type == SessionContinuationType.EXTERNAL_REQUEST
        assert session.parent_session_id is None
        assert session.replan_depth == 0

    def test_case_8_full_typed_conflicting_legacy(self):
        """Case 8: full typed with conflicting legacy - remain as typed (complete override)."""
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="A",
            replan_depth=1,
            metadata={
                "replanned_from_session_id": "B",
                "replan_count": 0,
            },
        )
        # Complete override: legacy is ignored
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "A"
        assert session.replan_depth == 1

    def test_real_decision_full_typed_auto_replan(self):
        """Real decision: full typed AUTO_REPLAN session governs _should_auto_replan."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )
        
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="parent-id",
            replan_depth=1,
            metadata={"governance": {"should_replan": True}},
        )
        
        # Should allow replan (depth=1 < 2)
        result = orchestrator._should_auto_replan(session)
        assert result is True

    def test_real_decision_full_typed_external_request(self):
        """Real decision: full typed EXTERNAL_REQUEST session governs _should_auto_replan."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )
        
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.EXTERNAL_REQUEST,
            parent_session_id=None,
            replan_depth=0,
            metadata={"governance": {"should_replan": True}},
        )
        
        # Should allow replan (depth=0 < 2)
        result = orchestrator._should_auto_replan(session)
        assert result is True

    def test_real_decision_historical_legacy_migrated(self):
        """Real decision: historical legacy session migrates and governs _should_auto_replan."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )
        
        # Historical session with only legacy metadata
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            metadata={
                "replanned_from_session_id": "parent-id",
                "replan_count": 1,
                "governance": {"should_replan": True},
            },
        )
        
        # Should migrate to AUTO_REPLAN and allow replan (depth=1 < 2)
        assert session.continuation_type == SessionContinuationType.AUTO_REPLAN
        assert session.parent_session_id == "parent-id"
        assert session.replan_depth == 1
        result = orchestrator._should_auto_replan(session)
        assert result is True

    def test_real_decision_partial_typed_matching_legacy(self):
        """Real decision: partial typed with matching legacy completes and governs decision."""
        session_repo = MagicMock(spec=AdaptiveSessionRepository)
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=MagicMock(),
            adaptive_session_repository=session_repo,
            intent_service=MagicMock(),
            context_assembler=MagicMock(),
            capability_service=MagicMock(),
            strategy_pack_registry=MagicMock(),
            planner_service=MagicMock(),
            approval_gate_service=MagicMock(),
            execution_playbook_service=MagicMock(),
            task_outcome_recorder=MagicMock(),
        )
        
        # Partial typed: type+parent, depth from matching legacy
        session = AdaptiveSession(
            user_goal="test goal",
            intent=TaskIntent(
                intent_key="test.intent",
                title="Test Intent",
                detected_role="training",
                confidence=1.0,
            ),
            context=TaskContext(),
            continuation_type=SessionContinuationType.AUTO_REPLAN,
            parent_session_id="A",
            metadata={
                "replanned_from_session_id": "A",
                "replan_count": 1,
                "governance": {"should_replan": True},
            },
        )
        
        # Should complete depth=1 and allow replan
        assert session.replan_depth == 1
        result = orchestrator._should_auto_replan(session)
        assert result is True
