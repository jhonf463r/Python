# R10 v0.7.4 consistency and traceability report

## Scope, provenance, and execution

Authoring workspace is separate from the IABV checkout. v0.7.3/v0.7.2 source ZIP identities were recalculated before work; input archive contents and v0.7.2 historical copies are checked again by the final preflight manifest. v0.7.3 review findings are adopted as review context, not independent proof by Codex. The literal v0.6 contract/matrix and claimed reconstructed-reference file with SHA prefix 5bab are `NOT_RECOVERED`; included namespaced reference SHA `107746aeb02cbf52d736f438cb466b013f66696545b9934b111458ce990ede9e` is non-normative.

No IABV checkout, `data/`, SQLite, M0A, dispatcher, physical bridge, or packages B–E accessed. Product code, tests, builds, runtime, services, migrations and probes were not executed. Matrix status remains `NOT_RUN`.

## F-01–F-14 disposition

| Finding | Candidate location | Repair / status | Limit |
|---|---|---|---|
| F-01 | Contract §§6.1–6.2, 8.3, 12; T162,T184,T211 | `FIXED_DOCUMENTARILY`: release leaves original evaluation quarantined; restoration needs fresh IDs, same lineage, new guarded plan. | Store semantics unverified. |
| F-02 | Contract §14; matrix; README/changelog | `FIXED_DOCUMENTARILY`: one I1–I12 table; I12 maps directly to L0–L5b rows. | No execution. |
| F-03 | Contract §7.2; matrix codes | `FIXED_DOCUMENTARILY`: listed rejection codes defined, legacy dotted labels retired. | Exhaustive consistency is static only. |
| F-04 | Contract §4.1; T136,T140,T208 | `FIXED_DOCUMENTARILY`: uncorrelated is diagnostic disposition, no eligible result; MANUAL requires independent ATTACHED. | Platform authentication implementation `UNPROVEN`. |
| F-05 | T175,T177–T179,T181–T182,T185,T191 | `FIXED_DOCUMENTARILY`: principal/state/effect oracles stated in preconditions/oracle. | Matrix tests not run. |
| F-06 | T130,T134,T161,T184 | `FIXED_DOCUMENTARILY`: explicit initial counts and exact deltas. | See row semantics; independent review required. |
| F-07 | T126,T130,T140,T142,T161,T162,T168,T178,T180,T183; T208–T217 | `FIXED_DOCUMENTARILY`: separated scenarios added sequentially; originals retained. | `T126` and other inherited row expectations need adversarial review. |
| F-08 | Contract §§7.1–7.2; T179,T198,T203 | `FIXED_DOCUMENTARILY`: digest distinguished from authenticated execution receipt; gate fail-closed. | Attestation/key custody/verifier capability `UNPROVEN`. |
| F-09 | Contract §8.3; T133,T196,T205 | `FIXED_DOCUMENTARILY`: two tombstone scopes and exact projection/pointer/count rules specified. | Cross-store reconciliation `UNPROVEN`. |
| F-10 | Contract §§6–7.2; T151–T153,T172 | `FIXED_DOCUMENTARILY`: policy identity, exact profile tuple, no assumed score, history≠authorization. | Actual scoring/policy implementation `UNPROVEN`. |
| F-11 | Contract §9; T174,T193 | `FIXED_DOCUMENTARILY`: auth generation distinct from fencing; task-head CAS and stale code defined. | CAS implementation `UNPROVEN`. |
| F-12 | Contract §§3.3,12; T177–T178,T191 | `FIXED_DOCUMENTARILY`: acceptance freezes evidence, not execution/eligibility; late output diagnostic. | Exact state machine compatibility needs independent review. |
| F-13 | Contract §4.1; T199–T200 | `FIXED_DOCUMENTARILY`: unauthenticated parent claim and session-turn uniqueness covered; nonce expiry removed from new tests. | Platform attestation implementation `UNPROVEN`. |
| F-14 | Contract §0; README/changelog | `FIXED_DOCUMENTARILY`: absent 5bab file declared unrecovered; included source identified; SC-10 policy is not claimed recovered. | Original source and SC-10 authority remain `NOT_RECOVERED`; any dependent normative claim is proposed only. |

## Matrix and L-level coverage

Historical T123–T197 are preserved by ID; added T198–T221, total N=221 and 99 rows, contiguous with no duplicates. Added rows: T198 incomplete validator receipt; T199 unauthenticated captor claim; T200 turn uniqueness; T201–T207 positive L0–L5b; T208 uncorrelated/MANUAL split; T209 no retroactive freeze; T210 unrelated lineage; T211 post-release original evaluation reuse; T212 crash before commit; T213 MANUAL relabel; T214 before deadline; T215 after deadline; T216 unavailable clock; T217 missing observed-mode attestation; T218 negative L0; T219 negative L3; T220 negative L5a; T221 negative L5b. All rows have explicit fixture, oracle, basis, expected state/evidence/discriminant fields; all status values are NOT_RUN.

L0–L5b definitions are in contract §7.1. The positive/negative matrix rows state concrete distinguishing evidence and falsifiers. T206/T207 parameters are PROPOSED fixture values, not historical policy or universal thresholds.

## Static checks and classification

`PROVEN_BY_SOURCE`: only locally inspected archive bytes, entry manifests, and exact candidate file bytes once final preflight output is recorded. `CLAUDE_REPORTED`: prior independent v0.7.3 verdict as supplied in the adopted prompt. `PROPOSED`: all new normative rules, tests, thresholds and recovery semantics. `UNPROVEN`: product implementation, authenticated platform evidence, validator receipt verification, CAS/atomicity, visibility projections, selector influence, learning efficacy. `NOT_RECOVERED`: original v0.6 and the absent 5bab reference file. `NOT_RUN`: every matrix case and all product execution. `GITHUB_API_VERIFIED`: only after live API checks and remote downloads in the relay phase.

## Completed local documentary preflight

Observed source ZIPs: v0.7.3 86,835 bytes / SHA-256 `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`; v0.7.2 50,589 bytes / SHA-256 `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`. v0.7.3 archive inventory had 14 unique entries and each matched its preserved extracted file; its embedded payload manifest was verified. v0.7.2 archive had seven unique entries; six payloads matched the embedded SHA/byte manifest and preserved historical copies.

Candidate matrix structural check: 99 unique contiguous IDs T123–T221, nonempty normative basis, every status `NOT_RUN`. Candidate archive check: unique safe relative paths, payload manifest excludes only itself, all 13 listed payload lengths/digests match archive bytes. Final candidate ZIP size/SHA are reported in the relay index and delivery response after archive freeze. These are static documentary/integrity checks, not tests or product execution. Relay status is not claimed here until remote publication and pinned-download checks complete.
