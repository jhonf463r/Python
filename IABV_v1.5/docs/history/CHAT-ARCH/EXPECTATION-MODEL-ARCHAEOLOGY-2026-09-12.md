# IABV v1.5 — Expectation / Contract Model Archaeology

## CANONICAL STATUS

**State:** CONCEPTUAL DESIGN RECONCILED AFTER DEVIN + CLAUDE + UK-15 FORENSICS
**Date:** 2026-09-12

This record preserves the latest architecture finding before implementation.

## 1. CURRENT VERDICT

The active evidence supports:

**SMALL_NEW_REPRESENTATION_REQUIRED**, but the scope must remain minimal and is not yet an implementation authorization.

Existing IABV models represent findings, validations, experiments, decisions, signals, environment matches and handoffs, but no current model was demonstrated to represent a general producer→consumer expectation independent of a specific domain.

`SelfCodeAnalysis.verify_intent_routing()` is a concrete partial seed for `EXPECTATION → DISCOVER ACTUAL → COMPARE → DETECT`, but it is hardcoded to intent-routing handlers and specific files.

## 2. IMPORTANT LIMITATION

The conclusion "new representation required" is an architectural working hypothesis, not permission to create a large framework.

The next audit must establish the minimum semantics actually required and determine whether an existing model combination can satisfy any of them.

Avoid creating a new central brain, coordinator, registry, scanner, or duplicate responsibility.

## 3. EXPECTATION VS CONTRACT

Current conceptual distinction:

- **Expectation:** what a producer/consumer relationship is expected to satisfy, including source/evidence and confidence.
- **Contract:** the technical invariants that make that expectation verifiable.
- **Verification result:** the observed comparison and evidence.
- **Reconciliation/correction:** downstream action, not part of the expectation itself.

These concepts should not be collapsed prematurely.

## 4. PROPOSED MINIMAL SEMANTICS — STILL TO BE ADVERSARIALLY TESTED

Potential expectation dimensions include:

- producer identity;
- consumer identity;
- artifact/operation kind;
- artifact identity/name;
- expected shape/invariant;
- evidence source and provenance;
- confidence/epistemic status;
- episode/scope where relevant.

Temporal and semantic constraints may be necessary, but they should only be included when evidence demonstrates they are required for the first capability increment.

A large list of possible contract kinds is not itself evidence that all must be represented now.

## 5. EXPECTATION SOURCES

Candidate sources identified:

- explicit declaration;
- source-derived call sites/interfaces;
- test-derived expectations;
- schema/model-derived expectations;
- lifecycle-derived expectations;
- runtime-derived expectations;
- semantic-derived expectations.

Critical rule:

`FACT != INFERENCE != ASSUMPTION`

The representation must preserve that distinction rather than turn inferred expectations into authoritative facts.

## 6. ACTUAL REPRESENTATION

Candidate actuals include:

- source definition;
- runtime object;
- runtime event;
- persisted record;
- decision;
- outcome.

Static verification and runtime verification must not silently mix source, live state and historical evidence.

## 7. CURRENT ORGAN CONTRIBUTION

Relevant current organs include:

- `SystemIdentityRegistry` — subsystem/dependency identity;
- `SelfCodeAnalysis` — source definitions, imports, method/field inspection;
- `RuntimeAuditTracer` — runtime events/timestamps;
- `DecisionAuditTrail` — decision/outcome provenance/timestamps;
- `TaskContextAssembler` — context composition;
- `OrganismStateSnapshot` — organism-state aggregation;
- `DiscernmentFrameService` — contradiction/discernment;
- `PerceptionCrossValidator` — expected-vs-real environment evidence;
- `OSES` — findings, anomaly review and deduplication;
- `UniversalPerceptionService` — signal normalization;
- `ToolDiscoveryService` — tool signal reconciliation;
- `CommonSenseEngine` — expected-vs-real reasoning and correction;
- `CodeResponsibilityInferencer` — responsibility inference in construction tooling.

The important architectural question remains whether a small representation can connect these outputs without replacing them.

## 8. P040 / UK-15 LESSONS

P040 is evidence of source/runtime mismatch being exposed by a real execution path. It is not evidence that every contract check is absent.

UK-15 is a superseded false-positive temporal interpretation. Correct lifecycle for the audited case was:

`R_prev → prediction extraction → Run_N → R_new`

The post-run recommendation is a future-facing update. The historical recommendation was valid prediction input. The previous five-month gap is stale knowledge but not itself a retrieval failure.

## 9. NEXT UNCERTAINTY

The critical open question is:

> Is a general Expectation representation sufficient, or does IABV also require a distinct inference algorithm/pipeline to derive expectations from actual relationships in source/runtime data?

This must be resolved before implementation.

## 10. CURRENT GATE

**NO IMPLEMENTATION YET.**

The next action is an adversarial review of the conceptual expectation/inference model, with emphasis on minimality, false positives, provenance and whether the proposed fields are actually necessary.

## 11. REQUIRED FUTURE RETRIEVAL

Future objectives involving systemic integrity, contract drift, cross-organ connectivity, self-audit or expectation/verification should retrieve this record together with:

- `SYSTEMIC-INTEGRITY-AND-CONNECTIVITY-2026-09-12.md`
- `CURRENT-STATE.md`
- `CONTEXT-INDEX.md`
- `SYMBIOSIS-MAP.md`
- `UNRESOLVED-KNOWLEDGE.md`
- the P040 runtime record
- the UK-15 forensic record.

## 12. UPDATE RULE

Later direct source/runtime evidence may supersede this design. Preserve historical reasoning and provenance while updating the active model.
