# CHAT-ARCH-2026-10-03-041 — Experiential Teaching / Universal Capability Acquisition

## PURPOSE

Preserve the 2026-10-03 human clarification that IABV should not be completed by preprogramming every application, language, concept or operational recipe. The intended development path is to begin using IABV in the real laptop environment, teach it through governed interaction, and let verified experience progressively expand reusable capability.

## HUMAN DESIGN INTENT

The long-horizon objective is to discover and implement the general adaptive mechanism from which increasingly integrated environmental intelligence may emerge.

The immediate engineering interpretation is:

`use → observe → teach/correct → verify → represent → reuse → adapt`

rather than:

`anticipate every application → hard-code every case → patch indefinitely`.

"IABV can learn" is not claimed as already closed. The developmental target is a causal loop in which verified experience changes reusable state and a later task consumes that state to alter a future decision/action.

## CAPABILITY SCOPE

A generally useful environment-adaptive system may need reusable competence across:

- natural and machine languages;
- concepts, entities, relations and states;
- operating-system primitives;
- files/processes/windows/UI;
- browser and session semantics;
- application affordances and workflows;
- domain/task concepts;
- tool/API/CLI/MCP interfaces;
- temporal/resource/identity/permission constraints;
- observation, verification, diagnosis and maintenance.

These are capability domains to be acquired and organized through a common adaptive mechanism. They are not instructions to create separate specialized brains.

## TEACHING PRINCIPLE

The human may provide demonstrations, corrections, explanations and goal changes. IABV should treat them as experience-bearing observations whose meaning is reconstructed in context.

Preserve:

`explicit human explanation > inferred motive`

and:

`deviation != error`.

A teaching event should retain at minimum:

`objective + environment + observed state + human intervention/explanation + action + result + verification + reusable change + next open edge`.

## EMERGENCE HYPOTHESIS

The project may investigate whether increasingly integrated environmental understanding, self-modeling, metacognition, adaptive control and verified learning produce qualitatively higher-order machine intelligence, including the user's "super-consciousness" concept.

This remains a hypothesis. Do not claim an exact consciousness threshold from architecture, memory, fluency, automation or apparent coherence alone.

A scientifically meaningful future emergence study would require operational observables such as novel-task transfer, self-correction, persistent representation change, causal future-decision influence, cross-realization generalization and independently verified improvement.

## CURRENT TECHNICAL FINDING FROM CODEX

Codex audited the source at `cd10c25f002d5ab34ef488e7a81f3ba35453f16e`. That audit SHA is older than current main, but the subsequent 13 commits to current main changed only documentation/data according to the repository comparison; no source-code file changed. Therefore the source-level finding remains applicable while its provenance must be stated as an audit performed at `cd10c25f...`.

The first open composition seam identified is:

`PerceptionSnapshot(environment/world evidence) → CapabilityReadinessService(normalized required capability/affordance)`.

Observed source structure:
- `TaskContextAssembler` builds `PerceptionSnapshot` containing `EnvironmentSelfModel` and `WorldModelSnapshot`.
- `AdaptiveTaskOrchestrator` later calls `CapabilityReadinessService.evaluate(intent, context)` using the `TaskContext`.
- `CapabilityReadinessService._required_capabilities()` currently maps known `intent_key` values to a finite capability vocabulary.
- The inspected path does not demonstrate a universal normalization from fresh environmental evidence to the required capability representation that downstream realization selection can consume.

This is a composition/integration finding, not proof that a new organ is required.

## DEVELOPMENTAL INTERPRETATION

This seam matters because teaching a genuinely unfamiliar application requires the system to be able to move from observed reality to reusable capability meaning.

The desired progression is:

`observe unfamiliar environment → identify concepts/affordances → formulate capability hypothesis → select safe realization → act → observe effect → verify → encode reusable capability → later reuse`.

A provider-specific recipe can demonstrate one task but does not by itself establish the universal learning mechanism.

## REQUIRED CONTROL

Before changing code:

`current objective → current truth → parent concept → first open edge → capability-fit actor → minimal discriminating experiment → observation → independent verification → delta`.

Do not replace this seam with a provider-specific integration or a new "brain" component.

## STATUS

- Human design intent: CANONICAL DEVELOPMENTAL CONTEXT.
- Experiential teaching mechanism: DESIGN / NOT RUNTIME CAUSALLY PROVEN.
- Universal capability acquisition from unfamiliar reality: OPEN.
- Consciousness/super-consciousness emergence: RESEARCH HYPOTHESIS / NOT PROVEN.
- First technical seam: `PerceptionSnapshot → capability representation`, pending controlled discriminating experiment.
