# CHAT-ARCH-2026-10-13-280 — M0B-R8.1 C6 delta adjudication and amendment 274.5

- Episode: CHAT-ARCH-2026-10-13-280
- Date: 2026-10-13 (America/Bogota)
- Input: targeted delta review of Entries 278 and 279, supplied by Sonnet/Claude.
- Status: `M0B_R8_1_AMENDMENT_274_5_PROPOSED_PENDING_TARGETED_DELTA_REVIEW`
- Operational posture: `KEEP_BLOCKED`
- Normative standing: proposed text amendment only. It does not replace Entry 278 or Entry 279 and is not an accepted contract baseline.

## 0. Scope and source provenance

Public artifacts fetched for this adjudication:

- Entry 278: `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-278-m0b-r8-1-consolidated-contract-candidate-274-3.md`
  - Blob SHA: `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`
- Entry 279: `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-279-m0b-r8-1-c5-delta-adjudication-and-amendment-274-4.md`
  - Blob SHA: `fccd67f375c265986215210b5161e684c65b7e27`

The C6 review returned `FAIL` for Entry 279's proposed text. This is a documentary consistency finding, not an implementation finding. The reviewer did not compare the embedded contract clauses against every immutable historical blob from Entries 274–277 and did not inspect the local M0A checkout.

The Owner's supplied report identifies S1–S11. This amendment addresses the recommended bounded set S1–S4, S6–S8 and S11. **S5, S9 and S10 remain explicitly open and are not waived.** They must be reconciled before any replacement consolidated manifest can be accepted. This limited amendment is not itself the final consolidation.

## 1. S1 — One authoritative anti-rollback epoch rule

The anti-rollback gate MUST cover every C4 R1 state whose freshness affects authorization, including:

- workspace/repository/checkout registrations, lifecycle lineage and tombstones;
- the active governance-block set and its revision;
- the authoritative scope-model/version;
- the Owner trust store, enrolled/revoked credentials and trust epoch;
- authoritative revocation-source identity/version and protected freshness state;
- protected destination/recipient configuration;
- any other R1-protected authority state named by the active contract.

**Gate selection:**

1. If a required epoch is readable and is less than, inconsistent with, or not anchored to the independent trusted anti-rollback anchor, select `REGISTRY_ROLLBACK`.
2. If a required store/record is missing, truncated or unreadable, and the independent anchor proves that the state/epoch existed or that its current version must be at least a known value, select `REGISTRY_ROLLBACK`.
3. If there is no proof of rollback, all required epochs are current and consistent with the anchor, but a scope dimension or block application still cannot be evaluated, select `BLOCK_SCOPE_UNEVALUABLE`.
4. `BLOCK_SCOPE_UNEVALUABLE` MUST NOT override a demonstrated rollback. `BLOCK_RELEASE_UNSUPPORTED` is considered only after integrity/epoch and scope-evaluation gates pass and an applicable unreleased block is established.

The ordered R2 table in the next consolidation MUST name all epoch categories explicitly at the anti-rollback gate; do not leave the active-block-set or scope-model epoch only in a test note.

**Discriminating tests:**

- Same fixture except one required epoch is N−1 relative to a valid independent anchor: `REGISTRY_ROLLBACK`.
- All epochs equal N and current, but a named scope dimension is not supported/evaluable: `BLOCK_SCOPE_UNEVALUABLE`.
- Registration/lineage store is missing and the anchor proves a prior committed registration: `REGISTRY_ROLLBACK`.
- Store is present, epochs current, but historical evidence for one referenced scope field is intrinsically unavailable without a rollback signal: `BLOCK_SCOPE_UNEVALUABLE`.

## 2. S2 — Define preview/open phases and prevent object-dependent oracles

Define the operation phases normatively:

- `PREVIEW_PHASE`: from request acceptance until a specific existing filesystem object and its safe scope can be bound to the Owner approval request. No content is read and no reparse/symlink destination is followed to discover a target.
- `APPROVAL_WINDOW`: the fixed public waiting interval defined in §6. The requester sees a uniform state during this interval.
- `OPEN_PHASE`: begins only after a valid approval has been recorded against an established object binding and the reader is about to open/use that same bound object.
- `FINAL_GATE`: final decision/epoch/revocation/budget/containment verification before any staged content can be released.

A path that is already a symlink, junction or reparse point during `PREVIEW_PHASE`, or whose safe object binding cannot be established, has not yet been bound for approval. It MUST select `PATH_SCOPE_UNAVAILABLE` after the disclosure window, never `CONTAINMENT_UNPROVEN` merely because the path currently exists as a link.

`CONTAINMENT_UNPROVEN` applies when a successful approval has established an object binding and the object opened later differs, a link/reparse escape is encountered during open/use, or same-object containment cannot be demonstrated.

For any pre-approval, requester-visible response, the exact internal gate code is not the response code. During `APPROVAL_WINDOW`, all syntactically valid requests return the same requester-visible `APPROVAL_PENDING` envelope. After the window, object-dependent path/list failures use a uniform requester-visible result `REQUEST_UNAVAILABLE`; their specific gate code is retained only in the protected audit result. Do not expose `PATH_FORM_UNSUPPORTED`, `PATH_SCOPE_UNAVAILABLE`, `CONTAINMENT_UNPROVEN`, `BLOCK_SCOPE_UNEVALUABLE`, `BLOCK_RELEASE_UNSUPPORTED`, byte-limit or list-limit codes through a path/list response when doing so would reveal object existence, type, sensitivity or link status. This public-result rule does not override the internal R2 precedence or the protected audit code.

For a listing, all failures caused by an actual entry's forbidden form, sensitive policy, or link/reparse status MUST have the same requester-visible `REQUEST_UNAVAILABLE` shape; the protected audit records the one internal code selected by R2. Never return partial names.

**Discriminating tests:**

- Outside-root symlink already present when requested: during `APPROVAL_WINDOW`, requester gets `APPROVAL_PENDING`; afterward the safe-binding failure is internally `PATH_SCOPE_UNAVAILABLE`, publicly `REQUEST_UNAVAILABLE`.
- Same path was safely bound and approved, then replaced before open with an outside-root link: internally `CONTAINMENT_UNPROVEN`, lifecycle `DISCARDED` if content was staged, publicly `REQUEST_UNAVAILABLE`.
- A missing valid path and an existing-but-unbindable symlink use the same requester-visible shape and public result.
- Directory listings with one invalid, one sensitive, or one reparse entry have identical public failure shape and no names; each individual fixture has one protected internal result.

## 3. S3 — Give each observer and probe a distinct expected-result field

The next conformance manifest MUST replace the single `expected_primary_result` schema in Entry 279 §1 with the following explicit fields:

- `qualified_id`
- `setup` — one fixed reproducible configuration, not a compound list;
- `evaluation_stage`;
- `probe_request` — one of `INITIAL_REQUEST`, `DIAGNOSTIC_ONLY`, `ISSUANCE_RETRY`, `OPERATION_RETRY`, `STATUS_QUERY`, `NEW_OPERATION`, or `RECOVERY_AFTER_CRASH`;
- `expected_result_requester` — exactly one member of the requester-visible vocabulary for that stage;
- `expected_internal_code` — exactly one internal R2 code/state or `NONE`, visible only in the protected audit;
- `expected_decision_status` — exactly one of `NOT_APPLICABLE`, `PENDING`, `ACTIVE`, `EXPIRED`, `REVOKED`, or `NONE`;
- `expected_lifecycle_state` — exactly one lifecycle state or `NOT_APPLICABLE`;
- `classification` — positive, negative, boundary, recovery, concurrency/interleaving, or artifact-validation;
- `oracle_type` — `FIXED_RESULT`, `INTERLEAVING_FORCED`, or `INVARIANT`;
- `traceability` — the clause/gate being discriminated.

These fields have disjoint meanings. A requester-visible `APPROVAL_PENDING` result can coexist with a protected internal `PATH_SCOPE_UNAVAILABLE` result without ambiguity because they occupy separate, explicitly named fields. A diagnostic-only probe can return `DIAGNOSTIC_COMPLETE_NO_DECISION` with `expected_internal_code=NONE`, decision status `NOT_APPLICABLE), and lifecycle `NOT_APPLICABLE`. Nonce replay/rejection also needs an explicit result row rather than an implicit “no second decision”.

The manifest validator MUST reject: missing fields; a token placed in the wrong field vocabulary; multiple or slash-separated expected values; a compound setup; duplicate IDs; a concurrency case with no forced interleaving/invariant oracle; or any active row not connected to a gate/requirement.

## 4. S4 — Distinguish operation replay from a new attempt after expiry

### 4.1 Issuance key

The decision-issuance key remains:

`(authenticated_requester_agent_principal, requester_session, client_request_token)`

The Owner/approver identity is separate evidence. It is not the `principal` term in the requester issuance key.

### 4.2 Operation key

The operation-idempotency key MUST be:

`(decision_id, authenticated_requester_agent_principal, authenticated_requester_session, client_operation_token)`

The trusted server atomically maps that key to one server-generated `operation_id`, canonical argument digest and durable operation state before content I/O or release. Token reuse with different canonical arguments is denied as `APPROVAL_CHANNEL_UNTRUSTED`, audited, and cannot create another operation.

### 4.3 Recovery and status query

A retry with an already registered operation key is a **status/result lookup**, not a new read request. It passes only the ledger-availability, ledger-integrity and unresolved-recovery gates plus authenticated principal/session binding. It returns the current persisted operation ID/state and never returns file content, starts a second intent, makes a new budget reservation, or replays delivery. For an `UNRESOLVED` operation, return `UNRESOLVED` and keep the reader halted.

A new operation token follows the complete R2 order. If the referenced decision is expired, return `DECISION_EXPIRED` and do not create a new operation.

`EXPIRED` is a derived decision status: derive it from the trusted current time, decision expiry and durable restart/freshness marker when queried. The design MUST NOT require a separate expiry-write transaction merely for the passage of time. If the ledger cannot be read to validate the key or current state, return `LEDGER_UNAVAILABLE`; do not claim the status is `EXPIRED` without the evidence needed to derive it.

An already completed operation remains queryable after its associated decision expires. The existence of that prior operation key means the operation retry returns its persisted state; expiry only blocks creation of a new operation or access to new content.

**Discriminating tests:**

- Existing completed operation, response lost, process restarted, same key/arguments: return same `operation_id` and current terminal state; no content redelivery, second intent or budget change.
- Existing unresolved operation, response lost, then restart: return `UNRESOLVED`; halt persists; no replay.
- New operation token after the decision expires: `DECISION_EXPIRED`; no operation record, nonce or budget reservation is created.
- Valid authenticated requester presents an unknown decision ID or a decision bound to another requester session/workspace: use the same public result `DECISION_NOT_APPLICABLE); do not halt the reader or reveal whether the ID exists.
- Ledger unavailable during operation-status query: `LEDGER_UNAVAILABLE), not a fabricated `EXPIRED` status.

## 5. S6 — Fixed requester-visible approval-window boundary

For v1, define `APPROVAL_WINDOW` as a fixed, requester-independent interval of exactly 120 seconds from accepted request time, using a trusted clock with established monotonic/suspend semantics. The public status and response shape remain `APPROVAL_PENDING` until that fixed endpoint, regardless of whether the Owner confirms, rejects, dismisses or does not respond earlier.

Every syntactically valid request in scope receives the same externally visible waiting envelope. The trusted Owner UI receives a prompt for every such request; it may indicate that a target cannot safely be bound and therefore cannot be approved, but that distinction is not visible to the requester during the window. An Owner confirmation/rejection received before the deadline is recorded with its authenticated timestamp and nonce binding. At the fixed endpoint, the issuer may act only on a valid, timely approval receipt and a still-valid target/policy binding. A request with no approval, a rejected request, an expired nonce, or an object that was never safely approvable cannot produce a read decision. Requester-visible timing MUST NOT close early in response to the Owner's action.

If the trusted time basis or fixed endpoint cannot be established, fail closed without issuing a decision. The Owner's independent choice may still carry information; this residual side channel remains `UNPROVEN` and MUST NOT be described as solved by fixed timing.

**Discriminating test:** use an injected clock with an Owner action at t=5 seconds and no action in another run. For normal existing, normal missing, sensitive-by-name and existing-link requests, requester-visible status/shape remains `APPROVAL_PENDING` until the same 120-second endpoint. At the endpoint, internal results may differ, but pre-endpoint requester-visible observations do not.

## 6. S7 — Add a non-terminal, non-enumerating result for inapplicable decisions

Add `DECISION_NOT_APPLICABLE` to the R2 result taxonomy. Update the advertised count from 16 to **17 ordered primary terminal selections**; `UNRESOLVED` remains a fail-stop recovery state, not an ordinary denial code.

The full ordered table for the next consolidation MUST be exactly this sequence, with the first applicable result selected and the stated recovery/phase constraints applied:

1. `LEDGER_UNAVAILABLE` — authoritative ledger state cannot be durably read or a required write cannot be durably committed.
2. `LEDGER_INTEGRITY_UNPROVEN` — a chain, durable-state authenticity or independent-anchor integrity check fails.
3. `UNRESOLVED` — an earlier operation/handoff lacks a reconciled durable state; this is a fail-stop lifecycle result and halts new reads.
4. `REGISTRY_ROLLBACK` — a required anti-rollback epoch is demonstrably stale/inconsistent with the independent anchor, including any R1 authority epoch.
5. `DECISION_NOT_APPLICABLE` — the authenticated requester presents an unknown decision ID or a decision whose principal/session/workspace/target binding does not match; this result does not halt the reader.
6. `APPROVAL_CHANNEL_UNTRUSTED` — authenticated approval evidence, requester identity evidence, UI/issuer separation or nonce provenance/replay protection is untrusted.
7. `PATH_FORM_UNSUPPORTED` — syntax fails the active grammar before filesystem lookup.
8. `PATH_SCOPE_UNAVAILABLE` — a safe path/object scope cannot be established in the permitted phase.
9. `CONTAINMENT_UNPROVEN` — after an approved object binding exists, the actual opened object/containment does not match that binding or cannot be proven.
10. `BLOCK_SCOPE_UNEVALUABLE` — required block/scope evidence is current but cannot establish applicability.
11. `BLOCK_RELEASE_UNSUPPORTED` — the block is established as applicable but no independent valid governance-owned release exists.
12. `DECISION_EXPIRED` — the decision/approval nonce is expired or clock semantics invalidate freshness; an existing operation-key status lookup remains governed by §4.3 instead.
13. `DECISION_REVOKED` — an authenticated authoritative check proves revocation.
14. `REVOCATION_UNAVAILABLE` — authoritative revocation cannot be checked with the required current freshness proof.
15. `BUDGET_EXCEEDED` — aggregate reservation cannot be made atomically before content I/O.
16. `FILE_LIMIT_EXCEEDED` — actual file length exceeds the effective file ceiling after the required final gate is considered.
17. `LIST_LIMIT_EXCEEDED` — actual directory entries exceed the effective listing ceiling after the required final gate is considered.

The first four system-health/fail-stop selections precede request-specific denial evaluation. `DECISION_NOT_APPLICABLE` follows successful requester authentication and ledger/epoch/recovery checks, and precedes approval/path/object checks. Public requester output remains separately governed by §2 and §5; the internal code is retained in protected audit fields.
`DECISION_NOT_APPLICABLE` is used when a validly authenticated requester presents an unknown decision ID, a decision bound to another principal/session/workspace/target, or another non-matching decision binding. It MUST be requester-visible in the same shape for an unknown ID and a known-but-not-applicable ID, and MUST NOT trigger a global reader halt. Do not use `LEDGER_INTEGRITY_UNPROVEN` for a simple unknown ID.

Reserve `LEDGER_INTEGRITY_UNPROVEN` for verified/inferred ledger-chain, durable-state-authenticity or independent-anchor failures. Reserve `LEDGER_UNAVAILABLE` for failures to durably read **or write** required ledger state, including an unavailable intent/completion commit. Such failures fail closed; if a read has already occurred internally but its completion cannot be committed, retain the maximum reservation, mark `UNRESOLVED` when durable state allows, deliver no content, and halt until reconciliation.

For nonce cases: an expired nonce/decision is `DECISION_EXPIRED`; a replayed, mismatched or unauthenticated approval nonce that is not merely expired is `APPROVAL_CHANNEL_UNTRUSTED`. An authenticated operation request whose referenced decision does not apply is `DECISION_NOT_APPLICABLE`. The next consolidated R2 table must place and order this result explicitly, update all shifted gate numbers/references, and map each active fixture to one result.

A missing/invalid per-operation ceiling is a malformed/non-applicable decision and returns `DECISION_NOT_APPLICABLE); never silently default to a more permissive cap. An actual exhausted aggregate budget remains `BUDGET_EXCEEDED).

**Discriminating tests:**

- Unknown decision ID vs known ID bound to another session: same requester-visible `DECISION_NOT_APPLICABLE`; subsequent valid operation is not halted.
- Injected ledger-chain/anchor mismatch: `LEDGER_INTEGRITY_UNPROVEN); reader halts pending reconciliation.
- Required ledger write unavailable: `LEDGER_UNAVAILABLE); no content delivery.
- Expired approval nonce: `DECISION_EXPIRED); replayed nonce: `APPROVAL_CHANNEL_UNTRUSTED).
- Missing per-operation ceiling: `DECISION_NOT_APPLICABLE); no read.

## 7. S8 — Make budget-edge and concurrency fixtures deterministic

The operation MUST atomically reserve the effective deliverable ceiling before content I/O. The effective ceilings are:

- file deliverable bytes: `min(1 MiB, decision_file_byte_cap)`;
- actual directory entries disclosed: `min(200, decision_list_entry_cap)`.

A file read may examine at most one additional byte beyond the effective file ceiling to detect overflow; listing may observe at most the 201st actual entry to detect overflow. That single detection sentinel is bounded internal control overhead, not deliverable content and not charged against the reserved deliverable-byte/entry budget. Record the sentinel occurrence in the operation audit/overhead counter. On overflow, charge the maximum reserved deliverable budget; do not refund it. No partial bytes or names are released. The implementation must also bound this detection overhead so it cannot be used for unbounded probing.

If the aggregate budget cannot reserve the effective deliverable ceiling, return `BUDGET_EXCEEDED` before reading. If the reservation succeeds and the operation proves the file/list exceeds its effective cap, return `FILE_LIMIT_EXCEEDED` or `LIST_LIMIT_EXCEEDED` respectively, even if the extra sentinel is what establishes overflow. The sentinel itself never causes overspend of the reserved deliverable budget.

For a concurrency test, the manifest MUST declare `oracle_type=INTERLEAVING_FORCED` and identify the ledger commit barrier/order that selects the winner. Do not assign a deterministic winner to an uncontrolled race. The invariant oracle for all concurrent schedules is that reservations are atomic and no aggregate budget is overspent.

**Discriminating tests:**

- Remaining deliverable byte budget equals the effective cap; object is cap+1 bytes: `FILE_LIMIT_EXCEEDED), charge the cap reservation, record one bounded detection byte separately.
- Remaining deliverable entry budget equals the effective cap; directory has cap+1 actual entries: `LIST_LIMIT_EXCEEDED), charge the cap reservation and record the sentinel entry separately.
- Two operations contend for the final budget unit. Force operation 1's ledger reservation commit first: operation 1 may pass that gate; operation 2 returns `BUDGET_EXCEEDED`; remaining budget equals zero. Also retain an invariant test over schedules proving no overspend.

## 8. S11 — One physically contiguous manifest and mechanical parse gate

The next consolidated contract MUST contain exactly one authoritative manifest table in one contiguous section. It MUST have one header and separator; all active and retired rows, with status fields, must be inside that table. No prose, subheading, explanatory paragraph or second table may split the manifest.

The manifest parser must count source rows and parsed rows, confirm every active row has every field in §3, validate unique qualified IDs across active and retired rows, and report active/retired totals. The contract text must not claim that the manifest is a single table if rows fall outside its header/separator or if parser results differ from the written count.

**Discriminating test:** fetch back the entire next consolidated artifact; parse the single Section 6 table; require parsed row count equals the explicitly declared row count and all rows belong to that table. A split table with 62 parsed rows and 44 orphaned rows must fail.

## 9. Residual findings intentionally not closed by this amendment

The following findings from the C6 report remain open and are not waived by the present bounded delta:

- **S5 — Composite fixtures and missing lexical/race/crash-boundary cases.** The current candidate still contains compound rows and some proposed replacement coverage is incomplete. Before consolidation, enumerate each lexical rejection class as its own fixed row and complete crash-boundary, root replacement and in-place-writer coverage.
- **S9 — Delivery acknowledgement authority and crash recovery.** A trusted acknowledgement must originate outside requester control, be authenticated and bind operation ID, recipient and response digest. Recovery must cover the last durable state for both `transport_ack_capability=none` and `trusted`; whether `DELIVERY_ACKNOWLEDGED` is a separate event or the transition to `DELIVERED` must be one normative rule.
- **S10 — Coverage of every precedence/boundary mutation.** Enumerate required adjacent-gate pairs and final-gate pairs, test each applicable time limit at T−ε, T and T+ε, test final-gate `DECISION_REVOKED` with staged content, and distinguish supported block-release behavior from a deny-all mutant.

These residuals remain acceptance blockers for the eventual consolidated artifact. The recommended immediate action is one targeted review of this Entry 280 amendment; after that review, resolve S5/S9/S10 before producing a candidate that could be submitted for final acceptance.

## 10. Acceptance, evidence and next actor

The next review is successful only if it confirms the internal consistency of this amendment and that its proposed tests discriminate the named alternatives. It does not accept Entry 278/279 by reference.

Evidence classifications:

- `PROVEN_BY_SOURCE`: Entry 278 and Entry 279 were fetched from their public GitHub paths and their current blob identities recorded.
- `OWNER_REPORTED`: the supplied Sonnet/Claude C6 `FAIL` report and previous M0A refusal reports.
- `PROPOSED`: all clauses, revised vocabularies, gates, test requirements and residual tracking in this entry.
- `UNPROVEN`: every implementation/runtime/platform property, actual M0A identity, Owner/requester isolation, anti-rollback anchor behavior, filesystem handle containment, revocation freshness, durable acknowledgment, authoritative block-scope implementation and any supported governance-owned block release.

**Next actor:** Sonnet/Claude. Perform one targeted delta review of Entry 279 plus this Entry 280 amendment, restricted to S1–S4, S6–S8 and S11. Return `PASS`, `PASS_WITH_REPAIRS` or `FAIL`; each survivor must have a fixed counterexample, expected requester result, expected internal code, lifecycle/decision state where applicable, minimal normative repair and one discriminating test. Do not perform another broad repository audit.

No source implementation, code/config edits, tests/builds/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update or launch is authorized. Contract review cannot issue read authority or release an active governance block. `KEEP_BLOCKED`.
