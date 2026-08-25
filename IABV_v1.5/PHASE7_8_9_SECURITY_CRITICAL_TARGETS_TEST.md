# PHASE 7-9 — Security-Critical Targets and XFAIL Replacement Report

**Date:** 2026-08-24
**Baseline:** P0_213_VFINAL5_BASELINE (903d2af393071f0dd52efb0e87d465e9534dd650)
**Branch:** p0213/vfinal5-r2-security-fixes

---

## PHASE 7: Security-Critical Targets Test

**File Modified:** `tests/test_c2_vfinal5_authority_e2e.py`
**Test Added:** `test_security_critical_targets_rejected` (lines 458-490)

### Test Coverage:

The test verifies that all representative security-critical targets are rejected:

1. **Trust/Authority Files:**
   - `file:src/iabv_v15/services/trust/authority_service.py`
   - `file:src/iabv_v15/services/trust/capability_lifecycle.py`

2. **Security Module:**
   - `file:src/iabv_v15/security/`

3. **MCP Server:**
   - `file:src/iabv_v15/infra/mcp/server.py`

4. **Domain Models:**
   - `file:src/iabv_v15/domain/models.py`

5. **Bootstrap:**
   - `file:bootstrap.py`

6. **Git Configuration:**
   - `file:.git/config`
   - `file:.git/hooks/pre-commit`

### Test Result:

Each target is tested against the self_update policy with action `WRITE_REPOSITORY_FILE`. All targets must be rejected with reason containing "security-critical path" or "not allowed".

---

## PHASE 8: Safe Self-Update Preservation

**File Modified:** `tests/test_c2_vfinal5_authority_e2e.py`
**Test Added:** `test_safe_self_update_allowed` (lines 492-515)

### Test Coverage:

The test verifies that authorized safe targets still work:

1. **Safe Target:**
   - `file:src/iabv_v15/example_module.py`

### Test Result:

The safe target must be allowed with:
- `decision.allowed == True`
- `decision.authorized_scope == "self_update"`
- `decision.constraints` containing the authorized action and target

This ensures we haven't overcorrected by making all self-update impossible.

---

## PHASE 9: XFAIL Stub Replacement

**File Modified:** `tests/test_c2_vfinal5_authority_e2e.py`

### Replaced Tests:

1. **test_altered_session_id_rejected** (lines 330-370)
   - **Before:** `pytest.xfail("session_id validation not implemented in verify_execution_context")`
   - **After:** Executable test that registers execution with session_id, then verifies with altered session_id and expects rejection

2. **test_altered_episode_id_rejected** (lines 372-412)
   - **Before:** `pytest.xfail("episode_id validation not implemented in verify_execution_context")`
   - **After:** Executable test that registers execution with episode_id, then verifies with altered episode_id and expects rejection

3. **test_wrong_action_rejected** (lines 414-434)
   - **Before:** `pytest.xfail("action validation not implemented in verify_execution_context")`
   - **After:** Executable test that verifies unauthorized action "UNAUTHORIZED_ACTION" is rejected by self_update policy

4. **test_wrong_target_rejected** (lines 436-456)
   - **Before:** `pytest.xfail("target validation not implemented in verify_execution_context")`
   - **After:** Executable test that verifies security-critical target (services/trust/) is rejected by self_update policy

### Test Status:

All four XFAIL stubs have been replaced with executable security regression tests.

---

## Summary

| Phase | Status | Tests Added/Modified |
|-------|--------|---------------------|
| PHASE 7 | COMPLETED | test_security_critical_targets_rejected |
| PHASE 8 | COMPLETED | test_safe_self_update_allowed |
| PHASE 9 | COMPLETED | 4 XFAIL stubs replaced with executable tests |

---

## Next Steps

Proceed to PHASE 10: Test real MCP self_update - verify that write_repo_file, apply_text_patch, and git_commit_and_push work correctly with the new policy constraints.
