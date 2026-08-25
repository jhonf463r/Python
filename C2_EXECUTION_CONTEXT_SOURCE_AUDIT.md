# C2 EXECUTION CONTEXT SOURCE AUDIT (VFINAL5)

**Date:** 2026-08-24 (Updated for VFINAL5)  
**Component:** P0.213 Authority System - C2 Execution Context Investigation  
**Status:** RESOLVED - Option A Implemented

---

## Canonical Execution Context Sources

### CANONICAL_EXECUTION_CONTEXT_FILE = src/iabv_v15/domain/models.py

### CANONICAL_EXECUTION_CONTEXT_CLASS = ToolTask

**File:** `src/iabv_v15/domain/models.py`  
**Lines:** 1299-1322

**Fields:**
```python
class ToolTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_id: str
    title: str
    objective: str
    requested_by_role: TaskRole = TaskRole.TOOL_USE
    status: ToolTaskStatus = ToolTaskStatus.PENDING
    actions: list[ToolAction] = Field(default_factory=list)
    rollback_actions: list[ToolAction] = Field(default_factory=list)
    execution_scope: str = "read_only"
    approval_decision: ApprovalDecision = ApprovalDecision.PENDING
    sandbox_first: bool = True
    site_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    pack_id: str = ""
    expected_outcome: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    # F14: Authority integration fields
    execution_id: str | None = None
    lease_id: str | None = None
    action: str | None = None
    target: str | None = None
```

### CANONICAL_RUN_ID_SOURCE = ToolTask.run_id

### CANONICAL_EXECUTION_ID_SOURCE = ToolTask.execution_id

### CANONICAL_EPISODE_ID_SOURCE = ExecutionDossier.episode_id

**File:** `src/iabv_v15/domain/models.py`  
**Lines:** 2542-2576

```python
class ExecutionDossier(BaseModel):
    dossier_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    scope: DossierScope = DossierScope.CHAT
    title: str
    summary: str
    run_id: str | None = None
    episode_id: str | None = None
    # ... other fields
```

### CANONICAL_SESSION_ID_SOURCE = ToolTask.session_id

### CANONICAL_GENERATION_SOURCE = NOT_FOUND

**Finding:** No `generation` field exists in the current canonical execution context models. Generation is managed by the AuthorityService internally.

---

## VFINAL5 Resolution: Option A - Preserve Causal Attribution Through Trusted MCP Execution Context

### Implementation Summary

**Option A was implemented:** Pass execution context via MCP protocol with authority validation.

### Key Changes

1. **Trusted Execution Context Model**
   - File: `src/iabv_v15/services/trust/trusted_execution_context.py`
   - Created `TrustedExecutionContext` dataclass with run_id, execution_id, session_id, episode_id
   - Includes serialization/deserialization and placeholder for cryptographic proof

2. **Authority Protocol Extension**
   - File: `src/iabv_v15/services/trust/authority_protocol.py`
   - Added `VerifyExecutionContextRequest` and `VerifyExecutionContextResponse`
   - New operation: `VERIFY_EXECUTION_CONTEXT`

3. **Authority Client Extension**
   - File: `src/iabv_v15/services/trust/authority_client.py`
   - Added `verify_execution_context()` method
   - Validates existing execution context against authority's RunRecord database

4. **Authority Service Handler**
   - File: `src/iabv_v15/services/trust/authority_service.py`
   - Added `handle_verify_execution_context()` method
   - Validates execution exists, belongs to authenticated client (PID match), generation match

5. **Capability Lifecycle Refactoring**
   - File: `src/iabv_v15/services/trust/capability_lifecycle.py`
   - Added `acquire_capability_for_existing_execution()` function
   - Uses `verify_execution_context()` before issuing lease
   - Does NOT create new execution - reuses existing execution_id and run_id
   - Original `acquire_capability_for_execution()` preserved for non-MCP use

6. **MCP Tool Wrapper Updates**
   - File: `src/iabv_v15/infra/mcp/self_update_tools.py`
   - Added parameters: execution_id, run_id, session_id, episode_id
   - Changed to use `acquire_capability_for_existing_execution()`
   - Fail-closed if execution context missing or invalid
   - Updated all three tools: write_repo_file, apply_text_patch, git_commit_and_push

### New MCP Invocation Context Trace (VFINAL5)

```
IABV Execution (with ToolTask: run_id, execution_id, session_id)
    ↓
MCP invocation (external client passes execution context)
    ↓
IABVMCPServer (receives execution_id, run_id, session_id, episode_id)
    ↓
MCP tool wrapper (validates context, calls acquire_capability_for_existing_execution)
    ↓
AuthorityClient.verify_execution_context() (validates against RunRecord)
    ↓
AuthorityService.handle_verify_execution_context() (PID check, generation check)
    ↓
AuthorityClient.issue_lease() (issues lease for EXISTING execution)
    ↓
Capability acquisition with SAME execution_id and run_id
    ↓
Causal attribution preserved
```

### Security Guarantees

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

---

## Architectural Implications (VFINAL5)

### Problem (Original)

The MCP server was designed as a standalone service that does not participate in the IABV execution lifecycle. Therefore:

1. **MCP server did NOT receive ToolTask context** when a tool was invoked
2. **MCP server did NOT have access to the IABV execution that caused the invocation**
3. **MCP wrappers could not pass existing execution context** to `acquire_capability_for_execution()`

### Solution (VFINAL5 - Option A)

**Pass execution context via MCP protocol with authority validation:**

- MCP protocol extended to include execution context (execution_id, run_id, episode_id, session_id)
- MCP client (external) must obtain and pass IABV execution context
- MCP server receives and validates execution context via authority
- MCP wrappers use existing execution context via `acquire_capability_for_existing_execution()`
- Authority validates context before issuing lease

### Trust Model

**Critical Security Rule:** Raw MCP arguments for execution context are NOT trusted as authoritative identity. Authority validation is required via `VERIFY_EXECUTION_CONTEXT` operation.

The authority validates:
- Execution exists in RunRecord database
- Execution belongs to authenticated client (PID match)
- Generation matches current authority generation

This prevents:
- Forged execution context
- Cross-execution context misuse
- Cross-session context misuse
- Cross-episode context misuse
- Generation mismatch attacks

---

## Authority Semantics (VFINAL5)

### Extended Authority Protocol

**New Operation: VERIFY_EXECUTION_CONTEXT**

**AuthorityClient.verify_execution_context():**
```python
def verify_execution_context(
    self,
    execution_id: str,
    run_id: str,
    session_id: Optional[str] = None,
    episode_id: Optional[str] = None
) -> dict[str, Any]:
```

**Returns:**
```python
{
    'valid': bool,
    'consumer_pid': int (if valid),
    'generation': int (if valid),
    'authorized_scope': str (if valid),
    'error': str (if invalid)
}
```

**New Capability Acquisition Function:**

**capability_lifecycle.acquire_capability_for_existing_execution():**
```python
def acquire_capability_for_existing_execution(
    *,
    execution_id: str,
    run_id: str,
    action: str,
    target: str,
    requested_scope: str = "tool:execute",
    invocation_id: str = "tool_execution",
    episode_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

**Key Difference:**
- Does NOT call `register_execution()`
- Calls `verify_execution_context()` first
- Calls `issue_lease()` for existing execution
- Returns SAME execution_id and run_id (no new execution created)

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

## Conclusion (VFINAL5)

**CANONICAL_EXECUTION_CONTEXT = ToolTask**  
**CANONICAL_RUN_CONTEXT = ToolTask.run_id**  
**CANONICAL_EPISODE_CONTEXT = ExecutionDossier.episode_id**  
**CANONICAL_SESSION_CONTEXT = ToolTask.session_id**  
**CANONICAL_GENERATION_CONTEXT = AuthorityService._generation (internal)**

**MCP Context Gap:** RESOLVED via Option A - Trusted execution context passed via MCP protocol with authority validation.

**Architectural Decision:** Option A implemented - Preserve causal attribution through trusted MCP execution context.

**Security Model:** Raw MCP arguments are NOT trusted. Authority validation via VERIFY_EXECUTION_CONTEXT is required for all self-update operations.

**Causal Attribution:** Preserved end-to-end from IABV ToolTask through MCP invocation, capability acquisition, ActionRequest, authority consumption, self-update, observation, and persistence.
