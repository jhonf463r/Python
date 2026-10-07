# CHAT-ARCH-2026-10-07-140 — capability → realization implementation-review blocker reconciliation

## PURPOSE

Reconcile the CODEX implementation-review response received after the 2026-10-07 empty-set closure against the current executable baseline and active IABV routing state.

## PROVENANCE

- Supplied CODEX review targets checkout `07ebffc8f866fc99a3f78091dcd1edd456a0da00` / tree `f0e1294982479426b140eab21f16f2f839504413`, clean.
- Direct GitHub compare confirms `07ebffc8f866fc99a3f78091dcd1edd456a0da00 → 6ce3fc6b747bb1e8375cd6928cb065a33e439559` contains documentation/history changes only. No executable-source changes were detected in the coordination movement.
- No source modification, test execution or runtime was performed in this reconciliation.

## CODEX MATERIAL FINDING

CODEX identifies:

`FIRST IMPLEMENTATION CONTRACT BLOCKER: per-ToolTask capability subset is not derivable from existing exact semantics`

The report specifically establishes that:
- `CapabilityReadinessService.evaluate(intent, context)` derives a list from the complete `TaskIntent`;
- `AdaptiveSession.capability_readiness` stores that list;
- `build_task_for_session()` reconstructs an `InferenceRequest` without directly transporting `session.capability_readiness`;
- `ToolTask` has no first-class required-capability field in the baseline;
- no inspected rule states how multiple session/intent capabilities partition into one individual `ToolTask`;
- `ToolTaskStatus.DEFERRED` exists but is not itself a proof of propagation.

## DIRECT RECONCILIATION

The blocker is **credible and currently supported**, but is not yet promoted to an independently verified permanent contract because CODEX is the implementation-review actor, not the independent challenger.

The source adds an important detail:

- `ExecutionPlaybook.steps` already has a `capability_id` field, but the current planner assigns only one capability to the execution step (the weakest unresolved capability, otherwise the first capability). This is insufficient evidence for a conjunctive multi-capability `ToolTask.required_capability_ids` contract.
- `StrategyPack.required_capabilities` exists, but prior reconciliation established contract inconsistencies and no proven operative dependence sufficient to treat it as the exact per-task requirement source.
- `InferenceRequest.allowed_tools` uses the existing coarse `ToolCapability` vocabulary and must not be silently substituted for `CapabilityReadiness.capability_id`.

Therefore the remaining question is not whether a field can technically be added. It is whether the existing composition already defines the semantic unit boundary needed to populate it without inventing meaning.

## CURRENT INTERPRETATION

`NO_ELIGIBLE_REALIZATION` conceptual contract remains closed:

`eligible realization set = ∅ → explicit no-realization outcome → governed defer/fail-closed → no fallback resurrection`

But the implementation route is **not authorized** because the exact source of per-`ToolTask` requirements is unresolved.

This preserves:
- `implemented ≠ proven`
- `defined ≠ wired`
- `declared ≠ consumed`
- `session requirement set ≠ automatically per-task requirement set`
- `ToolCapability ≠ universal capability identity`
- `eligible_tool_ids` remains ephemeral selection state, never durable `ToolTask` truth.

## NEXT DISCRIMINATING EDGE

Before implementation, independently test whether one existing semantic unit already defines the task boundary:

`TaskIntent / AdaptiveSession → playbook phase or execution step → ToolTask`

and whether that unit provides an exact, reproducible capability subset.

Possible outcomes:

1. **Existing exact rule found:** REUSE/COMPOSE it; no new requirement-derivation mechanism.
2. **Single-ToolTask == whole intent is explicitly established and safe for all constrained callers:** bounded composition may use the whole required set.
3. **Task granularity is variable / multi-step:** keep the blocker; define the smallest existing-owner contract for task-level requirement mapping.
4. **Only heuristic/text/task-kind mappings exist:** they are not sufficient proof of capability identity transport.

Do not use naming similarity, the weakest-capability heuristic, `StrategyPack.required_capabilities`, `ToolCapability`, or task text as an unproved semantic bridge.

## ROUTING

Next actor: **SONNET / CLAUDE**

Capability required: independent static semantic-contract audit / composition archaeology.

Question:
Can the existing codebase derive the exact required capability subset for each `ToolTask` without inventing semantics, or is this genuinely a blocking contract gap?

No implementation, source modification, tests or runtime in this audit.

## STOP CONDITION

Stop when one of the four outcomes above is demonstrated with exact producer → transformation → consumer evidence and at least one counterexample/negative case where the alternative interpretation would be wrong.
