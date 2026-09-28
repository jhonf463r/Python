# BIO-UNIVERSAL-09.11-R32-G2 v2 — ChatGPT Implementation Contract Reconciliation

## Status

The Sonnet implementation-contract specification is substantively accepted for contract B+C, but implementation is paused for two precise semantic corrections.

## Canonical accepted contract

- `ExternalWorkerTelemetry` and `worker_kind` remain external-worker-only.
- `metacognitive_evaluation` is generic ExperimentRun-level evidence produced by TaskOutcomeRecorder.
- OSES owns conversion of that evidence into calibration findings.
- `_task_packet_pattern_findings()` remains task-packet/worker-scoped.
- No `worker_kind='ollama'`.
- Existing thresholds remain unchanged.

## Correction 1 — method-name collision

The proposed new method name `_metacognitive_calibration_findings()` is NOT available for reuse.

At the pinned baseline, OSES already defines and invokes:

`_metacognitive_calibration_findings(previous_review=..., experiment_runs=...)`

This existing method is a different metacognitive mechanism: it compares previous OSES findings/ledger state against post-review outcomes. It must remain intact.

Therefore the extracted raw-run consumer needs a distinct name, preferably:

`_experiment_run_metacognitive_findings(*, experiment_runs)`

or an equally explicit name that distinguishes it from the existing previous-review calibration method.

This is a semantic identity boundary, not merely a cosmetic rename.

## Correction 2 — R-1 observation-unit collapse must NOT be silently included in the minimal seam

The proposal to collapse ExperimentRuns by `linked_run_id` would change the measurement unit of existing metacognitive evidence. TaskOutcomeRecorder creates one ExperimentRun per subject_key, and different subject keys can legitimately represent distinct recommendation evaluations even when they share one execution.

Therefore:
- preserve existing ExperimentRun-level measurement in the first seam implementation;
- do NOT select an arbitrary “first evaluation” per linked execution;
- preserve all existing subject-key lanes for the generic consumer unless a separate contract decision explicitly defines execution-level aggregation as the canonical statistical unit.

The negative knowledge remains:

`3 subject-key ExperimentRuns sharing one execution != 3 independent experiences`.

This is a constraint on experimental proof and statistical interpretation, not yet a reason to change production measurement semantics.

The next runtime causal experiment must use multiple distinct production `linked_run_id` executions when claiming >=3 independent observations. A separate aggregation design can be evaluated later if required.

## Correction 3 — evidence_basis eligibility is structural, not evidence-quality proof

TaskOutcomeRecorder constructs `metadata['evidence_basis']` with a dict fallback, including `{}` when upstream evidence_basis is absent.

OSES currently counts a run as eligible when:

`evidence_basis is not None`

Therefore the existing `total >= 5` gate should remain unchanged for this seam, but it must be described as a structural eligibility predicate, not as proof that five runs have substantive evidence.

Do not change the predicate in this implementation.

## Test isolation finding

The independent Linux reproduction of the existing tests passed 11 tests but created:

`data/evolution/adaptive_weights/metacognitive_adjustments.json`

containing `local|codex: 0.15`.

This is explained by tests that instantiate `AdaptiveWeightLayer()` without `persistence_path`; the class then falls back to `Path.cwd()/data/evolution/adaptive_weights/`.

By contrast, AppBootstrap explicitly supplies a workspace-scoped persistence path.

Classification:
- test-isolation defect: YES;
- production persistence defect established by this observation: NO;
- new OSES tests must use a workspace-scoped AdaptiveWeightLayer/persistence path.

## Canonical minimal seam after correction

`build_review()`
→ existing `_task_packet_pattern_findings()` (worker/task-packet only)
→ new `_experiment_run_metacognitive_findings(experiment_runs=...)` (generic run-level metacognition)
→ dedupe
→ review assembly
→ existing `_apply_metacognitive_feedback()`
→ `AdaptiveWeightLayer.apply_metacognitive_adjustment()`

The existing `_metacognitive_calibration_findings(previous_review=...)` remains separate and unchanged.

## Required regression contract

- existing worker tests keep the same categories/payload;
- local/run-level ExperimentRun with metacognitive_evaluation and no worker_kind reaches the generic consumer;
- no local run receives worker_kind;
- no duplicated metacognitive findings;
- generic findings use the existing feedback path;
- threshold values remain unchanged;
- tests are isolated from repository cwd persistence.

## Current causal frontier

After implementation, the first unproven production edge remains:

`multiple independent local production executions`
→ `ExperimentRun.metacognitive_evaluation`
→ `generic OSES consumer`
→ `finding`

The R32-G2 v2 single execution cannot itself prove the >=3 independent-observation requirement.

## Routing

Next actor: SONNET for a delta-only correction of the implementation-contract specification covering:
1. distinct method name;
2. removal of automatic linked_run_id collapse from the minimal seam;
3. explicit treatment of `evidence_basis is not None` as structural eligibility;
4. test-isolation requirement.

No implementation yet.
