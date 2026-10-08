# CHAT-ARCH 2026-10-08-151 — RQ21.37 ADVERSARIAL CHALLENGE RECONCILIATED

## 1. Provenance and epistemic scope

Actor: SONNET / CLAUDE.

Scope explicitly declared by actor:
- semantic analysis only;
- no repository inspection;
- RQ21.35 conclusions treated as FACT reported by the corpus, not independently reverified;
- all new conclusions classified as INFERENCE or DESIGN JUDGMENT unless otherwise noted.

Therefore:
- RQ21.37 is independent semantic challenge, not source verification.
- RQ21.35 source facts remain report-only in this episode unless separately verified.
- No source/runtime/implementation claim is promoted by RQ21.37.

## 2. Verdict

RQ21.37:
**PASS WITH REPAIRS / REVISE THEN RECHALLENGE**

The provisional semantic contract has a sound causal skeleton, but is not implementation-safe yet.

## 3. Strongly supported design invariants

The adversarial challenge supports preserving:

1. preference cannot create capability eligibility;
2. selected realization/action cannot retroactively define pre-selection R_task;
3. tool/provider/adapter identity is not capability identity;
4. readiness and availability are distinct from capability;
5. minimum conjunctive capability semantics are coherent for single-realization eligibility;
6. ToolActionType should not be promoted to a pre-selection oracle.

These are design judgments, not runtime facts.

## 4. Critical repairs

### Repair A — remove circularity

Previous proposal: operation was partly defined by its effect on required capabilities, while capability was defined by the operation.

Required repair: anchor operation/capability semantics in non-circular functional terms:
- required result;
- success criterion;
- conditions that materially determine satisfaction.

Do not define an operation by saying it changes the capabilities required.

### Repair B — distinguish capability satisfaction from permission/eligibility

Use separate concepts:

capable = functionally satisfies the demand;
permitted = governance allows the realization to perform it here;
ready = execution prerequisites are prepared;
available = realization can currently be used.

Avoid overloading the word eligible until these layers are composed explicitly.

### Repair C — demand state

R_task must not be represented solely as a set.

Minimum semantic form:

R_task = (requirements, demand_state)

with demand_state at least:
- KNOWN
- AMBIGUOUS
- UNKNOWN
- EMPTY_CAPABILITY_DEMAND

R_task = empty set without an explicit demand state is not sufficient evidence of no capability demand and should default to UNKNOWN.

### Repair D — capability satisfaction evidence

Capability satisfaction should have:
- capability identity;
- realization;
- relevant deterministic/contextual envelope;
- evidence basis at least distinguishing DECLARED / DEMONSTRATED / UNKNOWN.

A readiness/availability failure must not be learned as functional incapability.

The exact evidence ontology remains a design question and must not be expanded unnecessarily in the next contract revision.

### Repair E — governance-derived demand

Some constraints that look like policy can materially alter the functional demand, e.g. effect bounds or locality.

Minimum correction: separate:
- task-intrinsic demand;
- demand legitimately derived from task governance constraints;
- no demand derived from the selected realization itself.

Authorization/grant state remains execution/governance state, not capability identity.

### Repair F — success criterion vs evidence requirement

Distinguish:
- functional success criterion: what must be true;
- evidence requirement: what must be demonstrated, with what independence.

A verification capability belongs in R_task only when verification is itself an explicit or governing requirement, not universally.

### Repair G — conjunctive boundary

Minimum contract defines individual realization eligibility: a single realization satisfies all R_task requirements.

The current contract does not settle:
- multi-realization composition;
- order;
- data dependencies;
- interface compatibility.

Those remain explicit out-of-scope semantics, not implicit assumptions.

Capability parameters/envelopes must be preserved so that materially different bounded problems are not collapsed under one generic capability label.

### Repair H — anti-circular demand stability

R_task must be treated as a decision input with provenance and version identity.

At minimum the conceptual contract needs:
- who/what produced the interpretation;
- source/context;
- time/decision episode;
- version or immutable identity.

Candidate-set visibility must not change the derived requirement semantics.

This is a methodological/design requirement, not yet a runtime contract.

### Repair I — failure attribution

Separate:
- wrong demand interpretation;
- insufficient capability;
- readiness/availability failure;
- governance denial;
- execution failure;
- verification failure.

Otherwise later learning can assign evidence to the wrong relation.

## 5. Important distinctions retained

Do not collapse:

UNKNOWN demand != KNOWN demand with no capable realization
capable != permitted
capable != ready
capable != available
capability demand != evidence requirement
post-selection action != pre-selection demand
writeback != learning

## 6. Conjunctive requirement boundary

The minimum contract remains:

R_task = [C1,C2,C3]

means:

C1 AND C2 AND C3

for a single-realization capability-satisfaction test.

Multi-realization composition is not prohibited, but is outside this contract until a separate semantic edge is opened.

## 7. Universal/adaptive implication

The adversarial challenge strengthens the developmental target:
- capability identity must remain stable across realization substitution;
- experience must be attached to capability + realization + relevant envelope;
- readiness/availability failures must not be recorded as capability failures;
- R_task must be frozen/versioned before outcome observation;
- later behavioral change must be independently attributable to retained knowledge rather than retrospective R_task rewriting.

Therefore the capability model provides a structured join for future learning; it does not itself prove learning.

## 8. FACT / INFERENCE / DESIGN JUDGMENT / UNPROVEN

FACT:
- Sonnet/Claude returned PASS WITH REPAIRS under its declared semantic-only scope.
- It identified the listed logical/design defects in the provisional contract.

INFERENCE:
- the next correct activity is semantic-contract revision, not implementation or another generic source search.

DESIGN JUDGMENT:
- use the repaired distinctions above as the next provisional contract.

UNPROVEN:
- RQ21.35 source findings remain report-only in this episode;
- the revised semantic contract is not yet independently accepted;
- the proposed evidence ontology is not yet an executable implementation contract;
- multi-realization composition semantics remain unresolved;
- runtime learning and causal self-improvement remain unproven.

## 9. Symbiosis / Method Delta

Knowledge Delta:
the provisional semantic model requires a richer separation between demand state, functional capability, execution state, governance and evidence.

Method Delta:
before implementation, adversarially test not only capability granularity but also:
- circularity;
- vacuous truth;
- epistemic-state loss;
- candidate-set leakage;
- evidence attribution;
- policy-derived demand.

Routing Delta:
next actor is ChatGPT/coordinator-synthesis to produce the minimum repaired semantic contract. After that, return the revised contract to Sonnet/Claude for one focused re-challenge.

## 10. Implementation status

DO NOT IMPLEMENT.