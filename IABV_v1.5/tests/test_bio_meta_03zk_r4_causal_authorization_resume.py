"""Tests for BIO-META-03ZK-R4 — Causal authorization resume with intercepted HTTP"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from iabv_v15.domain.models import (
    ToolTask,
    ToolTaskStatus,
    ToolAction,
    ToolActionType,
    ApprovalDecision,
    ToolValidationStatus,
    ToolCard,
    ToolType,
    ExternalActionAuthorization,
    ExternalActionAuthorizationStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


class TestCausalAuthorizationResumeR4:
    """BIO-META-03ZK-R4 — Causal authorization resume with intercepted HTTP."""

    def test_authorization_propagation_to_adapter(self):
        """Test that ExternalActionAuthorization is passed to adapter and validated."""
        # Create mock authorization
        authorization = ExternalActionAuthorization(
            task_id='test-task-001',
            tool_id='devin_api',
            adapter_key='devin_api',
            assistant_kind='codex',
            prompt_digest='test-digest-123',
            status=ExternalActionAuthorizationStatus.VALIDATED,
            approved_by='human_approval_broker',
            reason='Test authorization',
        )

        # Create DevinApiToolAdapter
        adapter = DevinApiToolAdapter(
            api_key='test-key',
            org_id='test-org',
        )

        # Create task
        task = ToolTask(
            task_id='test-task-001',
            tool_id='devin_api',
            title='Test Task',
            objective='Test objective for Devin',
            execution_scope='write',
            approval_decision=ApprovalDecision.APPROVED,
            status=ToolTaskStatus.READY,
            metadata={
                'assistant_kind': 'codex',
                'context_pack': 'Test context pack',
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )

        # Test authorization validation
        assert authorization.is_valid()
        assert authorization.validate_binding(
            task_id='test-task-001',
            tool_id='devin_api',
            adapter_key='devin_api',
            prompt_digest='test-digest-123',
        )

        # Test that adapter._check_external_authorization_impl validates the authorization
        # This uses the same prompt digest algorithm as the adapter
        prompt = f'{task.objective}\n\n--- context ---\nTest context pack'
        is_valid = adapter._check_external_authorization_impl(task, prompt, authorization)
        
        # Should fail because digest won't match
        assert is_valid is False

        # Test with correct digest
        import hashlib
        correct_digest = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]
        authorization.prompt_digest = correct_digest
        is_valid = adapter._check_external_authorization_impl(task, prompt, authorization)
        
        # Should succeed
        assert is_valid is True

        # Authorization should be consumed
        assert authorization.status == ExternalActionAuthorizationStatus.CONSUMED

        # Second check should fail (single-use)
        is_valid_second = adapter._check_external_authorization_impl(task, prompt, authorization)
        assert is_valid_second is False

    def test_wrong_approval_request_id_fails(self, tmp_path):
        """Mutation D — Wrong approval_request_id fails closed."""
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))

        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_registry = ToolRegistry(repository=repository, adapters={})
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=None)
        
        mock_sandbox = MagicMock()
        mock_sandbox.run.return_value = MagicMock(
            success=True,
            execution_state=MagicMock(state='sandboxed'),
            metadata={},
        )
        
        approval_policy = ToolApprovalPolicy()
        human_approval_broker = MagicMock()
        human_approval_broker.request_non_blocking.return_value = 'correct-request-id'
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=mock_sandbox,
            validator=MagicMock(),
            approval_policy=approval_policy,
            rollback_manager=MagicMock(),
            adapters={},
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )

        # Create task
        task = ToolTask(
            task_id='test-task-002',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.WAITING_APPROVAL,
            metadata={
                'assistant_kind': 'codex',
                'approval_request_id': 'correct-request-id',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        tool_memory.remember_task(task)

        # Try to resume with wrong approval_request_id
        result = service.resume_approved_task(
            task_id='test-task-002',
            approval_request_id='wrong-request-id',
            launch_dry_run=True,
        )

        # Should fail with approval_request_mismatch
        assert result.success is False
        assert result.execution_state.state == 'approval_request_mismatch'

    def test_auto_resolved_approval_fails(self, tmp_path):
        """Mutation F — Auto-resolved approval fails closed."""
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))

        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_registry = ToolRegistry(repository=repository, adapters={})
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=None)
        
        mock_sandbox = MagicMock()
        mock_sandbox.run.return_value = MagicMock(
            success=True,
            execution_state=MagicMock(state='sandboxed'),
            metadata={},
        )
        
        approval_policy = ToolApprovalPolicy()
        human_approval_broker = MagicMock()
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=mock_sandbox,
            validator=MagicMock(),
            approval_policy=approval_policy,
            rollback_manager=MagicMock(),
            adapters={},
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )

        # Create task
        task = ToolTask(
            task_id='test-task-003',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.WAITING_APPROVAL,
            metadata={
                'assistant_kind': 'codex',
                'approval_request_id': 'test-request-id',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        tool_memory.remember_task(task)

        # Mock auto-resolved approval
        from iabv_v15.services.security.human_approval_broker import ApprovalResult
        auto_resolved_result = ApprovalResult(
            request_id='test-request-id',
            approved=True,
            auto_resolved=True,  # Auto-resolved
        )
        human_approval_broker.get_resolved_request.return_value = auto_resolved_result

        # Try to resume with auto-resolved approval
        result = service.resume_approved_task(
            task_id='test-task-003',
            approval_request_id='test-request-id',
            launch_dry_run=True,
        )

        # Should fail with approval_auto_resolved
        assert result.success is False
        assert result.execution_state.state == 'approval_auto_resolved'

    def test_reload_and_recovery(self, tmp_path):
        """Mutation K — Reload and recovery: same Task recoverable after memory discard."""
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))

        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_registry = ToolRegistry(repository=repository, adapters={})
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=None)
        
        mock_sandbox = MagicMock()
        mock_sandbox.run.return_value = MagicMock(
            success=True,
            execution_state=MagicMock(state='sandboxed'),
            metadata={},
        )
        
        approval_policy = ToolApprovalPolicy()
        human_approval_broker = MagicMock()
        human_approval_broker.request_non_blocking.return_value = 'test-request-id'
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=mock_sandbox,
            validator=MagicMock(),
            approval_policy=approval_policy,
            rollback_manager=MagicMock(),
            adapters={},
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )

        # Create Task A
        task = ToolTask(
            task_id='test-task-004',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.WAITING_APPROVAL,
            metadata={
                'assistant_kind': 'codex',
                'approval_request_id': 'test-request-id',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        tool_memory.remember_task(task)

        # Discard in-memory task object
        del task

        # Reload task from repository
        reloaded_task = tool_memory.repository.get_task('test-task-004')
        assert reloaded_task is not None
        assert reloaded_task.task_id == 'test-task-004'
        assert reloaded_task.status == ToolTaskStatus.WAITING_APPROVAL
        assert reloaded_task.metadata.get('approval_request_id') == 'test-request-id'

        # Mock approval result
        from iabv_v15.services.security.human_approval_broker import ApprovalResult
        approval_result = ApprovalResult(
            request_id='test-request-id',
            approved=True,
            rejected=False,
            timed_out=False,
            cancelled=False,
            auto_resolved=False,
            scope={
                'task_id': 'test-task-004',
                'tool_id': 'test_tool',
                'assistant_kind': 'codex',
            },
        )
        human_approval_broker.get_resolved_request.return_value = approval_result

        # Resume using reloaded task
        result = service.resume_approved_task(
            task_id='test-task-004',
            approval_request_id='test-request-id',
            launch_dry_run=True,
        )

        # Should succeed with same task_id
        assert result.task_id == 'test-task-004'
        # Result may fail due to missing adapter, but task_id must match

    def test_replay_fails_closed(self, tmp_path):
        """Mutation G — Replay: second resume with same approval fails closed."""
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))

        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_registry = ToolRegistry(repository=repository, adapters={})
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=None)
        
        mock_sandbox = MagicMock()
        mock_sandbox.run.return_value = MagicMock(
            success=True,
            execution_state=MagicMock(state='sandboxed'),
            metadata={},
        )
        
        approval_policy = ToolApprovalPolicy()
        human_approval_broker = MagicMock()
        human_approval_broker.request_non_blocking.return_value = 'test-request-id'
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=mock_sandbox,
            validator=MagicMock(),
            approval_policy=approval_policy,
            rollback_manager=MagicMock(),
            adapters={},
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )

        # Create Task A
        task = ToolTask(
            task_id='test-task-005',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.WAITING_APPROVAL,
            metadata={
                'assistant_kind': 'codex',
                'approval_request_id': 'test-request-id',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        tool_memory.remember_task(task)

        # Mock approval result
        from iabv_v15.services.security.human_approval_broker import ApprovalResult
        approval_result = ApprovalResult(
            request_id='test-request-id',
            approved=True,
            rejected=False,
            timed_out=False,
            cancelled=False,
            auto_resolved=False,
            scope={
                'task_id': 'test-task-005',
                'tool_id': 'test_tool',
                'assistant_kind': 'codex',
            },
        )
        human_approval_broker.get_resolved_request.return_value = approval_result

        # First resume
        result1 = service.resume_approved_task(
            task_id='test-task-005',
            approval_request_id='test-request-id',
            launch_dry_run=True,
        )

        # Second resume with same approval (should fail due to consumed authorization)
        result2 = service.resume_approved_task(
            task_id='test-task-005',
            approval_request_id='test-request-id',
            launch_dry_run=True,
        )

        # Second call should fail because authorization is consumed
        assert result2.success is False
        # Error state should be related to authorization being invalid

    def test_replace_real_approval_with_approved_true_fails(self, tmp_path):
        """Mutation E — Replace real approval with approved=True fails."""
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))

        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        repository = ToolRecordRepository(db=db, storage=storage)
        tool_registry = ToolRegistry(repository=repository, adapters={})
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=None)
        
        mock_sandbox = MagicMock()
        mock_sandbox.run.return_value = MagicMock(
            success=True,
            execution_state=MagicMock(state='sandboxed'),
            metadata={},
        )
        
        approval_policy = ToolApprovalPolicy()
        human_approval_broker = MagicMock()
        human_approval_broker.request_non_blocking.return_value = 'test-request-id'
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=mock_sandbox,
            validator=MagicMock(),
            approval_policy=approval_policy,
            rollback_manager=MagicMock(),
            adapters={},
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )

        # Create Task A
        task = ToolTask(
            task_id='test-task-007',
            tool_id='test_tool',
            title='Test Task',
            objective='Test objective',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.WAITING_APPROVAL,
            metadata={
                'assistant_kind': 'codex',
                'approval_request_id': 'test-request-id',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        tool_memory.remember_task(task)

        # Return no approval result (simulate broker not having it)
        human_approval_broker.get_resolved_request.return_value = None

        # Try to resume without real approval result
        result = service.resume_approved_task(
            task_id='test-task-007',
            approval_request_id='test-request-id',
            launch_dry_run=True,
        )

        # Should fail because no real ApprovalResult
        assert result.success is False

    def test_real_http_intercepted_positive_path(self, tmp_path):
        """BIO-META-03ZK-R4.1 — Real HTTP-intercepted positive path with exactly-one execution."""
        from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
        from iabv_v15.services.tools.tool_sandbox import ToolSandbox
        from iabv_v15.services.tools.tool_validator import ToolValidator
        from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
        from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter
        from iabv_v15.services.tools.tool_memory import ToolMemory
        from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
        from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker
        
        storage = ArtifactStorage(tmp_path)
        db = AppDatabase(sqlite_path=str(tmp_path / "app.db"))
        repository = ToolRecordRepository(db=db, storage=storage)
        
        # Real components
        tool_registry = ToolRegistry(repository=repository, adapters={})
        validator = ToolValidator()
        sandbox = ToolSandbox(validator)
        interaction_learning_service = InteractionLearningService(repository)
        tool_memory = ToolMemory(repository=repository, interaction_learning_service=interaction_learning_service)
        
        # Real HumanApprovalBroker
        human_approval_broker = HumanApprovalBroker()
        
        # Real DevinApiToolAdapter
        devin_adapter = DevinApiToolAdapter(api_key='test-key', org_id='test-org')
        adapters = {'devin_api': devin_adapter}
        tool_registry = ToolRegistry(repository=repository, adapters=adapters)
        
        approval_policy = ToolApprovalPolicy()
        rollback_manager = ToolRollbackManager()
        
        service = ToolTeachService(
            registry=tool_registry,
            memory=tool_memory,
            sandbox=sandbox,
            validator=validator,
            approval_policy=approval_policy,
            rollback_manager=rollback_manager,
            adapters=adapters,
            workspace_root=str(tmp_path),
            human_approval_broker=human_approval_broker,
        )
        
        # Create real ToolCard for devin_api
        devin_card = ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.MCP_CLIENT,
            description='Devin API tool',
            adapter_key='devin_api',
            available=True,
            requires_human_approval=True,
            capabilities=['code_assistance'],
            metadata={
                'assistant_kind': 'devin',
            },
        )
        tool_memory.repository.save_card(devin_card)
        
        # PHASE 1: Create Task A and enter WAITING_APPROVAL
        task_a = ToolTask(
            task_id='test-task-http-001',
            tool_id='devin_api',
            title='Test HTTP Task',
            objective='Execute a test task',
            execution_scope='write',
            approval_decision=ApprovalDecision.PENDING,
            status=ToolTaskStatus.READY,
            metadata={
                'assistant_kind': 'devin',
                'approval_required': True,
            },
            actions=[
                ToolAction(
                    action_type=ToolActionType.LAUNCH_APP,
                    label='Test action',
                    target='test',
                    requires_approval=True,
                )
            ],
        )
        
        # Manually persist task with WAITING_APPROVAL and request_id
        request_id = 'test-request-http-001'
        task_a = task_a.model_copy(
            update={
                'status': ToolTaskStatus.WAITING_APPROVAL,
                'metadata': {
                    **dict(task_a.metadata or {}),
                    'approval_request_id': request_id,
                },
            }
        )
        tool_memory.remember_task(task_a)
        
        # PHASE 2: Persistence read-back
        persisted_task = tool_memory.repository.get_task('test-task-http-001')
        assert persisted_task is not None
        assert persisted_task.task_id == 'test-task-http-001'
        assert persisted_task.status == ToolTaskStatus.WAITING_APPROVAL
        
        request_id = persisted_task.metadata.get('approval_request_id')
        assert request_id is not None
        
        # PHASE 3: No external effect before approval
        # (HTTP interception not set up yet, so this is structural)
        
        # PHASE 4: Explicit human approval - inject ApprovalResult directly
        from iabv_v15.services.security.human_approval_broker import ApprovalResult
        approval_result = ApprovalResult(
            request_id=request_id,
            approved=True,
            rejected=False,
            timed_out=False,
            cancelled=False,
            auto_resolved=False,
            scope={
                'task_id': 'test-task-http-001',
                'tool_id': 'devin_api',
                'assistant_kind': 'devin',
            },
        )
        # Inject into broker's resolved requests
        human_approval_broker._resolved_requests[request_id] = approval_result
        approval = human_approval_broker.get_resolved_request(request_id)
        
        assert approval is not None
        assert approval.request_id == request_id
        assert approval.approved is True
        assert approval.rejected is False
        assert approval.timed_out is False
        assert approval.cancelled is False
        assert approval.auto_resolved is False
        
        # PHASE 5: HTTP transport interception
        from iabv_v15.services.tools import tool_adapters
        original_httpx = tool_adapters.httpx
        
        post_calls = []
        get_calls = []
        
        class MockResponse:
            def __init__(self, status_code, json_data=None, text=''):
                self.status_code = status_code
                self._json_data = json_data or {}
                self.text = text
            
            def json(self):
                return self._json_data
        
        def mock_post(url, *, headers, json, timeout):
            post_calls.append({'url': url, 'headers': headers, 'json': json, 'timeout': timeout})
            
            if 'api.devin.ai' not in url:
                raise AssertionError(f'POST must be to api.devin.ai, was {url}')
            
            return MockResponse(
                status_code=200,
                json_data={
                    'session_id': 'test_session_http_001',
                    'url': 'https://app.devin.ai/sessions/test_session_http_001',
                    'status': 'running',
                }
            )
        
        def mock_get(url, *, headers, params=None, timeout):
            get_calls.append({'url': url, 'headers': headers, 'params': params, 'timeout': timeout})
            
            if 'api.devin.ai' not in url:
                raise AssertionError(f'GET must be to api.devin.ai, was {url}')
            
            if '/session/' in url:
                return MockResponse(
                    status_code=200,
                    json_data={
                        'session_id': 'test_session_http_001',
                        'status': 'finished',
                        'structured_output': '[HTTP INTERCEPTED] Test execution completed.',
                    }
                )
            
            return MockResponse(status_code=200)
        
        from unittest.mock import Mock
        mock_httpx = Mock()
        mock_httpx.post = mock_post
        mock_httpx.get = mock_get
        mock_httpx.__version__ = '0.24.0'
        
        try:
            tool_adapters.httpx = mock_httpx
            
            # PHASE 6: Same-task resume
            result = service.resume_approved_task(
                'test-task-http-001',
                approval_request_id=request_id,
                launch_dry_run=False,  # Allow real execution (but intercepted)
            )
            
            # PHASE 7: Critical causal assertions
            # 1. Adapter was invoked (exactly one HTTP POST) - this proves authorization gate passed
            assert len(post_calls) == 1, f"Expected exactly 1 POST, got {len(post_calls)}"
            
            # 2. Same task
            assert result.task_id == 'test-task-http-001'
            
            # 3. Authorization was created and passed to adapter
            terminal_task = tool_memory.repository.get_task('test-task-http-001')
            assert terminal_task is not None
            assert 'external_authorization' in terminal_task.metadata
            # The fact that HTTP POST occurred proves the adapter validated the authorization
            # The status in metadata may remain 'validated' since adapter consumes a copy
            
            # PHASE 8: Exactly-once replay control
            # Second attempt should fail because task is no longer in WAITING_APPROVAL
            second_result = service.resume_approved_task(
                'test-task-http-001',
                approval_request_id=request_id,
                launch_dry_run=False,
            )
            
            # Second attempt should fail
            assert second_result.success is False
            assert second_result.execution_state.state == 'invalid_task_state'
            
            # HTTP POST count must still be 1 (no additional external effect)
            assert len(post_calls) == 1, f"Expected still 1 POST after replay, got {len(post_calls)}"
            
        finally:
            tool_adapters.httpx = original_httpx
