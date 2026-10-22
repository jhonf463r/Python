# Central space-time coordinator — M1A reconciliation and operating correction

- **Episode:** `EP-20261022-CENTRAL-COORDINATOR-M1A-RECONCILIATION`
- **Date:** 2026-10-22, America/Bogota.
- **Type:** architecture / coordination-method correction; documentary only.
- **Owner clarification:** the intended coordinator is not a passive reviewer that returns every design ambiguity to the Owner. It should restore the global objective and history, model dependencies, infer the next logically justified construction step, coordinate the appropriate actor, reconcile its evidence, persist the causal delta, and reuse it.
- **Canonical route authority:** [CURRENT-STATE.md](./CURRENT-STATE.md). This document records the reasoning and recommended next step; it does not itself authorize code execution or release any governance block.

## 1. The Owner's architectural analogy, made operational

The Owner describes a central “space-time brain” that sees the whole construction, understands how each part depends on the others, and activates the next valid continuation like a domino chain. Individual components are like scaffolding, temporary training wheels, or construction machinery: they may help construct and validate the system, but the coordinator must preserve the architecture and understand which interfaces and authorities remain separate after construction.

The coordinator's job is therefore not to take the latest local defect as a self-contained topic and then ask the Owner to design every repair. It must:
1. Restore the north star, current route, prior decisions, failed approaches, evidence provenance and exclusions.
2. Represent the project as a dependency graph with explicit preconditions, outputs and acceptance conditions.
3. Find the earliest unresolved edge that blocks the current outcome, not merely the most recently discussed defect.
4. Derive the best candidate repair from the existing normative contract and the simplest coherent model.
5. Separate technical deductions that the coordinator can make from authority choices that must remain with the authorized Owner/governance.
6. Route only the bounded work to the correct actor/tool; do not invent that an unavailable actor was invoked.
7. Compare the returned artifact/receipt with the original request and acceptance criteria.
8. Reconcile the decision delta, update canonical continuity, and later demonstrate reuse by avoiding a known loop or making a changed decision for a documented reason.

This is a causal coordination process:
`objective/context → evidence/provenance → current frontier → hypotheses and constraints → authorized next action → observation/receipt → reconciliation → durable decision delta → reuse`.

A documentary note alone does not prove that a persistent autonomous runtime brain exists. The coordination protocol already distinguishes `DOCUMENTED` from `COORDINATOR_RUNTIME=NOT_PROVEN` and `CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN`. The coordinator must embody the documented method in its own available workflow now, and must not pretend background autonomous execution or cross-model dispatch exists where no tool proves it.

## 2. Correction to the preceding M1A interaction

The recent handling treated selector semantics too much as a ballot to send back to the Owner. That was the wrong order. The coordinator should first derive and state the coherent candidate semantics from the existing Entry 274 contract, test the decision table against them, and expose only any genuinely irreducible governance decision.

The Owner should not be asked to resolve ordinary logical consequences that can be derived from a formal model. Conversely, the coordinator must not turn a useful technical deduction into current authority by declaration. Keep three layers separate:
- **Derived technical recommendation:** the most coherent formal rule under the existing constraints.
- **Normative acceptance:** an authorized Owner/governance decision where the policy or principal/authority is genuinely theirs to decide.
- **Implementation authority:** always a separate explicit gate; a policy design/review does not authorize code, tests, runtime, transport or block release.

## 3. Recommended formal semantics for the two selectors

This is a **coordinator-derived design recommendation**, not adopted policy.

Assume a block constrains two independent dimensions: an assistant identity and an operation/target-scope identity. Each field constrains only its own dimension. Their combination is the intersection (conjunction) of those two constraints.

Definitions for a well-formed, trusted, fully resolved evaluation:
- `GLOBAL` matches every valid value of **that dimension only**. It does not make the entire block global if the other selector is `EXACT(...)`.
- `EXACT(x)` matches only when the trusted, canonical target ID for its dimension equals the registered canonical ID `x`.
- A block applies only when both dimension selectors match.
- If both the block metadata and trusted target identity are complete, valid, version-compatible and internally consistent, a known `EXACT` mismatch in either dimension proves the target lies outside the block's intersection. It can therefore produce `PROVEN_NOT_APPLICABLE`, whether the other selector matches, also mismatches, or is `GLOBAL`.
- A known mismatch is **not** enough to prove non-applicability if the block itself is incomplete, malformed, untrusted or internally contradictory, or if catalogue/version/identity resolution is unavailable. Those conditions produce a specific fail-closed indeterminate/denial result instead.

Consequently, these cases are coherent under the recommended conjunction:
| Assistant selector | Target selector | Trusted target | Per-block result (only if all fields/catalogue/versions are valid) |
|---|---|---|---|
| `GLOBAL` | `GLOBAL` | Any valid assistant + target | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | Assistant is `a` | `BLOCK_APPLIES` |
| `EXACT(a)` | `GLOBAL` | Assistant is not `a` | `PROVEN_NOT_APPLICABLE` |
| `GLOBAL` | `EXACT(t)` | Target scope is `t` | `BLOCK_APPLIES` |
| `GLOBAL` | `EXACT(t)` | Target scope is not `t` | `PROVEN_NOT_APPLICABLE` |
| `EXACT(a)` | `EXACT(t)` | Both match | `BLOCK_APPLIES` |
| `EXACT(a)` | `EXACT(t)` | Either one mismatches | `PROVEN_NOT_APPLICABLE` |
| Any selector absent, malformed, unknown or based on unresolved/conflicting identity | Any | Incomplete/untrusted | Fail closed; never infer non-applicability |

That formalization resolves the proposal's odd row (“one dimension differs while the other matches” → `BLOCK_SCOPE_UNEVALUABLE`) without pretending that `GLOBAL` covers both dimensions. A partial *valid mismatch* is not intrinsically contradictory if the dimensions are independent conjunctions. The row should be separated from genuine *incomplete or conflicting metadata*, which remains unevaluable and blocking.

However, this recommendation depends on the model truly intending two independent conjunctive selectors. If an authoritative pre-existing contract defines a different relationship, that source prevails. No such authoritative/versioned model was found in the bounded source set used in M1. Accordingly, the coordinator may recommend this rule but must label it `PROPOSED` until formally adjudicated; it must not silently wire it into source.

## 4. Fail-closed trust and decision aggregation

The formal selector rule is only one layer. It must not make a forged block or untrusted target authoritative.

- Missing/unsupported/revoked model or policy version, catalogue integrity/signature failure, ambiguous alias, unknown selector ID, missing selector, unauthorized producer, contradictory provenance, or unresolved operation-to-target mapping cannot be treated as `PROVEN_NOT_APPLICABLE`.
- `producer_id` is an identity claim, not proof of authority. The evaluator must validate the producer against an authorized issuer/producer policy.
- A digest proves which bytes were hashed; it does not identify who authorized those bytes. A catalogue needs an established trust anchor, version/lifecycle rules and revocation path. The responsible authority/principal and revocation mandate are genuine governance decisions; the signature mechanism and validation design are technical work once that authority is specified.
- Caller-supplied `operation_scope` cannot establish the trusted target. The server-side resolver derives the operation-to-target mapping; the caller's value is ignored for the authoritative decision (it may only be compared separately for anomaly telemetry).
- Every active block must be accounted for. Preserve each per-block evaluation and deny if any active block applies without an independent valid release, or any block cannot be safely evaluated. A diagnostic `BlockEvaluation` or receipt is evidence, never a transferable permission or block release.
- A read approval cannot release its own governance block. Block release remains a separate artifact from its independently established authority, consistent with Entry 274.

The final aggregation must be deterministic and must not allow record order or short-circuit evaluation to hide an unevaluable block. Where multiple denial reasons exist, preserve them all in the audit result; do not force a single status-code precedence without defining it in the revised contract.

## 5. What belongs to the coordinator vs. what belongs to Owner/governance

**Coordinator should derive, document and verify:**
- the formal interpretation of selector operations and decision-table completeness;
- the separation between a valid mismatch, incomplete metadata, unknown identity, unsupported version and unauthenticated source;
- deterministic evaluation/aggregation and the conformance cases required to discriminate those states;
- how a trusted resolver and server-side evaluation must interact, without using caller-supplied scope as authority;
- the dependency order, evidence ledger, exact task handoff and acceptance conditions.

**Owner/governance must decide or explicitly delegate:**
- who is the authoritative catalogue/policy owner and which identity can approve its versions;
- the authorized issuer/producer population and trust root (or the governance mechanism that names them);
- who can revoke a catalogue/policy version and who may independently release a governance block;
- whether to adopt the recommended selector semantics as normative policy, or point to another already authoritative semantic contract;
- when/if implementation, tests, runtime, transport or release are separately authorized.

Do not report every item under the second heading as an unstructured list of “11 decisions.” Reconcile the existing proposal §G into a normalized ledger, merge duplicates, and distinguish decisions from evidence requirements and engineering acceptance tests. The supplied Sonnet-attributed report contained an internal counting inconsistency; its count must not be reused without reconciliation.

## 6. Next continuation

The correct next action is coordinator-led documentary reconciliation of M1A:
1. Keep the original Codex proposal and the independent-review report immutable as evidence.
2. Use this document as the proposed technical resolution for the selector-semantics ambiguity.
3. Normalize the decision ledger into (a) derived repairs, (b) Owner/governance authority decisions, and (c) implementation prerequisites.
4. Produce one bounded amended design only after the Owner has authorized that documentary transition, or after the route is explicitly updated to authorize it.
5. Send the revised design for independent review only if the amendment makes a material policy or security change; do not repeat a broad review of already settled facts.
6. Do not implement, run tests/build/runtime, inspect the local checkout, use real transport, merge or release any block under this task.

The operational posture remains `GOVERNANCE=KEEP_BLOCKED`, `IMPLEMENTATION=NOT_AUTHORIZED`, `TESTS=NOT_RUN`, `READ_LIST=FAIL_CLOSED`, `BRIDGE=BRIDGE_NOT_READY`.
