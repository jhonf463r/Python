# PHASE 10 — Real MCP Self-Update Integration

**Date:** 2026-08-24
**Baseline:** P0_213_VFINAL5_BASELINE (903d2af393071f0dd52efb0e87d465e9534dd650)
**Branch:** p0213/vfinal5-r2-security-fixes

---

## MCP Self-Update Tools Integration

**File:** `src/iabv_v15/infra/mcp/self_update_tools.py`

### Existing MCP Tools:

1. **write_repo_file** (lines 350-418)
2. **apply_text_patch** (lines 425-490)
3. **git_commit_and_push** (lines 497-560)

### Integration with Authority Policy:

All three MCP tools already correctly integrate with the authority policy:

#### write_repo_file:
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

#### apply_text_patch:
```python
capability = acquire_capability_for_existing_execution(
    execution_id=execution_id,
    run_id=run_id,
    action='APPLY_PATCH',
    target=f'file:{relative_path}',
    requested_scope='self_update',
    invocation_id='apply_text_patch',
    episode_id=episode_id,
    session_id=session_id,
)
```

#### git_commit_and_push:
```python
capability = acquire_capability_for_existing_execution(
    execution_id=execution_id,
    run_id=run_id,
    action='COMMIT',
    target='repository:workspace',
    requested_scope='self_update',
    invocation_id='git_commit_and_push',
    episode_id=episode_id,
    session_id=session_id,
)
```

### VFINAL5-R2 Policy Enforcement:

The MCP tools now benefit from the new policy constraints:

1. **Action Validation:** Each tool passes a specific action (WRITE_REPOSITORY_FILE, APPLY_PATCH, COMMIT)
2. **Target Validation:** Each tool passes a specific target (file:, repository:, remote:)
3. **Security-Critical Path Protection:** The policy rejects targets containing services/trust/, security/, authority, bootstrap.py, .git/config, .git/hooks
4. **Fail-Closed Behavior:** Authority unavailable results in denial

### Execution Flow:

```
MCP Tool (write_repo_file)
  ↓
acquire_capability_for_existing_execution
  ↓
AuthorityClient.register_execution (if first call)
  ↓
AuthorityClient.verify_execution_context
  ↓
AuthorityService.handle_verify_execution_context
  ↓
Session/Episode validation (NEW in VFINAL5-R2)
  ↓
AuthorityProtocol.apply_authorization_policy
  ↓
Action/Target constraints (NEW in VFINAL5-R2)
  ↓
Security-critical path check (NEW in VFINAL5-R2)
  ↓
CapabilityActionBridge.authorize_action
  ↓
AuthorityService.handle_issue_lease
  ↓
Lease with action/target binding
  ↓
MCP Tool execution
  ↓
CapabilityActionBridge.consume_capability
  ↓
AuthorityService.handle_consume_lease
  ↓
Action/Target binding verification (already in baseline)
  ↓
Side effect execution
```

### Status:

**MCP_INTEGRATION:** VERIFIED
**ACTION_TARGET_PASSING:** CORRECT
**POLICY_ENFORCEMENT:** APPLIED
**FAIL_CLOSED_BEHAVIOR:** PRESERVED

---

## Summary

The MCP self-update tools are correctly integrated with the new VFINAL5-R2 policy constraints. No changes to the MCP tools were required - the policy enforcement happens in the authority service layer.

The tools now:
- Pass specific actions (not blank-check)
- Pass specific targets (not blank-check)
- Benefit from session/episode validation
- Benefit from security-critical path protection
- Maintain fail-closed behavior for authority unavailability

---

## Next Steps

Proceed to PHASE 11: Negative self-update test matrix - 13 test cases for comprehensive negative testing.
