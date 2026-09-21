# BIO-R14 — SONNET HANDOFF
## Auditar la arista causal mínima outcome → propuesta — 2026-09-21

**NEXT ACTOR:** SONNET  
**MODE:** forensic/static + test-design audit  
**NO PRODUCTION IMPLEMENTATION**

## CONTEXT

BIO-R13 was attempted by Devin but did not execute. Reported provenance:
- branch: `devin/i0-external-route-target-fix-2026-09-20`
- HEAD: `f0c98ca1af756273f14a7fae65fafa9bd69a3a30`
- working tree: 5738 untracked files
- runtime: Python 3.14.4 win32
- no test artifact, no command execution, no control/treatment

Verdict: **BLOCKED**, not disproven.

The exact blocker was the cost/complexity of building a deterministic full runtime harness for `ToolEvolutionMonitor.build_status()` while controlling repository/storage/adaptive-weight state and all confounds.

## CURRENT RECONCILED FACT

Current source contains a real path:

`ExperimentRun → ExperimentRecommendation → ToolDiscovery/ToolEvolution → ToolEvolutionProposal → AutonomousValidationCycle → SandboxExperiment → ExperimentLab.record_outcome`.

Also:

`ExperimentRecommendation → ToolTeachService._preferred_external_tool_id() → real external route selection`.

Therefore the remaining question is NOT whether a consumer exists.

The remaining causal question is:

`different prior outcome → different later proposal/experiment`

under matched conditions.

## OBJECTIVE

Find the **smallest existing real-code seam** capable of discriminating outcome sensitivity, before investing in a full runtime harness.

Do not assume the entire `ToolEvolutionMonitor.build_status()` path must execute to gain useful causal evidence.

## REQUIRED INVESTIGATION

Inspect, in order of increasing scope:

1. `ExperimentLab.record_outcome()` and `run_experiment()`
2. `ExperimentLabRepository` persistence/read paths
3. `AdaptiveWeightLayer.suggest()`
4. `ToolEvolutionMonitor._grouped_runs()`
5. `ToolEvolutionMonitor._rank_profiles()`
6. `ToolEvolutionMonitor._proposal_for_subject()`
7. `ToolDiscoveryService._recommendation_from_runs()`
8. `ToolTeachService._preferred_external_tool_id()`
9. existing tests/fixtures around these components
10. `AutonomousValidationCycleService` only if necessary for the next edge

For every candidate seam determine:

- required inputs;
- whether function is deterministic for fixed inputs;
- hidden/persistent state;
- minimum fixture;
- whether it represents a real production path;
- whether its result is directly relevant to the causal claim.

## KEY DISTINCTION

Rank candidate seams by evidentiary strength:

**Level 1:** raw score/metric changes only  
**Level 2:** recommendation changes  
**Level 3:** ToolEvolutionProposal changes  
**Level 4:** SandboxExperiment candidate changes  
**Level 5:** actual subsequent decision/action changes

Do not call Level 1 proof of Level 5.

## SEARCH FOR EXISTING TEST SUPPORT

Before recommending new harness code, search existing tests for:

- `ExperimentLabRepository`
- `AdaptiveWeightLayer`
- `ToolEvolutionMonitor`
- `ToolDiscoveryService`
- `AutonomousValidationCycleService`
- `SandboxExperimentService`

Determine whether a fixture already provides sufficient deterministic state.

## IMPORTANT OBSERVATION

The current code suggests some functions may be pure-ish with explicit inputs, while the full monitor path depends on persistence and state.

Determine whether:

`matched ExperimentRun sets → AdaptiveWeightLayer.suggest() → ranked profiles → _proposal_for_subject()`

can be driven using a compact in-memory/persisted fixture.

If yes, propose this as the next minimum experiment.

If no, identify the exact earliest dependency that forces a larger harness.

## CAUSAL DESIGN

Construct the smallest possible:

### CONTROL

Prior run/outcome A.

### TREATMENT

Same runs/context except prior outcome B.

### OBSERVATION

Compare the earliest downstream artifact that changes:

`score → profile → ranking → recommendation → proposal → sandbox candidate`

### NEGATIVE CONTROL

A mutation that should not affect the target decision.

## CONFOUND CHECK

Explicitly rule out:

- assistant preference shortcuts;
- tool availability;
- world/environment blockers;
- candidate-universe differences;
- configuration-signature differences;
- persistent adaptive-weight state;
- stale cache;
- non-deterministic ordering;
- timestamps;
- residual process state.

## DO NOT IMPLEMENT

Do not modify production.

Do not create a new scientific coordinator.

Do not create a universal harness framework.

Do not alter the existing architecture.

If one test fixture/helper can isolate the seam, describe it and route implementation later.

## REQUIRED DELIVERABLE

### A. CURRENT PROVENANCE
Exact current branch + SHA after fresh GitHub read-back.

### B. BIO-R13 RECLASSIFICATION

State:

- BLOCKED before execution;
- not disproven;
- causal question remains open.

### C. CANDIDATE SEAMS

Table:

| Seam | Inputs | Hidden state | Deterministic? | Evidence level | Harness cost |
|---|---|---|---|---|---|

### D. SMALLEST DISCRIMINATING SEAM

Choose exactly one.

Format:

`producer → representation → function → observable output`

Explain why it is the earliest sufficient causal boundary.

### E. MINIMUM TEST DESIGN

Give exact control/treatment/negative-control construction.

### F. WHAT THIS WOULD PROVE

Explicitly distinguish:

- local causal sensitivity;
- recommendation-level causal sensitivity;
- proposal-level causal sensitivity;
- next-experiment causal sensitivity;
- full next-cycle causal learning.

### G. FIRST OPEN CAUSAL EDGE

One edge only.

### H. NEXT ACTOR

Choose:

DEVIN / CODEX / SONNET / OPUS 5 / ChatGPT

based on:

`objective → uncertainty → required capability → access → evidence cost`.

### I. STOP CONDITION

If the minimum seam still requires a full runtime harness, say so and explain precisely why.

## FINAL RULE

The goal is not to make the experiment executable at any cost.

The goal is to locate the **first causal boundary at which outcome information can be shown to influence later scientific/developmental choice** with the least confounding and least infrastructure.

Do not trade epistemic quality for convenience.
