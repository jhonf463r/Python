# C2 EXECUTION CONTEXT SEMANTICS AUDIT

**Date:** 2026-08-24  
**Component:** P0.213 Authority System - C2 Execution Context Investigation

---

## Executive Summary

Claude's audit identified a critical architectural question: Does `acquire_capability_for_execution()` obtain capability for the EXISTING IABV execution context, or does it create a NEW execution on every MCP invocation?

This audit traces the execution context flow to answer this question definitively.

---

## Execution Context Audit

### acquire_capability_for_execution() Implementation

**File:** `src/iabv_v15/services/trust/capability_lifecycle.py`  
**Lines:** 18-93

**Key Code:**
```python
def acquire_capability_for_execution(
    *,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
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
```

### AuthorityClient.register_execution() Implementation

**File:** `src/iabv_v15/services/trust/authority_client.py`  
**Lines:** 311-353

**Key Code:**
```python
def register_execution(
    self,
    invocation_id: str,
    action: str,
    target: str,
    requested_scope: str,
    task_context: Optional[str] = None,
    episode_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> dict[str, Any]:
    request = AuthorityRequest(
        request_type="REGISTER_EXECUTION",
        data=RegisterExecutionRequest(
            invocation_id=invocation_id,
            action=action,
            target=target,
            requested_scope=requested_scope,
            task_context=task_context,
            episode_id=episode_id,
            session_id=session_id
        ).to_dict(),
        request_id=invocation_id
    )
    response = self._send_request(request)
    
    if not response.success:
        raise RuntimeError(f"Failed to register execution: {response.error}")
    
    return response.data
```

### MCP Wrapper Implementation

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`  
**Lines:** 369-401 (write_repo_file example)

**Key Code:**
```python
# C2 PRODUCTION INTEGRATION: Acquire capability from authority
lease_id = None
execution_id = None

if capability_action_bridge:
    try:
        from iabv_v15.services.trust.capability_lifecycle import acquire_capability_for_execution
        capability = acquire_capability_for_execution(
            action='WRITE_REPOSITORY_FILE',
            target=f'file:{relative_path}',
            requested_scope='self_update',
            invocation_id='write_repo_file',
        )
        lease_id = capability.get('lease_id')
        execution_id = capability.get('execution_id')
    except Exception as e:
        # Authority unavailable - FAIL CLOSED
        return {"status": "error", "detail": f"Authorization denied: capability acquisition failed: {e}"}
else:
    # Authority unavailable - FAIL CLOSED
    return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
```

---

## Execution Context Analysis

### NEW_EXECUTION_PER_MCP_INVOCATION = YES

**Evidence:**

1. **MCP wrapper calls `acquire_capability_for_execution()`** on each invocation
2. **`acquire_capability_for_execution()` creates a new `AuthorityClient()`** each call
3. **`AuthorityClient.register_execution()` is called** with the authority process
4. **Authority process generates new `run_id` and `execution_id`** for each registration
5. **No existing execution context is passed** to `acquire_capability_for_execution()`

**Parameters Passed:**
- `invocation_id='write_repo_file'` (hardcoded string, not existing execution ID)
- `action='WRITE_REPOSITORY_FILE'`
- `target=f'file:{relative_path}'`
- `requested_scope='self_update'`
- `episode_id=None` (not passed)
- `session_id=None` (not passed)

### EXISTING_EXECUTION_REUSED = NO

**Evidence:**

1. **No existing `run_id` is passed** to `acquire_capability_for_execution()`
2. **No existing `execution_id` is passed** to `acquire_capability_for_execution()`
3. **No existing `episode_id` is passed** to `acquire_capability_for_execution()`
4. **No existing `session_id` is passed** to `acquire_capability_for_execution()`
5. **No existing `generation` is passed** to `acquire_capability_for_execution()`

---

## Causality Analysis

### CAUSAL_EXECUTION_BINDING = BROKEN

**Problem:**

The IABV execution that causes the MCP invocation is NOT the execution that receives the capability.

**Causal Chain:**
```
IABV Execution (existing, with run_id, execution_id, episode_id, session_id)
    ↓
IABV invokes MCP tool (write_repo_file)
    ↓
MCP wrapper calls acquire_capability_for_execution()
    ↓
AuthorityClient.register_execution() creates NEW execution
    ↓
NEW execution_id (unrelated to IABV execution)
    ↓
NEW lease_id bound to NEW execution
    ↓
Self-update attributed to NEW execution, not IABV execution
```

**Gap:**

The self-update operation is causally attributed to a NEW execution created by the authority process, not the IABV execution that actually requested the self-update.

**Implication:**

If the IABV execution is later audited, the self-update will NOT appear in its causal history. The self-update will appear in the history of the NEW execution created by the authority process, which has no relationship to the IABV execution.

---

## Session/Episode/Generation Binding

### EXISTING_EXECUTION_CONTEXT = NOT_PASSED

**Values Not Passed:**
- `EXISTING_RUN_ID = None` (not passed to acquire_capability_for_execution)
- `EXISTING_EPISODE_ID = None` (not passed to acquire_capability_for_execution)
- `EXISTING_SESSION_ID = None` (not passed to acquire_capability_for_execution)
- `EXISTING_GENERATION = None` (not passed to acquire_capability_for_execution)

### CAPABILITY_EXECUTION_BINDING = NEW_EXECUTION

**The capability is bound to:**
- NEW run_id (generated by authority)
- NEW execution_id (generated by authority)
- NO episode_id (None passed)
- NO session_id (None passed)

**Cross-Run/Episode/Session Rejection:**

The current implementation does NOT pass existing context, so there is no cross-run/episode/session rejection to verify. The authority process will accept the NEW execution registration regardless of the IABV execution context.

---

## Architectural Assessment

### Current Architecture

**Each MCP invocation creates a NEW execution in the authority process.**

**Is this the intended architecture?**

**UNKNOWN** - This is not documented as the intended architecture. The authority protocol supports passing `episode_id` and `session_id` to bind the capability to an existing execution context, but the MCP wrappers do not pass these values.

### Recommended Architecture

**For causal attribution, the MCP wrappers should:**

1. **Obtain the existing IABV execution context** from the IABV runtime
2. **Pass the existing `run_id`, `execution_id`, `episode_id`, `session_id`** to `acquire_capability_for_execution()`
3. **Authority process should bind the capability to the existing execution** (or reject if the execution is not authorized for self-update)
4. **Self-update should be causally attributed to the IABV execution** that requested it

### Alternative Architecture

**If the intended architecture is to create a NEW execution for each MCP invocation:**

1. **This should be explicitly documented** as the intended architecture
2. **The causal gap should be acknowledged** and addressed (e.g., by linking the NEW execution to the IABV execution in the authority)
3. **Audit trails should account for this gap** (e.g., by recording the IABV execution that caused the MCP invocation)

---

## Conclusion

**NEW_EXECUTION_PER_MCP_INVOCATION = YES**  
**EXISTING_EXECUTION_REUSED = NO**  
**CAUSAL_EXECUTION_BINDING = BROKEN**

The current implementation creates a NEW execution for each MCP invocation and does NOT preserve causal attribution to the IABV execution that requested the self-update. This is a critical architectural gap that must be resolved before C2 can be considered complete.

**Required Resolution:**

1. **Explicitly document the intended execution context semantics**
2. **If causal attribution is required**, modify MCP wrappers to pass existing IABV execution context
3. **If NEW execution is intended**, document the rationale and address the causal gap
4. **Verify the authority process supports the intended semantics**

---

## Implementation Gate Status

**IMPLEMENTATION_GATE = NOT_READY**

**Root Blocker:** Execution context semantics are unknown and causal attribution is broken.

**NEXT_DECISION:** Resolve execution context semantics before proceeding with VFINAL5.
