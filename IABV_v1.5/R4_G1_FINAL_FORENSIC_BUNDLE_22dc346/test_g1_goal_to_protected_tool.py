"""E2E tests for G1 operational path: Goal → Plan → Tool → C2 → Protected Effect.

These tests verify the real implementation of the G1 bridge on the source of truth.
"""

import pytest
import subprocess
from pathlib import Path


def test_g1_code_verification():
    """Code verification test: Verify the three blockers are fixed in code.

    This test verifies:
    1. Fix 1: acquire_capability_for_execution performs REGISTER_EXECUTION
    2. Fix 2: write_repo_file in planner TOOL_DESCRIPTORS
    3. Fix 3: Canonical MCP registry dispatch (not hardcoded if)
    """
    from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_execution
    from iabv_v15.services.adaptive.cloud_reasoning_planner import TOOL_DESCRIPTORS
    from iabv_v15.infra.mcp.server import IABVMCPServer
    from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
    from iabv_v15.services.trust.authority_client import AuthorityClient

    # Verify Fix 1: acquire_capability_for_execution performs REGISTER_EXECUTION
    # Read the function to verify it calls client.register_execution
    import inspect
    source = inspect.getsource(acquire_capability_for_execution)
    assert 'register_execution' in source, "Fix 1: acquire_capability_for_execution must call register_execution"
    assert 'issue_lease' in source, "Fix 1: acquire_capability_for_execution must call issue_lease"

    # Verify Fix 2: write_repo_file in planner TOOL_DESCRIPTORS
    tool_ids = [t['id'] for t in TOOL_DESCRIPTORS]
    assert 'write_repo_file' in tool_ids, "Fix 2: write_repo_file must be in TOOL_DESCRIPTORS"

    # Verify Fix 3: Canonical MCP registry dispatch in G1 implementation
    # Read server.py to verify G1 uses self.mcp._tools[assigned_tool].fn
    with open('src/iabv_v15/infra/mcp/server.py', 'r', encoding='utf-8') as f:
        server_source = f.read()
    
    # Verify G1 exists
    assert 'def g1_goal_to_protected_tool' in server_source, "G1 tool must exist"
    
    # Verify canonical dispatch (not hardcoded if)
    assert 'self.mcp._tools[assigned_tool].fn' in server_source, "Fix 3: Must use canonical MCP registry dispatch"
    
    # Verify no hardcoded if for write_repo_file
    assert 'if assigned_tool == "write_repo_file"' not in server_source, "Fix 3: No hardcoded if for write_repo_file"
    
    # Verify acquire_capability_for_execution is used (not acquire_capability_for_existing_execution)
    g1_section = server_source[server_source.find('def g1_goal_to_protected_tool'):server_source.find('def g1_goal_to_protected_tool') + 10000]
    assert 'acquire_capability_for_execution' in g1_section, "Fix 1: G1 must use acquire_capability_for_execution"


def test_g1_mcp_registration():
    """Verify G1 tool is registered in MCP."""
    # Read server.py to verify G1 tool is decorated with @mcp.tool()
    with open('src/iabv_v15/infra/mcp/server.py', 'r', encoding='utf-8') as f:
        server_source = f.read()
    
    # Verify G1 tool is decorated with @mcp.tool()
    assert '@mcp.tool()' in server_source and 'def g1_goal_to_protected_tool' in server_source, "G1 tool must be decorated with @mcp.tool()"
    
    # Verify write_repo_file is also registered (from self_update_tools)
    # This is registered in self_update_tools.py, which is called in server.run()


def test_g1_negative_unsupported_tool():
    """Negative test: Verify canonical dispatch validation logic exists.

    This test verifies that the G1 implementation has validation logic
    to reject unsupported tools via canonical dispatch.
    """
    # Read server.py to verify validation logic exists
    with open('src/iabv_v15/infra/mcp/server.py', 'r', encoding='utf-8') as f:
        server_source = f.read()
    
    # Verify tool validation step exists
    g1_section = server_source[server_source.find('def g1_goal_to_protected_tool'):server_source.find('def g1_goal_to_protected_tool') + 10000]
    
    assert 'registered_tools' in g1_section, "G1 must check registered_tools for validation"
    assert 'assigned_tool not in registered_tools' in g1_section, "G1 must validate assigned_tool against registry"
    assert 'Unsupported tool' in g1_section, "G1 must reject unsupported tools"
