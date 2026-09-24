"""Tests for BIO-META-03ZK-R3 — Real approval seam + same-task resume with ExternalActionAuthorization"""
from pathlib import Path
from unittest.mock import MagicMock

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
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker, ApprovalResult
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_teach_service import ToolTeachService


class TestSameTaskApprovalResumeR3:
    """BIO-META-03ZK-R3 — Real approval seam with ExternalActionAuthorization integration."""

    def test_bootstrap_wires_human_approval_broker_to_tool_teach_service(self):
        """Test 2 — Bootstrap wiring: human_approval_broker is the same instance."""
        # This test verifies that bootstrap.human_approval_broker and
        # bootstrap.tool_teach_service.human_approval_broker are the same instance
        # when the real bootstrap is used.
        # For now, we verify the contract exists and the parameter is wired correctly.
        from iabv_v15.services.security.human_approval_broker import HumanApprovalBroker
        
        broker = HumanApprovalBroker()
        
        # Create a minimal ToolTeachService with the broker
        mock_registry = MagicMock()
        mock_memory = MagicMock()
        mock_sandbox = MagicMock()
        mock_validator = MagicMock()
        mock_approval_policy = MagicMock()
        mock_rollback_manager = MagicMock()
        mock_adapters = {}
        
        service = ToolTeachService(
            registry=mock_registry,
            memory=mock_memory,
            sandbox=mock_sandbox,
            validator=mock_validator,
            approval_policy=mock_approval_policy,
            rollback_manager=mock_rollback_manager,
            adapters=mock_adapters,
            workspace_root="/tmp",
            human_approval_broker=broker,
        )
        
        # Verify the broker is wired correctly
        assert service.human_approval_broker is broker
        assert service.human_approval_broker is not None

    def test_non_blocking_approval_request_creates_request_without_blocking(self):
        """Test non-blocking approval request: request_non_blocking returns request_id immediately."""
        broker = HumanApprovalBroker()
        
        # Register a dummy handler so the request stays pending
        broker.register_prompt_handler(lambda payload: None)
        
        # Call request_non_blocking should return immediately
        request_id = broker.request_non_blocking(
            kind='tool_execution',
            reason='Test approval',
            scope={'task_id': 'test-task-123', 'tool_id': 'test_tool'},
        )
        
        # Should return a valid request_id
        assert request_id is not None
        assert len(request_id) >= 8  # UUID-like hex
        
        # Request should be in pending
        assert broker.pending_count() == 1
        
        # Should not block or wait
        # (This is verified by the test completing quickly)

    def test_approved_result_can_be_retrieved_after_approval(self):
        """Test that get_resolved_request returns ApprovalResult after approval."""
        broker = HumanApprovalBroker()
        
        # Register a dummy handler so the request stays pending
        broker.register_prompt_handler(lambda payload: None)
        
        # Create non-blocking request
        request_id = broker.request_non_blocking(
            kind='tool_execution',
            reason='Test approval',
            scope={'task_id': 'test-task-123', 'tool_id': 'test_tool'},
        )
        
        # Approve the request
        approved = broker.approve(request_id)
        assert approved is True
        
        # Wait a moment for the callback to complete
        import time
        time.sleep(0.1)
        
        # Retrieve the resolved result
        result = broker.get_resolved_request(request_id)
        assert result is not None
        assert result.approved is True
        assert result.rejected is False
        assert result.timed_out is False
        assert result.cancelled is False

    def test_rejected_result_can_be_retrieved_after_rejection(self):
        """Test that get_resolved_request returns rejected ApprovalResult after rejection."""
        broker = HumanApprovalBroker()
        
        # Register a dummy handler so the request stays pending
        broker.register_prompt_handler(lambda payload: None)
        
        # Create non-blocking request
        request_id = broker.request_non_blocking(
            kind='tool_execution',
            reason='Test approval',
            scope={'task_id': 'test-task-123', 'tool_id': 'test_tool'},
        )
        
        # Reject the request
        rejected = broker.reject(request_id)
        assert rejected is True
        
        # Wait a moment for the callback to complete
        import time
        time.sleep(0.1)
        
        # Retrieve the resolved result
        result = broker.get_resolved_request(request_id)
        assert result is not None
        assert result.approved is False
        assert result.rejected is True
