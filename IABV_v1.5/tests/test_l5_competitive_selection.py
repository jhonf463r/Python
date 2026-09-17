"""L5 Competitive Selection Experiment

Tests whether persisted verified experience changes the winner in a competitive
selector decision using the normal production select() path.

Causal chain to verify:
prior verified world experience
        ↓
persistent learning state
        ↓
fresh reload
        ↓
normal InteractionModeSelector.select()
        ↓
multiple competing candidates
        ↓
winner changes
"""

import pytest
from pathlib import Path

from iabv_v15.domain.models import (
    InteractionChannel,
    InteractionMode,
    InferenceRequest,
    ToolCard,
    ToolType,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_registry import ToolRegistry


class DummyAdapter:
    """Deterministic adapter fixture for controlled availability."""
    def __init__(self, tool_type: ToolType, *, available: bool = True) -> None:
        self.tool_type = tool_type
        self.available = available

    def is_available(self, card: ToolCard) -> bool:
        return self.available


def test_l5_competitive_selection_winner_changes(tmp_path):
    """L5: Verified experience → persistence → reload → select() → winner change.

    CONTROL: Candidate A wins (baseline score advantage)
    TREATMENT: Candidate B wins (verified experience provides score boost)

    This test uses the normal production InteractionModeSelector.select() path
    with two competing candidates to demonstrate that persisted verified
    experience can change the actual selection decision.
    """
    tmp_path = Path(tmp_path)
    db_path = tmp_path / 'tool_records.sqlite'
    storage_path = tmp_path / 'tool_teaching'

    # Shared request for both control and treatment
    request = InferenceRequest(
        user_goal='write a simple python function',
        site_hint=None,
    )

    # ===== CONTROL: Baseline competition =====
    control_db_path = tmp_path / 'control_tool_records.sqlite'
    control_storage_path = tmp_path / 'control_tool_teaching'

    control_repository = ToolRecordRepository(
        AppDatabase(str(control_db_path)),
        ArtifactStorage(str(control_storage_path))
    )

    # Candidate A: Better baseline (higher success history)
    candidate_a = ToolCard(
        tool_id='candidate_a',
        tool_type=ToolType.CODE_EDITOR,
        title='Candidate A',
        name='Candidate A',
        description='Candidate with better success history',
        adapter_key='aider',
        available=True,
        success_count=10,  # Better baseline
        failure_count=0,
        cost_score=0.5,
        capabilities=['code_generation'],
    )
    control_repository.save_card(candidate_a)

    # Candidate B: Worse baseline (no success history)
    candidate_b = ToolCard(
        tool_id='candidate_b',
        tool_type=ToolType.CODE_EDITOR,
        title='Candidate B',
        name='Candidate B',
        description='Candidate with no success history',
        adapter_key='aider',
        available=True,
        success_count=0,  # Worse baseline
        failure_count=0,
        cost_score=0.5,
        capabilities=['code_generation'],
    )
    control_repository.save_card(candidate_b)

    # Both candidates use the same adapter (both available)
    adapters = {
        'aider': DummyAdapter(ToolType.CODE_EDITOR, available=True),
    }
    control_registry = ToolRegistry(control_repository, adapters)
    control_selector = InteractionModeSelector(control_registry, control_repository)

    # Normal production select() call
    control_decision = control_selector.select(
        request=request,
        draft_task=None,
        suggested_tool_id=None,
        allowed_tool_ids=None,
        worker_pool=None,
    )

    print("\n=== CONTROL (NO VERIFIED EXPERIENCE) ===")
    print(f"Selected tool: {control_decision.selected_tool_id}")
    print(f"Selected mode: {control_decision.selected_mode}")
    print(f"Reason: {control_decision.reason}")

    # Verify A wins in control
    assert control_decision.selected_tool_id == 'candidate_a', \
        f"Control: Candidate A should win baseline, got {control_decision.selected_tool_id}"

    # ===== TREATMENT: Add verified experience for B =====
    treatment_db_path = tmp_path / 'treatment_tool_records.sqlite'
    treatment_storage_path = tmp_path / 'treatment_tool_teaching'

    treatment_repository = ToolRecordRepository(
        AppDatabase(str(treatment_db_path)),
        ArtifactStorage(str(treatment_storage_path))
    )

    # Same candidates as control
    treatment_repository.save_card(candidate_a)
    treatment_repository.save_card(candidate_b)

    treatment_registry = ToolRegistry(treatment_repository, adapters)
    treatment_learning = InteractionLearningService(treatment_repository)

    # Create verified transition for Candidate B
    import hashlib
    action_signature = hashlib.sha256(
        f'candidate_b|write_file|test.py'.encode('utf-8')
    ).hexdigest()

    from iabv_v15.domain.models import VerifiedTransition
    verified_transition = VerifiedTransition(
        action_signature=action_signature,
        action='write_file',
        target='test.py',
        tool_id='candidate_b',
        tool_type=ToolType.CODE_EDITOR,
        channel=InteractionChannel.BACKGROUND,
        objective='write a simple python function',  # Match request goal
        actor_reported_success=True,
        verification_status='verified',
        action_executed=True,
        action_result_observed=True,
        action_result_verified=True,
        expected_state_source='plan_parameters_deterministic',
        observed_state_source='independent_filesystem_observation',
        expected_state={'file_exists': True},
        observed_state={'file_exists': True},
    )

    treatment_learning.learn_from_verified_transition(verified_transition)

    # Fresh reload: NEW repository, NEW registry, NEW selector
    del treatment_repository
    del treatment_registry
    del treatment_learning

    fresh_treatment_repository = ToolRecordRepository(
        AppDatabase(str(treatment_db_path)),
        ArtifactStorage(str(treatment_storage_path))
    )
    fresh_treatment_registry = ToolRegistry(fresh_treatment_repository, adapters)
    fresh_treatment_selector = InteractionModeSelector(fresh_treatment_registry, fresh_treatment_repository)

    # Normal production select() call with fresh objects
    treatment_decision = fresh_treatment_selector.select(
        request=request,  # SAME request
        draft_task=None,
        suggested_tool_id=None,
        allowed_tool_ids=None,
        worker_pool=None,
    )

    print("\n=== TREATMENT (WITH VERIFIED EXPERIENCE FOR B) ===")
    print(f"Selected tool: {treatment_decision.selected_tool_id}")
    print(f"Selected mode: {treatment_decision.selected_mode}")
    print(f"Reason: {treatment_decision.reason}")

    # Verify B wins in treatment
    assert treatment_decision.selected_tool_id == 'candidate_b', \
        f"Treatment: Candidate B should win with learning, got {treatment_decision.selected_tool_id}"

    # Verify winner change
    assert control_decision.selected_tool_id != treatment_decision.selected_tool_id, \
        "Winner should change from control to treatment"

    print("\n=== L5 COMPETITIVE SELECTION CONFIRMED ===")
    print(f"Control winner: {control_decision.selected_tool_id}")
    print(f"Treatment winner: {treatment_decision.selected_tool_id}")
    print(f"Winner changed: YES")
