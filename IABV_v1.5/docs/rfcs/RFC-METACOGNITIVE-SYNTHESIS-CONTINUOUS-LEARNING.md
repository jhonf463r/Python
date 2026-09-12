# RFC — Metacognitive Synthesis and Continuous Learning

**Status:** Proposed architectural invariant
**Scope:** IABV v1.5
**Intent:** Convert distributed perception, world-model, temporal, adaptive, execution, verification and learning organs into one coherent inference loop without creating a second brain or a parallel orchestrator.

## 1. Problem

IABV already contains many organs that represent pieces of cognition: perception/context assembly, world state, self/environment examination, routing, governance, adaptive weights, strategy selection, experimentation, outcome recording, audit tracing, portable context and UI projection.

The recurring failure mode is not necessarily absence of an organ. It is **lack of algorithmic synthesis between organs**.

A local component can be correct while the system as a whole remains cognitively incomplete when:

- an observation is not contextualized with its provenance and temporal position;
- a world-model fact is not allowed to influence the decision that follows;
- an adaptive weight exists but does not change strategy selection;
- a result is observed but cannot be attributed to the exact action/interaction that produced it;
- a contradiction is detected but not promoted to a hypothesis or diagnostic branch;
- a lesson is written to a document but is not reintroduced into future reasoning;
- persistence exists without measurable behavioral change.

## 2. Core deduction

**Cognition emerges from the composition of existing organs, not from any single universal engine.**

The missing abstraction is therefore a **metacognitive synthesis function** that continuously organizes and connects the outputs of existing organs.

Do not create another brain, another global orchestrator, another memory subsystem, or another progress manager merely to implement this RFC.

The synthesis function must sit conceptually across the current architecture and use its existing canonical interfaces.

## 3. Universal cognitive loop

The canonical loop is:

`raw observation`
`→ provenance + temporal anchoring`
`→ canonical perception/context`
`→ environment/self state`
`→ world model`
`→ constraints + governance`
`→ contradiction detection`
`→ hypothesis set`
`→ uncertainty/risk`
`→ actor/action selection`
`→ execution`
`→ result observation`
`→ independent verification`
`→ accept / reject / unresolved`
`→ model update`
`→ learning extraction`
`→ provenance-preserving persistence`
`→ measurable reuse in a later decision`
`→ recurse

A loop that stops before verification and reuse is **analysis**, not learning.

## 4. Evidence discipline

The system must distinguish at least:

- `DECLARED_STATE` — what code, reports or configuration claim;
- `OBSERVED_STATE` — what a real runtime, test, file, trace or external source shows;
- `INFERRED_STATE` — a conclusion derived from observations;
- `HYPOTHESIZED_STATE` — an explanation not yet proven;
- `EFFECTIVE_STATE` — the behavior actually exerted on the current decision/execution path.

Invariant:

**Declared state must never silently become effective state.**

Examples:

- tests passing ≠ complete runtime proof;
- adaptive weight present ≠ adaptive behavior demonstrated;
- WorldModel snapshot exists ≠ WorldModel influenced the decision;
- learning file updated ≠ learning occurred;
- UI activity visible ≠ underlying cognitive progress is real.

## 5. Temporal continuity

Every causal unit crossing an asynchronous boundary must preserve enough identity to reconstruct its history.

Minimum causal identity should include, when applicable:

- interaction identity;
- dispatch identity;
- task identity;
- parent/preceding action identity;
- creation timestamp;
- update timestamp;
- terminal timestamp;
- provenance/source;
- current state and terminal state.

Temporal continuity is not only timestamps. It means the system can answer:

1. What existed before?
2. What changed?
3. What action caused or coincided with the change?
4. What evidence verified the change?
5. What later decision should be different because of it?

Stale asynchronous results must be rejected or quarantined rather than mutating a newer causal context.

## 6. Metacognitive synthesis function

Conceptually define a synthesis operation with the following inputs:

`SYNTHESIS(observation, context, self_state, world_state, history, capabilities, constraints, uncertainties, contradictions, learned_weights)`

and the following outputs:

`{hypotheses, confidence, contradictions, selected_actor, selected_action, expected_information_gain, execution_plan, verification_plan, learning_candidates}`

This is a reasoning contract, not permission to create a new monolithic class.

### 6.1 Contextualization

Before deciding, bind each relevant signal to:

- time;
- provenance;
- causal ancestry;
- current world state;
- environment/self capabilities;
- current workload and constraints;
- known historical outcomes;
- applicable lessons.

### 6.2 Contradiction-first analysis

Do not immediately optimize for the first plausible explanation.

Search for contradictions such as:

`UI says working + causal worker absent`
`lifecycle identity A + active identity B`
`adaptive weight changed + strategy unchanged`
`world model says X + selected action assumes not-X`
`learning persisted + future behavior unchanged`

A contradiction should become a first-class diagnostic signal.

### 6.3 Hypothesis management

For each meaningful contradiction or unexplained observation, maintain candidate hypotheses with:

- supporting evidence;
- contradicting evidence;
- confidence;
- cost to test;
- information gain if resolved;
- expected consequences.

Prefer the next experiment that most reduces uncertainty per unit intervention cost.

## 7. Actor selection

Actor selection must be dynamic, based on:

`actor_score = information_gain × capability_fit / intervention_cost`

subject to governance and availability constraints.

Possible actors include, depending on the task and available evidence:

- IABV internal services for self-observation, synthesis, tracing or model inspection;
- Windows/runtime execution for environmental truth;
- Devin for implementation and runtime-capable repair;
- Claude for independent static audit;
- Codex for cross-source reconciliation/adjudication after evidence exists.

The system must not select an actor simply because it was used previously.

## 8. Adaptive weights are causal only when behavior changes

An adaptive parameter has cognitive meaning only when its value can be traced through the decision path.

Required trace conceptually:

`experience → lesson candidate → weight/update → strategy/routing decision → action → outcome`

The system should be able to demonstrate whether the updated weight changed:

- ranking;
- route selection;
- strategy selection;
- confidence;
- experiment choice;
- intervention cost;
- verification policy.

A stored number without downstream effect is state, not learning.

## 9. World model is an active causal participant

The world model must not be treated as a passive report repository.

For decisions that depend on world state, the system should be able to expose:

`world_state_used_in_decision = true`

plus provenance for the relevant fields.

When current world state conflicts with historical assumptions, the newer evidence must trigger either:

- model update;
- uncertainty increase;
- hypothesis revision;
- experiment;
- safe refusal/deferment.

## 10. Learning criterion

A learning event is legitimate only when all required evidence exists:

1. a real experience or verified observation occurred;
2. provenance is known;
3. the observation was interpreted into a lesson or model update;
4. the lesson/update was persisted through the canonical persistence mechanism;
5. a later decision can demonstrate reuse or measurable behavioral influence.

Therefore:

**persistence is necessary but not sufficient for learning.**

## 11. From chat finding to reusable deduction

When an incident exposes a new architectural pattern, the system must attempt to generalize it.

Example:

`sendChat stale result`

must not remain only a chat fix.

The generalized deduction is:

`all asynchronous causal results must preserve origin identity and validate it before state mutation.`

Likewise:

`deep-audit early return`

must generalize to:

`a diagnostic/observational guard may record or annotate a flow, but must not accidentally terminate the productive causal pipeline unless termination is explicitly part of the contract.`

This generalization step is mandatory for future incident analysis.

## 12. Self-perception and UI projection

Internal self-perception and external UI perception are related but distinct.

Internal perception answers:

- what the system believes it is doing;
- why it selected the current path;
- what state it is in;
- what evidence supports that belief;
- where uncertainty or contradiction exists.

The UI should project this canonical state. It must not invent a second interpretation of system progress.

A progress indicator is trustworthy only when it is downstream of the same causal state used by orchestration and verification.

## 13. Friction minimization

The system should prefer the path that preserves causal continuity while minimizing unnecessary context switches, synchronous blocking, duplicated computation and redundant agents.

However, friction reduction must never override evidence, governance or verification.

The objective is not merely speed. It is:

`minimum unnecessary intervention + maximum useful information + preserved causal trace`.

## 14. Continuous synthesis without a new universal engine

The synthesis behavior can be distributed across existing organs:

- perception/context organs collect and normalize evidence;
- world/self models provide current reality;
- governance constrains actions;
- routing/strategy/weights select useful next steps;
- audit/trace services preserve causal evidence;
- outcome/experiment services capture feedback;
- portable/history mechanisms preserve continuity;
- UI projection exposes the canonical state.

The architectural gap is the **contract that requires these outputs to participate in one loop**.

Implementations should therefore prefer:

1. extending existing contracts;
2. adding trace/provenance fields where missing;
3. connecting existing outputs to downstream decision points;
4. adding verification gates;
5. improving persistence/reuse;
6. only then considering new abstractions.

## 15. Required meta-audit question set

Before declaring a system change complete, the audit should be able to answer:

- What did the system observe?
- Where did the evidence come from?
- At what time and in what causal context?
- What did the world/self model say?
- What contradictions existed?
- What hypotheses were considered?
- Why was this actor/action selected?
- Which adaptive/history signals affected that choice?
- What actually executed?
- What independently verified the result?
- What changed in the model?
- What lesson was persisted?
- Where exactly is that lesson reused later?

Any unanswered question should be classified as `UNKNOWN`, not silently inferred as `PASS`.

## 16. Architectural invariants to retain

### I1 — No second brain

Do not introduce a parallel orchestrator, memory or cognition engine when an existing organ can own the responsibility.

### I2 — Evidence before synthesis, synthesis before action

Never convert unverified claims directly into effective state.

### I3 — Identity across time

Causal results must retain origin identity through asynchronous boundaries.

### I4 — World-model relevance must be observable

A world model counts as decision-relevant only when its state can be traced into the decision.

### I5 — Adaptive relevance must be observable

A weight counts as adaptive learning only when it changes subsequent behavior.

### I6 — Persistence is not learning

A persisted lesson must eventually alter a later decision or behavior to qualify as learned state.

### I7 — Contradictions are information

Contradictions should increase diagnostic priority rather than be normalized away.

### I8 — Guards should preserve productive flow

Observability and diagnostics should not accidentally terminate the execution path they are supposed to illuminate.

### I9 — Actor selection is dynamic

Choose the next actor by expected information gain, capability fit and intervention cost.

### I10 — Unknown remains unknown

Unproven runtime behavior must remain unproven until the required runtime evidence exists.

## 17. Acceptance criterion for metacognitive maturity

IABV should be considered to have crossed a meaningful metacognitive threshold only when a real incident can be shown end-to-end as:

`observe → contextualize → model → detect contradiction → hypothesize → choose actor → act → verify → learn → persist → reuse → behave differently`.

Passing unit tests alone does not satisfy this criterion.

## 18. Implementation rule

This RFC is a **coordination contract** for existing organs. It is not a mandate to create a monolithic `UniversalSpaceTimeEngine`, `MetacognitionEngine`, `Brain`, or equivalent abstraction.

The desired evolution is an increasingly coherent distributed cognitive system whose parts share provenance, temporal continuity, world state, adaptive feedback and verification.
