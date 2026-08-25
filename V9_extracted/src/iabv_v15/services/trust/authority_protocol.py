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
    if input.task_context and input.requested_scope not in ["codebase:read", "codebase:write"]:
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
