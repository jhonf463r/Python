# CHAT-ARCH-2026-10-14-286 — C13 bounded repair of D1–D3 (amendment 274.11)

- Status: `M0B_R8_1_AMENDMENT_274_11_PROPOSED_PENDING_C13_REVIEW`
- Parent review: Entry 285 / amendment 274.10 received `PASS_WITH_REPAIRS` from C12.
- Operational posture: `KEEP_BLOCKED`.
- Scope: repair only D1, D2, and D3. This is not implementation, runtime evidence, or final contract acceptance.

## 0. Scope and provenance

C12 left three targeted survivors:
- **D1 / S9:** missing normative state for a validated trusted acknowledgement whose atomic acknowledgement/DELIVERED commit fails or remains uncommitted after a crash.
- **D2 / S10:** missing explicit fixture for decision expiry and fresh authenticated revocation coinciding at the same final-gate time.
- **D3 / S5:** incomplete retired-fixture replacement map for `278-A56a`, omitting the detected backward wall-clock step.

Current public sources fetched before drafting:
- Entry 280 blob: `6d7d7f4966e1224456e00410c812395e6a5c598f`.
- Entry 281 blob: `46cf60a60500f942047500c3f19cced0e9beb83d`.
- Entry 282 blob: `0fa5cc1cb8f63c05c7309ec7dcb98966d738ecf3`.
- Entry 283 blob: `a9fcd0ca56c01d9118504aa77274b6737a3961c7`.
- Entry 284 current blob after the R1-C Markdown repair: `6c80ccfa8d976780fac8373a9ede80b78fe7e89b`.
- Entry 285 current blob: `778afe7ebd883e68681f066c2f5f75f30983c633`.

The coordinator fetched Entry 285 through the connected GitHub content route and verified its current blob as stated above. C12 reports that its raw-content fetch was blocked and that it read the HTML-rendered source; that access limitation is `OWNER_REPORTED` for C12's environment. Current public source text and blob IDs independently fetched here are `PROVEN_BY_SOURCE`. The C12 review and its three findings are `OWNER_REPORTED`. The repair rules and proposed fixtures in this entry are `PROPOSED`. Actual runtime, durability, timing, filesystem, and transport behavior remain `UNPROVEN`.

This amendment supersedes only the specific clauses named in §§1–3. It does not reopen Entry 284's bounded R1–R4 result. S5, S9, and S10 remain open until the entire C12 delta and its repairs pass review and are included in a subsequently consolidated, fetched-back contract.

## 1. D1 / S9 — Acknowledgement commit failure is explicit and non-replayable

### 1.1 Normative correction to Entry 285 §2.2

Amend Entry 285 §2.2, step 5, and the relevant failure clauses in step 6 as follows:

A trusted acknowledgement is not a persisted lifecycle state by itself. The only successful delivery transition is one atomic durable transaction that commits the validated acknowledgement evidence and terminal lifecycle `DELIVERED` together.

If a validated acknowledgement is known to have been received but that atomic acknowledgement/DELIVERED transaction fails, rolls back, or is confirmed not durable, set `expected_delivery_ack_status=ACK_COMMIT_FAILED` and recover the operation as `UNRESOLVED`. Retain the full reservation, halt new content-bearing operations, release no further content, and never replay the handoff automatically. The operation remains unresolved until authenticated reconciliation establishes a safe terminal state.

The audit may record a protected event that the acknowledgement was received/validated, but that event MUST NOT independently assert delivery or act as a separately durable lifecycle transition. It must not contradict the requirement that acknowledgement evidence and `DELIVERED` are committed atomically.

Define the observation point precisely:
- `ACK_COMMIT_FAILED` is expected when the trusted acknowledgement receipt is independently authenticated/available to the recovery path and the authoritative ledger evidence proves the acknowledgement/DELIVERED transaction did not commit.
- If a crash leaves the transaction outcome or the acknowledgement receipt unknowable and the trusted source cannot be queried, do not infer `ACK_COMMIT_FAILED` or `ACK_ACCEPTED` from volatile memory. Use `ACK_SOURCE_UNAVAILABLE` with lifecycle `UNRESOLVED`, unless stronger evidence requires `LEDGER_UNAVAILABLE` or `LEDGER_INTEGRITY_UNPROVEN`.
- If the atomic transaction did commit durably before the crash, the only result is persisted `DELIVERED` with `ACK_ACCEPTED`; do not label that case `ACK_COMMIT_FAILED`.

This is a field/state distinction, not an extra lifecycle stage. `DELIVERY_ACKNOWLEDGED` remains a protected audit-event name, not a member of `expected_lifecycle_state`.

### 1.2 Required D1 fixture

Add a deterministic recovery fixture for crash point `AFTER_TRUSTED_ACK_RECEIVED_BEFORE_ACK_COMMIT` with:
- `transport_ack_capability=TRUSTED`;
- a valid signed acknowledgement bound to the exact operation ID, configured recipient, handoff ID, response digest/count, authority, and event ID;
- trusted recovery evidence that the receipt is available but the atomic acknowledgement/DELIVERED transaction did not commit;
- `expected_delivery_ack_status=ACK_COMMIT_FAILED`;
- `expected_lifecycle_state=UNRESOLVED`;
- protected internal recovery state `UNRESOLVED` and reader state `HALTED`;
- reservation `COMMITTED_RETAINED`, no content redelivery, and no new intent or reservation.

The fixture must assert no content release after recovery, no second handoff, no automatic replay, and no delivery claim. The row's event sequence and state effects must show an authenticated ack observation without a durable acknowledgement/DELIVERED commit.

Add the neighboring controls:
1. Valid ack exists but the recovery source is unavailable and cannot prove receipt/commit state → `ACK_SOURCE_UNAVAILABLE` / `UNRESOLVED`; no replay.
2. The acknowledgement and `DELIVERED` committed atomically before the crash → `ACK_ACCEPTED` / lifecycle `DELIVERED`; no replay.
3. The ledger definitively rejects/rolls back the atomic commit while the authenticated acknowledgement remains available → `ACK_COMMIT_FAILED` / `UNRESOLVED`; no replay.

The manifest validator must reject these wrong tuples for the D1 fixture:
- `UNRESOLVED` + `WAITING`, because a validated acknowledgement is known to have arrived;
- `UNRESOLVED` + `ACK_ACCEPTED`, because the delivery transaction did not commit;
- `DELIVERED` + `ACK_COMMIT_FAILED`, because the durable terminal states contradict each other.

This resolves the gap in Entry 285 §§2.2–2.3 without inventing a durable intermediate lifecycle token.

## 2. D2 / S10 — Coincident decision-expiry and fresh-revocation fixture

### 2.1 Normative precedence clarification

Entry 285 §3.2 already states that when `DECISION_EXPIRED` and `DECISION_REVOKED` are independently established at the same eligible final gate, `DECISION_EXPIRED` is the selected primary internal result under R2. Add the explicit coincident-boundary test below.

The injected trusted clock is exactly the decision's expiry timestamp `Texp`. At that same instant, the final gate receives a fresh, authenticated authoritative revocation proof that positively establishes revocation; its proof age is strictly less than the configured revocation freshness TTL. The two facts are independently valid at time T. This is not the contradictory-source case where the same source evaluation is both unavailable and positively authenticated.

Because the operation was admitted while its decision was valid and the conflict is discovered at the final release gate after staging, the external requester result is the generic `REQUEST_DENIED` response for this final-gate denial; protected audit records only `DECISION_EXPIRED` as the selected primary internal result. This stage-specific public mapping applies to this staged final-gate combination; it does not replace Entry 282's mapping for a new operation initially presented with an already-expired decision.

Expected state/effects for a file-read fixture:
- `expected_internal_code=DECISION_EXPIRED`;
- `expected_result_requester=REQUEST_DENIED`;
- `expected_decision_status=EXPIRED`;
- `state_effects.decision_record=EXPIRED`;
- `expected_lifecycle_state=DISCARDED`;
- `state_effects.operation_lifecycle=DISCARDED`;
- the maximum committed reservation remains charged;
- staged bytes are destroyed or rendered inaccessible, and zero bytes are released;
- no handoff, no acknowledgement, no redelivery, and no new intent;
- final-gate audit records the independently verified fresh revocation fact as a secondary observed condition without promoting it to the primary result.

This explicit stage rule reconciles Entry 285 §3.2's R2 winner with its §3.4 final-gate denial mapping. If a future consolidated contract instead chooses to expose `DECISION_EXPIRED` publicly for this final-gate stage, it must supersede this mapping explicitly and keep the same non-oracle response policy; do not leave both outputs acceptable in the same fixture.

### 2.2 Required D2 fixture and discriminating control

Add one fixture with:
- a validly issued decision whose expiry is exactly `Texp`;
- a trusted injected clock reading exactly `Texp`;
- content already staged under a durable intent/reservation;
- a fresh, authenticated revocation proof also independently valid at T;
- final-gate R2 ordering applied without bypassing any mandatory gate.

The fixture accepts exactly:
`expected_internal_code=DECISION_EXPIRED`, `expected_result_requester=REQUEST_DENIED`, `expected_decision_status=EXPIRED`, `expected_lifecycle_state=DISCARDED`, reservation `COMMITTED_RETAINED`, content state `DISCARDED`, and no delivery.

Reject as primary-result alternatives:
- `DECISION_REVOKED`, because it loses to `DECISION_EXPIRED` in the stated R2 order;
- `REQUEST_UNAVAILABLE`, because this is not an object-dependent path/list denial;
- `CONTENT_RELEASED` or lifecycle `DELIVERED`, because final-gate failure forbids release.

The injected clock and proof timestamps must be declared in the fixture. The standalone T−1ms/T/T+1ms deadline tests remain required; this case is an additional precedence-at-coincidence fixture, not a replacement for them.

## 3. D3 / S5 — Complete the retired clock-fixture replacement map

Replace Entry 285 §1.6's incomplete mapping for `278-A56a` with this exhaustive one-to-many mapping. Every item is an independent fixture with its own fixed setup, one expected result, one observation sequence, and traceability to the retired case:
- `285-A39` — wall/monotonic elapsed-time discrepancy strictly below 2,000 ms;
- `285-A40` — discrepancy exactly 2,000 ms;
- `285-A41` — discrepancy strictly above 2,000 ms;
- `285-A42` — suspend semantics unknown or unavailable;
- `285-A43` — a detected backward wall-clock step, distinct from a mere wall/monotonic discrepancy fixture.

For all five active replacement rows, `supersedes_retired_ids=278-A56a`. The retirement cross-check must verify that the single retired ID maps to all five distinct cases and cannot treat four-of-five as complete replacement coverage.

Expected results:
- `285-A39` and `285-A40`: if suspend semantics are established and no other clock fault exists, the discrepancy alone does not expire the decision; use the positive/valid-time result appropriate to the fixture's declared stage.
- `285-A41`: `DECISION_EXPIRED` because discrepancy exceeds the 2,000 ms tolerance.
- `285-A42`: `DECISION_EXPIRED` for active decisions and pending nonces because suspend behavior cannot be established.
- `285-A43`: `DECISION_EXPIRED` for active decisions and pending nonces after any detected backward wall-clock step, regardless of the absolute step size.

The backward-step fixture must assert no content release, no revival of a decision/nonce, no fresh decision from the previous approval, and no budget reset. Its lifecycle result is determined by the stage: before operation intent the attempted operation lifecycle is `NONE`; if content was already staged, lifecycle is `DISCARDED` and the reservation remains charged; if durable outcome recording fails, recover `UNRESOLVED` and halt.

This explicit map supersedes only the `278-A56a` line in Entry 285 §1.6. It does not combine the five tests into one clock fixture.

## 4. C13 acceptance scope and residual blockers

C13 is restricted to D1–D3. The reviewer must verify:
1. D1 distinguishes a validated ack with a confirmed failed/uncommitted transaction from a committed ack/DELIVERED state and from an unknown ack-source/commit state.
2. D2 states one result tuple for expiry and fresh revocation coinciding at T, including the stage-specific requester mapping, lifecycle, retained reservation, and withheld staged content.
3. D3 explicitly maps `278-A56a` to all five separate clock fixtures and makes omitted backward-step coverage mechanically detectable.
4. The edits do not reopen R1–R4 or invent a persisted `DELIVERY_ACKNOWLEDGED` lifecycle state.

S5, S9, and S10 remain acceptance blockers until the overall delta passes review and is reflected in the consolidated contract. Even a C13 `PASS` means only that D1–D3 are textually consistent, not that the runtime, filesystem, clock, storage, or transport meets the design.

Evidence:
- `PROVEN_BY_SOURCE`: current public blobs for Entries 280–285 fetched by the coordinator.
- `OWNER_REPORTED`: C12 review narrative and its raw-fetch limitation report.
- `PROPOSED`: D1–D3 normative repairs and fixtures in this entry.
- `UNPROVEN`: all runtime and platform claims, authoritative acknowledgement availability, clock behavior, crash/power-loss durability, and M0A local state.

**Next actor: Claude/Sonnet.** Conduct one targeted C13 review of Entry 286 and only the source clauses needed for D1–D3. Do not repeat the broad C12 audit, do not reopen R1–R4 absent a specific contradiction, and do not attempt implementation. Return exactly one `PASS`, `PASS_WITH_REPAIRS`, or `FAIL`. For every survivor, specify the clause, deterministic counterexample, full result tuple, minimum repair, and discriminating fixture.

No implementation, product source/config changes, builds/tests/runtime, local M0A access, blocked-reader retry/bypass, credential inspection, authentication, installation/update/launch, or canonical-route rewrite is authorized. Entry 286 cannot grant read authority or release a governance block. `KEEP_BLOCKED`.
