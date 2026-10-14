
# CHAT-ARCH-2026-10-13-277 — M0B-R8.1-C4 adjudication and proposed amendment 274.3

- Episode: CHAT-ARCH-2026-10-13-277
- Date: 2026-10-13 (America/Bogota)
- Input: Owner-supplied Sonnet/Claude C4 report, verdict `PASS_WITH_REPAIRS`, repairs R1–R9
- Effective design inputs: Entry 274 + clean historical body of Entry 275 + Entry 276 + this proposed amendment
- Status: `M0B_R8_1_AMENDMENT_274_3_PROPOSED_PENDING_DELTA_REVIEW`
- Operational posture: `KEEP_BLOCKED`

## 1. Adjudication and evidence boundary

C4 is accepted as a focused documentary review, not as proof of implementation. Its nine repair requests are narrow and compatible with the fail-closed architecture in the inspected contract texts. This entry proposes one text-only amendment, 274.3; it does not accept the design baseline yet.

**Independently verified by coordinator fetch-back from GitHub:**
- Entry 274 current blob: `5943a87d907436fc7ecac31534cbfcd31fe7de55`.
- Clean historical Entry 275 body at commit `1e644ee663118b6567018cd2211c107e48489d4c`: blob `0945248916fa4f83cc0e7d9d354e39fe3720bb5a`, 35,546 characters, one top-level heading.
- Entry 275's current path is a supersession/provenance notice, blob `71b051f3e6c210db0c94d46b60536c86bc11a889`; it is not the contract body.
- Entry 276 current blob: `023272e14ec5c6ef26b904c47c3fed66eb93c532`.
- The CHAT-ARCH README contains the marker “ENTRY 274 … SECOND CHALLENGE PENDING” twice. C4 says the blocks are identical; the coordinator independently confirms the duplicate marker, not a byte-for-byte comparison of both complete blocks. Deduplication remains a separate, non-blocking cleanup.

The exact corrupt-blob metrics, Git ancestry and standalone regex experiment described by C4 remain `OWNER_REPORTED` here unless separately re-fetched/recomputed. Inspected contract clauses are `PROVEN_BY_SOURCE` as document text only. R1–R9 and tests below are `PROPOSED`. Every OS, clock, credential-isolation, revocation, transport and runtime property remains `UNPROVEN`.

Do not use the current Entry 275 notice as normative content. This amendment takes precedence over conflicting clauses in Entry 274, the clean historical Entry 275 body and Entry 276; unmodified clauses remain in force. No implementation, local M0A access, blocked-reader retry/bypass, tests/builds/runtime, source/config edits, credential inspection, authentication, installation/update or launch is authorized.

## 2. R1 — broaden anti-rollback and re-check at final release (high)

The independently protected monotonic epoch/anchor MUST cover, as one coherent authority state:
1. workspace/checkout registration, lifecycle lineage and deletion tombstones;
2. active governance-block set, block revisions and authoritative scope-model version;
3. Owner trust roots, enrolled credentials, rotation/revocation state and authoritative revocation-source state/version;
4. protected destination/provider configuration and binding between destination, authenticated agent and session;
5. every policy/configuration value whose rollback could widen an approval.

Owner credential enrollment, rotation and revocation are authenticated, Owner-verified, durably ledgered events. Each increments the protected epoch and expires all active decisions and pending challenges/nonces. Destination, block-set, scope-model and registration changes that increment the same epoch also invalidate those decisions/nonces. Restoring a data snapshot must not restore the independent anchor.

The issuer and reader MUST compare the epoch in the approval/intent with the current protected epoch at issuance, before every reserved operation, and immediately before the `RELEASE_AUTHORIZED` gate and handoff. Any change means discard staged content, emit no bytes/names, record the stale epoch and safely detected causes, and select the primary denial under R2. If the epoch or its protection cannot be checked, fail closed.

**Tests:** (a) restore a trust-store snapshot containing a credential revoked after that snapshot while the protected anchor remains newer — `REGISTRY_ROLLBACK`; (b) change credential, block or destination epoch after intent commit but before `RELEASE_AUTHORIZED` — `DISCARDED`, no content, no active decision or nonce preserved.

## 3. R2 — deterministic denial precedence (medium)

Every fixed fixture MUST select exactly one primary result/status. The protected audit may record all conditions in a deterministic order, but requester-visible results must not create an object-existence oracle. An unqualified “X or Y”, duplicate ID or unassigned denial result invalidates the conformance artifact.

For simultaneous conditions, apply this ordered gate precedence and stop at the first failing gate for primary-result selection. Do not perform a lookup prohibited by an earlier gate.

1. Ledger integrity/recovery and unresolved-intent halt.
2. Protected anchor or registry/trust/destination epoch/lineage rollback — `REGISTRY_ROLLBACK`.
3. Owner credential, requester/session or trusted approval-channel failure — `APPROVAL_CHANNEL_UNTRUSTED`.
4. Lexical path grammar before lookup — `PATH_FORM_UNSUPPORTED`.
5. Uniform path/scope resolution denial at the permitted resolution stage — `PATH_SCOPE_UNAVAILABLE`.
6. Inability to prove actual-object containment — `CONTAINMENT_UNPROVEN`.
7. Incomplete/contradictory block scope or identity evidence — `BLOCK_SCOPE_UNEVALUABLE`.
8. Applicable block without independent governance-owned release — `BLOCK_RELEASE_UNSUPPORTED`.
9. Clock, expiry or revocation failure at its authorization gate — discard and deny.
10. Byte, entry or operation-budget violation — use its specific stable code, such as `FILE_LIMIT_EXCEEDED` or `LIST_LIMIT_EXCEEDED`.

After earlier integrity gates pass, `BLOCK_SCOPE_UNEVALUABLE` still dominates a simultaneously applicable-but-unreleased block; otherwise the result is `BLOCK_RELEASE_UNSUPPORTED`. A stale registry/trust/destination epoch is caught before block combination and yields `REGISTRY_ROLLBACK`. `APPROVAL_PENDING` is a public pre-approval state, not a denial code; R3 governs it. Any other named denial code must be assigned to exactly one gate before adoption; an unknown/unassigned code invalidates the artifact.

Retire the ambiguous active alias `A29` and replace it with `277-A29a` and `277-A29b`. Retire `276-A47` as an ambiguous “X or Y” fixture and replace it with `277-A47a` and `277-A47b`. Each replacement has one fixed setup and one expected result.

## 4. R3 — close pre-approval existence and block oracles (medium)

Before Owner confirmation, requester-visible state, response shape and timing envelope for a syntactically valid, non-sensitive-by-name request MUST be indistinguishable across existing, missing and differently sized targets. Keep the state `APPROVAL_PENDING` for the same approval window; do not return a requester-visible path result early. Detailed information may be available in the protected Owner UI/audit. The Owner's decision remains a possible side channel; timing equivalence and the information inferred from Owner choices remain `UNPROVEN` until tested.

Names denied as sensitive MUST be rejected before target lookup. Existing and nonexistent sensitive-name cases must have the same requester-visible status/shape and perform no lookup. Object-dependent `BLOCK_*` codes and detailed path/scope errors MUST NOT be exposed to the requester before the approval window closes. `PATH_SCOPE_UNAVAILABLE` may be returned in the post-approval decision/result channel only; Owner/audit detail is separate.

**Test:** expand Entry 276 `A37` to compare full externally observable state sequences, response shape and timing envelope for (1) normal existing, (2) normal missing, (3) sensitive existing and (4) sensitive missing targets. Require equivalence within each pair, prove sensitive-name denial precedes lookup, and prohibit object-dependent `BLOCK_*` results before approval. Owner-choice leakage remains `UNPROVEN`.

## 5. R4 — idempotency key excludes the scope digest (medium)

The uniqueness key is exactly `(authenticated principal, session, client_request_token)`. The canonical scope digest is an immutable attribute of that key, not part of the key itself. Reuse with a different digest is denied and audited; it cannot create a parallel decision, fresh nonce or new budget. The caller token is only an idempotency hint and never authority.

A retry returns the current persisted status, not the original issuance-time response. After process/host restart, a formerly active decision is `EXPIRED` under clean Entry 275 `3.2`. Retrying the original key returns `EXPIRED` and cannot reactivate the decision, create a nonce, restore/reset budget or issue a new decision.

**Tests:** extend `A42` through restart: same principal/session/token/digest returns `EXPIRED` with no new nonce, decision or budget. Extend `A43`: same key with a different digest denies, audits the mismatch and cannot create a second ledger key.

## 6. R5 — consistent definition of actual directory entries (medium)

Across Entries 274, clean 275, 276 and the final consolidation, “raw entry”, “enumerated entry” and “entry consumed” mean an actual directory entry. Exact structural pseudo-names `.` and `..`, if emitted by the platform, are excluded from the listing ceiling, enumeration-count limit and entry budget.

Enumerate actual entries until the 201st actual entry is observed, then deny the entire listing with `LIST_LIMIT_EXCEEDED` and disclose no names. Exactly 200 valid actual entries may pass if every other gate passes. Any invalid, sensitive, link/reparse or unsupported actual entry in an in-limit listing denies the whole list; never filter an unsafe actual entry and return a partial list. Unsupported counting or unstable enumeration fails closed.

**Tests:** (a) `.`, `..` plus 199 valid actual entries: permit if all gates pass, charge 199; (b) 200 actual entries plus pseudo-names: the boundary may pass; (c) 201 actual entries plus pseudo-names: deny whole list and disclose no names. Reconcile 274 `8`, clean 275 `6`/`7.1` and 276 `C3-09`/`A40` to this definition.

## 7. R6 — path grammar, reserved basenames and positive boundaries (medium)

### 7.1 Full-component match

Do not use a dollar end-of-line anchor to simulate full-string validation. Validate each component with a genuine full-match operation (for example, the engine's fullmatch API) on ASCII input, then apply length, depth, reserved-name, sensitivity, allowlist, pinned-root containment and object-identity checks. The component language is either one ASCII alphanumeric character, or an ASCII alphanumeric first character, zero to 126 interior characters from letters/digits/dot/underscore/hyphen/ordinary space, and a final character from letters/digits/underscore/hyphen. Maximum component length is 128. A newline or other unconsumed suffix must not pass.

Caller input is slash-separated relative components only: no leading slash, backslash or empty component. Total path length is at most 240 ASCII characters including separators; depth is at most 16 components. Reject colon/ADS, wildcards, traversal, trailing dot/space, tilde short-name patterns, controls, non-ASCII/Unicode (including bidi/confusables), absolute/UNC/device forms and any unsupported syntax with `PATH_FORM_UNSUPPORTED` before lookup. Expansion requires a separately reviewed contract change.

### 7.2 Reserved names

For the reserved-name check only, compare case-insensitively the component text before its first period after stripping trailing ASCII spaces from that comparison substring. Do not rewrite/normalize the path before actual filesystem lookup. Conservatively reject `CON`, `PRN`, `AUX`, `NUL`, `COM0`–`COM9` and `LPT0`–`LPT9`, along with the special names CONIN$, CONOUT$ and CLOCK$. Dollar-sign forms are already rejected by the grammar; mentioning them is defense-in-depth, not accepted syntax. Thus `con.txt`, `CON .txt` and `NUL  .x` are rejected. Do not over-reject `CONSOLE`, `COM10`, `LPT10` or `NULL` under the reserved-name rule alone; other controls still apply.

### 7.3 Platform path ceiling and v1 utility limitation

A relative path within 240 characters does not prove that root-plus-relative path semantics are supported by the target OS/filesystem primitives. If the full target exceeds the platform's proven support, deny with uniform `PATH_SCOPE_UNAVAILABLE`. Do not assume a long-path prefix or change OS configuration. Such a mode requires separate contract review and platform evidence.

Dot-prefixed components such as `.git` and `.env` are outside this deliberately restrictive v1 grammar. Under whole-listing rules, any such actual invalid entry causes the directory listing to fail closed rather than be omitted. This reduces utility but does not permit silent filtering; positive listing fixtures must not assume a repository root containing these entries can be listed.

### 7.4 Required discriminating tests

The final suite MUST include both positive and negative cases; deny-all fails. Test: one-character alphanumeric (allow); valid 128-character component (allow); 129-character component (reject); path exactly 240 ASCII characters (allow if otherwise valid); 241 characters (reject); 16 components (allow if total length is valid); 17 (reject); interior space (allow); final hyphen and underscore (allow); trailing dot/space (reject); reserved examples and near-misses above; newline-suffix rejection by fullmatch. Every fixture needs one expected result.

## 8. R7 — process/session binding, crash recovery and clock regressions (medium)

If the platform cannot bind an approval/session to a unique authenticated agent/process strongly enough to prevent a different local process/agent from redeeming a copied token, v1 issues no decision. A copied bearer-like value never proves identity.

`DELIVERY_ACKNOWLEDGED` in clean Entry 275 and `DELIVERED` in Entry 276 are not synonyms. Use `DELIVERED` only when the contract-defined trusted transport acknowledgement proves delivery; use `HANDOFF_RETURNED` when the local handoff API returns without trusted acknowledgement. A crash or missing durable terminal record is `UNRESOLVED`, blocks new reads and requires durable Owner/governance reconciliation. Never automatically replay a possibly delivered response or claim exactly-once without transport proof.

- `277-A48` — Copy a valid session/token value to a different local process or agent principal. Expected: reject before content access; if process/agent distinction cannot be proven, issue no decision.
- `277-A49` — Two crash fixtures: (a) after `RELEASE_AUTHORIZED` and before `HANDOFF_RETURNED`; (b) after `HANDOFF_RETURNED` and before durable final state/ack. Expected: `UNRESOLVED`, reads halted pending reconciliation, reservation retained, no automatic replay and no `DELIVERED` without trusted acknowledgement.
- `277-A50` — Move wall clock backwards after issuance. Expected: all active decisions and pending nonces expire, fail closed and never revive. A tolerance does not forgive a detected backward step.

## 9. R8 — unique test IDs and matrix ownership (low)

The clean historical Entry 275 matrix A1–A35 is the sole active base and wholly replaces Entry 274's historical A1–A22. Do not merge them by bare number. Qualify retired cases as `274-A1` through `274-A22`, the active base as `275-A1` through `275-A35`, and Entry 276 supplements as `276-A36` through `276-A46`. Retire active alias `275-A29` and `276-A47`; replace them with `277-A29a`, `277-A29b`, `277-A47a` and `277-A47b`. New test cases introduced here use `277-A48` onward.

The final manifest MUST use qualified globally unique IDs, with one setup, one expected result, traceability and positive/negative/boundary classification. Duplicate IDs, bare ambiguous references, “X or Y”, unassigned codes, or no positive/exact-boundary tests invalidate the artifact.

Replacement fixtures:
- `277-A29a` — Submit forbidden lexical syntax/alias (ADS, UNC/device, traversal, tilde alias, trailing dot/space, reserved device basename, control/bidi/Unicode). Expected: `PATH_FORM_UNSUPPORTED` before lookup; no filesystem existence disclosure.
- `277-A29b` — Submit syntactically valid path whose scope cannot safely be established at the permitted stage. Expected: uniform `PATH_SCOPE_UNAVAILABLE`; no existence/type/size disclosure.
- `277-A47a` — Roll back/miss workspace registration or checkout-lineage/tombstone epoch against independent anchor. Expected: `REGISTRY_ROLLBACK`.
- `277-A47b` — Registry/trust/destination epoch is current, but only active-block-set or scope-model epoch is stale/missing. Expected: `BLOCK_SCOPE_UNEVALUABLE`.

## 10. R9 — clock tolerance and revocation freshness (low)

Set the proposed `CLOCK_DISAGREEMENT_TOLERANCE` to 2 seconds for disagreement between elapsed-time and wall-clock observations, but only on a platform whose monotonic source's suspend semantics have been established. A disagreement greater than two seconds expires every active decision and pending nonce. Independently, any detected backward wall-clock step expires every active decision and pending nonce regardless of magnitude; the tolerance never revives a grant. If clock comparison or suspend semantics cannot be established, fail closed.

At `RELEASE_AUTHORIZED`, cached revocation data is not acceptable. The verifier must query the authoritative revocation source at the gate with proposed `REVOCATION_MAX_STALENESS = 0 seconds`. The response must include an authenticated current version/time marker with independently established semantics. Missing/stale marker, unavailable/inconsistent source or inability to establish freshness means deny and discard staged content. Zero cache age does not prove linearizability or eliminate every race after the query; those properties remain `UNPROVEN` until established.

**Test:** extend `A39` with exact two-second boundary, greater-than-two-second discrepancy, unknown suspend semantics, missing/stale revocation version and stale trust/revocation epoch. Extend `277-A50` with backward wall-clock movement smaller than two seconds. Each setup has one expected result.

## 11. Supplemental required tests

- `277-A51` — Restore a trust-store snapshot older than the independent protected epoch, predating credential revocation. Expected: `REGISTRY_ROLLBACK` before approval/content access.
- `277-A52` — Change any covered authority epoch after intent commit but before the final release gate. Expected: staged output `DISCARDED`, no content, no new decision/nonce/budget.
- `277-A53` — Retry committed issuance after restart with same principal/session/token/digest. Expected: current state `EXPIRED`; no reactivation, nonce creation or budget reset.
- `277-A54` — Enumerate 199 valid actual entries plus `.` and `..`. Expected: count/charge 199 actual entries only and permit if every other gate passes.
- `277-A55` — Run every positive/negative/boundary case in `7.4` with one expected result; deny-all fails.
- `277-A56` — Verify clock tolerance and release-gate freshness. A cached revocation response at release fails even if it reports no revocation.
- `277-A57` — A valid relative path of at most 240 characters whose root-plus-relative target exceeds proven platform support. Expected: `PATH_SCOPE_UNAVAILABLE`; no unsupported lookup/assumed long-path mode.
- `277-A58` — Expand `A37` to assert complete requester-visible state sequence and timing envelope for all four target/sensitivity cases. No object-dependent `BLOCK_*` code before Owner confirmation.

## 12. Consolidation and adoption gate

The consolidated manifest uses qualified active cases only: Entry 275 A1–A35 except retired A29, Entry 276 A36–A46 except retired A47, and this entry's `277-A29a/b`, `277-A47a/b` and `277-A48`–`277-A58`. Entry 274 A1–A22 remains historical under `274-A#` IDs and is not merged with Entry 275. Replace Entry 276 `A44` validation with a validator requiring full-component match semantics, reserved-name checks, global test-ID uniqueness, assigned result codes and positive/boundary cases.

No cases are claimed executed by this amendment. The textual requirements/tests are `PROPOSED`. A future adoption requires one fully consolidated contract and one conformance manifest, followed by one targeted delta review. Even a later accepted design baseline does not authorize implementation or release a block.

## 13. Current posture and next actor

- Result: `M0B_R8_1_AMENDMENT_274_3_PROPOSED_PENDING_DELTA_REVIEW`.
- Operational posture: `KEEP_BLOCKED`.
- Next actor: Sonnet/Claude, one delta review of Entry 277 only against Entry 274, the clean historical Entry 275 body and Entry 276. Challenge R1–R9 and tests `277-A29a/b`, `277-A47a/b` and `277-A48`–`277-A58`. Return `PASS`, `PASS_WITH_REPAIRS` or `FAIL` with each surviving counterexample, minimal text repair and one discriminating test. No broad archaeology/source audit.
- No code, tests/build/runtime, local M0A, blocked-reader access/retry/bypass, source edits, credentials, authentication, software install/update or launch. Implementation and OS claims remain `UNPROVEN`; this report grants no access to or release of M0A.
