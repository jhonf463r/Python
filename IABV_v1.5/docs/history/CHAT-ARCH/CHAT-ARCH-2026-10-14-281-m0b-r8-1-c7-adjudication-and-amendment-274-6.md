# CHAT-ARCH-2026-10-14-281 — C7 adjudication / amendment 274.6

- Status: `M0B_R8_1_AMENDMENT_274_6_PROPOSED_PENDING_TARGETED_DELTA_REVIEW`
- Operational posture: `KEEP_BLOCKED`
- Type: documentary amendment proposal, not a consolidated/accepted contract.

## 0. Verdict conflict and provenance

The supplied C7 material contains two conclusions about Entry 280: an earlier section says `PASS_WITH_REPAIRS`; a later detailed section says `FAIL) and lists H1–H12. These must not be merged into one settled verdict. Record `REVIEW_OUTPUT_CONFLICT); conservatively, Entry 280 is not accepted and H1–H12 remain repair requirements until one normalized delta verdict is produced.

Current GitHub file retrieval verified:
- Entry 278 blob: `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`.
- Entry 279 blob: `fccd67f375c265986215210b5161e684c65b7e27`.
- Entry 280 blob: `6d7d7f4966e1224456e00410c812395e6a5c598f`.
- Commit `0a462d66071f2d354e8a299ffaf859b3aeac61d5) was fetched separately and its message identifies an Entry 280 document update.

A blob SHA and commit SHA are different Git object types and are not expected to match. The current Entry 280 blob identity is verified by this connector; historical equivalence of embedded Entry 274–277 clauses and runtime behavior remain unproven.

## 1. H1–H2 — Anti-rollback and fixture reconciliation

Do not infer rollback merely because a required epoch is absent from an anchor.

- A readable epoch provably lower than or inconsistent with an authenticated value actually present in the anchor: `REGISTRY_ROLLBACK`.
- A missing/truncated registration where the anchor proves a previously committed state or establishes a violated minimum epoch: `REGISTRY_ROLLBACK`.
- Anchor schema/coverage for a required epoch category absent, malformed or unauthenticated: `LEDGER_INTEGRITY_UNPROVEN`.
- Valid anchor explicitly proves a genuinely new workspace has never been registered, but required registration/scope evidence is missing: `BLOCK_SCOPE_UNEVALUABLE`.
- Current, anchor-consistent epochs but an unsupported scope dimension: `BLOCK_SCOPE_UNEVALUABLE`.

R1-protected epochs include workspace/checkout registration, lineage and tombstones; active-block set/revision; scope-model version; Owner trust/credential lifecycle; revocation-source identity/version; and protected destination/recipient configuration.

Retire or split conflicting fixtures. A stale block/scope-model epoch below the anchor is `REGISTRY_ROLLBACK), not `BLOCK_SCOPE_UNEVALUABLE). A revocation-source version below anchor is `REGISTRY_ROLLBACK); a current version with stale, missing, unauthenticated or unavailable freshness proof is `REVOCATION_UNAVAILABLE).

## 2. H3/H5 — Complete public/internal result mapping and schema

The next consolidation must give an exhaustive mapping from the 17 ordered internal results to requester-visible results. At minimum:
- `APPROVAL_PENDING`: before the fixed approval-window endpoint.
- `REQUEST_UNAVAILABLE`: uniform public response for object-dependent path/list/scope outcomes and requests lacking a usable decision at the endpoint.
- `DECISION_NOT_APPLICABLE`: unknown decision ID or authenticated but mismatched decision binding.
- `REQUEST_DENIED`: other denials whose specific cause must not be exposed.
- `DECISION_ISSUED`, `CONTENT_RELEASED), `STATUS_RETURNED) and `DIAGNOSTIC_COMPLETE_NO_DECISION): only for their defined stages.

Never place an internal code such as `PATH_SCOPE_UNAVAILABLE) in the requester-result field when the public result must be `REQUEST_UNAVAILABLE).

Every fixture must have fixed setup, ID, status column, probe request, evaluation stage, expected requester result, expected internal code, decision status, lifecycle status, stage-specific validator result, observation sequence, equivalence group, state effects, classification, oracle type and traceability. Probe types must include initial request, diagnostic-only, issuance retry, operation retry, status query, new operation, crash recovery, approval attestation and nonce replay.

Decision status must distinguish `NONE) (no record), `NOT_APPLICABLE) (field does not apply), `PENDING_VISIBILITY), `ACTIVE), `EXPIRED), `REVOKED) and `INVALID). Lifecycle state is a separate enum. Diagnostic-only fixtures use `DIAGNOSTIC_COMPLETE_NO_DECISION) and internal code `NONE). Grammar/manifest validation use a validator-result field, not a transport state. Recovery while halted uses public `REQUEST_DENIED) and internal/lifecycle `UNRESOLVED).

Reject blank fields, unknown per-field enums, compound setups, slash/or alternatives, duplicate IDs and equivalence tests lacking a declared observation sequence/comparison rule.

## 3. H4/H7 — Event timeline and fixed public window

Define E0 request acceptance at trusted time T0 and a fixed public window ending at T0+120 seconds. Safe preview/binding is an internal subphase during that window, not a separate public clock interval. Show the Owner prompt even if the scope cannot safely be approved; that fact stays in the protected Owner interface/audit.

When valid approval and a safe binding exist, issue a hidden durable decision within the approval freshness limit. Set `not_before = T0+120s), and start the usable decision lifetime at `not_before). Before the endpoint the requester always sees `APPROVAL_PENDING), regardless of Owner action. At the fixed endpoint publish `DECISION_ISSUED) only if the hidden decision, binding and policy remain valid; otherwise return `REQUEST_UNAVAILABLE). Rejection, no response, late approval, invalid nonce or unbindable target yields no usable decision. Late approval is internally `DECISION_EXPIRED) and publicly `REQUEST_UNAVAILABLE).

A safely bound object replaced before open yields internal `CONTAINMENT_UNPROVEN); an object never safely bound yields internal `PATH_SCOPE_UNAVAILABLE). The public mapping remains uniform. The Owner-choice side channel remains `UNPROVEN).

The final gate must re-evaluate current ledger/integrity/recovery, every protected epoch, identity/session/decision binding, path and object containment, block scope/release, expiry, revocation and the existing budget reservation before release. Do not reserve twice. Apply the full R2 order to bounded findings. An unresolved prior intent blocks new reads.

## 4. H6 — Atomic operation idempotency and status queries

The operation key is `(decision_id, authenticated_requester_agent_principal, authenticated_requester_session, client_operation_token)). One durable atomic transaction must commit the key, server operation ID, canonical-argument digest, `INTENT_COMMITTED) and budget/probe reservations. No partial key/intent/reservation may survive a failed transaction.

Decision records include authenticated boot generation, `not_before), expiry and all required caps. `EXPIRED) is derived from trusted time, expiry and boot-generation evidence; do not guess if required state cannot be read or authenticated.

A status query for an exact authenticated key with a verified terminal operation record may return `STATUS_RETURNED) even while a different unresolved operation halts new reads. It returns no content and creates no new intent or reservation. Unknown/mismatched keys do not bypass R2 gates 1–4. An unreadable operation record yields `LEDGER_UNAVAILABLE); an integrity failure yields `LEDGER_INTEGRITY_UNPROVEN). If a terminal operation record is authenticated but its decision record is unavailable, a metadata-only query may return the terminal operation state with decision status `NOT_APPLICABLE). A new operation token with an expired decision yields `DECISION_EXPIRED) without a new operation/reservation.

## 5. H8/H10 — Identity mismatch versus corrupt decision state

An independently authenticated requester using a decision bound to another principal/session/workspace/target gets `DECISION_NOT_APPLICABLE); the rightful owner's decision stays valid. If the process/agent cannot be distinguished or a copied bearer token is the only proof, select `APPROVAL_CHANNEL_UNTRUSTED).

An unknown ID in a healthy ledger is `DECISION_NOT_APPLICABLE), not `LEDGER_INTEGRITY_UNPROVEN). A present issued decision record that lacks a mandatory cap or violates its authenticated schema is `LEDGER_INTEGRITY_UNPROVEN), halts reads and requires reconciliation. The issuer must not emit a decision without every mandatory ceiling. `LEDGER_UNAVAILABLE) covers required durable reads and writes.

Split the historical unknown-ID fixture from cross-principal misuse, copied-token misuse and malformed decision-schema fixtures.

## 6. H9/H11 — Listing and probe budgets

For a list operation, validate ledger, identity and root containment first. Then count actual entries without following/resolving links, excluding exact `.` and `..`. Stop at effective cap plus one. If overflow is observed, `LIST_LIMIT_EXCEEDED) wins regardless of an invalid/reparse entry's enumeration position and no names are disclosed. At or under cap, validate every entry and deny the entire listing for any unsafe entry.

The detection allowance is per operation, not a shared global or cross-session pool. Atomically reserve one bounded detection attempt with the intent/reservation: one cap+1 read attempt for a file, or one cap+1 actual-entry observation for a list. Exact-cap and cap+1 cases consume one attempt and charge the same maximum deliverable reservation; never disclose the sentinel and never use unbounded lookahead. Failure to reserve the operation/probe allowance returns `BUDGET_EXCEEDED) before content I/O.

Concurrency tests must force the ledger commit order for deterministic winners. The invariant across bounded schedules is that reservations never exceed available budgets and each operation uses at most one probe attempt.

## 7. H12 — One manifest and parser for the whole artifact

The next consolidated contract must contain one contiguous active Markdown manifest table. Historical fixture suggestions from Entries 279/280 are to be preserved as prose/quoted records in the consolidated document, not as additional pipe-delimited test tables.

Use a separate normalized `qualified_id) column and `status) column with `ACTIVE) or `RETIRED). IDs contain a three-digit entry number, `-A), one or more digits and an optional lowercase suffix; status never appears in the ID. Declare the row count immediately before the table.

The parser scans the entire artifact, not just the table, for row-like qualified IDs. Acceptance requires parsed table rows = all row-like IDs = declared row count; IDs unique after normalization; valid status and complete fields on every active row; no orphan rows or unescaped pipes.

Required negatives: a 62-row table plus 44 orphan IDs despite declared count 62; the same ID active and retired; an unescaped pipe in a cell; duplicate IDs distinguished only by appended status. Each yields `MANIFEST_INVALID). Add one valid single-table fixture.

## 8. Residual acceptance blockers

These remain open and MUST be resolved before accepting a consolidated contract:
- **S5:** split remaining compound fixtures and add each rejected lexical class, all crash boundaries, root/path replacement, in-place concurrent writer, and valid sensitive-name pre-approval coverage; confirm retired tests have sufficient replacements.
- **S9:** define an authenticated acknowledgement source outside requester control, bound to operation ID, recipient and response digest; specify recovery for both transport-without-ack and trusted-ack modes; define the durable transition between `DELIVERY_ACKNOWLEDGED) and `DELIVERED).
- **S10:** enumerate adjacent-gate and final-gate precedence pairs; test every relevant time limit at T−epsilon, T and T+epsilon; include final-gate `DECISION_REVOKED) with staged content; ensure the suite rejects deny-all behavior.

## 9. Evidence and next step

- `PROVEN_BY_SOURCE): current public documents and blob SHAs fetched in the coordinator session; separate metadata for the Entry 280 update commit fetched.
- `OWNER_REPORTED): the supplied conflicting C7 review blocks and earlier M0A reports.
- `PROPOSED): all repairs and tests in this entry.
- `UNPROVEN): exact historical fidelity to all Entry 274–277 blobs unless each is re-fetched and compared; every runtime/platform claim; local M0A identity; Owner/requester isolation; actual anti-rollback enforcement; filesystem containment; revocation freshness; trusted delivery acknowledgement; production block-scope semantics; supported governance-owned release.

**Next actor:** Sonnet/Claude. Review Entry 280 plus Entry 281 only. Normalize the conflicting verdicts and issue exactly one `PASS), `PASS_WITH_REPAIRS) or `FAIL). Confirm H1–H12 repairs and retain S5/S9/S10 as acceptance blockers. No broad source archaeology.

No source implementation, product configuration edits, tests/builds/runtime, local M0A access, credential inspection, authentication, installation/update or launch is authorized. Contract review cannot grant repository-read authority or release a governance block. `KEEP_BLOCKED`.
