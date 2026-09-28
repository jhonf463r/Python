# BIO-UNIVERSAL-09.11-R32-G2 v2 — Sonnet Contract Archaeology Reconciliation

## Provenance
- Repository: `jhonf463r/Python`
- Technical baseline: `707388053dcc760dbcec017357f1b6001994bd57`
- Runtime observation state: report-backed; no new runtime execution in this archaeology.
- Purpose: reconcile semantic ownership before any implementation.

## Canonical finding

The R32-G2 v2 gap is best classified as a **cross-organ contract/composition defect**, not missing data and not merely missing wiring.

1. `ExternalWorkerTelemetry` is semantically scoped to externally dispatched workers. `worker_kind` is populated by external tool/adapters.
2. `TaskOutcomeRecorder` produces generic `metacognitive_evaluation` for adaptive executions with prior recommendations and stores those fields in run metadata. It may also merge the metacognitive fields into the `worker_telemetry` dictionary as a carrier, but this does not establish worker identity.
3. OSES `_task_packet_pattern_findings()` reads `metacognitive_evaluation` only inside a task-packet/worker analysis path and gates that entire section with `wt_total >= 3`.

Therefore:

`local production metacognitive_evaluation` → `OSES worker/task-packet metacognitive reader`

is a real semantic discontinuity.

## Contract decision

Canonical interpretation: **B + C**.

- Keep `worker_kind` external-worker-only.
- Keep `ExternalWorkerTelemetry` semantically external-worker scoped.
- Keep `_task_packet_pattern_findings()` as a task-packet/worker analysis surface.
- Treat `metacognitive_evaluation` as generic ExperimentRun-level evidence.
- A generic OSES consumer for run-level metacognitive calibration is not present in the inspected source and would be the likely existing-organ destination if implementation is later justified.
- Do **not** invent `worker_kind='ollama'`; that would alter semantic identity rather than close a legitimate causal edge.

## First causal boundary

The first broken edge is:

`metacognitive_evaluation` [OBSERVED] → OSES generic consumption [DEFINED/WIRED for worker path, NOT INVOKED for local chat]

The immediate reason is the external-worker gate.

This is not the only gate that must be preserved:

- `_task_packet_pattern_findings()` returns no findings when fewer than 5 eligible runs (those with `evidence_basis`) are present.
- Metacognitive calibration additionally needs at least 3 calibration-error observations and average error > 0.4; over/under-confidence use FP/FN thresholds.
- R32-G2 v2 itself reported calibration error 0.2992 and FP=FN=0, so it cannot exercise the finding branch even after removing the worker gate.

## Observation-unit warning

The three R32-G2 v2 target `ExperimentRun` records are three subject-key lanes derived from one target execution. They must not be treated as three independent real-world experiences merely because there are three rows. Any future calibration experiment must use multiple distinct production executions (or otherwise declare and enforce its statistical unit) to avoid pseudo-replication.

## Next discriminating action

Before implementation, use the existing Windows workspace read-only to:
1. count eligible `ExperimentRun` records seen by OSES (`evidence_basis` present);
2. count records with non-empty external `worker_telemetry.worker_kind`;
3. report whether `wt_total >= 3` is ever reached in real persisted operational data;
4. report the canonical run identity / subject-key relationship for the R32-G2 v2 target;
5. invoke the existing OSES method read-only and print `total`, `wt_total`, calibration sample size, average calibration error, FP/FN and returned categories.

No rerun, no mutation, no telemetry injection, no threshold changes, no implementation.

## Negative knowledge

- `worker_telemetry` being a dict does not mean a worker exists.
- `metacognitive_evaluation` and external worker identity have different semantic lifecycles.
- OSES `_metacognitive_accuracy_findings()` and `_metacognitive_calibration_findings()` operate on OSES findings/ledger state, not as an existing generic consumer of raw run-level `metacognitive_evaluation`.
- Existing metacognitive worker tests seed worker identity and evaluation together; they do not demonstrate recorder → OSES production causality.
