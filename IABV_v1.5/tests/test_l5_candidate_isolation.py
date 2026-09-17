"""L5 Candidate Isolation Experiment

Tests whether persisted verified experience changes the winner in a strictly
isolated two-candidate competition using the normal production select() path
with allowed_tool_ids filtering.

This variant addresses the methodological gap identified by the independent
Sonnet/Claude forensic audit: the previous competitive-selection experiment
did not isolate the candidate universe because ToolRegistry._seed_defaults()
inserted additional hidden candidates (e.g., aider_coder).

This experiment uses allowed_tool_ids to ensure exactly candidate_a and
candidate_b are admitted to the competitive set.

Causal chain to verify:
prior verified world experience
        ↓
persistent learning state
        ↓
fresh reload
        ↓
normal InteractionModeSelector.select()
        ↓
allowed_tool_ids=["candidate_a", "candidate_b"]
        ↓
exactly A/B scored
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


def test_l5_candidate_isolation_winner_changes(tmp_path):
    """L5: Verified experience → persistence → reload → select() with isolation → winner change.

    CONTROL: Candidate A wins (baseline success advantage)
    TREATMENT: Candidate B wins (verified experience provides score boost)

    This test uses allowed_tool_ids to ensure exactly candidate_a and candidate_b
    compete, demonstrating that persisted verified experience can change the actual
    selection decision in a genuinely isolated competition.
    """
    tmp_path = Path(tmp_path)
    db_path = tmp_path / 'tool_records.sqlite'
    storage_path = tmp_path / 'tool_teaching'

    # Shared request for both control and treatment
    request = InferenceRequest(
        user_goal='write a simple python function',
        site_hint=None,
    )

    # ===== CONTROL: Baseline competition with candidate isolation =====
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

    # Normal production select() call with candidate isolation
    control_decision = control_selector.select(
        request=request,
        draft_task=None,
        suggested_tool_id=None,
        allowed_tool_ids=["candidate_a", "candidate_b"],  # ISOLATE CANDIDATES
        worker_pool=None,
    )

    print("\n=== CONTROL (NO VERIFIED EXPERIENCE) ===")
    print(f"Selected tool: {control_decision.selected_tool_id}")
    print(f"Selected mode: {control_decision.selected_mode}")
    print(f"Reason: {control_decision.reason}")
    print(f"Metadata keys: {list(control_decision.metadata.keys()) if control_decision.metadata else 'None'}")

    # Verify candidate isolation
    control_ranking = control_decision.metadata.get('candidate_ranking', [])
    print(f"Candidate ranking: {control_ranking}")
    control_ranked_ids = [item.get('tool_id') for item in control_ranking]
    assert set(control_ranked_ids) == {'candidate_a', 'candidate_b'}, \
        f"Control ranking should contain only A and B, got {control_ranked_ids}"

    # Capture control scores
    control_a_score = next((item.get('score') for item in control_ranking if item.get('tool_id') == 'candidate_a'), None)
    control_b_score = next((item.get('score') for item in control_ranking if item.get('tool_id') == 'candidate_b'), None)
    print(f"Control scores: A={control_a_score}, B={control_b_score}")

    # Verify A wins in control
    assert control_decision.selected_tool_id == 'candidate_a', \
        f"Control: Candidate A should win baseline, got {control_decision.selected_tool_id}"

    # ===== TREATMENT: Add verified experience for B with same isolation =====
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

    # Normal production select() call with fresh objects and same isolation
    treatment_decision = fresh_treatment_selector.select(
        request=request,  # SAME request
        draft_task=None,
        suggested_tool_id=None,
        allowed_tool_ids=["candidate_a", "candidate_b"],  # SAME ISOLATION
        worker_pool=None,
    )

    print("\n=== TREATMENT (WITH VERIFIED EXPERIENCE FOR B) ===")
    print(f"Selected tool: {treatment_decision.selected_tool_id}")
    print(f"Selected mode: {treatment_decision.selected_mode}")
    print(f"Reason: {treatment_decision.reason}")
    print(f"Metadata keys: {list(treatment_decision.metadata.keys()) if treatment_decision.metadata else 'None'}")

    # Verify candidate isolation
    treatment_ranking = treatment_decision.metadata.get('candidate_ranking', [])
    print(f"Candidate ranking: {treatment_ranking}")
    treatment_ranked_ids = [item.get('tool_id') for item in treatment_ranking]
    assert set(treatment_ranked_ids) == {'candidate_a', 'candidate_b'}, \
        f"Treatment ranking should contain only A and B, got {treatment_ranked_ids}"

    # Capture treatment scores
    treatment_a_score = next((item.get('score') for item in treatment_ranking if item.get('tool_id') == 'candidate_a'), None)
    treatment_b_score = next((item.get('score') for item in treatment_ranking if item.get('tool_id') == 'candidate_b'), None)
    print(f"Treatment scores: A={treatment_a_score}, B={treatment_b_score}")

    # Capture learning state
    reusable_pattern_id = treatment_decision.metadata.get('reusable_pattern_id')
    print(f"Reusable pattern ID: {reusable_pattern_id}")

    # Verify B wins in treatment
    assert treatment_decision.selected_tool_id == 'candidate_b', \
        f"Treatment: Candidate B should win with learning, got {treatment_decision.selected_tool_id}"

    # Verify winner change
    assert control_decision.selected_tool_id != treatment_decision.selected_tool_id, \
        "Winner should change from control to treatment"

    print("\n=== L5 CANDIDATE ISOLATION CONFIRMED ===")
    print(f"Control winner: {control_decision.selected_tool_id} (score={control_a_score})")
    print(f"Treatment winner: {treatment_decision.selected_tool_id} (score={treatment_b_score})")
    print(f"Winner changed: YES")
    print(f"Candidate universe: allowed_tool_ids=['candidate_a', 'candidate_b']")
    print(f"Score delta for B: {treatment_b_score - control_b_score}")
    print(f"Reusable pattern: {reusable_pattern_id}")
