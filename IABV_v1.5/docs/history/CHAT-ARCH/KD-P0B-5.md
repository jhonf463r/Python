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
