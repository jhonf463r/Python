# Self-Update Call Graph Audit (VFINAL5)

**Date:** 2026-08-24 (Updated for VFINAL5)  
**Component:** C-2 Self-Update Authority  
**Status:** VFINAL5 - Causal Attribution Preserved

---

## Call Graph: write_repo_file (VFINAL5)

```
IABV Execution (ToolTask with run_id, execution_id, session_id)
    ↓
MCP Client (passes execution_id, run_id, session_id, episode_id)
    ↓
write_repo_file (registered MCP tool)
    ↓
execution_id/run_id validation (VFINAL5: FAIL CLOSED if missing)
    ↓
capability_action_bridge check (C2-CRIT-1: FAIL CLOSED if None)
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
write_repo_file_impl (tested implementation)
    ↓
ActionRequest(lease_id, execution_id, action, target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
AuthorityClient.consume_lease(lease_id, execution_id, action, target)
    ↓
Real AuthorityClient (in production)
    ↓
ActionAuthorization(authorized, error, consumed_at)
    ↓
if authorized:
    governance_fn(assistant_kind="self_update", requires_network=False)
    ↓
    if block is not None: return block
    ↓
    _safe_path(relative_path)
    ↓
    sensitive path check
    ↓
    target.write_text(content)
    ↓
    return {"status": "ok", "path", "bytes_written"}
else:
    return {"status": "error", "detail": f"Authorization denied: {error}"}
```

**VFINAL5 Key Changes:**
- MCP wrapper now requires execution_id and run_id parameters
- Uses `acquire_capability_for_existing_execution()` instead of `acquire_capability_for_execution()`
- Authority validates existing execution context before issuing lease
- No new execution created per MCP invocation
- Causal attribution preserved (same execution_id, run_id)

## Call Graph: apply_text_patch (VFINAL5)

```
IABV Execution (ToolTask with run_id, execution_id, session_id)
    ↓
MCP Client (passes execution_id, run_id, session_id, episode_id)
    ↓
apply_text_patch (registered MCP tool)
    ↓
execution_id/run_id validation (VFINAL5: FAIL CLOSED if missing)
    ↓
capability_action_bridge check (C2-CRIT-1: FAIL CLOSED if None)
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
apply_text_patch_impl (tested implementation)
    ↓
ActionRequest(lease_id, execution_id, action, target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
AuthorityClient.consume_lease(lease_id, execution_id, action, target)
    ↓
Real AuthorityClient (in production)
    ↓
ActionAuthorization(authorized, error, consumed_at)
    ↓
if authorized:
    governance_fn(assistant_kind="self_update", requires_network=False)
    ↓
    if block is not None: return block
    ↓
    _safe_path(relative_path)
    ↓
    sensitive path check
    ↓
    target.read_text()
    ↓
    target.write_text(patched_content)
    ↓
    return {"status": "ok", "path", "replacements_made"}
else:
    return {"status": "error", "detail": f"Authorization denied: {error}"}
```

**VFINAL5 Key Changes:**
- MCP wrapper now requires execution_id and run_id parameters
- Uses `acquire_capability_for_existing_execution()` instead of `acquire_capability_for_execution()`
- Authority validates existing execution context before issuing lease
- No new execution created per MCP invocation
- Causal attribution preserved (same execution_id, run_id)

## Call Graph: git_commit_and_push (VFINAL5)

```
IABV Execution (ToolTask with run_id, execution_id, session_id)
    ↓
MCP Client (passes execution_id, run_id, session_id, episode_id)
    ↓
git_commit_and_push (registered MCP tool)
    ↓
execution_id/run_id validation (VFINAL5: FAIL CLOSED if missing)
    ↓
capability_action_bridge check (C2-CRIT-1: FAIL CLOSED if None)
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
git_commit_and_push_impl (tested implementation)
    ↓
ActionRequest(lease_id, execution_id, action='GIT_COMMIT', target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
AuthorityClient.consume_lease(lease_id, execution_id, action, target)
    ↓
Real AuthorityClient (in production)
    ↓
ActionAuthorization(authorized, error, consumed_at)
    ↓
if authorized:
    governance_fn(assistant_kind="self_update", requires_network=push)
    ↓
    if block is not None: return block
    ↓
    subprocess.run(['git', 'add', '-A'])
    ↓
    subprocess.run(['git', 'commit', '-m', message])
    ↓
    if push:
        ActionRequest(lease_id, execution_id, action='GIT_PUSH', target, action_context)
        ↓
        CapabilityActionBridge.authorize_action(action_request)
        ↓
        AuthorityClient.consume_lease(lease_id, execution_id, action, target)
        ↓
        ActionAuthorization(authorized, error, consumed_at)
        ↓
        if authorized:
            subprocess.run(['git', 'push'])
    ↓
    return {"status": "ok", "commit_hash", "branch", "push_output"}
else:
    return {"status": "error", "detail": f"Authorization denied: {error}"}
```

**VFINAL5 Key Changes:**
- MCP wrapper now requires execution_id and run_id parameters
- Uses `acquire_capability_for_existing_execution()` instead of `acquire_capability_for_execution()`
- Authority validates existing execution context before issuing lease
- No new execution created per MCP invocation
- Causal attribution preserved (same execution_id, run_id)

## Failure Branches

### C2-CRIT-1: Authority Unavailable
```
capability_action_bridge is None
    ↓
return {"status": "error", "detail": "Authorization denied: authority unavailable — self-update denied"}
```

### C2-CRIT-1: ActionRequest Unavailable
```
ActionRequest is None
    ↓
return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
```

### C2-CRIT-2: Missing lease_id/execution_id
```
lease_id is None or execution_id is None
    ↓
return {"status": "error", "detail": "Authorization denied: lease_id and execution_id required from capability context"}
```

### Authorization Denied
```
auth_result.authorized == False
    ↓
return {"status": "error", "detail": f"Authorization denied: {auth_result.error}"}
```

### Governance Block
```
governance_fn returns non-None
    ↓
return block (governance denial)
```

### Path Safety Check
```
_safe_path returns None (directory traversal)
    ↓
return {"status": "error", "detail": "path escapes workspace (directory traversal)"}
```

### Sensitive Path Check
```
path contains sensitive pattern (.git/config, .git/hooks, .env, secrets)
    ↓
return {"status": "error", "detail": f"cannot write to sensitive path containing '{s}'"}
```

## Security Guarantees

**C2-CRIT-1:** All self-update tools FAIL CLOSED when authority unavailable
- capability_action_bridge is None → REJECT
- ActionRequest is None → REJECT
- No graceful degradation for protected modification

**C2-CRIT-2:** All self-update tools use correct ActionRequest contract
- lease_id: required from capability context
- execution_id: required from capability context
- action: WRITE_REPOSITORY_FILE, APPLY_PATCH, GIT_COMMIT, GIT_PUSH
- target: file:{path} or git:workspace
- action_context: {'requested_scope': 'self_update'}

**C2-CRIT-3:** Single authoritative implementation
- MCP tools are thin wrappers calling tested _impl functions
- No duplicate security-sensitive logic
- Tests exercise _impl functions (which MCP wrappers call)

**Replay Protection:**
- ControlledAuthorityClient tracks consumed leases
- Second use of consumed lease → REJECT
- No second side effect on replay

**Cross-Execution Isolation:**
- Capability for execution A cannot authorize operation under execution B
- Execution binding enforced by ControlledAuthorityClient
- Cross-execution attempts → REJECT

## Production Flow (Not Yet Implemented)

The current implementation uses placeholder lease_id and execution_id for testing. In production, the flow must be:

```
Execution Registration
    ↓
Capability Issuance
    ↓
lease_id + execution_id obtained
    ↓
ActionRequest(lease_id, execution_id, action, target, action_context)
    ↓
CapabilityActionBridge.authorize_action(action_request)
    ↓
Real AuthorityService (not ControlledAuthorityClient)
    ↓
Canonical lease consumption
    ↓
Authorized side effect
```

**CRITICAL:** The production flow must obtain lease_id and execution_id from the genuine capability/execution context. The current placeholder implementation MUST be replaced before production use.
