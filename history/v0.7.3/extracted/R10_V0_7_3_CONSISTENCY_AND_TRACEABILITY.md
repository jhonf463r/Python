# R10 v0.7.3 consistency and traceability report

## Provenance and scope

The candidate was authored from the seven-entry source archive whose observed size/hash matched the user-specified identity. The original archive payloads were hashed after full decompression and matched its internal manifest. The originals are preserved byte-for-byte under `historical/v0.7.2/`. The supplied audit report is treated as provenance and issue context, not as independent proof of implementation behavior. Original v0.6 contract/matrix remain `NOT_RECOVERED`.

No IABV checkout was read or modified for this documentary task. No `data/` or SQLite contents were inspected. No product code, test, build, runtime, migration, service, probe, external transport, provider, M0A, dispatcher, or physical bridge was executed/activated.

## Verified source ZIP inventory and payload hashes

Observed archive SHA-256: `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`; observed byte length: `50589`. The seven archive entries were exactly:

1. `R10_V0_7_2_RECONSTRUCTED_CONTRACT.md` — 33,982 bytes; `3be41ffc488e5f9e0577baf523d15ab62a8d1da9293ce1ed2d3ce73a90b1064c`
2. `R10_V0_7_2_TEST_MATRIX_T123_T196.csv` — 47,684 bytes; `48ebec8481d41cb2688dc8ee8945361d670419806aa026f630fe431405f40203`
3. `R10_V0_7_REFERENCE_NAMESPACED_NONNORMATIVE.md` — 60,428 bytes; `107746aeb02cbf52d736f438cb466b013f66696545b9934b111458ce990ede9e`
4. `R10_V0_7_1_AUDIT_REPORT_CLAUDE.md` — 10,816 bytes; `8f7cb6448213507ef33f3dd35e1bf1903dabd96dbcc5a54fd09cfaad155922f6`
5. `R10_V0_7_2_AUDIT_README.md` — 3,480 bytes; `5889bd840bc89b32410bb9867d7634d6452e45c35aedd51cd76be5cd7ee675a7`
6. `R10_V0_7_2_AUDIT_PROMPT_FOR_CLAUDE.md` — 3,084 bytes; `cab7393e70297247a69a1e185fd1509abdb5e8ad371e1386369373cdd558fe51`
7. `R10_V0_7_2_SHA256.txt` — preserved archive manifest; its own hash is not one of the six payload entries it lists.

Each of the six payload entries was fully read/decompressed and compared to the corresponding manifest length and digest; all matched. The historical copies in this candidate were independently re-hashed against those six values; all matched.
## M0–M5 repair record

| Gate | Documentary repair | Evidence in candidate | Remaining limit |
|---|---|---|---|
| M0 precedence | Normative contract precedence over matrix; matrix is sole test ID registry; conflicts require correction; v0.6 stays unrecovered. | Contract §§0,16; matrix IDs T123–T197. | No runtime validator enforces this precedence. |
| M1 conflict/quarantine | Release removes barrier only; no direct activation; restoration requires independent resolution, fresh evaluation/contribution IDs, same result lineage and new guarded plan. | Contract §§6.2,8.3,16.2; T162,T184. | Store atomicity and independent reviewer authorization are not demonstrated. |
| M2 execution state | Removed unsupported FAILED/ABORTED/TIMED_OUT; crash/infra timeout remains diagnostic until canonical abandonment/supersession. | Contract §§3.3,10,16.2; T132,T173. | No implementation/event-writer verification. |
| M3 correlation | Missing authenticated dispatch turn rejects before DISPATCHED; response parent must equal the dispatch turn; nonce/session/time alone insufficient; uncorrelated is not an eligible result. | Contract §§4.1–4.2,16.1; T135–T144,T176,T197. | Platform attestation, bridge wiring and actual producer behavior remain unverified. |
| M4 validation evidence | Evidence references are immutable, digest-bearing and bound to execution/result/check; complete frozen check set and exact digest match required. | Contract §§5,7,16.1; T145–T154,T179. | Validator execution and evidence custody remain `UNPROVEN`. |
| M5 oracle specificity | 75 unique IDs with explicit normative basis; repaired contradictions and added missing-turn case; all statuses NOT_RUN. | Matrix; changelog; this report. | Static documentary oracles are proposals, not test results. |

## Static consistency checks

Document-only checks intended and recorded for this package:

1. Source archive SHA/size and seven-entry inventory match the specified input.
2. Six payload entries match internal-manifest byte lengths and SHA-256 values; all were fully read/decompressed.
3. Historical source files were copied into candidate without editing; candidate manifest hashes will record exact bytes.
4. Matrix registry retains T123–T196, adds T197, has 75 unique IDs, a nonempty normative basis per row, and all statuses `NOT_RUN`.
5. Contract declares canonical execution, plan, contribution, correlation, evidence, authorization and abandonment semantics. Matrix rows that previously contradicted these were rewritten.
6. Package manifest will cover every package file other than itself. ZIP contents will be checked against that manifest after archive creation.

These are documentary integrity and text-structure checks only. They do not prove runtime behavior or conformance.

## Traceability and repaired oracle clusters

- Modes and eligibility: T123–T129, T175, T185–T187 → §§3.1,7,11,12.
- Strategy/result lineage and replacement: T130–T134 → §§1.3,8.
- Dispatch identity, response correlation and terminal slot: T135–T144, T176, T197 → §§2.2,3.3,4.1–4.2,10,11.
- Frozen criteria/evidence/evaluation: T145–T154, T179 → §§5–7.
- Projection, contribution uniqueness, plans and recovery: T155–T160, T164, T177–T178, T192 → §§1.3,6.3,8–9.
- Conflict, quarantine and restoration: T161–T162, T171, T181, T184 → §§6.1–6.3,8.3.
- Authorization, fencing, deadlines and reopen: T163, T165–T170, T173, T182, T190–T193 → §§2.3,9–10.
- Manual lane and legacy writer isolation: T140, T183–T195 → §§3.2,4.2,6.3,11.
- Tombstones, retraction and learning claims: T133,T160,T196 → §§8.3,13.

## Cases not automatically recoverable

1. Crash after an external side effect but before durable receipt/commit evidence: outcome may be unknown; do not automatically repeat ingestion or external operation. Preserve identity and block for explicit reconciliation.
2. Validator digest is present but validator execution evidence is absent/unresolvable: eligibility remains unproven; do not infer validation from named hashes.
3. Conflicting evaluation payloads or partial event identity: barrier/quarantine remains until independent conflict resolution; no sequence-based winner.
4. Dispatch lacks authenticated parent-turn identity or response parent does not match: reject/un-correlate; do not infer from nonce/time/session.
5. Authorization generation changes during partial plan: keep drafts invisible and void unless the exact original plan can be safely resumed under all current guards.
6. Trusted clock/deadline unavailable: do not auto-abandon.
7. Tombstone/retraction physical cleanup incomplete: visibility barrier remains authoritative; recovery obligation must be durable.

There is no cross-store transaction or demonstrated atomicity across effects. No exactly-once, automatic recovery, or replay safety claim is made beyond the normative idempotency rules proposed here.

## Proposed later tests (not run)

Run only after independent review and implementation contract approval: parameterized mode-gate tests; missing/mismatched parent-turn and missing dispatch-turn tests; same event ID/same digest versus same ID/different digest; complete/incomplete evidence-set and digest mismatch; crash injection at every effect-plan persistence boundary; old/new authorization generation race; strict deadline at t−1/t/t+1; conflict resolution without direct activation and fresh-identity restoration; MANUAL/AUTO isolation; tombstone barrier before cleanup; and legacy success-only write rejection. Preserve all cases as `NOT_RUN` until separately authorized and executed.

## Independence and classifications

This report is authored in the same task that created the documentary candidate. It is not an independent audit. Historical review content is not treated as proof. The next reviewer must inspect the entire candidate and source custody independently.

Classifications: `PROVEN_BY_SOURCE` applies only to inspected input archive bytes/inventory and authored package bytes; `CODEX_LOCAL_REPORTED` applies only to custody/procedure claims not independently reproduced in a separate reviewer context; `PROPOSED` applies to contract/matrix rules and later tests; `UNPROVEN` applies to runtime/validator/store behavior; `NOT_RECOVERED` applies to original v0.6 and `NOT_RUN` to every matrix case.
