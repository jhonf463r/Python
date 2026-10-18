# R10 v0.7.5 consistency, provenance and traceability report

## Basis, scope and evidence classes

This is a new reconstructed/proposed documentary candidate. Source package identity was checked from actual downloaded bytes before authoring. Repair basis includes the commit-pinned owner decision at `451e78a5418c96abadc6d6f01930b98497a2f801` and regenerated coordinator reconciliation at `6ccf63ad93ef4946c5fcccdc3f42951775f96e6e`. The owner explicitly accepts the regenerated reconciliation as a documentary substitute basis only. It is not the original Claude/Sonnet report and does not accept v0.7.4. The original report remains `NOT_RECOVERED / UNRESOLVED`; its reported size/prefix are `OWNER_REPORTED / HASH_UNVERIFIED`. Literal v0.6, claimed 5bab reference and SC-10 authority remain `NOT_RECOVERED / UNPROVEN` as applicable.

Evidence labels: `PROVEN_BY_SOURCE` means exact bytes/text were inspected; `OWNER_REPORTED` means not independently reproduced; `PROPOSED` means new documentary rule or test; `UNPROVEN` means implementation/authority/runtime not shown; `NOT_RECOVERED` means source absent; `NOT_RUN` means test not executed; `GITHUB_API_VERIFIED` is reserved for actual remote readback. Earlier Codex reports are not treated as independent evidence.

No IABV checkout or dirty worktree was inspected. No `data/`, SQLite, M0A, dispatcher, Packages B–E, product code, migration, test, build, runtime, service, probe or physical bridge was accessed or run.

## F-01–F-14 state

| Finding | v0.7.5 disposition | Evidence and remaining limit |
|---|---|---|
| F-01 | Documentary repair proposed; §17.3, T184 | Fresh IDs/restores_event_id specified; authorization implementation UNPROVEN. |
| F-02 | Carried forward documentary invariant mapping | No runtime proof; prior status is continuity-reported. |
| F-03 | Rejection vocabulary/precedence clarified §§7.2,17.2–17.3; T179,T200,T230,T232 | Product mapping UNPROVEN. |
| F-04 | DOCUMENTARILY_REPAIRED_WITH_NOTES; §§4.1,17.2; T136,T140,T200,T226 | Platform attestation UNPROVEN; not universal guarantee. |
| F-05 | Carried forward; relevant rows sharpened T175,T177–T179,T181–T185,T191,T212 | Every case NOT_RUN. |
| F-06 | Carried forward; exact deltas T130,T134,T161,T184,T210,T223 | Semantics proposed, pending independent review. |
| F-07 | OPEN; targeted compound repairs include T186/T190 splits, but inherited completeness not established | Full-row adversarial acceptance remains outstanding; original review unavailable. |
| F-08 | Validation mismatch clarified §§7.2,17.3; T179,T198,T203,T227,T228 | Attestation, key custody/verifier UNPROVEN. |
| F-09 | Scopes separated §17.4; T205/T233 | Cross-store reconciliation UNPROVEN. |
| F-10 | OPEN; writer, registration, history and no-score semantics proposed §17.6; T151,T153,T238–T240 | Intended product policy/score semantics and writer implementation require independent review. |
| F-11 | DOCUMENTARILY_REPAIRED_WITH_NOTES; §9 and T174,T193 | CAS/fencing implementation UNPROVEN; not universal guarantee. |
| F-12 | Proposed repair §§3.3,12,17.1; T170,T173,T231,T242,T243 | New state separation is normative proposal; ownership/writer compatibility UNPROVEN. |
| F-13 | Correlation rules clarified §§4.1,17.2; T199,T200,T226,T230 | Platform attestation UNPROVEN. |
| F-14 | Provenance clarified §0 and historical tree | v0.6, 5bab ref and original Claude report NOT_RECOVERED; SC-10 UNPROVEN. |

F-04/F-11 are documentary repairs with notes only. F-07/F-10 remain OPEN. F-12 has proposed wording but is not closed. No finding is accepted by authoring or archive integrity.

## Repair-to-clause/row map

| Repair | Contract | Rows | Changelog item |
|---|---|---|---|
| Correct package/version registry identity | §0, §17.1 | registry T123–T246 | 1 |
| Remove three duplicate columns and BOM; define remaining schema | §§14,17.9 | all 124 rows | 5 |
| Recovery applicability and deterministic fault points | §§8.2,17.5 | T156,T157–T159,T177,T178,T192,T212; remaining rows have per-scenario not-applicable rationale | 5 |
| Lineage independence separated from B outcome | §§1.3,17.7 | T134,T223 | 6 |
| Present digest mismatch | §§7.2,17.3 | T179 | 6 |
| Release vs resolution/restoration | §§6.2,17.3 | T184 | 6 |
| Same-turn second execution | §§4.1,17.2 | T200 | 6 |
| Tombstone pointer/counter scopes | §§8.3,17.4 | T205,T233 | 6 |
| Unrelated lineage numeric delta | §17.4 | T210 | 6 |
| Coherent pre-marker crash | §§8.2,17.5 | T212 | 6 |
| Split L5b sample/lift OR with controls | §17.7 | T221,T222,T224,T225 | 6 |
| Split unaccredited route/mode and auth/revocation paths | §§3.1,9,17.2 | T186,T190,T234–T237 | 6 |
| Independent L1/L2/L4 negatives | §17.7 | T226–T229 | 6 |
| Event digest conflict; result lifecycle; multi-guard rejection | §§17.1–17.2 | T230–T232 | 6 |
| Policy registration, digest, history non-authority | §17.6 | T151,T153,T238–T246 | 6 |

## Full matrix review and limitations

The v0.7.4 CSV was parsed in full: 99 source rows, IDs T123–T221. All historical IDs are retained, followed by T222–T246. The resulting registry has 124 rows, unique contiguous IDs T123–T246. All statuses are NOT_RUN. The three repeated columns were removed rather than copied; remaining columns have distinct definitions in §17.9. The CSV is UTF-8 without BOM. Generic “No crash injected” placeholders were removed. Recovery cases specify fault location/durable state/recovery/post-state, or explicitly explain scenario-specific non-applicability.

Adversarial inspection focused on all prompt-listed rows T143,T154,T156,T158,T159,T164,T166,T170,T173,T176–T179,T184,T186,T187,T190,T192,T201–T207,T238–T246 and heuristic hits for OR/subcases/multiple paths. T143/T230, T154/T241, T170/T242/T243, T176/T244 and T187/T245 split distinct causal paths; T186 and T190 are narrowed to one failure each with positive controls. T221's OR is split. Other inherited rows may still contain coupled lifecycle assertions; F-07 remains OPEN and Claude must review every row. This report does not claim a fully accepted semantic oracle or test execution.

I1–I12 predecessor map remains in §14. Added rows map to the relevant predicates under §17.8. L1 negative is T226; L2 unauthorized and incomplete are T227–T228; L4 uncommitted is T229. Thresholds in L5b rows are fixture constants only.

## Source preservation and static checks

Source identities expected and computed: v0.7.4 = 86,703 bytes, SHA-256 `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`; v0.7.3 = 86,835 bytes, SHA-256 `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`; v0.7.2 = 50,589 bytes, SHA-256 `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`. Source commit: `ad5c094fa3e7e4d1989079983f8f6c05f3296551`. These hashes establish byte identity only, not semantic validity. Each ZIP's inventory, CRC integrity, safe paths, embedded manifest, and extracted-file equivalence are checked in the preflight record. Historical trees and source zips are included without edits.

The original Claude report is not present in the source ZIPs and was not reconstructed. The owner-authorized coordinator reconciliation remains a separate source. Candidate archive integrity and remote relay identity will be appended only after their actual checks.


## Documentary preflight results

- `PASS` source archive byte identity: v0.7.4 (86,703 bytes / dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9), v0.7.3 (86,835 bytes / 1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049), v0.7.2 (50,589 bytes / acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14).
- `PASS` ZIP integrity, unique safe entry paths, full inventory and embedded manifests: v0.7.4 14 entries/13 payloads; v0.7.3 14/13; v0.7.2 7/6. Every manifest payload hash/byte count matches and every available extracted source file equals its archive member.
- `PASS` all historical extracted trees in this candidate compare byte-for-byte with verified source extraction trees; historical source ZIP copies match their original SHA-256 values.
- `PASS` candidate CSV parses; 124 unique contiguous IDs T123–T246; historical T123–T221 all present; required fields nonempty; old duplicate columns absent; no UTF-8 BOM; no generic “No crash injected” placeholder; all 124 statuses `NOT_RUN`.
- `PASS` targeted semantic consistency assertions: T179 digest mismatch uses CRITERIA_MISMATCH; T200 duplicate turn claim is UNCORRELATED; T205 and T233 scope/deltas differ as specified; T210 delta is +1; T221/T222 isolate sample vs lift; T226–T229 separate L1/L2/L4 negatives. These are text assertions, not execution.
- `PASS` candidate manifest: 44 payload entries, self-entry omitted; each listed size and SHA-256 matches actual extracted bytes. Candidate ZIP integrity and unique paths checked after freeze.
- `UNPROVEN` normative semantics, writer compatibility, exact intended policy/score authority, platform attestation, cross-store atomicity/recovery, and all runtime behavior. No tests were run.

Candidate ZIP size and outer SHA-256 are reported from the actual archive in the relay index and delivery report because including an archive's own digest inside that archive would be recursive.


Additional split-row review after the first relay artifact commit: T143/T230 isolate replay from digest conflict; T154/T241 isolate absent criteria from missing bundle bytes; T170/T242/T243 isolate missing receipt, invalid validator signature, and misbound dispatch receipt; T176/T244 isolate an old parent offered to a new execution from late output for an abandoned execution; T187/T245 isolate NO_RESULT from sandbox-only output. Positive/negative L-level assertions were separated where paired controls already exist. T240 now fixes both failed guards and applies AUTHORIZATION_REQUIRED by the §17.2 ordering. Added codes and their precedence are explicit in §17.2.
