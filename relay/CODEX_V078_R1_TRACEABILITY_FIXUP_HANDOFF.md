# Codex local — R10 v0.7.8 R1 bounded traceability/package fixup

Destination: Codex local, documentary author and static packager only.
Next reviewer: ChatGPT coordinator. Claude/Sonnet only after ChatGPT clears the exact new revision.
Current status: COORDINATOR_RECHECK_HOLD.
GOVERNANCE = KEEP_BLOCKED.

## Authoritative current state

Read these commit-pinned artifacts first:
- Coordinator recheck findings: https://github.com/jhonf463r/Python/blob/handoff/r10-v078-t137-repair-20261018/relay/R10_V0_7_8_R1_COORDINATOR_RECHECK_2026-10-18.md
- R1 preflight report: https://github.com/jhonf463r/Python/blob/a081b152407a22b61b6fb11d1947d34e9d0d2795/relay/R10_V0_7_8_R1_PREFLIGHT_REPORT_2026-10-18.md
- R1 artifact commit: https://github.com/jhonf463r/Python/tree/541e150b478bcbf24c739860f799f8e5ef227af7
- R1 matrix: https://github.com/jhonf463r/Python/blob/541e150b478bcbf24c739860f799f8e5ef227af7/candidate-r1/R10_V0_7_8_TEST_MATRIX_T123_T246.csv
- R1 contract: https://github.com/jhonf463r/Python/blob/541e150b478bcbf24c739860f799f8e5ef227af7/candidate-r1/R10_V0_7_8_CONTRACT.md
- R1 ZIP: https://raw.githubusercontent.com/jhonf463r/Python/541e150b478bcbf24c739860f799f8e5ef227af7/R10_V0_7_8_DOCUMENTARY_CANDIDATE_R1.zip
- R1 ZIP author-reported size/SHA-256: 5,248,720 bytes / 1b18f128ceaadce4a32abe4ec3deb7c08f330aa051c6239e4146f91af575ef1f
- R1 manifest SHA-256: cc5288f22724ee02ecddf0ec869448c333779e6c43f86ee5258c364fbff910c5
- Original candidate v0.7.8 commit aa8ea71578b024c69dba446d010f0ea7b068bee3 and R1 commit 541e150b478bcbf24c739860f799f8e5ef227af7 must both remain immutable.

## Work: only three bounded fixups

### COORD-02 — T137 normative_basis

R1 now distinguishes a previously authenticated execution completion receipt binding complete output from a separate later truncated result-ingress capture. The oracle says pre-allocation CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE and no result identity/state or downstream effect. Yet T137 normative_basis remains §4.2; §7.

Update T137 normative_basis to cite the direct rejection/allocation rules from §§4.1, 12, 17.1 and 17.2 as well as the current completeness/eligibility basis. Recommended value: §4.1; §4.2; §7; §12; §17.1; §17.2. Do not change the contract or the T137 oracle semantics.

### COORD-03 — T141 normative_basis

T141's oracle now correctly sets correlation_status=MATCHED, pursuant to §17.2, but its normative_basis remains §4.1; §4.2; §2.2.

Append §17.2 (e.g. §2.2; §4.1; §4.2; §17.2). Do not change the contract or any other T141 meaning.

### COORD-04 — stale embedded base preflight

Inside the current R1 package, candidate-r1/R10_V0_7_8_PREFLIGHT_REPORT.md is still the unmodified pre-R1 snapshot and has an ambiguous generic name/title. The current R1-specific report is external at relay/R10_V0_7_8_R1_PREFLIGHT_REPORT_2026-10-18.md.

Resolve this without modifying any previously published immutable commit. Preferred: refresh the embedded report as the internal R1.1 static preflight, accurate for current payload count/hashes/matrix/contract and statuses, and avoid recursively claiming the outer ZIP digest inside the ZIP. Alternatively, preserve the old report under an unmistakable BASE/PRE-R1 filename and update README/changelog/change map/consistency report and links so it cannot be mistaken for current R1.1 verification. Maintain one clearly identified current preflight. Regenerate manifest and outer ZIP after all payload changes.

## Hard invariants

- No changes to logical contract ID/version or any normative contract byte.
- Preserve test IDs T123–T246, exactly 124 rows, 12 fields each, all NOT_RUN.
- Current R1's only three matrix-cell changes are the comparison baseline; resulting revision should add exactly the two specified normative_basis cell changes unless you find another definite directly governed traceability issue. No scope expansion. Report any additional issue instead of guessing.
- Preserve the immutable original v0.7.8 commit, the R1 artifact commit and all historical bytes.
- No product code/tests/build/runtime/migrations/integrations, no IABV checkout/data/SQLite/M0A/Packages B–E/dispatcher/bridge access or modification.
- No PR, tag, release, merge or main-branch update.

## Verification and publication

Use a new isolated workspace outside the IABV checkout. Re-download actual R1 ZIP and recompute size/SHA-256; stop if mismatch. Update only R1.1 dependent files. Recompute manifest from actual payload bytes. Strict-parse CSV, compare against R1 and original v0.7.8, show every changed parsed cell, verify the contract is byte-identical, verify ZIP CRC/safe unique paths and tree equality, and compare preserved historical source ZIPs/trees byte-for-byte.

Publish as a new immutable commit on branch handoff/r10-v078-t137-repair-20261018. Do not replace the current R1 commit 541e150b478bcbf24c739860f799f8e5ef227af7. Refresh the R1 external report and relay index with current R1.1 ZIP size/SHA, manifest/matrix hashes, exact commit-pinned URLs, changed cells, status PENDING_COORDINATOR_RECHECK and next actor.

After publishing, re-download from new commit-pinned URLs and verify the text readback. If supported by the Codex interface, attach the actual R1.1 ZIP artifact in your final response so ChatGPT can independently calculate its outer SHA-256 in this session. If not supported, state that explicitly; do not call the coordinator's outer SHA independent.

## Required final sections

1. SOURCE_IDENTITY
2. COORD-02_T137_NORMATIVE_BASIS
3. COORD-03_T141_NORMATIVE_BASIS
4. COORD-04_PREFLIGHT_SNAPSHOT
5. CSV_FULL_ROW_WIDTH_AUDIT
6. PARSED_DIFF_AND_CONTRACT_GUARD
7. MANIFEST_ZIP_AND_HISTORY
8. GITHUB_PUBLICATION_AND_REMOTE_READBACK
9. UNRESOLVED_FRONTIER
10. NEXT_ACTOR
11. GOVERNANCE

Return DOCUMENTARY_PATCH_CREATED_PREFLIGHT_COMPLETE_PENDING_COORDINATOR_RECHECK only if all claimed checks actually pass. Otherwise use a precise BLOCKED outcome. Do not claim acceptance, tests passed, runtime behavior, exactly-once, cross-store atomicity, operational efficacy or bridge readiness.

All test cases remain NOT_RUN. GOVERNANCE = KEEP_BLOCKED. BRIDGE_NOT_READY.
