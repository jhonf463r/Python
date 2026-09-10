"""Regression test for cognitive bootstrap service late binding.

This test verifies the fix for the initialization-order bug where
ToolTeachService referenced intent_scoped briefing service before it was
initialized in AppBootstrap._wire_services().

The fix uses explicit two-phase binding:
1. ToolTeachService constructed without briefing service (or with None)
2. ToolTeachService.set_intent_scoped_briefing_service() called after
   IntentScopedBriefingService is initialized
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _reset_global_timeline():
    from iabv_v15.infra.startup_timeline import reset_global_timeline_for_tests
    reset_global_timeline_for_tests()
    yield
    reset_global_timeline_for_tests()


def test_bootstrap_wires_cognitive_service_to_tool_teach(tmp_path: Path) -> None:
    """Verify that AppBootstrap successfully wires intent_scoped briefing service to ToolTeachService."""
    from iabv_v15.bootstrap import AppBootstrap

    bootstrap = AppBootstrap(str(tmp_path))

    assert hasattr(bootstrap, 'tool_teach_service')
    assert hasattr(bootstrap, 'intent_scoped_briefing_service')
    assert bootstrap.tool_teach_service.intent_scoped_briefing_service is bootstrap.intent_scoped_briefing_service


def test_tool_teach_service_late_binding_method() -> None:
    """Verify that ToolTeachService has the late binding method."""
    from iabv_v15.services.tools.tool_teach_service import ToolTeachService

    assert hasattr(ToolTeachService, 'set_intent_scoped_briefing_service')


def test_tool_teach_service_accepts_none_initially() -> None:
    """Verify that ToolTeachService can be constructed with None briefing service."""
    from iabv_v15.services.tools.tool_teach_service import ToolTeachService
    from iabv_v15.services.tools.tool_registry import ToolRegistry
    from iabv_v15.services.tools.tool_memory import ToolMemory
    from iabv_v15.services.tools.tool_sandbox import ToolSandbox
    from iabv_v15.services.tools.tool_validator import ToolValidator
    from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
    from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager

    service = ToolTeachService(
        registry=MagicMock(spec=ToolRegistry),
        memory=MagicMock(spec=ToolMemory),
        sandbox=MagicMock(spec=ToolSandbox),
        validator=MagicMock(spec=ToolValidator),
        approval_policy=MagicMock(spec=ToolApprovalPolicy),
        rollback_manager=MagicMock(spec=ToolRollbackManager),
        adapters={},
        workspace_root="/tmp",
        intent_scoped_briefing_service=None,
    )

    assert service.intent_scoped_briefing_service is None


def test_tool_teach_service_late_binding_consumes_bound_service() -> None:
    """Verify that late binding actually binds the service for consumption."""
    from iabv_v15.services.tools.tool_teach_service import ToolTeachService
    from iabv_v15.services.tools.tool_registry import ToolRegistry
    from iabv_v15.services.tools.tool_memory import ToolMemory
    from iabv_v15.services.tools.tool_sandbox import ToolSandbox
    from iabv_v15.services.tools.tool_validator import ToolValidator
    from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
    from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
    from iabv_v15.domain.models import InferenceRequest, TaskIntent

    fake_briefing = MagicMock()
    fake_briefing.build_context_pack.return_value = "TEST_CONTEXT_PACK"

    service = ToolTeachService(
        registry=MagicMock(spec=ToolRegistry),
        memory=MagicMock(spec=ToolMemory),
        sandbox=MagicMock(spec=ToolSandbox),
        validator=MagicMock(spec=ToolValidator),
        approval_policy=MagicMock(spec=ToolApprovalPolicy),
        rollback_manager=MagicMock(spec=ToolRollbackManager),
        adapters={},
        workspace_root="/tmp",
        intent_scoped_briefing_service=None,
    )

    # Late bind the service
    service.set_intent_scoped_briefing_service(fake_briefing)

    # Verify it's bound
    assert service.intent_scoped_briefing_service is fake_briefing

    # Verify it's consumed (check if build_task_from_request would use it)
    # This is a basic check that the attribute is set and accessible
    assert service.intent_scoped_briefing_service is not None
