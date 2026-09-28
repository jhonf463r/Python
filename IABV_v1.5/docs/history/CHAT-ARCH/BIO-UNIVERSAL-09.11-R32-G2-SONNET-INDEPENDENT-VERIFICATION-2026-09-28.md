# BIO-UNIVERSAL-09.11-R32-G2 — SONNET INDEPENDENT VERIFICATION RESULT

## ADJUDICATION

**R32-G2 = PARTIALLY PROVEN / PENDING RUNTIME ATTRIBUTION.**

Independent runtime execution was not possible because the verifier environment did not provide Windows/Ollama. Therefore runtime-specific claims remain report-backed.

## VERIFIED

### GIT_PROVENANCE
PROVEN.

The reported baseline `707388053dcc760dbcec017357f1b6001994bd57` is the ancestor of evidence head `13c7f31425fb9055d9e4be4957bb7e497a9d171e`. GitHub compare reports exactly 3 commits ahead, 0 behind, with only the three R32-G2 evidence files added and no production source modifications.

### ARTIFACT_IDENTITY
PROVEN.

The 290-line artifact:
`IABV_v1.5/test_r32g2_production_runtime.py`
does not manually construct `RunRecord`, `AdaptiveSession`, or `ExperimentRecommendation`; it does not call `TaskOutcomeRecorder.record()` directly; and it does not inject `metacognitive_evaluation` or use synthetic inference.

### SOURCE_PATH
PROVEN AT SOURCE LEVEL.

At the pinned baseline:

`InferenceService.infer_task()`
→ `_execute()`
→ `AdaptiveTaskOrchestrator.handle_request()`
→ local-chat provider
→ production `RunRecord`
→ `finalize_with_run()`
→ `TaskOutcomeRecorder.record(session, run_record=...)`
→ `_record_learning()`

The verifier independently read the relevant source for the production execution/finalization and recorder path.

### SYSTEM-GENERATED RECOMMENDATION MECHANISM
PROVEN AT SOURCE LEVEL.

`TaskOutcomeRecorder._record_learning()` calls:

`latest_recommendation(domain, subject_key)`

before:

`experiment_lab.record_outcome(...)`

and derives prediction from the previous recommendation before evaluating the current run.

### PREDICTION EXTRACTION
PROVEN AT SOURCE LEVEL.

The predicted-success logic uses the previous recommendation's top-level `confidence` together with route/assistant-kind matching.

### METACOGNITIVE EVALUATION DERIVATION
PROVEN AT SOURCE LEVEL.

`_evaluate_prediction(prediction, actual_success)` computes the evaluation, including:

`predicted_outcome`
`actual_outcome`
`confidence`
`calibration_error`
`false_positive`
`false_negative`

The reported numeric result is internally consistent:
`|0.7008 - 1.0| = 0.2992`.

## REPORT-BACKED

- actual Windows runtime invocation;
- Ollama participation for those exact run IDs;
- exact model sent to Ollama;
- exact warm-up and target RunRecord identities;
- exact recommendation instance consumed;
- actual target-side `latest_recommendation()` result;
- exact ExperimentRun instance carrying the evaluation.

## CRITICAL FINDING: EFFECTIVE OLLAMA MODEL UNKNOWN

The report's:

`gemma3:1b configured`

does not establish the effective model.

The artifact preserves an existing `IABV_OLLAMA_MODEL` value and only defaults to `gemma3:1b` when that environment variable is absent.

The provider then uses:

`request.metadata['override_model'] or self.config.model`.

The production `RunRecord.executor_model` is not sufficient because source tracing shows it can come from the static `RoleRoute.model_name` rather than the HTTP payload model.

The local-chat evidence has empty `provider_model`.

Therefore neither `gemma3:1b` nor `qwen3:8b` is proven as the model actually sent to Ollama.

## CRITICAL FINDING: RECOMMENDATION CONSUMPTION IS ONLY PARTIALLY PROVEN

The production recorder iterates multiple subject keys and calls `latest_recommendation()` for each.

The harness:
1. takes `subject_keys[0]`;
2. selects the first recommendation matching that subject key;
3. runs the target;
4. scans ExperimentRuns and takes the first run containing `metacognitive_evaluation`.

The evaluation payload does not contain `recommendation_id` or another direct recommendation identity.

Therefore the exact claim:

`target consumed recommendation 7541abd2-846b-4dd3-835f-7dfc3458ec70`

is not established.

What is supported is weaker:

`target consumed a previous recommendation matching the relevant prediction contract`

subject to runtime evidence.

## PERSISTENCE BOUNDARY

The repository's `list_runs()` performs fresh JSON loads for each returned run rather than using a metadata cache, so the read-back is a real disk read. However, the harness repeats it in the same process and same repository instance. This proves persistence/readability, but not independent runtime attribution.

## FINAL CLASSIFICATION

`R32-G2 = PARTIALLY PROVEN / PENDING RUNTIME ATTRIBUTION`.

No implementation change is required yet.

## MINIMUM NEXT EXPERIMENT

A Windows re-run of the same production artifact/harness, with read-only evidence capture for:

1. exact model actually loaded/sent by Ollama, preferably `/api/ps` and a request-side record if available;
2. exact `recommendation_id` returned by `latest_recommendation()` for every subject key immediately before target;
3. exact subject key of every ExperimentRun carrying `metacognitive_evaluation`;
4. explicit mapping from target-side `latest_recommendation()` to the warm-up recommendation;
5. fresh repository-instance reload after closing/reconstructing the repository object.

Do not modify production learning semantics.

## NEGATIVE KNOWLEDGE

- configured model may differ from effective model;
- provider name `Ollama` does not identify the model;
- `RunRecord.executor_model` does not necessarily observe the HTTP model;
- recommendation existence does not prove target consumption;
- persistence does not prove causal attribution;
- `metacognitive_evaluation` does not imply OSES;
- OSES does not imply AdaptiveWeightLayer adjustment;
- adjustment does not imply future decision influence.
