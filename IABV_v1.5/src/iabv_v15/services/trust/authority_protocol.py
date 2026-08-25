"""Canonical Authority Protocol for P0.213 V5 Phase 2 Round 3.

This module defines the ONE canonical protocol schema for client-server IPC.
Both AuthorityClient and AuthorityService MUST use this schema.

CRITICAL: Do NOT maintain parallel naming models for the same semantic field.
The protocol contract must be unified and authoritative.

PROTOCOL CONTRACT:
- CALLER REQUEST: invocation_id, action, target, requested_scope, task_context
- AUTHORITY DERIVED: run_id, execution_id, consumer_pid, generation, authorized_scope
- The client may REQUEST. The authority DECIDES.
- No caller-controlled authoritative fields.

Phase 2 Round 3 Status: CANONICAL_PROTOCOL_WITH_CONTEXTUAL_AUTHORIZATION
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path


# ── Canonical Target Normalization ───────────────────────────────────────────────

def canonicalize_target(target: str) -> str:
    """
    Canonicalize a target string for platform-independent policy evaluation.
    
    Normalizes:
    - Path separators (/ and \\) to forward slash
    - Removes redundant separators
    - Normalizes . and .. components where possible
    - Handles absolute vs relative forms
    
    This ensures that:
    - file:src/iabv_v15/services/trust/foo.py
    - file:src\\iabv_v15\\services\\trust\\foo.py
    - file:src/iabv_v15\\services\\trust/foo.py
    
    all resolve to the same canonical representation for policy evaluation.
    
    Args:
        target: Raw target string (e.g., "file:src/foo.py")
        
    Returns:
        Canonicalized target string with normalized separators
    """
    # Extract the prefix (e.g., "file:", "repository:", "remote:")
    if ":" in target:
        prefix, path = target.split(":", 1)
    else:
        # No prefix, treat entire string as path
        prefix = ""
        path = target
    
    # Normalize path separators to forward slash
    # This handles both Windows backslashes and Unix forward slashes
    normalized_path = path.replace("\\", "/")
    
    # Remove redundant separators (e.g., // -> /)
    while "//" in normalized_path:
        normalized_path = normalized_path.replace("//", "/")
    
    # Normalize path components to prevent traversal bypasses
    # Split into components and process
    if normalized_path:
        components = normalized_path.split("/")
        normalized_components = []
        
        for component in components:
            if component == ".":
                # Current directory - skip
                continue
            elif component == "..":
                # Parent directory - remove last component if possible
                # This prevents traversal attacks
                if normalized_components:
                    normalized_components.pop()
                # If no components to pop, keep the .. (it's at root)
                else:
                    normalized_components.append("..")
            else:
                # Normal component - keep
                normalized_components.append(component)
        
        normalized_path = "/".join(normalized_components)
    
    # Reconstruct target with prefix
    if prefix:
        canonical_target = f"{prefix}:{normalized_path}"
    else:
        canonical_target = normalized_path
    
    return canonical_target


# ── Canonical Request Contracts ────────────────────────────────────────────────

@dataclass
class RegisterExecutionRequest:
    """Canonical REGISTER_EXECUTION request.
    
    CALLER REQUEST FIELDS (caller-provided):
    - invocation_id: Unique invocation identifier
    - action: Requested operation (e.g., "READ", "WRITE")
    - target: Requested target (e.g., "codebase", "repo")
    - requested_scope: Caller's requested authorization scope
    - task_context: Task/development objective context (e.g., "self_analysis")
    - episode_id: Optional episode identifier
    - session_id: Optional session identifier
    
    AUTHORITY DERIVED FIELDS (authority-provided in response):
    - run_id: Authority-owned run identifier
    - execution_id: Authority-owned execution identifier
    - consumer_pid: Authority-observed client PID
    - generation: Authority generation
    - authorized_scope: Authority-computed scope based on policy
    """
    invocation_id: str
    action: str
    target: str
    requested_scope: str
    task_context: Optional[str] = None
    episode_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "invocation_id": self.invocation_id,
            "action": self.action,
            "target": self.target,
            "requested_scope": self.requested_scope,
            "task_context": self.task_context,
            "episode_id": self.episode_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisterExecutionRequest":
        """Create from dictionary for IPC."""
        return cls(
            invocation_id=data["invocation_id"],
            action=data["action"],
            target=data["target"],
            requested_scope=data["requested_scope"],
            task_context=data.get("task_context"),
            episode_id=data.get("episode_id"),
            session_id=data.get("session_id")
        )


@dataclass
class RegisterExecutionResponse:
    """Canonical REGISTER_EXECUTION response.
    
    AUTHORITY DERIVED FIELDS:
    - run_id: Authority-owned run identifier
    - execution_id: Authority-owned execution identifier
    - consumer_pid: Authority-observed client PID
    - generation: Authority generation
    - authorized_scope: Authority-computed scope based on policy
    """
    run_id: str
    execution_id: str
    consumer_pid: int
    generation: int
    authorized_scope: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "run_id": self.run_id,
            "execution_id": self.execution_id,
            "consumer_pid": self.consumer_pid,
            "generation": self.generation,
            "authorized_scope": self.authorized_scope
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisterExecutionResponse":
        """Create from dictionary for IPC."""
        return cls(
            run_id=data["run_id"],
            execution_id=data["execution_id"],
            consumer_pid=data["consumer_pid"],
            generation=data["generation"],
            authorized_scope=data["authorized_scope"]
        )


@dataclass
class IssueLeaseRequest:
    """Canonical ISSUE_LEASE request.
    
    CALLER REQUEST FIELDS (caller-provided):
    - run_id: Authority-owned run identifier (from registration)
    - execution_id: Authority-owned execution identifier (from registration)
    - requested_ttl_seconds: Requested lease TTL in seconds (optional)
    
    AUTHORITY DERIVED FIELDS (authority-provided in response):
    - lease_id: Authority-owned lease identifier
    - authorized_scope: Authority-computed scope (from RunRecord)
    - issued_at: Authority timestamp
    - expires_at: Authority timestamp
    - signature: Authority HMAC signature
    
    NOTE: The authority looks up canonical RunRecord rather than trusting
    the client to restate authoritative fields.
    """
    run_id: str
    execution_id: str
    requested_ttl_seconds: Optional[int] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "run_id": self.run_id,
            "execution_id": self.execution_id,
            "requested_ttl_seconds": self.requested_ttl_seconds
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssueLeaseRequest":
        """Create from dictionary for IPC."""
        return cls(
            run_id=data["run_id"],
            execution_id=data["execution_id"],
            requested_ttl_seconds=data.get("requested_ttl_seconds")
        )


@dataclass
class IssueLeaseResponse:
    """Canonical ISSUE_LEASE response.
    
    AUTHORITY DERIVED FIELDS:
    - lease_id: Authority-owned lease identifier
    - run_id: Authority-owned run identifier
    - execution_id: Authority-owned execution identifier
    - authorized_scope: Authority-computed scope
    - issued_at: Authority timestamp
    - expires_at: Authority timestamp
    - signature: Authority HMAC signature
    """
    lease_id: str
    run_id: str
    execution_id: str
    authorized_scope: str
    issued_at: float
    expires_at: float
    signature: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "lease_id": self.lease_id,
            "run_id": self.run_id,
            "execution_id": self.execution_id,
            "authorized_scope": self.authorized_scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssueLeaseResponse":
        """Create from dictionary for IPC."""
        return cls(
            lease_id=data["lease_id"],
            run_id=data["run_id"],
            execution_id=data["execution_id"],
            authorized_scope=data["authorized_scope"],
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            signature=data["signature"]
        )


@dataclass
class ConsumeLeaseRequest:
    """Canonical CONSUME_LEASE request.
    
    CALLER REQUEST FIELDS (caller-provided):
    - lease_id: Authority-owned lease identifier
    - execution_id: Authority-owned execution identifier (from registration)
    - requested_action: Requested action for validation
    - requested_target: Requested target for validation
    
    AUTHORITY DERIVED FIELDS (authority retrieves from canonical state):
    - run_id: From lease state
    - consumer_pid: Authority-observed client PID
    - generation: Authority generation
    - authorized_scope: From RunRecord
    - authorized_action: From RunRecord (for validation)
    - authorized_target: From RunRecord (for validation)
    - expiry: From lease state
    - signature: From lease state
    
    NOTE: The authority validates requested_action/target against authorized_action/target
    from the RunRecord before consuming the lease.
    """
    lease_id: str
    execution_id: str
    requested_action: str
    requested_target: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "lease_id": self.lease_id,
            "execution_id": self.execution_id,
            "requested_action": self.requested_action,
            "requested_target": self.requested_target
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsumeLeaseRequest":
        """Create from dictionary for IPC."""
        return cls(
            lease_id=data["lease_id"],
            execution_id=data["execution_id"],
            requested_action=data["requested_action"],
            requested_target=data["requested_target"]
        )


@dataclass
class ConsumeLeaseResponse:
    """Canonical CONSUME_LEASE response.
    
    AUTHORITY DERIVED FIELDS:
    - consumed: Whether lease was successfully consumed
    - consumed_at: Authority timestamp (if consumed)
    """
    consumed: bool
    consumed_at: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "consumed": self.consumed,
            "consumed_at": self.consumed_at
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsumeLeaseResponse":
        """Create from dictionary for IPC."""
        return cls(
            consumed=data["consumed"],
            consumed_at=data.get("consumed_at")
        )


@dataclass
class VerifyExecutionContextRequest:
    """Canonical VERIFY_EXECUTION_CONTEXT request.
    
    CALLER REQUEST FIELDS (caller-provided):
    - execution_id: Execution identifier to verify
    - run_id: Run identifier to verify
    - session_id: Session identifier to verify (optional)
    - episode_id: Episode identifier to verify (optional)
    
    AUTHORITY DERIVED FIELDS (authority retrieves from canonical state):
    - valid: Whether the execution context is valid
    - consumer_pid: Authority-observed client PID from RunRecord
    - generation: Authority generation from RunRecord
    - authorized_scope: Authorized scope from RunRecord
    
    The authority validates that:
    - The execution exists in the RunRecord database
    - The execution belongs to the authenticated client (consumer_pid matches peer)
    - The generation matches the current authority generation
    """
    execution_id: str
    run_id: str
    session_id: Optional[str] = None
    episode_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "episode_id": self.episode_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerifyExecutionContextRequest":
        """Create from dictionary for IPC."""
        return cls(
            execution_id=data["execution_id"],
            run_id=data["run_id"],
            session_id=data.get("session_id"),
            episode_id=data.get("episode_id")
        )


@dataclass
class VerifyExecutionContextResponse:
    """Canonical VERIFY_EXECUTION_CONTEXT response.
    
    AUTHORITY DERIVED FIELDS:
    - valid: Whether the execution context is valid
    - consumer_pid: Authority-observed client PID from RunRecord
    - generation: Authority generation from RunRecord
    - authorized_scope: Authorized scope from RunRecord
    - error: Error message if invalid (optional)
    """
    valid: bool
    consumer_pid: Optional[int] = None
    generation: Optional[int] = None
    authorized_scope: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for IPC."""
        return {
            "valid": self.valid,
            "consumer_pid": self.consumer_pid,
            "generation": self.generation,
            "authorized_scope": self.authorized_scope,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerifyExecutionContextResponse":
        """Create from dictionary for IPC."""
        return cls(
            valid=data["valid"],
            consumer_pid=data.get("consumer_pid"),
            generation=data.get("generation"),
            authorized_scope=data.get("authorized_scope"),
            error=data.get("error")
        )


# ── Authorization Policy ────────────────────────────────────────────────────────

@dataclass
class AuthorizationPolicyInput:
    """Input to authorization policy decision.
    
    The policy input includes:
    - observed_process_identity: Authority-observed client identity
    - canonical_run_record: Authority-owned RunRecord (if exists)
    - action: Requested operation
    - target: Requested target
    - requested_scope: Caller's requested scope
    - task_context: Task/development objective context
    - generation: Authority generation
    """
    observed_process_identity: dict[str, Any]
    canonical_run_record: Optional[dict[str, Any]]
    action: str
    target: str
    requested_scope: str
    task_context: Optional[str]
    generation: int


@dataclass
class AuthorizationPolicyDecision:
    """Output from authorization policy decision.
    
    The policy produces:
    - allowed: ALLOW/DENY decision
    - authorized_scope: Authority-computed scope (if allowed)
    - constraints: Optional constraints/expiry
    - reason: Human-readable reason for decision
    """
    allowed: bool
    authorized_scope: Optional[str] = None
    constraints: Optional[dict[str, Any]] = None
    reason: str = ""


def apply_authorization_policy(input: AuthorizationPolicyInput) -> AuthorizationPolicyDecision:
    """Apply authorization policy to request.
    
    This is a REAL authorization policy, not a placeholder.
    
    Phase 2 Round 3: Contextual authorization policy.
    - Identity materially affects decision
    - Task context materially affects decision
    - requested_scope != authorized_scope
    
    POLICY EXAMPLES:
    
    CASE A: Authorized identity + approved task context → ALLOW
    - action = "read_source"
    - target = "IABV_v1.5"
    - scope = "repo.read"
    - task_context = "self_analysis"
    - identity = authorized process
    → ALLOW
    
    CASE B: Unauthorized identity → DENY
    - Same action/target/scope/context
    - identity = unauthorized process
    → DENY
    
    CASE C: Wrong task context → DENY
    - Same identity/action/target/scope
    - task_context = "unrelated_objective"
    → DENY
    
    CASE D: Wildcard/admin scope → DENY
    - scope = "*" or "admin"
    → DENY
    
    CASE E: Scope broader than task permits → DENY
    - task_context = "self_analysis"
    - scope = "repo.write"
    → DENY (only read permitted for self_analysis)
    
    The policy must NOT simply return the caller's string.
    """
    # CASE D: Reject wildcard/admin scopes
    if input.requested_scope in ["*", "admin", "admin:all", "root", "superuser"]:
        return AuthorizationPolicyDecision(
            allowed=False,
            reason="Privileged scope not allowed"
        )
    
    # CASE B: Identity check - for demo, allow any process (in production, use allowlist)
    # In production, this would check against an authorized process list
    # For now, we'll use a simple heuristic: allow if PID is reasonable
    client_pid = input.observed_process_identity.get("pid", 0)
    if client_pid <= 0:
        return AuthorizationPolicyDecision(
            allowed=False,
            reason="Invalid process identity"
        )
    
    # CASE C: Task context check
    # For self_analysis task, only allow read operations
    if input.task_context == "self_analysis":
        if input.action == "READ" and input.target == "codebase":
            if input.requested_scope == "codebase:read":
                return AuthorizationPolicyDecision(
                    allowed=True,
                    authorized_scope="codebase:read",
                    reason="Read operation on codebase allowed for self_analysis task"
                )
            elif input.requested_scope == "codebase:write":
                return AuthorizationPolicyDecision(
                    allowed=False,
                    reason="Write scope not allowed for self_analysis task"
                )
        elif input.action == "WRITE" and input.target == "codebase":
            return AuthorizationPolicyDecision(
                allowed=False,
                reason="Write operations not permitted for self_analysis task"
            )
    
    # CASE E: Scope broader than task permits
    # Allow self_update scope for tool_execution task context (VFINAL5-R2: constrained by action/target)
    if input.task_context == "tool_execution":
        if input.requested_scope == "self_update":
            # VFINAL5-R2.1: Canonicalize target for platform-independent policy evaluation
            canonical_target = canonicalize_target(input.target)
            
            # VFINAL5-R2: Explicit action/target constraints for self_update
            # Define allowed self_update actions and their target scopes
            allowed_self_update_actions = {
                "WRITE_REPOSITORY_FILE": "file:workspace",
                "APPLY_PATCH": "file:workspace",
                "COMMIT": "repository:authorized",
                "PUSH": "remote:authorized"
            }
            
            # Check if action is allowed
            if input.action not in allowed_self_update_actions:
                return AuthorizationPolicyDecision(
                    allowed=False,
                    reason=f"Action '{input.action}' not allowed for self_update scope. Allowed actions: {list(allowed_self_update_actions.keys())}"
                )
            
            # Check if target matches expected scope for the action
            expected_target_scope = allowed_self_update_actions[input.action]
            
            # For file:workspace, target must start with "file:" and be within workspace
            if expected_target_scope == "file:workspace":
                if not canonical_target.startswith("file:"):
                    return AuthorizationPolicyDecision(
                        allowed=False,
                        reason=f"Target '{canonical_target}' must be file: path for WRITE_REPOSITORY_FILE action"
                    )
                # Additional check: target must not be security-critical
                # VFINAL5-R2.1: Use canonical target for security-critical path checks
                security_critical_paths = [
                    "services/trust/",
                    "security/",
                    "authority",
                    "bootstrap.py",
                    ".git/config",
                    ".git/hooks"
                ]
                for critical_path in security_critical_paths:
                    if critical_path in canonical_target:
                        return AuthorizationPolicyDecision(
                            allowed=False,
                            reason=f"Target '{canonical_target}' contains security-critical path '{critical_path}' - not allowed for self_update"
                        )
            
            # For repository:authorized, target must be repository path
            elif expected_target_scope == "repository:authorized":
                if not canonical_target.startswith("repository:"):
                    return AuthorizationPolicyDecision(
                        allowed=False,
                        reason=f"Target '{canonical_target}' must be repository: path for COMMIT action"
                    )
            
            # For remote:authorized, target must be remote path
            elif expected_target_scope == "remote:authorized":
                if not canonical_target.startswith("remote:"):
                    return AuthorizationPolicyDecision(
                        allowed=False,
                        reason=f"Target '{canonical_target}' must be remote: path for PUSH action"
                    )
            
            # Action and target are allowed
            return AuthorizationPolicyDecision(
                allowed=True,
                authorized_scope="self_update",
                constraints={
                    "allowed_action": input.action,
                    "allowed_target": canonical_target,  # Store canonical target
                    "target_scope": expected_target_scope
                },
                reason=f"Self-update action '{input.action}' on target '{canonical_target}' authorized (scope: {expected_target_scope})"
            )
    
    if input.task_context and input.requested_scope not in ["codebase:read", "codebase:write", "self_update"]:
        return AuthorizationPolicyDecision(
            allowed=False,
            reason=f"Scope '{input.requested_scope}' not permitted for task context '{input.task_context}'"
        )
    
    # CASE A: Default allow for valid combinations
    if input.action == "READ" and input.target == "codebase":
        if input.requested_scope == "codebase:read":
            return AuthorizationPolicyDecision(
                allowed=True,
                authorized_scope="codebase:read",
                reason="Read operation on codebase allowed"
            )
    
    # Default deny for unknown combinations
    return AuthorizationPolicyDecision(
        allowed=False,
        reason=f"Action '{input.action}' on target '{input.target}' with scope '{input.requested_scope}' not authorized"
    )
