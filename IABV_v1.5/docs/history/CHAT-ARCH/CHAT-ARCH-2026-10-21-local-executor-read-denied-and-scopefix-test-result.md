# IABV — Local executor read denied; candidate test result reconciled

- **Date:** 2026-10-21 (America/Bogota)
- **Primary objective:** `GOVERNED_IABV_CODEX_BRIDGE`
- **Evidence basis:** owner-supplied Codex result plus independent public-source reads in the coordinating session.
- **Scope:** continuity and routing reconciliation only. No local source/configuration was read or changed.

## Current adjudication

`NO_GO_KEEP_BLOCKED`.

The latest Codex report `IABV_LOCAL_EXECUTOR_RECEIPT_ROUTE_A_RESULT` states that it did not inspect code or configuration. The prior MCP reader denial remains `governance_blocked=true`, `reason=operational_block_active`; the read request produced no source files. This is a governance/access precondition stop, not a source finding and not proof of local source absence.

Local executor identity, registration/call chain, consumer, effective Codex policy and live MCP server root/revision remain `UNRESOLVED`. The eight Route A hard conditions remain `UNRESOLVED`; no Codex CLI/App Server, IABV/MCP launch or real transport was performed.

## Candidate test result (owner-reported)

- Isolated branch: `fix/iabv-operational-block-target-scope-20261021`.
- Base: `6a231f7f8edd80753444b05c06729c4c4b184673`.
- Candidate HEAD: `433d993df71e02c041b562e80110d7b46fb11bb7`.
- Sparse-first checkout: `C:\\_iabv_sf3_20261021`, reported clean before and after the test run; no `data/` materialized; diff limited to `server.py` and `test_mcp_server.py`.
- Correct SDK import: passed using Python 3.14.4 and pytest 9.0.3.
- Collection: 76 tests, including all six new operational-block scope tests.
- Execution: 74 passed, 2 failed, 0 skipped, 0 errors; exit code 1.
- Failures: `test_world_model_snapshot_returns_current_without_refresh` and `test_world_model_snapshot_refresh_triggers_request_refresh`, both reported as `AttributeError` because the test double `_FakeWorldModelService` lacks `scan_stats`.

## Independent source reconciliation

Public-source reads confirmed:

- At base `6a231f7f8edd80753444b05c06729c4c4b184673`, `server.py` accesses `svc.scan_stats` in `world_model_snapshot`, while `_FakeWorldModelService` in the base test file does not define it.
- Candidate `server.py` retains that same `scan_stats` access; the candidate source change is the separate operational-block target-scope correction.
- Public `WorldModelService` defines `scan_stats` as a property.

Therefore the two failures are statically consistent with a pre-existing test-fixture/contract mismatch, not caused by the target-scope diff. The base suite was not run separately, so this remains a source-backed diagnosis rather than a reproduced base-test result. Do not widen or amend the candidate to fix the fixture without separate authorization.

The six target-scope tests were collected and are not among the two reported failures; by the supplied aggregate, they are among the 74 passing tests. This validates the reported focused cases only within that test run, not live runtime behavior.

## Why the bridge is still not ready

The read request did not reach source inspection. A prompt cannot override the runtime governance gate. Do not repeat the denied reader, use an alternate reader to bypass it, clear the live RAM block by hand, merge/adopt the candidate, or launch the bridge.

The next required transition is a **supported governance-owned, scoped read authorization or an already-supported read-only route** that permits the previously authorized static inspection. The exact mechanism is not established in this record. Until it is identified and used through its legitimate control plane, there is no executable Codex source-inspection prompt that can close the local executor/receipt seam.

## Sole next action

`NEXT_STEP = IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.

The permitted request is limited to static inspection of the executor registration/caller/consumer and whitelisted non-secret effective Codex policy fields. If the supported mechanism is unavailable or still denies the operation, stop and retain `UNRESOLVED`; do not loop or bypass the gate. Do not ask again about the second independent human, do not rerun Route A/B analysis, and do not recreate any candidate clone.

## Preserved states

`GOVERNANCE=KEEP_BLOCKED`  
`BRIDGE=BRIDGE_NOT_READY`  
`REAL_TRANSPORT=NOT_RUN`  
`CANDIDATE_MERGED=NO`  
`LOCAL_WORKTREE=UNTOUCHED`  
`LOCAL_EXECUTOR_IDENTITY=UNRESOLVED`  
`LOCAL_EFFECTIVE_CONFIGURATION=UNRESOLVED`  
`RSK01A5_SERVER_REVISION_AND_ROOT=UNRESOLVED`  
`ROUTE_A=NO_GO_KEEP_BLOCKED`

