# IABV v1.5 — Metacognitive Deduction / Temporal-Causal Synthesis

STATUS=CANONICAL_OPERATIONAL_KNOWLEDGE
DATE=2026-09-12
SCOPE=Cross-chat continuity, cognitive control plane, temporal reasoning, incident deduction, dynamic AI-role selection

## 1. PURPOSE

This record preserves a material deduction from the 2026-09-12 cross-chat review: when an incident blocks an expected interaction path, the incident itself is an observation in IABV's causal timeline and must be fed into the same reasoning method used to select the next action.

The system must not require the user to successfully transmit another prompt before the system can diagnose the blocked path. A failed communication path is itself evidence.

This record complements `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md` and the proposed `RFC-METACOGNITIVE-SYNTHESIS-CONTINUOUS-LEARNING.md` on the P040 branch. It does not claim that full runtime cognitive symbiosis has been proven.

## 2. CENTRAL DEDUCTION

IABV does not need a second monolithic brain or an invented `UniversalSpaceTimeEngine` merely because its cognition is distributed.

The more precise missing capability is a **temporal-causal synthesis function** that makes the outputs of existing organs participate in one continuously reconciled decision loop.

The function is conceptually:

`OBSERVATION`
`→ TEMPORAL + PROVENANCE ANCHOR`
`→ STATE_BEFORE`
`→ RELEVANT_MEMORY`
`→ SELF_STATE + WORLD_STATE`
`→ EXPECTATION / HYPOTHESES`
`→ CONTRADICTIONS / GAPS`
`→ INFORMATION_GAIN`
`→ ACTOR / ACTION SELECTION`
`→ EXECUTION`
`→ OBSERVED_RESULT`
`→ STATE_AFTER`
`→ EXPECTED-vs-ACTUAL DELTA`
`→ INDEPENDENT VERIFICATION`
`→ RECONCILIATION`
`→ KNOWLEDGE_DELTA`
`→ PERSISTENCE`
`→ FUTURE REUSE`
`→ BEHAVIORAL CHANGE`
`→ RECURSE`

The loop is incomplete when it stops at message receipt, formatted context, persisted data or a visible UI state.

## 3. SPATIAL-TEMPORAL INTERPRETATION

"Space-time" is used here as an engineering reasoning model, not as a claim that IABV implements a physics-level universal theory.

For each meaningful event, the system should preserve enough information to reconstruct:

- where the event occurred in the system;
- which workspace / runtime / branch / commit was active;
- which actor, task and interaction produced it;
- what the system knew before the event;
- what environment/world state was visible;
- what action was selected;
- what happened afterward;
- what changed;
- what evidence verified that change;
- what future behavior should be different because of the experience.

Temporal continuity therefore means more than timestamps. It means **causal reconstructability across state transitions**.

## 4. DECLARED VS EFFECTIVE REALITY

Always distinguish:

`DECLARED_STATE`
`OBSERVED_STATE`
`INFERRED_STATE`
`HYPOTHESIZED_STATE`
`EFFECTIVE_STATE`

The following are permanent epistemic boundaries:

- code exists != capability proven;
- code is wired != route executed;
- test passes != runtime proof;
- context exists != context consumed;
- context consumed != context influenced a decision;
- visible activity != actual work;
- world model exists != world model influenced a decision;
- adaptive weight exists != adaptive behavior;
- persistence != learning;
- external-agent output != truth;
- repository target != runtime target until proven.

## 5. INCIDENTS ARE SYSTEM OBSERVATIONS

When the user reports that an IABV interaction cannot be sent, treat that report as a real system observation.

Do not reduce it immediately to "UI bug".

The incident should expand into a causal chain such as:

`USER_INTENT`
`→ UI_ACCEPTANCE?`
`→ sendChat INVOCATION?`
`→ INTERACTION CREATED?`
`→ DISPATCH CREATED?`
`→ CONTEXT BUILT?`
`→ WORKER CREATED?`
`→ ACTION EXECUTED?`
`→ RESULT RETURNED?`
`→ TERMINALIZED?`
`→ UI_RELEASED?`

At each edge classify:

`DEFINED | WIRED | INVOKED | OBSERVED | CAUSED`

The first broken edge is the current causal gate, but downstream consequences must also be recorded because they may reveal a generalized defect class.

## 6. GENERALIZATION RULE

A local incident should be generalized only after the concrete evidence is established.

Example already observed in P040:

`sendChat stale result`

generalizes to:

`asynchronous causal results must preserve origin identity and validate origin before mutating current state.`

Likewise:

`deep-audit early return`

generalizes to:

`an observability or diagnostic guard must not accidentally terminate a productive execution path unless termination is explicitly part of its contract.`

This is the mechanism by which incident knowledge becomes reusable architecture rather than repeated patching.

## 7. SELF-PERCEPTION MAP

IABV already contains multiple self/environment observation organs. Current repository evidence identifies, among others:

- `PerceptionSnapshot` — unified pre-decision perception input;
- `UniversalPerceptionSignal` — point observation;
- `EnvironmentSelfModel` — hardware/runtime/risk state;
- `WorldModelSnapshot` / `WorldModelService` — operational environment state;
- `OperationalSelfExaminationService` — repeated-pattern, degradation and temporal review;
- `ControlMasterService` — governance, objectives, risks, rules and decisions;
- `organism_state_snapshot.py` — unified read-only organism-state view;
- `RuntimeAuditTracer` — causal runtime tracing;
- `ExperimentLab`, `TaskOutcomeRecorder`, `StrategySelector`, `AdaptiveWeightLayer` — outcome/history and future-route feedback;
- `PortableContextService` — objective-relevant continuity/context projection;
- `ControlCenterViewModel` / `EvolutionCenterViewModel` — external UI projection.

`organism_state_snapshot.py` explicitly remains observational and read-only; it is not itself the decision authority.

Therefore the open question is not "does IABV have an organ that can see itself?" It clearly has multiple observation mechanisms. The open question is whether those observations form a **causally continuous path into decisions and back into updated state**.

## 8. INTERNAL VS EXTERNAL SELF-PERCEPTION

Internal self-perception answers:

- what the organism believes it is doing;
- what environment it sees;
- what risks/constraints exist;
- what evidence supports that state;
- what contradictions are present;
- what temporal anomalies are present.

External/UI perception should be a projection of the same causal state.

The UI must not become a second source of truth for progress.

A displayed `working`, `consulting`, `received`, `idle` or similar status is trustworthy only when it is downstream of the same identity-bearing state used by lifecycle, dispatch, orchestration and verification.

## 9. CANONICAL COGNITIVE STATE

For external-agent cognition, the key transition to audit is:

`OrganismState / ControlMaster / WorldModel / PortableContext`
`→ DecisionContext`
`→ AdaptiveTaskOrchestrator`
`→ routing / governance`
`→ external agent`
`→ result`
`→ reconciliation`
`→ persisted delta`

The important question is not whether a `context_pack` exists, but whether it represents the **current canonical operational reality** that IABV determined was relevant to the decision.

A context packet is an artery. It is not proof of a central nervous system.

## 10. DYNAMIC ROLE SELECTION

The collaboration strategy is not a fixed sequence such as `ChatGPT → Devin → Claude → Codex`.

The objective should first identify:

- uncertainty;
- evidence boundary;
- missing capability;
- intervention cost;
- information gain.

Then select the strongest currently available actor.

The historical capability map remains:

- ChatGPT — synthesis, architecture framing, reconciliation, epistemic boundary control;
- Claude — adversarial/independent audit and challenge;
- Devin — implementation and exact-runtime work;
- Codex — controlled experiments and focused implementation/reconciliation;
- Windows runtime — environmental truth;
- GitHub — provenance/read-back evidence;
- IABV internal organs — self-observation, context/model/routing evidence.

This is capability evidence, not permanent identity.

A useful selection rule is:

`actor_score = expected_information_gain × capability_fit / intervention_cost`

subject to governance, safety, permissions and availability.

## 11. THE BLOCKED-PROMPT PRINCIPLE

If an external agent cannot receive the next prompt because an IABV interaction path is broken, do not stop reasoning.

Instead:

`communication failure`
`→ runtime/system observation`
`→ reconstruct pre-state`
`→ inspect relevant history and negative knowledge`
`→ inspect current repository/runtime evidence`
`→ identify broken causal edge`
`→ select minimal discriminating action`

The failed path is therefore both:

1. a blocker for external communication; and
2. a sensor event for self-diagnosis.

This avoids the methodological mistake of treating the user as a manual message relay required to unlock the system's own diagnosis.

## 12. CROSS-IA CONTINUITY

A true cross-AI continuity property requires:

`canonical_state_A`
`→ agent_A reasoning/action`
`→ verified result`
`→ `canonical_state_B`
`→ agent_B retrieval`
`→ continuation`

without manual reconstruction of material history.

The repository already defines objective-conditioned retrieval and cross-IA knowledge transfer as operational-memory goals. Current unresolved work still requires empirical proof that a later/new agent actually reconstructs the right state and uses it in its decision.

## 13. LEARNING CRITERION

Learning should not be declared merely because a record is written.

A valid learning event requires:

`experience`
`→ provenance`
`→ interpretation / lesson`
`→ canonical persistence`
`→ later retrieval`
`→ changed decision/action`
`→ independent observation of that change.

This aligns with the existing unresolved knowledge rule that persistence alone is insufficient.

## 14. PREDICTION AND CALIBRATION

The mature loop should also capture pre-action expectation:

`prediction`
`→ confidence / uncertainty`
`→ execution`
`→ observed result`
`→ comparison`
`→ calibration`
`→ strategy update.

Existing scientific-metacognition history already identified this as a key frontier. The important deduction is that the same temporal-causal synthesis function should connect prediction to the later verified outcome rather than treating them as unrelated records.

## 15. MINIMAL-DISCRIMINATING-ACTION PRINCIPLE

Before modifying code, ask:

`What single experiment would most reduce the important uncertainty?`

Prefer that experiment when it is safe and materially cheaper than broad refactoring.

The system should minimize unnecessary context switches, duplicated computation and redundant agents, but never at the expense of provenance, governance or verification.

## 16. MATURITY LEVELS

Use the following evidence ladder for every cognitive claim:

`IDEA`
`→ DESIGN`
`→ CODE`
`→ WIRED`
`→ TESTED`
`→ PRODUCTION PATH`
`→ RUNTIME OBSERVED`
`→ INDEPENDENTLY VERIFIED`
`→ CAUSAL EFFECT`
`→ LEARNED / REUSED`

A claim must not jump levels because multiple agents repeat it.

## 17. CURRENT REPOSITORY STATE RELEVANT TO THIS DEDUCTION

At the time of this record:

- `main` is the historical/operational-memory canonical branch and currently points to `4d147998ec5d9c710d994539b1c92323298ab55f`.
- `devin/p040-runtime-progress-observability` currently points to `083eed36f59b9ee6cf7282e8e362deb48a075779`, whose parent is `a5eae19aed08a7e1b9f46e816f8fadf290bc615d`.
- Commit `083eed...` added the proposed RFC on metacognitive synthesis and continuous learning to the P040 branch.
- The P040 chain therefore contains both implementation history and this architectural deduction, but the RFC is not being asserted as runtime proof.

## 18. CURRENT OPEN QUESTIONS

`OQ-01` — What exact existing component/contract should own the temporal-causal synthesis responsibility at runtime?

`OQ-02` — Does `DecisionContext` already contain enough canonical state, or is relevant state lost before routing?

`OQ-03` — Does `AdaptiveTaskOrchestrator` actually consume world/self/history/adaptive signals in a causal decision, or only make them available/descriptive?

`OQ-04` — Where does the first evidence-bearing break occur in the actual sendChat → external-agent path?

`OQ-05` — Can IABV produce a real A/B decision-influence demonstration from canonical context/state?

`OQ-06` — Can a second external AI continue from the first AI's canonical post-state without manual prompt reconstruction?

`OQ-07` — Does a verified experience measurably change a later route/weight/strategy decision?

`OQ-08` — Can prediction + confidence + outcome + calibration be joined into one causal record?

## 19. DO-NOT-REPEAT ERRORS

- Do not treat a failed UI interaction as a request to simply create a new communication mechanism.
- Do not make the user manually relay prompts as a permanent systems dependency when repository/runtime evidence can diagnose the blocker.
- Do not create a monolithic universal engine before demonstrating which existing contract is insufficient.
- Do not infer decision influence from context presence.
- Do not infer learning from persistence.
- Do not infer runtime from tests.
- Do not infer current truth from stale historical reports.
- Do not infer agent capability from historical role labels alone.

## 20. NEXT EXPERIMENT ORDER

When the communication path becomes executable again, the order should be:

1. prove the real UI → sendChat → interaction → dispatch → worker → result → terminal path;
2. prove canonical context propagation into the real production external-agent route;
3. run a controlled A/B where canonical state/context is materially different and measure a decision/action difference;
4. capture post-action observation and independently verify it;
5. persist the verified delta;
6. invoke a second agent/cycle and determine whether the delta is retrieved and changes behavior;
7. reconcile the result and update the canonical memory/capability model.

Do not claim cognitive symbiosis before the relevant edges are empirically demonstrated.

## 21. RELATION TO EXISTING CANONICAL MEMORY

This record should be activated for objectives involving:

- cognitive control plane;
- external-agent cognition;
- sendChat/UI/runtime causal continuity;
- temporal awareness;
- adaptive routing / weights;
- self-examination;
- cross-AI continuity;
- learning causality;
- architecture-to-runtime reconciliation.

It is intentionally a synthesis/deduction record, not an implementation ticket.

## 22. SOURCE AND EVIDENCE BOUNDARY

Sources used for this deduction:

- current GitHub repository state and current operational-memory files;
- `SYMBIOSIS-MAP.md`, `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, `UNRESOLVED-KNOWLEDGE.md`;
- `RFC-METACOGNITIVE-SYNTHESIS-CONTINUOUS-LEARNING.md` on the P040 branch;
- current `organism_state_snapshot.py` source;
- uploaded historical chat records from 2026-09-12 containing the sendChat incident, the P040 report and the subsequent temporal-causal deductions.

This record does **not** assert that the full loop is currently operational. Its purpose is to ensure that the deduction itself survives chat boundaries and changes how future objectives are analyzed.
