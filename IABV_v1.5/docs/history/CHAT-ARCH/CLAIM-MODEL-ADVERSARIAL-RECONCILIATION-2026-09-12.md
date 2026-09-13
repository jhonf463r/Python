# IABV v1.5 — Claim Model Adversarial Reconciliation

## STATUS

**State:** RECONCILED AFTER DEVIN ARCHAEOLOGY + CLAUDE ADVERSARIAL REVIEW
**Date:** 2026-09-12

## PROCEDURAL PROVENANCE FINDINGS

- The repository `main` is mutable during this investigation; other processes/sessions may push canonical memory commits while an auditor is working.
- Therefore future audits MUST record the exact `main` HEAD/commit used for source inspection and distinguish it from later memory-only commits.
- Conceptual field proposals from prompts/reports are `REVIEWED` evidence until present in source; they must not be treated as canonical code artifacts.
- `verify_intent_routing()` is a module-level function using hardcoded cases and substring matching, not a general AST contract engine. It is a weak/partial architectural precedent.

## CURRENT CONVERGED INTERPRETATION

The project has converged on a smaller hypothesis:

> A generalized cross-organ integrity capability needs a representation of a relation/invariant that can point to existing evidence, without duplicating all observation, diagnosis or reconciliation data.

The previous two-model proposal (`Expectation` + `Contract` + `VerificationResult`) was judged over-modeled.

The adversarial review proposed a single minimal conceptual record, tentatively called `Claim`, containing approximately:

- subject/reference to the relevant code or relationship;
- invariant/relationship to be tested;
- epistemic status (`FACT | INFERENCE | ASSUMPTION`), separate from confidence;
- confidence as evidence strength, not truth status;
- evidence reference(s) to existing runtime/source/test records, not duplicated payloads;
- verification status (`PASS | FAIL | WARN | UNKNOWN | NOT_APPLICABLE`);
- observation timestamp;
- existing episode/dispatch identity where applicable;
- optional `superseded_by` for explicit evolution, rather than age-based validity windows.

This is a conceptual candidate, not an implementation specification.

## CRITICAL DESIGN GUARDRAILS

1. `FACT/INFERENCE/ASSUMPTION` must never be encoded solely as confidence.
2. A high-confidence inference remains an inference.
3. Observation history must not automatically become a binding contract.
4. Runtime observations, source facts, tests and historical records must remain provenance-distinguishable.
5. A verifier should compare expectation/invariant against evidence and produce verification status/evidence reference; diagnosis, impact and corrective action belong to existing reasoning/reconciliation organs.
6. Do not create `validity_window` merely because stale recommendations existed; UK-15 established that an old recommendation can still be a valid prior prediction source.
7. Do not introduce a new producer/consumer taxonomy if existing identities/interaction/dispatch/session/trace identifiers can express the relation.
8. `artifact_kind` must not mix physical artifacts (`method`, `import`, `field`, `event`) with dimensions such as temporal, semantic, causal or authority.

## ARCHITECTURAL QUESTION NOW

Before creating even this minimal Claim representation, test whether its data can live inside an existing persistence model/table.

The current leading candidate tables named by the adversarial review are:

- `capability_snapshots`
- `approval_checkpoints`
- `replay_annotations`

This must be checked directly against current schema/code. Do not create a table merely because the conceptual model exists.

## REQUIRED NEXT GATE

For the six previously defined contract/integrity probes:

1. method → method consumer;
2. import → imported symbol;
3. structure → dataclass/model consumer;
4. runtime event → event consumer;
5. decision/output → decision consumer;
6. lifecycle → consumer with ordering relation;

determine whether the minimum Claim information can be represented in an existing persistence structure without semantic abuse.

For each candidate existing table/model answer:

- what it means now;
- what fields actually exist;
- which Claim attributes fit naturally;
- which would be forced into metadata;
- whether provenance remains intact;
- whether multiple claims can coexist without ambiguity;
- whether lifecycle/verification status would be misrepresented;
- whether reusing it would create a second meaning for an existing table.

## IMPLEMENTATION GATE

**DO NOT IMPLEMENT.**

If no existing model can carry the concept without semantic distortion, only then is a minimal new representation justified for later design/implementation.

## SYMBIOTIC ROUTING

Future objectives about systemic integrity, cross-organ drift, contract verification, self-audit or architecture coherence should retrieve this document together with:

- `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`
- `CONTRACT-EXPECTATION-GAP-2026-09-12.md`
- `EXPECTATION-MODEL-ARCHAEOLOGY-2026-09-12.md`
- `CURRENT-STATE.md`
- `CONTEXT-INDEX.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`

and reconcile against the exact current source/runtime target before acting.
