R10 v0.7.2 — Candidate C Documentary Repair Report

Result: PROPOSED_CANDIDATE_C_READY_FOR_INDEPENDENT_REVIEW
Governance: KEEP_BLOCKED

Source: Candidate B commit e2876e8e015078d81dd9e1592d2a98122c430b2c, parent 9e0ce66768aedd7422e0d3551affd398f44a7532. Candidate B and PR #465 remain unchanged. The reconstructed contract is preserved byte for byte.

Repairs: T130/T131 withdraw missing STRATEGY lifecycle/version rules and the unsupported generic crash/replay oracle (D-C1); T138 separates nonce TTL from execution deadline; T142 replaces undefined FREEZE/INVALID_STATE with a platform-attestation negative under §§4.1–4.2/12; T152 removes deterministic-score assertions; T162/T184 distinguish conflict_id and event_id and gate restoration on an owner decision; T193 separates fencing token from authorization_generation; T194 tests MANUAL/AUTO isolation only, not idempotency.

D-C1 sweep: 44 of 74 crash_retry_conflict_oracle cells carried the generic phrase "No injected crash in this test; durable replay is idempotent and does not add effects." before this patch; 42 remain. Patched (authorized): T130, T131. Explicit replay/identity rule in the contract: T143 (§2.2), T164 (§8.2/§9), T167 (§6.1). Rows that already declare a contract gap but still carry the generic replay phrase (flagged, not patched): T138 (nonce TTL undefined), T152 (score function undefined). Replay semantics not defined by the contract for the operation, since §2.2 is scoped to AUTO producer events (flagged, not patched): T132 (FAILED), T133 and T160 (TOMBSTONE_COMMITTED), T140 (MANUAL ATTACHED; T194 already withdraws this), T168 (nonce-expiry operation), T173 (TASK_REOPENED). Remaining 31 rows (T123-T129, T134-T137, T139, T141, T142, T144-T151, T153-T155, T158, T161, T163, T169, T170, T172) are single-shot rejections, derivations, read-only checks or operations with a defined rule; the phrase is not contradicted there and was not changed. Widening the patch requires a new decision.

Handoff/brief correct the claim that T185–T196 were intact: IDs/titles stayed the same, but 10 of 12 rows had cell changes in Candidate B.

Matrix maintains IDs T123–T196, 11 original headers and all NOT_RUN statuses. Delta C compares against the original baseline and enumerates all changed (test_id, field) pairs with parsed old/new values. Manifests exclude themselves. Hashes are SHA-256 over exact UTF-8 bytes; Git blob IDs are separate. No Candidate C ZIP is claimed.

Open limits: STRATEGY lifecycle/versioning, nonce TTL, score/incompatibility predicate, restore reference and evaluation transition, manual ATTACHED replay/conflict, §0 reference mismatch, §14 coverage claims. Platform attestation, validator execution, sequencer/CAS, atomic publication/barriers, fencing, auth-generation propagation and legacy-writer isolation remain UNPROVEN. No product tests/build/runtime or M0A access.

Verdict: documentary candidate for independent review; not contract acceptance or implementation authorization. KEEP_BLOCKED.
