"""
D1 FIRST CAUSAL EXPERIMENT: N=1 Baseline reproduction

This test reproduces D1 using REAL components but minimal setup.
Goal: Demonstrate sandbox_pass resets consecutive_reuse_failures in baseline.
"""
import shutil
from pathlib import Path
from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    ToolAction,
    ToolActionType,
    ToolResult,
    ToolTask,
    ToolValidationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService


def _workspace(name: str) -> Path:
    """Workspace temporal para pruebas."""
    import tempfile
    return Path(tempfile.mkdtemp(prefix=f'{name}_'))


def test_d1_baseline_n1_sandbox_reset_bug():
    """
    D1 BASELINE N=1: Reproduce sandbox reset bug using minimal real components.
    
    This test uses real InteractionLearningService and repository but simulates
    the sandbox vs real execution distinction via result.execution_state.sandboxed.
    
    Expected behavior WITHOUT fix:
    - sandbox_pass (sandboxed=True) should reset consecutive_reuse_failures
    - real failure (sandboxed=False) should increment consecutive_reuse_failures
    """
    root = _workspace('d1_baseline_n1')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(root=str(root))
        repository = ToolRecordRepository(db=db, storage=storage)
        learning_service = InteractionLearningService(repository=repository)

        # Create pattern P with verified success
        task = ToolTask(
            tool_id='test_tool',
            title='Test task',
            objective='Test objective',
            requested_by_role='tool_use',
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
            tool_id='test_tool',
            tool_type='shell',
            result_id='result_1',
            success=True,
            output_text='hello',
            error_message='',
            execution_ms=100,
            execution_state=ExecutionState(state='completed', detail='Success', sandboxed=False),
            validation_status=ToolValidationStatus.APPROVED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        
        # Create a card for the test
        from iabv_v15.domain.models import ToolCard, ToolType
        card = ToolCard(
            tool_id='test_tool',
            title='Test Tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            description='Test tool for D1 experiment',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': '/tmp'},
        )
        repository.save_card(card)
        
        pattern = learning_service.learn_from_execution(card=card, task=task, result=result)
        pattern_id = pattern.pattern_id

        # Verify pattern is reusable
        assert pattern.reusable is True
        assert pattern.success_count == 1
        assert pattern.failure_count == 0
        assert pattern.metadata.get('consecutive_reuse_failures') == 0

        # Execute 3 times with: sandbox_pass + real failure
        for i in range(3):
            # Simulate sandbox preflight success
            preflight_result = ToolResult(
                task_id=task.task_id,
                tool_id='test_tool',
                tool_type='shell',
                result_id=f'preflight_{i+1}',
                success=True,
                output_text='preflight passed',
                error_message='',
                execution_ms=50,
                execution_state=ExecutionState(state='sandbox_pass', detail='Preflight passed', sandboxed=True),
                validation_status=ToolValidationStatus.SANDBOX_PASS,
                rollback_state=ExecutionState(state='none', detail=''),
                extracted_data={},
                artifacts=[],
                metadata={},
            )

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

            # Learn from preflight (BASELINE: should reset consecutive)
            learning_service.learn_from_execution(card=card, task=task_with_reuse, result=preflight_result)

            # Reload pattern to check state
            pattern = repository.get_interaction_pattern(pattern_id)
            consecutive_after_preflight = pattern.metadata.get('consecutive_reuse_failures', 0)

            # Simulate real execution failure
            failure_result = ToolResult(
                task_id=task.task_id,
                tool_id='test_tool',
                tool_type='shell',
                result_id=f'failure_{i+1}',
                success=False,
                output_text='',
                error_message=f'Real failure {i+1}',
                execution_ms=100,
                execution_state=ExecutionState(state='failed', detail='Error', sandboxed=False),
                validation_status=ToolValidationStatus.UNVALIDATED,
                rollback_state=ExecutionState(state='none', detail=''),
                extracted_data={},
                artifacts=[],
                metadata={},
            )

            # Learn from real failure (should increment consecutive)
            pattern = learning_service.learn_from_execution(card=card, task=task_with_reuse, result=failure_result)

            # Verify state after real failure
            consecutive = pattern.metadata.get('consecutive_reuse_failures', 0)
            
            # BASELINE EXPECTATION: consecutive may not reach 3 due to sandbox resets
            print(f"Round {i+1}: consecutive_reuse_failures = {consecutive}")

        # BASELINE RESULT: Report actual behavior
        print(f"BASELINE RESULT: consecutive_reuse_failures = {pattern.metadata.get('consecutive_reuse_failures')}")
        print(f"BASELINE RESULT: reusable = {pattern.reusable}")

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_d1_post_fix_n1_sandbox_isolation():
    """
    D1 POST-FIX N=1: Verify sandbox_pass does NOT reset consecutive_reuse_failures.
    
    Expected behavior WITH fix:
    - sandbox_pass (sandboxed=True) should NOT reset consecutive_reuse_failures
    - real failure (sandboxed=False) should increment consecutive_reuse_failures
    - After 3 real failures, consecutive should reach 3 and reusable should be False
    """
    root = _workspace('d1_post_fix_n1')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(root=str(root))
        repository = ToolRecordRepository(db=db, storage=storage)
        learning_service = InteractionLearningService(repository=repository)

        # Create pattern P with verified success
        task = ToolTask(
            tool_id='test_tool',
            title='Test task',
            objective='Test objective',
            requested_by_role='tool_use',
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
            tool_id='test_tool',
            tool_type='shell',
            result_id='result_1',
            success=True,
            output_text='hello',
            error_message='',
            execution_ms=100,
            execution_state=ExecutionState(state='completed', detail='Success', sandboxed=False),
            validation_status=ToolValidationStatus.APPROVED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        
        # Create a card for the test
        from iabv_v15.domain.models import ToolCard, ToolType
        card = ToolCard(
            tool_id='test_tool',
            title='Test Tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            description='Test tool for D1 experiment',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': '/tmp'},
        )
        repository.save_card(card)
        
        pattern = learning_service.learn_from_execution(card=card, task=task, result=result)
        pattern_id = pattern.pattern_id

        # Verify pattern is reusable
        assert pattern.reusable is True
        assert pattern.success_count == 1
        assert pattern.failure_count == 0
        assert pattern.metadata.get('consecutive_reuse_failures') == 0

        # Execute 3 times with: sandbox_pass + real failure
        for i in range(3):
            # Simulate sandbox preflight success
            preflight_result = ToolResult(
                task_id=task.task_id,
                tool_id='test_tool',
                tool_type='shell',
                result_id=f'preflight_{i+1}',
                success=True,
                output_text='preflight passed',
                error_message='',
                execution_ms=50,
                execution_state=ExecutionState(state='sandbox_pass', detail='Preflight passed', sandboxed=True),
                validation_status=ToolValidationStatus.SANDBOX_PASS,
                rollback_state=ExecutionState(state='none', detail=''),
                extracted_data={},
                artifacts=[],
                metadata={},
            )

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

            # Learn from preflight (POST-FIX: should NOT reset consecutive)
            learning_service.learn_from_execution(card=card, task=task_with_reuse, result=preflight_result)

            # Reload pattern to check state
            pattern = repository.get_interaction_pattern(pattern_id)
            consecutive_after_preflight = pattern.metadata.get('consecutive_reuse_failures', 0)

            # Simulate real execution failure
            failure_result = ToolResult(
                task_id=task.task_id,
                tool_id='test_tool',
                tool_type='shell',
                result_id=f'failure_{i+1}',
                success=False,
                output_text='',
                error_message=f'Real failure {i+1}',
                execution_ms=100,
                execution_state=ExecutionState(state='failed', detail='Error', sandboxed=False),
                validation_status=ToolValidationStatus.UNVALIDATED,
                rollback_state=ExecutionState(state='none', detail=''),
                extracted_data={},
                artifacts=[],
                metadata={},
            )

            # Learn from real failure (should increment consecutive)
            pattern = learning_service.learn_from_execution(card=card, task=task_with_reuse, result=failure_result)

            # Verify state after real failure
            consecutive = pattern.metadata.get('consecutive_reuse_failures', 0)
            
            # POST-FIX EXPECTATION: consecutive should increment without reset
            expected_consecutive = i + 1
            assert consecutive == expected_consecutive, \
                f"After round {i+1}, consecutive should be {expected_consecutive}, got {consecutive}"
            print(f"Round {i+1}: consecutive_reuse_failures = {consecutive}")

        # POST-FIX RESULT: Verify invalidation occurred
        assert pattern.reusable is False, "Pattern should be invalid after 3 consecutive failures"
        assert pattern.metadata.get('consecutive_reuse_failures') == 3, "Consecutive failures should be 3"
        assert pattern.metadata.get('invalidated_at_utc') is not None, "Pattern should have invalidation timestamp"
        
        print(f"POST-FIX RESULT: consecutive_reuse_failures = {pattern.metadata.get('consecutive_reuse_failures')}")
        print(f"POST-FIX RESULT: reusable = {pattern.reusable}")

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_d1_real_success_resets_consecutive():
    """
    D1 VERIFY: Real execution success (not sandbox) should still reset consecutive_reuse_failures.
    
    Verify that the fix doesn't break the original reset behavior for real success.
    """
    root = _workspace('d1_real_success_reset')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(root=str(root))
        repository = ToolRecordRepository(db=db, storage=storage)
        learning_service = InteractionLearningService(repository=repository)

        # Create pattern P with verified success
        task = ToolTask(
            tool_id='test_tool',
            title='Test task',
            objective='Test objective',
            requested_by_role='tool_use',
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
            tool_id='test_tool',
            tool_type='shell',
            result_id='result_1',
            success=True,
            output_text='hello',
            error_message='',
            execution_ms=100,
            execution_state=ExecutionState(state='completed', detail='Success', sandboxed=False),
            validation_status=ToolValidationStatus.APPROVED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )
        
        from iabv_v15.domain.models import ToolCard, ToolType
        card = ToolCard(
            tool_id='test_tool',
            title='Test Tool',
            tool_type=ToolType.SHELL,
            adapter_key='test_adapter',
            description='Test tool for D1 experiment',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': '/tmp'},
        )
        repository.save_card(card)
        
        pattern = learning_service.learn_from_execution(card=card, task=task, result=result)
        pattern_id = pattern.pattern_id

        # Accumulate 2 consecutive failures
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
                tool_id='test_tool',
                tool_type='shell',
                result_id=f'failure_{i+1}',
                success=False,
                output_text='',
                error_message=f'Failure {i+1}',
                execution_ms=100,
                execution_state=ExecutionState(state='failed', detail='Error', sandboxed=False),
                validation_status=ToolValidationStatus.UNVALIDATED,
                rollback_state=ExecutionState(state='none', detail=''),
                extracted_data={},
                artifacts=[],
                metadata={},
            )

            pattern = learning_service.learn_from_execution(card=card, task=task_with_reuse, result=failure_result)

        # Verify 2 consecutive failures
        assert pattern.metadata.get('consecutive_reuse_failures') == 2
        assert pattern.reusable is True  # Not yet invalid (threshold is 3)

        # Execute real success (not sandbox) - should reset consecutive
        success_result = ToolResult(
            task_id=task.task_id,
            tool_id='test_tool',
            tool_type='shell',
            result_id='success_reset',
            success=True,
            output_text='real success',
            error_message='',
            execution_ms=100,
            execution_state=ExecutionState(state='completed', detail='Success', sandboxed=False),
            validation_status=ToolValidationStatus.APPROVED,
            rollback_state=ExecutionState(state='none', detail=''),
            extracted_data={},
            artifacts=[],
            metadata={},
        )

        pattern = learning_service.learn_from_execution(card=card, task=task_with_reuse, result=success_result)

        # Verify reset happened
        assert pattern.metadata.get('consecutive_reuse_failures') == 0, \
            "Real execution success should reset consecutive failures"
        assert pattern.reusable is True, "Pattern should remain reusable after reset"
        
        print(f"RESET TEST: consecutive_reuse_failures = {pattern.metadata.get('consecutive_reuse_failures')}")
        print(f"RESET TEST: reusable = {pattern.reusable}")

    finally:
        shutil.rmtree(root, ignore_errors=True)
