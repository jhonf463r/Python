# Handoff — R10 v0.7.3 documentary repair M0–M5

**Status:** prompt prepared; package repair not performed by this continuity update.  
**Destination:** actual R10 package author in the conversation containing the source artifacts.  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`.

The next task is documentary only: create a new v0.7.3 candidate from the actual v0.7.2 artifacts, preserving v0.7.2 immutably. Do not reconstruct missing files from audit prose. If the source package is not available, stop and request it.

Required repairs:
- **M0:** establish clause-over-oracle precedence and require correction/removal of a contradictory matrix row.
- **M1:** correct/remove T162 so conflict/quarantine never permits direct forbidden activation; align with §§6.2, 8.3, 12 and the T184 behavior where applicable.
- **M2:** make T141 require an attested parent relationship; remove or normatively define T138 nonce expiry; add fail-closed AUTO dispatch without `dispatch_turn_id`.
- **M3:** normalize the 14 flagged rows; reconcile T165/T169 error codes; define or remove unsupported FAILED/ABORTED/TIMED_OUT states and their writers.
- **M4:** remove T130/T131's uncontracted `strategy_lineage_id`/CAS behavior or specify it normatively and resolve order-invariance contradiction.
- **M5:** make expected outcomes explicit in T175–T185 and T187–T196 (21 rows), including exact T180 t0+600s behavior and self-contained T124–T126.
- Minor repairs: T159's §10.1 reference; copied headings in T144/T154/T164; valid I4/I10/I12 mappings; define §7(7)'s evidence contract.

Deliver new contract, matrix, README, changelog, self-consistency report, necessary historical artifacts without mutation, and a new SHA-256 manifest covering all included payload artifacts but not itself. Keep every matrix test `NOT_RUN`. Preserve source provenance and unresolved equivalence claims. Produce `DOCUMENTARY_CANDIDATE_CREATED_PENDING_INDEPENDENT_DELTA_REVIEW` only if all required files exist and consistency checks support it; otherwise `BLOCKED`.

Do not edit the IABV local checkout, modify product code, run tests/build/runtime/probes, inspect `data/`/SQLite/M0A, activate a dispatcher, authorize Packages B–E, merge the continuity PR, or claim the candidate is accepted.

The full ready-to-paste authoring prompt was provided in the conversation on 2026-10-17. This record stores the assignment, gates and acceptance criteria, not a claim that the repair has occurred.
