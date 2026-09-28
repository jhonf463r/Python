# BIO-UNIVERSAL-09.11-R32-G2 — PRODUCTION RUNTIME RESULT

## CANONICAL RECONCILIATION STATUS

This record preserves the runtime report supplied to the canonical memory process.

Important provenance boundary:
- The supplied report identifies evidence branch `devin/bio-universal-09-11-r32g2-production-runtime-2026-09-28` and head `6ed48b8c6`.
- Direct GitHub read-back at reconciliation time could not resolve that branch/ref; the short SHA also did not resolve as a GitHub commit.
- Therefore the runtime claims below are **REPORT-BACKED / USER-SUPPLIED**, not remotely attributable execution evidence.
- The report is still valuable as negative/observational knowledge and may guide the next runtime attempt.
- R32-G2 is **BLOCKED AFTER EXECUTION ATTEMPT**, not PROVEN and not DISPROVEN.

## REPORTED CURRENT_TRUTH

The R32-G2 experiment was executed but blocked during the warm-up path because Ollama exceeded the configured 30-second timeout. A script encoding failure occurred while printing the result and is separate from the production timeout.

## REPORTED BASELINE

`707388053dcc760dbcec017357f1b6001994bd57`

## REPORTED EVIDENCE

- Branch: `devin/bio-universal-09-11-r32g2-production-runtime-2026-09-28`
- Reported head: `6ed48b8c6`
- Reported artifact SHA256: `55f8e33d408e32d6565e7b9d810b5794d4c145e413c5cffd015d347bbb8c8508`
- Worktree: `C:/IABV_WORKTREES/bio-universal-09.11-r22b-runtime/IABV_v1.5`
- Git status reported modified data/`__pycache__` plus test artifact.
- Isolated workspace:
  `C:\IABV_WORKTREES\bio-universal-09.11-r22b-runtime\IABV_v1.5\data\r32g2_isolated\run_0bec66b5203843eca0cfb687f43cf5`
- Effective AdaptiveWeightLayer path:
  `C:\IABV_WORKTREES\bio-universal-09.11-r22b-runtime\IABV_v1.5\data\r32g2_isolated\run_0bec66b5203843eca0cfb687f43cf5\data\evolution\adaptive_weights\metacognitive_adjustments.json`
- Python: 3.13.2
- Ollama endpoint: `http://127.0.0.1:11434`
- Ollama model: `phi3:latest`
- Ollama model availability: reported YES via `curl /api/tags`
- Reported response time: ~54 seconds versus configured 30-second timeout.

## REPORTED PRODUCTION OBSERVATION

Reported as observed:
- isolated `AppBootstrap` construction succeeded;
- `InferenceService` was available;
- `ExperimentLab` was available;
- AdaptiveWeightLayer used an isolated workspace-derived persistence path;
- `InferenceService.infer_task()` was invoked;
- `AdaptiveTaskOrchestrator.handle_request()` was invoked;
- the real Ollama provider path reached a timeout;
- no production `RunRecord`, system-generated recommendation, session finalization, prediction consumption or `metacognitive_evaluation` was produced.

## FALSE-POSITIVE CONTROLS REPORTED

The run did not manually construct:
- `RunRecord`;
- `AdaptiveSession`;
- `ExperimentRecommendation`;
- `TaskOutcomeRecorder` invocation;
- `metacognitive_evaluation`.

No synthetic learning result was injected.

## RECONCILED EPISTEMIC STATUS

### Proven/observed at the report level

`AppBootstrap(isolated workspace) → InferenceService.infer_task() → AdaptiveTaskOrchestrator` was reportedly entered, and the real Ollama inference attempt timed out.

### Not proven

- successful real Ollama completion through the production path;
- production RunRecord creation after successful completion;
- production finalization into TaskOutcomeRecorder;
- system-generated prior recommendation;
- recommendation-derived prediction extraction;
- causal `metacognitive_evaluation`;
- persistence/read-back of the resulting learning event;
- remote attribution of this specific run to the reported branch/head.

## NEGATIVE KNOWLEDGE

1. Ollama model availability does not imply that the selected model can complete within the provider's configured timeout.
2. The current `phi3:latest` runtime observation reported ~54 seconds, exceeding the 30-second provider timeout.
3. An isolated AppBootstrap can be constructed successfully even when the first real model call cannot complete.
4. A script encoding failure can obscure reporting after the production path has already encountered a runtime timeout; these are separate failure classes.
5. A real provider timeout blocks downstream lifecycle evidence; absence of RunRecord in this attempt must not be interpreted as evidence that the downstream path is unwired.
6. No manual object construction was used in this attempt, so the boundary failure is materially closer to the intended production path than the earlier R32-G artifact.
7. The reported branch/SHA remains unverified remotely; runtime observation and Git provenance remain separate claims.

## FIRST OPEN CAUSAL EDGE

`real Ollama completion under configured timeout → production RunRecord → finalize_with_run() → TaskOutcomeRecorder.record() → _record_learning() → prior recommendation lookup → prediction → metacognitive_evaluation`

## NEXT EXPERIMENTAL PRINCIPLE

Do not modify the learning/recorder contract merely because this run timed out.

The smallest discriminating next action is to preserve the exact production bootstrap seam and alter only the runtime variable necessary to obtain a real completion within the existing timeout contract:
1. inventory actually installed Ollama models;
2. choose an installed model that can satisfy the 30-second production timeout;
3. set `IABV_OLLAMA_MODEL` before AppBootstrap construction;
4. correct the script's UTF-8-safe reporting;
5. rerun the same two-phase warm-up → target production experiment;
6. preserve exact runtime provenance and publish remotely before verification.

A timeout-class change must remain distinct from any future production-code change to provider timeout semantics.

## INDEPENDENT VERIFICATION REQUIRED

After successful remote publication, Sonnet should independently verify:
- exact artifact and commit;
- actual production call path;
- `raw_output['local_chat_llm']` evidence;
- system-generated recommendation identity/confidence;
- target consumption of that prior recommendation;
- production RunRecord/session linkage;
- `metacognitive_evaluation` derivation;
- absence of manual/synthetic shortcuts.

No OSES or AdaptiveWeightLayer learning claim should be promoted from a single successful evaluation without its own aggregation/causal evidence.
