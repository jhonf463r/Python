"""Capability Lifecycle Helper - F14 Integration

This module provides helper functions for the canonical capability acquisition lifecycle:
1. REGISTER_EXECUTION
2. ISSUE_LEASE
3. CONSUME_LEASE (via CapabilityActionBridge)

The lifecycle is used to obtain a valid capability before tool execution.
"""

from __future__ import annotations

from typing import Any

from iabv_v15.services.trust.authority_client import AuthorityClient


def acquire_capability_for_execution(
    *,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Acquire a capability for tool execution using canonical protocol.
    
    This function performs the full authority lifecycle:
    1. REGISTER_EXECUTION with action, target, requested_scope
    2. ISSUE_LEASE with run_id, execution_id
    3. Returns capability context (run_id, execution_id, lease_id)
    
    Args:
        action: Action to be authorized (e.g., "READ", "WRITE", "EXECUTE")
        target: Target of action (e.g., "codebase", "filesystem", "network")
        requested_scope: Requested scope for the capability
        invocation_id: Unique identifier for this invocation
        episode_id: Optional episode identifier
        session_id: Optional session identifier
        
    Returns:
        Dictionary with capability context:
        {
            "run_id": str,
            "execution_id": str,
            "lease_id": str,
            "action": str,
            "target": str,
            "authorized_scope": str
        }
        
    Raises:
        Exception: If authority service is unavailable or authorization fails
    """
    client = AuthorityClient()
    client.connect()
    
    try:
        # Register execution with canonical protocol
        registration = client.register_execution(
            invocation_id=invocation_id,
            action=action,
            target=target,
            requested_scope=requested_scope,
            task_context="tool_execution",
            episode_id=episode_id,
            session_id=session_id
        )
        
        run_id = registration["run_id"]
        execution_id = registration["execution_id"]
        
        # Issue lease with canonical protocol
        lease = client.issue_lease(
            run_id=run_id,
            execution_id=execution_id,
            requested_ttl_seconds=3600
        )
        
        lease_id = lease["lease_id"]
        authorized_scope = lease.get("authorized_scope", requested_scope)
        
        return {
            "run_id": run_id,
            "execution_id": execution_id,
            "lease_id": lease_id,
            "action": action,
            "target": target,
            "authorized_scope": authorized_scope
        }
    finally:
        client.disconnect()


def consume_capability(
    *,
    lease_id: str,
    execution_id: str,
    requested_action: str,
    requested_target: str,
) -> bool:
    """Consume a capability via CapabilityActionBridge.
    
    This is a convenience wrapper for CapabilityActionBridge.authorize_action.
    In production, use CapabilityActionBridge directly for better control.
    
    Args:
        lease_id: Capability identifier
        execution_id: Execution identifier
        requested_action: Action being requested
        requested_target: Target being requested
        
    Returns:
        True if consumption succeeded, False otherwise
    """
    from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge
    
    client = AuthorityClient()
    client.connect()
    
    try:
        bridge = CapabilityActionBridge(authority_client=client)
        result = bridge.authorize_action(
            lease_id=lease_id,
            requested_action=requested_action,
            requested_target=requested_target,
            execution_id=execution_id
        )
        return result.success
    finally:
        client.disconnect()
