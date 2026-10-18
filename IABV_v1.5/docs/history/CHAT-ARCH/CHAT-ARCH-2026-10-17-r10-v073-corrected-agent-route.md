# CHAT-ARCH 2026-10-17 — Corrected IA routing for R10 v0.7.3 repair

**Current task destination:** **Codex local**, documentary package author only, with the verified source ZIP attached to its actual conversation.  
**Independent follow-up reviewer:** **Claude/Sonnet**, after the new candidate exists; not the author of its own audited candidate.  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`.

## 1. Why the previous Codex attempt returned BLOCKED

Codex's result was correct for the evidence it received: the instruction file was not the R10 source package, and Codex did not have the original contract/CSV/README/manifest attached in that conversation. It correctly refused to reconstruct the missing artifacts from the audit report. The process error was the handoff: the prompt omitted an explicit destination IA and the source ZIP was not attached.

## 2. Source package recovered and verified in this ChatGPT Library session

The actual package was found in the Library as `R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip` and materialized for read-only verification. Archive SHA-256:

`acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`

Archive bytes: 50,589.

The ZIP contains:
- `R10_V0_7_2_RECONSTRUCTED_CONTRACT.md` — 33,982 bytes
- `R10_V0_7_2_TEST_MATRIX_T123_T196.csv` — 47,684 bytes
- `R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md` — 60,428 bytes
- `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md` — 10,816 bytes
- `R10_V0_7_2_AUDIT_README.md` — 3,480 bytes
- `R10_V0_7_2_AUDIT_PROMPT_FOR_CLAUDE.md` — 3,084 bytes
- `R10_V0_7_2_SHA256.txt` — manifest.

The six listed payload sizes and SHA-256 values were checked against the embedded manifest and matched. The manifest does not hash itself. Three identical Library copies of the ZIP were compared; the archive hash matched across copies. Hash agreement establishes package byte integrity against the manifest, not semantic approval.

Download/attachable copy in the current conversation runtime: `/mnt/data/r10_recovery/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip`. The Codex chat does not automatically inherit ChatGPT Library/session files: attach this exact ZIP to the Codex conversation before sending the authoring prompt. Do not send just the instruction file.

## 3. Correct agent sequence

1. **Codex local — authoring pass:** attach the verified ZIP; create only a new documentary v0.7.3 candidate in a fresh temporary output directory outside `C:/temp/IABV_coordination_20261016`. It may inspect the ZIP and run file/hash/text consistency utilities on copied package contents; it must not execute product code/tests/build/runtime or modify the dirty IABV checkout.
2. **Claude/Sonnet — independent delta reviewer:** after Codex produces the complete v0.7.3 bundle and evidence map, attach that full bundle and request review of M0–M5 plus contract↔matrix consistency. Do not ask Claude to author and independently approve the same candidate in one pass.
3. If Codex cannot read the attached archive or any required file is missing, remain `BLOCKED`; do not reconstruct from report prose or ask for a broad re-audit.

## 4. Source of task and retained blockers

R10 v0.7.2 audit result is `FAIL`. Repairs M0–M5 remain `PROPOSED`. Targeted repair:
- M0: clause-over-oracle precedence.
- M1: T162 quarantine/conflict behavior.
- M2: T141 parent correlation; T138 nonce expiry; missing AUTO dispatch-turn fail-closed case.
- M3: vocabulary, codes, status writers/events.
- M4: T130/T131 strategy lineage and order contradiction.
- M5: explicit outcomes in 21 rows and T180 at exactly t0+600s.
Plus the documented minor traceability/evidence-contract repairs.

Candidate completion state, only if all artifacts exist and internal consistency checks pass:
`DOCUMENTARY_CANDIDATE_CREATED_PENDING_INDEPENDENT_DELTA_REVIEW`.

It is not a PASS, not an accepted normative baseline, not v0.6/v0.7 historical equivalence, and not implementation authorization. All 74 tests remain `NOT_RUN`.

The separate discovery/sync-pulse trace is still `TRACE_ACCEPTED_WITH_LIMITATIONS`; the possible `evidence_refs → ExperimentRun → proposal_id/discovery_signal_id` two-hop remains `UNRESOLVED`. Do not blend these results.

`PRODUCT_CODE_EXECUTION = NOT_RUN`; `TESTS = NOT_RUN`; `BUILD = NOT_RUN`; `RUNTIME = NOT_RUN`; `IMPLEMENTATION_AUTHORIZED = NO`; `GOVERNANCE = KEEP_BLOCKED`.
