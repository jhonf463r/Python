"""NF-IL-01: Invalidación de conocimiento por refutación experiencial.

Este test demuestra:
learned pattern P
    ↓
reuse P
    ↓
refuting experience
    ↓
invalidate P
    ↓
future non-reuse P
"""

import tempfile
from pathlib import Path

import pytest

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    InteractionPattern,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        yield Path(tmp)


@pytest.fixture
def repository(temp_workspace):
    temp_workspace.mkdir(parents=True, exist_ok=True)
    (temp_workspace / 'tool_teaching').mkdir(parents=True, exist_ok=True)
    db = AppDatabase(str(temp_workspace / 'app.sqlite'))
    storage = ArtifactStorage(str(temp_workspace / 'tool_teaching'))
    repo = ToolRecordRepository(db, storage)
    yield repo


@pytest.fixture
def simple_card(repository):
    card = ToolCard(
        tool_id='test_pattern_tool',
        title='Test Pattern Tool',
        tool_type=ToolType.SHELL,
        adapter_key='shell_adapter',
        available=True,
        success_count=0,
        failure_count=0,
        metadata={'workspace_root': '/tmp'},
    )
    repository.save_card(card)
    return card


@pytest.fixture
def learning_service(repository):
    return InteractionLearningService(repository=repository)


def test_e1_create_knowledge(simple_card, repository, learning_service):
    """E1: Crear conocimiento - ejecución exitosa produce patrón P con success_count > 0."""
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

    assert pattern.success_count == 1
    assert pattern.failure_count == 0
    assert pattern.reusable is True

    # Verify pattern persists
    saved = repository.get_interaction_pattern_by_signature(pattern.signature)
    assert saved is not None
    assert saved.success_count == 1
    assert saved.reusable is True


def test_e2_reuse_tracking(simple_card, repository, learning_service):
    """E2: Reutilizar - metadata contiene reusable_pattern_id cuando se reutiliza."""
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

    # Execute with reusable_pattern_id in metadata
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'mode_selection': {
                    'reusable_pattern_id': pattern_id,
                    'reusable_episode_id': '',
                    'equivalent_pattern_exists': True,
                }
            }
        }
    )
    result2 = ToolResult(
        task_id=task.task_id,
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
        card=simple_card, task=task_with_reuse, result=result2
    )

    assert updated_pattern.success_count == 2
    assert updated_pattern.failure_count == 0


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

    # Now execute with reusable_pattern_id in metadata and fail
    task_with_reuse = task.model_copy(
        update={
            'metadata': {
                'mode_selection': {
                    'reusable_pattern_id': pattern_id,
                    'reusable_episode_id': '',
                    'equivalent_pattern_exists': True,
                }
            }
        }
    )
    failure_result = ToolResult(
        task_id=task.task_id,
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

    # Threshold is 3 consecutive failures after reuse
    THRESHOLD = 3

    for i in range(THRESHOLD):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'mode_selection': {
                        'reusable_pattern_id': pattern_id,
                        'reusable_episode_id': '',
                        'equivalent_pattern_exists': True,
                    }
                }
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
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
        pattern = learning_service.learn_from_execution(
            card=simple_card, task=task_with_reuse, result=failure_result
        )

    # After threshold, pattern should be invalidated
    assert pattern.failure_count >= THRESHOLD
    assert pattern.reusable is False
    assert pattern.metadata.get('consecutive_reuse_failures') == THRESHOLD
    assert pattern.metadata.get('invalidated_at_utc') is not None


def test_e5_future_selection_ignores_invalidated_pattern(simple_card, repository, learning_service):
    """E5: Nueva selección - patrón invalidado no se considera en selector."""
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

    # Invalidate with 3 failures
    THRESHOLD = 3
    for i in range(THRESHOLD):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'mode_selection': {
                        'reusable_pattern_id': pattern_id,
                        'reusable_episode_id': '',
                        'equivalent_pattern_exists': True,
                    }
                }
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
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
        metadata={'mode_selection': {}},
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

    assert pattern.success_count == 0
    assert pattern.reusable is True  # Still True initially


def test_control_b_unrelated_failure(simple_card, repository, learning_service):
    """Control B: Fallo no relacionado (sin reutilización) no invalida patrón."""
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

    # Execute without reusable_pattern_id (not reusing the pattern)
    task_without_reuse = task.model_copy(
        update={
            'metadata': {
                'mode_selection': {
                    'reusable_pattern_id': '',
                    'reusable_episode_id': '',
                    'equivalent_pattern_exists': False,
                }
            }
        }
    )
    failure_result = ToolResult(
        task_id=task.task_id,
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
        card=simple_card, task=task_without_reuse, result=failure_result
    )

    # Pattern should still be reusable
    assert updated_pattern.reusable is True
    # Failure count may increment globally, but consecutive_reuse_failures should be 0
    assert updated_pattern.metadata.get('consecutive_reuse_failures') == 0


def test_control_c_same_pattern_refutation(simple_card, repository, learning_service):
    """Control C: Fallos repetidos con reusable_pattern_id == P invalidan P."""
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

    # Fail with reusable_pattern_id == P
    THRESHOLD = 3
    for i in range(THRESHOLD):
        task_with_reuse = task.model_copy(
            update={
                'metadata': {
                    'mode_selection': {
                        'reusable_pattern_id': pattern_id,
                        'reusable_episode_id': '',
                        'equivalent_pattern_exists': True,
                    }
                }
            }
        )
        failure_result = ToolResult(
            task_id=task.task_id,
            tool_id=simple_card.tool_id,
            tool_type=simple_card.tool_type,
            result_id=f'result_{i+2}',
            success=False,
            output_text='',
            error_message='Pattern refutation failure',
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
    assert pattern.metadata.get('consecutive_reuse_failures') == THRESHOLD
