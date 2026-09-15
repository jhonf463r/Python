"""
NF-IL-01: Invalidación de conocimiento por refutación experiencial

Pruebas para verificar que los patrones de interacción pueden invalidarse
cuando producen fallos consecutivos tras ser reutilizados.
"""

import pytest
from datetime import datetime, timezone

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    InteractionChannel,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolResult,
    ToolTask,
    ToolValidationStatus,
)
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector


@pytest.fixture
def simple_card():
    """Card simple para pruebas."""
    from iabv_v15.domain.models import ToolCard, ToolType
    return ToolCard(
        tool_id='test_pattern_tool',
        title='Test Pattern Tool',
        tool_type=ToolType.SHELL,
        adapter_key='test_pattern_tool',
        description='Tool for pattern invalidation tests',
        available=True,
        success_count=0,
        failure_count=0,
        last_result_id=None,
        last_validated_at_utc=None,
        metadata={'workspace_root': '/tmp'},
    )


@pytest.fixture
def repository(simple_card):
    """Repository temporal para pruebas."""
    from pathlib import Path
    import shutil
    import tempfile
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.storage import ArtifactStorage
    from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository

    root = Path(tempfile.mkdtemp(prefix='test_pattern_invalidation_'))
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(root=str(root))
        repo = ToolRecordRepository(db=db, storage=storage)
        
        yield repo
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def learning_service(repository):
    """Learning service con repository temporal."""
    return InteractionLearningService(repository=repository)


def test_e1_create_knowledge(simple_card, repository, learning_service):
    """E1: Crear conocimiento - ejecución exitosa crea patrón."""
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    
    assert pattern.success_count == 1
    assert pattern.failure_count == 0
    assert pattern.reusable is True
    assert pattern.metadata.get('consecutive_reuse_failures') == 0


def test_e2_reuse_tracking(simple_card, repository, learning_service):
    """E2: Reutilización - ejecución con reusable_pattern_id incrementa success_count."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Execute with reusable_pattern_id in metadata
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    success_result = ToolResult(
        task_id=task_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=True,
        output_text='hello again',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse, result=success_result
    )
    
    assert updated_pattern.success_count == 2
    assert updated_pattern.failure_count == 0
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0


def test_e3_refute_pattern(simple_card, repository, learning_service):
    """E3: Refutar - ejecución reutilizada falla y se asocia al patrón."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Now execute with reusable_pattern_id in metadata and fail
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result = ToolResult(
        task_id=task_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Simulated failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse, result=failure_result
    )
    
    assert updated_pattern.failure_count == 1
    assert updated_pattern.success_count == 1
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 1


def test_e4_repeat_refutation_to_threshold(simple_card, repository, learning_service):
    """E4: Repetir refutación hasta alcanzar threshold de invalidación."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Threshold is 3 consecutive failures after reuse
    THRESHOLD = 3

    for i in range(THRESHOLD):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'reused_pattern_id': pattern_id,
                    'reused_actions_from_pattern': True,
                },
                'actions': [
                    ToolAction(
                        action_type=ToolActionType.OPEN_URL,
                        target='http://example.com',
                        label='open test url',
                        metadata={'reused_from_pattern': True}
                    )
                ]
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message=f'Failure {i+1}',
            execution_ms=100,
            execution_state=ExecutionState(state='failed', detail='Error'),
            validation_status=ToolValidationStatus.UNVALIDATED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )

    assert pattern.reusable is False
    assert pattern.metadata.get('invalidated_at_utc') is not None
    assert pattern.metadata.get('consecutive_reuse_failures') == 3


def test_e5_future_selection_ignores_invalidated_pattern(simple_card, repository, learning_service):
    """E5: Selección futura ignora patrón invalidado."""
    # Create and invalidate pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Invalidate with 3 failures
    THRESHOLD = 3
    for i in range(THRESHOLD):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'reused_pattern_id': pattern_id,
                    'reused_actions_from_pattern': True,
                },
                'actions': [
                    ToolAction(
                        action_type=ToolActionType.OPEN_URL,
                        target='http://example.com',
                        label='open test url',
                        metadata={'reused_from_pattern': True}
                    )
                ]
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message=f'Failure {i+1}',
            execution_ms=100,
            execution_state=ExecutionState(state='failed', detail='Error'),
            validation_status=ToolValidationStatus.UNVALIDATED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )

    assert pattern.reusable is False

    # Reload from repository and verify
    reloaded = repository.get_interaction_pattern_by_signature(pattern.signature)
    assert reloaded is not None
    assert reloaded.reusable is False


def test_control_a_persistence_vs_learning(simple_card, repository, learning_service):
    """Control A: Patrón sin éxito verificado (success_count == 0) no se invalida."""
    # Create pattern with success_count == 0
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=False,
        output_text='',
        error_message='Initial failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    
    # Pattern should have success_count == 0, failure_count == 1
    assert pattern.success_count == 0
    assert pattern.failure_count == 1
    
    # Even with reuse_pattern_id, should not trigger invalidation mechanism
    # because it requires verified success first
    pattern_id = pattern.pattern_id
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result = ToolResult(
        task_id=task_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Another failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse, result=failure_result
    )
    
    # Pattern should still be reusable (no verified success to invalidate)
    assert updated_pattern.reusable is True
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0


def test_control_b_unrelated_failure(simple_card, repository, learning_service):
    """Control B: Fallo no relacionado no incrementa consecutive_reuse_failures."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Failure WITHOUT reusable_pattern_id (unrelated execution)
    unrelated_task = task.model_copy(
        update={
            'metadata': {},  # No pattern_id
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://different.com',
                    label='different action',
                    metadata={}
                )
            ]
        }
    )
    unrelated_failure = ToolResult(
        task_id=unrelated_task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Unrelated failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=unrelated_task, result=unrelated_failure
    )
    
    # Unrelated failure should NOT affect consecutive_reuse_failures
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0
    assert updated_pattern.reusable is True


def test_control_c_same_pattern_refutation(simple_card, repository, learning_service):
    """Control C: Fallos repetidos del mismo patrón invalidan."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Two refuting failures
    for i in range(2):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'reused_pattern_id': pattern_id,
                    'reused_actions_from_pattern': True,
                },
                'actions': [
                    ToolAction(
                        action_type=ToolActionType.OPEN_URL,
                        target='http://example.com',
                        label='open test url',
                        metadata={'reused_from_pattern': True}
                    )
                ]
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message=f'Failure {i+1}',
            execution_ms=100,
            execution_state=ExecutionState(state='failed', detail='Error'),
            validation_status=ToolValidationStatus.UNVALIDATED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )

    assert pattern.metadata.get('consecutive_reuse_failures') == 2
    assert pattern.reusable is True  # Not yet at threshold


def test_control_d_unrelated_failure_preserves_negative_evidence(simple_card, repository, learning_service):
    """Control D (NF-IL-01-R1): Fallo no relacionado preserva evidencia negativa acumulada."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # P reused + failure → consecutive_reuse_failures = 1
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result = ToolResult(
        task_id=task_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure 1',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse, result=failure_result
    )
    assert pattern.metadata.get('consecutive_reuse_failures') == 1

    # P reused + failure → consecutive_reuse_failures = 2
    task_with_reuse_2 = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result_2 = ToolResult(
        task_id=task_with_reuse_2.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_3',
        success=False,
        output_text='',
        error_message='Failure 2',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse_2, result=failure_result_2
    )
    assert pattern.metadata.get('consecutive_reuse_failures') == 2

    # Unrelated failure (no pattern_id) → should NOT reset
    unrelated_task = task.model_copy(
        update={
            'metadata': {},  # No pattern_id
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',  # SAME target = same signature
                    label='open test url',
                    metadata={}
                )
            ]
        }
    )
    unrelated_failure = ToolResult(
        task_id=unrelated_task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_4',
        success=False,
        output_text='',
        error_message='Unrelated',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=unrelated_task, result=unrelated_failure
    )
    
    # Negative evidence should be preserved
    assert pattern.metadata.get('consecutive_reuse_failures') == 2


def test_control_e_success_resets_negative_evidence(simple_card, repository, learning_service):
    """Control E (NF-IL-01-R1): Éxito después de reutilización resetea evidencia negativa."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Accumulate negative evidence
    for i in range(2):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'reused_pattern_id': pattern_id,
                    'reused_actions_from_pattern': True,
                },
                'actions': [
                    ToolAction(
                        action_type=ToolActionType.OPEN_URL,
                        target='http://example.com',
                        label='open test url',
                        metadata={'reused_from_pattern': True}
                    )
                ]
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message=f'Failure {i+1}',
            execution_ms=100,
            execution_state=ExecutionState(state='failed', detail='Error'),
            validation_status=ToolValidationStatus.UNVALIDATED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )
    
    assert pattern.metadata.get('consecutive_reuse_failures') == 2

    # Success after reuse should reset
    task_with_success = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    success_result = ToolResult(
        task_id=task_with_success.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_4',
        success=True,
        output_text='success',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_success, result=success_result
    )
    
    assert pattern.metadata.get('consecutive_reuse_failures') == 0


def test_control_f_cross_pattern_failure_does_not_affect_p(simple_card, repository, learning_service):
    """Control F (NF-IL-01-R1): Fallo de Q no altera evidencia de P."""
    # Create pattern P
    task_p = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task P',
        objective='Test objective P',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site_p',  # Different site for different signature
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(card=simple_card, task=task_p, result=result_p)
    pattern_p_id = pattern_p.pattern_id

    # Create pattern Q
    task_q = task_p.model_copy(update={'title': 'Test task Q', 'objective': 'Test objective Q', 'site_id': 'test_site_q'})
    result_q = result_p.model_copy(update={'result_id': 'result_q1'})
    pattern_q = learning_service.learn_from_execution(card=simple_card, task=task_q, result=result_q)
    pattern_q_id = pattern_q.pattern_id

    # Accumulate negative evidence for P
    task_p_reuse = task_p.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_p_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p2',
        success=False,
        output_text='',
        error_message='Pattern P failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(
        card=simple_card, task=task_p_reuse, result=failure_p
    )
    assert pattern_p.metadata.get('consecutive_reuse_failures') == 1

    # Fail with Q (different pattern)
    task_q_reuse = task_q.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_q_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_q = ToolResult(
        task_id=task_q.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_q2',
        success=False,
        output_text='',
        error_message='Pattern Q failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_q = learning_service.learn_from_execution(
        card=simple_card, task=task_q_reuse, result=failure_q
    )

    # Reload P and verify negative evidence preserved
    reloaded_p = repository.get_interaction_pattern_by_signature(pattern_p.signature)
    assert reloaded_p is not None
    assert reloaded_p.metadata.get('consecutive_reuse_failures') == 1
    assert reloaded_p.reusable is True


def test_control_g_pattern_id_without_actions_reuse_does_not_refute(simple_card, repository, learning_service):
    """Control G (NF-IL-01-R1): reusable_pattern_id poblado pero reused_actions_from_pattern=False no cuenta como refutación."""
    # Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={'mode_selection': {}},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # Now execute with pattern_id but actions NOT reused
    task_with_pattern_id_no_actions = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': False,  # Key: not actually reusing actions
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': False}
                )
            ]
        }
    )
    failure_result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure with pattern_id but no action reuse',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_pattern_id_no_actions, result=failure_result
    )

    # Should NOT count as refutation since actions weren't actually reused
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0


def test_control_h_complete_e1_e8_sequence(simple_card, repository, learning_service):
    """Control H: Secuencia completa E1-E8 con intercalación de fallo no relacionado."""
    # E1: Create pattern
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id

    # E2: Reused + failure
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result = ToolResult(
        task_id=task_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure 1',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse, result=failure_result
    )
    assert pattern.metadata.get('consecutive_reuse_failures') == 1

    # E3: Reused + failure again
    task_with_reuse_2 = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result_2 = ToolResult(
        task_id=task_with_reuse_2.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_3',
        success=False,
        output_text='',
        error_message='Failure 2',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse_2, result=failure_result_2
    )
    assert pattern.metadata.get('consecutive_reuse_failures') == 2

    # E4: Unrelated failure (interleaved)
    unrelated_task = task.model_copy(
        update={
            'metadata': {},  # No pattern_id
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',  # SAME target = same signature
                    label='open test url',
                    metadata={}
                )
            ]
        }
    )
    unrelated_failure = ToolResult(
        task_id=unrelated_task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_4',
        success=False,
        output_text='',
        error_message='Unrelated',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=unrelated_task, result=unrelated_failure
    )
    # Critical: consecutive_reuse_failures should remain 2
    assert pattern.metadata.get('consecutive_reuse_failures') == 2

    # E5: Reused + failure again (should reach threshold)
    task_with_reuse_3 = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    failure_result_3 = ToolResult(
        task_id=task_with_reuse_3.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_5',
        success=False,
        output_text='',
        error_message='Failure 3',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_reuse_3, result=failure_result_3
    )
    # E6: Threshold reached
    assert pattern.metadata.get('consecutive_reuse_failures') == 3
    # E7: P.reusable == False
    assert pattern.reusable is False
    assert pattern.metadata.get('invalidated_at_utc') is not None

    # E8: Future selection excludes P (verify via reusable flag)
    # Selector would exclude P because reusable=False
    assert pattern.reusable is False


def test_nf_il_02_identity_survives_signature_change(simple_card, repository, learning_service):
    """
    NF-IL-02: Pattern identity survives materialization signature change.
    
    Demonstrates that execution E derived from pattern P retains identity
    even when materialized operations have different signature than P.
    """
    # Create pattern P with minimal metadata (original signature S1)
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(
                action_type=ToolActionType.OPEN_URL,
                target='http://example.com',
                label='open test url',
                expected_signal='',  # Empty in original pattern
            ),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    original_signature = pattern.signature
    
    # Simulate materialization where signature changes (S2 != S1)
    # This is what _action_from_pattern_step does: adds expected_signal, concrete paths
    materialized_actions = [
        ToolAction(
            action_type=ToolActionType.OPEN_URL,
            target='http://example.com',
            label='open test url',
            expected_signal='page_opened',  # DIFFERENT from original
            metadata={'reused_from_pattern': True}
        )
    ]
    
    # Create task with materialized actions AND correct metadata
    # This simulates what production does via ToolTeachService
    task_with_materialized = task.model_copy(
        update={
            'actions': materialized_actions,
            'metadata': {
                'reused_pattern_id': pattern_id,  # Identity preserved here
                'reused_actions_from_pattern': True,  # Actions actually from pattern
            }
        }
    )
    
    # Calculate signature of materialized execution (S2)
    channel = learning_service._channel_for_tool(simple_card.tool_type)
    normalized_materialized = [learning_service._normalize_action(action, channel) for action in materialized_actions]
    materialized_signature = learning_service._signature_for(
        task=task_with_materialized, card=simple_card, channel=channel, steps=normalized_materialized
    )
    
    # Verify signatures are different
    assert materialized_signature != original_signature, "Materialized signature should differ from original"
    
    # Execute with materialized actions and fail
    failure_result = ToolResult(
        task_id=task_with_materialized.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Simulated failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    # Learn from execution
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_with_materialized, result=failure_result
    )
    
    # VERIFY: Pattern P received negative evidence despite signature difference
    assert updated_pattern.pattern_id == pattern_id, "Should have retrieved original pattern by ID"
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 1, "Negative evidence should be attributed"
    assert updated_pattern.failure_count == 1


def test_nf_il_02_selection_without_actual_reuse(simple_card, repository, learning_service):
    """
    NF-IL-02 Control: Pattern selected but actions provided explicitly.
    
    When reusable_pattern_id exists but actions were not actually reused,
    negative evidence should NOT be attributed to the pattern.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    
    # Caller provides explicit actions (simulating goal_parameters['actions'])
    # but pattern_id is still selected
    task_explicit = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,  # Pattern selected
                'reused_actions_from_pattern': False,  # But NOT actually reused
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='explicit action',
                    metadata={'reused_from_pattern': False}  # Explicit actions
                )
            ]
        }
    )
    
    failure_result = ToolResult(
        task_id=task_explicit.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Explicit action failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_explicit, result=failure_result
    )
    
    # VERIFY: Negative evidence NOT attributed to P
    assert updated_pattern.pattern_id == pattern_id
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0, "Should not count as refutation"


def test_nf_il_02_no_false_fallback(simple_card, repository, learning_service):
    """
    NF-IL-02 Control: No false fallback when signature differs but not actually reused.
    
    When signature differs and reused_pattern_id exists but actions were not
    actually reused, should NOT use ID fallback.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    
    # Execution with different signature, pattern_id present, but NOT actually reused
    task_different = task.model_copy(
        update={
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://different.com',  # Different target = different signature
                    label='different action',
                    metadata={'reused_from_pattern': False}
                )
            ],
            'metadata': {
                'reused_pattern_id': pattern_id,  # Pattern ID present
                'reused_actions_from_pattern': False,  # But NOT actually reused
            }
        }
    )
    
    failure_result = ToolResult(
        task_id=task_different.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Different signature failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_different, result=failure_result
    )
    
    # VERIFY: Should create NEW pattern, not attribute to P
    # Signature lookup fails, ID fallback should NOT happen (actions_actually_reused = False)
    assert updated_pattern.pattern_id != pattern_id, "Should create new pattern, not reuse existing"


def test_nf_il_02_rejects_spoofed_reuse_metadata_with_unrelated_actions(simple_card, repository, learning_service):
    """
    NF-IL-02 Adversarial: Reject spoofed reuse metadata with unrelated actions.
    
    Test FIX #1: Even if metadata is spoofed with reused_pattern_id and
    reused_actions_from_pattern=True, if actual actions don't carry
    reused_from_pattern=True, the pattern should NOT be updated.
    
    This prevents forgery of provenance.
    """
    # Create pattern P (Playwright-like)
    task_p = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task P',
        objective='Test objective P',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(card=simple_card, task=task_p, result=result_p)
    pattern_p_id = pattern_p.pattern_id
    original_operations = pattern_p.operations
    original_failures = pattern_p.failure_count
    original_consecutive_failures = pattern_p.metadata.get('consecutive_reuse_failures', 0)
    
    # Create Shell task with unrelated actions (run_command)
    task_shell = ToolTask(
        tool_id=simple_card.tool_id,
        title='Shell task',
        objective='Shell objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.RUN_COMMAND, target='echo test', label='run command'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={
            # SPOOF: Fake reuse metadata pointing to P
            'reused_pattern_id': pattern_p_id,
            'reused_actions_from_pattern': True,
        },
    )
    
    # Actions do NOT carry reused_from_pattern (actual provenance)
    result_shell = ToolResult(
        task_id=task_shell.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_shell1',
        success=False,
        output_text='',
        error_message='Shell failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_shell, result=result_shell
    )
    
    # VERIFY: P should NOT be updated
    assert updated_pattern.pattern_id != pattern_p_id, \
        "Should create new pattern for different actions, not reuse P"
    
    # Reload P and verify it's unchanged
    reloaded_p = repository.get_interaction_pattern(pattern_p_id)
    assert reloaded_p is not None, "Original pattern P should still exist"
    assert reloaded_p.operations == original_operations, \
        "P operations should not be contaminated with Shell actions"
    assert reloaded_p.failure_count == original_failures, \
        "P failure count should not be incremented"
    assert reloaded_p.metadata.get('consecutive_reuse_failures') == original_consecutive_failures, \
        "P consecutive failures should not be incremented"


def test_nf_il_02_signature_operations_integrity(simple_card, repository, learning_service):
    """
    NF-IL-02: Verify signature ↔ operations integrity after learning.
    
    Test FIX #2: After learning with signature fallback, ensure that
    stored signature matches recomputed signature from stored operations.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    
    # Simulate materialized execution with different signature
    materialized_actions = [
        ToolAction(
            action_type=ToolActionType.OPEN_URL,
            target='http://example.com',
            label='open test url',
            expected_signal='page_opened',  # Different metadata = different signature
            metadata={'reused_from_pattern': True}
        )
    ]
    
    task_reused = task.model_copy(
        update={
            'actions': materialized_actions,
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            }
        }
    )
    
    failure_result = ToolResult(
        task_id=task_reused.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_reused, result=failure_result
    )
    
    # Reload from repository
    reloaded = repository.get_interaction_pattern(pattern_id)
    assert reloaded is not None
    
    # Recompute signature from stored operations
    channel = learning_service._channel_for_tool(simple_card.tool_type)
    recomputed_signature = learning_service._signature_for(
        task=task_reused,
        card=simple_card,
        channel=channel,
        steps=reloaded.operations
    )
    
    # VERIFY: Stored signature should match recomputed signature
    assert reloaded.signature == recomputed_signature, \
        "Stored signature should match recomputed signature from stored operations"
    
    # Verify repository can still locate the pattern
    found_by_signature = repository.get_interaction_pattern_by_signature(reloaded.signature)
    assert found_by_signature is not None, \
        "Pattern should be locatable by its updated signature"
    assert found_by_signature.pattern_id == pattern_id


def test_nf_il_02_success_without_actual_reuse_does_not_reset_refutation(simple_card, repository, learning_service):
    """
    NF-IL-02: Success without actual reuse does not reset refutation.
    
    Test FIX #4: Success should only reset consecutive_reuse_failures
    if there was actual reuse. Mere selection should not reset.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    
    # Accumulate 2 failures with real reuse
    for i in range(2):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'reused_pattern_id': pattern_id,
                    'reused_actions_from_pattern': True,
                },
                'actions': [
                    ToolAction(
                        action_type=ToolActionType.OPEN_URL,
                        target='http://example.com',
                        label='open test url',
                        metadata={'reused_from_pattern': True}
                    )
                ]
            }
        )
        failure_result = ToolResult(
            task_id=task_with_reuse.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message=f'Failure {i+1}',
            execution_ms=100,
            execution_state=ExecutionState(state='failed', detail='Error'),
            validation_status=ToolValidationStatus.UNVALIDATED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )
    
    assert pattern.metadata.get('consecutive_reuse_failures') == 2
    
    # Success WITHOUT actual reuse (only selection)
    task_success_no_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,  # Selected
                'reused_actions_from_pattern': False,  # But NOT actually reused
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': False}
                )
            ]
        }
    )
    success_result = ToolResult(
        task_id=task_success_no_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_4',
        success=True,
        output_text='success',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_success_no_reuse, result=success_result
    )
    
    # VERIFY: Counter should remain 2 (not reset)
    assert pattern.metadata.get('consecutive_reuse_failures') == 2, \
        "Success without actual reuse should not reset consecutive failures"
    
    # Success WITH actual reuse should reset
    task_success_with_reuse = task.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    success_result_2 = ToolResult(
        task_id=task_success_with_reuse.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_5',
        success=True,
        output_text='success',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_success_with_reuse, result=success_result_2
    )
    
    # VERIFY: Counter should now reset to 0
    assert pattern.metadata.get('consecutive_reuse_failures') == 0, \
        "Success with actual reuse should reset consecutive failures"


def test_nf_il_02_rejects_mixed_actions(simple_card, repository, learning_service):
    """
    NF-IL-02 Adversarial P1: Reject mixed actions.
    
    One valid action from P + several unrelated actions.
    Should reject as complete reuse of P.
    """
    # Create pattern P
    task_p = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task P',
        objective='Test objective P',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(card=simple_card, task=task_p, result=result_p)
    pattern_p_id = pattern_p.pattern_id
    original_operations = pattern_p.operations
    original_failures = pattern_p.failure_count
    
    # Task with mixed actions: one from P (reused_from_pattern=True), one unrelated (False)
    task_mixed = ToolTask(
        tool_id=simple_card.tool_id,
        title='Mixed task',
        objective='Mixed objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url', metadata={'reused_from_pattern': True}),
            ToolAction(action_type=ToolActionType.RUN_COMMAND, target='echo test', label='run command', metadata={'reused_from_pattern': False}),
        ],
        metadata={
            'reused_pattern_id': pattern_p_id,
            'reused_actions_from_pattern': True,
        },
    )
    
    result_mixed = ToolResult(
        task_id=task_mixed.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_mixed1',
        success=False,
        output_text='',
        error_message='Mixed failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_mixed, result=result_mixed
    )
    
    # VERIFY: Should NOT attribute to P (mixed actions = not complete reuse due to all() check)
    assert updated_pattern.pattern_id != pattern_p_id, \
        "Should create new pattern for mixed actions, not reuse P"
    
    # Reload P and verify it's unchanged
    reloaded_p = repository.get_interaction_pattern(pattern_p_id)
    assert reloaded_p is not None, "Original pattern P should still exist"
    assert reloaded_p.operations == original_operations, \
        "P operations should not be modified"
    assert reloaded_p.failure_count == original_failures, \
        "P failure count should not be incremented"


def test_nf_il_02_same_tool_wrong_pattern_id_does_not_contaminate(simple_card, repository, learning_service):
    """
    NF-IL-02 Adversarial P2: Same tool, wrong pattern_id.
    
    P and Q have same tool_id but different IDs.
    Task with Q's actions but reused_pattern_id=P should not contaminate P.
    """
    # Create pattern P
    task_p = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task P',
        objective='Test objective P',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site_p',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(card=simple_card, task=task_p, result=result_p)
    pattern_p_id = pattern_p.pattern_id
    original_p_operations = pattern_p.operations
    original_p_failures = pattern_p.failure_count
    original_p_consecutive = pattern_p.metadata.get('consecutive_reuse_failures', 0)
    
    # Create pattern Q (same tool, different site_id = different signature)
    task_q = task_p.model_copy(update={'site_id': 'test_site_q'})
    result_q = result_p.model_copy(update={'result_id': 'result_q1'})
    pattern_q = learning_service.learn_from_execution(card=simple_card, task=task_q, result=result_q)
    pattern_q_id = pattern_q.pattern_id
    
    # Task with Q's actions but reused_pattern_id=P
    task_for_p = task_q.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_p_id,  # Wrong pattern ID
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    
    result_for_p = ToolResult(
        task_id=task_for_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_for_p1',
        success=False,
        output_text='',
        error_message='Failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_for_p, result=result_for_p
    )
    
    # VERIFY: P should remain intact (not contaminated by Q's actions)
    reloaded_p = repository.get_interaction_pattern(pattern_p_id)
    assert reloaded_p is not None, "Pattern P should still exist"
    assert reloaded_p.operations == original_p_operations, \
        "P operations should not be contaminated with Q's actions"
    assert reloaded_p.pattern_id == pattern_p_id, \
        "P identity should be preserved"
    assert reloaded_p.failure_count == original_p_failures, \
        "P failure count should not be incremented"
    assert reloaded_p.metadata.get('consecutive_reuse_failures') == original_p_consecutive, \
        "P consecutive failures should not be incremented"


def test_nf_il_02_post_build_mutation_rejected(simple_card, repository, learning_service):
    """
    NF-IL-02 Adversarial P3: Post-build mutation.
    
    Construct a legitimately reused task, then modify actions incompatibly
    while preserving provenance flags. Learner should reject attribution.
    """
    # Create pattern P
    task_p = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task P',
        objective='Test objective P',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result_p = ToolResult(
        task_id=task_p.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_p1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern_p = learning_service.learn_from_execution(card=simple_card, task=task_p, result=result_p)
    pattern_p_id = pattern_p.pattern_id
    original_operations = pattern_p.operations
    
    # Construct legitimately reused task
    task_reused = task_p.model_copy(
        update={
            'metadata': {
                'reused_pattern_id': pattern_p_id,
                'reused_actions_from_pattern': True,
            },
            'actions': [
                ToolAction(
                    action_type=ToolActionType.OPEN_URL,
                    target='http://example.com',
                    label='open test url',
                    metadata={'reused_from_pattern': True}
                )
            ]
        }
    )
    
    # POST-BUILD MUTATION: modify action incompatibly while preserving flags
    task_reused.actions[0] = ToolAction(
        action_type=ToolActionType.RUN_COMMAND,  # Incompatible operator
        target='echo test',
        label='run command',
        metadata={'reused_from_pattern': True}  # Flag preserved
    )
    
    result_mutation = ToolResult(
        task_id=task_reused.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_mutation1',
        success=False,
        output_text='',
        error_message='Mutation failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_reused, result=result_mutation
    )
    
    # VERIFY: Should NOT attribute to P (incompatible operator detected by structural check)
    assert updated_pattern.pattern_id != pattern_p_id, \
        "Should create new pattern for mutated actions, not reuse P"
    
    # Reload P and verify it's unchanged
    reloaded_p = repository.get_interaction_pattern(pattern_p_id)
    assert reloaded_p is not None, "Original pattern P should still exist"
    assert reloaded_p.operations == original_operations, \
        "P operations should not be modified"


def test_nf_il_02_fallback_does_not_fragment_canonical_pattern(simple_card, repository, learning_service):
    """
    NF-IL-02: Fallback does not fragment canonical pattern.
    
    After fallback with different signature, P should remain the canonical pattern.
    Executing original representation should still find P.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    original_signature = pattern.signature
    original_operations = pattern.operations
    original_success_count = pattern.success_count
    
    # Simulate materialized execution with different signature
    materialized_actions = [
        ToolAction(
            action_type=ToolActionType.OPEN_URL,
            target='http://example.com',
            label='open test url',
            expected_signal='page_opened',  # Different metadata = different signature
            metadata={'reused_from_pattern': True}
        )
    ]
    
    task_materialized = task.model_copy(
        update={
            'actions': materialized_actions,
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            }
        }
    )
    
    failure_result = ToolResult(
        task_id=task_materialized.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_materialized, result=failure_result
    )
    
    # VERIFY: P should still be the canonical pattern
    assert updated_pattern.pattern_id == pattern_id, \
        "Pattern ID should be preserved"
    
    # VERIFY: Canonical signature should be preserved (not changed to materialized)
    assert updated_pattern.signature == original_signature, \
        "Canonical signature should be preserved (not replaced with materialized)"
    
    # VERIFY: Canonical operations should be preserved
    assert updated_pattern.operations == original_operations, \
        "Canonical operations should be preserved (not replaced with materialized)"
    
    # VERIFY: Counters should be updated (evidence)
    assert updated_pattern.success_count == original_success_count, \
        "Success count should be preserved"
    assert updated_pattern.failure_count == 1, \
        "Failure count should be incremented"
    
    # VERIFY: Executing original representation should still find P
    channel = learning_service._channel_for_tool(task.tool_id)
    normalized_original = [learning_service._normalize_action(action, channel) for action in task.actions]
    original_signature_recalc = learning_service._signature_for(
        task=task, card=simple_card, channel=channel, steps=normalized_original
    )
    
    found_by_original_signature = repository.get_interaction_pattern_by_signature(original_signature_recalc)
    assert found_by_original_signature is not None, \
        "Original signature should still locate P"
    assert found_by_original_signature.pattern_id == pattern_id, \
        "Should locate same P by original signature"
    
    # VERIFY: No fragmentation (P' should not exist)
    all_patterns = repository.list_interaction_patterns(limit=100)
    patterns_with_same_id = [p for p in all_patterns if p.pattern_id == pattern_id]
    assert len(patterns_with_same_id) == 1, \
        "Should not create fragmented P' (only one P should exist)"


def test_nf_il_02_signature_operations_integrity_after_fallback(simple_card, repository, learning_service):
    """
    NF-IL-02: Signature/operations integrity after fallback.
    
    Demonstrate that after fallback:
    signature == hash(canonical operations)
    and fallback does not substitute canonical content with materialization.
    """
    # Create pattern P
    task = ToolTask(
        tool_id=simple_card.tool_id,
        title='Test task',
        objective='Test objective',
        requested_by_role=TaskRole.TOOL_USE,
        execution_scope='read_only',
        site_id='test_site',
        actions=[
            ToolAction(action_type=ToolActionType.OPEN_URL, target='http://example.com', label='open test url'),
        ],
        approval_decision=ApprovalDecision.SKIPPED,
        metadata={},
    )
    result = ToolResult(
        task_id=task.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_1',
        success=True,
        output_text='hello',
        error_message='',
        execution_ms=100,
        execution_state=ExecutionState(state='completed', detail='Success'),
        validation_status=ToolValidationStatus.APPROVED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    pattern = learning_service.learn_from_execution(card=simple_card, task=task, result=result)
    pattern_id = pattern.pattern_id
    original_signature = pattern.signature
    original_operations = pattern.operations
    
    # Verify integrity before fallback
    channel = learning_service._channel_for_tool(task.tool_id)
    recomputed_before = learning_service._signature_for(
        task=task, card=simple_card, channel=channel, steps=original_operations
    )
    assert original_signature == recomputed_before, \
        "Canonical signature should hash canonical operations before fallback"
    
    # Execute materialized execution with different signature
    materialized_actions = [
        ToolAction(
            action_type=ToolActionType.OPEN_URL,
            target='http://example.com',
            label='open test url',
            expected_signal='page_opened',
            metadata={'reused_from_pattern': True}
        )
    ]
    
    task_materialized = task.model_copy(
        update={
            'actions': materialized_actions,
            'metadata': {
                'reused_pattern_id': pattern_id,
                'reused_actions_from_pattern': True,
            }
        }
    )
    
    failure_result = ToolResult(
        task_id=task_materialized.task_id,
        tool_id=simple_card.tool_id,
        tool_type=simple_card.tool_type,
        result_id='result_2',
        success=False,
        output_text='',
        error_message='Failure',
        execution_ms=100,
        execution_state=ExecutionState(state='failed', detail='Error'),
        validation_status=ToolValidationStatus.UNVALIDATED,
        rollback_state=ExecutionState(state='none', detail=''),
        extracted_data={},
        artifacts=[],
        metadata={},
    )
    
    updated_pattern = learning_service.learn_from_execution(
        card=simple_card, task=task_materialized, result=failure_result
    )
    
    # Verify integrity after fallback
    recomputed_after = learning_service._signature_for(
        task=task, card=simple_card, channel=channel, steps=updated_pattern.operations
    )
    assert updated_pattern.signature == recomputed_after, \
        "Canonical signature should hash canonical operations after fallback"
    
    # Verify signature did not change
    assert updated_pattern.signature == original_signature, \
        "Canonical signature should remain unchanged after fallback"
    
    # Verify operations did not change
    assert updated_pattern.operations == original_operations, \
        "Canonical operations should remain unchanged after fallback"
