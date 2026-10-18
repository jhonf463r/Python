# R10 v0.7.8 R1.1 — independent documentary delta review (Claude)

> **Coordinator persistence/provenance note (2026-10-18):** Before persistence, the coordinator attempted GitHub readback of this filename under `relay/`, repository root, and `candidate-r1.1/` on branch `handoff/r10-v078-t137-repair-20261018`; all three paths returned 404. The report below is therefore recorded from the complete reviewer text supplied inline in the conversation, not claimed as a previously fetched GitHub file. The findings that the reviewer labels `DIRECT_BYTES` remain reviewer-reported evidence; this preamble does not convert them into coordinator-calculated hashes. The preamble is coordinator-added; the report follows.

`GOVERNANCE = KEEP_BLOCKED` · `BRIDGE_NOT_READY` · `T123–T246 = NOT_RUN` · PR #467 observed `open / draft / unmerged` (head `05539f1b…`, GitHub REST, directly queried).

## Overall disposition: `READY_WITH_LIMITATIONS`

All seven requested checks pass on bytes I retrieved and hashed myself. I found no defect in the R1.1 delta. I record three non-blocking traceability notes (N-1..N-3) and the scope limits below. This is not acceptance and authorizes no implementation, test, runtime or bridge activity.

## Evidence I inspected directly (DIRECT_BYTES)

Retrieved from `raw.githubusercontent.com` pinned to commit `23e46401e282acd4f39083fc184fced51770f2fa`:

- `R10_V0_7_8_DOCUMENTARY_CANDIDATE_R1_1.zip`: 5,249,358 bytes; SHA-256 `f4e67a51…0920352`; git blob SHA-1 `7b6d636c…e1e`. All three match the declared values. Computed by me.
- The original ZIP (5,236,484 B; SHA-256 `82d0c634…6f37`; blob `1cc390a6…`) and the R1 ZIP (5,248,720 B; SHA-256 `1b18f128…ef1f`; blob `5f316d94…`). These match the R1 identity quoted in the preflight and the git tree sizes.
- Git tree listing (REST API) for `candidate-r1.1/`: 213 blobs.
- Codex binary report and coordinator readback, read as text.

## Findings per check

**1. Basis changes are exactly T137 and T141 — PASS.** A strict-CSV field-level diff R1→R1.1 yields exactly two cells: T137 `normative_basis` (`§4.2; §7` → `§4.1; §4.2; §7; §12; §17.1; §17.2`) and T141 `normative_basis` (`§4.1; §4.2; §2.2` → `§2.2; §4.1; §4.2; §17.2`). I read the cited clauses:

- T141: §17.2 defines `correlation_status` as MATCHED / UNCORRELATED / LATE_STALE / CONFLICT_DETECTED, so it directly supports the `MATCHED` oracle. §4.1 and §4.2 cover parent-turn equality and the slot. `CORRELATED` no longer appears anywhere in the contract or matrix (the only substring hits are inside `UNCORRELATED`).
- T137: §4.1, §12 (`CAPTURE_RECEIVED` and `RESULT_RECORDED` rows) and §17.2 establish that incomplete capture writes `CAPTURE_REJECTED` before allocation with no `result_id`, `ResultState` or slot. §3.3, §12 (`EXECUTION_SUCCEEDED` rows) and §17.1 define `SUCCEEDED` via an authenticated observer receipt binding the complete-output digest. §7 item 2 (complete terminal result) supports the effects. The citation set supports the oracle; see N-1 and N-2 for the precision limits.

**2. Three R1 changes retained — PASS.** The original→R1.1 diff contains T137 `initial_state_and_preconditions`, T137 `ordered_events_and_oracle` and T141 `ordered_events_and_oracle`, identical in R1 and R1.1 (original→R1 = exactly these 3 cells; R1→R1.1 does not touch them).

**3. Embedded preflight — PASS.** `R10_V0_7_8_PREFLIGHT_REPORT.md` calls itself "the current internal static preflight for this extracted R1.1 package", supersedes the R1 snapshot, and says explicitly that the outer ZIP size and SHA-256 are not recorded inside the payload. Its claims agree with what I recomputed: 124 rows, 12 fields, contract hash `f251ad59…`, 213 files, 212 manifest entries, 201 historical files identical to R1. The outer ZIP hash does not appear in the payload.

**4. Five parsed-cell delta — PASS.** Original→R1.1 has exactly 5 differing cells: T137 `initial_state_and_preconditions`, T137 `ordered_events_and_oracle`, T137 `normative_basis`, T141 `ordered_events_and_oracle`, T141 `normative_basis`. Each is justified: the undefined `EXECUTION.COMPLETED` is replaced by the canonical `ExecutionState=SUCCEEDED` (§3.3/§17.1); `CORRELATED` becomes `MATCHED` (§17.2); the basis cells add the supporting clauses. The `R10_V0_7_8_R1_1_MATRIX_DIFF.md` tables match my diff cell for cell. All other cells are identical, including all deltas and all `execution_status`.

**5. Contract unchanged — PASS.** `R10_V0_7_8_CONTRACT.md` is byte-identical in the original, R1 and R1.1 extractions (60,222 B; SHA-256 `f251ad59dfee6a524538b08b034ca895388c03d0427b16a5178eb441a7261419`, recomputed and also listed in all three manifests).

**6. Matrix structure — PASS.** In the original, R1 and R1.1: 124 data rows; 12 fields in the header and every row; IDs T123–T246 unique and contiguous; every `execution_status = NOT_RUN`; no BOM. R1.1 is 77,009 B and matches the manifest.

**7. Manifest / ZIP / tree / history — PASS within what I can inspect.**

- ZIP: `testzip` clean; 213 members; no duplicate, absolute or `..` paths.
- Every ZIP member's git blob SHA-1 and size equals the `candidate-r1.1/` blob in the Git tree (213/213; no extracted-only or ZIP-only files).
- Manifest: 212 entries, all unique; recomputed SHA-256 and byte length of each = declared (0 mismatches); the only file not listed is the manifest itself (self-entry omitted, as the header states). No manifest path is missing from the package.
- Historical: the 201 files under `historical/` are byte-identical to R1 and to the original package.
- File-set delta: R1.1 adds `R10_V0_7_8_R1_1_MATRIX_DIFF.md` and the R1 prompt relative to the original. R1→R1.1 replaces `R1_MATRIX_DIFF.md` with `R1_1_MATRIX_DIFF.md`.

## Traceability notes (non-blocking)

- **N-1 (T137 code mapping).** `VALIDATION_EVIDENCE_INCOMPLETE` is defined in §7.2 for a validator receipt ("receipt absent/incomplete/untrusted/inconsistent"), and §12 row `CAPTURE_RECEIVED` types the disposition only as `UNCORRELATED` or `LATE_STALE`. T137 uses the code for a truncated capture; the support is §4.1 ("completeness" is an ingress gate) plus §17.2, which lists the code in the `CAPTURE_REJECTED` guard precedence. This is supported by listing, not by an explicit clause. Optional future wording.
- **N-2 (contract text, pre-existing, not an R1.1 change).** §12 row `CAPTURE_RECEIVED` says a failed gate "or terminal execution" writes `CAPTURE_REJECTED`, while `SUCCEEDED` is terminal (§3.3) and T137's precondition is a capture after `SUCCEEDED`. §3.3 and §4.2 limit `LATE_STALE` to `ABANDONED`/`SUPERSEDED` and speak of an "eligible" execution, so the consistent reading is that `SUCCEEDED` does not block capture. T137's control row ("complete output … accepted") relies on that reading. Because the contract is frozen, this is a candidate for a later contract amendment, not an R1.1 defect.
- **N-3 (T141 §2.2).** §2.2 (producer idempotency) is only tangential to the T141 oracle; harmless over-citation.
- Also noted: the R1 prompt remains inside the package alongside the original prompt; neither affects the matrix or contract.

## Evidence separation

- **Directly verified by me:** all hashes, sizes, CSV parsing, diffs, manifest recomputation, ZIP/tree equality, historical equality, contract equality, clause reading, PR #467 state.
- **Reported, not independently reproduced:** Codex's local PowerShell hashes of its own local file (`CODEX_LOCAL_CALCULATED`); the coordinator's statement of its prior text recheck. My retrieval of the pinned bytes matches Codex's figures, which corroborates them without making them mine.
- **Not verifiable by me:** the preflight's statement that the R1 source came from commit `541e150b…` (I verified the R1 ZIP bytes at `23e46401`, not at that commit).

## Limits and proposed repairs

- Documentary/static only. No claims about tests, runtime, implementation, exactly-once, cross-store atomicity, operational efficacy or bridge readiness. Validator and observer authenticity remain `UNPROVEN`.
- Documentary repairs: none required for R1.1. Optional for a later revision: resolve N-2 (§12 "terminal execution" wording) and N-1 (type completeness failures explicitly).
- Next actor: coordinator adjudication. `KEEP_BLOCKED`.
