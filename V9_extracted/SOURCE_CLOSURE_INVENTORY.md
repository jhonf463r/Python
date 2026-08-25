# Source Closure Inventory

**Date:** 2026-08-23  
**Objective:** Complete source closure for Phase 3, Phase 4, F14/F15/F16/F17

---

## Phase 3 Source Files

### Authority Core

| File | Path | Status |
|------|------|--------|
| authority_process.py | src/iabv_v15/services/trust/authority_process.py | ✅ FOUND |
| authority_service.py | src/iabv_v15/services/trust/authority_service.py | ✅ FOUND |
| authority_server.py | src/iabv_v15/services/trust/authority_server.py | ✅ FOUND |
| authority_client.py | src/iabv_v15/services/trust/authority_client.py | ✅ FOUND |
| authority_protocol.py | src/iabv_v15/services/trust/authority_protocol.py | ✅ FOUND |

### Trust & Identity

| File | Path | Status |
|------|------|--------|
| trusted_lease.py | src/iabv_v15/services/trust/trusted_lease.py | ✅ FOUND |
| root_trust_anchor.py | src/iabv_v15/services/trust/root_trust_anchor.py | ✅ FOUND |
| trusted_execution_identity.py | src/iabv_v15/services/trust/trusted_execution_identity.py | ✅ FOUND |

### Phase 3 Tests

| File | Path | Status |
|------|------|--------|
| test_phase3_transport_integration.py | src/iabv_v15/services/trust/test_phase3_transport_integration.py | ✅ FOUND |
| test_phase3_negative_security.py | src/iabv_v15/services/phase3/test_phase3_negative_security.py | ✅ FOUND |

**CORRECTED:** Phase 3 regression tests exist in src/ directory (unusual location but present).

---

## Phase 4 Source Files

### Capability & Observation

| File | Path | Status |
|------|------|--------|
| capability_action_bridge.py | src/iabv_v15/services/trust/capability_action_bridge.py | ✅ FOUND |
| post_action_observer.py | src/iabv_v15/services/trust/post_action_observer.py | ✅ FOUND |
| capability_lifecycle.py | src/iabv_v15/services/trust/capability_lifecycle.py | ✅ FOUND |

### Phase 4 Tests

| File | Path | Status |
|------|------|--------|
| test_phase4_capability_action_bridge.py | tests/test_phase4_capability_action_bridge.py | ✅ FOUND |
| test_phase4_action_target_binding.py | tests/windows_e2e/test_phase4_action_target_binding.py | ✅ FOUND |
| test_phase4_authority_action_observation_e2e.py | tests/windows_e2e/test_phase4_authority_action_observation_e2e.py | ✅ FOUND |

---

## Tool Execution Source Files

### Core Tool Services

| File | Path | Status |
|------|------|--------|
| tool_teach_service.py | src/iabv_v15/services/tools/tool_teach_service.py | ✅ FOUND |
| tool_operational_executor.py | src/iabv_v15/services/tools/tool_operational_executor.py | ✅ FOUND |
| tool_adapters.py | src/iabv_v15/services/tools/tool_adapters.py | ✅ FOUND |
| tool_memory.py | src/iabv_v15/services/tools/tool_memory.py | ✅ FOUND |
| tool_registry.py | src/iabv_v15/services/tools/tool_registry.py | ✅ FOUND |
| tool_sandbox.py | src/iabv_v15/services/tools/tool_sandbox.py | ✅ FOUND |
| tool_validator.py | src/iabv_v15/services/tools/tool_validator.py | ✅ FOUND |
| tool_approval_policy.py | src/iabv_v15/services/tools/tool_approval_policy.py | ✅ FOUND |
| tool_rollback_manager.py | src/iabv_v15/services/tools/tool_rollback_manager.py | ✅ FOUND |

---

## F14/F15/F16/F17 Source Files

### Evolution & Autonomous Execution

| File | Path | Status |
|------|------|--------|
| autonomous_evolution_service.py | src/iabv_v15/services/evolution/autonomous_evolution_service.py | ✅ FOUND |
| tool_calling_bridge.py | src/iabv_v15/services/llm/tool_calling_bridge.py | ✅ FOUND |
| local_role_router.py | src/iabv_v15/services/roles/local_role_router.py | ✅ FOUND |

### GitHub Remote Service

| File | Path | Status |
|------|------|--------|
| github_remote_service.py | src/iabv_v15/services/tools/github_remote_service.py | ✅ FOUND |

---

## Regression Tests

### F14 Tests

| File | Path | Status |
|------|------|--------|
| test_f14_authority_down_fail_closed.py | tests/test_f14_authority_down_fail_closed.py | ✅ FOUND |
| test_f14_negative_execution.py | tests/test_f14_negative_execution.py | ✅ FOUND |
| test_f14_real_authority_up_e2e.py | tests/test_f14_real_authority_up_e2e.py | ✅ FOUND |
| test_f14_real_execution_e2e.py | tests/windows_e2e/test_f14_real_execution_e2e.py | ✅ FOUND |

**CORRECTED:** F14 regression tests exist in tests/ directory.

### F15 Tests

| File | Path | Status |
|------|------|--------|
| test_f15_autonomous_evolution_execution.py | tests/test_f15_autonomous_evolution_execution.py | ✅ FOUND |

### F16 Tests

| File | Path | Status |
|------|------|--------|
| test_f16_rollback_authorization.py | tests/test_f16_rollback_authorization.py | ✅ FOUND |

### F17 Tests

| File | Path | Status |
|------|------|--------|
| test_critical2_github_remote_authorization.py | tests/test_critical2_github_remote_authorization.py | ✅ FOUND |

### CRITICAL-1 Tests

| File | Path | Status |
|------|------|--------|
| test_critical1_tool_sandbox_semantics.py | tests/test_critical1_tool_sandbox_semantics.py | ✅ FOUND |

---

## Domain Models

| File | Path | Status |
|------|------|--------|
| domain/models.py | src/iabv_v15/domain/models.py | ✅ FOUND |

---

## Persistence

| File | Path | Status |
|------|------|--------|
| persistence/*.py | src/iabv_v15/persistence/ | 🔍 TO SCAN |

---

## Critical Findings

1. **Phase 3 regression tests exist** - Found in src/ directory (unusual location but present)
2. **F14 regression tests exist** - Found in tests/ directory (4 test files)
3. **Phase 4 tests exist** - 3 test files found (1 unit, 2 E2E)
4. **F15/F16/F17/CRITICAL-1 tests exist** - All have regression tests
5. **Persistence files exist** - Found in src/iabv_v15/infra/persistence/ (20+ files)

---

## Next Steps

1. Complete source closure inventory for all dependencies
2. Verify Phase 3 tests can run
3. Verify Phase 4 tests can run
4. Verify F14/F15/F16/F17 tests can run
5. Build complete audit bundle with full source closure
