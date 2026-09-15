"""
D2: Double Counting Tests

Tests para verificar que una sola tarea lógica produce exactamente una contribución
de aprendizaje, incluso cuando atraviesa múltiples fases (sandbox preflight + ejecución real).
"""

import pytest
import tempfile
from pathlib import Path

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExecutionState,
    TaskRole,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolResult,
    ToolTask,
    ToolType,
    ToolValidationStatus,
    InferenceRequest,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy


class DeterministicAdapter:
    """Adapter determinista para pruebas D2."""
    def __init__(self, tool_type: ToolType, *, available: bool = True, sandbox_pass: bool = True, real_pass: bool = True) -> None:
        self.tool_type = tool_type
        self.available = available
        self.sandbox_pass = sandbox_pass
        self.real_pass = real_pass

    def is_available(self, card: ToolCard) -> bool:
        return self.available

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, any]:
        if sandbox:
            success = self.sandbox_pass
        else:
            success = self.real_pass
        stage = 'sandbox' if sandbox else 'executed'
        return {
            'success': success,
            'output_text': f'{card.tool_id}:{stage}',
            'extracted_data': {'action_count': len(task.actions)},
            'artifacts': [],
            'error_message': '' if success else f'{stage} failed',
            'execution_ms': 5,
            'metadata': {'sandbox': sandbox, 'tool_id': card.tool_id},
        }

    def set_sandbox_pass(self, value: bool):
        self.sandbox_pass = value

    def set_real_pass(self, value: bool):
        self.real_pass = value


def _create_service(root: Path, *, sandbox_pass: bool = True, real_pass: bool = True) -> tuple[ToolTeachService, ToolRecordRepository]:
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    repo = ToolRecordRepository(db=db, storage=storage)
    adapters = {
        'shell': DeterministicAdapter(ToolType.SHELL, sandbox_pass=sandbox_pass, real_pass=real_pass),
    }
    registry = ToolRegistry(repo, adapters)
    validator = ToolValidator()
    sandbox = ToolSandbox(validator)
    interaction_learning_service = InteractionLearningService(repo)
    mode_selector = InteractionModeSelector(registry, repo)
    memory = ToolMemory(repo, interaction_learning_service)
    approval_policy = ToolApprovalPolicy()
    service = ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=sandbox,
        validator=validator,
        approval_policy=approval_policy,
        rollback_manager=None,
        adapters=adapters,
        workspace_root=str(root),
        interaction_learning_service=interaction_learning_service,
        mode_selector=mode_selector,
        experiment_lab=None,
        live_audit_supervisor=None,
    )
    return service, repo


def test_d2_case_a_sandbox_pass_real_pass_no_double_count():
    """
    D2 Case A: Sandbox PASS + Real PASS → success_count == 1, failure_count == 0
    
    Verifies that a single logical task produces exactly one learning contribution
    even though it passes both sandbox preflight and real execution.
    """
    import shutil
    root = Path(tempfile.mkdtemp(prefix='d2_case_a_'))
    try:
        service, repo = _create_service(root, sandbox_pass=True, real_pass=True)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell Command',
            tool_type=ToolType.SHELL,
            adapter_key='shell',
            description='Test shell tool',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': str(root)},
        )
        repo.save_card(card)

        # Execute one logical task
        request = InferenceRequest(
            user_goal='Ejecutar comando shell',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task = service.build_task_from_request(request)
        result = service.execute_task(task, approved=False)

        # Verify single learning contribution
        patterns = repo.list_interaction_patterns()
        assert len(patterns) == 1, "Should create one pattern for one logical task"
        pattern = patterns[0]
        
        # Case A: success_count must be exactly 1, not 2
        assert pattern.success_count == 1, \
            f"Expected success_count == 1 for single logical task, got {pattern.success_count}"
        assert pattern.failure_count == 0, \
            f"Expected failure_count == 0 for successful task, got {pattern.failure_count}"
        
        # KD-2: Verify ToolCard counters also not double-counted
        card_after = repo.get_card(card.tool_id)
        assert card_after.success_count == 1, \
            f"Expected ToolCard success_count == 1 for single logical task, got {card_after.success_count}"
        assert card_after.failure_count == 0, \
            f"Expected ToolCard failure_count == 0 for successful task, got {card_after.failure_count}"

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_d2_case_b_sandbox_pass_real_fail_no_double_count():
    """
    D2 Case B: Sandbox PASS + Real FAIL → success_count == 0, failure_count == 1
    
    Verifies that a single logical task produces exactly one learning contribution
    even though it passes sandbox preflight but fails real execution.
    """
    import shutil
    root = Path(tempfile.mkdtemp(prefix='d2_case_b_'))
    try:
        service, repo = _create_service(root, sandbox_pass=True, real_pass=False)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell Command',
            tool_type=ToolType.SHELL,
            adapter_key='shell',
            description='Test shell tool',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': str(root)},
        )
        repo.save_card(card)

        # Execute one logical task
        request = InferenceRequest(
            user_goal='Ejecutar comando shell',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task = service.build_task_from_request(request)
        result = service.execute_task(task, approved=False)

        # Verify single learning contribution
        patterns = repo.list_interaction_patterns()
        assert len(patterns) == 1, "Should create one pattern for one logical task"
        pattern = patterns[0]
        
        # Case B: success_count must be 0, failure_count must be 1
        assert pattern.success_count == 0, \
            f"Expected success_count == 0 for failed task, got {pattern.success_count}"
        assert pattern.failure_count == 1, \
            f"Expected failure_count == 1 for single logical task, got {pattern.failure_count}"
        
        # KD-2: Verify ToolCard counters also not double-counted
        card_after = repo.get_card(card.tool_id)
        assert card_after.success_count == 0, \
            f"Expected ToolCard success_count == 0 for failed task, got {card_after.success_count}"
        assert card_after.failure_count == 1, \
            f"Expected ToolCard failure_count == 1 for single logical task, got {card_after.failure_count}"

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_d2_case_c_sandbox_fail_early_return():
    """
    D2 Case C: Sandbox FAIL → early return, no real execution
    
    Documents the current architecture behavior when sandbox preflight fails.
    The task should not proceed to real execution.
    
    D2 decision: Sandbox failure does NOT contribute to learning because
    it is an intermediate observation, not a final experience. The task
    never actually executed, so there is no learning contribution.
    """
    import shutil
    root = Path(tempfile.mkdtemp(prefix='d2_case_c_'))
    try:
        service, repo = _create_service(root, sandbox_pass=False, real_pass=False)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell Command',
            tool_type=ToolType.SHELL,
            adapter_key='shell',
            description='Test shell tool',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': str(root)},
        )
        repo.save_card(card)

        # Execute one logical task
        request = InferenceRequest(
            user_goal='Ejecutar comando shell',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task = service.build_task_from_request(request)
        result = service.execute_task(task, approved=False)

        # D2 decision: Sandbox failure does NOT contribute to learning
        # because it is an intermediate observation, not a final experience
        patterns = repo.list_interaction_patterns()
        assert len(patterns) == 0, \
            "Sandbox failure should NOT create a pattern (intermediate observation, not final experience)"

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_d1_e2e_adversarial_sandbox_pass_real_fail():
    """
    D1 E2E Adversarial: Sandbox PASS + Real FAIL → consecutive_reuse_failures 1 → 2 → 3 → reusable=False
    
    Demuestra que el éxito de sandbox NO borra el fracaso acumulado de la ejecución real.
    Usa el pipeline real de producción con adaptador determinista.
    """
    import shutil
    root = Path(tempfile.mkdtemp(prefix='d1_e2e_'))
    try:
        service, repo = _create_service(root, sandbox_pass=True, real_pass=True)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell Command',
            tool_type=ToolType.SHELL,
            adapter_key='shell',
            description='Test shell tool',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': str(root)},
        )
        repo.save_card(card)

        # Ronda 1: Crear patrón P con éxito
        request1 = InferenceRequest(
            user_goal='Ejecutar comando shell',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task1 = service.build_task_from_request(request1)
        result1 = service.execute_task(task1, approved=False)

        patterns = repo.list_interaction_patterns()
        assert len(patterns) == 1, "Should create one pattern after first execution"
        pattern_p = patterns[0]
        pattern_p_id = pattern_p.pattern_id
        assert pattern_p.reusable is True, "Pattern should be reusable after success"
        assert pattern_p.success_count == 1, "Pattern should have 1 success"
        assert pattern_p.failure_count == 0, "Pattern should have 0 failures"

        # Cambiar adapter a: sandbox PASS, real FAIL
        adapter = service.adapters['shell']
        adapter.set_real_pass(False)

        # Ronda 1: Reutilizar P con sandbox PASS + real FAIL
        request2 = InferenceRequest(
            user_goal='Ejecutar comando shell similar',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task2 = service.build_task_from_request(request2)
        # FIXTURE: Simular que el selector decidió reutilizar P
        task2.metadata['reused_pattern_id'] = pattern_p_id
        task2.metadata['reused_actions_from_pattern'] = True
        for action in task2.actions:
            action.metadata['reused_from_pattern'] = True
        result2 = service.execute_task(task2, approved=False)

        patterns_after_1 = repo.list_interaction_patterns()
        assert len(patterns_after_1) == 1, "Should still have one pattern"
        pattern_p_1 = patterns_after_1[0]
        assert pattern_p_1.pattern_id == pattern_p_id, "Pattern ID should be preserved"
        assert pattern_p_1.metadata.get('consecutive_reuse_failures') == 1, \
            f"Expected consecutive_reuse_failures == 1 after round 1, got {pattern_p_1.metadata.get('consecutive_reuse_failures')}"

        # Ronda 2: Reutilizar P con sandbox PASS + real FAIL
        request3 = InferenceRequest(
            user_goal='Ejecutar comando shell similar',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task3 = service.build_task_from_request(request3)
        task3.metadata['reused_pattern_id'] = pattern_p_id
        task3.metadata['reused_actions_from_pattern'] = True
        for action in task3.actions:
            action.metadata['reused_from_pattern'] = True
        result3 = service.execute_task(task3, approved=False)

        patterns_after_2 = repo.list_interaction_patterns()
        assert len(patterns_after_2) == 1, "Should still have one pattern"
        pattern_p_2 = patterns_after_2[0]
        assert pattern_p_2.pattern_id == pattern_p_id, "Pattern ID should be preserved"
        assert pattern_p_2.metadata.get('consecutive_reuse_failures') == 2, \
            f"Expected consecutive_reuse_failures == 2 after round 2, got {pattern_p_2.metadata.get('consecutive_reuse_failures')}"

        # Ronda 3: Reutilizar P con sandbox PASS + real FAIL
        request4 = InferenceRequest(
            user_goal='Ejecutar comando shell similar',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task4 = service.build_task_from_request(request4)
        task4.metadata['reused_pattern_id'] = pattern_p_id
        task4.metadata['reused_actions_from_pattern'] = True
        for action in task4.actions:
            action.metadata['reused_from_pattern'] = True
        result4 = service.execute_task(task4, approved=False)

        patterns_after_3 = repo.list_interaction_patterns()
        assert len(patterns_after_3) == 1, "Should still have one pattern"
        pattern_p_3 = patterns_after_3[0]
        assert pattern_p_3.pattern_id == pattern_p_id, "Pattern ID should be preserved"
        assert pattern_p_3.metadata.get('consecutive_reuse_failures') == 3, \
            f"Expected consecutive_reuse_failures == 3 after round 3, got {pattern_p_3.metadata.get('consecutive_reuse_failures')}"
        assert pattern_p_3.reusable is False, \
            "Pattern should be reusable=False after 3 consecutive failures"

    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_h1_selector_real_before_after_invalidation():
    """
    H1: Real selector behavior before and after pattern invalidation
    
    Demonstrates:
    1. BEFORE: InteractionModeSelector selects P (reusable=True)
    2. AFTER: InteractionModeSelector does NOT select P (reusable=False)
    
    Uses real selector without fabricating reuse metadata.
    """
    import shutil
    root = Path(tempfile.mkdtemp(prefix='h1_selector_'))
    try:
        service, repo = _create_service(root, sandbox_pass=True, real_pass=True)

        card = ToolCard(
            tool_id='shell_command',
            title='Shell Command',
            tool_type=ToolType.SHELL,
            adapter_key='shell',
            description='Test shell tool',
            available=True,
            success_count=0,
            failure_count=0,
            last_result_id=None,
            last_validated_at_utc=None,
            metadata={'workspace_root': str(root)},
        )
        repo.save_card(card)

        # FASE A: Crear patrón P con éxito
        request_create = InferenceRequest(
            user_goal='ejecutar comando shell get-location',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={
                'tool_id': 'shell_command',
                'command': 'Get-Location',
                'execution_scope': 'read_only',
            },
        )
        task_create = service.build_task_from_request(request_create)
        result_create = service.execute_task(task_create, approved=False)

        patterns = repo.list_interaction_patterns()
        assert len(patterns) == 1, "Should create one pattern after first execution"
        pattern_p = patterns[0]
        pattern_p_id = pattern_p.pattern_id
        assert pattern_p.reusable is True, "Pattern should be reusable after success"
        assert pattern_p.success_count == 1, "Pattern should have 1 success"

        # FASE B: Selector ANTES de invalidación
        selector = service.mode_selector
        decision_before = selector.select(
            request=request_create,
            draft_task=task_create,
        )
        
        # Verificar que el selector selecciona P
        assert decision_before.reusable_pattern_id == pattern_p_id, \
            f"BEFORE: Selector should select P, got reusable_pattern_id={decision_before.reusable_pattern_id}"
        assert decision_before.selected_tool_id == card.tool_id, \
            f"BEFORE: Selector should select the tool, got {decision_before.selected_tool_id}"

        # FASE C: Tres fallos reales
        adapter = service.adapters['shell']
        adapter.set_real_pass(False)

        for i in range(3):
            request_fail = InferenceRequest(
                user_goal='ejecutar comando shell get-location',
                task_role=TaskRole.TOOL_SANDBOX,
                goal_parameters={
                    'tool_id': 'shell_command',
                    'command': 'Get-Location',
                    'execution_scope': 'read_only',
                },
            )
            task_fail = service.build_task_from_request(request_fail)
            # El selector debe decidir reutilizar P naturalmente
            decision_fail = selector.select(request=request_fail, draft_task=task_fail)
            if decision_fail.reusable_pattern_id:
                task_fail.metadata['reused_pattern_id'] = decision_fail.reusable_pattern_id
                task_fail.metadata['reused_actions_from_pattern'] = True
                for action in task_fail.actions:
                    action.metadata['reused_from_pattern'] = True
            result_fail = service.execute_task(task_fail, approved=False)

        # Verificar invalidación
        patterns_after_3 = repo.list_interaction_patterns()
        assert len(patterns_after_3) == 1, "Should still have one pattern"
        pattern_p_3 = patterns_after_3[0]
        assert pattern_p_3.pattern_id == pattern_p_id, "Pattern ID should be preserved"
        assert pattern_p_3.metadata.get('consecutive_reuse_failures') == 3, \
            f"Expected consecutive_reuse_failures == 3, got {pattern_p_3.metadata.get('consecutive_reuse_failures')}"
        assert pattern_p_3.reusable is False, \
            "Pattern should be reusable=False after 3 consecutive failures"

        # FASE D: Selector DESPUÉS de invalidación
        decision_after = selector.select(
            request=request_create,
            draft_task=task_create,
        )
        
        # Verificar que el selector NO selecciona P
        assert decision_after.reusable_pattern_id != pattern_p_id, \
            f"AFTER: Selector should NOT select P, got reusable_pattern_id={decision_after.reusable_pattern_id}"
        assert decision_after.reusable_pattern_id is None, \
            f"AFTER: Selector should return None for reusable_pattern_id, got {decision_after.reusable_pattern_id}"

    finally:
        shutil.rmtree(root, ignore_errors=True)
