"""L5 Causal Decision Experiment

Tests whether a persisted verified experience changes a future selector decision.

Causal chain to verify:
prior verified world experience
        ↓
persistent learning state
        ↓
fresh reload
        ↓
future normal selector
        ↓
future decision
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


def test_l5_verified_experience_changes_selector_scoring(tmp_path):
    """L5: Verified experience → persistence → reload → selector scoring.

    CONTROL: No prior verified experience
    TREATMENT: Prior verified experience present (persisted + reloaded)

    This test isolates the selector scoring to determine whether the
    verified_transition_success_count actually affects future decisions.
    """
    tmp_path = Path(tmp_path)
    db_path = tmp_path / 'tool_records.sqlite'
    storage_path = tmp_path / 'tool_teaching'

    # Shared candidate universe (same tools, same initial state)
    repository = ToolRecordRepository(
        AppDatabase(str(db_path)),
        ArtifactStorage(str(storage_path))
    )
    
    # Create a simple candidate tool
    test_card = ToolCard(
        tool_id='test_tool',
        tool_type=ToolType.CODE_EDITOR,
        title='Test Tool',
        name='Test Tool',
        description='A test tool for L5 experiment',
        adapter_key='test_adapter',
        available=True,
        success_count=0,
        failure_count=0,
        cost_score=0.5,
        capabilities=['code_generation'],
    )
    repository.save_card(test_card)
    
    # Use minimal registry for selector (same pattern as existing tests)
    from iabv_v15.services.tools.tool_registry import ToolRegistry
    registry = ToolRegistry(repository, adapters={})
    
    # REQUEST 1: CONTROL (no verified experience)
    control_selector = InteractionModeSelector(registry, repository)
    
    control_request = InferenceRequest(
        user_goal='write a simple python function',
        site_hint=None,  # No site_id to match pattern
    )
    
    control_assessment = control_selector._assess_candidate(
        card=registry.get_card('test_tool'),
        request=control_request,
        draft_task=None,
        suggested_tool_id=None,
        desired_modes=[InteractionMode.BACKGROUND],  # CODE_EDITOR maps to BACKGROUND
        task_kind='code',
        worker_pool=None,
    )
    
    # REQUEST 2: TREATMENT (verified experience present)
    # First, create a verified transition through the learning service
    from iabv_v15.domain.models import VerifiedTransition
    import hashlib

    learning_service = InteractionLearningService(repository)

    # Create a verified transition for the same action signature
    # action_signature is a SHA256 hash string, not an object
    action_signature = hashlib.sha256(
        f'test_tool|write_file|test.txt'.encode('utf-8')
    ).hexdigest()

    verified_transition = VerifiedTransition(
        action_signature=action_signature,
        action='write_file',
        target='test.txt',
        tool_id='test_tool',
        tool_type=ToolType.CODE_EDITOR,
        channel=InteractionChannel.BACKGROUND,  # CODE_EDITOR maps to BACKGROUND mode
        objective='write a simple python function',  # Match the control request goal
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
    
    learning_service.learn_from_verified_transition(verified_transition)
    
    # Close repository to release database lock
    del repository
    del learning_service
    
    # NOW: FRESH RELOAD - create NEW repository instance
    treatment_repository = ToolRecordRepository(
        AppDatabase(str(db_path)),
        ArtifactStorage(str(storage_path))
    )
    treatment_selector = InteractionModeSelector(registry, treatment_repository)

    treatment_assessment = treatment_selector._assess_candidate(
        card=registry.get_card('test_tool'),
        request=control_request,  # SAME request
        draft_task=None,
        suggested_tool_id=None,
        desired_modes=[InteractionMode.BACKGROUND],  # CODE_EDITOR maps to BACKGROUND
        task_kind='code',
        worker_pool=None,
    )
    
    # CAPTURE EVIDENCE
    print("\n=== CONTROL (NO VERIFIED EXPERIENCE) ===")
    print(f"learned_pattern score: {control_assessment.scores['learned_pattern']}")
    print(f"total_score: {control_assessment.total_score}")
    print(f"pattern_id: {control_assessment.reusable_pattern_id}")
    
    print("\n=== TREATMENT (WITH VERIFIED EXPERIENCE) ===")
    print(f"learned_pattern score: {treatment_assessment.scores['learned_pattern']}")
    print(f"total_score: {treatment_assessment.total_score}")
    print(f"pattern_id: {treatment_assessment.reusable_pattern_id}")
    
    # VERIFY CAUSALITY
    # The learned_pattern score should increase from 0.0 (no pattern) to 1.0 (with verified experience)
    assert control_assessment.scores['learned_pattern'] == 0.0, \
        f"Control learned_pattern should be 0.0 (no pattern), got {control_assessment.scores['learned_pattern']}"

    assert treatment_assessment.scores['learned_pattern'] == 1.0, \
        f"Treatment learned_pattern should be 1.0 (with verified experience), got {treatment_assessment.scores['learned_pattern']}"
    
    # The total_score should be higher in treatment due to learned_pattern * 1.8
    # (plus possible secondary effects on frequency, stability, etc.)
    score_delta = treatment_assessment.total_score - control_assessment.total_score
    assert score_delta > 0, \
        f"Total score should increase in treatment, got delta {score_delta}"
    # learned_pattern contributes 1.8 (1.0 * 1.8), other factors may add more
    assert score_delta >= 1.7, \
        f"Score delta should be at least 1.7 (learned_pattern contribution), got {score_delta}"
    
    # Verify the pattern is now reusable
    assert control_assessment.reusable_pattern_id is None, \
        "Control should have no reusable pattern"
    assert treatment_assessment.reusable_pattern_id is not None, \
        "Treatment should have a reusable pattern from verified experience"
    
    print("\n=== L5 CAUSALITY CONFIRMED ===")
    print(f"Verified experience persisted and reloaded")
    print(f"Selector scoring changed: learned_pattern {control_assessment.scores['learned_pattern']} -> {treatment_assessment.scores['learned_pattern']}")
    print(f"Total score changed: {control_assessment.total_score} -> {treatment_assessment.total_score}")
    print(f"Pattern now reusable: {treatment_assessment.reusable_pattern_id}")
