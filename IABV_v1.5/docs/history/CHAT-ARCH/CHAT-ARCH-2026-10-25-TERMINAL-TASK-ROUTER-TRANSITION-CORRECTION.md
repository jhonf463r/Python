# Protocol correction — consume terminal results into the canonical route

- Date: 2026-10-25 (America/Bogota).
- Task: IABV_PROTOCOL_TERMINAL_COMPLETION_ROUTING_RECONCILIATION.
- Authorization: explicit Owner request to correct the cross-chat protocol defect.
- Base: live main f041e31fa36e293a770e23143d799d8687a039c0.
- Scope: documentation and routing only; no product code or local execution.
- Canonical adoption: merged into live main at `9289d024b1700ea7894c8dcd3223c4d901bc723d`; the route, protocol and receipt were fetched back from main and compared successfully.

## Incident

The Owner supplied the result for M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT, but CURRENT-STATE.md and all four front-door summaries still advertised that same task as active. This could make a new chat repeat a completed task or ask the Owner to reproduce evidence. The coordinator preserved AUTOMATIC_FOLLOW_ON=FALSE but failed to reconcile the completed result into the canonical router.

## Evidence boundary

The reported assessment completed a bounded source search. No concrete local asset locator was found in the inspected files. Windows trust stores, service metadata, access-control metadata and named-pipe metadata were not inspected. Therefore LOCAL_WINDOWS_ASSET_METADATA=NOT_RUN and AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED. The Owner's existing decision says no independent authority is currently known to them; that is not proof of global absence. Entra remains Owner-reported and is not yet trusted by IABV. G1, G2 and G3 remain unestablished.

## Required state transition

When a result is received, the coordinator MUST:
1. Match the exact task ID and result to the current route and acceptance criteria.
2. Classify provenance and preserve NOT_RUN, NOT_INSPECTED and SUPPORTED_ROUTE_NOT_FOUND distinctions.
3. On terminal completion, record LAST_TERMINAL_TASK and LAST_TERMINAL_RESULT and consume the task's authorization.
4. Move CURRENT-STATE.md to the next authorized task or an explicit wait/Owner-decision state; never leave a completed action as NEXT_ACTION.
5. Synchronize AGENTS.md, README.md, CONTEXT-INDEX.md and MEMORY-OPERATING-PROTOCOL.md in the same documentation transition.
6. Interpret AUTOMATIC_FOLLOW_ON=FALSE as “do not start new technical work automatically,” not “do not reconcile completed work.”
7. If writeback is not authorized, report ROUTE_STATE_STALE and request only the narrow documentation authorization. Do not repeat the completed task to work around stale routing.
8. Claim canonical adoption only after merge is permitted and live-main fetch-back verifies the new route and receipt.

## Regression invariants

```text
TASK_ID_MATCHED_TO_RESULT=TRUE
TERMINAL_RESULT_CONSUMED_BY_ROUTER=TRUE
LAST_TERMINAL_TASK_IS_NOT_STILL_PENDING=TRUE
NEXT_ACTION_DOES_NOT_REPEAT_COMPLETED_TASK=TRUE
UNKNOWN_NOT_INSPECTED_NOT_RUN_PRESERVED=TRUE
AUTOMATIC_FOLLOW_ON=FALSE; NO_NEW_TECHNICAL_ACTION_STARTED
FRONT_DOOR_SUMMARIES_MATCH_CURRENT_STATE=TRUE
CANONICAL_CLAIM_REQUIRES_MAIN_FETCH_BACK=TRUE
```

## Post-assessment route

```text
LAST_TERMINAL_TASK=M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT
LAST_TERMINAL_RESULT=EXISTING_TRUST_ASSET_READ_ONLY_ASSESSMENT_ONLY
SOURCE_LOCATOR_ASSESSMENT=COMPLETE_FOR_INSPECTED_FILES
LOCAL_WINDOWS_ASSET_METADATA=NOT_RUN; NO_SOURCE_GROUNDED_LOCATOR_FOUND
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
ENTRA_TRUSTED_BY_IABV=NOT_ESTABLISHED
G1=G2=G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
PROTECTED_READS=FAIL_CLOSED
TESTS=BUILD=RUNTIME=MCP=REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
ACTIVE_TASK=M1A_G1_WAIT_FOR_GENUINELY_NEW_INDEPENDENT_ROOT_AND_MANDATE_EVIDENCE
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_INDEPENDENT_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

This is a coordinator/memory-navigation correction only. It creates no trust authority, changes no code, closes no gate and does not prove autonomous runtime learning.
