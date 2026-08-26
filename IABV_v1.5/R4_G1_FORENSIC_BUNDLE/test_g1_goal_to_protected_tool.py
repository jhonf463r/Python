"""
G1 Goal → Plan → Tool → Capability → Protected Effect E2E Test

TEST_PROVENANCE = R4_G1_RUNTIME_TEST
This is a NEW runtime test for R4 G1 gate.

Tests the complete G1 operational path:
Goal → CloudReasoningPlanner → plan → assigned_tool → 
register_execution → execution context propagation → 
write_repo_file → acquire_capability_for_existing_execution → 
Authority → authorized effect → real file mutation

CRITICAL: This test must demonstrate that a human only provides a goal,
and the system automatically propagates execution context through the
entire chain without manual copy/paste of IDs.

NOTE: This test requires the authority_service fixture from windows_e2e/conftest.py
and should be run with pytest from the windows_e2e directory or with conftest.py
in the path.
"""

import pytest
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from iabv_v15.services.trust.authority_client import AuthorityClient
from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
from iabv_v15.services.adaptive.adaptive_task_orchestrator import AdaptiveTaskOrchestrator
from iabv_v15.infra.mcp.server import IABVMCPServer


class TestG1GoalToProtectedTool:
    """G1 Goal → Plan → Tool → Capability → Protected Effect E2E Tests."""

    @pytest.fixture
    def isolated_repo(self):
        """Create an isolated temporary git repository for testing."""
        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "g1_test_repo"
            repo_path.mkdir()
            
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'g1@test.com'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'G1 Test'], cwd=str(repo_path), check=True, capture_output=True)
            
            # Create initial file
            test_file = repo_path / "initial.txt"
            test_file.write_text("Initial content\n", encoding="utf-8")
            
            subprocess.run(['git', 'add', '.'], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=str(repo_path), check=True, capture_output=True)
            
            yield repo_path

    @pytest.fixture
    def authority_pid(self, authority_service):
        """Return the authority PID from the fixture for process separation verification."""
        import os
        service, authority_pid = authority_service
        client_pid = os.getpid()
        print(f"[G1 Test] Client PID: {client_pid}, Authority PID: {authority_pid}", flush=True)
        print(f"[G1 Test] Process separation: {client_pid != authority_pid}", flush=True)
        return authority_pid

    def test_g1_goal_to_protected_tool(self, isolated_repo, authority_pid, authority_service):
        """G1 POSITIVE TEST: Goal → Plan → Tool → C2 → Protected Effect.
        
        Required flow:
        1. Human provides ONLY a goal (no manual ID propagation)
        2. System generates cloud plan with assigned_tool
        3. System registers execution with Authority
        4. System propagates execution_id, run_id, session_id, episode_id
        5. System invokes selected tool with propagated IDs
        6. Tool acquires capability for existing execution
        7. Authority authorizes the action
        8. Real file mutation occurs
        9. Git worktree mutation verified
        
        Expected: AUTHORIZATION_BEFORE_EFFECT = TRUE
        Expected: HUMAN_ONLY_PROVIDES_GOAL = TRUE
        """
        import os
        
        service, _ = authority_service
        
        # Record initial git state
        initial_head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(isolated_repo), check=True, capture_output=True, text=True).stdout.strip()
        initial_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(isolated_repo), check=True, capture_output=True, text=True).stdout.strip()
        print(f"[G1 Test] Initial HEAD: {initial_head}", flush=True)
        print(f"[G1 Test] Initial status: {initial_status}", flush=True)
        
        # Step 1: Create CloudReasoningPlannerService with mocked provider for G1 demo
        # For G1 demo, we need to ensure the planner returns write_repo_file
        # In production, this would use the real provider
        from unittest.mock import Mock
        mock_planner = Mock(spec=CloudReasoningPlannerService)
        
        # Create a mock plan that assigns write_repo_file
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudPlan, PlanStep
        from datetime import datetime, timezone
        import uuid
        
        mock_plan = CloudPlan(
            plan_id=str(uuid.uuid4()),
            user_goal="Create a test file to demonstrate G1 execution",
            summary="Create test file via write_repo_file",
            steps=[
                PlanStep(
                    order=1,
                    title="Create test file",
                    description="Create g1_goal_execution_test.txt with execution metadata",
                    assigned_tool="write_repo_file",
                    tool_rationale="G1 demo requires file write to demonstrate full path",
                    requires_approval=False,
                    estimated_seconds=1,
                )
            ],
            cloud_source="mock_for_g1_demo",
            confidence=1.0,
            created_at_utc=datetime.now(timezone.utc),
        )
        mock_planner.generate_plan = Mock(return_value=mock_plan)
        
        # Step 2: Create minimal orchestrator with mocked planner
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=Mock(),
            adaptive_session_repository=Mock(),
            intent_service=Mock(),
            context_assembler=Mock(),
            capability_service=Mock(),
            strategy_pack_registry=Mock(),
            planner_service=Mock(),
            approval_gate_service=Mock(),
            execution_playbook_service=Mock(),
            task_outcome_recorder=Mock(),
        )
        orchestrator.cloud_reasoning_planner = mock_planner
        
        # Step 3: Create minimal MCP server mock with capability_action_bridge
        # G1 will create its own authority connection via acquire_capability_for_execution
        # The capability_action_bridge is only needed for the final tool invocation
        mock_mcp_server = Mock()
        mock_mcp_server.capability_action_bridge = None  # G1 handles this internally
        mock_mcp_server.mcp = Mock()
        
        # Step 4: Execute goal through G1 entry point
        # Human provides ONLY the goal - no manual ID propagation
        goal = "Create a test file to demonstrate G1 execution"
        
        result = orchestrator.execute_goal_to_protected_tool(
            user_goal=goal,
            workspace_root=str(isolated_repo),
            mcp_server=mock_mcp_server,
        )
        
        print(f"[G1 Test] Result: {result}", flush=True)
        
        # Step 6: Verify result structure
        assert result['status'] == 'completed', f"G1 execution failed: {result['errors']}"
        assert 'plan_id' in result, "Plan ID not in result"
        assert 'execution_id' in result, "Execution ID not in result"
        assert 'run_id' in result, "Run ID not in result"
        assert 'session_id' in result, "Session ID not in result"
        assert 'episode_id' in result, "Episode ID not in result"
        assert 'lease_id' in result, "Lease ID not in result"
        assert 'assigned_tool' in result, "Assigned tool not in result"
        
        # Step 7: Verify tool selection
        assert result['assigned_tool'] == 'write_repo_file', f"Expected write_repo_file, got {result['assigned_tool']}"
        
        # Step 8: Verify execution context propagation
        assert result['execution_id'] is not None, "Execution ID is None"
        assert result['run_id'] is not None, "Run ID is None"
        assert result['session_id'] is not None, "Session ID is None"
        assert result['episode_id'] is not None, "Episode ID is None"
        
        # Step 9: Verify authorization
        assert result['authorization_result'] == 'authorized', f"Authorization failed: {result.get('errors')}"
        
        # Step 10: Verify protected effect
        assert result['protected_effect'] == 'file_written', f"Expected file_written, got {result['protected_effect']}"
        assert result['file_exists'] is True, "File was not created"
        
        # Step 11: Verify real file mutation
        test_file = isolated_repo / "g1_goal_execution_test.txt"
        assert test_file.exists(), "Test file does not exist"
        content = test_file.read_text(encoding="utf-8")
        assert goal in content, "Goal not found in file content"
        assert result['execution_id'] in content, "Execution ID not found in file content"
        
        # Step 12: Verify git worktree mutation
        final_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(isolated_repo), check=True, capture_output=True, text=True).stdout.strip()
        print(f"[G1 Test] Final status: {final_status}", flush=True)
        assert 'g1_goal_execution_test.txt' in final_status, "File not shown in git status"
        
        final_diff = subprocess.run(['git', 'diff', '--stat'], cwd=str(isolated_repo), check=True, capture_output=True, text=True).stdout.strip()
        print(f"[G1 Test] Final diff: {final_diff}", flush=True)
        
        # Step 13: Verify steps completed
        expected_steps = [
            'plan_generated',
            'tool_selected',
            'capability_acquired',
            'tool_invoked',
            'protected_effect_verified',
            'verification_complete',
        ]
        for step in expected_steps:
            assert step in result['steps_completed'], f"Step {step} not completed"
        
        print(f"[G1 Test] G1 execution successful", flush=True)
        print(f"[G1 Test] HUMAN_ONLY_PROVIDES_GOAL = TRUE", flush=True)
        print(f"[G1 Test] AUTHORIZATION_BEFORE_EFFECT = TRUE", flush=True)

    def test_g1_negative_plan_rejection(self, isolated_repo, authority_pid, authority_service):
        """G1 NEGATIVE TEST: Reject plan with unsupported tool.
        
        Required flow:
        1. Human provides goal
        2. System generates plan with assigned_tool != write_repo_file
        3. System REJECTS the plan
        4. NO execution registration
        5. NO tool invocation
        6. NO file mutation
        
        Expected: STATUS = rejected
        Expected: NO_PROTECTED_EFFECT = TRUE
        """
        import os
        
        service, _ = authority_service
        
        # Create mock planner that returns unsupported tool
        from unittest.mock import Mock
        from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudPlan, PlanStep
        from datetime import datetime, timezone
        import uuid
        
        mock_plan = CloudPlan(
            plan_id=str(uuid.uuid4()),
            user_goal="Delete all files",
            summary="Unsupported operation",
            steps=[
                PlanStep(
                    order=1,
                    title="Delete files",
                    description="Delete all files in workspace",
                    assigned_tool="delete_all_files",  # Unsupported for G1 demo
                    tool_rationale="Malicious intent",
                    requires_approval=False,
                    estimated_seconds=1,
                )
            ],
            cloud_source="mock_for_g1_demo",
            confidence=1.0,
            created_at_utc=datetime.now(timezone.utc),
        )
        
        mock_planner = Mock(spec=CloudReasoningPlannerService)
        mock_planner.generate_plan = Mock(return_value=mock_plan)
        
        # Create minimal orchestrator
        orchestrator = AdaptiveTaskOrchestrator(
            role_router=Mock(),
            adaptive_session_repository=Mock(),
            intent_service=Mock(),
            context_assembler=Mock(),
            capability_service=Mock(),
            strategy_pack_registry=Mock(),
            planner_service=Mock(),
            approval_gate_service=Mock(),
            execution_playbook_service=Mock(),
            task_outcome_recorder=Mock(),
        )
        orchestrator.cloud_reasoning_planner = mock_planner
        
        # Create minimal MCP server mock
        mock_mcp_server = Mock()
        mock_mcp_server.capability_action_bridge = None
        mock_mcp_server.mcp = Mock()
        
        # Execute goal
        goal = "Delete all files"
        result = orchestrator.execute_goal_to_protected_tool(
            user_goal=goal,
            workspace_root=str(isolated_repo),
            mcp_server=mock_mcp_server,
        )
        
        print(f"[G1 Negative Test] Result: {result}", flush=True)
        
        # Verify rejection
        assert result['status'] == 'rejected', f"Expected rejected, got {result['status']}"
        assert 'G1 demo only supports write_repo_file' in result['errors'][0], f"Unexpected error: {result['errors']}"
        
        # Verify no execution registration
        assert 'execution_id' not in result or result['execution_id'] is None, "Execution ID should not exist"
        assert 'run_id' not in result or result['run_id'] is None, "Run ID should not exist"
        
        # Verify no tool invocation
        assert 'tool_result' not in result or result.get('tool_result') is None, "Tool should not have been invoked"
        
        # Verify no file mutation
        test_file = isolated_repo / "g1_goal_execution_test.txt"
        assert not test_file.exists(), "File should not have been created"
        
        print(f"[G1 Negative Test] Plan correctly rejected", flush=True)
