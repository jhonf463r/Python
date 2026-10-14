# CHAT-ARCH-2026-10-14-282 — C8 adjudication and amendment 274.7

- Status: `M0B_R8_1_AMENDMENT_274_7_PROPOSED_PENDING_TARGETED_DELTA_REVIEW`
- Normalized review verdict: `FAIL` against Entry 281 / amendment 274.6.
- Operational posture: `KEEP_BLOCKED`.
- Type: bounded documentary delta; not a consolidated contract, implementation specification, runtime result, or authorization.

## 0. Scope, verdict normalization, and provenance

This amendment addresses only V1–V9 reported against Entry 281. It does not claim to reconstruct or reconcile the original C7 review blocks that are not present in the inspected material. The detailed C8 findings supplied to the coordinator remain `OWNER_REPORTED`; the source text and current blob identities below were fetched independently.

Current public source identities fetched for this delta:
- Entry 278: `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`.
- Entry 279: `fccd67f375c265986215210b5161e684c65b7e27`.
- Entry 280: `6d7d7f4966e1224456e00410c812395e6a5c598f`.
- Entry 281: `46cf60a60500f942047500c3f19cced0e9beb83d`.

The Entry 281 source still contains the editorial defect at its line 46: the code delimiters for `NONE` and `NOT_APPLICABLE` are malformed. This amendment supplies the corrected, field-scoped definitions below; it does not rewrite Entry 281 itself. Its semantic effect is superseded only where this delta expressly says so.

Historical fidelity of Entries 274–277 remains `UNPROVEN` unless each original object is independently retrieved and compared with the embedded clauses. The supplied report's claim about clone HEAD `0134a01d…` is `OWNER_REPORTED`; this delta does not infer anything about the local M0A checkout.

## 1. Supersession boundary

If accepted, this amendment supersedes only conflicting provisions in the following areas:
- Entry 280 §1 and Entry 281 §1: epoch/anchor comparison and rollback classification.
- Entry 280 §§2–3 and §6, and Entry 281 §§2 and 5: stage-specific requester mapping, schema, and selected-decision validation order.
- Entry 280 §4.3 and Entry 281 §§3–4: unresolved-operation status, issuance outcomes, fixed-window timing, and approval freshness.
- Entry 281 §6 and the conflicting Entry 280 S7/S8 ordering: list-overflow precedence and probe accounting.
- Entry 281 §7: row-like manifest records and parser acceptance.
- Entry 281 §4 and §6: preflight, atomic intent/reservation, and post-commit failure accounting.

Unrelated restrictions remain cumulative. This is not acceptance of Entry 280 or Entry 281. S5, S9, and S10 remain acceptance blockers as specified in §9.

## 2. V1 and V9 — R2 precedence, operation ordering, and reservation

### 2.1 The ordered R2 list remains the base rule, with one explicit list-local exception

The 17 primary internal selections in Entry 280 §6 remain the base ordered taxonomy. The listing exception below is normative and must also be reflected in the next consolidated R2 table; it is not an implicit reinterpretation.

For `list_directory`, first pass the shared ledger, integrity, recovery, anti-rollback, requester-authentication, decision-binding, lexical-form, and directory-target/root-binding checks needed to establish that the requested directory itself is safely bound. Do not enumerate directory contents if one of those checks fails.

After the directory target is safely bound and the operation has a committed intent/reservation, perform a bounded **count-first pass** over actual direct entries. Do not follow, resolve, open, or inspect the destination of an entry while counting. Exclude only exact `.` and `..` names. Observe no more than the effective cap plus one actual entry. Entry count is established before per-entry path/sensitivity/reparse validation.

- If the actual count exceeds the effective cap, select `LIST_LIMIT_EXCEEDED` even if a forbidden, malformed, sensitive, or reparse-point entry appeared earlier in enumeration. This local rule overrides the ordinary per-entry selection order only for the listing's cap decision.
- If the count is at or below the cap, validate every actual entry. Any unsafe entry rejects the entire listing; for the reparse fixture in this delta, the internal result is `PATH_SCOPE_UNAVAILABLE`.
- Never disclose partial names. The requester-visible result for all three fixtures below is the same `REQUEST_UNAVAILABLE`.
- This exception does not override a failure of global health, decision binding, requester authentication, lexical request form, or the directory target/root's own safe binding. It overrides validation of an individual listed entry, not validation of the directory being listed.

The next consolidated R2 table must state this local precedence beside the `LIST_LIMIT_EXCEEDED` row and the per-entry path/scope rows. It must not leave the exception only in prose or a fixture note.

### 2.2 New-operation gate order and atomic intent

For a new operation, evaluate all non-I/O preflight gates in the normative R2 order before creating an operation record or reserving budgets. In particular, ledger/recovery/epoch checks, requester and decision binding, expiry, revocation availability/freshness, block applicability/release, lexical form, and every other preflight gate that does not require content I/O precede the reservation transaction.

The reader then performs one durable atomic transaction committing all of the following together:
- the operation key `(decision_id, authenticated_requester_agent_principal, authenticated_requester_session, client_operation_token)`;
- one server-generated `operation_id`;
- the canonical-argument digest;
- `INTENT_COMMITTED`;
- the maximum deliverable byte/entry/call reservation required for the chosen operation; and
- the operation's fixed one-attempt probe allowance, recorded as an operation-local hard limit rather than a shared consumable pool.

The transaction either commits all fields or commits none. There must be no orphan key, intent, operation ID, or reservation. If available aggregate budget cannot be reserved, return `BUDGET_EXCEEDED` before content I/O and without creating an operation record or intent.

Some gates necessarily have a post-commit verification because they depend on the actual opened object or the state after staging. After intent commit, verify the opened object and containment before reading content. After staging, run the final gate over current ledger/integrity/recovery, protected epochs, requester/decision/session binding, path and object containment, block scope/release, expiry, revocation, and the existing reservation. Do not reserve twice.

A reservation is non-refundable after the intent transaction commits. If a post-commit gate rejects before or after staging, make no content delivery, persist the terminal denial when possible, and retain the reservation. If a required completion/denial commit cannot be made, preserve the `UNRESOLVED` fail-stop state and halt new content-bearing operations. If content has been staged and a final gate fails, set lifecycle `DISCARDED`; do not deliver staged bytes or names.

This ordering fixes the budget-versus-expiry ambiguity: a validly bound decision that is already expired selects `DECISION_EXPIRED` before budget reservation is attempted. An exhausted budget must not mask expiry. That case creates no new intent, operation ID, reservation, or probe attempt.

## 3. V2 — Decision binding before request-selected payload-schema adjudication

A decision record must expose a separately authenticated binding envelope containing its issuer-authenticated principal, session, workspace/checkout, target, and a protected reference/digest for the decision payload. The envelope is only a routing/binding object; it does not itself grant read authority.

The global R2 integrity/availability/recovery/epoch gates remain first. Those checks must concern authoritative global ledger and anchor integrity; they must not turn the semantic validation of an attacker-selected decision payload into a request-triggered global halt.

After requester authentication and global gates:
1. An unknown decision ID yields internal and requester result `DECISION_NOT_APPLICABLE`.
2. A readable, authenticated binding envelope that proves another principal/session/workspace/target owns the decision yields `DECISION_NOT_APPLICABLE`, with the same public response shape as an unknown ID. Do not validate the foreign payload's required-cap schema on this request path, do not halt because of its payload-schema defect, and record a protected anomaly.
3. Only after the binding envelope matches the authenticated requester and target may the issuer/reader validate the full decision payload schema. A matching, present, readable issued record missing a mandatory cap or other required field yields `LEDGER_INTEGRITY_UNPROVEN`, a protected `DECISION_RECORD_SCHEMA_INVALID` validator result, and a reader halt pending reconciliation.
4. Actual global chain, anchor, or durable-state authenticity failure still selects `LEDGER_INTEGRITY_UNPROVEN` at the global gate, independent of request-selected payload fields. An unavailable required ledger read/write remains `LEDGER_UNAVAILABLE`.

The issuer MUST reject issuance unless every mandatory per-operation and aggregate ceiling is present. It MUST NOT repair a malformed issued decision by silently defaulting a cap.

The C8 differential fixture must use a malformed payload whose independently authenticated binding envelope is intact and identifies Owner A. Requester B presenting that ID and B presenting an unknown ID must have the same requester result, no reader halt, and no content I/O. Owner A presenting the same malformed decision must receive the protected integrity result and trigger the halt. The foreign-payload schema must not be adjudicated on B's request path.

## 4. V3–V5 and V7 — One typed manifest schema, fixed result mapping, and issuance outcomes

### 4.1 Field-scoped vocabularies

The next consolidated manifest must use one authoritative set of typed fields. A value accepted in one field is not thereby valid in another. In particular, `UNRESOLVED` is never a requester-result token.

Every fixture row must contain:
- `qualified_id`;
- `status`;
- `setup`;
- `probe_request`;
- `evaluation_stage`;
- `expected_result_requester`;
- `expected_internal_code`;
- `expected_binding_result`;
- `expected_decision_status`;
- `expected_lifecycle_state`;
- `expected_issuance_result`;
- `expected_validator_result`;
- `expected_observation_sequence`;
- `equivalence_group`;
- `state_effects`;
- `classification`;
- `oracle_type`; and
- `traceability`.

Use these exact field-scoped enums:

- `status`: `ACTIVE`, `RETIRED`.
- `probe_request`: `INITIAL_REQUEST`, `DIAGNOSTIC_ONLY`, `ISSUANCE_RETRY`, `OPERATION_RETRY`, `STATUS_QUERY`, `NEW_OPERATION`, `RECOVERY_AFTER_CRASH`, `APPROVAL_ATTESTATION`, `NONCE_REPLAY`.
- `expected_result_requester`: `APPROVAL_PENDING`, `REQUEST_UNAVAILABLE`, `DECISION_NOT_APPLICABLE`, `DECISION_EXPIRED`, `DECISION_ISSUED`, `CONTENT_RELEASED`, `STATUS_RETURNED`, `DIAGNOSTIC_COMPLETE_NO_DECISION`, `REQUEST_DENIED`.
- `expected_internal_code`: one of the 17 ordered R2 internal selections in Entry 280 §6, or `NONE` where the row's stage outcome has no R2 primary code. `NONE` in this field means “no R2 primary code selected”; it does not mean that no decision record exists.
- `expected_binding_result`: `NOT_CHECKED`, `UNKNOWN_ID`, `MATCH`, `MISMATCH`, `BINDING_ENVELOPE_UNTRUSTED`.
- `expected_decision_status`: `NONE`, `NOT_APPLICABLE`, `PENDING_VISIBILITY`, `ACTIVE`, `EXPIRED`, `REVOKED`, `UNAVAILABLE`, `SCHEMA_INVALID`. `NONE` means no decision record exists. `NOT_APPLICABLE` means the field's concept does not apply to that fixture. `UNAVAILABLE` means the required record could not be read. `SCHEMA_INVALID` means a present, readable decision record failed the mandatory schema check. Do not use an ambiguous generic `INVALID` state.
- `expected_lifecycle_state`: `NONE`, `NOT_APPLICABLE`, `INTENT_COMMITTED`, `CONTENT_STAGED`, `RELEASE_AUTHORIZED`, `DELIVERED`, `DELIVERY_ACKNOWLEDGED`, `HANDOFF_RETURNED`, `DISCARDED`, `UNRESOLVED`. `NONE` means no lifecycle record exists; `NOT_APPLICABLE` means lifecycle is not relevant to the fixture. `UNRESOLVED` is permitted here as a typed durable lifecycle value, but it is forbidden in `expected_result_requester`.
- `expected_issuance_result`: `NOT_APPLICABLE`, `DECISION_ISSUED`, `OWNER_REJECTED`, `OWNER_NO_RESPONSE`, `APPROVAL_LATE`, `TARGET_UNBINDABLE`, `OWNER_ATTESTATION_INVALID`.
- `expected_validator_result`: `NOT_APPLICABLE`, `PATH_FORM_ACCEPTED`, `PATH_FORM_REJECTED`, `MANIFEST_VALID`, `MANIFEST_INVALID`, `DECISION_RECORD_SCHEMA_VALID`, `DECISION_RECORD_SCHEMA_INVALID`.
- `classification`: `POSITIVE`, `NEGATIVE`, `BOUNDARY`, `RECOVERY`, `CONCURRENCY_INTERLEAVING`, `ARTIFACT_VALIDATION`.
- `oracle_type`: `FIXED_RESULT`, `FIXED_SEQUENCE`, `INTERLEAVING_FORCED`, `INVARIANT`.

The `evaluation_stage`, `expected_observation_sequence`, `equivalence_group`, `state_effects`, and `traceability` fields must each contain one explicit value or sequence appropriate to their declared type. They cannot contain blank values, slash-separated alternatives, “A or B” outcomes, or compound setups. Duplicate IDs, unknown per-field enums, and equivalence groups without a common observation sequence/comparison rule are invalid.

### 4.2 Exhaustive requester mapping for the 17 R2 selections

The protected internal code and requester result are separate fields. Apply the following exhaustive mapping to a path/list operation after the stage-specific approval-window rule is applied:

1. `LEDGER_UNAVAILABLE` → `REQUEST_DENIED`.
2. `LEDGER_INTEGRITY_UNPROVEN` → `REQUEST_DENIED`.
3. `UNRESOLVED` → `STATUS_RETURNED` only for an authenticated query of an exact existing operation key whose status can be read; for a new content-bearing request while halted, use `REQUEST_DENIED`.
4. `REGISTRY_ROLLBACK` → `REQUEST_DENIED`.
5. `DECISION_NOT_APPLICABLE` → `DECISION_NOT_APPLICABLE`.
6. `APPROVAL_CHANNEL_UNTRUSTED` → `REQUEST_DENIED`.
7. `PATH_FORM_UNSUPPORTED` → `REQUEST_UNAVAILABLE` when a requester result is returned for a path/list request.
8. `PATH_SCOPE_UNAVAILABLE` → `REQUEST_UNAVAILABLE`.
9. `CONTAINMENT_UNPROVEN` → `REQUEST_UNAVAILABLE`.
10. `BLOCK_SCOPE_UNEVALUABLE` → `REQUEST_UNAVAILABLE`.
11. `BLOCK_RELEASE_UNSUPPORTED` → `REQUEST_UNAVAILABLE`.
12. `DECISION_EXPIRED` → `DECISION_EXPIRED` for a new operation token using a bound decision that expired. For a late approval that leaves no usable decision at the fixed visibility endpoint, use `REQUEST_UNAVAILABLE`.
13. `DECISION_REVOKED` → `REQUEST_DENIED`.
14. `REVOCATION_UNAVAILABLE` → `REQUEST_DENIED`.
15. `BUDGET_EXCEEDED` → `REQUEST_DENIED`.
16. `FILE_LIMIT_EXCEEDED` → `REQUEST_UNAVAILABLE`.
17. `LIST_LIMIT_EXCEEDED` → `REQUEST_UNAVAILABLE`.

The stage-specific fixed-window outputs take precedence over these ordinary mappings: while the fixed approval window remains open, every accepted syntactically valid request receives the same `APPROVAL_PENDING` envelope, without an internal gate code in requester-visible output. At the endpoint, a valid still-usable hidden decision gives `DECISION_ISSUED`; absent an eligible decision, give `REQUEST_UNAVAILABLE`. A request-specific internal code remains in the protected audit field.

A diagnostic-only probe with no decision record uses requester result `DIAGNOSTIC_COMPLETE_NO_DECISION`, internal code `NONE`, decision status `NONE`, and lifecycle `NOT_APPLICABLE`. A status query never releases content. A public result field may never contain an internal R2 code or a lifecycle token.

### 4.3 Separate issuance-stage results and precedence

The 17 R2 codes do not exhaustively describe Owner/issuer stage outcomes. Use `expected_issuance_result` to record them rather than inventing a seventeenth-plus-one R2 code or overloading `NONE`.

- A timely explicit Owner rejection yields issuance result `OWNER_REJECTED`, decision status `NONE`, and no decision issuance. The internal R2 code is `NONE`; after the fixed endpoint the requester sees `REQUEST_UNAVAILABLE`.
- No Owner response through the fixed endpoint yields `OWNER_NO_RESPONSE`, decision status `NONE`, and no decision issuance. The internal R2 code is `NONE`; the requester sees `APPROVAL_PENDING` before the endpoint and `REQUEST_UNAVAILABLE` at the endpoint.
- An approval/attestation arriving after its challenge or approval-freshness deadline, or a timely attestation for which no hidden decision is durably committed before the fixed endpoint, yields `APPROVAL_LATE` and internal `DECISION_EXPIRED`. This time-expiry result takes precedence over evaluating or exposing whether the target was bindable; the requester sees `APPROVAL_PENDING` before the fixed endpoint and `REQUEST_UNAVAILABLE` when no usable decision exists at/after it.
- A timely valid approval with no safely established target binding yields `TARGET_UNBINDABLE`, internal `PATH_SCOPE_UNAVAILABLE`, and requester `REQUEST_UNAVAILABLE` at the endpoint.
- An invalid/replayed/untrusted Owner attestation yields `OWNER_ATTESTATION_INVALID` and internal `APPROVAL_CHANNEL_UNTRUSTED`.
- Only valid fresh approval plus a safe binding and all issuance gates can yield `DECISION_ISSUED`.

The Owner prompt remains visible in the trusted Owner channel even for an unapprovable target; that fact is not shown to the requester. Rejection, no response, late approval, invalid attestation, and unbindable target must not be represented as one interchangeable `NONE` result in the issuance field.

## 5. V3 and V5 — Unresolved status query and required-record unavailability

### 5.1 `UNRESOLVED` is not a requester result

An exact authenticated `STATUS_QUERY` for an existing operation whose durable operation record is readable returns `STATUS_RETURNED`, including when that operation's lifecycle is `UNRESOLVED`. The protected internal code and lifecycle are both `UNRESOLVED`; the requester-result field must not contain that token. The reader remains halted for new content-bearing operations. A status lookup creates no new intent/reservation, returns no content, and does not resume or reconcile the reader.

A new operation, initial content request, or other content-bearing request while the reader is halted returns `REQUEST_DENIED` with internal/lifecycle `UNRESOLVED`. Thus the result depends on the probe stage, not on inconsistent token vocabularies.

### 5.2 A required decision-record read failure is not `NOT_APPLICABLE`

A status query's required durable read failure returns public `REQUEST_DENIED` and internal `LEDGER_UNAVAILABLE`. It must not return `STATUS_RETURNED` merely because the operation record was readable, and must not use `NOT_APPLICABLE` to mean “decision record unavailable.”

For the paired status-query fixtures:
- If the linked decision record exists but an I/O error prevents reading it, use decision status `UNAVAILABLE`, internal `LEDGER_UNAVAILABLE`, public `REQUEST_DENIED`, and no content redelivery.
- If an authenticated tombstone proves that no linked decision record exists, use decision status `NONE`. If the operation record is authenticated and terminal and no other required state is unavailable, the status query may return `STATUS_RETURNED` with the terminal operation state and no content redelivery.

`NOT_APPLICABLE` is reserved for a field whose concept truly does not apply to that fixture. An unreadable record, missing record without a tombstone, or malformed record must never be silently converted to `NOT_APPLICABLE`.

## 6. V6 — Define row-like IDs and repair manifest acceptance

The next consolidated contract must contain exactly one authoritative, physically contiguous Markdown conformance-manifest table. Historical fixture suggestions from Entries 279–282 must be prose records, not additional pipe-delimited fixture tables.

A normalized `qualified_id` must match `^[0-9]{3}-A[0-9]+[a-z]?$`. It contains the three-digit entry number, `-A`, one or more digits, and optionally one lowercase suffix. The `status` is a separate column and is exactly `ACTIVE` or `RETIRED`. Do not append status text to the ID.

For parser purposes, a **row-like ID** is a physical Markdown line whose first non-whitespace character is `|` and whose first cell, after trimming whitespace, matches the normalized `qualified_id` pattern. A citation such as “see 278-A17a” in ordinary prose is not row-like. A pipe-delimited row whose first cell is a qualified ID but which appears outside the sole manifest table is an orphan and invalidates the artifact.

Declare the total row count immediately before the manifest table. Acceptance requires all of the following:
- exactly one contiguous authoritative manifest table with one header and one separator;
- parsed table row count equals the declared row count;
- parsed table rows equals the total row-like IDs found across the entire artifact;
- every qualified ID is unique across active and retired rows;
- each row has every required field;
- every active row uses field-valid enum values;
- no orphan row, ID with a status suffix, duplicate normalized ID, or unescaped pipe that changes cell count exists.

The 62-row table plus 44 orphan-ID fixture must fail even when the declared count says 62. The same ID active and retired must fail as a duplicate. An unescaped pipe that adds a cell must fail. An ID such as `275-A17 [RETIRED]` must fail normalization; the next consolidated artifact must represent it as `qualified_id=275-A17` and `status=RETIRED`. Do not rewrite the historical Entry 278 record merely to make it appear conformant.

Required parser fixtures: a prose citation that is accepted; a qualified-ID pipe row outside the manifest that is rejected; the valid one-table positive case; and the three negative cases above. Each failure returns validator result `MANIFEST_INVALID`, not a delivery or requester transport state.

## 7. V8 — Authoritative anti-rollback comparison

The following comparison replaces any broader wording in Entry 280/281 that treated “not anchored” or “inconsistent” as automatically equivalent to rollback:

- If an authenticated anchor contains a required epoch value and a readable, authenticated store value is lower than that anchored value, select `REGISTRY_ROLLBACK`.
- If the store value is higher than the authenticated anchor value, select `LEDGER_INTEGRITY_UNPROVEN`, not `REGISTRY_ROLLBACK`, unless a separately specified and authenticated write-ahead/anchor-commit protocol proves exactly how that state is valid. This amendment defines no such exception.
- If the anchor schema/coverage for a mandatory epoch category is absent, malformed, incomplete, or unauthenticated, select `LEDGER_INTEGRITY_UNPROVEN`. Do not infer rollback from an anchor that does not reliably state the category.
- If authenticated anchor evidence proves that a workspace was previously registered or establishes a committed minimum epoch, but the required current registration/tombstone is missing or below that minimum, select `REGISTRY_ROLLBACK` when the stale/missing state is demonstrable.
- If a valid anchor explicitly proves the workspace has never been registered, but the required current scope/registration evidence is insufficient to evaluate an applicable block, select `BLOCK_SCOPE_UNEVALUABLE`.
- Current, anchor-consistent epochs do not make an unsupported or incomplete scope model evaluable; that remains `BLOCK_SCOPE_UNEVALUABLE`.

Retain all protected epoch categories already listed in Entry 280 §1, including workspace/checkout registration and lineage/tombstones, active-block set/revision, scope-model version, Owner trust/credential lifecycle, revocation-source identity/version, and protected destination/recipient configuration. The next consolidated R2 table must implement the comparison rule explicitly. It must not silently supersede the prior clause.

## 8. V1–V9 discriminating fixture requirements

These fixtures are requirements for the next manifest; they are not evidence that a runtime implementation behaves this way.

### V1 — List overflow versus per-entry invalidity

Assume the directory target/root is safely bound, all shared R2 gates pass, and the effective listing cap is 200.
- 201 actual entries with a reparse point at entry 1: internal `LIST_LIMIT_EXCEEDED`, public `REQUEST_UNAVAILABLE`, lifecycle `DISCARDED`, maximum deliverable reservation charged, one operation-local probe attempt.
- 201 actual entries with a reparse point at entry 201: same internal/public/state result as the preceding fixture.
- 200 actual entries with a reparse point at entry 200: internal `PATH_SCOPE_UNAVAILABLE`, public `REQUEST_UNAVAILABLE`, lifecycle `DISCARDED` for the buffered names, maximum reservation retained, one bounded end/probe attempt.

The equivalence group for requester observations must be identical across all three. Enumeration must count before per-entry validation and must not follow or resolve any reparse point.

### V2 — Malformed decision payload bound to another principal

- Requester B presents an ID whose authenticated binding envelope belongs to A and whose readable payload lacks a mandatory cap: internal/public `DECISION_NOT_APPLICABLE`; binding result `MISMATCH`; no content I/O; no request-triggered halt; anomaly recorded.
- Requester B presents an unknown ID: same requester result and observation shape; binding result `UNKNOWN_ID`; no halt.
- A presents the malformed decision bound to A: internal `LEDGER_INTEGRITY_UNPROVEN`, public `REQUEST_DENIED`, validator `DECISION_RECORD_SCHEMA_INVALID`, decision status `SCHEMA_INVALID`, reader halted pending reconciliation.

### V3 — Existing unresolved operation versus new operation

- Exact authenticated status query for a readable unresolved operation: public `STATUS_RETURNED`, internal/lifecycle `UNRESOLVED`, no content, no new intent or reservation; reader remains halted for new reads.
- New operation while that unresolved state halts the reader: public `REQUEST_DENIED`, internal/lifecycle `UNRESOLVED`, no second intent/reservation.

### V4 — Owner rejection, no response, and late approval

Use otherwise identical fixtures and fixed trusted clock observations at T0, T0+5 seconds, T0+120 seconds, and T0+121 seconds.
- Owner rejection at T0+5 seconds: `OWNER_REJECTED`, internal code `NONE`, decision status `NONE`.
- No Owner response through T0+120 seconds: `OWNER_NO_RESPONSE`, internal code `NONE`, decision status `NONE`.
- Approval arriving at T0+121 seconds: `APPROVAL_LATE`, internal `DECISION_EXPIRED`, decision status `NONE`; it cannot create or reveal a usable decision.

All three have `APPROVAL_PENDING` before the fixed endpoint and `REQUEST_UNAVAILABLE` once the endpoint has passed without a usable hidden decision. The late approval must not be recoded as `PATH_SCOPE_UNAVAILABLE` merely because the target is unbindable.

### V5 — Decision-record I/O failure versus authenticated tombstone

- Terminal operation record is readable, but its required linked decision record returns an I/O error: `REQUEST_DENIED`, internal `LEDGER_UNAVAILABLE`, decision status `UNAVAILABLE`, no content redelivery.
- Terminal operation record is readable and an authenticated tombstone proves no linked decision record exists: decision status `NONE`; `STATUS_RETURNED` may report the terminal operation state if no other required read fails. No content redelivery.

These outcomes must not use `NOT_APPLICABLE` to represent a read failure or a record absence.

### V6 — Row-like manifest IDs

- A prose citation to `278-A17a` outside any manifest row: valid for this parser check.
- A pipe-delimited row outside the sole manifest whose first cell is `278-A17a`: `MANIFEST_INVALID`.
- A valid single-table artifact whose parsed, row-like, and declared counts agree: accepted.
- The 62-plus-44 orphan case, duplicate active/retired ID, malformed status-in-ID, and extra-cell unescaped-pipe cases: `MANIFEST_INVALID`.

### V7 — Field-scoped vocabulary

- `expected_decision_status=PENDING`: reject as `MANIFEST_INVALID`.
- `expected_decision_status=PENDING_VISIBILITY`: accept if the setup states that a durable decision is hidden until T0+120 seconds.
- `expected_result_requester=UNRESOLVED`: reject; `UNRESOLVED` remains a typed internal/lifecycle state only.
- `expected_result_requester=REQUEST_DENIED`, `expected_internal_code=UNRESOLVED`, and `expected_lifecycle_state=UNRESOLVED`: accept only for a matching halted new-operation fixture.
- A generic `INVALID` token in the decision-status field is invalid; use the precise validator and `SCHEMA_INVALID` decision-status value only where the present decision record is readable but malformed.

### V8 — Store/anchor direction

- Store epoch N+1 and authenticated anchor epoch N: `LEDGER_INTEGRITY_UNPROVEN`, halt; not `REGISTRY_ROLLBACK`.
- Store epoch N−1 and authenticated anchor epoch N: `REGISTRY_ROLLBACK`, halt.
- Required epoch category missing from anchor coverage: `LEDGER_INTEGRITY_UNPROVEN`.
- Authenticated evidence of a genuinely never-registered workspace with unevaluable applicable scope: `BLOCK_SCOPE_UNEVALUABLE`.

### V9 — Expiry, budget, reservation, and probe

- Bound decision expired and aggregate budget exhausted: `DECISION_EXPIRED`, no intent, operation ID, reservation, or probe attempt. Expiry is adjudicated before budget commit.
- Decision valid but aggregate budget cannot be atomically reserved: `BUDGET_EXCEEDED`, no intent or operation record and no content I/O.
- Decision valid, reservation committed, and a later containment/revocation/final-gate check fails: retain the reservation, persist terminal denial when possible, discard any staged result, release no content, and leave `UNRESOLVED` plus halt if required durable recording fails.
- The probe allowance is exactly one bounded attempt per operation, not a shared or cross-session budget pool. It cannot independently become “exhausted” before the operation exists. Record `probe_attempts_used` from zero to at most one in the operation audit. Only a failure to reserve the defined aggregate deliverable/call budget produces `BUDGET_EXCEEDED`; do not invent an unreservable-probe branch.
- Force the ledger transaction order in concurrency tests. The invariant is no aggregate overspend, no duplicate intent for an idempotent key, and at most one probe attempt per operation.

## 9. Residual acceptance blockers — unchanged

These remain mandatory blockers before accepting a consolidated contract. This delta does not claim to close them.

- **S5 — Composite fixtures and lexical/race/crash boundaries:** split every remaining compound setup; enumerate each rejected lexical class; cover every crash boundary; test root replacement, path replacement, an in-place concurrent writer, and a valid sensitive-name pre-approval case; verify retired tests have adequate replacements.
- **S9 — Trusted delivery acknowledgement:** define acknowledgement authority outside requester control and bind it to operation ID, recipient, and response digest. Specify crash recovery for both no-ack transport and trusted-ack modes. Define one rule for `DELIVERY_ACKNOWLEDGED` versus `DELIVERED`.
- **S10 — Precedence and temporal-boundary mutation coverage:** enumerate relevant adjacent-gate and final-gate precedence pairs; test every applicable limit at T−ε, T, and T+ε; test final-gate `DECISION_REVOKED` with staged content; and ensure the suite rejects a deny-all implementation. Specifically add boundary cases for challenge nonce TTL (proposed maximum 120 seconds), approval-to-issuance freshness (proposed maximum 60 seconds), the fixed public endpoint (T0+120 seconds), decision expiry (proposed maximum five minutes from `not_before`), and authoritative revocation freshness. Each TTL/freshness limit uses the strict interval `now < deadline`; equality is expired. The hidden decision must be durably issued before the fixed endpoint and while the challenge and approval-freshness limits are both valid. Its issuance deadline is the earliest of Owner-attestation time plus 60 seconds, challenge creation time plus 120 seconds, and T0+120 seconds. `not_before` controls visibility at T0+120 and starts the usable decision lifetime. A valid hidden decision is not rejected merely because the Owner's attestation is older at T0+120 than it was at issuance, but revocation, current policy, identity, epochs, scope, and expiry are rechecked at the final gate.

For timing coherence, the proposed timeline is: T0 is trusted request acceptance; the public approval window ends at T0+120 seconds; Owner attestation remains valid only while its challenge and freshness deadlines remain open; the hidden decision must be durably committed strictly before the earliest deadline defined above and before T0+120 seconds; the hidden decision has `not_before=T0+120s`; and its usable lifetime starts at `not_before`, with the existing proposed five-minute ceiling. At exactly any challenge/freshness expiry deadline, that evidence is expired. The next review must test T−ε/T/T+ε at each relevant limit. Stating these limits does not close S10's mutation-coverage requirement.

## 10. Acceptance, evidence, and next actor

This amendment may receive `PASS` only if a targeted review demonstrates that V1–V9 have one unambiguous normative rule each, their fixtures discriminate the named alternatives, and no new contradictions remain between the delta and the exact Entry 280/281 clauses it supersedes. A result of `PASS_WITH_REPAIRS` must enumerate the remaining local repairs. Any conflict in outcome vocabularies, priority, state effects, or fixture observability is `FAIL`.

Evidence labels:
- `PROVEN_BY_SOURCE`: current public Entry 278, 279, 280, and 281 content and the blob IDs listed in §0 were fetched through the connected source route.
- `OWNER_REPORTED`: the supplied C8 review narrative, its sandbox-clone HEAD report, and earlier local M0A reports.
- `PROPOSED`: every repair rule and test requirement in this amendment.
- `UNPROVEN`: fidelity to all original Entry 274–277 objects, any implementation/runtime/platform behavior, local M0A identity or state, actual anti-rollback enforcement, filesystem containment, Owner/requester isolation, revocation freshness, trusted delivery acknowledgement, and production block-scope/release behavior.

**Next actor:** Sonnet/Claude. Review Entry 280 only where referenced as the parent baseline, Entry 281, and this Entry 282. Return exactly one `PASS`, `PASS_WITH_REPAIRS`, or `FAIL` for V1–V9. Do not perform broad repository archaeology; do not attempt S5/S9/S10 closure in this pass, but verify that all three remain visible acceptance blockers.

No implementation, source/config changes, builds/tests/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update, launch, or canonical-route rewrite is authorized by this document. It cannot grant repository-read authority or release a governance block. `KEEP_BLOCKED`.
