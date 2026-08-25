# PHASE 2-5 — Session/Episode/Action/Target Binding Fix Report

**Date:** 2026-08-24
**Baseline:** P0_213_VFINAL5_BASELINE (903d2af393071f0dd52efb0e87d465e9534dd650)
**Branch:** p0213/vfinal5-r2-security-fixes

---

## PHASE 2: Session and Episode Binding

**File Modified:** `src/iabv_v15/services/trust/authority_service.py`
**Function:** `handle_verify_execution_context`
**Lines:** 957-975, 997-1017

### Changes Made:

1. **Modified SQL query** to select session_id and episode_id from run_records:
```python
cursor.execute("""
    SELECT run_id, execution_id, consumer_pid, generation, authorized_scope, session_id, episode_id
    FROM run_records
    WHERE run_id = ? AND execution_id = ?
""", (run_id, execution_id))
```

2. **Added session_id validation** (CROSS_SESSION = REJECT):
```python
# Verify session_id matches canonical record (CROSS_SESSION = REJECT)
if session_id is not None and record_session_id is not None:
    if session_id != record_session_id:
        return AuthorityResponse(
            success=True,
            data=VerifyExecutionContextResponse(
                valid=False,
                error=f"Session ID mismatch: provided '{session_id}' does not match canonical '{record_session_id}'"
            ).to_dict()
        )
```

3. **Added episode_id validation** (CROSS_EPISODE = REJECT):
```python
# Verify episode_id matches canonical record (CROSS_EPISODE = REJECT)
if episode_id is not None and record_episode_id is not None:
    if episode_id != record_episode_id:
        return AuthorityResponse(
            success=True,
            data=VerifyExecutionContextResponse(
                valid=False,
                error=f"Episode ID mismatch: provided '{episode_id}' does not match canonical '{record_episode_id}'"
            ).to_dict()
        )
```

### Test Updated:

**File:** `tests/test_c2_vfinal5_authority_e2e.py`
**Test:** `test_altered_session_id_rejected` (lines 330-370)
**Test:** `test_altered_episode_id_rejected` (lines 372-412)

Both tests now execute real verification instead of xfail stubs.

---

## PHASE 3-5: Self_Update Policy with Explicit Action/Target Constraints

**File Modified:** `src/iabv_v15/services/trust/authority_protocol.py`
**Function:** `apply_authorization_policy`
**Lines:** 487-559

### Changes Made:

Replaced blank-check self_update policy with explicit action/target constraints:

1. **Defined allowed self_update actions** with specific target scopes:
```python
allowed_self_update_actions = {
    "WRITE_REPOSITORY_FILE": "file:workspace",
    "APPLY_PATCH": "file:workspace",
    "COMMIT": "repository:authorized",
    "PUSH": "remote:authorized"
}
```

2. **Added action validation**:
```python
if input.action not in allowed_self_update_actions:
    return AuthorizationPolicyDecision(
        allowed=False,
        reason=f"Action '{input.action}' not allowed for self_update scope. Allowed actions: {list(allowed_self_update_actions.keys())}"
    )
```

3. **Added target scope validation** for each action type:
   - `file:workspace`: target must start with "file:"
   - `repository:authorized`: target must start with "repository:"
   - `remote:authorized`: target must start with "remote:"

4. **Added security-critical path protection**:
```python
security_critical_paths = [
    "services/trust/",
    "security/",
    "authority",
    "bootstrap.py",
    ".git/config",
    ".git/hooks"
]
for critical_path in security_critical_paths:
    if critical_path in input.target:
        return AuthorizationPolicyDecision(
            allowed=False,
            reason=f"Target '{input.target}' contains security-critical path '{critical_path}' - not allowed for self_update"
        )
```

5. **Added constraints to authorization decision**:
```python
constraints={
    "allowed_action": input.action,
    "allowed_target": input.target,
    "target_scope": expected_target_scope
}
```

---

## PHASE 6: Lease Binding Verification

**File:** `src/iabv_v15/services/trust/authority_service.py`
**Function:** `handle_consume_lease`
**Lines:** 879-895

### Existing Implementation (Already Present in Baseline):

The baseline already implements action/target binding verification in lease consumption:

1. **Action binding verification**:
```python
# Phase 4: Verify action binding
if requested_action != authorized_action:
    conn.close()
    return AuthorityResponse(
        success=False,
        data={},
        error=f"Action mismatch: requested '{requested_action}' but authorized '{authorized_action}'"
    )
```

2. **Target binding verification**:
```python
# Phase 4: Verify target binding
if requested_target != authorized_target:
    conn.close()
    return AuthorityResponse(
        success=False,
        data={},
        error=f"Target mismatch: requested '{requested_target}' but authorized '{authorized_target}'"
    )
```

### Status:

**LEASE_BINDING_ALREADY_IMPLEMENTED:** YES
**ACTION_BINDING_ENFORCED:** YES
**TARGET_BINDING_ENFORCED:** YES

The lease consumption path already enforces action/target matching. No changes needed.

---

## Summary of Changes

| Phase | Status | Files Modified |
|-------|--------|----------------|
| PHASE 2 | COMPLETED | authority_service.py, test_c2_vfinal5_authority_e2e.py |
| PHASE 3 | COMPLETED | authority_protocol.py |
| PHASE 4 | COMPLETED | authority_protocol.py |
| PHASE 5 | COMPLETED | authority_protocol.py |
| PHASE 6 | ALREADY IMPLEMENTED | No changes needed |

---

## Next Steps

Proceed to PHASE 7: Test security-critical targets - verify that trust/authority files are rejected by the new policy.
