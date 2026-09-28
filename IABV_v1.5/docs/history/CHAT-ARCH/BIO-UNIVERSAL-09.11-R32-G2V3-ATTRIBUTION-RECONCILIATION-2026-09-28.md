# BIO-UNIVERSAL-09.11-R32-G2-V3 — ATTRIBUTION RECONCILIATION

## OBJECTIVE

Resolve the V3 apparent contradiction between the reported empty warm-up `subject_keys/recommendations` and the three target `metacognitive_evaluation` records, using direct source and remote Git evidence.

## PROVENANCE

V3 runtime branch:
`devin/r32g2-v3-production-runtime-discriminating-2026-09-28`

V3 HEAD:
`d611eefb8eb76578a84880ed27184d32ab4248a3`

V3 commit parent:
`79bdd8ab47206e9f5a07fdc2151923f934da474a`

Baseline:
`707388053dcc760dbcec017357f1b6001994bd57`

V3 report blob:
`ae4a83f8530afe070a23a80114a57f59927f416d`

V3 harness blob:
`7f1b1678e619c86394060a04cd705db93622ceda`

## KEY FINDING

The V3 report's statement:

`warm-up subject_keys = []`
`warm-up recommendations = []`

is not evidence that the production warm-up created no subject keys.

The V3 harness reads:

`warmup_result.result.raw_output['adaptive_session']['subject_keys']`

but the source-verified `AdaptiveSession` model has no top-level `subject_keys` field.

The source-verified `TaskOutcomeRecorder._subject_keys()` computes the actual learning keys and returns up to three keys including `general`. During production finalization, `TaskOutcomeRecorder._record_learning()` iterates those keys, calls `latest_recommendation()`, executes `ExperimentLab.record_outcome()`, and `record_outcome()` saves a new `ExperimentRecommendation`.

The computed keys are retained in:

`session.metadata['adaptive_learning']['subject_keys']`

not:

`session.subject_keys`.

Therefore the harness accessor defaults to `[]` even when real subject keys were used and recommendations were created.

## SOURCE CHAIN

Production inference path:

`InferenceService.infer_task()`
→ `AdaptiveTaskOrchestrator.handle_request()`
→ real local chat
→ `RunRecord`
→ `AdaptiveTaskOrchestrator.finalize_with_run()`
→ `TaskOutcomeRecorder.record(session, run_record)`
→ `TaskOutcomeRecorder._record_learning()`

Within `_record_learning()`:

`_subject_keys()`
→ for each subject key, `latest_recommendation()`
→ `_extract_prediction(previous)`
→ `ExperimentLab.record_outcome()`
→ new recommendation saved
→ `_evaluate_prediction()`
→ `metacognitive_evaluation` saved when prediction exists.

The V3 harness's warm-up recommendation inspection is therefore a bad read location, not a valid negative observation.

## WHY THE THREE TARGET EVALUATIONS ARE SOURCE-CONSISTENT

For a fresh workspace, a warm-up finalization can create a recommendation for `general` because `_subject_keys()` always includes `general`.

Each target also includes `general` in its computed subject keys.

The target's `latest_recommendation(domain='language', subject_key='general')` can therefore retrieve the warm-up recommendation, even though the harness incorrectly reported the warm-up list as empty.

Because the three target prompts differ, their comparison-scope keys can differ, explaining why only the shared `general` lane naturally carries a previous recommendation and therefore a `metacognitive_evaluation` in the reported result.

This is a source-level explanation of the reported pattern; the exact consumed recommendation IDs still require raw persisted repository evidence or direct target-side capture to be independently attributed.

## CORRECTED NEGATIVE KNOWLEDGE

Invalidate the prior V3 claim:

`warm-up did NOT generate subject_keys`.

Replace it with:

`the V3 harness did NOT read the actual subject-key location; the empty list is an observability/accessor artifact`.

Valid negative knowledge remains:

- only one target subject-key lane (`general`) produced metacognitive evaluations in the reported V3 data;
- the observed calibration population did not cross the OSES thresholds;
- no real OSES metacognitive finding or AWL adjustment was observed.

## CAUSAL STATUS

V3 now has a coherent source explanation for the three reported `metacognitive_evaluation` records.

However, independent runtime attribution is still limited because the raw `evidence.json` referenced by the report was not published into the V3 commit.

Therefore:

- V3 provenance = CONFIRMED remotely.
- production path = report-backed and source-consistent.
- metacognitive-evaluation origin = SOURCE-EXPLAINED, but exact recommendation ID attribution remains UNPROVEN.
- generic OSES consumer path = source-wired and exercised by the V3 review according to the report, but raw runtime evidence is not independently read back.
- threshold state = NOT-CROSSED.
- real OSES finding = NOT OBSERVED.
- real AWL adjustment = NOT OBSERVED.
- adjustment → future decision influence = NOT PROVEN.

## FIRST OPEN CAUSAL EDGE

The first unresolved causal edge is:

`real threshold-crossing metacognitive population → real OSES finding → AdaptiveWeightLayer adjustment`

The later edge:

`AdaptiveWeightLayer adjustment → future decision influence`

must NOT be promoted as the immediate next edge because no real finding or adjustment has yet occurred in V3.

## NEXT DISCRIMINATING ACTION

Before attempting adaptive-causality proof, capture one real threshold-crossing population without synthetic metadata.

The experiment must observe the actual target-side recommendation immediately before each production execution and persist:

- recommendation ID;
- subject key;
- confidence;
- target RunRecord ID;
- linked_run_id;
- resulting ExperimentRun ID;
- prediction;
- actual outcome;
- calibration error;
- OSES finding;
- AWL adjustment state before/after.

Do not use the V3 harness's `adaptive_session.subject_keys` accessor again. Read the actual `session.metadata['adaptive_learning']['subject_keys']` or directly inspect the persisted ExperimentRun/recommendation repository.

No source changes are authorized merely to improve observability during this causal experiment.
