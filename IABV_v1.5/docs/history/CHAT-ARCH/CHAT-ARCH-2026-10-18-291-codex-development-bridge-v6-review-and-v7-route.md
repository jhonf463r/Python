# Entry 291 — IABV → Codex development-bridge contract: v6 review and v7 route

**Date:** 2026-10-18.  
**Route:** parallel documentary workstream; does not replace the current M0B/R8 canonical route in Entry 280.  
**Status:** `PASS_WITH_REPAIRS` on v6 document only; v7 pending seventh adversarial documentary review.  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`; `IMPLEMENTATION = NOT_AUTHORIZED`; `BRIDGE_NOT_READY`.

## 1. Current canonical task

Continue only the documentary design of the IABV → Codex development bridge. The next actor is **Claude/Sonnet**, performing the seventh adversarial documentary review of the exact attached file:

- `IABV_CODEX_contract_review_bundle_v7_2026-10-18.md`
- SHA-256: `1672457e391a8882e0b20a855a6d834257cddf3e5f57de198ce6ed85c80db6a4`
- Size: 147,208 bytes.

The v7 candidate is an artifact generated in the preceding ChatGPT work session and was not yet published in this repository when this Entry was drafted. The reviewer must receive the file itself as an attachment, not this Entry in place of the contract. Standalone handoff: `IABV_CODEX_NEW_CHAT_HANDOFF_2026-10-18.md`, SHA-256 `c296f2f8465a9e3623f9bb0ebd618961af98e4bd5c912f6b5c2f2c23071b0563`.

## 2. Sixth adversarial review result (user-supplied)

Claude/Sonnet reviewed v6 §2.1–§2.15 and returned `PASS_WITH_REPAIRS`, strictly on written-design coherence. The report said:

- N-01–N-64: 27 `CLOSED`, 37 `PARTIALLY_CLOSED`, none `OPEN` (under its literal-text method).
- New findings N65–N79: 15 total, six high severity.
- N-09 degraded from `CLOSED` in the v4 report to `PARTIALLY_CLOSED` in v6. N-01 and N-07 remained below the `CLOSED` state reported in v3.
- The satisfiability register recognized only part of the true blockers. It called out per-operation anti-rollback versus offline custody (N65), missing authorized process-tree terminator/revocation actor (N70), OS ACL/handle conflict with the no-ACL-change constraint (N71), and human-quorum constraints with a single owner (N74).

The review did not reopen public sources or inspect the local machine/checkout, credentials, data or configuration; it executed no commands, Codex, tests, builds or runtime. `CLAUDE_REPORTED_PUBLIC_SOURCE` remains unverified by this review.

## 3. N65–N79 blockers v7 must challenge

- **N65 — HIGH:** anti-rollback per operation needs an admissible existing nonrollback log; offline human root custody alone cannot prove zero rollback window for every nonce/lock.
- **N66 — HIGH:** authority to read `CODEX_HOME`/environment is circular/incomplete before content review; requires dedicated authorization and exact handles, with secrets excluded.
- **N67 — HIGH:** a digest verifier cannot prove snapshot completeness by hashing only paths declared by a parser; it must independently enumerate the complete immutable snapshot.
- **N68:** an independent component must recompute the baseline-to-candidate diff; hashing a supplied diff does not prove its completeness.
- **N69 — HIGH:** a missing observer event/heartbeat cannot be treated as proof of no process creation; coverage gaps must yield `UNKNOWN`.
- **N70 — HIGH:** the principal matrix had no authorized process-tree terminator or revocation actor.
- **N71:** OS ACL/handle enforcement conflicts with “do not change source ACLs” unless a compatible pre-existing capability exists.
- **N72:** the owner-signature channel must independently show the exact immutable bytes/view covered by the signature.
- **N73:** state dimensions and cross-state invariants are incomplete.
- **N74:** human separation/quorum can be impossible with one owner or too few humans.
- **N75:** inventory-scope authorization must precede bounded listing, path-manifest approval, copying and content approval.
- **N76:** the satisfiability register must distinguish unknown, incompatible, and blocked-under-current-constraints per requirement.
- **N77:** disclose bounds must define sources, transforms, channels, protocol, endpoint and limits; isolate authentication metadata as a separate class.
- **N78:** final-state summary must list all required components/statuses.
- **N79:** v7 chooses strict policy A: OS enforcement prevents the first instruction beyond a finite authorized deadline; bounded stop after revocation is additional, not a substitute.

## 4. v7's proposed design delta — none proved

v7 proposes `NonRollbackReservationLog`; separate `ClientInputReviewAuthorization`; ordered inventory-scope authorization → bounded metadata enumeration → `path_manifest` approval → authorized copy → content manifests/review; independent `SnapshotInventoryVerifier` and `SnapshotDiffVerifier`; continuous observer-coverage proof for `CLOSED_NO_EFFECT`; explicit `RevocationAuthority` and `ProcessTreeTerminator`; a trusted owner-view/signature path; complete state/satisfiability records; and strict OS enforcement of the first-instruction deadline.

None of these names proves a real existing service, identity, root, key, OS capability, human quorum, or test result. If a prerequisite capability is unavailable or cannot be evidenced without local access, new authentication, installation, spending, or relaxing a constraint, preserve `BLOCKED_UNDER_CURRENT_CONSTRAINTS`.

## 5. Seventh review protocol

Claude/Sonnet must read v7 completely and return `PASS`, `PASS_WITH_REPAIRS`, or `FAIL` on documentary coherence. Re-adjudicate N-01–N-79 against exact v7 text; do not automatically inherit `CLOSED`. Use `NOT_RECOVERED` where the inherited summary cannot reconstruct the original counterexample. Add N80+ with severity, exact location, counterexample, consequence, minimal repair and discriminating criterion.

Priorities: actual atomicity/anti-rollback; authorized source readers and ACL/handles; independent snapshot enumeration/diff; observer coverage; stop/revocation actors; trusted owner view; root-of-roots/rotation; state invariants; human minimums; and satisfiability. Return the six close-out judgments defined by v7 §1. Do not claim local/runtime/source verification.

After the review returns, the coordinator adjudicates against v7. Do not create v8 pre-emptively or record a PASS before the review.

## 6. Six close-out axes

1. One-use authorization and anti-rollback.
2. Enforcement boundary against Codex `Allow`/bypass and client/descendant separation.
3. Independent receipt and trust roots.
4. Quarantine, incidents, interruption, duplicates and overlapping resources.
5. Baseline/candidate identity, materialization, diff and IABV consumer.
6. Compatibility with decision C and current constraints.

## 7. GitHub continuity separation

Read-only fetches from `jhonf463r/Python` returned `IABV_v1.5/AGENTS.md` blob `69028c4677d121fa455399a27b271c1b36c88187`, `IABV_v1.5/docs/history/CHAT-ARCH/README.md` blob `1a1a7c2f6fa82b3171da69c6f54cdb1667babf16`, with the public objects returned at commit `9e0ce66768aedd7422e0d3551affd398f44a7532`.

Those fetched public index files start with Entry 280 for the M0B-R8.1 read-decision track. This development-bridge contract is a separate parallel route; it must not overwrite or confuse Entry 280. PR #467 is a separate R10/space-time continuity branch `docs/iabv-space-time-agent-continuity-2026-10-16`; do not repurpose or merge it. This Entry is being reviewed in separate **draft PR #468** (`https://github.com/jhonf463r/Python/pull/468`), commit `8e0ef246ce39e894b8c34a1ba99e05f517cc6243`; it is open, draft and unmerged. It does not update the main canonical index and does not contain the complete v7 contract artifact.

## 8. Separate pending work

1. **R10 v0.7.4 independent audit:** 99 row-by-row evaluations were reportedly written; final Markdown assembly/delivery pending (`OWNER_REPORTED`).
2. **Candidate C verdict:** access reportedly verified and analysis completed, but the written adjudication was not emitted (`OWNER_REPORTED`).

Do not mix either deliverable into this v7 contract review, and do not infer those outputs exist here or in GitHub. Finish the v7 route first.

## 9. Binding governance

`GOVERNANCE = KEEP_BLOCKED` · `BRIDGE_NOT_READY` · `IMPLEMENTATION = NOT_AUTHORIZED`.

No local preflight, source inventory, client-input review, materialization, Codex/App Server/model turn, canary, tests, build, runtime, install/update, authentication, quota query or extra spend; no M0A access, `data/` or SQLite inspection, or retry/bypass of a `governance_blocked` reader. Public GitHub source is not a substitute for local dirty source. Documentary acceptance cannot release a governance gate.
