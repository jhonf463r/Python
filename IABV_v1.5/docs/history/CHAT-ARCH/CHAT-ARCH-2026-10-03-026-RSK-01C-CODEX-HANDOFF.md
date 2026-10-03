# CHAT-ARCH-2026-10-03-026 — RSK-01C CODEX HANDOFF

## IA DESTINO
Codex

## CAPABILITY
Repository/code archaeology + evaluation-fixture/contract design.

## CURRENT OBJECTIVE
Make cross-chat continuity measurable and reliable enough that a new AI does not select one protocol/history neighborhood and silently omit material knowledge, negative knowledge, recent deltas, provenance/currentness or correct routing.

## VERIFIED STATE AFTER RSK-01B
Five fresh Sonnet sessions were run against frozen corpus `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`.

Observed:
- 01 technical state + negatives: bounded PASS; Codex route recovered.
- 02 methodological correction: bounded PASS; single routing spine and stale contradictions recovered.
- 03 BIO-04 M1/M2: strong knowledge recovery; local Sonnet verification route selected after a provenance gap. Global-vs-domain routing scope was not experimentally fixed, so this is not classified as a routing failure.
- 04 human-aware plasticity: bounded PASS; method and negative knowledge recovered; Codex route recovered.
- 05 routing authority: bounded PASS; Codex route recovered.

Aggregate:
`5/5` sessions recovered substantial relevant material; `4/5` explicitly reconstructed Codex from the frozen routing snapshot.

However, the experiment did **not** freeze an independent expected material state before each session. The agents' own `OMITTED` sections therefore cannot establish complete recall.

RSK-01A static audit remains the leading architectural hypothesis: **B — missing causal integration**, with A/C as contributors and D unproven. RSK-01B does not confirm runtime B because it tested an external AI navigating repository documentation, not IABV runtime composition.

## FIRST OPEN EDGE
`objective → measurable complete relevant candidate activation`

## REQUIRED READ-ONLY AUDIT
Inspect the existing repository/test/evidence structures and determine the smallest reproducible fixture that can measure completeness without creating a new retrieval service.

Specifically determine:

1. How to derive an **independent expected material set** from the fixed SHA for each objective.
2. How to distinguish positive knowledge, negative knowledge, current routing, historical routing, provenance, corrections and superseded material in that expected set.
3. How to define materiality independently of the evaluated AI's own retrieval claims.
4. How to define the boundary between the **global project objective/current route** and a **domain-specific sub-objective route**. Session 03 demonstrated that this scope relation is currently ambiguous.
5. Whether an existing fixture, benchmark, registry, evidence schema, archive index or test infrastructure can own this evaluation without adding a new permanent service.
6. Whether the next test should remain document-level or move to runtime integration.
7. What exact evidence would distinguish:
   - A = session/procedure failure;
   - B = missing causal composition;
   - C = corpus/index/currentness/canonicalization ambiguity;
   - D = irreducible semantic ownership gap.

## EXISTING-ORGAN RESTRAINT
Do not create:
- a retrieval brain;
- universal memory engine;
- new actor selector;
- new semantic ontology;
- HumanModel/PlasticityEngine or similar.

First prove that no existing test/evidence/registry/index contract can own the fixture.

## REQUIRED OUTPUT

### CURRENT MAIN SHA
Use and report the actual current remote `main` SHA at the time of audit.

### EXISTING FIXTURE / EVIDENCE SURFACES
List exact files, tests, services and schemas that could provide:
`expected-state derivation`, `materiality`, `currentness`, `provenance`, `objective tagging`, `negative knowledge`, `routing authority`, `omission scoring`.

### GAP ANALYSIS
Identify the first missing contract. Do not call it a missing component until an existing owner has been ruled out.

### RSK-01C MINIMUM FIXTURE
Specify the smallest reproducible read-only fixture, including:
- fixed corpus SHA;
- fixed objective suite;
- independent expected-state derivation procedure;
- materiality rules;
- omission/staleness scoring;
- historical NEXT ACTOR suppression test;
- global-vs-domain routing rule;
- evidence/provenance fields;
- pass/fail interpretation.

### TEST DESIGN
Explain exactly how a fresh AI will be evaluated without seeing the expected state or prior session outputs.

### A/B/C/D DISCRIMINATION
State which observations would establish A, B, C or D.

### NEXT ACTOR
After the fixture audit, name the concrete actor and next action. Do not inherit a route from historical documents.

## EPISTEMIC CONTROLS
Preserve:
`relevant hit != complete relevant state`
`agent self-report != independent ground truth`
`stored Knowledge Delta != consumed Knowledge Delta`
`protocol exists != protocol executed`
`historical NEXT ACTOR != current routing authority`
`static architecture finding != runtime causal proof`

Do not claim general continuity from RSK-01B.

## STOP CONDITION
Stop after producing a concrete fixture/contract specification and deciding whether the next discriminating step is document-level or runtime-level.

NO IMPLEMENTATION.