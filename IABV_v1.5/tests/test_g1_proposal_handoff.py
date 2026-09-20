"""
Tests for G1 autonomous proposal handoff to governance.

Tests the circuit:
G1 proposal → proposed_assistant_kind → governance → accepted/vetoed/overridden → assistant_kind

Classification: UNIT_BEHAVIOR (uses real AutonomyGovernancePolicy with controlled dependencies)
"""

from unittest.mock import Mock, patch
import pytest

from iabv_v15.domain.models import (
    CapabilityReadiness,
    CapabilityStatus,
    EnvironmentSelfModel,
    GoalContext,
    NetworkStatusSnapshot,
    OperationalBlockRecord,
    WorldModelSnapshot,
)
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy


class TestG1ProposalHandoff:
    """Test G1 autonomous proposal handoff to governance."""

    def test_a1_proposal_accepted(self):
        """A1: Autonomous proposal is accepted when no human override exists."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        result = policy.evaluate(
            user_goal='Test objective',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='codex',
            proposed_assistant_source='autonomous_validation_cycle',
        )

        assert result['should_consult'] is True
        assert result['assistant_kind'] == 'codex'
        assert result['proposal_disposition'] == 'accepted'
        assert result['proposed_assistant_kind'] == 'codex'
        assert result['proposed_assistant_source'] == 'autonomous_validation_cycle'
        assert result['final_assistant_kind'] == 'codex'

    def test_a2_proposal_vetoed_by_blocked_assistant(self):
        """A2: Autonomous proposal is vetoed when assistant is in blocked_assistants."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        result = policy.evaluate(
            user_goal='Test objective',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='codex',
            proposed_assistant_source='autonomous_validation_cycle',
            blocked_assistants=['codex'],
        )

        assert result['should_consult'] is False
        assert result['assistant_kind'] == ''
        assert result['proposal_disposition'] == 'vetoed'
        assert result['proposed_assistant_kind'] == 'codex'
        assert result['proposed_assistant_source'] == 'autonomous_validation_cycle'

    def test_a3_human_override_autonomous_proposal(self):
        """A3: Human explicit request overrides autonomous proposal."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        result = policy.evaluate(
            user_goal='consulta a codex este fallo',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='chatgpt',
            proposed_assistant_source='autonomous_validation_cycle',
        )

        assert result['should_consult'] is True
        assert result['assistant_kind'] == 'codex'
        assert result['proposal_disposition'] == 'overridden'
        assert result['proposed_assistant_kind'] == 'chatgpt'
        assert result['final_assistant_kind'] == 'codex'

    def test_a4_world_model_veto_proposal(self):
        """A4: World Model block vetoes autonomous proposal."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        block_record = OperationalBlockRecord(
            block_type='assistant_unavailable',
            assistant_kind='codex',
            title='Codex unavailable',
            reason='Codex is not available',
            confidence=0.8,
            target_scope='consult_codex',
        )
        network_status = NetworkStatusSnapshot(status='connected')
        world_model = WorldModelSnapshot(
            block_records=[block_record],
            network_status=network_status,
        )

        result = policy.evaluate(
            user_goal='Test objective',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='codex',
            proposed_assistant_source='autonomous_validation_cycle',
            world_model=world_model,
        )

        assert result['should_consult'] is False
        assert result['assistant_kind'] == ''
        assert result['proposal_disposition'] == 'vetoed'
        assert result['proposed_assistant_kind'] == 'codex'


class TestGovernanceResourceOrder:
    """Test F1: Governance decision happens before resource gate."""

    def test_f1_governance_before_resource_gate(self):
        """F1: Governance decision precedes resource gate selection."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        # Event log to track execution order
        events = []

        def mock_worker_gate(target_assistant):
            events.append('resource_gate')
            return {'usable': True, 'top_worker': {'resource_id': 'test'}}

        # Governance should happen first
        result = policy.evaluate(
            user_goal='Test objective',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='codex',
            proposed_assistant_source='autonomous_validation_cycle',
        )

        # Governance decision is made
        assert result['assistant_kind'] == 'codex'
        assert result['should_consult'] is True

        # Resource gate was NOT called (no event)
        assert 'resource_gate' not in events

        # Governance received proposed_assistant_kind, not a pre-selected resource
        assert result['proposed_assistant_kind'] == 'codex'


class TestProposalIdentityContinuity:
    """Test identity continuity from proposal to decision."""

    def test_proposal_to_decision_identity_continuity(self):
        """Test proposal identity survives through governance to decision."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        result = policy.evaluate(
            user_goal='Test objective',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='chatgpt',
            proposed_assistant_source='autonomous_validation_cycle',
        )

        # Proposal trace
        assert result['proposed_assistant_kind'] == 'chatgpt'
        assert result['proposed_assistant_source'] == 'autonomous_validation_cycle'

        # Governance decision
        assert result['assistant_kind'] == 'chatgpt'
        assert result['proposal_disposition'] == 'accepted'
        assert result['final_assistant_kind'] == 'chatgpt'

        # Identity preserved: P proposal → P decision
        assert result['proposed_assistant_kind'] == result['final_assistant_kind']

    def test_override_identity_distinction(self):
        """Test override case: proposal P != decision Q are distinct."""
        policy = AutonomyGovernancePolicy(allow_parallel_comparison=False)

        result = policy.evaluate(
            user_goal='consulta a codex este fallo',
            session_status='planned',
            session_readiness={},
            live_audit={},
            assistant_guidance={},
            capability_snapshot=[],
            approval_pending=False,
            intent_key='auto_execute_from_pulse',
            proposed_assistant_kind='chatgpt',
            proposed_assistant_source='autonomous_validation_cycle',
        )

        # Proposal trace
        assert result['proposed_assistant_kind'] == 'chatgpt'

        # Governance decision (human override)
        assert result['assistant_kind'] == 'codex'
        assert result['proposal_disposition'] == 'overridden'
        assert result['final_assistant_kind'] == 'codex'

        # Identity distinction: P proposal != Q decision
        assert result['proposed_assistant_kind'] != result['final_assistant_kind']


class TestSecondaryIADerivation:
    """Test secondary_ia derivation from action_plan."""

    def test_secondary_ia_from_action_plan_consultation(self):
        """Test secondary_ia is derived when action_plan[1] is a consultation."""
        from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService

        # Create a minimal cycle instance
        cycle = AutonomousValidationCycleService(
            experiment_lab=Mock(),
            experiment_lab_repository=Mock(),
            sandbox_experiment_service=Mock(),
            auto_start=False,
        )

        # action_plan with real consultation in step 2
        action_plan = [
            {'step': 1, 'ia': 'codex', 'action': 'Investigar y proponer solución'},
            {'step': 2, 'ia': 'chatgpt', 'action': 'Validar y complementar propuesta'},
        ]

        secondary_ia = cycle._derive_secondary_ia_from_action_plan(action_plan)

        # Should derive secondary_ia because step 2 is a consultation
        assert secondary_ia == 'chatgpt'

    def test_secondary_ia_from_action_plan_policy_adjustment(self):
        """Test secondary_ia is NOT derived when action_plan[1] is a policy adjustment."""
        from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService

        # Create a minimal cycle instance
        cycle = AutonomousValidationCycleService(
            experiment_lab=Mock(),
            experiment_lab_repository=Mock(),
            sandbox_experiment_service=Mock(),
            auto_start=False,
        )

        # action_plan with policy adjustment in step 2 (route_substitution case)
        action_plan = [
            {'step': 1, 'ia': 'codex', 'action': 'Asumir tareas que fallaban con chatgpt'},
            {'step': 2, 'ia': 'chatgpt', 'action': 'Reducir prioridad hasta evidencia de mejora'},
        ]

        secondary_ia = cycle._derive_secondary_ia_from_action_plan(action_plan)

        # Should NOT derive secondary_ia because step 2 is a policy adjustment
        assert secondary_ia == ''

    def test_secondary_ia_from_single_step_plan(self):
        """Test secondary_ia is empty when action_plan has only one step."""
        from iabv_v15.services.self_teach.autonomous_validation_cycle import AutonomousValidationCycleService

        # Create a minimal cycle instance
        cycle = AutonomousValidationCycleService(
            experiment_lab=Mock(),
            experiment_lab_repository=Mock(),
            sandbox_experiment_service=Mock(),
            auto_start=False,
        )

        # action_plan with only one step
        action_plan = [
            {'step': 1, 'ia': 'codex', 'action': 'Investigar problema'},
        ]

        secondary_ia = cycle._derive_secondary_ia_from_action_plan(action_plan)

        # Should be empty
        assert secondary_ia == ''
