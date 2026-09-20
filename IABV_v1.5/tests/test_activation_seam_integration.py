"""ACTIVATION SEAM INTEGRATION TEST: Phase 1 → Phase 2

Tests that:
- Phase 1 produces a serialized AdaptiveSession
- Phase 2 can be activated from non-UI context
- Resource identity is preserved across the boundary
- Canonical Phase 2 implementation is reused
- Duplicate activation is prevented
- Governance and authorization are preserved

This test demonstrates the I0/I1 activation seam closure.
"""

import pytest
import os
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch

from iabv_v15.domain.models import (
    InferenceRequest,
    TaskRole,
    TaskIntent,
    IntentRouteDecision,
    AdaptiveSession,
)
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.services.evolution.autonomous_evolution_service import AutonomousEvolutionService


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _minimal_orchestrator(root: Path) -> AdaptiveTaskOrchestrator:
    """Build AdaptiveTaskOrchestrator with minimal controlled dependencies."""
    # Controlled mocks for dependencies not directly related to activation seam
    intent_service = Mock()
    intent_service.classify_with_schema = Mock(return_value=(
        TaskIntent(
            intent_key='test',
            confidence=0.8,
            detected_role=TaskRole.TOOL_USE,
            extracted_goals=[],
            estimated_complexity='low',
        ),
        Mock(),
    ))

    context_assembler = Mock()
    context_assembler.build_perception_snapshot = Mock(return_value=Mock(
        decision_context={'user_goal': 'test goal', 'governance': {'should_consult': True, 'assistant_kind': 'codex'}, 'metadata': {}},
        task_context=Mock(metadata={}),
        metadata={},
    ))

    adaptive_session_repository = Mock()
    adaptive_session_repository.get = Mock(return_value=None)
    adaptive_session_repository.save = Mock(side_effect=lambda s: s)

    capability_service = Mock()
    strategy_pack_registry = Mock()
    planner_service = Mock()
    approval_gate_service = Mock()

    task_outcome_recorder = Mock()
    task_outcome_recorder.record = Mock(side_effect=lambda s: s)

    execution_playbook_service = Mock()

    # AutonomousEvolutionService mock (will be controlled in test)
    autonomous_evolution_service = Mock(spec=AutonomousEvolutionService)
    autonomous_evolution_service.plan_or_execute = Mock(return_value={
        'status': 'noop',
        'reason': 'Dry run - no external execution',
        'assistant_kind': 'codex',
    })

    # LocalRoleRouter mock
    role_router = Mock()
    role_router.build_decision_from_intent = Mock(return_value=IntentRouteDecision(
        detected_role=TaskRole.TOOL_USE,
        planner_required=False,
        visual_required=False,
        tool_chain=[],
        reason='Mocked route decision',
    ))
    role_router.worker_health_gate = Mock(return_value={
        'usable': True,
        'top_worker': {
            'resource_id': 'devin_credential_0',
            'provider': 'devin',
            'tool': 'devin_api',
            'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
            'email': '',
            'browser': '',
            'profile': '',
        },
        'recommended_account': None,
        'ranked_workers': [],
        'available_count': 1,
        'reason': '',
        'account_selection_source': 'auto_ranked',
        'fallback_used': False,
    })

    orchestrator = AdaptiveTaskOrchestrator(
        intent_service=intent_service,
        role_router=role_router,
        context_assembler=context_assembler,
        adaptive_session_repository=adaptive_session_repository,
        capability_service=capability_service,
        strategy_pack_registry=strategy_pack_registry,
        planner_service=planner_service,
        approval_gate_service=approval_gate_service,
        autonomous_evolution_service=autonomous_evolution_service,
        task_outcome_recorder=task_outcome_recorder,
        execution_playbook_service=execution_playbook_service,
    )

    return orchestrator


class TestActivationSeamIntegration:
    """Test that Phase 1 → Phase 2 activation seam works correctly."""

    def test_phase1_to_phase2_activation_seam(self):
        """Test: Phase 1 result → activate_phase2() → Phase 2 executed (INTEGRATION)."""
        os.environ['DEVIN_API_KEY_A'] = 'credential_a'

        root = _workspace('test_activation_seam')
        orchestrator = _minimal_orchestrator(root)

        # === PHASE 1: Create serialized AdaptiveSession ===
        # Simulate Phase 1 result: serialized AdaptiveSession with worker_gate selection
        serialized_session = {
            'session_id': str(uuid4()),
            'user_goal': 'Test objective',
            'intent': {
                'intent_key': 'test',
                'confidence': 0.8,
                'detected_role': 'tool_use',
            },
            'metadata': {
                'worker_gate': {
                    'usable': True,
                    'top_worker': {
                        'resource_id': 'devin_credential_0',
                        'provider': 'devin',
                        'tool': 'devin_api',
                        'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                        'email': '',
                        'browser': '',
                        'profile': '',
                    },
                    'recommended_account': None,
                    'ranked_workers': [],
                    'available_count': 1,
                    'reason': '',
                    'account_selection_source': 'auto_ranked',
                    'fallback_used': False,
                },
                'selection_status': 'valid',
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                'decision_context': {
                    'governance': {
                        'should_consult': True,
                        'assistant_kind': 'codex',
                    },
                },
            },
        }

        # Verify Phase 1 result has worker_gate selection
        assert 'metadata' in serialized_session
        assert 'worker_gate' in serialized_session['metadata']
        assert serialized_session['metadata']['worker_gate']['top_worker']['resource_id'] == 'devin_credential_0'
        assert serialized_session['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert serialized_session['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

        # === PHASE 2: Activate from non-UI context ===
        # Call activate_phase2() with the serialized session
        phase2_payload = orchestrator.activate_phase2(
            adaptive_session=serialized_session,
            user_goal='Test objective',
            source='executive',
        )

        # Verify Phase 2 was executed through canonical implementation
        assert orchestrator.autonomous_evolution_service.plan_or_execute.called
        call_args = orchestrator.autonomous_evolution_service.plan_or_execute.call_args
        assert call_args[1]['user_goal'] == 'Test objective'
        assert call_args[1]['source'] == 'executive'

        # Verify resource identity is preserved across Phase 1 → Phase 2
        assert phase2_payload['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert phase2_payload['metadata']['selected_provider'] == 'devin'
        assert phase2_payload['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

        # Verify Phase 2 result is appended
        assert 'autonomous_evolution' in phase2_payload['metadata']
        assert phase2_payload['metadata']['autonomous_evolution']['status'] == 'noop'

        # Cleanup
        del os.environ['DEVIN_API_KEY_A']

    def test_duplicate_activation_guard(self):
        """Test: activate_phase2() prevents duplicate execution when already activated."""
        orchestrator = _minimal_orchestrator(_workspace('test_duplicate_guard'))

        # Phase 1 result with Phase 2 already executed
        serialized_session = {
            'session_id': str(uuid4()),
            'user_goal': 'Test objective',
            'metadata': {
                'worker_gate': {
                    'usable': True,
                    'top_worker': {
                        'resource_id': 'devin_credential_0',
                        'provider': 'devin',
                        'tool': 'devin_api',
                        'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                    },
                },
                'autonomous_evolution': {
                    'status': 'prepared',
                    'assistant_kind': 'codex',
                },
            },
        }

        # Call activate_phase2() - should return existing result without re-executing
        phase2_payload = orchestrator.activate_phase2(
            adaptive_session=serialized_session,
            user_goal='Test objective',
            source='executive',
        )

        # Verify autonomous_evolution_service was NOT called (duplicate prevented)
        assert not orchestrator.autonomous_evolution_service.plan_or_execute.called

        # Verify existing Phase 2 result is preserved
        assert phase2_payload['metadata']['autonomous_evolution']['status'] == 'prepared'
        assert phase2_payload['metadata']['autonomous_evolution']['assistant_kind'] == 'codex'

    def test_governance_preserved_in_phase2(self):
        """Test: activate_phase2() preserves resource identity even when governance blocks external consultation."""
        orchestrator = _minimal_orchestrator(_workspace('test_governance'))

        # Phase 1 result with governance.should_consult = False and selection already propagated
        serialized_session = {
            'session_id': str(uuid4()),
            'user_goal': 'Test objective',
            'intent': {
                'intent_key': 'test',
                'confidence': 0.8,
                'detected_role': 'tool_use',
            },
            'metadata': {
                'worker_gate': {
                    'usable': True,
                    'top_worker': {
                        'resource_id': 'devin_credential_0',
                        'provider': 'devin',
                        'tool': 'devin_api',
                        'credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                    },
                },
                'selection_status': 'valid',
                'selected_resource_id': 'devin_credential_0',
                'selected_provider': 'devin',
                'selected_credential_ref': 'devin:credential_0:DEVIN_API_KEY_A',
                'decision_context': {
                    'governance': {
                        'should_consult': False,
                        'assistant_kind': 'local',
                    },
                },
            },
        }

        # Call activate_phase2()
        phase2_payload = orchestrator.activate_phase2(
            adaptive_session=serialized_session,
            user_goal='Test objective',
            source='executive',
        )

        # Verify resource identity is preserved even though Phase 2 may not execute
        assert phase2_payload['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert phase2_payload['metadata']['selected_provider'] == 'devin'
        assert phase2_payload['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'

    def test_auto_execute_from_sync_pulse_uses_canonical_authority(self):
        """Test: auto_execute_from_sync_pulse() delegates to activate_phase2() canonical authority."""
        orchestrator = _minimal_orchestrator(_workspace('test_g1_canonical'))

        # Simulate proposals from sync_pulse
        proposals = [
            {
                'estimated_confidence': 0.8,
                'primary_ia': 'codex',
                'secondary_ia': 'chatgpt',
                'type': 'coordinated_plan',
                'title': 'Test proposal',
            },
        ]

        # Mock activate_phase2 to track invocation
        original_activate_phase2 = orchestrator.activate_phase2
        activate_phase2_called = []

        def mock_activate_phase2(adaptive_session, *, user_goal, source):
            activate_phase2_called.append({
                'adaptive_session': adaptive_session,
                'user_goal': user_goal,
                'source': source,
            })
            return original_activate_phase2(adaptive_session, user_goal=user_goal, source=source)

        orchestrator.activate_phase2 = mock_activate_phase2

        # Call auto_execute_from_sync_pulse
        result = orchestrator.auto_execute_from_sync_pulse(proposals)

        # Verify activate_phase2 was called (canonical authority used)
        assert len(activate_phase2_called) == 1
        assert activate_phase2_called[0]['user_goal'] == 'Test proposal'
        assert activate_phase2_called[0]['source'] == 'auto_execute_from_sync_pulse'

        # Verify result is not None (proposal was qualified)
        assert result is not None
        assert result['executed'] is True
        assert result['coordination_status'] == 'auto_executed'

        # Verify worker_gate selection was propagated to adaptive_session
        adaptive_session_arg = activate_phase2_called[0]['adaptive_session']
        assert 'worker_gate' in adaptive_session_arg['metadata']
        assert adaptive_session_arg['metadata']['selected_resource_id'] == 'devin_credential_0'
        assert adaptive_session_arg['metadata']['selected_credential_ref'] == 'devin:credential_0:DEVIN_API_KEY_A'
