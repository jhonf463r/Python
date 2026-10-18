# Codex local — R10 v0.7.8 normative lifecycle/correlation reconciliation and documentary candidate

**Destination IA:** Codex local  
**Role:** documentary author + static verifier only  
**Coordinator:** ChatGPT  
**Next independent reviewer:** Claude/Sonnet, only after coordinator recheck  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`

## 0. Canonical continuation and decision already made

Read the reconciled Claude/Sonnet verdict first:

https://github.com/jhonf463r/Python/blob/handoff/r10-v077-review-20261018/relay/R10_V0_7_7_INDEPENDENT_REVIEW_RECONCILIATION_2026-10-18.md

Frozen v0.7.7 relay index and reviewer handoff:
- https://github.com/jhonf463r/Python/blob/handoff/r10-v077-review-20261018/relay/RELAY_INDEX.md
- https://github.com/jhonf463r/Python/blob/handoff/r10-v077-review-20261018/relay/CLAUDE_REVIEW_HANDOFF.md

Coordinator decision:
- R10 v0.7.7 = `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- HI-01, HI-02, HI-03 are verified as delta repairs; v0.7.7 stays frozen and unchanged.
- F1/F2 are material internal lifecycle/correlation contradictions. F3–F5 are smaller traceability/fixture-quality repairs. Also clarify T157’s scenario title because it currently suggests general “durable retraction after crash” but its oracle is specifically replay of an already-committed P2.
- The next work changes normative clauses. Therefore, the next logical contract AND outer package must be v0.7.8, unless the immutable historical artifacts contradict this convention. Historical v0.7.3/v0.7.4 IDs match their contract versions, so use `R10_V0_7_8_CONTRACT`, `R10_V0_7_8_CONTRACT.md`, and `R10_V0_7_8_TEST_MATRIX_T123_T246.csv`. Do not retain logical v0.7.5 identity for a newly changed normative contract.
- Do not ask the owner to repeat decisions already recorded. If the source documents cannot support a deterministic semantic repair, state the precise unresolved rule and stop instead of inventing hidden historical authority.

## 1. Mandatory source identity preflight

Before authoring, download the actual bytes for the five source ZIPs and recompute byte size + SHA-256. A declared hash or GitHub blob SHA-1 does not replace SHA-256 over received bytes.

### v0.7.7 — authoring base; prior delta candidate

URL: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip

Expected: **1,248,405 bytes**  
Expected SHA-256: `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf`

This ZIP was independently binary-verified by Claude/Sonnet according to the supplied review. You must nevertheless verify actual bytes before editing.

### v0.7.5 — prior logical source package

URL: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_5_DOCUMENTARY_CANDIDATE.zip

Expected: **491,529 bytes**  
Expected SHA-256: `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`

### v0.7.4

URL: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip

Expected: **86,703 bytes**  
Expected SHA-256: `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`

### v0.7.3

URL: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_3_DOCUMENTARY_CANDIDATE.zip

Expected: **86,835 bytes**  
Expected SHA-256: `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`

### v0.7.2

URL: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip

Expected: **50,589 bytes**  
Expected SHA-256: `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`

If any required file is unavailable/corrupt or actual size/hash fails, stop with `BLOCKED_SOURCE_IDENTITY_MISMATCH`. Do not reconstruct, substitute arbitrary URLs, or continue using extracted files as a replacement for a failed source ZIP.

Use a fresh isolated workspace outside every IABV checkout.

## 2. Preserve all frozen candidates and source provenance

- Do not alter/delete v0.7.5, v0.7.6 or v0.7.7.
- v0.7.6 remains a frozen failed-preflight artifact. The coordinator’s commit-pinned text check found T222–T233 each had 13 fields despite the 12-column header. Its full ZIP was not independently reverified by the Claude reviewer due API 403; do not misrepresent that limitation or re-open the already-sufficient text finding.
- v0.7.7 is the verified authoring base, and must remain byte-identical as a preserved historical package.
- Preserve v0.7.5, v0.7.4, v0.7.3 and v0.7.2 packages and historical payloads byte-for-byte. Do not normalize historic payloads.
- The full v0.7.8 package must identify all sources, true hashes/sizes, change map, residuals and commit-pinned links.

## 3. Create v0.7.8 as a new logical contract version

The new package filename is:

`R10_V0_7_8_DOCUMENTARY_CANDIDATE.zip`

The logical contract filename/ID:
- `R10_V0_7_8_CONTRACT.md`
- `Artifact ID: R10_V0_7_8_CONTRACT`

The matrix filename:
- `R10_V0_7_8_TEST_MATRIX_T123_T246.csv`

Preserve the 124 existing numeric test IDs T123–T246 exactly; do not renumber or add test IDs without authorization. Retain all test execution statuses `NOT_RUN`.

Update all package version labels, cross references, manifests, README, changelog, traceability/change map, preflight report, and independent-review prompt coherently. Do not rewrite the historical meaning of the v0.7.5 clauses merely by renaming section titles: retain historical section/provenance references as historical references and record the v0.7.8 normative amendments explicitly. Reconcile existing duplicated rules in place so the contract has one consistent operative meaning; an appended “supersedes” paragraph by itself is not a repair.

## 4. Required repair F1 — one execution lifecycle and explicit writers

### Contradictions to resolve

- §3.3 currently says `FAILED`, `ABORTED`, and `TIMED_OUT` are not canonical because no writer/transition exists, and puts `RESULT_ACCEPTED` in the execution-state chain.
- §17.1 proposes a distinct execution lifecycle with `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `ABANDONED`, `SUPERSEDED`, and says `RESULT_ACCEPTED` is not an execution state.
- The §12 authorized-writer matrix is declared closed but does not explicitly define writers/preconditions for `SUCCEEDED`, `FAILED` and `TIMED_OUT`.
- §16.3 explicitly says that a conflict between normative wording and an oracle makes the candidate internally inconsistent; do not rely solely on §17.1’s “supersedes earlier text” sentence to waive the conflict.
- T132 forbids `TIMED_OUT` for an unattributed infrastructure timeout, but the fixture does not explicitly say that no authorized terminal-timeout event/attestation was accepted.
- T231 tests capture/result acceptance separation but currently cites §3.2 (profile semantics) unnecessarily.

### Required repair

1. Define exactly one `ExecutionState` machine, with one set of states and transitions in §3.3, §12 and §17.1. Keep execution terminality separate from result/capture acceptance. `RESULT_ACCEPTED` must not terminalize execution.
2. Define every supported execution terminal’s exact event/state mapping, authorized writer, durable evidence, preconditions, rejection conditions and terminal effects in the closed writer/transition tables. Ensure §12 no longer claims its writer matrix is closed while omitting terminal writers.
3. Specifically adjudicate `SUCCEEDED`, `FAILED`, and `TIMED_OUT`: retain each only if this reconstructed normative contract gives it a deterministic, fail-closed writer and triggering condition. Do not infer a timeout trigger from a generic infrastructure-timeout diagnostic or from missing output alone. An infrastructure timeout remains `INFRASTRUCTURE_TIMEOUT_DIAGNOSED` unless the separately defined terminal-timeout guard is satisfied. If that terminal event cannot be grounded deterministically, remove the unsupported terminal state rather than inventing an unstated timeout deadline/authority.
4. Align §3.3, §12, §17.1, relevant cross references, the state vocabulary and event writer tables. Preserve diagnostic-only treatment of unattributed timeout and do not infer negative strategy learning from infrastructure failure.
5. Repair T132 so its preconditions explicitly state whether an authorized terminal-timeout event has been accepted. It should reject terminalization in the diagnostic-only fixture while remaining consistent with the defined valid terminal-timeout path, if such a path is retained.
6. Repair T231’s `normative_basis` to cite §17.1 only, unless §12 is also specifically needed after its transition table is corrected. Remove §3.2 as unrelated profile scope.
7. Inspect the complete contract and matrix text for every directly dependent reference to `RESULT_ACCEPTED`, `RESULT_RECORDED`, `TIMED_OUT`, `FAILED`, `ABORTED`, and `SUCCEEDED`; document and reconcile the affected references. Do not do an unrelated general audit.

Do not claim implementation verification. This is proposed normative clarification that must be reviewed independently.

## 5. Required repair F2 — ResultState vs. correlation/rejection dispositions

### Contradictions to resolve

- §4.1 and §16.1 state `UNCORRELATED` is a capture-rejection disposition, never a `ResultState`.
- T136 says uncorrelated capture creates no `result_id` and no `ResultState`.
- §17.1 nevertheless includes `UNCORRELATED` in its `ResultState` enumeration.
- §17.2 separately defines `correlation_status` values including `UNCORRELATED` and `LATE_STALE`.
- §12 describes `RESULT_RECORDED` as “captured → correlated/frozen”, while §17.1 says `RESULT_RECORDED` durably creates `CAPTURED` only.

### Required repair

1. Define one normative `ResultState` taxonomy that applies only to an allocated result entity. Preserve the already repeated fail-closed rule: if parent correlation/completeness fails before result allocation, record durable `CAPTURE_REJECTED`, no `result_id`/ResultState/terminal slot/effect, and `correlation_status=UNCORRELATED`.
2. Keep `UNCORRELATED` as a rejection/correlation disposition, not a `ResultState`. Reconcile `LATE_STALE` against the same no-result-ID rule in §3.3/§12; do not put a pre-allocation disposition in ResultState if it has no result ID. Distinguish any accepted stored result subsequently rejected from a capture that never became a result entity.
3. Define `RESULT_RECORDED` as the specific transition to `CAPTURED` only after its named ingress gates pass. Fix §12 to be consistent with §17.1: correlation/rejection occurs through the specified gates; it is not a conflicting second ResultState transition.
4. Align §§4.1, 12, 16.1, 17.1, 17.2, and matrix T136/T231 plus any directly dependent result/correlation-state references. Keep `correlation_status`, rejection code/disposition, `ResultState`, and `ExecutionState` as distinct concepts.
5. T136’s oracle must remain explicit: no `result_id`, no ResultState, no automatic slot/evaluation/effect; durable capture-rejection evidence with `UNCORRELATED` in the correctly typed field. T231 must remain explicit that `RESULT_RECORDED` leaves ResultState at `CAPTURED` and execution at `EXECUTION_STARTED`; later result acceptance changes only the result lifecycle, not the execution state.

## 6. Required smaller repairs F3–F5 and the T157 label

### F3 — T231 basis

Set T231 `normative_basis` to §17.1 only (or §12; §17.1 if the corrected transition table directly governs the oracle). Do not cite §3.2 as a lifecycle basis.

### F4 — explicit per-row L5b metric/sample thresholds

Rows T221, T222, T224 and T225 are paired negative/positive controls. Each row must independently specify:
- fixture metric name: `lift` as the fixture-supplied scalar used for L5b;
- the threshold/comparator: `lift >= 0.10`;
- minimum sample sizes: `n_treatment >= 20` and `n_control >= 20`;
- its actual treatment/control sample counts and lift value;
- the single intended failing or passing predicate.

T221 isolates sample size (treatment n=19, control n=20, lift=0.12); T222 isolates lift (n=20 per arm, lift=0.09); T224 is the positive sample boundary (n=20 per arm, lift=0.12); T225 is the positive lift boundary (n=20 per arm, lift=0.10). Ensure each applicable row repeats the relevant numeric rule so it does not rely on a sibling row for its expected result. Add §17.7 to T221’s `normative_basis` if needed for direct threshold traceability. Do not fabricate a formula for deriving lift from raw data if no normatively supported formula exists; record the boundary as a fixture-supplied scalar and flag the formula gap only if the intended claim depends on it.

### F5 — scenario prose normalization

Normalize exactly these 20 scenario cells by removing their leading embedded `NEW_COVERAGE` / `REFERENCE_LABEL_*` metadata prefixes while retaining each scenario’s meaning: T128, T129, T135, T136, T137, T139, T140, T145, T146, T148, T149, T151, T152, T153, T155, T156, T157, T160, T161, T172. Preserve the separate `category` and `provenance` columns unchanged.

Normalize the “Estado inicial:” prefix in the ordered-oracle cells for T137, T139, T146 and T149 to the consistent oracle framing used by adjacent rows. Do not change the stimuli, disposition, state or effects. The change map must list all touched fields.

### T157 low-severity title clarity

Change only the T157 `scenario` wording to distinguish its post-commit P2 replay from general retract-obligation/cleanup scenarios (T133/T196) and ordinary no-crash idempotent replay (T164). Recommended title: “Reproducción postcommit de P2 conserva el estado comprometido”. Keep HI-02’s repaired `crash_retry_conflict_oracle`, preconditions and 0/0 deltas intact.

## 7. Versioned package, diff, and preservation

- New candidate: `R10_V0_7_8_DOCUMENTARY_CANDIDATE.zip`.
- Contract: `R10_V0_7_8_CONTRACT.md`, Artifact ID `R10_V0_7_8_CONTRACT`.
- Matrix: `R10_V0_7_8_TEST_MATRIX_T123_T246.csv`.
- New `R10_V0_7_8_CHANGELOG.md`, `R10_V0_7_8_CHANGE_MAP.md`, `R10_V0_7_8_CONSISTENCY_AND_TRACEABILITY.md`, `R10_V0_7_8_PREFLIGHT_REPORT.md`, `R10_V0_7_8_SHA256.txt`, README and independent review prompt.
- Include preserved historical v0.7.7 ZIP, v0.7.5 ZIP and v0.7.4/v0.7.3/v0.7.2 ZIPs and historical trees byte-for-byte. Keep v0.7.6 frozen/external as failed preflight; do not mutate it.
- Every normative repair must have exact clause/row cross-references. Separate proposed repairs from reviewed findings and all unproven implementation properties.
- Diff the entire new contract/matrix against v0.7.7. The only allowed logical content changes are F1/F2 lifecycle/correlation reconciliations, T231 basis (F3), T221/T222/T224/T225 threshold fixture explicitness (F4), the 20 scenario prefix removals and four oracle-framing changes (F5), T157 scenario label clarification, and necessary version/name/cross-reference updates resulting from making v0.7.8 the logical contract version. If any other normative/cell change appears, stop and explain it before proceeding.

## 8. Mandatory preflight and relay

Perform archive integrity/CRC, safe and unique path checks, every payload’s real size/SHA-256 against manifest, historical byte-preservation checks, strict CSV parsing of all records, and contract/matrix cross-reference checks.

Matrix requirements:
- exactly 124 records, unique contiguous IDs T123–T246;
- exactly 12 columns in header and **exactly 12 fields on every data row**;
- every status `NOT_RUN`;
- T222–T233 bases remain in field 12 and no row has a surplus field;
- T132/T136/T231 oracles and clause references align with the repaired state machines;
- T221/T222/T224/T225 state the explicit sample/metric threshold;
- no 20 scenario marker prefixes or four “Estado inicial:” prefixes remain in the specified cells;
- T157 scenario clarifies the specific post-commit replay case.
Run parsed field-level diff against the full v0.7.7 source and report every changed cell/line.

Publish only after complete preflight to new isolated relay branch `handoff/r10-v078-review-20261018`; first confirm that branch does not already exist. If it exists, create a fresh unique suffix. Do not create a PR/tag/release or update canonical `main`. Publish the ZIP, extracted tree, manifest, reports and review prompt; then download ZIP and text back from the immutable artifact commit and repeat key identity/matrix-width checks independently from the remote bytes.

Use existing GitHub authentication only; no new authentication, paid plan, installation or spend. If any source identity fails or the binary/relay readback fails, stop with a precise `BLOCKED_*` status. Do not route to Claude automatically; coordinator must independently recheck first.

## 9. Report format and stop rules

Return:
- `SOURCE_PREFLIGHT`
- `NORMATIVE_REPAIR_TRACEABILITY`
- `EXECUTION_STATE_AND_RESULT_STATE_RECONCILIATION`
- `CSV_FULL_ROW_WIDTH_AUDIT`
- `FULL_PARSED_DIFF_V0_7_7_TO_V0_7_8`
- `STATIC_PREFLIGHT`
- `MANIFEST_AND_HISTORICAL_PRESERVATION`
- `GITHUB_RELAY_AND_READBACK`
- `UNRESOLVED_FRONTIER`
- `NEXT_ACTOR`
- `GOVERNANCE`

Expected status only if every documentary check passes:
`DOCUMENTARY_CANDIDATE_CREATED_PREFLIGHT_COMPLETE_PENDING_COORDINATOR_RECHECK`

Otherwise return a precise `BLOCKED_*` result. No test row may be called passed; all 124 are `NOT_RUN`.

Absolute prohibitions: no product code, tests, build, runtime, migration, integration probes, services, dispatcher or bridge. Do not access M0A, Packages B–E, the dirty IABV checkout, `data/`, SQLite, or `relay-staging\\IABV_v1.5\\data`. Do not overwrite/delete v0.7.5, v0.7.6 or v0.7.7. PR #467 remains `OPEN / DRAFT / UNMERGED`.

Retain: v0.7.2 `FAIL`; v0.7.3/v0.7.4/v0.7.5 `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.6 failed-preflight/frozen; v0.7.7 `REQUIRES_REPAIRS / NOT_ACCEPTED`; F-07/F-10 `OPEN`; F-12 `PROPOSED / UNRESOLVED`; SC-10 `PARTIAL`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
