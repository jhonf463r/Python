# UAAL-ROOT-001 construction-completeness overlay — traceability and omission control

- Episode: `EP-20261022-UAAL-CONSTRUCTION-COMPLETENESS-TRACEABILITY`
- Date: 2026-10-22, America/Bogota.
- Status: `DOCUMENTARY_METHOD_AMENDMENT`, subordinate to `UAAL-ROOT-001`; not a parallel algorithm.
- North Star: `GOVERNED_IABV_CODEX_BRIDGE`.
- Canonical route: [CURRENT-STATE.md](./CURRENT-STATE.md).
- Posture: `GOVERNANCE=KEEP_BLOCKED`; `IMPLEMENTATION=NOT_AUTHORIZED`; `TESTS=NOT_RUN`; `BRIDGE=BRIDGE_NOT_READY`.

## 1. Purpose and architectural fit

M1A exposed a specific construction failure pattern: a locally coherent proposal omitted important combinations, trust-chain requirements and decision-table states. The review surfaced `GLOBAL` plus mismatch across independent dimensions, missing rows, and an absent publisher/root trust/revocation chain. Its item-count summary also needed reconciliation. In addition, a general “proceed” instruction must not silently become the explicit adoption of a normative policy when the canonical ledger requires a defined acceptance decision.

The repair is not a new “space-time brain.” Apply this **completeness overlay inside the existing [UAAL-ROOT-001](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md)** loop. Reuse the [Memory Operating Protocol](./MEMORY-OPERATING-PROTOCOL.md), [Development Control Tower](./DEVELOPMENT-CONTROL-TOWER-2026-09-21.md), goal-lock/anti-drift, [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), and M0 causal-routing reconciliation. `CURRENT-STATE.md` remains the sole task-routing authority.

This is a documentary method improvement, not proof of runtime enforcement. Until a correlated run demonstrates otherwise, keep `COORDINATOR_RUNTIME=NOT_PROVEN` and `CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN`.

## 2. Construction invariant

A design is not complete because its happy path is plausible, a reviewer says PASS, or its text was saved. Every mandatory requirement must have provenance, an owner/type, a model representation or explicit exclusion, a defined result for relevant unknown/invalid states, an acceptance observation, and a truthful canonical status.

Use bidirectional traceability:

`requirement/source → assumption → rule or authority decision → decision-table row → conformance case → evidence/receipt → verdict → Knowledge Delta → later reuse`

Reverse traceability must also hold: every rule, decision, test and claim points back to its requirement/source authority and provenance. An orphan in either direction is an open completeness gap.

## 3. Mandatory construction stages, embedded in UAAL

### C0 — Restore route and baseline
Read the top routing snapshot of `CURRENT-STATE.md`, then the canonical parent/indexes and only the relevant historical records. Pin repository ref/commit and material blob SHAs. Reconcile front-door conflicts before routing work. Prior “next actor” text is historical unless the current snapshot reactivates it.

### C1 — Type the obligations
Separate: goal, requirement/invariant, source claim, derived technical rule, normative Owner/governance decision, implementation prerequisite/permission, exclusion/stop condition, and unknown/hypothesis. Derive ordinary logic from established requirements; never promote a derived recommendation into policy. A general “proceed” can authorize a bounded documentary step without adopting a separate pending policy.

### C2 — Build a traceability ledger
For every requirement/finding preserve:
- stable ID and exact source path/ref/blob SHA/line or symbol anchor where available;
- provenance (`HEAD_SOURCE`, `WORKTREE_SOURCE`, `OWNER_REPORTED`, `PROPOSED`, `NOT_FOUND_IN_BOUNDED_SCOPE`, `UNRESOLVED`, etc.);
- obligation type, dependency and affected interface/component;
- model location or explicit exclusion;
- decision-table/conformance cases;
- evidence/receipt required to close it;
- status and re-entry condition.

Counts must reconcile with the ledger. Findings, design repairs, governance decisions, acceptance cases and evidence prerequisites are different categories; never sum them as interchangeable votes. Keep original proposals/reviews immutable.

### C3 — Define the state space before drafting rules
Identify all independent dimensions and each dimension's source of truth. Distinguish valid mismatch from missing, partial, malformed, unknown, ambiguous, conflicting, stale, revoked, unauthorized and unsupported inputs. Separate an identity assertion from verified identity and from authority. Specify defaults, aliases, legacy handling, versioning, integrity and revocation. Define safe results and aggregation semantics for every relevant state. Reuse authoritative existing contracts; if none exists in the bounded authorized source set, record the gap instead of inventing a trusted registry.

### C4 — Close decision-table coverage
Enumerate the meaningful combinations before declaring completion. For M1A this includes:
- `GLOBAL`/`EXACT` per independent selector and both-match/mismatch-in-either/multiple-mismatch cases;
- missing/partial/malformed/unknown selectors and alias conflicts;
- caller-asserted scope versus trusted server-side target resolution;
- unsupported or mixed policy versions, revoked catalogue and invalid integrity;
- unauthenticated/unauthorized producer;
- legacy schema versus recognized-but-incomplete record;
- every active block, independent release/no-release, deterministic aggregation and order independence;
- diagnostic evaluation/receipt versus actual authority.

For another domain, build its analogous state space. Use exhaustive combinations when bounded; otherwise document the coverage-reduction rationale and omitted cases. Every rule needs a positive case and, where applicable, a counterexample/denial/unknown case. Every review finding gets a disposition. A sample of happy paths is not proof of exhaustive coverage.

### C5 — Separate authority planes
Label every material statement as one of:
`DERIVED_TECHNICAL_RULE`, `OWNER_GOVERNANCE_DECISION`, `IMPLEMENTATION_ACCEPTANCE`, `OPERATIONAL_VERIFICATION`, or `RELEASE_AUTHORITY`.
For authority-critical data, record who may decide, how their identity is authenticated, which artifact records the decision, its scope/lifecycle, revocation and what remains blocked without proof. A digest, static PASS, reader receipt or “owner responsible” sentence does not prove a runtime trust anchor. Approval/evaluation evidence must not become a transferable permission or release authority.

### C6 — Select the causal frontier
Describe each candidate action's inputs, permission, dependency edge, smallest discriminating observation, expected receipt, acceptance criterion and stop condition. Choose the earliest unresolved edge materially blocking the North Star, not the latest topic. Keep one active task. If a route is unavailable, record a bounded `NOT_FOUND` or `UNRESOLVED`, stop repeating it, and continue only a distinct directly relevant action that is currently authorized.

### C7 — Pre-construction gate
Before independent review or an actor handoff, verify:
- every requirement maps to a rule or explicit exclusion, and every rule maps back to a source/requirement;
- independent dimensions, trust boundaries and failure/unknown states are represented;
- decision-table coverage is evidenced;
- all findings have unique IDs, reconciled counts and explicit dispositions;
- technical derivations are not smuggled in as normative defaults;
- versioning, integrity, publisher/producer authority and revocation are addressed where relevant;
- no receipt is misrepresented as authority;
- route/indexes do not point to stale next actors;
- baseline, boundaries, acceptance and stop conditions are explicit;
- design authority is not mistaken for permission to implement/test/run/transport/merge/release.

If an applicable mandatory item fails, report `DESIGN_INCOMPLETE` with exact gaps; do not downgrade a blocker to vague “clarification.”

### C8 — Bounded handoff
Every agent prompt names the exact destination/session (or `NOT_DISPATCHED`), task ID, mode/authority, source baseline, bounded paths, in/out of scope, expected response schema, artifact/commit/blob or correlated receipt, acceptance criteria, stop conditions and return route. Never claim invocation, source access, tests or runtime unless its receipt exists. Prefer a delta review over another general review.

### C9 — Reconcile against the original request
Compare the returned artifact row-by-row with C2, not only on its own terms. Check source identity, coverage, scope/exclusions, counterexamples, policy/implementation boundary, arithmetic/counts, IDs/versions and provenance. A PASS applies only to the named artifact/baseline/scope. A partial PASS does not close neighboring findings or runtime gates. Preserve prior artifacts and document the exact delta.

### C10 — Persist, fetch back and reuse
After a material write, update the artifact and only relevant canonical pointers; fetch the committed content back; verify path, blob SHA, key contents and links; record commit/blob identity and claim scope; write the Knowledge Delta with what closed/changed, remaining dependency, failed route and re-entry condition. On the next applicable decision, explicitly apply that delta. Merely saving text is not causal learning.

## 4. Failures in this episode converted to controls

| Failure mode exposed | Mandatory prevention | Closure evidence |
|---|---|---|
| Cross-dimension selector combinations omitted | Enumerate the Cartesian state space of independent selectors; define unknowns separately | Full decision table and discriminating cases |
| Trust chain/publisher/revocation omitted | Track policy owner, authenticated publisher/trust root, authorized producer, integrity/version lifecycle and revocation as distinct requirements | Named authority and contract; runtime identity still a separate gate |
| Caller metadata mistaken for trusted identity | Track provenance and resolve target on trusted server-side path | Source/call-site contract, then separately authorized verification |
| Order/short-circuit hides an active block | Account for every active block and define deterministic aggregation | Order-independence and unevaluable-block cases |
| Receipt/evaluation confused with permission | State evidence-only, non-bearer, non-release semantics | Link to Entry 274 and explicit contract clause |
| Legacy absence confused with malformed known schema | Separate legacy/unknown schema from required-field omission in a recognized schema | Version/parsing table and cases |
| Report tally contradicted itemization | Maintain unique IDs and separate counts by record type | Ledger reconciliation |
| General “proceed” confused with policy acceptance | Preserve exact normative acceptance gate; continue only work independently authorized | Explicit decision receipt; pending policy stays pending otherwise |
| Documentation confused with execution/learning | Distinguish `DOCUMENTED`, `WIRED`, `INVOKED`, `OBSERVED`, `VERIFIED`, `CAUSAL`, `REUSED` | Evidence correlated to each claimed level |

## 5. Acceptance criteria

A construction cycle can be called complete only when: (1) no orphan requirement/rule remains; (2) important match, mismatch, invalid, unknown, conflicting, unauthorized and revoked states are covered; (3) technical derivation, governance, implementation, operations and release are separated; (4) the action closes a real dependency within authorization; (5) handoff and stop criteria are explicit; (6) returned artifacts reconcile with the original request; (7) canonical write is fetched back and identified; and (8) the Knowledge Delta is later reused before claiming causal learning.

Stop repetitive review/scan loops when only an unavailable authority/receipt remains. Do not compensate with speculative registries, broad scans, repeated general reviews or new document versions that do not close a new edge.

## 6. Current application and non-escalation

This amendment does **not** accept the M1A proposal on the Owner's behalf and does not authorize implementation or release. It only records a stronger construction method.

```text
PARENT_CONCEPT=UAAL-ROOT-001
OVERLAY=CONSTRUCTION_COMPLETENESS_TRACEABILITY
STATUS=DOCUMENTED_METHOD
RUNTIME_ENFORCEMENT=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
M1A_SCOPE_POLICY=PROPOSED_NON_AUTHORITATIVE
OWNER_GOVERNANCE_DECISIONS=OG-M1A-01..OG-M1A-07_PENDING
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

Related parents: [UAAL-ROOT-001](./UNIVERSAL-ADAPTIVE-ALGORITHM-CONSTITUTION-2026-10-04.md), [Memory Operating Protocol](./MEMORY-OPERATING-PROTOCOL.md), [CURRENT-STATE.md](./CURRENT-STATE.md), [Control Tower](./DEVELOPMENT-CONTROL-TOWER-2026-09-21.md), [goal-lock/anti-drift](./CHAT-ARCH-2026-10-20-protocol-anti-drift-and-bridge-goal-lock.md), [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), [M1A normalized decision ledger](./CHAT-ARCH-2026-10-22-M1A-normalized-scope-decision-ledger-and-design-amendment.md).
