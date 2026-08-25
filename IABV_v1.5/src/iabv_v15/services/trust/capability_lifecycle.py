"""Capability Lifecycle Helper - F14 Integration

This module provides helper functions for the canonical capability acquisition lifecycle:
1. REGISTER_EXECUTION
2. ISSUE_LEASE
3. CONSUME_LEASE (via CapabilityActionBridge)

The lifecycle is used to obtain a valid capability before tool execution.

PROVENANCE: RECOVERED_FROM_ARTIFACT (temp_audit_bundle_final, V9_extracted)
NOT_GIT_TRACKED: This module was never committed to git history.
RESTORED_FOR_R3_4_RUNTIME_TEST: Restored to enable C2/F15 runtime verification.
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
            session_id=session_id,
            episode_id=episode_id,
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


def acquire_capability_for_existing_execution(
    *,
    execution_id: str,
    run_id: str,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Acquire a capability for an EXISTING execution (C2 self-update path).
    
    This function verifies an existing execution context and issues a new lease
    without creating a new execution. This is critical for C2 self-update where
    multiple MCP invocations must share the same causal attribution.
    
    PROVENANCE: NEW_R3_4_IMPLEMENTATION (function was missing from recovered artifact)
    PURPOSE: Enable C2 runtime verification for self-update authority path.
    
    This function performs:
    1. VERIFY_EXECUTION_CONTEXT with run_id, execution_id, session_id, episode_id
    2. ISSUE_LEASE for the existing execution
    3. Returns capability context (SAME run_id, SAME execution_id, NEW lease_id)
    
    Args:
        execution_id: Existing execution identifier to verify
        run_id: Existing run identifier to verify
        action: Action to be authorized
        target: Target of action
        requested_scope: Requested scope for the capability
        invocation_id: Unique identifier for this invocation
        episode_id: Episode identifier for verification
        session_id: Session identifier for verification
        
    Returns:
        Dictionary with capability context:
        {
            "run_id": str,  # SAME as input
            "execution_id": str,  # SAME as input
            "lease_id": str,  # NEW lease
            "action": str,
            "target": str,
            "authorized_scope": str
        }
        
    Raises:
        RuntimeError: If execution context validation fails
        Exception: If authority service is unavailable
    """
    client = AuthorityClient()
    client.connect()
    
    try:
        # Verify existing execution context
        verification = client.verify_execution_context(
            execution_id=execution_id,
            run_id=run_id,
            session_id=session_id,
            episode_id=episode_id
        )
        
        if not verification.get('valid'):
            raise RuntimeError(
                f"Execution context validation failed: {verification.get('error', 'unknown error')}"
            )
        
        # Issue lease for the existing execution
        lease = client.issue_lease(
            run_id=run_id,
            execution_id=execution_id,
            session_id=session_id,
            episode_id=episode_id,
            requested_ttl_seconds=3600
        )
        
        lease_id = lease["lease_id"]
        authorized_scope = lease.get("authorized_scope", requested_scope)
        
        return {
            "run_id": run_id,  # SAME execution context
            "execution_id": execution_id,  # SAME execution context
            "lease_id": lease_id,  # NEW lease for this invocation
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
        from iabv_v15.services.trust.capability_action_bridge import ActionRequest
        bridge = CapabilityActionBridge(authority_client=client)
        result = bridge.authorize_action(
            ActionRequest(
                lease_id=lease_id,
                execution_id=execution_id,
                action=requested_action,
                target=requested_target,
            )
        )
        return result.authorized
    finally:
        client.disconnect()
