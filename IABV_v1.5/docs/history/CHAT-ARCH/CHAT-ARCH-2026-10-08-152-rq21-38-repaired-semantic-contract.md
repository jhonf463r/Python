# CHAT-ARCH 2026-10-08-152 — RQ21.38 REPAIRED PROVISIONAL SEMANTIC CONTRACT

## 1. Status

RQ21.37 adversarial result:
PASS WITH REPAIRS / REVISE THEN RECHALLENGE.

This record is the ChatGPT coordinator's repaired semantic synthesis. It is PROVISIONAL and must be re-challenged by Sonnet/Claude before implementation.

No repository/runtime/source implementation is authorized.

## 2. Non-circular semantic anchor

### Operation

An operation is defined by:
1. the required functional result;
2. the success predicate that determines whether that result has been achieved;
3. the determinant conditions/parameters under which that success predicate is valid.

An operational distinction exists when changing one of those determinant elements can change which realizations can satisfy the functional contract.

Do NOT define an operation by reference to which capability/tool/provider performs it.

### Capability

A capability is an abstract functional competence represented by the existence of a class of realizations that can satisfy a specified functional demand under a specified parameter/envelope.

Capability identity is therefore tied to functional behavior, not provider identity.

## 3. Demand representation

Conceptually:

R_task = (requirements, demand_state)

where each requirement means:

required capability + relevant parameter/envelope

and demand_state is one of:
- KNOWN
- AMBIGUOUS
- UNKNOWN
- EMPTY_CAPABILITY_DEMAND

### KNOWN

A complete sufficient requirement set has been established for the current decision.

### AMBIGUOUS

Two or more materially different requirement sets remain plausible.

Do not union them into a fake single requirement set.

### UNKNOWN

There is insufficient information to construct a justified requirement set.

### EMPTY_CAPABILITY_DEMAND

An explicit, justified claim that the task's success contract requires no functional capability in this capability dimension.

An empty requirements set without this explicit state is not treated as EMPTY; it is UNKNOWN.

## 4. Candidate-set independence

R_task derivation must not depend on the current set of available tools, providers, assistants or selected realizations.

Conceptual invariance test:

derive_R_task(task, candidate_set_visible) = derive_R_task(task, candidate_set_masked)

for the same task/context.

Any change caused only by exposing a particular candidate is evidence of realization leakage.

R_task is a decision input and must be frozen/versioned before observing the result of the selected realization.

A later reinterpretation creates a new R_task version; it does not rewrite the original demand used for the decision.

## 5. Separate four distinct predicates

Do not use one overloaded eligible predicate.

### Functionally capable

The realization is capable of satisfying every requirement in R_task under the relevant parameter/envelope, with an explicit evidence basis.

### Permitted

Governance/authorization allows the realization to perform the proposed action in this context.

### Ready

The operational prerequisites for execution are satisfied.

### Available

The realization can currently be used/assigned.

The composite concept may later be called operationally eligible:

operationally_eligible = functionally_capable AND permitted AND ready AND available

but these predicates remain semantically separate.

Preference operates only after functional and operational sufficiency have been established.

## 6. Capability-satisfaction evidence

A capability-satisfaction relation should distinguish at least:
- DECLARED
- DEMONSTRATED
- UNKNOWN

Evidence belongs to the relation:

realization × capability × parameter/envelope

not to the abstract capability label itself.

A failure caused only by readiness, availability or permission must not update the capability-satisfaction relation as a functional failure.

## 7. Governance-derived demand

Task demand has two legitimate semantic sources:

1. task-intrinsic functional requirements;
2. functional constraints that are part of the task/governance contract and therefore alter the required effect or success predicate.

The selected realization is never allowed to define the demand.

Authorization/grant state is not capability identity.

Example distinction:
- modify only within directory X can affect the functional contract if preserving that boundary is part of success;
- this actor is authorized to modify directory X is permission state.

## 8. Success vs evidence

Separate:

### Functional success predicate
What must be true for the task outcome to count as successful.

### Evidence requirement
What must be demonstrated about that outcome, including any independence requirement.

A verification capability is included in R_task only when verification is itself an explicit functional objective or a governing evidence requirement that materially belongs to the task contract.

Intrinsic checks required to produce the requested effect remain part of the operation's execution semantics rather than automatically becoming a separate verification capability.

## 9. Minimum conjunctive semantics

For:

R_task = [C1, C2, C3]

single-realization functional sufficiency means:

C1 AND C2 AND C3

The minimum contract does NOT define:
- multi-realization composition;
- execution order;
- data-flow dependencies;
- interface compatibility;
- workflow decomposition.

Those are separate semantic questions and must not be silently invented here.

Parameterized/enveloped capability requirements remain distinct when their functional conditions differ materially.

## 10. Anti-circularity and learning safety

The following are mandatory methodological properties:

pre-selection demand → frozen R_task → realization selection → execution → observation

not:

selection → result/action → revised R_task → justify selection

Any later revision must be represented as a new semantic interpretation/version.

This protects later learning from post hoc relabeling.

Failure attribution must distinguish:
- demand interpretation error;
- functional capability insufficiency;
- permission denial;
- readiness failure;
- availability failure;
- execution failure;
- verification/evidence failure.

Only evidence appropriate to the relation being updated should modify future capability knowledge.

## 11. Universal adaptive compatibility

The contract should permit:

same abstract requirement → multiple functionally equivalent realizations

and preserve experience by:

capability + parameter/envelope + realization + evidence/provenance

rather than by tool identity alone.

This enables later reuse without forcing experience from Tool A to become a Tool-A-specific pseudo-capability.

## 12. Explicit falsification targets

A future challenge falsifies or requires revision if it demonstrates any of:

1. R_task changes merely because candidate tools become visible;
2. a readiness/availability/permission failure is incorrectly treated as functional incapability;
3. a capability label groups a realization that can satisfy one demand but not another under the same stated envelope;
4. a capability distinction disappears when provider/interface/mode is changed without changing the functional contract;
5. a post-selection action is required to establish what R_task supposedly was;
6. UNKNOWN demand is silently treated as EMPTY_CAPABILITY_DEMAND;
7. evidence requirements are confused with functional task requirements;
8. multi-capability semantics silently assume workflow composition not covered by the contract.

## 13. Epistemic status

FACT:
- RQ21.37 produced PASS WITH REPAIRS under semantic-only scope.
- This record incorporates its nine repair classes.

INFERENCE:
- the repaired separation is a better candidate for the next adversarial test.

DESIGN JUDGMENT:
- the exact terminology and minimum predicate decomposition in this record.

UNPROVEN:
- that this repaired contract survives further adversarial counterexamples;
- that it is sufficient for the actual code path;
- that it is the minimal implementation contract;
- that it will remain stable under future capability domains;
- any runtime learning effect.

## 14. Current route

Next actor:
SONNET/CLAUDE.

Question:
Can this repaired contract still be falsified by semantic counterexamples, especially around:
- parameter/envelope identity;
- governance-derived functional constraints;
- capability evidence;
- candidate-set invariance;
- UNKNOWN vs EMPTY;
- verification requirements;
- conjunctive limits?

If it survives, perform source-level reconciliation before implementation.

Implementation status:
DO NOT IMPLEMENT.