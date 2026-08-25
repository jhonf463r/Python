# C2 Capability Provenance Document (VFINAL5)

**Date:** 2026-08-24 (Updated for VFINAL5)  
**Component:** P0.213 Authority System - C2 Self-Update Production Integration  
**Status:** RESOLVED - Causal Attribution Preserved

---

## Executive Summary

This document traces the provenance of execution context and capability identifiers (execution_id, lease_id) through the production self-update tool chain.

**VFINAL5 State:** Genuine IDs from authority process with causal attribution preserved  
**Mechanism:** Trusted execution context passed via MCP protocol with authority validation  
**Causal Attribution:** Preserved end-to-end from IABV ToolTask through MCP invocation, capability acquisition, ActionRequest, authority consumption, self-update, observation, and persistence

---

## Real Execution Context Source

**File:** `src/iabv_v15/services/trust/trusted_execution_identity.py`

**Data Contract:** `CanonicalRunRecord`
```python
@dataclass(frozen=True)
class CanonicalRunRecord:
    run_id: str
    execution_id: str
    episode_id: Optional[str]
    session_id: Optional[str]
    invocation_id: str
    requested_scope: str
    authorized_scope: str
    action: str
    target: str
    consumer_pid: int
    generation: int
    created_at: float
```

**Source:** Authority Process (Phase 2)  
**Acquisition:** `AuthorityClient.register_execution()`  
**Canonical Source:** ToolTask (src/iabv_v15/domain/models.py)

---

## Real Capability Source (VFINAL5)

**File:** `src/iabv_v15/services/trust/capability_lifecycle.py`

**Function:** `acquire_capability_for_existing_execution()` (NEW for VFINAL5)

**Protocol:**
```python
def acquire_capability_for_existing_execution(
    *,
    execution_id: str,  # EXISTING execution_id from ToolTask
    run_id: str,  # EXISTING run_id from ToolTask
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    client = AuthorityClient()
    client.connect()
    
    # VERIFY_EXECUTION_CONTEXT (NEW for VFINAL5)
    verification = client.verify_execution_context(
        execution_id=execution_id,
        run_id=run_id,
        session_id=session_id,
        episode_id=episode_id
    )
    
    if not verification.get("valid"):
        raise RuntimeError(f"Execution context validation failed: {verification.get('error', 'Unknown error')}")
    
    # ISSUE_LEASE for EXISTING execution (NOT register_execution)
    lease = client.issue_lease(
        run_id=run_id,
        execution_id=execution_id,
        requested_ttl_seconds=3600
    )
    
    lease_id = lease["lease_id"]
    authorized_scope = lease.get("authorized_scope", requested_scope)
    
    return {
        "run_id": run_id,  # SAME run_id (no new execution)
        "execution_id": execution_id,  # SAME execution_id (no new execution)
        "lease_id": lease_id,  # NEW lease for existing execution
        "action": action,
        "target": target,
        "authorized_scope": authorized_scope
    }
```

**Key Difference (VFINAL5):**
- Does NOT call `register_execution()` - no new execution created
- Calls `verify_execution_context()` to validate existing execution
- Returns SAME execution_id and run_id - causal attribution preserved
- Issues NEW lease for existing execution

**Original Function (preserved for non-MCP use):**
```python
def acquire_capability_for_execution(
    *,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    # Creates NEW execution (for non-MCP use)
    # Calls register_execution() then issue_lease()
```

---

## Authority Protocol Extension (VFINAL5)

**File:** `src/iabv_v15/services/trust/authority_protocol.py`

**New Operation:** `VERIFY_EXECUTION_CONTEXT`

**Request Data Contract:**
```python
@dataclass
class VerifyExecutionContextRequest:
    execution_id: str
    run_id: str
    session_id: Optional[str] = None
    episode_id: Optional[str] = None
```

**Response Data Contract:**
```python
@dataclass
class VerifyExecutionContextResponse:
    valid: bool
    consumer_pid: Optional[int] = None
    generation: Optional[int] = None
    authorized_scope: Optional[str] = None
    error: Optional[str] = None
```

**Validations:**
- Execution exists in RunRecord database
- Client PID matches RunRecord consumer_pid
- Generation matches current authority generation

---

## Lease Data Contract

**File:** `src/iabv_v15/services/trust/trusted_lease.py`

**Data Contract:** `TrustedLease`
```python
@dataclass(frozen=True)
class TrustedLease:
    # Issuer (authority-owned, NOT caller-controlled)
    issuer_pid: int
    issuer_generation: int
    
    # Identity binding (authority-owned)
    execution_id: str
    invocation_id: str
    
    # Unique lease ID (authority-generated, NOT caller-controlled)
    lease_id: str
    
    # Process binding (authority-owned, NOT caller-controlled)
    producer_pid: int
    
    # Authorization (authority-owned, NOT caller-controlled)
    producer_scope: str
    authorization_context: Optional[str]
    
    # Lifecycle (authority-owned)
    issued_at: float
    expires_at: float
    
    # Cryptographic proof (Phase 2: HMAC signature)
    signature: str
    
    # Consumption flag (has default)
    consumed: bool = False
```

---

## MCP Tool Wrapper Updates (VFINAL5)

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**MCP Tool Wrapper (write_repo_file) - VFINAL5:**
```python
@mcp.tool()
def write_repo_file(
    relative_path: str,
    content: str,
    create_dirs: bool = True,
    # VFINAL5: Trusted execution context parameters
    execution_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    episode_id: str | None = None,
) -> dict[str, Any]:
    # VFINAL5: Require trusted execution context for self-update
    if not execution_id or not run_id:
        return {"status": "error", "detail": "Authorization denied: missing execution context (execution_id, run_id required)"}
    
    # VFINAL5: Acquire capability for EXISTING execution
    lease_id = None
    capability_execution_id = None
    
    if capability_action_bridge:
        try:
            from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_existing_execution
            capability = acquire_capability_for_existing_execution(
                execution_id=execution_id,
                run_id=run_id,
                action='WRITE_REPOSITORY_FILE',
                target=f'file:{relative_path}',
                requested_scope='self_update',
                invocation_id='write_repo_file',
                episode_id=episode_id,
                session_id=session_id,
            )
            lease_id = capability.get('lease_id')
            capability_execution_id = capability.get('execution_id')
        except Exception as e:
            # Authority unavailable - FAIL CLOSED
            return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
    else:
        # Authority unavailable - FAIL CLOSED
        return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
    
    # C-2-CRIT-3: Thin wrapper calling tested implementation
    return write_repo_file_impl(
        workspace_root=Path(workspace_root_fn()),
        relative_path=relative_path,
        content=content,
        create_dirs=create_dirs,
        governance_fn=governance_fn,
        capability_action_bridge=capability_action_bridge,
        lease_id=lease_id,
        execution_id=capability_execution_id,
    )
```

**Key Changes (VFINAL5):**
- Added parameters: execution_id, run_id, session_id, episode_id
- Changed to use `acquire_capability_for_existing_execution()`
- Fail-closed if execution context missing
- Fail-closed if authority unavailable
- Same pattern applied to apply_text_patch and git_commit_and_push

---

## Complete Production Flow (VFINAL5)

```
IABV Execution (ToolTask with run_id, execution_id, session_id)
    ↓
MCP invocation (external client passes execution context)
    ↓
IABVMCPServer (receives execution_id, run_id, session_id, episode_id)
    ↓
MCP tool wrapper (write_repo_file with execution context)
    ↓
acquire_capability_for_existing_execution(execution_id, run_id, ...)
    ↓
AuthorityClient.verify_execution_context()
    ↓
AuthorityService.handle_verify_execution_context()
    ↓
Validation: execution exists in RunRecord
    ↓
Validation: client PID matches RunRecord consumer_pid
    ↓
Validation: generation matches current authority generation
    ↓
AuthorityClient.issue_lease() (for EXISTING execution)
    ↓
genuine lease_id (NEW lease for existing execution)
    ↓
SAME execution_id (no new execution created)
    ↓
SAME run_id (no new execution created)
    ↓
write_repo_file_impl(lease_id, execution_id)
    ↓
ActionRequest(lease_id, execution_id, action, target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
AuthorityService.consume_lease()
    ↓
authorized
    ↓
actual self-update side effect
    ↓
Causal attribution preserved (same execution_id, run_id)
```

**Causal Attribution Preservation:**
- execution_id: SAME as original IABV ToolTask execution_id
- run_id: SAME as original IABV ToolTask run_id
- lease_id: NEW lease for existing execution (one per MCP invocation)
- No per-call execution creation
- Full causal chain preserved end-to-end

---

## Test Coverage (VFINAL5)

### Production Path Tests
- File: `tests/test_c2_self_update_mcp_production_path.py`
- Tests MCP wrapper requires execution context
- Tests MCP wrapper uses existing execution context
- Tests fail-closed behavior for missing/invalid context

### Negative Security Tests (10 scenarios)
- Missing execution_id
- Missing run_id
- No context at all
- Forged execution_id (non-existent)
- Cross-execution context (PID mismatch)
- Cross-session context
- Cross-episode context
- Generation mismatch
- Authority unavailable
- No capability_action_bridge

### Authority E2E Tests
- File: `tests/test_c2_vfinal5_authority_e2e.py`
- Tests register_execution creates new execution
- Tests verify_execution_context validates existing execution
- Tests acquire_capability_for_existing_execution reuses execution
- Tests causal attribution preservation across multiple invocations
- Tests verify_execution_context fails for non-existent execution

---

## Status (VFINAL5)

**REAL_EXECUTION_CONTEXT_SOURCE:** ToolTask (canonical) → AuthorityClient.register_execution()  
**REAL_CAPABILITY_SOURCE:** AuthorityClient.issue_lease()  
**REAL_LEASE_SOURCE:** Authority process (via AuthorityClient)  
**CONTEXT_PROPAGATION_MECHANISM:** ✅ IMPLEMENTED (MCP protocol with authority validation)  
**PRODUCTION_INTEGRATION:** ✅ COMPLETE  
**CAUSAL_ATTRIBUTION:** ✅ PRESERVED

---

## Security Guarantees (VFINAL5)

1. **Execution Context Validation**
   - Authority validates execution exists in RunRecord database
   - Authority validates client PID matches RunRecord consumer_pid
   - Authority validates generation matches current authority generation

2. **Fail-Closed Behavior**
   - Missing execution context → rejection
   - Invalid execution context → rejection
   - Authority unavailable → rejection
   - No capability_action_bridge → rejection

3. **No New Execution Creation**
   - MCP self-update uses existing execution context
   - No per-call execution creation
   - Causal attribution preserved end-to-end

4. **Trust Model**
   - Raw MCP arguments are NOT trusted as authoritative identity
   - Authority validation via VERIFY_EXECUTION_CONTEXT is required
   - Prevents forged context, cross-execution/session/episode misuse, generation mismatch attacks

---

## Conclusion (VFINAL5)

**Causal Attribution:** Preserved end-to-end from IABV ToolTask through MCP invocation, capability acquisition, ActionRequest, authority consumption, self-update, observation, and persistence.

**Mechanism:** Trusted execution context passed via MCP protocol with authority validation using VERIFY_EXECUTION_CONTEXT operation.

**Security:** Fail-closed behavior with comprehensive validation prevents unauthorized self-update operations.
