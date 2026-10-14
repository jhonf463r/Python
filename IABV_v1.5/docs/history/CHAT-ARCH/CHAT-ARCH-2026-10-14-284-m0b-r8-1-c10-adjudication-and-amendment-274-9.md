# CHAT-ARCH-2026-10-14-284 — C10 adjudication and amendment 274.9

- Status: `M0B_R8_1_AMENDMENT_274_9_PASS_FOR_R1_R4_PENDING_S5_S9_S10`
- Normalized bounded result: `PASS` for the R1–R4 delta after the sole C10 repair was checked by C11.
- Operational posture: `KEEP_BLOCKED`.
- Type: bounded documentary amendment; not a consolidated/accepted contract or runtime claim.

## 0. Scope and provenance

Entry 284 addresses the four repairs identified by the C10 review of Entry 283: R1 deadline-source fixtures; R2 status-query dependency ordering; R3 listing-overflow lifecycle; and R4 cross-field state correspondence.

Review chain:
- C10 result: `PASS_WITH_REPAIRS`; the only reported survivor was R1-D, the explicit shared Owner-channel enum membership for `ISSUANCE_MULTIPLE_DEADLINES_TIED`.
- C11 result: `PASS` for the restricted R1-D scope. C11 verified that the complete shared enum retains the ten inherited tokens, includes the four deadline-specific tokens, and that fixture R1-C uses the tied-deadline value consistently.
- Therefore R1-D is closed for this bounded delta. This does not accept or implement the consolidated contract and does not close S5, S9, or S10.

Current public files and blob identities were fetched by the coordinator before this adjudication:
- Entry 280: `6d7d7f4966e1224456e00410c812395e6a5c598f`.
- Entry 281: `46cf60a60500f942047500c3f19cced0e9beb83d`.
- Entry 282: `0fa5cc1cb8f63c05c7309ec7dcb98966d738ecf3`.
- Entry 283: `a9fcd0ca56c01d9118504aa77274b6737a3961c7`.

The current public text and blobs for Entries 280–283 are `PROVEN_BY_SOURCE`. The supplied C10/C11 narratives and their conclusions are `OWNER_REPORTED`. The normative repairs and fixtures below remain `PROPOSED`. Runtime behavior, M0A local state, and historical fidelity to Entries 274–277 remain `UNPROVEN`.

If accepted, Entry 284 supersedes only Entry 283 §§2.2–2.4 for deadline-source fixtures, §4 for status-query ordering, §6 phase 5 for listing-overflow lifecycle, and §8.2/§8.4 for Owner-channel and cross-field state consistency. It does not close S5, S9, or S10.

## 1. R1 — Deadline-source field and exact-boundary fixtures

### 1.1 Strict commit rule

Retain Entry 283's deadlines:
- `Dchallenge` = challenge creation time + 120 seconds.
- `Downer` = authenticated Owner-attestation time + 60 seconds.
- `Dwindow` = `T0 + 120 seconds`.

The hidden decision's durable ledger commit must linearize strictly before the earliest deadline. Equality is expired. Distinguish attempt-start checks from commit-time checks:

- If issuance starts at or after `Downer`, freshness fails before commit: `APPROVAL_FRESHNESS_EXPIRED` / internal `DECISION_EXPIRED`.
- If issuance starts while evidence is fresh but its durable commit linearizes exactly at or after the earliest deadline, outcome is `ISSUANCE_DEADLINE_MISSED` / internal `DECISION_EXPIRED`.
- If the authoritative ledger write itself fails while the commit deadline is still open, outcome is `ISSUANCE_FAILED` / internal `LEDGER_UNAVAILABLE`.

A decision is usable only if its durable commit is timely and `not_before = Dwindow`. No decision record is created for unsuccessful issuance.

### 1.2 Required deadline-source field and shared Owner-channel enum

Add `expected_issuance_deadline_sources` to the required fixture schema. Accepted values are `NONE`, `DCHALLENGE`, `DOWNER`, `DWINDOW`, `DCHALLENGE_AND_DOWNER`, `DCHALLENGE_AND_DWINDOW`, `DOWNER_AND_DWINDOW`, and `ALL_THREE`. For a deadline fixture, it lists all deadlines tied for the earliest time. The validator derives the correct value from event times; it must reject a single-source value when the times show a tie.

**Normative enum amendment, superseding the prior Owner-channel enum in Entry 283 §8.2.** The complete and exhaustive allowed enum for both `expected_result_owner_channel` and `state_effects.owner_channel` is:

`NOT_APPLICABLE`, `OWNER_PROMPT_SHOWN`, `OWNER_APPROVAL_ACCEPTED`, `OWNER_REJECTION_RECORDED`, `OWNER_NO_RESPONSE`, `OWNER_ATTESTATION_LATE`, `OWNER_ATTESTATION_STALE`, `OWNER_ATTESTATION_INVALID`, `ISSUANCE_WRITE_FAILED`, `ISSUANCE_DEADLINE_MISSED`, `ISSUANCE_CHALLENGE_DEADLINE_REACHED`, `ISSUANCE_OWNER_FRESHNESS_DEADLINE_REACHED`, `ISSUANCE_PUBLIC_WINDOW_DEADLINE_REACHED`, `ISSUANCE_MULTIPLE_DEADLINES_TIED`.

This is one shared enum, not two independently maintained lists. Entry 283 §8.4's `state_effects.owner_channel` field MUST reference exactly this enum. The four final values extend the prior enum; in particular, `ISSUANCE_MULTIPLE_DEADLINES_TIED` is a valid enum member, not merely an example token in a fixture. C11 returned `PASS` for this precise issue.

For an issuance attempt begun while evidence remains fresh but committed exactly at the controlling deadline:
- unique `DCHALLENGE` → `ISSUANCE_CHALLENGE_DEADLINE_REACHED`;
- unique `DOWNER` → `ISSUANCE_OWNER_FRESHNESS_DEADLINE_REACHED`;
- unique `DWINDOW` → `ISSUANCE_PUBLIC_WINDOW_DEADLINE_REACHED`;
- two or three tied earliest deadlines → `ISSUANCE_MULTIPLE_DEADLINES_TIED`.

`expected_result_owner_channel` and `state_effects.owner_channel` must match. These fields distinguish the protected cause; they do not change the public result or internal R2 code. Each commit-at-deadline fixture expects issuance `ISSUANCE_DEADLINE_MISSED`, internal `DECISION_EXPIRED`, decision status `NONE`, and lifecycle `NONE`. Before `Dwindow`, requester output stays `APPROVAL_PENDING`; at/after `Dwindow` without a usable hidden decision, it is `REQUEST_UNAVAILABLE`.

### 1.3 Discriminating fixtures

**R1-A — `Downer` uniquely earliest.** Challenge creation `T0+10s`; Owner attestation `T0+58s`; issuance attempt starts before `T0+118s`; durable commit linearizes exactly at `T0+118s`. Thus `Downer=T0+118s`, `Dchallenge=T0+130s`, `Dwindow=T0+120s`. Expected: `ISSUANCE_DEADLINE_MISSED` / `DECISION_EXPIRED`; source `DOWNER`; Owner channel `ISSUANCE_OWNER_FRESHNESS_DEADLINE_REACHED`; decision status/lifecycle `NONE`. Requester remains `APPROVAL_PENDING` until the window endpoint, then sees `REQUEST_UNAVAILABLE`.

**R1-B — `Dwindow` uniquely earliest.** Challenge creation `T0+10s`; Owner attestation `T0+65s`; attempt begins before `T0+120s`; durable commit linearizes exactly at `T0+120s`. Thus `Downer=T0+125s`, `Dchallenge=T0+130s`, `Dwindow=T0+120s`. Expected: `ISSUANCE_DEADLINE_MISSED` / `DECISION_EXPIRED`; source `DWINDOW`; Owner channel `ISSUANCE_PUBLIC_WINDOW_DEADLINE_REACHED`; decision status/lifecycle `NONE`; requester sees `REQUEST_UNAVAILABLE` at the endpoint.

**R1-C — `Dchallenge` and `Dwindow` tied.** Challenge creation `T0`, so both deadlines equal `T0+120s); set `Downer` later. The attempt starts before the tied deadline and durable commit linearizes exactly at it. Expected: `ISSUANCE_DEADLINE_MISSED` / `DECISION_EXPIRED`; source `DCHALLENGE_AND_DWINDOW`; `expected_result_owner_channel=ISSUANCE_MULTIPLE_DEADLINES_TIED`; `state_effects.owner_channel=ISSUANCE_MULTIPLE_DEADLINES_TIED`; decision status and `state_effects.decision_record` are `NONE`; expected lifecycle and operation lifecycle are `NONE`; operation record `NONE`; reader state `AVAILABLE`; reservation `NONE`; probe attempts `0`; content state `NONE`. Requester sees `REQUEST_UNAVAILABLE` at the endpoint.

The validator rejects a deadline miss mislabeled `ISSUANCE_FAILED` when the ledger was available. These fixtures improve W1/W11 but do not close S10.

## 2. R2 — Ordered status-query dependencies; no partial result

A `STATUS_QUERY` must use one authenticated consistent ledger snapshot/transaction, or an equivalent consistency barrier. No partial metadata may be returned if a mandatory dependency fails. Check in this order:

1. Authenticate requester principal/session and form the exact operation key from trusted identity plus the supplied client token. This reveals nothing about whether the operation exists.
2. Check ledger availability, global ledger/anchor integrity, anti-rollback epochs and applicable recovery state **before record-specific reads**. An unavailable required read is `LEDGER_UNAVAILABLE`; a detected integrity/anchor failure is `LEDGER_INTEGRITY_UNPROVEN`.
3. Read and authenticate the exact linked operation record. Unavailable → `REQUEST_DENIED` / `LEDGER_UNAVAILABLE`; authenticity/integrity failure → `REQUEST_DENIED` / `LEDGER_INTEGRITY_UNPROVEN`.
4. Read and authenticate the linked decision record or an authenticated tombstone proving its absence. Apply Entry 283 §4's exact result tuple for valid, unavailable, malformed, authenticated-tombstone and missing-unproven cases.

If a dependency fails after earlier reads succeeded, discard the partial response and return the applicable failure. If global integrity failure is discovered after the operation record was tentatively read, never return `STATUS_RETURNED`. If a consistent authenticated snapshot cannot be guaranteed, fail closed without a status response.

An exact authenticated query of a prior `UNRESOLVED` operation is still permitted as a bounded metadata-only query; `UNRESOLVED` halts new content-bearing operations, not this status lookup. All requester-binding, global-integrity/availability, operation-record and linked-decision/tombstone requirements still apply. The query creates no intent/reservation, does not resume the reader, and never releases repository content.

Required tests: (a) global integrity fails before operation read; (b) integrity failure is discovered after a tentative operation read; both return denial with no partial status; (c) linked decision read fails, yielding `REQUEST_DENIED` / `LEDGER_UNAVAILABLE` / `UNAVAILABLE`; (d) a valid exact query for an unresolved operation returns `STATUS_RETURNED` with lifecycle `UNRESOLVED`, while the reader stays halted for new content operations.

## 3. R3 — Listing overflow uses DENIED, not DISCARDED

Append this rule to Entry 283 §6 phase 5:

For listing overflow, lifecycle is `DENIED` under §3.2, not `DISCARDED`, because count-first enumeration does not stage or buffer entry names. `DISCARDED` applies only when names/content were actually staged and subsequently destroyed after a later gate failed.

For every cap+1 listing, internal result remains `LIST_LIMIT_EXCEEDED`; public result remains `REQUEST_UNAVAILABLE`; the maximum deliverable reservation remains charged; no names are delivered; and one bounded probe is used. This lifecycle rule applies regardless of where an invalid/reparse entry appears.

Discriminating pair: cap+1 count-first listing with no names staged → `DENIED`; within-cap listing staged and then rejected at the final gate → `DISCARDED`. Reject `DISCARDED` for the first fixture.

## 4. R4 — Cross-field state correspondence

The next consolidated manifest must validate `expected_decision_status` against `state_effects.decision_record` using this exact mapping:

| `expected_decision_status` | Required `state_effects.decision_record` |
|---|---|
| `NONE` | `NONE` |
| `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| `PENDING_VISIBILITY` | `HIDDEN` |
| `ACTIVE` | `ACTIVE` |
| `EXPIRED` | `EXPIRED` |
| `REVOKED` | `REVOKED` |
| `UNAVAILABLE` | `UNAVAILABLE` |
| `SCHEMA_INVALID` | `SCHEMA_INVALID` |
| `MISSING_UNPROVEN` | `MISSING_UNPROVEN` |

Add `NOT_APPLICABLE` to the allowed enum for `state_effects.decision_record`; it differs from `NONE`. Validate both fields against their own enums first, then enforce this crosswalk. `PENDING_VISIBILITY` with `HIDDEN` is valid for a durable decision before `not_before`; with `ACTIVE` it is `MANIFEST_INVALID`. `NONE` with `HIDDEN` is also invalid.

Every fixture carries `expected_issuance_deadline_sources`; use `NONE` for non-deadline cases. For deadline fixtures, the value must match event times. `expected_result_owner_channel` and `state_effects.owner_channel` must agree. For fixtures with no Owner/issuer event, both must be `NOT_APPLICABLE`.

## 5. Required delta fixtures

Add independent fixtures for R1-A, R1-B, R1-C; R2's ordering and partial-response cases; R3's count-first versus staged lifecycle pair; and R4's matching/mismatching cross-field values. Do not combine multiple faults in one fixture. Each fixture requires one requester result, one internal result or `NONE`, one issuance result or `NOT_APPLICABLE`, one decision status, one operation lifecycle, one deadline-source value, one Owner-channel result, a fixed observation sequence, and fully parsed `state_effects`.

## 6. Residual blockers — unchanged

- **S5 — Composite fixtures and lexical/race/crash boundaries:** split compound setups; enumerate rejected lexical classes; cover crash boundaries, root/path replacement, and an in-place concurrent writer; include a valid sensitive-name pre-approval case; confirm retired cases have adequate replacements.
- **S9 — Trusted delivery acknowledgement:** define an acknowledgement authority outside requester control, bound to operation ID, recipient and response digest; specify no-ack and trusted-ack crash recovery; define the transition for `DELIVERY_ACKNOWLEDGED` versus `DELIVERED`.
- **S10 — Precedence/time-boundary mutation coverage:** enumerate adjacent-gate/final-gate precedence pairs; test every relevant deadline at T−ε, T and T+ε; test final-gate `DECISION_REVOKED` with staged content; ensure deny-all mutants fail. R1 fixtures do not close S10.

## 7. Acceptance and next actor

C10 found a single repair in this bounded scope (R1-D). C11 returned `PASS` on that repair. The bounded R1–R4 amendment is therefore marked `PASS` for documentary purposes; this does not accept the consolidated contract or close S5/S9/S10.

Evidence:
- `PROVEN_BY_SOURCE`: current public blobs listed in §0.
- `OWNER_REPORTED`: C10 and C11 review narratives.
- `PROPOSED`: the amendment rules and fixture requirements.
- `UNPROVEN`: runtime/platform behavior, M0A local state, historical fidelity to Entries 274–277, anti-rollback enforcement, filesystem containment, Owner/requester isolation, revocation freshness, trusted delivery acknowledgement, and production block-scope/release behavior.

**Next workstream:** address S5, S9, and S10 in one bounded adversarial delta, then submit that delta to Claude/Sonnet for targeted review. Do not repeat R1-D or reopen R2–R4 absent contradictory evidence.

No implementation, builds/tests/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update/launch, or canonical-route rewrite is authorized. Entry 284 cannot grant repository-read authority or release a governance block. `KEEP_BLOCKED`.
