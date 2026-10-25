# Terminal hand-back — integrated fail-closed authorization-organ candidate

- Date: 2026-10-25, America/Bogota.
- Task: `M1A_G1_INTEGRATED_FAIL_CLOSED_AUTHORIZATION_ORGAN_COMPLETION_20261025`.
- Result: `SOURCE_CANDIDATE_ONLY`.
- Provenance: Owner-supplied Codex report pasted in the current conversation. The candidate diff, local worktree and test process were not directly inspected or executed by this ChatGPT session.
- Canonical main at route reconciliation: `9078bf1f1e9b9d3e4f9e682def78af7bfe19a3fa`.
- Candidate directory reported: `C:\Users\faber\AppData\Local\Temp\iabv-organ-candidate-21b3b76da03342a180fd31d16d363dd0`.
- Original checkout reported unchanged at `C:\Users\faber\AppData\Local\Temp\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`.

## 1. Reported preservation and candidate identity

Codex reports:
- original branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, HEAD `6bc568e1c5a898afd65cc045c779c25a9cdc5489`;
- candidate branch/HEAD equal to the original branch/HEAD;
- local `origin/main` is stale; no refs were updated and no rebase was performed;
- 7 staged, 11 unstaged and 2 untracked entries remained in the original checkout; candidate final status reportedly matched its own initial status and staged entries were identical;
- index SHA-256 reported for both checkouts: `8A32E6F7B2D642EE4A0217F96DF037497CF47ECAC52CECBEA08717D4B8CB301A`;
- source delta against the pre-task working checkout spans 8 routes; the complete diff is reported as 2,411 lines with SHA-256 `6950FB87DCD6F57573F88BBD58B0B880BD0437E69EB5830D9F55A22AD9AA5F93`;
- diff path reported as `C:\Users\faber\AppData\Local\Temp\iabv-organ-source-diff-981d62fd719541e79cdd02652c14c892\candidate-vs-pretask-checkout.diff`.

These facts remain `OWNER_SUPPLIED_CODEX_REPORT` until the exact diff bytes and required review assertions are independently checked. The file-count summary is not reconciled here: the report names an 8-route delta, while a UI fragment in the hand-back says “4 files +33/-12”. Those may refer to different views, but the exact diff must determine the actual scope. The candidate-vs-pre-task diff is against the dirty working checkout, not the Git HEAD; the review must retain that distinction.

## 2. Reported test evidence

The focalized command was reportedly executed twice. The first run yielded 11 failures and 253 passes; after changes to expectations/fixtures, the second yielded 264 passes in 174.92 seconds. The command targeted:
- `test_read_authorization.py`
- `test_windows_handle_reader.py`
- `test_github_owner_merge_bootstrap.py`
- `test_mcp_server.py`
- `test_mcp_bridge_service.py`
- `test_bootstrap_defer_init.py`

Codex reports no new dependencies, no product build or production runtime, no live MCP or real transport, and no protected reads. The test outputs and actual source are not independently available in this receipt. The independent review must inspect whether the 11 initially failing tests were repaired through valid production-contract changes versus weakened assertions or fixtures, and whether all claims are supported by exact test code and captured output.

## 3. Reported implementation disposition

- R-01: `PARTIAL_SOURCE_CANDIDATE`; independent root, mandate and real Owner authority absent/unestablished.
- R-02: `PARTIAL_SOURCE_CANDIDATE`; fail-closed composition reportedly present, productive providers not established.
- R-03: `SOURCE_CORRECTED_AND_TESTED_IN_CANDIDATE` for the source-level/synthetic object contract only; native/operational Windows semantics remain unestablished.
- R-04: `PARTIAL_SOURCE_CANDIDATE`; trusted production registry-identity origin absent.
- R-05: `SOURCE_CORRECTED_AND_TESTED_IN_CANDIDATE` for SQLite consume-once and transactional error cases only; rollback resistance unestablished.
- R-06: `SOURCE_CORRECTED_AND_TESTED_IN_CANDIDATE` for signature mathematics only; key-to-Owner authority binding unestablished.
- R-07: `SOURCE_CORRECTED_AND_TESTED_IN_CANDIDATE` for source/configuration only; no real transport was run.
- R-08: `EXTERNAL_AUTHORITY_OR_PLATFORM_PREREQUISITE`; real authenticated IPC, protected issuer process and verifiable ACL boundary remain unestablished.

## 4. Canonical state after this terminal report

```text
LAST_TERMINAL_TASK=M1A_G1_INTEGRATED_FAIL_CLOSED_AUTHORIZATION_ORGAN_COMPLETION_20261025
LAST_TERMINAL_RESULT=SOURCE_CANDIDATE_ONLY; OWNER_SUPPLIED_CODEX_REPORT
CANDIDATE_DIFF=LOCAL_PATH_REPORTED; HASH_REPORTED_NOT_RECOMPUTED_HERE
INDEPENDENT_STATIC_REVIEW=NOT_COMPLETE
TESTS=OWNER_REPORTED_264_PASSED; NOT_INDEPENDENTLY_VERIFIED_HERE
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0 UNTIL INDEPENDENT ADJUDICATION
GOVERNANCE=KEEP_BLOCKED_FOR_POSITIVE_PROTECTED_READS
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CODE_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=INDEPENDENT_STATIC_REVIEW_OF_EXACT_CANDIDATE_VS_PRETASK_DIFF
STOP_CONDITION=REVIEW_ONLY; NO_SOURCE_EDIT; NO_TRUST_PROVIDER_INVENTION; NO_GATE_RELEASE
```

## 5. Next review scope

A reviewer must inspect the exact diff bytes, not this summary alone. Review the 8 reported routes against the pre-task working checkout and prior R-01–R-08 findings. Verify changed file count, diff completeness and SHA-256; the difference between base HEAD and pre-task working tree; the actual implementation of decision/permit/open-handle binding; replay atomicity; resource lifetime and cleanup; strict G2 policy/revocation; cryptographic trust provenance; and whether the test fixes weakened assertions or merely updated valid expectations.

The review is analysis-only. It may recommend exact source corrections, but it must not edit the candidate, execute source changes, publish diffs, run production code, release protected reads or claim any gate closure. If the exact diff is not available to the reviewer, return `REVIEW_NOT_RUN; REASON=EXACT_DIFF_BYTES_UNAVAILABLE` and request only the one exact diff artifact; do not repeat implementation or inventory work.

This receipt updates the route only. It does not adopt the candidate, validate its tests independently, close any trust gate or authorize a follow-on implementation task.
