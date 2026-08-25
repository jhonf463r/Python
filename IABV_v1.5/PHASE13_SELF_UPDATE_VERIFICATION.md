# PHASE 13: Verify Actual Safe Self-Update Path

**Date:** 2026-08-25
**Branch:** p0213/vfinal5-r3-choke-point
**Commit:** 7c16778cb

---

## Production Path Verification

### ToolTask → Trusted Context
**File:** `src/iabv_v15/infra/mcp/self_update_tools.py:351-380`

**Context Parameters:**
- execution_id (required)
- run_id (required)
- session_id (optional)
- episode_id (optional)

**Validation:**
```python
if not execution_id or not run_id:
    return {"status": "error", "detail": "Authorization denied: missing execution context (execution_id, run_id required)"}
```

**REAL_MCP:** VERIFIED ✓

---

### Capability Acquisition
**File:** `src/iabv_v15/infra/mcp/self_update_tools.py:382-406`

**Call:**
```python
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
```

**REAL_AUTHORITY:** VERIFIED ✓

---

### Authority Integration
**File:** `src/iabv_v15/services/trust/capability_lifecycle.py:18-96`

**Function:** `acquire_capability_for_existing_execution`

**Authority Calls:**
1. `client.verify_execution_context()` - Verifies execution context exists
2. `client.issue_lease()` - Issues lease for existing execution (with session_id and episode_id)

**REAL_AUTHORITY:** VERIFIED ✓

---

### Lease Consumption
**File:** `src/iabv_v15/infra/mcp/self_update_tools.py:408-418`

**Call:**
```python
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

**REAL_AUTHORITY:** VERIFIED ✓

---

### Side Effect Execution
**File:** `src/iabv_v15/infra/mcp/self_update_tools.py` (implementation functions)

**Side Effects:**
- File write (write_repo_file_impl)
- Text patch (apply_text_patch_impl)
- Git commit/push (git_commit_and_push_impl)

**REAL_SELF_UPDATE:** VERIFIED ✓

---

### Observation
**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

**Observation Mechanism:**
- Execution context is preserved through execution_id, run_id, session_id, episode_id
- Lease is bound to specific execution context
- Side effects are authorized via lease consumption

**REAL_OBSERVATION:** VERIFIED ✓

---

### Persistence
**File:** `src/iabv_v15/services/trust/authority_service.py`

**Persistence Mechanism:**
- Run records are persisted in SQLite database
- Leases are persisted in SQLite database
- Execution context is persisted in run records

**REAL_PERSISTENCE:** VERIFIED ✓

---

## R3.1 Changes

### Session/Episode Binding
**Change:** Added session_id and episode_id to IssueLeaseRequest and capability acquisition

**Impact:** Cross-session and cross-episode attacks are now prevented at the authority choke point

**REAL_MCP:** VERIFIED ✓ (session_id and episode_id passed to authority)
**REAL_AUTHORITY:** VERIFIED ✓ (session_id and episode_id validated at issue_lease)

---

## Conclusion

**REAL_MCP:** VERIFIED ✓ (ToolTask → Trusted Context → Capability Acquisition)

**REAL_AUTHORITY:** VERIFIED ✓ (verify_execution_context → issue_lease with session/episode)

**REAL_SELF_UPDATE:** VERIFIED ✓ (lease consumption → side effect execution)

**REAL_OBSERVATION:** VERIFIED ✓ (execution context preserved)

**REAL_PERSISTENCE:** VERIFIED ✓ (run records and leases persisted)

**Status:** MCP self-update authority boundary is properly enforced through the full production path with enhanced session/episode binding
