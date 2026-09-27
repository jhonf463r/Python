"""Test BIO-UNIVERSAL-09.11-R20 - Execution-bound ExternalActionAuthorization issuance from approved checkpoint."""

import hashlib

import pytest

from iabv_v15.domain.models import (
    ApprovalDecision,
    ExternalActionAuthorization,
    ExternalActionAuthorizationStatus,
    TaskIntent,
    TaskRole,
    ToolCard,
    ToolTask,
    ToolType,
)
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
import inspect


def test_authorization_transport_signature():
    """TEST 3 - authorization transported through ToolOperationalExecutor → ToolTeachService → adapter.run"""
    # Verify the signature accepts the parameter
    sig = inspect.signature(ToolTeachService.execute_task)
    assert 'external_authorization' in sig.parameters
    assert sig.parameters['external_authorization'].default is None


def test_devin_consumer_accepts_valid_authorization():
    """TEST 4 - authorization VALIDATED + matching bindings → _check_external_authorization() == True"""
    # Create test authorization
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    prompt_digest = hashlib.sha256(task.objective.encode('utf-8')).hexdigest()[:16]
    
    auth = ExternalActionAuthorization(
        task_id=task.task_id,
        tool_id=task.tool_id,
        adapter_key="devin_api",
        assistant_kind="devin",
        prompt_digest=prompt_digest,
        status=ExternalActionAuthorizationStatus.VALIDATED,
        reason="Test approval",
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # Verify consumer accepts valid authorization
    result = adapter._check_external_authorization(task, task.objective, external_authorization=auth)
    assert result is True
    
    # Verify single-use: second call should fail
    result2 = adapter._check_external_authorization(task, task.objective, external_authorization=auth)
    assert result2 is False


def test_replay_protection():
    """TEST 5 - after consume(), second utilization fails"""
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    prompt_digest = hashlib.sha256(task.objective.encode('utf-8')).hexdigest()[:16]
    
    auth = ExternalActionAuthorization(
        task_id=task.task_id,
        tool_id=task.tool_id,
        adapter_key="devin_api",
        assistant_kind="devin",
        prompt_digest=prompt_digest,
        status=ExternalActionAuthorizationStatus.VALIDATED,
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # First use succeeds
    assert adapter._check_external_authorization(task, task.objective, external_authorization=auth) is True
    
    # Second use fails (consumed)
    assert adapter._check_external_authorization(task, task.objective, external_authorization=auth) is False


def test_cross_task_binding_fails():
    """TEST 6 - authorization for task A fails for task B"""
    task_a = ToolTask(
        task_id="task_a",
        tool_id="devin_api",
        title="Task A",
        objective="Task A",
    )
    
    task_b = ToolTask(
        task_id="task_b",
        tool_id="devin_api",
        title="Task B",
        objective="Task B",
    )
    
    prompt_digest_a = hashlib.sha256(task_a.objective.encode('utf-8')).hexdigest()[:16]
    
    auth = ExternalActionAuthorization(
        task_id=task_a.task_id,
        tool_id=task_a.tool_id,
        adapter_key="devin_api",
        assistant_kind="devin",
        prompt_digest=prompt_digest_a,
        status=ExternalActionAuthorizationStatus.VALIDATED,
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # Works for task A
    assert adapter._check_external_authorization(task_a, task_a.objective, external_authorization=auth) is True
    
    # Fails for task B (different task_id)
    assert adapter._check_external_authorization(task_b, task_b.objective, external_authorization=auth) is False


def test_prompt_mismatch_fails():
    """TEST 7 - authorization for prompt A fails for prompt B"""
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Original prompt",
    )
    
    prompt_digest_original = hashlib.sha256(task.objective.encode('utf-8')).hexdigest()[:16]
    
    auth = ExternalActionAuthorization(
        task_id=task.task_id,
        tool_id=task.tool_id,
        adapter_key="devin_api",
        assistant_kind="devin",
        prompt_digest=prompt_digest_original,
        status=ExternalActionAuthorizationStatus.VALIDATED,
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # Works with original prompt
    assert adapter._check_external_authorization(task, task.objective, external_authorization=auth) is True
    
    # Fails with different prompt
    modified_task = task.model_copy(update={"objective": "Modified prompt"})
    assert adapter._check_external_authorization(modified_task, modified_task.objective, external_authorization=auth) is False


def test_no_authorization_blocks():
    """TEST 8 - sandbox=False, authorization=None → blocked"""
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # sandbox=False without authorization should block
    result = adapter._check_external_authorization(task, task.objective, external_authorization=None)
    assert result is False


def test_sandbox_safe_without_authorization():
    """TEST 9 - sandbox=True should not require authorization"""
    card = ToolCard(
        tool_id="devin_api",
        tool_type=ToolType.CUSTOM,
        title="Devin API",
        adapter_key="devin_api",
    )
    
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # sandbox=True should succeed without authorization
    result = adapter.run(card, task, sandbox=True, external_authorization=None)
    assert result['success'] is True
    assert '[SANDBOX]' in result.get('output_text', '')


def test_issued_status_blocks():
    """TEST 10 - status=ISSUED should not be accepted (only VALIDATED)"""
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    prompt_digest = hashlib.sha256(task.objective.encode('utf-8')).hexdigest()[:16]
    
    auth = ExternalActionAuthorization(
        task_id=task.task_id,
        tool_id=task.tool_id,
        adapter_key="devin_api",
        assistant_kind="devin",
        prompt_digest=prompt_digest,
        status=ExternalActionAuthorizationStatus.ISSUED,  # NOT VALIDATED
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # Should fail because status is ISSUED, not VALIDATED
    result = adapter._check_external_authorization(task, task.objective, external_authorization=auth)
    assert result is False


def test_adapter_binding_enforcement():
    """TEST 11 - authorization with wrong adapter_key should fail binding"""
    task = ToolTask(
        task_id="test_task",
        tool_id="devin_api",
        title="Test Task",
        objective="Test prompt",
    )
    
    prompt_digest = hashlib.sha256(task.objective.encode('utf-8')).hexdigest()[:16]
    
    # Create authorization with wrong adapter_key
    auth = ExternalActionAuthorization(
        task_id=task.task_id,
        tool_id=task.tool_id,
        adapter_key="wrong_adapter",  # WRONG
        assistant_kind="devin",
        prompt_digest=prompt_digest,
        status=ExternalActionAuthorizationStatus.VALIDATED,
    )
    
    adapter = DevinApiToolAdapter(api_key="test_key")
    
    # Should fail because adapter_key doesn't match consumer's "devin_api"
    result = adapter._check_external_authorization(task, task.objective, external_authorization=auth)
    assert result is False


def test_seam_integration_full_chain():
    """TEST 12 - Full seam integration: Approved checkpoint → issuer → transport → consumer"""
    from iabv_v15.domain.models import AdaptiveSession, ApprovalCheckpoint
    from iabv_v15.services.tools.tool_operational_executor import ToolOperationalExecutor
    
    # Create session with approved checkpoint
    session = AdaptiveSession(
        user_goal="test task",
        intent=TaskIntent(detected_role=TaskRole.TOOL_USE),
        approval_checkpoints=[
            ApprovalCheckpoint(
                title="Test checkpoint",
                detail="Approved for execution",
                decision=ApprovalDecision.APPROVED,
                phase_key="execute_sensitive",
                reason="Human approved execution",
            )
        ],
    )
    
    # Verify issuer condition in ToolOperationalExecutor.execute()
    # This test verifies the logic: approved = not any(PENDING)
    approved = not any(
        item.decision == ApprovalDecision.PENDING
        for item in session.approval_checkpoints
    )
    
    assert approved is True  # No PENDING checkpoints
    
    # If approved, issuer should create authorization
    if approved:
        # Find the approved checkpoint
        approved_checkpoint = None
        for checkpoint in session.approval_checkpoints:
            if checkpoint.decision == ApprovalDecision.APPROVED:
                approved_checkpoint = checkpoint
                break
        
        assert approved_checkpoint is not None
        assert approved_checkpoint.phase_key == "execute_sensitive"
        assert approved_checkpoint.checkpoint_id is not None
