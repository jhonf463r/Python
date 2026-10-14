# CHAT-ARCH-2026-10-14-287 — C13 adjudication and bounded D1/D2/D3a/D3b repairs (amendment 274.12)

- Status: `M0B_R8_1_AMENDMENT_274_12_PROPOSED_PENDING_C14_REVIEW`
- Parent: Entry 286 / amendment 274.11.
- C13 verdict: `PASS_WITH_REPAIRS` (`OWNER_REPORTED` review outcome).
- Operational posture: `KEEP_BLOCKED`.
- Scope: only C13-D1, C13-D2, C13-D3a, and C13-D3b. R1–R4 are not reopened. No implementation, runtime claim, launch authority, or final contract acceptance is granted.

## 0. Sources and provenance

Current public-source text and blob identities fetched back through the connected GitHub contents route:

- Entry 282: `0fa5cc1cb8f63c05c7309ec7dcb98966d738ecf3`.
- Entry 283: `a9fcd0ca56c01d9118504aa77274b6737a3961c7`.
- Entry 285: `778afe7ebd883e68681f066c2f5f75f30983c633`.
- Entry 286: `912a9c0b156b17317f611007dc6711296b84e4c9`.

The C13 reviewer reports that raw fetch was blocked in its environment and that Entries 282/283 could not be retrieved there; those access limitations and C13's findings are `OWNER_REPORTED`. The current public text and blob identities above were independently fetched for this amendment and are `PROVEN_BY_SOURCE`. The proposed normative wording and fixtures below remain `PROPOSED`. Runtime behavior, crash durability, clock behavior, filesystem behavior, and transport behavior remain `UNPROVEN`.

References: [Entry 282](CHAT-ARCH-2026-10-14-282-m0b-r8-1-c8-adjudication-and-amendment-274-7.md), [Entry 283](CHAT-ARCH-2026-10-14-283-m0b-r8-1-c9-adjudication-and-amendment-274-8.md), [Entry 285](CHAT-ARCH-2026-10-14-285-m0b-r8-1-c12-s5-s9-s10-delta-274-10.md), and [Entry 286](CHAT-ARCH-2026-10-14-286-m0b-r8-1-c13-repair-d1-d3-amendment-274-11.md).

## 1. C13-D1 / S9 — Disambiguate `ACK_COMMIT_FAILED` from `ACK_TIMED_OUT`

### 1.1 Normative rule for `Tack`

Amend Entry 286 §1.1 and Entry 285 §§2.2–2.4 with the following exclusive classification rule. The deadline is strict: a trusted acknowledgement/DELIVERED transaction must linearize strictly before `Tack`.

Evaluate authenticated receipt-event time and authoritative ledger evidence of the commit attempt. Recovery wall-clock time alone never determines this classification:

1. Select `ACK_TIMED_OUT` if the authenticated receipt event time is at or after `Tack`, or trusted ledger evidence shows that the acknowledgement/DELIVERED commit was linearized or rejected at or after `Tack`.
2. Select `ACK_COMMIT_FAILED` only if the authenticated receipt event time is strictly before `Tack`, the atomic transaction is known not to be durable, and there is no evidence of a commit attempt linearized or rejected at or after `Tack`. A verified rollback before `Tack` and a crash before any commit attempt satisfy this condition. Recovery after `Tack` does not, by itself, turn this case into a timeout.
3. If receipt time or commit outcome cannot be established because the authoritative source/evidence is unavailable, select `ACK_SOURCE_UNAVAILABLE`, unless the higher-priority ledger availability/integrity outcome applies. Do not infer `ACK_COMMIT_FAILED` from absence of evidence when the outcome is unknowable.
4. If the acknowledgement evidence and `DELIVERED` were atomically committed durably strictly before `Tack`, select `ACK_ACCEPTED` with lifecycle `DELIVERED`.

For either `ACK_TIMED_OUT` or `ACK_COMMIT_FAILED`, the operation is `UNRESOLVED`; retain the committed reservation, halt new content-bearing operations, release no further content, and never replay or repeat the handoff automatically. `DELIVERY_ACKNOWLEDGED` remains an audit event, never a lifecycle state.

This rule resolves the overlap between Entry 285 §2.3 (deadline expiry without a durable valid acknowledgement) and §2.4 (commit at `Tack` or later). It preserves a single `expected_delivery_ack_status` for each fully specified fixture.

### 1.2 Required discriminating fixtures

Keep the three fixtures independent and fix the receipt timestamp, authoritative transaction evidence, and recovery time in each row:

- **287-D1a — rollback before deadline:** valid authenticated receipt event at `Tack−10ms`; authoritative rollback at `Tack−5ms`; no commit attempt at or after `Tack`. Expected `ACK_COMMIT_FAILED` / lifecycle `UNRESOLVED` / reader `HALTED` / reservation `COMMITTED_RETAINED` / no replay.
- **287-D1b — commit at the boundary:** valid receipt event at `Tack−10ms`; atomic commit linearizes exactly at `Tack`. Expected `ACK_TIMED_OUT` / lifecycle `UNRESOLVED` / reader `HALTED` / reservation `COMMITTED_RETAINED` / no replay.
- **287-D1c — crash before attempt:** valid receipt event at `Tack−10ms`; crash before any commit attempt; recovery at `Tack+60s); no authoritative evidence of an attempt at or after `Tack`. Expected `ACK_COMMIT_FAILED` / lifecycle `UNRESOLVED` / reader `HALTED` / reservation `COMMITTED_RETAINED` / no replay.

The validator must reject the alternate ack-status value in each of these rows. Add controls already required by Entry 286 §1.2: unknowable receipt/commit state maps to `ACK_SOURCE_UNAVAILABLE`; a durable atomic commit before `Tack` maps to `ACK_ACCEPTED` / `DELIVERED`.

## 2. C13-D2 / S10 — Phase-aware requester mapping for decision expiry

### 2.1 Inherited Entry 282 rule (verbatim)

Entry 282 §4.2, item 12, states:

> `DECISION_EXPIRED` → `DECISION_EXPIRED` for a new operation token using a bound decision that expired. For a late approval that leaves no usable decision at the fixed visibility endpoint, use `REQUEST_UNAVAILABLE`.

Entry 282 §4.2 also says the exhaustive mapping is applied after the stage-specific approval-window rule. Its fixed-window rule remains in force: before the endpoint, the requester receives the uniform `APPROVAL_PENDING` envelope; at the endpoint, an eligible durably committed decision yields `DECISION_ISSUED`, while the absence of an eligible decision yields `REQUEST_UNAVAILABLE`.

### 2.2 Required phase field and mapping key

Add a normative per-fixture field `gate_phase` with exactly these values:

- `ISSUANCE`: the approval/decision issuance window, including its fixed visibility endpoint.
- `PREFLIGHT`: admission of a new content-bearing operation before intent, staging, or content I/O.
- `FINAL_GATE`: revalidation before release after an operation has been admitted and result content has been staged.

The requester mapping for a `DECISION_EXPIRED` internal result is keyed by the pair `(expected_internal_code, gate_phase)`, after the fixed-window override is applied:

| `expected_internal_code` | `gate_phase` | Required `expected_result_requester` | Required stage effect |
|---|---|---|---|
| `DECISION_EXPIRED` | `ISSUANCE` | `REQUEST_UNAVAILABLE` at the fixed visibility endpoint when no eligible usable decision exists | No usable decision is issued; no content operation or reservation is created. Before the endpoint, the fixed-window `APPROVAL_PENDING` override applies. |
| `DECISION_EXPIRED` | `PREFLIGHT` | `DECISION_EXPIRED` | Reject before intent/staging/content I/O; lifecycle `NONE`; reservation `NONE`. |
| `DECISION_EXPIRED` | `FINAL_GATE` | `REQUEST_DENIED` | With staged content, destroy or make it inaccessible and durably record `DISCARDED`; retain the reservation; release zero bytes; no handoff. |

For the D2 coincident-boundary fixture, `gate_phase=FINAL_GATE`, `expected_internal_code=DECISION_EXPIRED`, and `expected_result_requester=REQUEST_DENIED`. The independently fresh authenticated revocation remains a secondary audit fact; it does not change the selected primary code.

For a new operation first presented with an already-expired bound decision, `gate_phase=PREFLIGHT` and the inherited public result is `DECISION_EXPIRED`. That row is not interchangeable with the staged final-gate row. No fixture may omit `gate_phase` or use one phase's requester result for another.

### 2.3 Discriminating pair and validator behavior

Create two fixtures with the same internal code but different phases:

- **287-D2-P:** an already-expired bound decision at admission, no intent, no staging. Expected `PREFLIGHT` / internal `DECISION_EXPIRED` / requester `DECISION_EXPIRED` / decision status `EXPIRED` / lifecycle `NONE` / reservation `NONE` / reader `AVAILABLE`.
- **287-D2-F:** the Entry 286 §2.2 coincident expiry-and-fresh-revocation case at the final gate, with content staged. Expected `FINAL_GATE` / internal `DECISION_EXPIRED` / requester `REQUEST_DENIED` / decision status `EXPIRED` / lifecycle `DISCARDED` / reservation `COMMITTED_RETAINED` / reader `AVAILABLE` / content state `DISCARDED` / zero bytes released.

The manifest validator accepts each public value only with its specified phase and rejects the pair of rows if their requester outputs are exchanged. This adds a phase discriminator; it does not change the inherited mapping for other R2 selections.

## 3. C13-D3a / S5 — Mechanically enforce retired-fixture replacement coverage

### 3.1 Normative manifest data

Add a machine-readable, normative `required_replacement_ids` table to the authoritative manifest. For the clock composite in this amendment, the exact required set is:

| Retired ID | Required active replacement IDs |
|---|---|
| `278-A56a` | `{285-A39, 285-A40, 285-A41, 285-A42, 285-A43, 287-A44, 287-A45, 287-A46}` |

The five existing base fixtures remain independently mandatory: `285-A39` (<2,000 ms), `285-A40` (=2,000 ms), `285-A41` (>2,000 ms), `285-A42` (unknown suspend semantics for an active decision), and `285-A43` (detected backward wall-clock step). The three additional fixtures in Entry 287 split out phase/object/recording variants required by D3b; they do not substitute for any of the five base fixtures.

Each required ID must exist exactly once among active fixtures, retain its traceability to `278-A56a`, and have its own fixed setup and single result tuple. An absent, duplicated, retired, or renamed required ID makes replacement coverage incomplete.

### 3.2 Validator rule and tests

For each retired ID, compute the active fixture IDs linked to it and compare them with its normative `required_replacement_ids` set. If any required replacement is missing, the validator must emit `MANIFEST_INVALID` with diagnostic `REPLACEMENT_COVERAGE_INCOMPLETE`. A prose assertion, total row count, or nonempty replacement list is not sufficient evidence of coverage.

The discriminating omission matrix must remove each of the eight required IDs in turn. Every resulting manifest must fail with `REPLACEMENT_COVERAGE_INCOMPLETE`; the complete manifest must pass this specific cross-check. In particular, all five original omission tests (one each for `285-A39` through `285-A43`) remain required. This delta addresses the `278-A56a` mapping only; the other multi-replacement maps in Entry 285 §1.6 are not adjudicated here and remain within the open S5 blocker.

## 4. C13-D3b / S5 — Give each clock fixture one phase and one complete result tuple

Every active fixture `285-A39` through `285-A43`, and each new fixture `287-A44` through `287-A46`, must declare exactly one `gate_phase` and one allowed value for each outcome field. No result may say “appropriate to the fixture's stage,” “depending on stage,” or list alternatives such as `NONE/DISCARDED/UNRESOLVED`.

For these tuples, `reader_state=AVAILABLE` means no global reader halt is caused by that row; `reader_state=HALTED` is required when its unresolved durable outcome invokes the halt rule. A final-gate denial after staging uses `REQUEST_DENIED`, lifecycle `DISCARDED`, a retained reservation, and zero content release. Before intent, use lifecycle `NONE` and no reservation. An outcome-recording failure after a durable intent is `UNRESOLVED`; do not report a completed `DISCARDED` lifecycle while the required terminal record is not durable.

### 4.1 Required fixed tuples

| Fixture | Single setup / `gate_phase` | Internal result | Requester result | Decision status | Lifecycle | Reservation | Reader state | Additional fixed effects |
|---|---|---|---|---|---|---|---|---|
| `285-A39` | Discrepancy strictly below 2,000 ms; suspend semantics established; no other clock fault; otherwise valid file read, staged result, final gate | `NONE` | `CONTENT_RELEASED` | `ACTIVE` | `HANDOFF_RETURNED` | `COMMITTED_RETAINED` | `AVAILABLE` | Mode `NONE`; ack status `NO_ACK_REQUIRED`; no `DELIVERED` claim. |
| `285-A40` | Discrepancy exactly 2,000 ms; suspend semantics established; no other clock fault; otherwise valid file read, staged result, final gate | `NONE` | `CONTENT_RELEASED` | `ACTIVE` | `HANDOFF_RETURNED` | `COMMITTED_RETAINED` | `AVAILABLE` | Mode `NONE`; ack status `NO_ACK_REQUIRED`; no `DELIVERED` claim. |
| `285-A41` | Discrepancy strictly above 2,000 ms; active decision checked at final gate after staging | `DECISION_EXPIRED` | `REQUEST_DENIED` | `EXPIRED` | `DISCARDED` | `COMMITTED_RETAINED` | `AVAILABLE` | Content state `DISCARDED`; zero bytes released; no handoff or ack. |
| `285-A42` | Suspend semantics unknown/unavailable; the protected object under test is one active decision at the final gate after staging | `DECISION_EXPIRED` | `REQUEST_DENIED` | `EXPIRED` | `DISCARDED` | `COMMITTED_RETAINED` | `AVAILABLE` | Content state `DISCARDED`; zero bytes released; no handoff or ack. Nonce behavior is covered separately by `287-A46`. |
| `285-A43` | Detected backward wall-clock step; active decision checked at final gate after staging | `DECISION_EXPIRED` | `REQUEST_DENIED` | `EXPIRED` | `DISCARDED` | `COMMITTED_RETAINED` | `AVAILABLE` | Content state `DISCARDED`; zero bytes released; no decision/nonce revival, no fresh decision from the previous approval, and no budget reset. |
| `287-A44` | Detected backward wall-clock step invalidates the bound decision before a new operation's intent commit; `PREFLIGHT` | `DECISION_EXPIRED` | `DECISION_EXPIRED` | `EXPIRED` | `NONE` | `NONE` | `AVAILABLE` | No intent, staging, content I/O, handoff, or reservation. |
| `287-A45` | Detected backward wall-clock step at the final gate after staging; the authoritative registry then demonstrably rolls back the required terminal-outcome record while remaining readable and trustworthy | `REGISTRY_ROLLBACK` | `REQUEST_DENIED` | `EXPIRED` | `UNRESOLVED` | `COMMITTED_RETAINED` | `HALTED` | `operation_record=UNRESOLVED`; content is not released and must not be claimed durably `DISCARDED`; no replay; halt pending authenticated reconciliation. |
| `287-A46` | Suspend semantics unknown/unavailable for one pending approval nonce; the fixed issuance endpoint arrives without a usable eligible decision; `ISSUANCE` | `DECISION_EXPIRED` | `REQUEST_UNAVAILABLE` | `NONE` | `NOT_APPLICABLE` | `NONE` | `AVAILABLE` | The nonce cannot issue a decision; no operation intent, reservation, staging, content I/O, or handoff. Before the endpoint, the fixed-window `APPROVAL_PENDING` override applies. |

For `285-A39` and `285-A40`, the positive result is fixed to a complete valid handoff in mode `NONE`; it is not deferred to unspecified stage-dependent wording. For `285-A43`, the base fixture is fixed to the final gate with staging. Its pre-intent and outcome-record-failure variants are separate IDs, not alternate tuples in `285-A43`. `285-A42` covers one decision object; pending-nonce invalidation is the separate `287-A46` fixture. Each new row declares `supersedes_retired_ids=278-A56a`.

### 4.2 Enum and state-effects cross-check against Entry 283 §8.4

The current public Entry 283 §8.4 explicitly permits these field/value pairs used by the proposed fixtures:

- `reader_state`: `AVAILABLE`, `HALTED`.
- `reservation`: `NONE`, `COMMITTED_RETAINED`.
- `content_state`: `NONE`, `STAGED`, `RELEASED`, `DISCARDED`.
- `operation_record`: `NONE`, `COMMITTED`, `TERMINAL`, `UNRESOLVED`.
- `decision_record`: `NONE`, `HIDDEN`, `ACTIVE`, `EXPIRED`, `REVOKED`, `UNAVAILABLE`, `SCHEMA_INVALID`, `MISSING_UNPROVEN`.

Entry 283 §3.2 defines the lifecycle vocabulary and explicitly assigns meanings to `NONE`, `HANDOFF_RETURNED`, `DISCARDED`, and `UNRESOLVED`; its requester-result allowlist includes `CONTENT_RELEASED`, `DECISION_EXPIRED`, and `REQUEST_UNAVAILABLE`. The proposed rows use each token in its own field; they do not treat `COMMITTED_RETAINED`, `HALTED`, or `DISCARDED` as interchangeable values across fields. The new field `gate_phase` and diagnostic `REPLACEMENT_COVERAGE_INCOMPLETE` are additions proposed by this amendment and require inclusion in the next consolidated schema/validator.

These are schema-level checks only. They do not prove that a runtime ledger, reader, clock, or transport implements the states.

## 5. C14 review boundary and residual status

**Next actor: Claude/Sonnet.** Perform one delta review of Entry 287 against the fetched-back current text of Entries 282, 283, 285, and 286. Review only C13-D1, C13-D2, C13-D3a, and C13-D3b:

1. D1: verify exclusive classification at `Tack`, and the three exact discriminators for rollback before deadline, commit at deadline, and crash before attempt followed by late recovery.
2. D2: verify the verbatim Entry 282 mapping, the `gate_phase` field, and the discriminating P/F rows.
3. D3a: verify the normative required-replacement table, validator diagnostic, and omission matrix.
4. D3b: verify that all eight mapped clock fixtures have one fixed phase/result tuple, and that each proposed state/token is field-valid under Entry 283 §8.4 and §3.2.

Start with exactly one verdict: `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`. For each survivor, give the exact clause, counterexample, conflicting fields/state effects, minimal repair, and discriminating test. Do not conduct a broad audit or reopen R1–R4 without a concrete contradiction in these four clauses.

S5, S9, and S10 remain acceptance blockers until their combined deltas, required manifest coverage, and positive controls are reviewed and consolidated. This entry is not implementation or runtime evidence, does not verify the local M0A checkout, does not authorize reader access/retry/bypass or credential inspection, and does not update canonical route documents.

**Final posture: `KEEP_BLOCKED`.**
