# BIO-R13 — DEVIN HANDOFF
## Causal sensitivity: prior outcome → next proposal/experiment — 2026-09-21

**Actor:** DEVIN  
**Mode:** bounded implementation + controlled test execution  
**Production mutation:** NO  
**Architecture change:** NO

## OBJECTIVE

Prove or falsify the narrow causal claim:

`different prior ExperimentRun outcome → different next ExperimentRecommendation / ToolEvolutionProposal / SandboxExperiment`

under otherwise matched conditions.

## CURRENT SOURCE RECONCILIATION

The current source already contains this path:

`ExperimentRun → ExperimentLab recommendation → ToolDiscovery/ToolEvolution → ToolEvolutionProposal → AutonomousValidationCycle → SandboxExperiment → ExperimentLab.record_outcome`.

It also contains:

`ExperimentRecommendation → ToolTeachService._preferred_external_tool_id() → external assistant routing`.

Therefore do NOT repeat the older claim that Recommendation has no consumer.

The unresolved question is now causal sensitivity of the next experimental/developmental proposal to the prior outcome.

## PROVENANCE

Before changing anything:
- run `git rev-parse HEAD`;
- record branch;
- record working-tree status;
- use exact current HEAD as the test baseline;
- do not rely on a historical SHA from this handoff as current truth.

Historical forensic snapshot:
`f0c98ca1af756273f14a7fae65fafa9bd69a3a30`.

## TEST DESIGN

Build a new isolated test on a temporary/experimental branch or test-only worktree.

### Control

Same:
- subject_key;
- domain;
- objective;
- candidate universe;
- tool registry availability;
- world/environment state;
- configuration signatures;
- governance state.

Create a prior outcome A and persist it through the real `ExperimentLab.record_outcome()` / repository path.

Then run the existing downstream path that derives the next recommendation/proposal and observe the next `ToolEvolutionProposal` / `SandboxExperiment`.

### Treatment

Use the same inputs, but change only the prior outcome evidence in a way that should alter the ranking/learning state.

Persist through the same production methods.

Run the same downstream path.

Observe whether the next recommendation/proposal/experiment differs.

## REQUIRED ATTRIBUTION

A difference counts only if it is attributable to the changed prior outcome.

Exclude:
- hard-coded winner;
- assistant_preference shortcut;
- manually injected candidate;
- changed tool availability;
- changed world-model blocker;
- random/non-deterministic ranking;
- unrelated timestamp logic;
- different candidate universe;
- different governance state.

## NEGATIVE CONTROL

Use an outcome mutation that should NOT change the downstream decision.

The test should demonstrate that the causal path is sensitive where expected and stable where it should be stable.

## COLD-RELOAD

Where practical, persist, restart/reconstruct the relevant repository/service state, and repeat the downstream read.

Distinguish:

`persistence → reload`

from:

`reload → causal decision change`.

## OBSERVABLE CHAIN

Capture:

`prior ExperimentRun`
→ `persisted representation`
→ `ExperimentRecommendation`
→ `ToolEvolutionProposal`
→ `AutonomousValidationCycle`
→ `SandboxExperiment`

Record IDs/keys for each step.

## EPISTEMIC CLASSIFICATION

Return one of:

- CAUSALLY PROVEN
- OBSERVED BUT NOT CAUSALLY ATTRIBUTABLE
- PATH EXISTS BUT OUTCOME SENSITIVITY NOT PROVEN
- NOT REPRODUCIBLE
- CONTRADICTED

Do not promote persistence to learning automatically.

## NO PRODUCTION CHANGES

Do not change:
- `ExperimentLab`;
- `ToolEvolutionMonitor`;
- `AutonomousValidationCycleService`;
- `SandboxExperimentService`;
- `ToolTeachService`;

unless a tiny test fixture/helper is strictly necessary outside production code.

If the experiment cannot be constructed faithfully without production modification, STOP and report the exact semantic/access blocker.

## DELIVERABLE

Return:

### A. PROVENANCE
branch, HEAD, working tree.

### B. TEST ARTIFACT
exact file path, commit SHA and artifact hash if available.

### C. CONTROL
exact persisted outcome and downstream proposal/experiment.

### D. TREATMENT
exact changed outcome and downstream proposal/experiment.

### E. ATTRIBUTION
why the observed difference is or is not caused by the prior outcome.

### F. NEGATIVE CONTROL
result and interpretation.

### G. COLD RELOAD
result.

### H. FIRST OPEN EDGE
single remaining causal edge after this test.

### I. NEXT ACTOR
Recommend the next actor by capability/access/evidence fit.

## IMPORTANT

This experiment is not L5, not I0, not I1 and not I2.

It is a scientific/developmental circuit experiment focused on whether verified prior outcomes can causally generate a different subsequent experiment through the existing IABV organs.

No new architecture should be introduced until this causal boundary is understood.
