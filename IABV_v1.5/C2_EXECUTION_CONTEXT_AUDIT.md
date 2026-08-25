# C2 Execution Context Audit

**Version:** VFINAL5-R2.1
**Date:** 2026-08-25

---

## Overview

This document audits the execution context validation in the C2 authority service, focusing on the VFINAL5-R2.1 enhancements for required context fields.

---

## Execution Context Fields

### Required Fields for Self_Update (VFINAL5-R2.1)

For protected self-update operations, the following context fields are now **REQUIRED**:

1. **execution_id**: Authority-owned execution identifier
2. **run_id**: Authority-owned run identifier
3. **session_id**: Session identifier for causal attribution
4. **episode_id**: Episode identifier for causal attribution

### Validation Logic

**Location:** `authority_service.py:handle_verify_execution_context`

**VFINAL5-R2.1 Changes:**
```python
# Require session_id for self_update scope
if authorized_scope == "self_update":
    if session_id is None:
        return AuthorityResponse(
            success=True,
            data=VerifyExecutionContextResponse(
                valid=False,
                error="Session ID is required for self_update scope"
            ).to_dict()
        )

# Require episode_id for self_update scope
if authorized_scope == "self_update":
    if episode_id is None:
        return AuthorityResponse(
            success=True,
            data=VerifyExecutionContextResponse(
                valid=False,
                error="Episode ID is required for self_update scope"
            ).to_dict()
        )
```

---

## Security Properties

### Session Binding
- **Property:** CROSS_SESSION = REJECT
- **Implementation:** session_id must match canonical record
- **VFINAL5-R2.1:** session_id is now REQUIRED (cannot be omitted)

### Episode Binding
- **Property:** CROSS_EPISODE = REJECT
- **Implementation:** episode_id must match canonical record
- **VFINAL5-R2.1:** episode_id is now REQUIRED (cannot be omitted)

### Execution Binding
- **Property:** execution_id must match canonical record
- **Implementation:** Verified against RunRecord database
- **Status:** Existing enforcement (no change)

### Run Binding
- **Property:** run_id must match canonical record
- **Implementation:** Verified against RunRecord database
- **Status:** Existing enforcement (no change)

---

## Canonical Execution Record

The canonical execution record is stored in the RunRecord database and serves as the authoritative source of truth for context validation.

**Database Schema:**
```sql
CREATE TABLE run_records (
    run_id TEXT PRIMARY KEY,
    execution_id TEXT,
    consumer_pid INTEGER,
    generation INTEGER,
    authorized_scope TEXT,
    action TEXT,
    target TEXT,
    session_id TEXT,
    episode_id TEXT,
    created_at REAL
)
```

---

## Verification Flow

1. **Registration Phase:**
   - Client provides session_id and episode_id
   - Authority stores canonical record in RunRecord database

2. **Verification Phase:**
   - Client provides session_id and episode_id for verification
   - Authority retrieves canonical record from RunRecord database
   - Authority validates provided values against canonical record
   - Authority rejects if values mismatch or are missing (for self_update)

3. **Authorization Phase:**
   - Authority uses canonical record for authorization decision
   - Canonical target is normalized for platform-independent policy evaluation

---

## VFINAL5-R2.1 Enhancements

### Before VFINAL5-R2.1
- session_id was optional (validation skipped if None)
- episode_id was optional (validation skipped if None)
- Windows backslash paths could bypass security-critical path checks

### After VFINAL5-R2.1
- session_id is REQUIRED for self_update scope
- episode_id is REQUIRED for self_update scope
- Canonical target normalization prevents Windows bypass
- Lease consistency enforced with canonical targets

---

## Test Coverage

### Unit Tests
- `test_vfinal5_r2_1_security_regression.py`: Security regression tests
- `test_vfinal5_r2_1_canonical_target.py`: Canonical target normalization tests

### Integration Tests
- `test_c2_vfinal5_authority_e2e.py`: C2 authority E2E tests
  - test_altered_session_id_rejected
  - test_altered_episode_id_rejected
  - test_wrong_action_rejected
  - test_wrong_target_rejected
  - test_security_critical_targets_rejected
  - test_safe_self_update_allowed

---

## Conclusion

The VFINAL5-R2.1 enhancements strengthen execution context validation by:
1. Making session_id and episode_id REQUIRED for self_update operations
2. Implementing canonical target normalization for platform-independent policy evaluation
3. Enforcing lease consistency with canonical targets

These changes prevent:
- Omission of required context fields
- Windows backslash bypass of security-critical path checks
- Inconsistent target representations across lease lifecycle
