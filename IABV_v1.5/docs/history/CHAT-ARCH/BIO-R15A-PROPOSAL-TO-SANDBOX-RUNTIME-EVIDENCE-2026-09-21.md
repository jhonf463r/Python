# BIO-R15A — ToolEvolutionProposal to SandboxExperiment runtime evidence

## Scope and provenance

This is a test-only, isolated reproduction of the production consumer boundary:

```text
ToolEvolutionProposal
  -> AutonomousValidationCycleService.run_once()
  -> _recommendation_from_proposal()
  -> SandboxExperimentService.validate_recommendation()
  -> SandboxExperiment
```

No production source was changed.  No external tool was invoked.  The sandbox service records a synthetic sandbox outcome; it is not evidence of external action.

## Control

The harness supplied one actionable production `ToolEvolutionProposal` (`proposal_kind=validate_replacement`) through `ToolEvolutionStatus.proposals`.  It used a neutral `WorldModelSnapshot(block_records=[])` and no environment model, so `paused_reason` was empty.

`AutonomousValidationCycleService.run_once()` selected the proposal and executed its production `_recommendation_from_proposal()` conversion.  The test-only recording subclass then received the produced recommendation, immediately delegated to `SandboxExperimentService.validate_recommendation()` via `super()`, and captured the returned production `SandboxExperiment`.

Observed continuity:

| Stage | Identity / value |
| --- | --- |
| Proposal | `bio-r15a:proposal-to-sandbox|validate_replacement|language_understanding|chatgpt|chatgpt-browser|code_agent|codex|codex-plan` |
| Recommendation proposal key | same proposal key |
| Recommendation baseline | `chatgpt`, `language_understanding`, `chatgpt-browser`, score `0.42`, confidence `0.84` |
| Sandbox subject | `sandbox:bio-r15a:proposal-to-sandbox` |
| Sandbox candidate | `codex`, `code_agent` |
| Sandbox result | `experiment_id=c6eab636-8218-4749-97b6-fe1c07c7a538`, `verdict=doubtful`, `status=observed`, `promote_to_primary=false`, evidence strength `0.658` |

The first directly observable event is **validation invoked**.  The returned `SandboxExperiment` makes the boundary **INVOKED / OBSERVED**, reaching Level D.  Its `doubtful` verdict is an S6 evaluation result; it is not S4 execution or promotion.

## Treatment / negative control

The only relevant changed variable was removal of the candidate proposal (`ToolEvolutionStatus.proposals=[]`).  World-model and environment fixtures stayed equivalent.

The cycle returned `idle_empty`; the recording delegate observed `validate_recommendation_calls=0` and `sandbox_experiments_returned=0`.  With no candidate, the cycle does not evaluate proposal-specific scope inertia; this is recorded as `not_evaluated_no_candidate`, not an invented empty production field.

## Source alignment

The harness runs the production methods:

- `AutonomousValidationCycleService.run_once()`
- `AutonomousValidationCycleService._next_tool_evolution_candidate()`
- `AutonomousValidationCycleService._recommendation_from_proposal()`
- `SandboxExperimentService.validate_recommendation()`
- `SandboxExperimentService._record_sandbox_run()`

The recording class is observability-only: it records arguments and return value, then delegates directly to the production validation implementation.  It does not fabricate an `ExperimentRecommendation` or `SandboxExperiment`.

## Verdict

**CAUSAL_RUNTIME_CONFIRMED.** In the controlled fixture, an actionable `ToolEvolutionProposal` reached production conversion, invoked the real validation implementation, and returned a real `SandboxExperiment`. Removing only that proposal resulted in no validation invocation and no sandbox experiment from this branch.

## First open edge and negative knowledge

The next frontier remains:

```text
SandboxExperiment -> actual experimental action
```

- `SandboxExperiment -> actual external execution`: **NOT_TESTED**
- external effect: **NOT_TESTED**
- independently verified outcome: **NOT_TESTED**
- outcome -> next-cycle proposal: **NOT_TESTED**
- development: **NOT_PROVEN**
- evolution: **NOT_PROVEN**
- open-ended development: **NOT_PROVEN**
