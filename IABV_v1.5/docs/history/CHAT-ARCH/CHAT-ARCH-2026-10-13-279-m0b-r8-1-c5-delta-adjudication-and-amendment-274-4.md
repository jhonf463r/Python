# CHAT-ARCH-2026-10-13-279 — M0B-R8.1 C5 delta adjudication and amendment 274.4

- Episode: CHAT-ARCH-2026-10-13-279
- Date: 2026-10-13 (America/Bogota)
- Input: targeted delta review of Entry 278, supplied by Sonnet/Claude.
- Status: `M0B_R8_1_AMENDMENT_274_4_PROPOSED_PENDING_TARGETED_DELTA_REVIEW`
- Operational posture: `KEEP_BLOCKED`
- Normative standing: proposed textual amendment only. It does not replace Entry 278 until the next consolidation is fetched back and reviewed.

## 0. Scope, provenance and decision

The review is limited to the document in the public repository:

- Entry 278 path: `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-278-m0b-r8-1-consolidated-contract-candidate-274-3.md`
- Entry 278 blob SHA: `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`
- Entry 278 status before this adjudication: `M0B_R8_1_CONSOLIDATED_CANDIDATE_274_3_PENDING_TARGETED_DELTA_REVIEW`

The supplied reviewer reports `PASS_WITH_REPAIRS`. That verdict is accepted as a **documentary delta finding**, not as source-code or runtime evidence. The review did not compare every embedded clause with the historical source blobs and did not inspect the local M0A checkout. This amendment therefore does not elevate the candidate's internal provenance assertions into independent source verification.

The review found that structural uniqueness is not enough: 106 distinct identifiers do not guarantee one unambiguous setup, one expected result, or complete coverage of the stated denial-code precedence. Repairs P1–P10 below are required before the contract can be accepted as a single normative design artifact.

## 1. P1 — Required result fields and deterministic manifest

### 1.1 Required manifest schema

The next consolidated manifest MUST contain, for every active fixture:

- `qualified_id`
- `setup` — one fixed, reproducible condition; no compound alternatives
- `evaluation_stage` — one declared stage/gate or an explicit end-to-end operation
- `expected_primary_result` — exactly one value
- `expected_lifecycle_state` — exactly one value when lifecycle state is relevant; otherwise `NOT_APPLICABLE`
- `classification` — positive, negative, boundary, recovery, or artifact-validation
- `traceability` — the clause/gate being discriminated

The primary result is one of the 16 stable denial codes in Entry 278 §5 R2, or one explicitly enumerated non-denial result applicable to the declared stage. At minimum the non-denial vocabulary is: `APPROVAL_PENDING`, `PATH_FORM_ACCEPTED`, `MANIFEST_INVALID`, `ALLOW`, and `HANDOFF_RETURNED`. `DELIVERED` is permitted only when a trusted delivery acknowledgement has been durably recorded. Do not use a terminal transport result as the expected result for a grammar-only or manifest-lint fixture.

The lifecycle field is separate from the primary result. For example, a final-gate denial after bytes were staged may have `expected_primary_result=DECISION_EXPIRED` and `expected_lifecycle_state=DISCARDED`. This is not an ambiguous “X or Y”: one field selects the primary verdict and the other records the required operation state. The linter MUST reject missing values, unknown values, duplicate IDs, compound setups, or a result containing alternatives such as “X or Y”, a slash-delimited result, or an unspecified “deny/discard”.

### 1.2 Required mapping for formerly unmapped rows

During the next consolidation, assign the explicit result fields to every active row, not only to new tests. At a minimum resolve the following cases as specified here:

| Existing row / delta | Required primary result | Required lifecycle or handling |
|---|---|---|
| `275-A2`, `275-A3`, `275-A5`, `277-A48` | `APPROVAL_CHANNEL_UNTRUSTED` | No decision and no content access |
| `275-A6` | Retire compound row and split invalid syntax from untrusted/truncated approval UI | Syntax case: `PATH_FORM_UNSUPPORTED`; UI/attestation case: `APPROVAL_CHANNEL_UNTRUSTED` |
| `275-A7` | Retire compound row and split altered identity/scope, path/object mismatch, and budget mismatch | Use one result per fixed setup, under R2 order |
| `275-A8` | Split unavailable/incomplete target identity from a proven mismatch between approved and opened object | Incomplete block/target scope: `BLOCK_SCOPE_UNEVALUABLE`; actual object-binding/containment mismatch: `CONTAINMENT_UNPROVEN` |
| `275-A16` | `BLOCK_RELEASE_UNSUPPORTED` | No release inferred from a stale block revision |
| `275-A18`, `275-A19`, `275-A20` | `PATH_SCOPE_UNAVAILABLE` | No content or directory names |
| `275-A23` | `BUDGET_EXCEEDED` | Atomic reservation; no overspend |
| `275-A24` | Retire compound row and give every crash boundary its own fixture | `UNRESOLVED`; halt new reads; no automatic replay |
| `275-A25` | `LEDGER_UNAVAILABLE` when the completion commit cannot be durably made | Lifecycle `UNRESOLVED`; retain reservation; do not deliver content |
| `275-A28` | `LIST_LIMIT_EXCEEDED` when the 201st actual entry is observed | Deny whole listing; no names |
| `275-A30` | `CONTAINMENT_UNPROVEN` | Deny unsupported hard-link/volume guarantees |
| `275-A31` | Retire/split any distinct race setups | `CONTAINMENT_UNPROVEN`; if content was staged, `DISCARDED` |
| `275-A32` | Retire compound row and split invalid syntax, sensitive entry, and reparse/link entry | Respect R2 gate order; one setup/result per replacement |
| `276-A38` | `REGISTRY_ROLLBACK` for a covered destination-authority epoch mismatch | `DISCARDED` if content was staged |
| `276-A39`, `277-A50` | `DECISION_EXPIRED` for the specified clock invalidation | Expire active decisions/nonces; never revive |
| `276-A43` | `APPROVAL_CHANNEL_UNTRUSTED` for the same idempotency key reused with a different canonical scope digest | Deny, audit, no second decision/nonce/budget |
| `275-A32` / `278-A56b` | Retire composite rows; use the separate cases in §7 below | No “invalid, sensitive, or reparse” or “cached, stale, missing, or unauthenticated” bundles |

Positive cases MUST name their stage-specific result. Grammar acceptance fixtures use `PATH_FORM_ACCEPTED` and explicitly grant no authority. Full authorized read/handoff fixtures use `ALLOW` at the reader gate and `HANDOFF_RETURNED` only if that is the actual durable terminal outcome without a trusted transport acknowledgement. Do not assign `HANDOFF_RETURNED` indiscriminately to every positive grammar or identity fixture.

## 2. P2 — Make overlapping fixtures agree with the total gate order

Entry 278 §5 R2 is the controlling precedence order. Apply these clarifications:

1. Gate 7 (`PATH_SCOPE_UNAVAILABLE`) covers inability to establish the requested path/scope in the permitted phase, including pre-approval safe-preview failure. Gate 8 (`CONTAINMENT_UNPROVEN`) covers a mismatch between the object actually opened and the approved object, including post-approval replacement, link/junction/reparse escape, or failure to prove same-object containment.
2. Retire the current composite `275-A10`. Split changes before Owner approval/scope binding from replacements after the approved binding. A post-approval replacement at open/release is gate 8; if any content was staged, persist `DISCARDED`.
3. Narrow `275-A12` to an otherwise trusted, present and consistent lineage whose referenced scope dimension cannot be evaluated. It returns `BLOCK_SCOPE_UNEVALUABLE`. A demonstrated epoch rollback/mismatch against an independent anchor is instead `REGISTRY_ROLLBACK`.
4. Narrow `277-A47a` to demonstrated registration/checkout-lineage/tombstone epoch rollback against the independent anchor. Retire its “rollback or missing lineage” wording. Add a separate missing/ambiguous lineage fixture returning `BLOCK_SCOPE_UNEVALUABLE`.
5. Split `277-A52` into:
   - registry, credential-trust, revocation-source, or protected destination epoch changed/rolled back between intent and final release: `REGISTRY_ROLLBACK`, lifecycle `DISCARDED`;
   - active-block-set or scope-model evidence stale/missing without a registry/trust/destination rollback: `BLOCK_SCOPE_UNEVALUABLE`, lifecycle `DISCARDED`.
6. Gate 4's `REGISTRY_ROLLBACK` coverage MUST explicitly include every anti-rollback epoch named by C4 R1. Gate 9 remains responsible for an unevaluable active-block set/scope model when there is no higher-priority rollback finding.
7. Keep `BLOCK_SCOPE_UNEVALUABLE` ahead of `BLOCK_RELEASE_UNSUPPORTED` when both could apply. A stale block-release attestation does not overcome the current block revision.

Each conflict above needs its own fixed fixture and one primary result. The same scenario must not survive in two active rows with different expected codes.

## 3. P3 — Add operation-level idempotency and disambiguate principal

Keep R4's issuance key, but define `principal` as the **authenticated principal of the requesting agent**, not the Owner who later approves. The approver's authenticated identity and attestation remain separate fields and evidence.

Issuance idempotency remains exactly:

`(authenticated_requester_agent_principal, requester_session, client_request_token)`

The canonical scope digest is an immutable attribute; changing it under the same key is rejected and audited.

Add a separate operation idempotency key:

`(decision_id, authenticated_requester_session, client_operation_token)`

The trusted server maps this key to exactly one server-generated `operation_id`. It is persisted atomically before the operation can read or release content. A retry after a lost response must return the current persisted state for that operation; it MUST NOT create a new operation ID, intent, budget reservation, or delivery. Reuse of the same operation token with different canonical arguments is rejected with `APPROVAL_CHANNEL_UNTRUSTED` under the current fixed denial taxonomy, audited, and never treated as a new operation.

Retire/rewrite `275-A33` because “restored ledger, duplicate operation ID, and retry after lost reply” is a compound fixture, and the caller cannot choose the server's operation ID. Replace it with separate rollback/integrity, token-reuse mismatch, and lost-response retry fixtures.

**Required test:** perform one bounded read, lose the response, and retry with the same operation token and identical canonical arguments. Return the same persisted terminal state and operation ID, with no second intent, reservation, content delivery, or budget consumption. Reuse the token with different canonical arguments: deny/audit, with no second operation.

## 4. P4 — Separate persisted decision status from operation denial

`EXPIRED` is a persisted decision status returned by a status query; it is not a denial code in R2. An operation presented with an expired decision returns primary result `DECISION_EXPIRED`.

After a process/host restart, a formerly active decision is persisted/reconciled as `EXPIRED` according to R4. A status query returns `EXPIRED`; an attempted read/handoff returns `DECISION_EXPIRED`. Neither path may reactivate the decision, issue a nonce, reset a budget, or create a fresh decision.

Narrow `276-A42` to same-key retry before restart with the same scope: return the current persisted state with no duplicate issuance. Use the post-restart case in `277-A53`; do not let “same decision/state” override R4.

**Required test:** status query after restart → `EXPIRED`; operation against that decision → `DECISION_EXPIRED`; no new nonce/decision/operation/budget.

## 5. P5 — Use one defined delivery/lifecycle vocabulary

The next consolidation MUST include one authoritative ordered lifecycle definition:

1. `INTENT_COMMITTED` — durable intent and reservation exist.
2. `CONTENT_STAGED` — a bounded result exists internally but has not been released.
3. `RELEASE_AUTHORIZED` — final gates passed and durable release authorization is recorded.
4. `HANDOFF_RETURNED` — local handoff API returned; this alone proves neither receipt nor delivery.
5. `DELIVERY_ACKNOWLEDGED` — a trusted acknowledgement event was received and durably recorded, bound to operation ID, recipient and response digest.
6. `DELIVERED` — terminal delivered state, permitted only after the acknowledgement record is durable.
7. `DISCARDED` — staged content was invalidated and will not be delivered.
8. `UNRESOLVED` — durable state cannot establish the outcome; reader is halted pending authenticated reconciliation.

Decision status `EXPIRED` is a separate decision-state field, not an operation lifecycle state.

Therefore `DELIVERY_ACKNOWLEDGED` and `DELIVERED` are not synonyms: the former names the trusted receipt event; the latter is the durable terminal state that follows it. If no trusted acknowledgement exists, the strongest truthful terminal handoff result is `HANDOFF_RETURNED`, not `DELIVERED`.

Retain separate crash fixtures:
- crash after durable `RELEASE_AUTHORIZED` and before the local handoff returns;
- local handoff returned, but the `HANDOFF_RETURNED` ledger commit did not become durable.

In both cases, if recovery only sees the last durable state `RELEASE_AUTHORIZED`, the recovered operation is `UNRESOLVED`; reserve the budget, halt reads, and never automatically replay a potentially delivered response. Do not claim that recovery can distinguish an event whose record was not durable.

## 6. P6 — Cover every denial code, clock boundaries and precedence

The final manifest must contain at least one isolated, deterministic fixture for every stable denial code in R2, including the currently unexercised `DECISION_REVOKED` and `BUDGET_EXCEEDED`. A code being mentioned in prose is not test coverage.

Clock cases must be split:
- wall/elapsed discrepancy exactly 2,000 ms, with suspend semantics established and all other clocks trustworthy: the tolerance alone does **not** expire the decision;
- discrepancy greater than 2,000 ms: `DECISION_EXPIRED`;
- suspend semantics unknown/unavailable: `DECISION_EXPIRED`;
- backward wall-clock step of any detected magnitude: `DECISION_EXPIRED`.

Also add fixed pairwise-precedence fixtures for gates that can coexist, at minimum:
- `UNRESOLVED` prior operation plus an invalid approval signature → `UNRESOLVED`;
- `LEDGER_UNAVAILABLE` plus a later-gate target failure → `LEDGER_UNAVAILABLE`;
- unsupported path syntax plus an out-of-allowlist target → `PATH_FORM_UNSUPPORTED`;
- unevaluable block scope plus an applicable-but-unreleased block → `BLOCK_SCOPE_UNEVALUABLE`;
- expired decision discovered at final validation plus a file over the effective byte cap → `DECISION_EXPIRED`, lifecycle `DISCARDED`.

The linter must show which denial codes have at least one fixture and which gate-precedence pairs have explicit coverage. Missing coverage blocks acceptance.

## 7. P7 — Split composite setups and define final-gate evaluation

Retire and split the following composite fixtures in the consolidated manifest:

- `275-A24`: one fixture per crash boundary. Every unreconciled intent expected result is `UNRESOLVED`.
- `275-A31`: separate post-approval object replacement, link/reparse escape, and in-place writer/content change during staging. Each returns `CONTAINMENT_UNPROVEN`; if content is staged, lifecycle `DISCARDED`.
- `275-A32`: separate invalid entry syntax (`PATH_FORM_UNSUPPORTED`), sensitive target/entry (`PATH_SCOPE_UNAVAILABLE` at the permitted disclosure stage; remain non-oracular pre-approval), and reparse/link entry (`CONTAINMENT_UNPROVEN`). An unsafe actual entry never gets silently filtered from a partial listing.
- `275-A33`: separate ledger/anchor rollback, operation-token conflict, and lost-response idempotent retry.
- `278-A56a`: separate clock disagreement from unknown suspend semantics.
- `278-A56b`: separate unavailable revocation source, stale freshness marker, and missing/unauthenticated freshness proof.

**Final-gate rule:** for operations that reach content staging, the final security gate MUST run even when a bounded staging check has already found a size/list limit failure. Choose the primary result from all conditions detected through that final gate using the R2 order. A higher-priority expiry, revocation, ledger, or unresolved-state finding therefore cannot be hidden by an earlier-observed file/list limit. Content remains withheld in every failure case. Do not continue unbounded reads/enumeration merely to test lower-priority conditions: byte reads stay capped at effective limit plus one byte, and listings stop when the 201st actual entry is observed.

A pre-content failure that prevents any safe operation from starting may stop at its gate. The final-gate rule applies where an operation was staged or entered a state requiring the final re-check.

## 8. P8 — Close all pre-approval object-dependent oracles

During the pre-approval window, requester-visible states, shape and timing must remain uniform for every syntactically valid request, including normal existing/missing targets, sensitive-name targets, symlinks/reparse points, and paths that will later fail containment. Object-dependent results from R2 gates 7–10 and 15–16 MUST NOT be exposed to the requester during this interval. The protected Owner interface/audit may retain separately controlled details.

A sensitive-name rejection must happen before OS lookup. A symlink/reparse containment failure discovered internally must not be returned immediately to the requester.

Define the pre-approval window as the interval from accepted request until the first of: authenticated Owner confirmation, authenticated Owner rejection, or nonce expiry. Nonce expiry MUST be no later than 120 seconds after issuance. Before this window closes, the requester-visible result is exactly `APPROVAL_PENDING` with the same response shape and timing envelope across the specified fixtures. After it closes, the ordinary authorization/gate rules apply; do not expose path/object details through an earlier channel.

Correct `278-A82c` and `278-A82d` to name `APPROVAL_PENDING` explicitly. Correct `278-A82e` to compare the full pre-approval sequence/shape/timing across **all four** normal-existing, normal-missing, sensitive-existing and sensitive-missing cases, not just within pairs.

**Required test:** a requester submits a path that is an outside-root symlink. Before the approval window closes, the requester sees only `APPROVAL_PENDING`; any later permitted failure is delivered through the post-window decision channel as `CONTAINMENT_UNPROVEN`, with no content or target disclosure.

## 9. P9 — Mark the old C3 grammar line superseded

Entry 278 embeds the historical C3 grammar wording from Entry 276 §0, including a line-anchored expression and an incomplete reserved-name range. Although C4 R6 supplies the operative correction, the embedded older wording can be copied as if still normative.

In the next consolidation, mark the historical grammar line explicitly `SUPERSEDED — NOT NORMATIVE` and place the authoritative grammar only in the R6 section:
- use a genuine full-match operation, never a line-end anchor as a substitute for full matching;
- reserved device comparison includes `COM0`–`COM9` and `LPT0`–`LPT9`;
- the reserved-name predicate must not over-reject the documented near-misses.

Artifact lint must reject an active normative grammar containing the old line-anchor construction, unless that occurrence is explicitly marked as historical/superseded. Keep a positive full-match test and a trailing-line-terminator negative test.

## 10. P10 — Apply decision-specific ceilings as well as hard ceilings

For each file or directory operation, compute the effective per-operation ceiling as:

- file bytes: `min(1 MiB, decision_file_byte_cap)`;
- actual directory entries: `min(200, decision_list_entry_cap)`.

The hard caps cannot be raised by a decision. A decision may reduce them. Gates 15 and 16 MUST compare against these effective ceilings, while gate 14 remains the separate aggregate-budget check. If one operation cap is omitted or cannot be evaluated, deny closed; do not silently fall back to a larger value.

**Required tests:** decision cap 4,096 bytes with a 5,000-byte file and otherwise 1 MiB aggregate budget → `FILE_LIMIT_EXCEEDED`; decision cap 10 entries with 11 actual entries and otherwise 200-entry hard cap → `LIST_LIMIT_EXCEEDED`.

## 11. New discriminating tests required in the next manifest

These IDs are proposed additions; keep them globally unique and give each one setup/result fields required by P1.

| Proposed ID | Fixed setup | Expected primary result / lifecycle |
|---|---|---|
| `279-A1` | Status query after restart for a formerly active decision | `EXPIRED` decision status; no operation created |
| `279-A2` | Attempt an operation with that expired decision | `DECISION_EXPIRED`; no nonce/decision/operation/budget reset |
| `279-A3` | One operation response is lost; retry same decision/session/token and identical canonical arguments | Same operation ID/current persisted state; no second intent/reservation/delivery |
| `279-A4` | Reuse the operation token with changed canonical arguments | `APPROVAL_CHANNEL_UNTRUSTED`; audit, no second operation |
| `279-A5` | Approved object replaced by outside-root symlink after approval and before open | `CONTAINMENT_UNPROVEN`; `DISCARDED` if staged |
| `279-A6` | Missing/ambiguous lineage with no rollback evidence | `BLOCK_SCOPE_UNEVALUABLE` |
| `279-A7` | Trust/registry/destination epoch rolled back against independent anchor | `REGISTRY_ROLLBACK`; `DISCARDED` if staged |
| `279-A8` | Active-block-set or scope-model epoch stale without a registry/trust/destination rollback | `BLOCK_SCOPE_UNEVALUABLE`; `DISCARDED` if staged |
| `279-A9` | Decision is authoritatively and freshly proven revoked | `DECISION_REVOKED`; no content |
| `279-A10` | Aggregate operation/session budget is insufficient before reading | `BUDGET_EXCEEDED`; no content |
| `279-A11` | Trusted monotonic/wall comparison differs by exactly 2,000 ms; suspend semantics are known | No expiry from tolerance alone; continue other gates |
| `279-A12` | Clock disagreement exceeds 2,000 ms | `DECISION_EXPIRED` |
| `279-A13` | Clock suspend semantics are unknown | `DECISION_EXPIRED` |
| `279-A14` | Unresolved prior operation and invalid approval signature coexist | `UNRESOLVED`; reader remains halted |
| `279-A15` | Ledger unavailable and a later-gate path failure also exists | `LEDGER_UNAVAILABLE` |
| `279-A16` | Invalid path syntax and an out-of-allowlist target coexist | `PATH_FORM_UNSUPPORTED` before lookup |
| `279-A17` | Unevaluable block scope and an applicable unreleased block coexist | `BLOCK_SCOPE_UNEVALUABLE` |
| `279-A18` | File exceeds the effective file cap and the decision expires during staging/final validation | `DECISION_EXPIRED`; `DISCARDED` |
| `279-A19` | 5,000-byte file, decision file cap 4,096 bytes, aggregate budget 1 MiB | `FILE_LIMIT_EXCEEDED` |
| `279-A20` | 11 actual entries, decision listing cap 10, hard cap 200 | `LIST_LIMIT_EXCEEDED` |
| `279-A21` | Existing outside-root symlink submitted before Owner confirms/rejects or nonce expires | Requester-visible `APPROVAL_PENDING` for the full window; no object-dependent detail |
| `279-A22` | Requester-visible pre-approval sequence for the four existing/missing and sensitive/normal cases is compared as one fixed fixture | Identical shape and timing envelope across all four before window close |
| `279-A23` | Listing has one actual malformed-name entry and no other unsafe entries | `PATH_FORM_UNSUPPORTED`; whole listing withheld |
| `279-A24` | Listing has one sensitive actual entry and otherwise valid entries | `PATH_SCOPE_UNAVAILABLE` at permitted disclosure phase; whole listing withheld |
| `279-A25` | Listing has one reparse/link entry and otherwise valid entries | `CONTAINMENT_UNPROVEN`; whole listing withheld |
| `279-A26` | Revocation source is unavailable at final gate | `REVOCATION_UNAVAILABLE`; staged content discarded |
| `279-A27` | Revocation freshness marker is stale | `REVOCATION_UNAVAILABLE`; staged content discarded |
| `279-A28` | Revocation freshness marker is missing or unauthenticated | `REVOCATION_UNAVAILABLE`; staged content discarded |

The next consolidation MUST also split/rewrite the current compound cases listed in §§1–7. The table above does not silently leave those old rows active.

## 12. Acceptance and evidence boundary

The next candidate is adoptable only after:
1. one consolidated, fetch-back-verified document embeds this amendment with the precedence rule stated at the top;
2. every active manifest row has all P1 fields and one fixed setup/primary result;
3. every denial code and required precedence pair has explicit coverage;
4. the artifact linter accepts unique IDs, the active full-match grammar and no compound result alternatives;
5. a targeted delta reviewer finds no further contradiction.

Evidence labels:
- `PROVEN_BY_SOURCE`: Entry 278 itself was fetched from the public repository and its blob SHA recorded. That establishes the inspected public text and object identity only.
- `OWNER_REPORTED`: the supplied Sonnet/Claude delta report and prior local M0A denial reports.
- `PROPOSED`: all repairs, taxonomies, test cases and acceptance rules in this amendment.
- `UNPROVEN`: every implementation/runtime/platform property, local M0A identity, OS-level object containment, trusted Owner/requester provenance, durable anti-rollback ledger, authoritative revocation freshness, block-scope applicability and supported governance-owned release.

## 13. Next action and operational boundary

**Next actor:** Sonnet/Claude, one focused delta review of Entry 278 plus this Entry 279 amendment. Review the repair requirements and proposed discriminating tests; do not repeat broad source archaeology. Return `PASS`, `PASS_WITH_REPAIRS` or `FAIL`, naming only surviving counterexamples with section, fixed setup, primary result, minimum repair and one test.

After a delta pass, ChatGPT/coordinator should build one new consolidated candidate and fetch it back before another review. Do not overwrite the current Entry 278 artifact in place; preserve it as the historical C4 candidate.

No code implementation, product-source/config edits, tests/builds/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update or launch is authorized. Contract acceptance cannot grant read authority or release an active governance block. `KEEP_BLOCKED`.
