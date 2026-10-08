# CHAT-ARCH 2026-10-08-162 — RQ21.45 OWNER DECISION

## 1. Provenance / authority

RQ21.45 was presented as the explicit decision frame after RQ21.44A.
The user explicitly instructed the coordinator to follow the supplied RQ21.45 decision and continue from it. This record therefore treats the five decisions below as **owner-adopted for IABV routing**, while preserving the distinction that code implementation remains a separate later act.

Source decision:
- Machine ID: A1 — new separate ID
- E/X: CONFIRMED
- Task boundary: C1 — dedicated validation-step boundary
- Evidence acquisition: CONFIRMED
- Negative semantics: CONFIRMED

No executable source, runtime or tests are authorized by this record.

## 2. Input state

RQ21.44A = PASS WITH BOUNDED REPAIRS / READY FOR MINIMAL CODE CONTRACT.

Executable baseline remains:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

Semantic capability under adjudication:
`C_SANDBOX_DYNAMIC_VALIDATION`

## 3. Decision A — machine-readable identity

**A1 — new ID separate**

Authorized machine identity:
`capability.sandbox.dynamic_validation`

Meaning is limited to:
> dynamically evaluate a candidate under containment of protected effect set E against expected behavior X, producing observable and interpretable validation evidence.

The identity excludes:
- readiness;
- availability;
- locality;
- mechanism;
- provider;
- adapter;
- permission/governance state.

The existing IDs remain non-equivalent:
- `tools.local.sandbox` = readiness/inventory-oriented precondition;
- `tools.local.execution` = execution/availability precondition;
- `tools.local.registry` = inventory/discovery precondition.

No existing readiness ID is repurposed.

## 4. Decision B — E/X

**CONFIRMED**

Task/validation envelope inputs:
- `candidate`
- `X` = expected behaviour specification
- `E` = protected effect set

Semantic chain:
`candidate + X + E → dynamic execution under containment → observed behaviour + protected-effect evidence → validation result`

E and X are task/validation inputs, not capability identity.

No universal envelope subsystem is introduced by this decision.

A realization is eligible for a concrete task instance only when it can satisfy the relevant E/X constraints.

## 5. Decision C — task boundary

**C1 — validation-step boundary**

The first implementation slice is a dedicated validation step/task whose requirement is:

`R_task = {capability.sandbox.dynamic_validation}`

That capability is sufficient for the success predicate of that validation step only.

It is NOT sufficient by implication for arbitrary composite work involving:
- generation;
- deployment;
- modification;
- general execution;
- approval;
- other independent capabilities.

Those remain separately representable/composable.

## 6. Decision D — evidence acquisition

**CONFIRMED**

Strict separation:
`eligibility evidence ≠ governed capability test/acquisition`

A realization lacking prior evidence:
- does not become eligible merely because it declares the capability;
- may enter a governed capability-test/acquisition path.

A test can produce future eligibility evidence, but:
- declaration ≠ evidence;
- execution ≠ proof.

Evidence of the complete capability must establish the functional predicate, including behavioural agreement with X and preservation/protection of E.

The acquisition path must not weaken the hard eligibility invariant.

## 7. Decision E — negative semantics

**CONFIRMED**

Required invariants:

`KNOWN demand + eligible set = ∅ → governed negative`

and:

`KNOWN demand + requested tool_id unresolved → governed negative`

No automatic transition to:
- lexical fallback;
- family fallback;
- first-card fallback;
- unconstrained registry selection.

A constrained demand cannot be silently deleted to recover a realization.

## 8. Reconciled contract

The current contract is:

`semantic capability → machine identity → pre-selection demand → realization declaration → evidence/readiness/governance + E/X coverage → eligibility → governed selection → dynamic validation → evidence or governed negative`

The following distinctions remain mandatory:

`semantic capability ≠ machine identity`
`machine identity ≠ realization proof`
`declaration ≠ evidence`
`eligibility ≠ acquisition/test`
`readiness ≠ capability identity`
`ToolTask ≠ demand source`
`R_task={C} ≠ universal whole-task sufficiency`

## 9. Implementation status

**Implementation is not performed by RQ21.45.**

The semantic/contract decision gate is now closed enough to prepare the final implementation prompt.

Next actor:
**CODEX**

Next capability:
implementation of the bounded capability-demand/realization contract against the pinned executable baseline.

Required post-implementation step:
independent adversarial verification before any runtime proof.

## 10. Knowledge Delta

- The owner-adopted machine identity is now explicitly separate from readiness vocabulary.
- E/X are confirmed as task/validation envelope inputs.
- The first slice is explicitly a validation step, preventing accidental universal sufficiency claims.
- Capability evidence acquisition is governed as a separate path from eligibility.
- Negative semantics cover both empty eligibility and unresolved explicit realization.

## 11. Method Delta

- A closed semantic contract must be converted into a machine identity by explicit owner authorization, not inference.
- Evidence-bootstrap problems must be solved with a governed acquisition path, never by weakening eligibility.
- First-slice boundaries must be explicit so a single capability cannot masquerade as a composite workflow contract.
- Negative paths are part of the capability contract, not implementation afterthoughts.

## 12. Routing Delta

Current first open edge:
`owner-adjudicated capability contract → minimal executable implementation → independent verification`

Next actor:
**CODEX**

Why:
- source/implementation capability-fit;
- semantic decisions are now closed;
- remaining uncertainty is bounded implementation wiring rather than domain meaning.

No runtime is the next action. Runtime becomes relevant only after implementation and independent static verification.

## 13. Epistemic boundary

FACT:
- RQ21.44A was independently verified as a bounded code contract.
- The five RQ21.45 decisions are the owner-adopted decision set for this routing cycle.

INFERENCE:
- the implementation can now be specified without reopening the capability meaning.

UNPROVEN:
- implementation correctness;
- realization declarations actually satisfying the capability;
- runtime containment;
- observed validation against X;
- causal/learning effects.

## 14. Stop condition

Do not reinterpret the semantics during implementation.
Do not repurpose readiness IDs.
Do not create a new universal router/registry.
Do not claim runtime or capability proof from code presence alone.
