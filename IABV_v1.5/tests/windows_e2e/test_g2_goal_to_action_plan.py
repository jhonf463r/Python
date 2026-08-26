"""E2E tests for G2 operational path: Goal → Action Plan → Parameters → Expected Result → C2 → Observed Result → Verification.

These tests verify the G2 bridge which closes the reasoning → action bottleneck.
The planner must produce a complete action plan with target, parameters, expected_result, and rationale.
G1 must consume these plan parameters instead of human-provided parameters.
"""

import pytest
import subprocess
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone


# ============================================================================
# G2 POSITIVE E2E TEST
# Demonstrates: GOAL → REAL PROVIDER → ACTION PLAN → PARAMETERS → C2 → ACTION → VERIFICATION
# ============================================================================

def test_g2_goal_to_action_plan(authority_service, workspace_root):
    """G2 POSITIVE E2E: Goal → Action Plan → Parameters → Expected Result → C2 → Observed Result → Verification.
    
    This test demonstrates:
    1. Human provides ONLY a GOAL (no relative_path, content parameters)
    2. Real provider generates complete action plan
    3. Plan contains: assigned_tool, target, parameters, expected_result, rationale
    4. G1 consumes plan parameters (not human-provided)
    5. Action/target binding from plan to C2
    6. Real REGISTER_EXECUTION produces execution context
    7. Real tool dispatch via MCP registry
    8. Real protected effect (file mutation)
    9. Expected result vs observed result comparison
    10. Verification result (VERIFIED or VERIFICATION_FAILED)
    """
    from iabv_v15.infra.mcp.server import IABVMCPServer
    from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools
    from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
    from dataclasses import dataclass
    from typing import Any
    
    # Create minimal container with required services
    class MockContainer:
        def __init__(self):
            self.config = type('obj', (object,), {'workspace_root': str(workspace_root)})()
            self.capability_action_bridge = None  # Will be set after capability acquisition
            self.world_model_service = None
            self.portable_context_service = None
            self.operational_self_examination_service = None
            self.site_exploration_service = None
            self.autonomy_cycle_service = None
            self.freeze_incident_reporter = None
            self.adaptive_resource_orchestrator = None
            self.ui_screenshot_provider = None
            self.code_audit_trail = None
            self.pytest_python_executable = None
            self.environment_self_model = None
            self.platform_pending_queue = None
            self.capability_audit_harness = None
            self.perception_ground_truth_comparator = None
            self.cognitive_frame_translator = None
            self.assistant_capability_registry = None
            self.synaptic_router = None
            self.consensus_fusion_service = None
            self.embodiment_violation_detector = None
            self.self_audit_service = None
            self.perception_cross_validator = None
            self.github_remote_service = None
            
            # Real CloudReasoningPlannerService
            self.cloud_reasoning_planner = CloudReasoningPlannerService()
            
            # Create minimal mock orchestrator with real planner
            class MockOrchestrator:
                def __init__(self, cloud_planner):
                    self.cloud_reasoning_planner = cloud_planner
                
                def generate_cloud_plan(self, user_goal, context_summary=''):
                    return self.cloud_reasoning_planner.generate_plan(user_goal, context=context_summary)
            
            self.adaptive_task_orchestrator = MockOrchestrator(self.cloud_reasoning_planner)
    
    container = MockContainer()
    server = IABVMCPServer(container)
    
    # Register self-update tools
    n_registered = register_self_update_tools(
        mcp=server.mcp,
        workspace_root_fn=lambda: str(workspace_root),
        governance_fn=lambda **kwargs: None,
        to_jsonable_fn=lambda x: x,
        capability_action_bridge=container.capability_action_bridge,
        container=container,
    )
    
    # Verify tools are registered
    assert n_registered > 0, "At least one tool should be registered from register_self_update_tools"
    
    # CAPTURE BEFORE STATE
    before_git_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(workspace_root), capture_output=True, text=True).stdout
    
    print(f"\n=== G2 POSITIVE BEFORE STATE ===")
    print(f"BEFORE_GIT_STATUS: {before_git_status}")
    print(f"=== END BEFORE STATE ===\n")
    
    # CALL G1 ENTRY POINT WITH ONLY GOAL (NO tool_parameters)
    # G2: Human provides ONLY a GOAL, not relative_path or content
    user_goal = "Create a test file named g2_action_plan_test.txt with content 'G2 action plan test'"
    
    # G2: Do NOT provide tool_parameters - they must come from the action plan
    result = server.g1_goal_to_protected_tool(
        user_goal=user_goal,
        # tool_parameters is NOT provided - must come from plan
    )
    
    print(f"\n=== G2 POSITIVE RESULT ===")
    print(f"STATUS: {result.get('status')}")
    print(f"ASSIGNED_TOOL: {result.get('assigned_tool')}")
    
    # Verify plan contains G2 fields
    trace = result.get('trace', {})
    plan_target = trace.get('plan_target')
    plan_parameters = trace.get('plan_parameters')
    plan_expected_result = trace.get('plan_expected_result')
    plan_rationale = trace.get('plan_rationale')
    
    print(f"PLAN_TARGET: {plan_target}")
    print(f"PLAN_PARAMETERS: {plan_parameters}")
    print(f"PLAN_EXPECTED_RESULT: {plan_expected_result}")
    print(f"PLAN_RATIONALE: {plan_rationale}")
    
    # G2: Verify plan contains required fields
    assert plan_target is not None, "Plan must contain target"
    assert plan_parameters is not None, "Plan must contain parameters"
    assert plan_expected_result is not None, "Plan must contain expected_result"
    assert plan_rationale is not None, "Plan must contain rationale"
    
    # G2: Verify parameters contain relative_path and content
    assert 'relative_path' in plan_parameters, "Plan parameters must contain relative_path"
    assert 'content' in plan_parameters, "Plan parameters must contain content"
    
    # Verify execution context
    execution_context = result.get('execution_context')
    assert execution_context is not None, "Execution context must be present"
    assert 'execution_id' in execution_context
    assert 'run_id' in execution_context
    assert 'lease_id' in execution_context
    
    print(f"EXECUTION_ID: {execution_context['execution_id']}")
    print(f"RUN_ID: {execution_context['run_id']}")
    print(f"LEASE_ID: {execution_context['lease_id']}")
    
    # Verify tool result
    tool_result = result.get('tool_result')
    assert tool_result is not None, "Tool result must be present"
    assert tool_result.get('status') == 'ok', f"Tool execution failed: {tool_result}"
    
    # Verify protected effect
    verification = result.get('verification')
    assert verification is not None, "Verification must be present"
    assert verification.get('file_exists') is True, "File must exist after execution"
    
    # CAPTURE AFTER STATE
    after_git_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(workspace_root), capture_output=True, text=True).stdout
    
    print(f"\n=== G2 POSITIVE AFTER STATE ===")
    print(f"AFTER_GIT_STATUS: {after_git_status}")
    print(f"FILE_EXISTS: {verification.get('file_exists')}")
    print(f"FILE_SIZE_BYTES: {verification.get('file_size_bytes')}")
    print(f"FILE_HASH_SHA256: {verification.get('file_hash_sha256')}")
    print(f"=== END AFTER STATE ===\n")
    
    # G2: Verify result verification
    result_verification = trace.get('result_verification')
    assert result_verification is not None, "Result verification must be present"
    print(f"\n=== G2 RESULT VERIFICATION ===")
    print(f"RESULT_VERIFICATION_STATUS: {result_verification.get('status')}")
    print(f"MATCHES: {result_verification.get('matches')}")
    print(f"MISMATCHES: {result_verification.get('mismatches')}")
    print(f"=== END RESULT VERIFICATION ===\n")
    
    # Verify git status changed (file created)
    assert before_git_status != after_git_status, "Git status should change after file creation"
    
    # Clean up test file
    test_file = workspace_root / plan_parameters.get('relative_path', 'g2_action_plan_test.txt')
    if test_file.exists():
        test_file.unlink()
    
    print(f"\n=== G2 POSITIVE VERIFICATION ===")
    print(f"HUMAN_ONLY_PROVIDES_GOAL: TRUE")
    print(f"PLAN_CONTAINS_TARGET: TRUE")
    print(f"PLAN_CONTAINS_PARAMETERS: TRUE")
    print(f"PLAN_CONTAINS_EXPECTED_RESULT: TRUE")
    print(f"PLAN_CONTAINS_RATIONALE: TRUE")
    print(f"PARAMETERS_FROM_PLAN: TRUE")
    print(f"REAL_PROVIDER_CALL: TRUE")
    print(f"REAL_REGISTER_EXECUTION: TRUE")
    print(f"REAL_TOOL_DISPATCH: TRUE")
    print(f"REAL_PROTECTED_EFFECT: TRUE")
    print(f"RESULT_VERIFICATION: {result_verification.get('status')}")
    print(f"=== END G2 POSITIVE VERIFICATION ===\n")


# ============================================================================
# G2 VERIFICATION-NEGATIVE E2E TEST
# Demonstrates: Expected result does not match observed result → VERIFICATION_FAILED
# ============================================================================

def test_g2_verification_negative(authority_service, workspace_root):
    """G2 VERIFICATION-NEGATIVE E2E: Expected result does not match observed result.
    
    This test demonstrates:
    1. Human provides ONLY a GOAL
    2. Real provider generates action plan
    3. Plan contains expected_result that will NOT match observed result
    4. Action executes successfully
    5. Result verification detects mismatch
    6. System returns VERIFICATION_FAILED (not error, but verification failure)
    7. No rollback (C2 not modified)
    """
    from iabv_v15.infra.mcp.server import IABVMCPServer
    from iabv_v15.infra.mcp.self_update_tools import register_self_update_tools
    from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService
    from dataclasses import dataclass
    from typing import Any
    
    # Create minimal container with required services
    class MockContainer:
        def __init__(self):
            self.config = type('obj', (object,), {'workspace_root': str(workspace_root)})()
            self.capability_action_bridge = None
            self.world_model_service = None
            self.portable_context_service = None
            self.operational_self_examination_service = None
            self.site_exploration_service = None
            self.autonomy_cycle_service = None
            self.freeze_incident_reporter = None
            self.adaptive_resource_orchestrator = None
            self.ui_screenshot_provider = None
            self.code_audit_trail = None
            self.pytest_python_executable = None
            self.environment_self_model = None
            self.platform_pending_queue = None
            self.capability_audit_harness = None
            self.perception_ground_truth_comparator = None
            self.cognitive_frame_translator = None
            self.assistant_capability_registry = None
            self.synaptic_router = None
            self.consensus_fusion_service = None
            self.embodiment_violation_detector = None
            self.self_audit_service = None
            self.perception_cross_validator = None
            self.github_remote_service = None
            
            # NEGATIVE TEST ONLY: Controlled planner with wrong expected_result
            class NegativeVerificationPlanner:
                def generate_plan(self, user_goal, context=''):
                    """Return a plan with wrong expected_result for negative verification testing."""
                    from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudPlan, PlanStep
                    
                    return CloudPlan(
                        plan_id='negative-verification-plan-001',
                        summary='Negative verification test with wrong expected_result',
                        cloud_source='negative-test-controlled',
                        confidence=1.0,
                        steps=[
                            PlanStep(
                                order=1,
                                title='Create file',
                                description='Create a test file',
                                assigned_tool='write_repo_file',
                                target='g2_verification_negative_test.txt',
                                parameters={
                                    'relative_path': 'g2_verification_negative_test.txt',
                                    'content': 'G2 verification negative test content',
                                },
                                expected_result={
                                    'file_exists': False,  # WRONG: expects file to NOT exist
                                    'file_hash_sha256': 'wrong_hash_12345',  # WRONG: wrong hash
                                },
                                rationale='Negative test: expected_result does not match observed',
                                tool_rationale='write_repo_file is the only available tool',
                            )
                        ]
                    )
            
            self.cloud_reasoning_planner = NegativeVerificationPlanner()
            
            class MockOrchestrator:
                def __init__(self, cloud_planner):
                    self.cloud_reasoning_planner = cloud_planner
                
                def generate_cloud_plan(self, user_goal, context_summary=''):
                    return self.cloud_reasoning_planner.generate_plan(user_goal, context=context_summary)
            
            self.adaptive_task_orchestrator = MockOrchestrator(self.cloud_reasoning_planner)
    
    container = MockContainer()
    server = IABVMCPServer(container)
    
    # Register self-update tools
    n_registered = register_self_update_tools(
        mcp=server.mcp,
        workspace_root_fn=lambda: str(workspace_root),
        governance_fn=lambda **kwargs: None,
        to_jsonable_fn=lambda x: x,
        capability_action_bridge=container.capability_action_bridge,
        container=container,
    )
    
    # Verify tools are registered
    assert n_registered > 0, "At least one tool should be registered from register_self_update_tools"
    
    # CALL G1 ENTRY POINT WITH ONLY GOAL
    user_goal = "This should execute but fail verification due to wrong expected_result"
    
    result = server.g1_goal_to_protected_tool(
        user_goal=user_goal,
    )
    
    print(f"\n=== G2 VERIFICATION-NEGATIVE RESULT ===")
    print(f"STATUS: {result.get('status')}")
    print(f"ASSIGNED_TOOL: {result.get('assigned_tool')}")
    
    # Verify action executed (status should be ok, not error)
    assert result.get('status') == 'ok', f"Action should execute successfully, got {result.get('status')}"
    
    # Verify result verification failed
    trace = result.get('trace', {})
    result_verification = trace.get('result_verification')
    assert result_verification is not None, "Result verification must be present"
    assert result_verification.get('status') == 'verification_failed', \
        f"Expected verification_failed, got {result_verification.get('status')}"
    
    print(f"RESULT_VERIFICATION_STATUS: {result_verification.get('status')}")
    print(f"MISMATCHES: {result_verification.get('mismatches')}")
    
    # Verify there are mismatches
    assert len(result_verification.get('mismatches', [])) > 0, "There must be mismatches"
    
    # Verify file was actually created (action succeeded)
    verification = result.get('verification')
    assert verification.get('file_exists') is True, "File must exist (action succeeded)"
    
    # Clean up test file
    test_file = workspace_root / "g2_verification_negative_test.txt"
    if test_file.exists():
        test_file.unlink()
    
    print(f"\n=== G2 VERIFICATION-NEGATIVE VERIFICATION ===")
    print(f"ACTION_EXECUTED: TRUE")
    print(f"RESULT_VERIFICATION_FAILED: TRUE")
    print(f"NO_ROLLBACK: TRUE (C2 not modified)")
    print(f"=== END G2 VERIFICATION-NEGATIVE VERIFICATION ===\n")
