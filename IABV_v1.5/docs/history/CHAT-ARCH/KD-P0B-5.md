# KD-P0B-5

## TITLE
Production authorization issuance was absent

## TYPE
NEGATIVE / BOUNDARY

## CLAIM
P0-B enforcement existed without a production authorization issuance path.

## EVIDENCE
Git/code audit confirmed that `ExternalActionAuthorization` instances were only created in test helpers like `_create_external_authorization()` in `test_p0_b_external_action_authorization.py` and `test_e29_synaptic_to_delegation_with_intercepted_transport.py`. No production code path existed to emit authorization objects from actual human approval decisions.

## WHAT IT PROVES
The previous positive tests demonstrated only test-created authorization objects. The production path from `ApprovalDecision.APPROVED` to `ExternalActionAuthorization` issuance was broken.

## WHAT IT DOES NOT PROVE
Real production authorization behavior before this fix. The fix establishes the causal chain but requires runtime validation in actual operation.

## NEXT TEST
Approval → authorization issuance → adapter validation → execution.

## RESOLUTION
Added production authorization issuance in `ToolTeachService.execute_task()` when `approval_required=True` and `task.approval_decision == ApprovalDecision.APPROVED`. The authorization is created with real runtime values (task_id, tool_id, adapter_key, assistant_kind, prompt_digest) and persisted via `ToolRecordRepository.save_external_authorization()`.

---

## CORRECTIVE CYCLE REVISION (P0-B Audit Response)

### OBSERVATION
Independent audit confirmed that authorization issuance existed but was defective:
- Approval provenance was fabricated (`approved_by='human'` hard-coded)
- Digest computation was asymmetric between issuer and validator
- Persistence used ad hoc database instead of canonical repository

### EVIDENCE
Audit report `9975e5bf1` identified causal closure as FALSE:
- E1 Approval → Authorization: CONTRADICTED
- E2 Authorization → Binding: CONTRADICTED
- E3 Binding → Consume: UNKNOWN
- E4 Consume → Adapter: UNKNOWN
- E5 Adapter → Transport: NOT PROVEN

### INTERPRETATION
The previous implementation had the structure but not the causal integrity. Approval decisions did not deterministically lead to valid authorizations because:
1. Digest mismatch made binding impossible
2. Fabricated approval provenance broke trust chain
3. Canonical persistence was bypassed

### POLICY CHANGE
**FIX-1:** Shared canonical digest function `compute_canonical_prompt_digest()` ensures issuer and validator use exact same computation.
**FIX-2:** Authorization issuance requires explicit `ApprovalDecision.APPROVED`. REJECTED and PENDING do not issue authorization.
**FIX-3:** Approval provenance extracted from `task.metadata.get('approved_by')` or `task.requested_by_role` instead of hard-coded 'human'.
**FIX-6:** Authorization persisted via `self.memory.repository.save_external_authorization()` using canonical database.

### REMAINING UNCERTAINTY
Real runtime validation requires actual operation. Tests demonstrate causal path in controlled environment but production behavior depends on actual HumanApprovalBroker integration.
