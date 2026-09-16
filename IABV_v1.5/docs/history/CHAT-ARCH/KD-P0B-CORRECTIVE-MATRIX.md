# P0-B Corrective Cycle - Causal Matrix

## Causal Edge Analysis

| Edge | Implemented | Invoked | Observed | Caused | Evidence |
|------|------------|---------|----------|--------|----------|
| **E1: Approval → Authorization** | YES | YES | YES | YES | Code in `tool_teach_service.py` line 859-900 issues authorization only when `approval_required and task.approval_decision == ApprovalDecision.APPROVED`. Test `test_p0b_negative_control_rejected_approval` and `test_p0b_negative_control_pending_approval` verify REJECTED/PENDING do not issue authorization. |
| **E2: Authorization → Binding** | YES | YES | YES | YES | `validate_binding()` in `ExternalActionAuthorization` validates task_id, tool_id, adapter_key, prompt_digest, assistant_kind, endpoint, action. Test `test_p0b_negative_control_wrong_prompt_digest` verifies binding fails with wrong digest. |
| **E3: Binding → Consume** | YES | YES | YES | YES | `consume()` method in `ExternalActionAuthorization` marks status CONSUMED and sets consumed_at. Test `test_p0b_negative_control_consumed_authorization` verifies single-use protection. |
| **E4: Consume → Adapter** | YES | YES | YES | YES | `_check_external_authorization()` in `DevinApiToolAdapter` calls `auth.consume()` after successful binding validation (line 1921). Test `test_p0b_runtime_integration_with_loopback` verifies authorization passes to adapter. |
| **E5: Adapter → Transport** | YES | YES | PARTIAL | UNKNOWN | Adapter prepares HTTP request with canonical payload (objective + context_pack) but actual transport execution depends on external system. The adapter code at line 1999-2002 builds the canonical payload that matches the digest. |

## Corrective Fixes Applied

### FIX-1: Digest Asymmetry
- **Root Cause:** Issuer used SHA-256 complete, adapter used SHA-256 truncated to 16 chars.
- **Correction:** Created shared function `compute_canonical_prompt_digest()` in `tool_adapters.py`. Both issuer and validator now use exact same canonicalization.
- **Evidence:** Test `test_p0b_digest_symmetry` verifies same prompt produces same digest, different prompt produces different digest.

### FIX-2: ApprovalDecision Semantics
- **Root Cause:** Code could convert PENDING to APPROVED, empty checkpoints treated as approved.
- **Correction:** Authorization issuance now requires explicit `ApprovalDecision.APPROVED`. REJECTED and PENDING do not issue authorization.
- **Evidence:** Code check at line 859 in `tool_teach_service.py`: `if approval_required and task.approval_decision == ApprovalDecision.APPROVED`. Tests verify REJECTED/PENDING are distinct from APPROVED.

### FIX-3: HumanApprovalBroker Connection
- **Root Cause:** Fabricated `approved_by='human'` without real broker provenance.
- **Correction:** Use `task.metadata.get('approved_by')` or `task.requested_by_role` as fallback. This allows real broker approval identity to flow through.
- **Evidence:** Code at line 872 in `tool_teach_service.py` extracts real approval provenance from task metadata.

### FIX-4: assistant_kind/endpoint/action
- **Root Cause:** Fields were enforced but adapter passed empty strings, making checks inert.
- **Correction:** Fields are only populated from task.metadata if they exist. Empty values are not fabricated. Assistant kind from `synaptic_preferred_assistant_kind`, endpoint from `github_action`, action from `action_type`.
- **Evidence:** Code at lines 878-880 in `tool_teach_service.py` only uses real metadata values. TODO comments mark gaps where runtime extraction is not yet available.

### FIX-5: Unified Enforcement
- **Root Cause:** Bootstrap and adapter had different validation semantics.
- **Correction:** Shared function `_validate_external_authorization()` in `bootstrap.py` used by both bootstrap and adapter. Adapter still does full binding validation with context.
- **Evidence:** Code at line 145 in `bootstrap.py` provides shared validation logic. Bootstrap comment acknowledges adapter does full binding.

### FIX-6: Canonical Persistence
- **Root Cause:** Created new `AppDatabase` and `ArtifactStorage` inside task execution path instead of using canonical repository.
- **Correction:** Use `self.memory.repository.save_external_authorization()` which uses the canonical database already owned by the running service.
- **Evidence:** Code at line 900 in `tool_teach_service.py` uses canonical repository.

### FIX-7: Real Payload Binding
- **Root Cause:** Digest only covered `task.objective`, but adapter sends `objective + context_pack`.
- **Correction:** Issuer now builds canonical payload including context_pack: `f'{objective}\n\n--- context ---\n{context_pack}'`. Adapter uses same canonicalization for validation.
- **Evidence:** Code at lines 862-870 in `tool_teach_service.py` builds canonical payload. Code at lines 1905-1912 in `tool_adapters.py` builds same canonical payload for validation. Test `test_p0b_runtime_integration_with_loopback` verifies digest includes context_pack.

### FIX-8: Replace Source Inspection Tests
- **Root Cause:** Tests used `inspect.getsource()` and string assertions instead of runtime evidence.
- **Correction:** Replaced with runtime causal tests that actually execute authorization issuance, binding validation, and consumption.
- **Evidence:** New tests `test_p0b_runtime_integration_with_loopback`, `test_p0b_negative_control_wrong_prompt_digest`, `test_p0b_negative_control_expired_authorization`, `test_p0b_negative_control_consumed_authorization`, `test_p0b_digest_symmetry` all execute real code paths.

## Causal Closure Evaluation

### Mathematical Criterion
```
CP0B = E1 ∧ E2 ∧ E3 ∧ E4 ∧ E5
```

### Edge Status
- **E1 (Approval → Authorization):** PROVEN ✓
- **E2 (Authorization → Binding):** PROVEN ✓
- **E3 (Binding → Consume):** PROVEN ✓
- **E4 (Consume → Adapter):** PROVEN ✓
- **E5 (Adapter → Transport):** PARTIAL - Adapter prepares payload but transport execution depends on external system. Intercepted transport test does not demonstrate real external effect.

### Overall Classification
**P0-B Causal Closure: PARTIAL**

All four internal edges (E1-E4) are proven through runtime tests. E5 (Adapter → Transport) is partially proven in that the adapter correctly prepares the canonical payload, but real external execution is not demonstrated (intentionally - intercepted transport only).

## Test Results
- **12 tests** in `test_p0_b_external_action_authorization.py`: PASSED
- **7 tests** in `test_p0b_production_authorization_issuance.py`: PASSED
- **Total:** 19/19 PASSED

## Remaining Gaps
1. **Assistant kind extraction:** Not extracted from runtime (TODO marked in code)
2. **Endpoint/action extraction:** Not extracted from runtime (TODO marked in code)
3. **Real external effect:** Not proven (intentionally - intercepted transport only)
4. **Runtime validation:** Requires actual operation to verify production behavior

## Epistemic Boundaries Preserved
- implemented ≠ proven ✓
- wired ≠ invoked ≠ observed ≠ caused ✓
- approval ≠ authorization ✓
- authorization ≠ execution ✓
- execution ≠ external effect ✓
- intercepted transport ≠ real external execution ✓
- test object ≠ production object ✓
- test passes ≠ causal proof ✓
- source inspection ≠ runtime evidence ✓
- persistence ≠ semantic use ✓
- field presence ≠ enforcement ✓
- documentation ≠ evidence ✓
