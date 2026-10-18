# R10 v0.7.7 independent-review reconciliation — 2026-10-18

**Coordinator disposition: `REQUIRES_REPAIRS`.**  
**Delta findings HI-01 / HI-02 / HI-03: `PASS` with one low-severity fixture-label clarification recommended.**  
**Whole candidate v0.7.7: `REQUIRES_REPAIRS / NOT_ACCEPTED`.**  
**Governance: `GOVERNANCE = KEEP_BLOCKED`.**

## 1. Evidence boundary and candidate identity

- Reviewer-supplied report: Claude/Sonnet independent delta review pasted into the coordination chat; reviewer verdict `REQUIRES_REPAIRS`.
- Candidate immutable commit: `5534761ac877ee2f5b1f56ba354e4b09b760b717`.
- Candidate ZIP reported and independently byte-verified by Claude/Sonnet: 1,248,405 bytes, SHA-256 `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf`; archive Git blob SHA-1 reported/confirmed `f9d20193d2c318fd998a5ffb2660cd5c489d450c`.
- Reviewer reports all five ZIPs (v0.7.7, v0.7.5, v0.7.4, v0.7.3, v0.7.2) were downloaded and SHA-256 verified; candidate CRC/path/inventory, 57-payload manifest, and historical copies also verified. This evidence is attributed to the reviewer, not claimed as coordinator-performed binary hashing.
- The coordinator independently fetched the commit-pinned CSV bytes, recalculated SHA-256 `137d99bfc2154e533bf2ddd87a54629caee52f5b138d03d7f817b7628ffa25d5` (75,080 bytes), and parsed every row: 124 contiguous unique IDs T123–T246, 12 fields on each row, all `NOT_RUN`, exact bases in field 12 for T222–T233.
- Coordinator compared the parsed matrix to frozen v0.7.5: only 13 expected cell differences (T157 `crash_retry_conflict_oracle`, T222–T233 `normative_basis`). Contract diff is only opening `Artifact ID`, corrected to `R10_V0_7_5_CONTRACT`.
- v0.7.6 full binary identity remains unresolved by the Claude review due to its API 403 responses. Its malformed matrix structure was separately confirmed by coordinator text readback at commit `8ab3f72cc69a745e91450b159aa75d3b776fdeab`; preserve it as a failed-preflight frozen artifact. No need to recover its binary before fixing the new version.

Evidence labels: candidate ZIP/hash `BYTE_HASH_VERIFIED_BY_CLAUDE` per the supplied reviewer report; matrix text/hash and row structure `COORDINATOR_GITHUB_TEXT_AND_HASH_VERIFIED`; runtime/implementation efficacy `UNPROVEN`; all test cases `NOT_RUN`.

## 2. Delta adjudication

### HI-01 — PASS

The logical contract ID `R10_V0_7_5_CONTRACT` follows the historical naming convention evidenced by the v0.7.3/v0.7.4 IDs and the v0.7.5 normative section/title. It is a metadata correction only within v0.7.7. No further change to v0.7.7.

### HI-02 — PASS, with minor scenario-title issue

T157's preconditions place P2 after a durable commit. The repaired oracle models a crash strictly after the marker, preserves C1=`RETRACTED`, C2=`ACTIVE`, one visible contribution, prohibits reapplication/resurrection, and lists the required falsifiers. Delta values remain 0/0.

The scenario label “Retractación durable sobrevive a caída” is broader and can be confused with actual durable-retraction obligation/cleanup windows in T133/T196. T157 instead describes post-commit idempotent replay, overlapping with the no-crash replay concept in T164. For the next candidate, clarify the T157 scenario label (not its oracle) to “Reproducción postcommit de P2 conserva el estado comprometido”, while retaining the distinct crash point. Low-severity clarity repair.

### HI-03 — PASS

All T222–T233 bases are present in field 12 and each record has exactly 12 fields. T229 uses §8.2 alone. The independent review notes that §8.2 supports pre-commit invisibility but not the L4 predicate itself; a narrowly improved basis is `§7.1; §8.2; §17.5` (with §17.5 defining the commit-marker recovery boundary). This is a proposed traceability completion for the next candidate, not a failure of CSV serialization.

## 3. Inherited defects requiring a new logical contract revision

Section 16.3 explicitly says the candidate is internally inconsistent if wording conflicts and no appendix precedence rule repairs a conflicting normative clause or test oracle. Therefore, §17.1’s statement that it “supersedes conflicting earlier text” is not sufficient to waive the following contradictions. v0.7.7 remains `REQUIRES_REPAIRS`.

### F1 — Medium-high: execution lifecycle and terminal events conflict

**Locations:** contract §3.3, §12 writer/transition tables, §16.3, §17.1; matrix T132 and T231.

- §3.3 declares `FAILED`, `ABORTED` and `TIMED_OUT` non-canonical due to no writer/transition, and describes `RESULT_ACCEPTED` in the execution-state chain.
- §17.1 declares `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `ABANDONED`, and `SUPERSEDED` execution terminals, explicitly removes `RESULT_ACCEPTED` from the execution lifecycle, but does not define complete individual terminal writer/trigger/precondition semantics.
- The §12 closed writer matrix identifies `ABANDONED` but does not explicitly list writers/transitions for `SUCCEEDED`, `FAILED`, or `TIMED_OUT`.
- T132 forbids `TIMED_OUT` for an unattributed infrastructure timeout, while its fixture does not explicitly state that no authenticated terminal-timeout event has been accepted.
- T231 is based partly on §3.2 (profiles), which is unrelated to the result/execution lifecycle, and needs a direct lifecycle basis.

**Minimum repair:** create one unambiguous canonical ExecutionState machine and a separate ResultState/capture disposition model; align §§3.3, 12 and 17.1 and all directly affected test oracles. Explicitly define the authorized writer, event, durable trigger/preconditions and terminal effect for each supported execution terminal. Distinguish an infrastructure-timeout diagnostic from an accepted, attributable `TIMED_OUT` terminal event. If the contract cannot ground a terminal event deterministically, remove that unsupported terminal state rather than imply a writer/trigger. Correct T132’s fixture to state whether an accepted authoritative timeout event exists, then make its oracle consistent. Keep `RESULT_ACCEPTED` a result-acceptance transition, not execution terminality.

### F2 — Medium: UNCORRELATED is simultaneously forbidden and listed as ResultState

**Locations:** §§4.1, 12, 16.1, 17.1–17.2; matrix T136.

- §4.1 and §16.1 say `UNCORRELATED` is a capture-rejection disposition/correlation status, never a `ResultState`; T136 says no `result_id` or `ResultState` is created.
- §17.1 nevertheless includes `UNCORRELATED` in the `ResultState` enumeration.
- §17.2 separately defines `correlation_status` to include `UNCORRELATED` and `LATE_STALE`.
- §12 says `RESULT_RECORDED` transitions “captured → correlated/frozen”, while §17.1 says `RESULT_RECORDED` durably creates `CAPTURED` only.

**Minimum repair:** keep the fail-closed invariant already repeated in §§4.1/16.1/T136: an uncorrelated capture is recorded as a durable rejection diagnostic, allocates no `result_id` or ResultState, and records `correlation_status=UNCORRELATED`. Define ResultState only for result entities actually allocated after capture ingress; keep pre-allocation rejection dispositions separate. Reconcile `LATE_STALE` with the same no-result-ID rule. Make §12’s `RESULT_RECORDED` transition agree with §17.1’s CAPTURED-only semantics, and cross-reference the exact independent checks before ResultState changes to ACCEPTED/REJECTED. Do not merely rely on §17.1’s precedence sentence.

### F3 — Low: T231 mis-scoped normative basis

T231 cites `§3.2; §17.1`, but §3.2 defines profiles and does not support `RESULT_RECORDED`/execution-state separation. Remove §3.2 and keep the direct lifecycle basis (at minimum §17.1; add §12 only if the repaired transition table materially supports the row).

### F4 — Low-medium: L5b thresholds/sample minimum are not explicit per fixture

**Rows:** T221, T222, T224, T225 (Claude highlighted T222/T224/T225; T221 is their paired sample-size falsifier).

Every applicable row should spell out the same frozen test parameters instead of depending on a sibling:
- metric name: `lift` as the fixture-supplied scalar used by L5b;
- comparator and threshold: `lift >= 0.10`;
- minimum sample: `n_treatment >= 20` and `n_control >= 20`;
- row-specific sample/lift values and the one gate expected to fail/pass.

Do not invent an unstated formula for deriving lift from raw observations. If a formula is required to make the fixture deterministic, make the limitation explicit and do not pretend it was recovered from historical policy. T221 isolates sample size; T222 isolates lift; T224/T225 are corresponding positive controls/boundaries. Ensure each row states its applicable numeric threshold and sample minimum itself.

### F5 — Low: scenario metadata markers and inconsistent oracle prefixes

- Twenty scenario cells contain leading `NEW_COVERAGE` or `REFERENCE_LABEL_*` marker text (IDs T128, T129, T135, T136, T137, T139, T140, T145, T146, T148, T149, T151, T152, T153, T155, T156, T157, T160, T161, T172). Remove only these marker prefixes from the scenario prose; retain the category/provenance field and all scenario meaning.
- Four `ordered_events_and_oracle` cells use the inconsistent prefix “Estado inicial:” (T137, T139, T146, T149). Normalize the cell framing to the existing event/oracle convention; do not change stimuli, expected result or effects.

## 4. Required next version and versioning decision

The next work changes normative semantics, not just outer packaging. Therefore, do **not** keep the logical contract mislabeled v0.7.5. Create a new immutable logical contract and package version **R10 v0.7.8**, with coherent contract Artifact ID `R10_V0_7_8_CONTRACT`, contract filename `R10_V0_7_8_CONTRACT.md`, and matrix filename `R10_V0_7_8_TEST_MATRIX_T123_T246.csv`, unless an immutable historical artifact proves a different version convention. This is aligned with the historic v0.7.3/v0.7.4 contract identity convention. Keep v0.7.7 frozen and unchanged as the last candidate that passed its bounded delta recheck but failed whole-package semantic review.

Base the v0.7.8 candidate on the verified v0.7.7 ZIP, preserve the v0.7.5 and v0.7.4/v0.7.3/v0.7.2 source packages byte-for-byte, and preserve v0.7.6 as the frozen failed-preflight artifact (do not alter/delete it). All 124 test IDs stay T123–T246. Correct only the listed F1–F5 and T157 label clarity, plus dependent identifiers/cross-references and package metadata. No unrelated broad repair or row-by-row re-audit is authorized.

## 5. Next actor and retained boundary

**Next actor: Codex local**, documentary author for v0.7.8. After its preflight and relay publication, ChatGPT independently rechecks the exact candidate bytes/text and row-level structure. Only then route v0.7.8 to Claude/Sonnet for the independent delta review. The author must not self-approve.

States retained:
- v0.7.2 = `FAIL`
- v0.7.3/v0.7.4 = `REQUIRES_REPAIRS / NOT_ACCEPTED`
- v0.7.5 = `REQUIRES_REPAIRS / NOT_ACCEPTED`, frozen
- v0.7.6 = failed coordinator preflight, frozen
- v0.7.7 = `REQUIRES_REPAIRS / NOT_ACCEPTED` (delta HI-01/02/03 verified; whole candidate blocked by inherited F1–F5)
- F-07/F-10 = `OPEN`; F-12 = `PROPOSED / UNRESOLVED`; SC-10 = `PARTIAL`
- T123–T246 = `NOT_RUN`; no implementation/test/build/runtime/probes/dispatcher/bridge
- `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`

PR #467 remains `OPEN / DRAFT / UNMERGED`.
