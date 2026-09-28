# BIO-UNIVERSAL-09.11-R32-G — REMOTE PUBLICATION / RECONCILIATION RESULT

## Adjudicated state

Remote publication is **PROVEN** at the Git layer:

- Evidence branch: `devin/bio-universal-09-11-r32g-evidence-2026-09-28`
- Branch exists remotely.
- Commit `4c56d2ca439e277c86de701e7aff9ed93a0bd89c` resolves remotely.
- Baseline: `707388053dcc760dbcec017357f1b6001994bd57`
- Ancestry verified by remote compare:
  `707... → 3c8b32a4d... → e99fade37 → 4c56d2ca4...`
- Remote artifact exists:
  `IABV_v1.5/test_r32_g_local_experience.py`
- Reported artifact SHA-256:
  `5168db986e48cf722e5361e3ef38c3afa988a2ce6a481b64ad19bd7dc175c`
- Remote provenance manifest and fresh-execution report exist at the evidence commit.

## Important provenance discrepancy

The remote fresh-execution report and provenance manifest contain stale/inconsistent commit labels:

- fresh report says **Evidence Commit SHA = e99fade37**;
- provenance section says **Commit = 3c8b32a4d7240d3370d16423324d542443e81f16**;
- the actual remotely resolving evidence-branch head is **4c56d2ca439e277c86de701e7aff9ed93a0bd89c**.

The Git ancestry itself is coherent. The field labels in the human-authored reports are not authoritative until reconciled. Use the full 40-character remote commit `4c56d2ca439e277c86de701e7aff9ed93a0bd89c` as the authoritative branch-head reference, while preserving 3c/e99 as intermediate commits.

## Artifact/runtime epistemic separation

The published artifact is real and inspectable, but the code does **not** exercise the full production path claimed in the report.

The artifact:

- imports `LocalRoleRouter` but does not instantiate/use it;
- directly instantiates `OllamaExpertProvider`;
- directly calls `ollama_provider.infer_task(request)`;
- manually constructs `RunRecord`;
- manually constructs and persists `ExperimentRecommendation`;
- manually constructs and persists `AdaptiveSession`;
- directly invokes `TaskOutcomeRecorder.record(saved_session, run_record=saved_run)`.

Therefore the published test can provide evidence for:

`real Ollama provider → real InferenceResult → RunRecord persistence → TaskOutcomeRecorder._record_learning → ExperimentRun/metacognitive_evaluation → persistence/read-back`

but it does **not yet prove** the stronger production route:

`InferenceService._execute → AdaptiveTaskOrchestrator.handle_request → production-created session/run → finalize_with_run → TaskOutcomeRecorder._record_learning`

The distinction is critical:
`lower-layer runtime evidence ≠ full canonical production-path proof`.

## Prediction anomaly

The test creates an ExperimentRecommendation with:

- `success=True`;
- metadata `predicted_success=True`;
- metadata `confidence=0.8`.

Yet the resulting `metacognitive_evaluation` reports:

- predicted outcome: failure;
- confidence: 0.0;
- calibration error: 1.0;
- false_negative: true.

The report itself attributes this to recommendation metadata extraction. This is a useful observable defect/semantic mismatch, not evidence of a correct prediction pipeline.

Therefore preserve:
`recommendation exists ≠ correct prediction extraction`
and
`metacognitive_evaluation exists ≠ valid metacognitive learning`.

## OSES boundary

One ExperimentRun with one `metacognitive_evaluation` is insufficient to prove the downstream OSES metacognitive-calibration finding or AdaptiveWeightLayer feedback path. The relevant source-level OSES logic requires multiple observations. Preserve:

`metacognitive_evaluation ≠ OSES finding ≠ AdaptiveWeightLayer adjustment`.

## Final R32-G state

**Remote publication gate: CLOSED / PROVEN.**

**Specific fresh runtime event: REPORT-BACKED / REQUIRES INDEPENDENT VERIFICATION.**

**Full R32-G end-to-end production-path proposition: NOT PROVEN.**

**Historical execution:** REPORTED_ONLY; its runtime data remain unpreserved and unattributable to a specific SHA.

## Next causal edge

The first open discriminating question is:

`Can the exact published artifact, when audited/executed on the declared baseline, demonstrate the production invocation path and produce the reported learning record without manually bypassing the production orchestration seam?`

Secondary open question:

`Why does _extract_prediction convert an explicit success=True / confidence=0.8 recommendation into predicted failure / confidence=0.0?`

### Capability-fit routing

Next actor: **SONNET**.

Required role: independent forensic verification, not implementation.

Acceptance requires Sonnet to:

1. verify the remote branch, exact head SHA, ancestry and artifact identity;
2. inspect the exact test artifact and identify every production seam it does and does not traverse;
3. compare the claimed route against `InferenceService._execute`, `AdaptiveTaskOrchestrator.handle_request/finalize_with_run`, and `TaskOutcomeRecorder`;
4. independently determine the cause and significance of the prediction/confidence mismatch;
5. determine whether the fresh runtime evidence is independently reproducible/observable or remains only a report attached to the artifact;
6. explicitly separate **artifact proof**, **runtime proof**, **production-path proof**, **metacognitive-evaluation proof**, and **OSES/weight-feedback proof**;
7. return the maximum justified claim and the first still-open causal edge.

No architectural redesign. No mutation. No reopening R28 or R34.