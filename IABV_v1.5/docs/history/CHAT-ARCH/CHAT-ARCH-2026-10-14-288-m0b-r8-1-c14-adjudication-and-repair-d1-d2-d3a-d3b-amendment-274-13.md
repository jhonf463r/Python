# CHAT-ARCH-2026-10-14-288 — C14 adjudication and bounded D1/D2/D3a/D3b repair (amendment 274.13)

- Status: `M0B_R8_1_AMENDMENT_274_13_PROPOSED_PENDING_C15_REVIEW`
- Parent: Entry 287 / amendment 274.12.
- C14 verdict: `PASS_WITH_REPAIRS` (`OWNER_REPORTED` review outcome).
- Operational posture: `KEEP_BLOCKED`.
- Scope: ten local textual-defect groups from C14, restricted to D1, D2, D3a, D3b, and the D1/D2 fixture mechanics. R1–R4 are not reopened.

## 0. Provenance and scope boundary

The current public source files were fetched through the connected GitHub contents route before drafting. Their verified blob IDs are:

- Entry 282: `0fa5cc1cb8f63c05c7309ec7dcb98966d738ecf3`.
- Entry 283: `a9fcd0ca56c01d9118504aa77274b6737a3961c7`.
- Entry 285: `778afe7ebd883e68681f066c2f5f75f30983c633`.
- Entry 286: `912a9c0b156b17317f611007dc6711296b84e4c9`.
- Entry 287: `19d2937ee0e95e77a7401c73a81b09df18c361db`.

Those current public source identities and contents are `PROVEN_BY_SOURCE`. C14's review findings and its report that all five supplied blob identities match current `main` are `OWNER_REPORTED`; the current source fetch independently confirms the same identities. All rules and fixtures proposed below are `PROPOSED`. Runtime behavior, atomic durability, crash behavior, clock enforcement, filesystem behavior, and delivery transport remain `UNPROVEN`.

This entry supersedes only the four C13 repair areas in Entry 287 and the associated fixture mechanics. It does not establish final contract acceptance, runtime proof, implementation authority, local M0A state, or launch permission. S5, S9, and S10 remain open. `KEEP_BLOCKED`.

## 1. C14-D1-1 — Exhaustive, ordered acknowledgement-status classification

### 1.1 Scope and precedence

The `expected_delivery_ack_status` field describes acknowledgement/delivery evidence; `expected_internal_code` separately reports the applicable internal R2/recovery result. An internal `LEDGER_UNAVAILABLE` or `LEDGER_INTEGRITY_UNPROVEN` result is not inserted into the acknowledgement-status enum. The two fields must not be conflated.

This classifier applies when evaluating a trusted-ack operation under Entry 285 §2.2. Existing `ACK_INVALID`, `ACK_MISMATCH`, and `ACK_REPLAYED` handling remains unchanged. For a valid acknowledgement and its commit/recovery state, evaluate these rules in order; the first satisfied rule selects exactly one `expected_delivery_ack_status`:

1. **`ACK_ACCEPTED`:** authenticated receipt evidence and authoritative, integrity-verified ledger evidence prove that the acknowledgement and lifecycle `DELIVERED` were atomically committed durably, with receipt time strictly before commit time and commit time strictly before `Tack`. A successful acknowledgement commit is never valid at or after `Tack`.
2. **`ACK_TIMED_OUT` from independently sufficient late evidence:** a valid, correctly bound authenticated receipt event is timestamped at or after `Tack`; or a complete trusted journal proves that the acknowledgement/DELIVERED transaction was rejected by the strict deadline predicate at or after `Tack`. A late authenticated receipt is sufficient to select `ACK_TIMED_OUT` even if the commit-outcome source is subsequently unavailable. If an alleged durable success row contradicts the strict deadline, preserve the timeout classification for the acknowledgement field and separately select the applicable ledger-integrity internal result.
3. **`ACK_TIMED_OUT` from a proved missing acknowledgement:** there is no valid durable acknowledgement/DELIVERED commit by `Tack`; trusted evaluation time is at or after `Tack`; and both the configured acknowledgement authority and the complete authoritative commit journal have been successfully queried and prove that no valid acknowledgement was received/committed by the deadline. If no receipt exists and the deadline has not been reached, use `WAITING` instead.
4. **`ACK_COMMIT_FAILED`:** a valid authenticated receipt event is strictly before `Tack`; trusted and complete recovery evidence proves the acknowledgement/DELIVERED transaction is not durable; and the complete authoritative attempt journal proves either a rollback before `Tack` or that no commit attempt began before the crash. The journal also proves no attempt was made or accepted at/after `Tack`. A missing/incomplete journal is not proof of no attempt.
5. **`WAITING`:** trusted evaluation time is strictly before `Tack`, no valid receipt or successful commit is present, and the required acknowledgement authority and authoritative journal are queryable and complete.
6. **`ACK_SOURCE_UNAVAILABLE`:** none of rules 1–5 can be proved because the acknowledgement source, commit journal, or commit outcome is unavailable, incomplete, or untrustworthy. This does not suppress a higher-priority internal ledger result; record that result in `expected_internal_code` while keeping the acknowledgement field typed as `ACK_SOURCE_UNAVAILABLE`.

A late authenticated receipt is not downgraded to `ACK_SOURCE_UNAVAILABLE` merely because the commit-outcome source is unavailable. Conversely, absence of a receipt or attempt record is not proof of absence unless the trusted source is available and its completeness/watermark is established.

### 1.2 Journal completeness and no post-deadline commit retries

The trusted commit coordinator MUST enforce the strict predicate `trusted_commit_time < Tack` at the atomic transaction's commit-decision point. The atomic transaction may not persist acknowledgement evidence or lifecycle `DELIVERED` at or after `Tack`. An attempt evaluated exactly at `Tack` is rejected before any successful acknowledgement/DELIVERED state transition; a protected deadline-rejection audit event may record that rejection without claiming receipt commitment or delivery.

Every permitted acknowledgement commit attempt MUST have an authoritative journal entry registered before transaction execution, and its completion or rejection must be reflected in the authoritative attempt history. An incomplete or unavailable history yields `ACK_SOURCE_UNAVAILABLE` unless a stronger ledger-integrity result is selected. A supposedly complete journal that omits an attempt known to have occurred is an integrity defect, not evidence that no attempt occurred.

Recovery MUST NOT retry or initiate the acknowledgement/DELIVERED transaction at or after `Tack`. Recovery may query existing evidence and reconcile state, but may not create new post-deadline transaction attempts. This prevents recovery behavior from changing a pre-crash outcome classification.

If the authoritative ledger contains an acknowledgement/DELIVERED success record with commit time at or after `Tack`, that record violates the strict commit predicate: select internal `LEDGER_INTEGRITY_UNPROVEN`, halt the reader for new content-bearing operations, do not trust the record as a valid `ACK_ACCEPTED` delivery, and do not replay content.

### 1.3 Renumbered D1 fixtures and exact expected statuses

The malformed prose-only fixture labels in Entry 287 are superseded by these schema-valid `qualified_id` values:

- `287-A48` — rollback proved before deadline. A valid receipt occurs at `Tack−10ms`; the authoritative journal proves rollback at `Tack−5ms`, no later attempt, and complete history. Expected `ACK_COMMIT_FAILED`, internal/lifecycle recovery `UNRESOLVED`, reader `HALTED`, reservation `COMMITTED_RETAINED`, no replay.
- `287-A49` — deadline predicate rejects the boundary attempt. The valid receipt occurs at `Tack−10ms`; an attempt is evaluated exactly at `Tack` and rejected before any acknowledgement or `DELIVERED` state row is committed. Expected `ACK_TIMED_OUT`, `UNRESOLVED`, `HALTED`, `COMMITTED_RETAINED`, no replay.
- `287-A50` — crash before any attempt. The valid receipt occurs at `Tack−10ms`; the process crashes before invoking the commit coordinator; recovery occurs at `Tack+60s`; a successful complete journal/watermark proves that no attempt began and no commit exists. Expected `ACK_COMMIT_FAILED`, `UNRESOLVED`, `HALTED`, `COMMITTED_RETAINED`, no replay. Recovery performs zero acknowledgement/DELIVERED writes.
- `287-A53` — persisted-success integrity guard. Seed a purported acknowledgement/`DELIVERED` success record with commit time exactly `Tack`. Expected internal `LEDGER_INTEGRITY_UNPROVEN`, requester `REQUEST_DENIED` for a halted new content-bearing request, reader `HALTED`, no trusted delivery claim or replay. The record is not accepted as a valid successful commit.

For the C14 gap controls, add these exact discriminators:
- No receipt, both trusted sources available and complete at `Tack+1ms` → `ACK_TIMED_OUT`; the same setup at `Tack−1ms` → `WAITING`.
- A valid receipt event at `Tack+5ms` with the commit-outcome source unavailable → `ACK_TIMED_OUT`, not `ACK_SOURCE_UNAVAILABLE`; the validator rejects the alternate acknowledgement status for that setup.
- A source-unavailable pre-deadline receipt/commit state without independent late evidence → `ACK_SOURCE_UNAVAILABLE`, not `ACK_COMMIT_FAILED`.
- A complete journal proving no attempt for A50 → `ACK_COMMIT_FAILED`; an unavailable/incomplete journal for the same apparent pre-crash state → `ACK_SOURCE_UNAVAILABLE`. A test must assert zero post-`Tack` writes by the recovery process.

Worlds with a late transaction rejection that left no authoritative journal evidence are not valid `ACK_COMMIT_FAILED` fixtures. Under this proposal, every attempt is journaled before execution; if the history is incomplete or contradicts observed evidence, do not infer a timeout or a commit failure from absence alone. Return the applicable unavailable/integrity outcome.

## 2. C14-D1-2 — Make the `Tack` equality case an aborted attempt, not a successful atomic commit

Amend the Entry 287 A49 discriminator and the strict predicate in §1.2 above. The phrase “commit linearizes exactly at `Tack`” must not mean that an atomic acknowledgement/`DELIVERED` commit succeeds at that instant.

At exactly `Tack`, the commit-decision predicate evaluates false and the acknowledgement/DELIVERED transaction aborts before writing either success row. Only the non-successful deadline-rejection event may be recorded. The result is `ACK_TIMED_OUT` / `UNRESOLVED`, with reservation retained, reader halted, no replay, and no delivery claim.

Discriminating test: inject the trusted clock at `Tack` during commit-decision evaluation and assert that no acknowledgement success row and no `DELIVERED` lifecycle row exist afterward; recovery yields `ACK_TIMED_OUT` / `UNRESOLVED`. Separately seed a purported durable success row whose commit timestamp is `Tack`; the integrity guard `287-A53` must select `LEDGER_INTEGRITY_UNPROVEN`, not trust the row or treat it as successful delivery.

## 3. C14-D1-3 — Make “no attempt before crash” provable without absence-of-evidence inference

A50's “no attempt” setup is valid only when the complete trusted attempt history/watermark positively establishes that no attempt was invoked before the crash. An empty result from an unavailable, truncated, or non-authoritative journal is not enough.

The coordinator MUST register each attempt durably in the authoritative attempt journal before transaction execution. Recovery MUST NOT call the commit path after `Tack`. Therefore:
- complete journal proving no attempt + known pre-deadline authenticated receipt + no durable commit → `ACK_COMMIT_FAILED`;
- journal showing an attempt with a deadline rejection → `ACK_TIMED_OUT`;
- incomplete/unknown history or unknowable commit outcome → `ACK_SOURCE_UNAVAILABLE`, or `LEDGER_INTEGRITY_UNPROVEN` if the supposedly complete authoritative history is proven inconsistent.

This distinction avoids classifying two observationally indistinguishable durable states differently. It also prohibits a recovery-generated deadline rejection from changing A50's result. The required discriminating test uses a counting ledger-writer stub and asserts zero post-`Tack` commit attempts during recovery.

## 4. C14-D2-1 — Derive `gate_phase` from the existing `evaluation_stage`

### 4.1 Phase derivation

Do not allow `gate_phase` and Entry 283 §8.1's `evaluation_stage` to vary independently. Add the following derived field `gate_phase` enum:
`ISSUANCE`, `PREFLIGHT`, `FINAL_GATE`, `NOT_APPLICABLE`.

The only valid derivation is:

| `evaluation_stage` | Required `gate_phase` |
|---|---|
| `APPROVAL_WINDOW`, `ISSUANCE` | `ISSUANCE` |
| `DECISION_BINDING`, `OPERATION_PREFLIGHT` | `PREFLIGHT` |
| `FINAL_GATE` | `FINAL_GATE` |
| Every other allowed `evaluation_stage` value in Entry 283 §8.1 | `NOT_APPLICABLE` |

The manifest validator MUST reject any inconsistent pair with `MANIFEST_INVALID` and diagnostic `PHASE_STAGE_MISMATCH`. For example, `evaluation_stage=FINAL_GATE` with `gate_phase=PREFLIGHT` is invalid.

### 4.2 Full mapping key and unchanged mappings

For `expected_internal_code=DECISION_EXPIRED`, apply the phase-aware requester mapping below after Entry 282's fixed approval-window override:

| `gate_phase` | Condition | Required `expected_result_requester` |
|---|---|---|
| `ISSUANCE` | Before the fixed visibility endpoint, while the uniform window remains open | `APPROVAL_PENDING` under the fixed-window override |
| `ISSUANCE` | At/after the endpoint, with no eligible usable decision durably issued | `REQUEST_UNAVAILABLE` |
| `PREFLIGHT` | New operation presented with an already-expired bound decision before intent/staging/content I/O | `DECISION_EXPIRED` |
| `FINAL_GATE` | Previously admitted operation, content staged, expiry selected at final gate | `REQUEST_DENIED` |

Every `DECISION_EXPIRED` fixture MUST declare both `evaluation_stage` and the derived `gate_phase`. No fixture may omit the phase or use an output belonging to another phase. For internal codes other than `DECISION_EXPIRED`, retain Entry 282 §4.2's field-specific requester mapping; `gate_phase` does not redefine those mappings.

If `evaluation_stage` and `gate_phase` agree but the public requester result violates the phase-specific mapping, the validator MUST emit `MANIFEST_INVALID` with diagnostic `PHASE_RESULT_MISMATCH`. Diagnostics are validation details, not requester-visible output.

### 4.3 Renumbered discriminating D2 fixtures

- `287-A51` (formerly the prose label D2-P): `evaluation_stage=OPERATION_PREFLIGHT`, `gate_phase=PREFLIGHT`; a bound decision is already expired at admission; there is no intent, staging, content I/O, or reservation. Expected internal `DECISION_EXPIRED`, requester `DECISION_EXPIRED`, decision status `EXPIRED`, lifecycle `NONE`, reservation `NONE`, reader `AVAILABLE`.
- `287-A52` (formerly the prose label D2-F): `evaluation_stage=FINAL_GATE`, `gate_phase=FINAL_GATE`; the admitted operation has staged content, the clock is exactly at `Texp`, and a fresh authenticated revocation proof independently establishes revocation at the same instant. Expected internal `DECISION_EXPIRED`, requester `REQUEST_DENIED`, decision status `EXPIRED`, lifecycle `DISCARDED`, reservation `COMMITTED_RETAINED`, content state `DISCARDED`, reader `AVAILABLE`, zero bytes released and no handoff.

A51 and A52 deliberately share the internal code but have different stages/phases. The validator must reject `REQUEST_DENIED` for A51 and `DECISION_EXPIRED` for A52 with `PHASE_RESULT_MISMATCH`. Entry 282's quoted mapping and fixed-window override remain unchanged.

## 5. C14-D3a-1 — Machine-enforce replacement completeness and uniqueness

Replace Entry 287 §3.1's required set with this nine-ID set:

| Retired ID | Normative `required_replacement_ids` |
|---|---|
| `278-A56a` | `{285-A39, 285-A40, 285-A41, 285-A42, 285-A43, 287-A44, 287-A45, 287-A46, 287-A47}` |

A required replacement is covered only if its exact `qualified_id` occurs exactly once in the sole authoritative manifest, has `status=ACTIVE`, and explicitly links `supersedes_retired_ids=278-A56a`. All nine required IDs must be present. Additional linked active IDs are allowed, but they cannot substitute for any required ID. Each extra ID must still be unique, well-formed, active, and traceable; this coverage rule does not certify that its setup or oracle is behaviorally correct.

If any required ID is absent, renamed, duplicated, retired, or lacks the retired-ID linkage, the coverage validator MUST return `MANIFEST_INVALID` with diagnostic `REPLACEMENT_COVERAGE_INCOMPLETE`. The diagnostic remains required even if a generic duplicate-ID or schema diagnostic is also emitted. Row counts, prose, a nonempty replacement list, and an unparsed declaration cannot substitute for the structural cross-check.

### 5.1 Required structural mutation matrix

For each of the nine required IDs, the tests must independently:
1. remove that ID;
2. retain the ID but remove its `278-A56a` linkage;
3. mark the required row `RETIRED`;
4. duplicate the required `qualified_id`; and
5. rename the required ID while leaving the replacement declaration unchanged.

Every mutation must cause `MANIFEST_INVALID / REPLACEMENT_COVERAGE_INCOMPLETE`. This is 45 independent negative mutations in addition to the all-nine-present positive control. A43, for example, must fail when present with `supersedes_retired_ids=NONE`, when retired, when duplicated, or when renamed. This amendment does not close the other multi-replacement mappings in Entry 285 §1.6; S5 stays open.

## 6. C14-D3b-1 — Correct A45's internal result without misusing `REGISTRY_ROLLBACK`

Entry 282 §7 reserves `REGISTRY_ROLLBACK` for the authenticated anchor/store epoch-regression category. A failure to persist a terminal `DISCARDED` outcome is not, by itself, an epoch rollback.

Replace Entry 287 A45's setup and tuple as follows: a backward wall-clock step invalidates the active decision at the final gate after content staging; the terminal-denial/discard transaction then fails as a separately injected operation-local outcome-recording failure, while global ledger health is available and authoritative anchor/store epochs remain consistent. The setup asserts no epoch regression and no registry rollback.

Expected: primary cause/internal code `DECISION_EXPIRED`; requester `REQUEST_DENIED`; decision status `EXPIRED`; lifecycle and operation record `UNRESOLVED`; reader `HALTED`; reservation `COMMITTED_RETAINED`; durable content state remains `STAGED` (not durably `DISCARDED`); no bytes released, no handoff and no replay. The unresolved state reflects the failed durable outcome recording; it does not replace the expiry cause with an unrelated R2 code.

Discriminating test: run the exact A45 setup with consistent anchor/store epochs and assert that `REGISTRY_ROLLBACK` is rejected. If epoch regression is also tested, it must be a separate fixture with explicit anchor and store epoch values; do not compound it with A45.

## 7. C14-D3b-2 — Fix issuance outcome fields and distinguish a late attestation from no response

Entry 282 §4.1 makes `expected_issuance_result` mandatory, and Entry 283 §2.1 distinguishes `APPROVAL_LATE` from `OWNER_NO_RESPONSE`. A46 must not leave those outcomes interchangeable.

Replace A46's setup with: suspend semantics become unknown, which invalidates the pending nonce; an attestation is subsequently received after that invalidation and is therefore late relative to the nonce's effective validity window. At the fixed visibility endpoint, no eligible decision exists.

Required values: `evaluation_stage=ISSUANCE`, `gate_phase=ISSUANCE`, `expected_internal_code=DECISION_EXPIRED`, `expected_result_requester=REQUEST_UNAVAILABLE` at the endpoint, `expected_decision_status=NONE`, `expected_issuance_result=APPROVAL_LATE`, `expected_result_owner_channel=OWNER_ATTESTATION_LATE`, lifecycle `NOT_APPLICABLE`, reservation `NONE`, reader `AVAILABLE`, and no content/intent/handoff. This uses `APPROVAL_LATE` only because an attestation did arrive after its nonce had been invalidated; a nonce with no attestation remains `OWNER_NO_RESPONSE` / internal `NONE`, and is not this fixture.

The strict challenge deadline and clock-safety nonce invalidation are distinct invalidation triggers. Once either invalidates the nonce, a later attestation cannot revive it or issue a decision. The fixed-window requester override remains `APPROVAL_PENDING` before the endpoint.

## 8. C14-D3b-3 — Restore backward-step coverage for pending nonces

Add the independent fixture `287-A47`, with `supersedes_retired_ids=278-A56a`: a detected backward wall-clock step invalidates a pending nonce, and an attestation is subsequently presented using that invalidated nonce. This is an `ISSUANCE` fixture distinct from A43's active-decision final-gate case and A44's expired-decision preflight case.

Expected at the fixed visibility endpoint: `expected_internal_code=DECISION_EXPIRED`; `expected_result_requester=REQUEST_UNAVAILABLE`; `expected_decision_status=NONE`; `expected_issuance_result=APPROVAL_LATE`; `expected_result_owner_channel=OWNER_ATTESTATION_LATE`; lifecycle `NOT_APPLICABLE`; reservation `NONE`; operation record `NONE`; reader `AVAILABLE`; no issued decision, intent, content I/O, handoff, or replay. Before the fixed endpoint, `APPROVAL_PENDING` remains the requester-visible override.

The manifest must reject an implementation that expires active decisions after a backward step but leaves a pending nonce eligible. A47 is the required discriminator for that mutation. The `required_replacement_ids` declaration in §5 includes A47.

## 9. C14-D3b-4 — Field-complete clock-fixture tuples

Replace Entry 287 §4.1's eight-row table with the following nine fixed fixture tuples. The table is a normative fixture specification, not a claim that the final consolidated single-table manifest has already been produced. Each row fixes every outcome field required by Entry 282 §4.1 and Entry 283 §§8.2–8.4, plus the S9 delivery-ack fields from Entry 285. The `gate_phase` must equal the derivation from `evaluation_stage` in §4.1 above. `state_effects` follows Entry 283 §8.4's exact key order and contains no prose or alternate values.

| qualified_id | status | setup | probe_request | evaluation_stage | gate_phase | expected_result_requester | expected_internal_code | expected_binding_result | expected_decision_status | expected_lifecycle_state | expected_issuance_result | expected_validator_result | expected_result_owner_channel | expected_observation_sequence | equivalence_group | state_effects | classification | oracle_type | supersedes_retired_ids | transport_ack_capability | expected_delivery_ack_status | traceability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 285-A39 | ACTIVE | Wall/monotonic discrepancy strictly below 2,000 ms; suspend semantics known; no other clock fault; valid file read and handoff complete | NEW_OPERATION | FINAL_GATE | FINAL_GATE | CONTENT_RELEASED | NONE | MATCH | ACTIVE | HANDOFF_RETURNED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>CONTENT_BYTES>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=TERMINAL;operation_lifecycle=HANDOFF_RETURNED;reader_state=AVAILABLE;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=RELEASED;decision_record=ACTIVE;owner_channel=NOT_APPLICABLE | BOUNDARY | FIXED_RESULT | 278-A56a | NONE | NO_ACK_REQUIRED | Entry 285 §1.6; Entry 286 §3; clock discrepancy below tolerance |
| 285-A40 | ACTIVE | Wall/monotonic discrepancy exactly 2,000 ms; suspend semantics known; no other clock fault; valid file read and handoff complete | NEW_OPERATION | FINAL_GATE | FINAL_GATE | CONTENT_RELEASED | NONE | MATCH | ACTIVE | HANDOFF_RETURNED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>CONTENT_BYTES>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=TERMINAL;operation_lifecycle=HANDOFF_RETURNED;reader_state=AVAILABLE;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=RELEASED;decision_record=ACTIVE;owner_channel=NOT_APPLICABLE | BOUNDARY | FIXED_RESULT | 278-A56a | NONE | NO_ACK_REQUIRED | Entry 285 §1.6; Entry 286 §3; exact tolerance boundary |
| 285-A41 | ACTIVE | Wall/monotonic discrepancy strictly above 2,000 ms; active decision checked at final gate after staging | NEW_OPERATION | FINAL_GATE | FINAL_GATE | REQUEST_DENIED | DECISION_EXPIRED | MATCH | EXPIRED | DISCARDED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=TERMINAL;operation_lifecycle=DISCARDED;reader_state=AVAILABLE;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=DISCARDED;decision_record=EXPIRED;owner_channel=NOT_APPLICABLE | NEGATIVE | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 285 §1.6; Entry 286 §3; discrepancy above tolerance |
| 285-A42 | ACTIVE | Suspend semantics unknown; one active decision checked at final gate after staging | NEW_OPERATION | FINAL_GATE | FINAL_GATE | REQUEST_DENIED | DECISION_EXPIRED | MATCH | EXPIRED | DISCARDED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=TERMINAL;operation_lifecycle=DISCARDED;reader_state=AVAILABLE;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=DISCARDED;decision_record=EXPIRED;owner_channel=NOT_APPLICABLE | NEGATIVE | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 285 §1.6; Entry 286 §3; active-decision suspend-unknown case |
| 285-A43 | ACTIVE | Detected backward wall-clock step; active decision checked at final gate after staging | NEW_OPERATION | FINAL_GATE | FINAL_GATE | REQUEST_DENIED | DECISION_EXPIRED | MATCH | EXPIRED | DISCARDED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=TERMINAL;operation_lifecycle=DISCARDED;reader_state=AVAILABLE;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=DISCARDED;decision_record=EXPIRED;owner_channel=NOT_APPLICABLE | NEGATIVE | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 286 §3; retired clock composite; final-gate decision expiry |
| 287-A44 | ACTIVE | Detected backward wall-clock step invalidates the bound decision before intent commit | NEW_OPERATION | OPERATION_PREFLIGHT | PREFLIGHT | DECISION_EXPIRED | DECISION_EXPIRED | MATCH | EXPIRED | NONE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=NONE;operation_lifecycle=NONE;reader_state=AVAILABLE;reservation=NONE;probe_attempts_used=0;content_state=NONE;decision_record=EXPIRED;owner_channel=NOT_APPLICABLE | NEGATIVE | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 287 D3b; pre-intent backward-step control |
| 287-A45 | ACTIVE | Detected backward wall-clock step invalidates the active decision after staging; an operation-local terminal-outcome recording fault occurs; global ledger health and anchor/store epochs remain consistent | NEW_OPERATION | FINAL_GATE | FINAL_GATE | REQUEST_DENIED | DECISION_EXPIRED | MATCH | EXPIRED | UNRESOLVED | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | REQUEST_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=UNRESOLVED;operation_lifecycle=UNRESOLVED;reader_state=HALTED;reservation=COMMITTED_RETAINED;probe_attempts_used=1;content_state=STAGED;decision_record=EXPIRED;owner_channel=NOT_APPLICABLE | RECOVERY | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 287 D3b; failed final-outcome record without epoch regression |
| 287-A46 | ACTIVE | Suspend semantics unknown invalidates a pending nonce; an attestation arrives after that invalidation; no eligible decision exists at the fixed endpoint | APPROVAL_ATTESTATION | ISSUANCE | ISSUANCE | REQUEST_UNAVAILABLE | DECISION_EXPIRED | NOT_CHECKED | NONE | NOT_APPLICABLE | APPROVAL_LATE | NOT_APPLICABLE | OWNER_ATTESTATION_LATE | REQUEST_RESULT>OWNER_CHANNEL_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=NONE;operation_lifecycle=NOT_APPLICABLE;reader_state=AVAILABLE;reservation=NONE;probe_attempts_used=0;content_state=NONE;decision_record=NONE;owner_channel=OWNER_ATTESTATION_LATE | BOUNDARY | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 287 D3b; suspend-unknown pending-nonce case |
| 287-A47 | ACTIVE | Detected backward wall-clock step invalidates a pending nonce; an attestation is subsequently presented using that invalidated nonce; no eligible decision exists at the fixed endpoint | APPROVAL_ATTESTATION | ISSUANCE | ISSUANCE | REQUEST_UNAVAILABLE | DECISION_EXPIRED | NOT_CHECKED | NONE | NOT_APPLICABLE | APPROVAL_LATE | NOT_APPLICABLE | OWNER_ATTESTATION_LATE | REQUEST_RESULT>OWNER_CHANNEL_RESULT>PROTECTED_AUDIT_RESULT>READER_HALT_STATE | NOT_APPLICABLE | operation_record=NONE;operation_lifecycle=NOT_APPLICABLE;reader_state=AVAILABLE;reservation=NONE;probe_attempts_used=0;content_state=NONE;decision_record=NONE;owner_channel=OWNER_ATTESTATION_LATE | NEGATIVE | FIXED_RESULT | 278-A56a | NONE | NOT_APPLICABLE | Entry 288 §8; backward-step pending-nonce control |

Field clarifications for this table:

- `transport_ack_capability=NONE` means the configured handoff mode has no trusted recipient-side acknowledgement. It does not assert a handoff occurred. For A39/A40, handoff has occurred and the required delivery status is `NO_ACK_REQUIRED`; for rows with no handoff, `expected_delivery_ack_status=NOT_APPLICABLE`.
- `expected_issuance_result=NOT_APPLICABLE` is explicit for operation fixtures A39–A45. A46/A47 explicitly represent a late attestation after nonce invalidation and use `APPROVAL_LATE` plus `OWNER_ATTESTATION_LATE`.
- `probe_attempts_used=1` for A39–A43 and A45 because the bounded file read was attempted; it is `0` before intent for A44 and for issuance-only A46/A47.
- For A45, `expected_internal_code=DECISION_EXPIRED` retains the selected gate cause. The inability to durably record the final denial changes the operation/lifecycle recovery state to `UNRESOLVED` and reader state to `HALTED`. It does not fabricate an epoch regression.
- All nine rows are active, have exactly one setup/result tuple, and link to the retired `278-A56a`. Each `state_effects` string uses the eight keys in Entry 283 §8.4's required order; no free prose is embedded in it.

The validator must serialize each row to Entry 283 §8.4's grammar, validate each field against its own enum, verify `gate_phase` against `evaluation_stage`, and validate the phase-specific requester mapping. A missing key, extra key, duplicate key, key-order deviation, unknown value, or free text inside `state_effects` returns `MANIFEST_INVALID`. A row with swapped A51/A52 requester outputs returns `MANIFEST_INVALID / PHASE_RESULT_MISMATCH`.

## 10. C14 mechanical correction — Markdown delimiter and fixture-ID grammar

Entry 287's A50 predecessor contained an unbalanced inline code span around the recovery timestamp (`Tack+60s`). The correct text is now `recovery occurs at Tack+60s`; the opening and closing backticks are balanced. Entry 287's C13 D1/D2 prose identifiers are replaced by the schema-valid IDs:
- former D1a → `287-A48`;
- former D1b → `287-A49`;
- former D1c → `287-A50`;
- former D2-P → `287-A51`;
- former D2-F → `287-A52`.

Every manifest `qualified_id` introduced by this amendment MUST match `^[0-9]{3}-A[0-9]+[a-z]?$`. These fixture IDs must be present inside the sole authoritative manifest when consolidated, not only in prose. A prose reference alone is not fixture coverage.

Mechanical checks required before accepting the next consolidated manifest:
1. Inline code spans are balanced per line in the Markdown table and fixture clauses, including the corrected recovery timestamp.
2. All active/retired IDs are unique and every row ID matches the required regex.
3. The nine required clock fixtures are all active and linked to `278-A56a`.
4. Every clock row has all mandatory fields and a syntactically valid eight-key `state_effects` value.
5. Phase derivation, phase-specific results, and the ack-status discriminator tests all reject the specified alternative values.

## 11. C15 review boundary and residual blockers

**Next actor: Claude/Sonnet.** Review Entry 288 against the current fetched source text of Entries 282, 283, 285, 286, and 287. Review only the ten C14 defect groups: D1-1, D1-2, D1-3, D2-1, D3a-1, D3b-1, D3b-2, D3b-3, D3b-4, and the mechanical defect group M-1.

Start with exactly one verdict: `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`. For every surviving defect, give the exact clause, a concrete counterexample, conflicting result fields/state effects, the minimum repair, and a discriminating test. In particular, verify that the ACK classifier is exhaustive/ordered, the deadline-equality attempt cannot commit success, A50 does not infer absence from unavailable evidence, the phase field derives from `evaluation_stage`, the replacement set is machine-enforced, and every clock row serializes against the field enums and state-effects grammar. Do not reopen R1–R4 or broaden into a full S5/S9/S10 audit absent a concrete contradiction in these repairs.

S5, S9, and S10 remain acceptance blockers. The required full manifest, remaining Entry 285 §1.6 replacement maps, positive controls, timing-mutation coverage, and combined consolidated-contract acceptance have not been demonstrated by this amendment. No runtime, local M0A, implementation, reader retry/bypass, credential, install/update, launch, or canonical-route operation is authorized.

**Final posture: `KEEP_BLOCKED`.**
