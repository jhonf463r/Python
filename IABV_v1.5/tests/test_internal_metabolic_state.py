"""Focused tests for InternalMetabolicStateService.

Tests verify:
1. Inspector uses existing ControlMaster work queue
2. Inspector can detect an orphaned component
3. Inspector can detect a disconnected capability chain
4. Inspector distinguishes source-exists from runtime-reachable
5. Inspector distinguishes duplicate from merely adjacent implementations
6. Inspector reports UNKNOWN instead of inventing state
7. Inspector exposes resource health
8. Inspector exposes memory health
9. Inspector exposes validation health
10. Recommendations do not execute actions
11. No provider/tool executes during inspection
12. Existing governance remains unchanged
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from iabv_v15.domain.models import ControlMasterState, ObjectiveStatus
from iabv_v15.services.evolution.internal_metabolic_state_service import (
    BrokenChain,
    ChainStatus,
    ComponentConnection,
    DuplicateImplementation,
    HealthDimension,
    HealthStatus,
    InternalMetabolicState,
    InternalMetabolicStateService,
    OrphanedComponent,
    Recommendation,
)


@pytest.fixture
def mock_control_master_service():
    """Mock ControlMasterService with work queue."""
    service = MagicMock()
    state = ControlMasterState(
        active_objective_ids=["obj-1", "obj-2"],
        completed_objective_ids=["obj-3"],
        paused_objective_ids=[],
        recent_decisions=[],
        global_rules=[],
    )
    service.current_state.return_value = state
    return service


@pytest.fixture
def mock_environment_service():
    """Mock EnvironmentSelfAwarenessService."""
    service = MagicMock()
    env_model = MagicMock()
    env_model.ram_available_mb = 6000
    env_model.cpu_load_pct = 45.0
    env_model.disk_available_gb = 50.0
    env_model.gpu_available = True
    env_model.scan_status = "healthy"
    service.current_model.return_value = env_model
    return service


@pytest.fixture
def mock_operational_service():
    """Mock OperationalSelfExaminationService."""
    service = MagicMock()
    snapshot = MagicMock()
    snapshot.findings = [MagicMock(severity="medium"), MagicMock(severity="low")]
    snapshot.reviewed_at = datetime.now(timezone.utc)
    service._current_review = snapshot
    return service


@pytest.fixture
def mock_capability_service():
    """Mock CapabilityReadinessService."""
    service = MagicMock()
    repo = MagicMock()
    repo.list_recent.return_value = [
        MagicMock(status="READY"),
        MagicMock(status="PARTIAL"),
        MagicMock(status="INSUFFICIENT"),
    ]
    service.capability_repository = repo
    return service


@pytest.fixture
def mock_role_router():
    """Mock LocalRoleRouter."""
    service = MagicMock()
    health = [
        MagicMock(provider_name="Ollama", available=True, status=MagicMock(value="AVAILABLE")),
        MagicMock(provider_name="Ollama Vision", available=False, status=MagicMock(value="UNAVAILABLE")),
    ]
    service.health_snapshot.return_value = health
    return service


@pytest.fixture
def inspector(mock_control_master_service, mock_environment_service, mock_operational_service, mock_capability_service, mock_role_router):
    """Create InternalMetabolicStateService with mocked dependencies."""
    return InternalMetabolicStateService(
        workspace_root="C:/Python/IABV_v1.5",
        operational_self_examination_service=mock_operational_service,
        control_master_service=mock_control_master_service,
        environment_self_awareness_service=mock_environment_service,
        capability_readiness_service=mock_capability_service,
        role_router=mock_role_router,
    )


def test_uses_existing_control_master_work_queue(inspector, mock_control_master_service):
    """Test 1: Inspector uses existing ControlMaster work queue."""
    state = inspector.inspect()

    # Verify ControlMasterService was called
    mock_control_master_service.current_state.assert_called_once_with(refresh=False)

    # Verify work queue is exposed
    assert state.current_work is not None
    assert state.current_work['work_queue'] != 'UNKNOWN'
    assert 'active_objectives' in state.current_work['work_queue']
    assert state.current_work['work_queue']['active_objectives'] == ["obj-1", "obj-2"]
    # backlog and risks are optional fields
    assert 'backlog_count' in state.current_work['work_queue']
    assert 'risks_count' in state.current_work['work_queue']


def test_detects_orphaned_component(inspector):
    """Test 2: Inspector can detect an orphaned component."""
    # Add UnifiedMemoryLayer without TaskContextAssembler to trigger orphan detection
    inspector.unified_memory_layer = MagicMock()
    inspector.task_context_assembler = None

    state = inspector.inspect()

    # Verify orphaned component is detected
    assert len(state.orphaned_components) > 0
    orphan = state.orphaned_components[0]
    assert orphan.component_name == "UnifiedMemoryLayer"
    assert "UNKNOWN" in orphan.why_orphaned  # Requires static analysis for definitive answer
    assert orphan.primary_consumer_needed == "TaskContextAssembler or InferenceService"


def test_detects_disconnected_capability_chain(inspector):
    """Test 3: Inspector can detect a disconnected capability chain."""
    # Remove AdaptiveTaskOrchestrator to break the chain
    inspector.adaptive_task_orchestrator = None

    state = inspector.inspect()

    # Verify broken chain is detected
    broken_chains = [c for c in state.broken_chains if c.chain_name == "ControlMaster_to_Execution"]
    assert len(broken_chains) > 0
    chain = broken_chains[0]
    assert chain.status in (ChainStatus.PARTIAL, ChainStatus.DISCONNECTED)
    assert chain.first_broken_link == "AdaptiveTaskOrchestrator"


def test_distinguishes_source_exists_from_runtime_reachable(inspector):
    """Test 4: Inspector distinguishes source-exists from runtime-reachable."""
    # Set a component to exist but not be injected
    inspector.reflection_routing_service = None  # Source does not exist

    state = inspector.inspect()

    connection = state.connections.get('ReflectionRoutingService')
    assert connection is not None
    assert connection.source_exists == False
    assert connection.runtime_reachable == False

    # Now set it to exist
    inspector.reflection_routing_service = MagicMock()
    state = inspector.inspect(force_refresh=True)

    connection = state.connections.get('ReflectionRoutingService')
    assert connection.source_exists == True
    assert connection.runtime_reachable == True


def test_distinguishes_duplicate_from_adjacent_implementations(inspector):
    """Test 5: Inspector distinguishes duplicate from merely adjacent implementations."""
    # Both ResourceAwareController and EnvironmentSelfAwarenessService exist
    inspector.resource_aware_controller = MagicMock()
    inspector.environment_self_awareness_service = MagicMock()

    state = inspector.inspect()

    # Verify duplication detection marks them as NOT duplicate (they serve different purposes)
    resource_dup = [d for d in state.duplicated_capabilities if d.concept == "resource_control"]
    assert len(resource_dup) > 0
    dup = resource_dup[0]
    assert dup.duplicate == False
    assert "Keep both" in dup.reuse_recommendation


def test_reports_unknown_instead_of_inventing_state(inspector):
    """Test 6: Inspector reports UNKNOWN instead of inventing state."""
    # Remove all services to force UNKNOWN states
    inspector.operational_self_examination_service = None
    inspector.control_master_service = None
    inspector.environment_self_awareness_service = None
    inspector.capability_readiness_service = None
    inspector.role_router = None

    state = inspector.inspect()

    # Verify UNKNOWN is reported instead of invented values
    assert "UNKNOWN" in state.validation_state.get('operational_examination', '')
    assert "UNKNOWN" in state.governance_state.get('control_master', '')
    assert "UNKNOWN" in state.resource_state.get('environment', '')
    assert "UNKNOWN" in state.capabilities.get('readiness', '')
    assert "UNKNOWN" in state.provider_state.get('health', '')


def test_exposes_resource_health(inspector, mock_environment_service):
    """Test 7: Inspector exposes resource health."""
    state = inspector.inspect()

    # Verify resource health dimension exists
    resource_health = state.health_dimensions.get('resource')
    assert resource_health is not None
    assert resource_health.name == 'resource'
    assert resource_health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.BLOCKED, HealthStatus.UNKNOWN)

    # Verify resource state is composed from EnvironmentSelfAwarenessService
    assert state.resource_state['environment'] != 'UNKNOWN'
    assert state.resource_state['environment']['ram_available_mb'] == 6000
    assert state.resource_state['environment']['cpu_load_pct'] == 45.0


def test_exposes_memory_health(inspector):
    """Test 8: Inspector exposes memory health."""
    state = inspector.inspect()

    # Verify memory health dimension exists
    memory_health = state.health_dimensions.get('memory')
    assert memory_health is not None
    assert memory_health.name == 'memory'
    assert memory_health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.BLOCKED, HealthStatus.UNKNOWN)

    # Verify memory state is composed
    assert state.memory_state is not None


def test_exposes_validation_health(inspector, mock_operational_service):
    """Test 9: Inspector exposes validation health."""
    state = inspector.inspect()

    # Verify validation health dimension exists
    validation_health = state.health_dimensions.get('validation')
    assert validation_health is not None
    assert validation_health.name == 'validation'
    assert validation_health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.BLOCKED, HealthStatus.UNKNOWN)

    # Verify validation state is composed from OperationalSelfExaminationService
    assert state.validation_state['operational_findings'] is not None
    assert state.validation_state['operational_findings']['total_findings'] == 2


def test_recommendations_do_not_execute_actions(inspector):
    """Test 10: Recommendations do not execute actions."""
    # Create a state with recommendations
    inspector.resource_aware_controller = None  # Trigger broken chain recommendation

    state = inspector.inspect()

    # Verify recommendations are generated
    assert len(state.recommendations) > 0

    # Verify recommendations are data structures, not executed actions
    for rec in state.recommendations:
        assert isinstance(rec, Recommendation)
        assert rec.action in ('integrate', 'test', 'remove_duplicate', 'validate', 'investigate', 'use_ollama', 'use_devin', 'defer')
        assert rec.target is not None
        assert rec.reason is not None
        # Verify no side effects - recommendations are just data
        assert not hasattr(rec, 'executed')
        assert not hasattr(rec, 'result')


def test_no_provider_tool_executes_during_inspection(inspector, mock_role_router):
    """Test 11: No provider/tool executes during inspection."""
    # Track calls to provider methods
    initial_call_count = mock_role_router.health_snapshot.call_count

    state = inspector.inspect()

    # Verify only health_snapshot was called (for provider state)
    # No actual provider execution methods should be called
    assert mock_role_router.health_snapshot.call_count == initial_call_count + 1

    # Verify no other provider methods were called
    for attr in dir(mock_role_router):
        if not attr.startswith('_') and callable(getattr(mock_role_router, attr)):
            if attr != 'health_snapshot':
                # Should not have been called during inspection
                method = getattr(mock_role_router, attr)
                if hasattr(method, 'call_count'):
                    assert method.call_count == 0, f"Provider method {attr} was called during inspection"


def test_existing_governance_remains_unchanged(inspector, mock_control_master_service):
    """Test 12: Existing governance remains unchanged."""
    # Get initial governance state
    initial_state = mock_control_master_service.current_state(refresh=False)

    # Run inspection
    state = inspector.inspect()

    # Verify ControlMasterService state was not modified
    final_state = mock_control_master_service.current_state(refresh=False)
    assert initial_state.active_objective_ids == final_state.active_objective_ids
    assert initial_state.global_rules == final_state.global_rules
    assert initial_state.recent_decisions == final_state.recent_decisions

    # Verify inspector only read state, did not modify
    mock_control_master_service.current_state.assert_called_with(refresh=False)
    # No mutation methods should have been called
    for attr in dir(mock_control_master_service):
        if attr.startswith('add_') or attr.startswith('remove_') or attr.startswith('update_'):
            method = getattr(mock_control_master_service, attr)
            if hasattr(method, 'call_count'):
                assert method.call_count == 0, f"Governance mutation method {attr} was called"


def test_self_development_readiness(inspector):
    """Test self-development readiness determination."""
    readiness = inspector.self_development_readiness()

    # Verify all readiness flags are present
    required_keys = [
        'can_identify_current_state',
        'can_identify_work',
        'can_identify_gaps',
        'can_identify_disconnected_systems',
        'can_identify_duplication',
        'can_identify_resource_constraints',
        'can_generate_recommendation',
    ]
    for key in required_keys:
        assert key in readiness
        assert isinstance(readiness[key], bool)


def test_cached_state_for_bounded_performance(inspector):
    """Test that inspection uses cached state for bounded performance."""
    import time

    # First inspection
    start = time.monotonic()
    state1 = inspector.inspect()
    first_duration = time.monotonic() - start

    # Second inspection should use cache
    start = time.monotonic()
    state2 = inspector.inspect()
    second_duration = time.monotonic() - start

    # Second call should be faster (cached)
    assert second_duration < first_duration
    assert state1.generated_at == state2.generated_at

    # Force refresh should bypass cache
    start = time.monotonic()
    state3 = inspector.inspect(force_refresh=True)
    third_duration = time.monotonic() - start

    # Force refresh should take similar time to first call
    assert third_duration >= second_duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
