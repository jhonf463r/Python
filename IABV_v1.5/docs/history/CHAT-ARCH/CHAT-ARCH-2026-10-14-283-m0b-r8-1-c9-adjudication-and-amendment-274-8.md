# CHAT-ARCH-2026-10-14-283 — C9 adjudication and amendment 274.8

- Status: `M0B_R8_1_AMENDMENT_274_8_PROPOSED_PENDING_TARGETED_DELTA_REVIEW`
- Normalized review verdict: `FAIL` against Entry 282 / amendment 274.7.
- Operational posture: `KEEP_BLOCKED`.
- Type: bounded documentary delta for W1–W11; not a consolidated/accepted contract, implementation specification, runtime result, or authorization.

## 0. Scope, provenance, and routing

The supplied Claude C9 review returns `FAIL` and identifies W1–W11. This entry converts those findings into one bounded proposed amendment. It does not claim that the proposed clauses have passed review or that an implementation behaves accordingly.

Current public sources were re-fetched before this amendment:
- Entry 280 blob: `6d7d7f4966e1224456e00410c812395e6a5c598f`.
- Entry 281 blob: `46cf60a60500f942047500c3f19cced0e9beb83d`.
- Entry 282 blob: `0fa5cc1cb8f63c05c7309ec7dcb98966d738ecf3`.

Source file:
`https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-14-282-m0b-r8-1-c8-adjudication-and-amendment-274-7.md`

The C9 report's SHA computations and sandbox-clone HEAD are `OWNER_REPORTED`. The current public document text and blob values above are `PROVEN_BY_SOURCE`. The historical fidelity of Entries 274–277 remains `UNPROVEN`; no inference is made about the local M0A checkout.

This is the next review in the existing Claude/Sonnet review sequence. The next actor is explicitly Claude/Sonnet for a targeted review of Entry 280, Entry 281 only where needed to identify superseded clauses, Entry 282, and this Entry 283. Do not route the next prompt to the owner for manual analysis and do not treat this entry as accepted.

## 1. Supersession boundary

If accepted, this amendment supersedes only the conflicting parts of Entry 282:
- §4.2–4.3 and the requester-field prohibition in §4.2: public tokens that intentionally share a spelling with internal results, and issuance-stage outcome precedence.
- §§4.1, 5.1–5.2 and fixture guidance: operation-local lifecycle versus global reader state; mandatory status-query dependencies and missing/malformed linked decision records.
- §3 and the binding-related field rules: a selected decision's unauthenticated binding envelope.
- §§2.1–2.2 and §8: terminal denial states, list overflow lifecycle, and phase-aware precedence across preflight/reservation/open/final-gate stages.
- §6: row-like candidate detection for malformed/orphaned manifest IDs.
- §4.1 and §8: explicit stage enums, state-effects grammar, observer-specific fields, and visibility-before-`not_before` behavior.

All unrelated controls remain cumulative. Entry 280 is still a proposed parent contract, Entry 281 remains a proposed amendment, and Entry 282 remains a failed review target. No canonical-route file is changed by this entry.

## 2. W1 and W11 — Issuance outcomes, fixed-window precedence, and hidden decisions

### 2.1 Normative issuance outcomes

Use this field-scoped enum for `expected_issuance_result`:
`NOT_APPLICABLE`, `DECISION_ISSUED`, `OWNER_REJECTED`, `OWNER_NO_RESPONSE`, `APPROVAL_LATE`, `APPROVAL_FRESHNESS_EXPIRED`, `TARGET_UNBINDABLE`, `OWNER_ATTESTATION_INVALID`, `ISSUANCE_FAILED`, `ISSUANCE_DEADLINE_MISSED`.

The outcomes are distinct and the following order is normative:

1. An unauthenticated, replayed, mismatched, or otherwise untrusted Owner attestation yields `OWNER_ATTESTATION_INVALID` and internal `APPROVAL_CHANNEL_UNTRUSTED`. Do not issue a decision.
2. An attestation received at or after the strict challenge deadline is `APPROVAL_LATE` with internal `DECISION_EXPIRED`. `APPROVAL_LATE` means the attestation itself arrived late; do not use it to represent every failed issuance.
3. An attestation received before the challenge deadline but whose attestation-to-issuance freshness interval is no longer valid at the attempted issuance time yields `APPROVAL_FRESHNESS_EXPIRED` with internal `DECISION_EXPIRED`.
4. A valid, timely, still-fresh attestation whose target cannot be safely bound yields `TARGET_UNBINDABLE` with internal `PATH_SCOPE_UNAVAILABLE`. The decision status is `NONE`. Do not relabel this case as late approval.
5. If all approval, freshness, target-binding, policy, block, and revocation gates pass but the authoritative decision-ledger write fails or its durability cannot be established, yield `ISSUANCE_FAILED` with internal `LEDGER_UNAVAILABLE`. No decision is considered issued; decision status is `NONE`; the ledger/reader follows the applicable fail-closed health rule.
6. If the ledger remains available but the hidden decision cannot be durably committed strictly before the fixed visibility endpoint and before the challenge/freshness deadline, yield `ISSUANCE_DEADLINE_MISSED` with internal `DECISION_EXPIRED`. Do not issue or reveal a late decision.
7. A valid, fresh approval plus safe binding and all issuance gates may yield `DECISION_ISSUED` only after the hidden decision is durably committed before every applicable deadline.

A prompt/rejection/no-response has no decision record. `OWNER_REJECTED` means the Owner explicitly rejected in time; `OWNER_NO_RESPONSE` means no authenticated choice was received by the fixed endpoint. Both have internal code `NONE` and decision status `NONE`. An absent response is not a failed ledger write. A failed write is not a no-response.

### 2.2 One strict timing rule

Let:
- `T0` be trusted acceptance time for a syntactically valid initial request;
- `Dchallenge` be challenge creation time plus 120 seconds;
- `Downer` be authenticated Owner-attestation time plus 60 seconds;
- `Dwindow` be `T0 + 120 seconds`.

The decision-ledger commit deadline is the earliest of `Dchallenge`, `Downer`, and `Dwindow`. Each deadline is strict: issuance is timely only if the durable commit time is strictly less than all three. Equality is expired. These values remain proposed defaults and still require the S10 boundary suite.

A safely bound hidden decision has `not_before = Dwindow` and cannot be redeemed, listed, or confirmed as present before that time. Its usable decision lifetime begins at `not_before`. A decision not durably committed before the deadline does not become usable merely because a write completes later.

### 2.3 Window versus lexical rejection

The order is fixed:

1. Validate transport/request-envelope framing and required field types. A malformed envelope is rejected before request acceptance; no `T0` or Owner approval window is created.
2. Validate the active lexical path grammar without filesystem lookup. If unsupported (including traversal forms such as `..`), return public `REQUEST_UNAVAILABLE` with internal `PATH_FORM_UNSUPPORTED`; no Owner prompt, decision, operation intent, filesystem lookup, or content I/O is permitted. This class is outside the fixed waiting window because it is not an accepted syntactically valid path request.
3. Only after steps 1–2 pass, accept the request and set `T0`. During the fixed window, requester-visible response for the initial request is `APPROVAL_PENDING` regardless of Owner action or protected target-binding failure. The Owner prompt remains within the trusted Owner channel, including where the target cannot safely be bound.
4. At or after `Dwindow`, a usable hidden decision gives `DECISION_ISSUED`; absent an eligible hidden decision, return `REQUEST_UNAVAILABLE`. The protected issuance result and internal code remain in the audit.
5. A separate operation/status request that supplies a decision ID before its `not_before` is treated exactly like an unknown ID: public and internal result `DECISION_NOT_APPLICABLE`, same observation shape, no halt, no content I/O. Do not expose `PENDING_VISIBILITY` as an ID-existence response. The hidden-decision rule is stage-specific and does not override the public `APPROVAL_PENDING` response for the original initial request during its own fixed window.

### 2.4 Discriminating fixtures

- Valid attestation at `T0 + 5s`, target unbindable: `TARGET_UNBINDABLE` / `PATH_SCOPE_UNAVAILABLE`; it is not `APPROVAL_LATE`.
- Attestation at `T0 + 121s` where the challenge deadline is `T0 + 120s`: `APPROVAL_LATE` / `DECISION_EXPIRED`.
- Attestation is timely and target safely bound, but authoritative write fails: `ISSUANCE_FAILED` / `LEDGER_UNAVAILABLE`.
- Attestation and target are valid, but the ledger commit completes at exactly `Dwindow`: `ISSUANCE_DEADLINE_MISSED` / `DECISION_EXPIRED`, no usable decision.
- A hidden ID supplied before `not_before` and an unknown ID have identical requester-visible response and timing class.
- A path request containing `..` is rejected before `T0`; a lexically valid, object-missing path follows the normal fixed window. No filesystem existence check occurs for the lexical rejection fixture.

## 3. W2 and W7 — Field-scoped vocabulary and lifecycle state

### 3.1 Canonical requester-result enum

The only valid values for `expected_result_requester` are:
`APPROVAL_PENDING`, `REQUEST_UNAVAILABLE`, `DECISION_NOT_APPLICABLE`, `DECISION_EXPIRED`, `DECISION_ISSUED`, `CONTENT_RELEASED`, `STATUS_RETURNED`, `DIAGNOSTIC_COMPLETE_NO_DECISION`, `REQUEST_DENIED`.

`DECISION_NOT_APPLICABLE` and `DECISION_EXPIRED` are deliberately shared spellings: they are stable public protocol results in the requester field and also identify internal primary selections in `expected_internal_code`. Their spelling alone does not expose additional diagnostic detail. They are the only shared public/internal R2 spellings. No other R2 code may be copied into `expected_result_requester`. In particular, `UNRESOLVED` is never a requester-result token.

Replace Entry 282 §4.2's blanket statement that a public result field may never contain an internal R2 code. The normative rule is the field-specific allowlist above, including the two explicit shared spellings. The validator must validate the value against the enum belonging to its field, not infer validity or invalidity from cross-field token equality.

### 3.2 Operation-local lifecycle versus global reader state

Add `DENIED` to `expected_lifecycle_state`. The lifecycle enum is now exactly:
`NONE`, `NOT_APPLICABLE`, `INTENT_COMMITTED`, `CONTENT_STAGED`, `RELEASE_AUTHORIZED`, `DELIVERED`, `DELIVERY_ACKNOWLEDGED`, `HANDOFF_RETURNED`, `DENIED`, `DISCARDED`, `UNRESOLVED`.

Field semantics:
- `NONE` means no lifecycle record exists for the operation represented by this fixture.
- `NOT_APPLICABLE` means that the lifecycle concept does not apply to the fixture.
- `DENIED` means an operation intent exists and reached a durable terminal denial before any result content was staged.
- `DISCARDED` means content or names were actually staged/buffered for delivery and then destroyed because a later gate failed. Do not use it merely because an operation was denied.
- `UNRESOLVED` means the operation represented by the fixture has a durable intent whose outcome/handoff is not reconciled. It is not a generic synonym for a halted reader.

For a new operation rejected by an already unresolved earlier operation, the new attempt has no operation record: `expected_lifecycle_state=NONE`. Its `expected_internal_code=UNRESOLVED` and `expected_result_requester=REQUEST_DENIED`. Put the prior operation's `UNRESOLVED` state and the reader halt in `state_effects`. For a status query of that exact earlier operation, the lifecycle of the queried operation is `UNRESOLVED`.

Use these lifecycle results consistently:
- Rejection before intent commit: `NONE`.
- Intent committed and a gate denies before staging: `DENIED`.
- Content/names staged and a later gate denies: `DISCARDED`.
- Required durable outcome commit fails after intent, read, or staging: `UNRESOLVED` when that state is durably recoverable; halt new content-bearing operations and release no content.

In Entry 282 §2.1, the cap+1 list case has no staged names because count-first enumeration must not stage or disclose names. Its lifecycle is therefore `DENIED`, not `DISCARDED`. In any later fixture where names are deliberately staged and subsequently invalidated, `DISCARDED` applies.

## 4. W4 and W5 — Required status-query dependencies and all linked-decision states

A status query is a metadata-only read, never a content-read authorization. `STATUS_RETURNED` is permitted only after every mandatory record for that query has been retrieved and authenticated. Merely reading the operation record is not sufficient if the query also reports its linked decision status.

The mandatory dependencies for an exact status query are:
1. the authenticated requester principal/session and exact operation-key binding;
2. the authoritative operation record and its durable lifecycle state;
3. authoritative global ledger integrity/recovery state required by R2;
4. either the linked decision record, authenticated and schema-valid, or an authenticated tombstone that proves no linked decision record exists.

The query reports the stored operation state and the linked decision-record state. It does not promise that a decision is currently redeemable, does not return repository content, does not replay delivery, creates no intent/reservation, and does not resume a halted reader. If a dependency is unreadable or fails authentication, do not return a partial `STATUS_RETURNED` response.

Use the following complete cases for the linked decision:
- **Present, readable, valid record:** if all other status-query dependencies pass, return `STATUS_RETURNED` and the persisted operation/decision metadata.
- **Required read fails with I/O/unavailability:** public `REQUEST_DENIED`, internal `LEDGER_UNAVAILABLE`, decision status `UNAVAILABLE`. The operation's already persisted lifecycle may still be reported in the protected audit but not as a partial success to the requester. No content is released.
- **Present, readable, malformed or unauthenticated selected decision record:** public `REQUEST_DENIED`, internal `LEDGER_INTEGRITY_UNPROVEN`, decision status `SCHEMA_INVALID`, validator `DECISION_RECORD_SCHEMA_INVALID`; halt pending reconciliation. This status-query handling is for the operation's authenticated, bound dependency—not an arbitrary foreign ID probe.
- **Record absent and authenticated tombstone present:** decision status `NONE`. If the operation record is authenticated and terminal and all other required dependencies pass, the query returns `STATUS_RETURNED` with the terminal operation state and no content redelivery.
- **Record absent with no authenticated tombstone, or a tombstone that fails authentication:** public `REQUEST_DENIED`, internal `LEDGER_INTEGRITY_UNPROVEN`, decision status `MISSING_UNPROVEN`, and halt pending reconciliation.

Add `MISSING_UNPROVEN` to the field-scoped `expected_decision_status` enum. Its exact enum is:
`NONE`, `NOT_APPLICABLE`, `PENDING_VISIBILITY`, `ACTIVE`, `EXPIRED`, `REVOKED`, `UNAVAILABLE`, `SCHEMA_INVALID`, `MISSING_UNPROVEN`.
Do not use `NOT_APPLICABLE` to encode a missing, unreadable, malformed, or unauthenticated record. It is reserved for a field whose concept does not apply.

For an exact status query of an existing `UNRESOLVED` operation, if every mandatory dependency is readable/authenticated, return `STATUS_RETURNED` with operation lifecycle `UNRESOLVED`; keep the reader halted. If the linked decision dependency has an I/O error, the status query instead returns `REQUEST_DENIED` / `LEDGER_UNAVAILABLE` / decision status `UNAVAILABLE`. The second rule is an explicit dependency failure and supersedes any broad wording that could be read as unconditional success from operation-record readability alone.

## 5. W6 — Untrusted binding envelope for a request-selected decision

Keep the global ledger/anchor integrity check first, but separate it from request-selected validation of a single decision's binding envelope.

- A global ledger-chain, anchor, or durable-ledger authenticity failure independently detected by the mandatory global integrity gate returns `LEDGER_INTEGRITY_UNPROVEN` and halts reads, regardless of the selected decision ID.
- After requester authentication and global gates, if the supplied ID is unknown, if the decision is hidden before `not_before`, or if the selected decision's binding envelope cannot be authenticated on that request path, return public/internal `DECISION_NOT_APPLICABLE` with the same response shape. Set `expected_binding_result=BINDING_ENVELOPE_UNTRUSTED` for the envelope failure, record a protected anomaly, do not read content, and do not trigger a request-specific global halt.
- If a readable, authenticated binding envelope proves the selected decision is for a different principal/session/workspace/target, return `DECISION_NOT_APPLICABLE` with binding result `MISMATCH` and no halt.
- Only after a selected envelope is authenticated and matches the requester/target may the full decision payload schema be examined. A matching, present, readable but malformed decision payload gives `LEDGER_INTEGRITY_UNPROVEN`, public `REQUEST_DENIED`, validator `DECISION_RECORD_SCHEMA_INVALID`, status `SCHEMA_INVALID` and halt pending reconciliation.

A request-selected envelope failure and an independently detected global ledger-integrity failure are therefore different cases. The first is non-enumerating and non-halting for that request; the second is a global system-integrity failure. Do not validate the payload schema of a foreign decision before matching the independently authenticated binding envelope.

Add binding-envelope validator outcomes `BINDING_ENVELOPE_VALID` and `BINDING_ENVELOPE_INVALID` to the field-scoped `expected_validator_result` enum. Retain `expected_binding_result` as a separate enum containing `NOT_CHECKED`, `UNKNOWN_ID`, `MATCH`, `MISMATCH`, and `BINDING_ENVELOPE_UNTRUSTED`. `BINDING_ENVELOPE_UNTRUSTED` is not a primary R2 code and must not be written into `expected_internal_code`.

Discriminating fixtures:
- Unknown ID versus hidden-before-`not_before` ID: same public result and observation shape, no halt.
- Unknown ID versus selected record whose request-specific binding envelope fails authentication: same public result and observation shape, no content I/O and no request-specific halt; audit validator differs.
- Selected record with authenticated foreign binding: same public result, binding result `MISMATCH`, no payload-schema inspection.
- Own bound decision whose readable payload omits a mandatory cap: `LEDGER_INTEGRITY_UNPROVEN`, public `REQUEST_DENIED`, schema-invalid status, reader halted.

## 6. W8 — Phase-aware R2 precedence and operation transaction ordering

The ordered R2 taxonomy remains the set of internal selections, but “first applicable” is phase-aware. A later-phase gate is not observable and must not be selected before the operation reaches that phase. This explicit rule supersedes any reading of Entry 280's R2 table as requiring a gate that needs an open/staged object to be evaluated before reservation.

Use this mandatory phase sequence:

1. **Global health/recovery:** validate required ledger availability, independent integrity/anchor evidence, unresolved recovery state, and anti-rollback epochs. A failure here stops the request before request-specific payload parsing or content I/O.
2. **Authenticated request and preflight:** authenticate requester; validate operation/decision binding using §5; validate accepted lexical form; establish safe root/request-target scope; evaluate policy/block scope and supported release; evaluate decision/approval freshness and authoritative revocation as required. Select the first failed eligible preflight gate using R2 order among gates actually observable in this phase.
3. **Atomic reservation/intent commit:** only after all non-I/O preflight gates pass, atomically commit operation key, operation ID, canonical argument digest, `INTENT_COMMITTED`, aggregate deliverable/call reservation, and one operation-local probe allowance. If reservation fails, return `BUDGET_EXCEEDED` before opening or reading the content object. No intent, operation record, reservation or probe use is created.
4. **Opened-object/containment gate:** open using the pinned root/authorized handle semantics, then verify that the actual opened object matches the approved binding and containment. This is the first phase at which an open-time replacement can establish `CONTAINMENT_UNPROVEN`. Do not read content before that check passes.
5. **Bounded operation phase:** file read or count-first listing. File/list ceilings are established by at most one cap+1 probe. For listing, the specific exception in Entry 282 §2.1 remains: after safe binding of the directory itself and a committed reservation, count actual entries before per-entry validation; overflow gives `LIST_LIMIT_EXCEEDED` even if an individual entry is unsafe, and count-first enumeration does not stage names.
6. **Final gate:** after staging, recheck current ledger/integrity/recovery, protected epochs, requester/session/decision binding, actual object containment, block scope/release, expiry, revocation, and the already committed reservation before any release. If one or more final-gate failures are observed, select by the normative R2 priority among the failures observable at this final gate. Do not reserve twice. No content is released unless the final gate and durable completion commit pass.

The next consolidated R2 table must add a `phase` column for every row and explicitly identify which gates are preflight, opened-object, bounded-operation, or final-gate checks. It must also retain the canonical R2 number/meaning. A later-phase failure does not supersede a preflight failure that prevented the later phase from running.

### Required V9 conflict case

Given a valid, unexpired decision, exhausted aggregate budget, and a pathname that was approved earlier but was replaced by an outside-root link before open:
- reservation fails in phase 3;
- result is internal `BUDGET_EXCEEDED`, public `REQUEST_DENIED`;
- there is no open/content I/O and no containment result may be inferred;
- no operation intent, operation ID, reservation, probe attempt, or lifecycle record is created for that failed atomic transaction;
- lifecycle for this attempted operation is `NONE`; any prior approval/binding facts remain protected audit metadata.
Do not return `CONTAINMENT_UNPROVEN` because phase 4 was never reached.

If reservation succeeds and the actual opened object then fails containment, the result is internal `CONTAINMENT_UNPROVEN`, public `REQUEST_UNAVAILABLE`, reservation remains charged, no content is released, and lifecycle is `DENIED` when nothing was staged or `DISCARDED` if a staged result is destroyed. This explicitly resolves the phase-dependent result difference without violating the fixed R2 priority within a phase.

## 7. W10 — Manifest parser must detect malformed row-like ID candidates

Keep the single contiguous authoritative manifest-table requirement. Preserve prose citations as prose; do not classify a normal sentence containing an ID as an orphan row.

Define a **row-like ID candidate** as a physical Markdown line whose first non-whitespace character is `|` and whose first cell contains any recognizable qualified-ID core, even if malformed by status suffix, wrong case, surrounding backticks, or attached annotation. Candidate detection is deliberately broader than the normalized accepted ID grammar.

For candidate detection only, recognize the base pattern `[0-9]{3}-[Aa][0-9]+[a-zA-Z]?` as a substring of the trimmed first cell after stripping Markdown code delimiters for detection, not for acceptance. If such a candidate occurs in a pipe row outside the sole manifest table, the artifact is invalid. If it occurs inside the table but is not exactly the normalized ID syntax or otherwise violates the schema, the row is invalid. Do not silently ignore malformed candidates because they fail the strict accepted-ID regex.

The normalized accepted ID remains exactly `^[0-9]{3}-A[0-9]+[a-z]?$$$$`, with separate status `ACTIVE` or `RETIRED`; remove the duplicated dollar-sign typo if any source copy contains it, so the operative regex is `^[0-9]{3}-A[0-9]+[a-z]?$$`. The parser must not use the broad candidate regex as the accepted-ID regex.

Required parser behavior:
- Prose “see `278-A17a`” on a non-pipe line: not a row-like candidate, does not increase row count.
- Pipe row outside the manifest with first cell `278-A17a`: orphan row, `MANIFEST_INVALID`.
- Pipe row outside the manifest with first cell `278-A17a [RETIRED]`: malformed orphan, `MANIFEST_INVALID`.
- Pipe row outside the manifest with first cell `278-a17a` or code-delimited `278-A17a`: malformed orphan, `MANIFEST_INVALID`.
- A valid normalized row inside the sole manifest counts exactly once and has a separate status field.
- A valid table plus any malformed/orphan row above: `MANIFEST_INVALID`.

This rule preserves the intended no-false-positive behavior for prose while rejecting malformed pipe rows that could otherwise evade the artifact-wide orphan check.

## 8. W9 — Typed observer channels, stages, observation sequences, and state effects

In addition to the existing field-scoped enums, make these fields mechanically parseable:

### 8.1 `evaluation_stage` enum

The only accepted values are:
`REQUEST_ENVELOPE`, `PATH_GRAMMAR`, `APPROVAL_WINDOW`, `ISSUANCE`, `GLOBAL_HEALTH`, `DECISION_BINDING`, `OPERATION_PREFLIGHT`, `RESERVATION_COMMIT`, `OPEN_CONTAINMENT`, `BOUNDED_FILE_READ`, `LIST_COUNT`, `FINAL_GATE`, `STATUS_QUERY`, `RECOVERY`, `MANIFEST_VALIDATION`.

### 8.2 Owner-channel observer

Add `expected_result_owner_channel` with this enum:
`NOT_APPLICABLE`, `OWNER_PROMPT_SHOWN`, `OWNER_APPROVAL_ACCEPTED`, `OWNER_REJECTION_RECORDED`, `OWNER_NO_RESPONSE`, `OWNER_ATTESTATION_LATE`, `OWNER_ATTESTATION_STALE`, `OWNER_ATTESTATION_INVALID`, `ISSUANCE_WRITE_FAILED`, `ISSUANCE_DEADLINE_MISSED`.

This field describes only the trusted Owner/issuer/audit observer, not the requester. It must never be reflected in requester output or requester-observation comparisons. For requester-only probes with no Owner-channel event, use `NOT_APPLICABLE`. For a rejected/absent/late Owner choice, record the matching distinct token; do not collapse them into requester-visible data.

### 8.3 Observation-sequence grammar

Define the permitted observation tokens as:
`REQUEST_RESULT`, `REQUEST_TIMING_CLASS`, `RESPONSE_BODY_SHAPE`, `CONTENT_BYTES`, `ENTRY_NAMES`, `STATUS_FIELDS`, `OWNER_CHANNEL_RESULT`, `PROTECTED_AUDIT_RESULT`, `READER_HALT_STATE`.

The field `expected_observation_sequence` must be an ordered, duplicate-free sequence of these tokens written with `>` as delimiter. Blank, free-text, slash-separated alternatives, “A or B”, unknown tokens, duplicate tokens, or an undeclared comparison rule make the manifest invalid. The owner-channel token is visible only to the trusted Owner-side observer; it cannot be inserted into a requester equivalence group.

### 8.4 State-effects grammar

Define `state_effects` as a complete set of key-value pairs in this exact key order:
`operation_record`, `operation_lifecycle`, `reader_state`, `reservation`, `probe_attempts_used`, `content_state`, `decision_record`, `owner_channel`.

Allowed value vocabularies:
- `operation_record`: `NONE`, `COMMITTED`, `TERMINAL`, `UNRESOLVED`.
- `operation_lifecycle`: values of the lifecycle enum in §3.2.
- `reader_state`: `AVAILABLE`, `HALTED`.
- `reservation`: `NONE`, `COMMITTED_RETAINED`.
- `probe_attempts_used`: `0`, `1`.
- `content_state`: `NONE`, `STAGED`, `RELEASED`, `DISCARDED`.
- `decision_record`: `NONE`, `HIDDEN`, `ACTIVE`, `EXPIRED`, `REVOKED`, `UNAVAILABLE`, `SCHEMA_INVALID`, `MISSING_UNPROVEN`.
- `owner_channel`: values of `expected_result_owner_channel`.

Each field must appear exactly once and no additional prose may be embedded in the structured value. Any state effect not representable by this schema requires a reviewed schema amendment, not free-text improvisation.

### 8.5 Field-scoped validation

Extend `expected_validator_result` with `BINDING_ENVELOPE_VALID` and `BINDING_ENVELOPE_INVALID`. Keep validator results separate from requester outputs, internal R2 selections, decision status, issuance status, and lifecycle state.

Discriminating invalid rows:
- `evaluation_stage=BANANA` → `MANIFEST_INVALID`.
- `expected_result_requester=UNRESOLVED` → `MANIFEST_INVALID`.
- `expected_internal_code=BINDING_ENVELOPE_UNTRUSTED` → `MANIFEST_INVALID`.
- a requester-only fixture whose `state_effects.owner_channel` is `OWNER_REJECTION_RECORDED` but has no Owner-channel observer → invalid by fixture cross-check.
- duplicate or free-text observation-sequence tokens → `MANIFEST_INVALID`.

Discriminating valid rows include a blocked new operation with requester result `REQUEST_DENIED`, internal `UNRESOLVED`, lifecycle `NONE` for the rejected attempt, and state effects recording the earlier unresolved operation and `reader_state=HALTED`; and a status query of that earlier operation with requester result `STATUS_RETURNED` and lifecycle `UNRESOLVED`.

## 9. Required W1–W11 discriminating cases

The next consolidated manifest must include independent, fixed fixtures for each of the following. These are test requirements, not evidence of runtime behavior.

- **W1:** timely approval + unbindable target; late approval; freshness expired before issuance; durable decision write failure; ledger write completing exactly at the deadline. Each has a distinct issuance/internal result.
- **W2:** field validator accepts public `expected_result_requester=DECISION_EXPIRED` and rejects internal-only `expected_result_requester=LEDGER_UNAVAILABLE`; accepts public `expected_result_requester=DECISION_NOT_APPLICABLE`; rejects `expected_result_requester=UNRESOLVED`.
- **W3:** a new operation blocked by a prior unresolved operation has no new lifecycle record (lifecycle `NONE`); status query of the exact prior unresolved operation returns its lifecycle `UNRESOLVED`.
- **W4:** status query where the operation record is readable but the required linked decision record read fails; public `REQUEST_DENIED` / internal `LEDGER_UNAVAILABLE` / decision status `UNAVAILABLE`, no partial success.
- **W5:** separately test valid linked record, linked record read error, malformed linked record, authenticated tombstone, and absent record without authenticated tombstone; each maps to the exact tuple defined in §4.
- **W6:** unknown ID, hidden-before-`not_before` ID, selected binding envelope failing authentication, authenticated foreign binding, and own bound malformed payload; compare output shape and halt effects.
- **W7:** denial before staging → lifecycle `DENIED`; denial after staging → `DISCARDED`; uncommitted/failed atomic reservation → lifecycle `NONE`; unresolved durable intent → lifecycle `UNRESOLVED`.
- **W8:** exhausted budget + replaced object must return `BUDGET_EXCEEDED` before open; successful reservation + replacement is allowed to reach `CONTAINMENT_UNPROVEN`. Force the phase boundary and prove no open/content I/O occurred in the first case.
- **W9:** `evaluation_stage=BANANA` rejected, owner-channel result separately typed, and state-effects/observation sequences parsed mechanically.
- **W10:** valid prose citation accepted; strict valid ID table accepted; pipe-row orphan with uppercase, lowercase, status suffix, and backticks rejected.
- **W11:** hidden decision before `not_before` equals unknown ID; unsupported lexical path is rejected before `T0`; lexically valid missing path follows the fixed approval window; the original accepted request remains `APPROVAL_PENDING` until its fixed endpoint.

## 10. Residual acceptance blockers remain open

The following must remain explicit acceptance blockers and are not closed by this amendment:

- **S5 — Composite fixtures and lexical/race/crash boundaries:** split every remaining compound setup; enumerate every rejected lexical class; cover every crash boundary; test root/path replacement, an in-place concurrent writer, and valid sensitive-name pre-approval; verify retired tests have adequate replacements.
- **S9 — Trusted delivery acknowledgement:** define an acknowledgement authority outside requester control and bind it to operation ID, recipient and response digest; specify crash recovery for no-ack transport and trusted-ack modes; define the transition rule for `DELIVERY_ACKNOWLEDGED` versus `DELIVERED`.
- **S10 — Precedence and temporal-boundary mutation coverage:** enumerate adjacent-gate/final-gate precedence pairs; test each relevant deadline at T−ε, T and T+ε; test final-gate `DECISION_REVOKED` with staged content; ensure a deny-all mutant fails. Specifically cover challenge deadline, Owner-attestation freshness, fixed endpoint, decision expiry and authoritative revocation freshness. Stating the deadlines in this delta does not close the test-coverage requirement.

## 11. Acceptance, evidence, and next actor

This is a proposed delta and not a contract acceptance. A targeted review may return `PASS` only if W1–W11 have one unambiguous rule each, no field uses a token outside its field-scoped enum, each state reflects the lifecycle of the operation represented by the row, the phase-gated R2 order is deterministic, and every discriminating fixture can fail against the competing behavior. Any conflict in public result, internal selection, lifecycle, phase, observability, or effect is `FAIL`. If only bounded local defects remain, return `PASS_WITH_REPAIRS` with their exact clauses and one discriminating test each.

Evidence classifications:
- `PROVEN_BY_SOURCE`: current public Entry 280, Entry 281, and Entry 282 content plus blob identities fetched by the coordinator.
- `OWNER_REPORTED`: the supplied Claude C9 review narrative, sandbox-clone HEAD/hash report, and earlier local M0A reports.
- `PROPOSED`: every repair and fixture requirement in this Entry 283.
- `UNPROVEN`: historical fidelity to all original Entry 274–277 blobs unless individually compared; every runtime/platform claim; local M0A identity/state; actual anti-rollback enforcement; containment; Owner/requester isolation; revocation freshness; trusted delivery acknowledgement; and production block-scope/release behavior.

**Next actor: Claude/Sonnet.** Perform one targeted delta review of Entry 280's relevant parent clauses, Entry 281 where supersession context is necessary, Entry 282, and Entry 283. Return exactly one `PASS`, `PASS_WITH_REPAIRS`, or `FAIL` for W1–W11. Do not perform broad source archaeology; do not attempt to close S5/S9/S10. The owner is not the review executor for this stage.

No implementation, source/config change beyond this documentary entry, builds/tests/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update, launch, or canonical-route rewrite is authorized. This entry cannot grant repository-read authority or release a governance block. `KEEP_BLOCKED`.
