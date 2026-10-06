# CHAT-ARCH-2026-10-06-106 — UAAL-RQ13 PRIMARY RESULT CAPTURE CONTRACT GAP

## Episode

Date: 2026-10-06
Harness:
`C:\\temp\\rq13_task_precondition.py`
SHA authorized:
`771FBFDB26765CEB364D5D485D97A63270C018B8713360FB38FF567B6F464FFC`
Baseline:
`e46d8304167708bed0764d3bf2be8fd6643e8944`

## FACT

The authorized run did not start the target runtime.

Pre-execution provenance reportedly passed:
- harness SHA matched;
- HEAD matched baseline;
- four focal blobs matched;
- source-root/import-path preparation was present.

The harness itself reported a contract gap in `emit_returned_package()`: it does not currently serialize all fields required by the authorized evidence contract. It emits only identity/package ID/site/objective fields and omits:
- `created_at_utc`;
- `updated_at_utc`;
- `package_path`;
- `markdown_path`;
- complete relevant metadata.

Codex therefore stopped before importing IABV, as required by the authorization.

No AppBootstrap was constructed.
No `current_package(refresh=True)` or `latest_active()` call occurred.
No production, tests, harness or worktree files were modified.
No runtime evidence was produced.

## CLASSIFICATION

`PRIMARY RETURN CAPTURE CONTRACT GAP / RUNTIME NOT ENTERED`

This is a harness evidence-contract defect, not an IABV semantic defect.

## METHOD DELTA

New invariant:
`harness runtime-ready ≠ evidence-contract-complete`.

A primary target result is not sufficiently captured merely because package ID/site/objective are emitted. The evidence contract must preserve the complete designated return identity/metadata before secondary trace processing.

## CURRENT FIRST OPEN EDGE

`external harness completion of primary-result capture contract → self-test → new harness SHA → fresh human authorization → bounded RQ13 runtime`.

## NEXT ACTOR

CODEX, external harness correction/self-test only.

No target runtime is authorized for SHA `771FBF...` under the current incomplete capture contract.

## REQUIRED CORRECTION

Modify only `emit_returned_package()` and its associated self-tests/reporting contract so that the returned object is captured immediately after the single `current_package(refresh=True)` call, before trace processing, with at least:
- package ID;
- site ID;
- active objective ID;
- created_at_utc;
- updated_at_utc;
- package_path;
- markdown_path;
- complete relevant package metadata required for returned/persisted comparison.

Preserve existing trace-collision correction and all provenance gates.

After modification:
- syntax check;
- contract-self-test;
- primary-result-before-trace self-test;
- no IABV import;
- no AppBootstrap;
- no runtime;
- new SHA.

The previous SHA becomes superseded after modification and requires fresh human authorization.

## LEARNING STATUS

Unchanged:
- lower-layer adaptive learning mechanism: PRESENT/OBSERVED;
- selector-level learned-state influence: EVIDENCED;
- strong causal future-decision learning: NOT PROVEN.
