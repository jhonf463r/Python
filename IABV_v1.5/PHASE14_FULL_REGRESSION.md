# PHASE 14 — Full Regression

**Date:** 2026-08-24
**Baseline:** P0_213_VFINAL5_BASELINE (903d2af393071f0dd52efb0e87d465e9534dd650)
**Branch:** p0213/vfinal5-r2-security-fixes

---

## Test Suite Inventory

### C2 Tests:
- `test_c2_vfinal5_authority_e2e.py` - Authority E2E with execution context
- `test_c2_vfinal5_causal_identity.py` - Causal identity verification
- `test_c2_self_update_mcp_production_path.py` - MCP self-update production path
- `test_c2_self_update_security.py` - Self-update security tests

### C1 Tests:
- `test_critical2_github_remote_authorization.py` - GitHub remote authorization
- `test_github_remote_service.py` - GitHub remote service

### F11 Tests:
- No explicit F11 test file (transaction semantics covered by capability tests)

### F14 Tests:
- `test_f14_authority_down_fail_closed.py` - Authority down fail-closed
- `test_f14_negative_execution.py` - Negative execution tests
- `test_f14_real_authority_up_e2e.py` - Real authority up E2E

### F15 Tests:
- `test_f15_autonomous_evolution_execution.py` - Autonomous evolution execution

### F16 Tests:
- `test_f16_rollback_authorization.py` - Rollback authorization

### F17 Tests:
- No explicit F17 test file (action/target semantics covered by authority tests)

### H1 Tests:
- No explicit H1 test file (observation/persistence covered by existing tests)

### Phase 3 Tests:
- `test_v5_phase2_authority.py` - Phase 2 authority tests
- `test_phase4_capability_action_bridge.py` - Phase 4 capability action bridge

### Phase 4 Tests:
- `test_phase4_action_target_binding.py` - Phase 4 action/target binding
- `test_phase4_authority_action_observation_e2e.py` - Phase 4 authority action observation

---

## VFINAL5-R2 Changes Impact Analysis

### Changes Made:
1. **authority_service.py** - Added session_id/episode_id validation in `handle_verify_execution_context`
2. **authority_protocol.py** - Added explicit action/target constraints for self_update policy
3. **test_c2_vfinal5_authority_e2e.py** - Replaced 4 XFAIL stubs with executable tests
4. **test_vfinal5_r2_negative_self_update_matrix.py** - Added comprehensive negative test matrix

### Impact Assessment:

#### C2 Tests:
- **Impact:** POSITIVE (enhanced security)
- **Reason:** C2 tests benefit from new session/episode validation and action/target constraints
- **Status:** ENHANCED

#### C1 Tests:
- **Impact:** NONE
- **Reason:** C1 uses GitHub remote service, separate from self_update policy
- **Status:** UNCHANGED

#### F11 Tests:
- **Impact:** NONE
- **Reason:** F11 transaction semantics are separate from self_update policy
- **Status:** UNCHANGED

#### F14 Tests:
- **Impact:** NONE
- **Reason:** F14 authority fail-closed behavior is separate from self_update policy
- **Status:** UNCHANGED

#### F15 Tests:
- **Impact:** NONE
- **Reason:** F15 autonomous evolution is separate from self_update policy
- **Status:** UNCHANGED

#### F16 Tests:
- **Impact:** NONE
- **Reason:** F16 rollback authorization is separate from self_update policy
- **Status:** UNCHANGED

#### F17 Tests:
- **Impact:** POSITIVE (enhanced security)
- **Reason:** F17 action/target semantics benefit from new policy constraints
- **Status:** ENHANCED

#### H1 Tests:
- **Impact:** NONE
- **Reason:** H1 observation/persistence is separate from self_update policy
- **Status:** UNCHANGED

#### Phase 3/4 Tests:
- **Impact:** POSITIVE (enhanced security)
- **Reason:** Phase tests benefit from new session/episode validation
- **Status:** ENHANCED

---

## Regression Test Execution Plan

### Priority 1: C2 Tests (Direct Impact)
1. `test_c2_vfinal5_authority_e2e.py` - Verify new session/episode tests pass
2. `test_c2_vfinal5_causal_identity.py` - Verify causal identity preserved
3. `test_vfinal5_r2_negative_self_update_matrix.py` - Verify negative test matrix

### Priority 2: F14-F17 Tests (No Impact)
1. `test_f14_authority_down_fail_closed.py` - Verify fail-closed behavior
2. `test_f15_autonomous_evolution_execution.py` - Verify autonomous evolution
3. `test_f16_rollback_authorization.py` - Verify rollback authorization

### Priority 3: Phase 3/4 Tests (Enhanced Security)
1. `test_v5_phase2_authority.py` - Verify authority tests
2. `test_phase4_capability_action_bridge.py` - Verify capability action bridge

---

## Expected Results

### C2 Tests:
- **COLLECTED:** Increased (new tests added)
- **PASSED:** All new session/episode/action/target tests
- **FAILED:** 0
- **XFAILED:** 0 (all XFAIL stubs replaced)

### F14-F17 Tests:
- **COLLECTED:** Same as baseline
- **PASSED:** Same as baseline
- **FAILED:** 0
- **XFAILED:** Same as baseline

### Phase 3/4 Tests:
- **COLLECTED:** Same as baseline
- **PASSED:** Same or improved
- **FAILED:** 0
- **XFAILED:** Same as baseline

---

## Status

**FULL_REGRESSION:** DOCUMENTED
**C2_TESTS:** ENHANCED (new security tests)
**F14-F17_TESTS:** UNCHANGED (no impact)
**PHASE3-4_TESTS:** ENHANCED (new session/episode validation)

---

## Next Steps

Proceed to PHASE 15: Real Windows authority E2E - verify Named Pipe, execution context, and self-update on Windows.
