# BIO-UNIVERSAL-09.11-R32-G2V4 — SEMANTIC CONTRACT ADJUDICATION

## PURPOSE

Canonical reconciliation of the R32-G2 V4 provider-failure experiment and the subsequent independent static adjudication of the provider-failure versus actual_success contract.

## PROVENANCE
- Repository: jhonf463r/Python
- Project: IABV_v1.5
- R32-G2 implementation ancestor: 79bdd8ab47206e9f5a07fdc2151923f934da474a
- V4 branch: devin/r32g2-v4-threshold-crossing-2026-09-28
- V4 HEAD: e67a78a9be4b16718caaa5b04c112c5fbfc8c5f2
- Baseline: 707388053dcc760dbcec017357f1b6001994bd57
- GitHub compare 79bdd8a...e67a78a: exactly one commit; V4 added only documentation/harness artifacts and did not modify production source.
- Canonical-memory writeback branch: main

## V4 RUNTIME FINDING

The V4 experiment used request.metadata.override_model with a nonexistent Ollama model.

Observed runtime behavior:
provider HTTP 404 → adaptive recovery → successful outcome.

Reported target ExperimentRuns therefore had:
- success=True
- actual_outcome=success
- false_positive=False
- false_negative=False

Negative knowledge:
A real provider/request failure does not necessarily become RunStatus.FAILED or actual_success=False in the adaptive production path.

## INDEPENDENT STATIC ADJUDICATION

Sonnet performed source-level archaeology on main. Git compare establishes that V4 introduced no production-code divergence from the R32-G2 implementation ancestor, so the adjudicated contracts apply to the V4 code path.

The source contract is:
TaskOutcomeRecorder.actual_success = (run_record.status == RunStatus.SUCCESS)

InferenceService._execute derives:
RunStatus.PARTIAL if result.used_fallback else RunStatus.SUCCESS

The outer exception path can create/persist RunStatus.FAILED only when an exception actually escapes the adaptive path.

The adaptive local-chat path behaves differently:
- _maybe_invoke_local_chat_llm() catches provider errors.
- It returns a dict containing error information rather than an InferenceResult whose used_fallback is true.
- _build_result() can substitute assistant_guidance.prompt or a rendered summary.
- used_fallback remains false unless explicitly propagated.
- The resulting RunRecord is therefore SUCCESS under the existing status contract.

The separate LocalRoleRouter general→visual fallback path is not the adaptive infer_task execution path and must not be used to explain the V4 adaptive result.

## SEMANTIC MODEL

Canonical decision: SEMANTIC_MODEL = 3 — separate task outcome from provider-health/recovery cause while preserving the existing graduated outcome contract.

Canonical semantics:
- RunStatus.SUCCESS = the predicted production route completed without a degraded substitution.
- RunStatus.PARTIAL = a usable result was produced through an explicit degraded fallback/recovery.
- RunStatus.FAILED = no usable result was produced and the failure escapes to the outer execution boundary.
- used_fallback means degraded production-route recovery, not generic provider failure and not task failure.
- actual_success remains exactly run_record.status == RunStatus.SUCCESS.

Do not redefine actual_success merely to make an experiment cross an OSES threshold.

## REQUEST FAILURE VS PROVIDER FAILURE

The V4 nonexistent-model case is specifically a request/configuration failure surfaced through a provider error path, not proof of a generic provider outage.

Therefore: PROVIDER_FAILURE_SHOULD_COUNT_AS_TASK_FAILURE = CONTEXT-DEPENDENT.

The metacognitive outcome must reflect the contract actually being predicted. A malformed request/model-selection error should not automatically be treated as calibration evidence about the normal reliability of a route.

## FIRST OPEN CAUSAL EDGE

The current first open edge is:
llm_chat[error] → InferenceResult degradation signal in _build_result().

The error is currently retained in raw_output['local_chat_llm'] but does not enter the status/degradation channel consumed by InferenceService.

Before any source change, one runtime observation remains useful:
- determine whether the V4 404 target actually returned the templated assistant_guidance response to the user;
- if yes, the production system delivered a substitute response without reporting it through the existing degradation contract;
- if no, and the effective response was empty, the semantic classification may instead require FAILED.

## LEGITIMATE ARCHITECTURAL CHANGE

The smallest justified change, if independently approved, is at the boundary where llm_chat becomes an InferenceResult:
- propagate explicit degraded-route semantics when the system actually substitutes a response;
- add a cause such as fallback_reason to distinguish request/configuration failure, provider unavailability, and empty response;
- preserve the existing used_fallback → PARTIAL mapping;
- preserve actual_success = status == SUCCESS;
- do not change OSES thresholds;
- do not synthesize metacognitive evidence.

This change must be justified as contract consistency, not as an experiment-enabling trick.

## CLOSED / NOT CLOSED

CLOSED:
- V4 override_model does not itself produce a threshold-crossing failure in the adaptive path.
- used_fallback already has an established degraded-recovery meaning.
- The general→visual router fallback is a different execution path.
- actual_success should not be redefined.

NOT CLOSED:
- whether the V4 404 response was actually the templated substitute at the user-facing boundary;
- whether a real production experiment can legitimately generate PARTIAL or FAILED for the predicted route without changing production;
- OSES threshold crossing;
- real OSES finding;
- AWL adjustment;
- future decision influence.

## NEXT ROUTING

No further blind runtime retries of the nonexistent-model strategy.

Next required capability is bounded source/contract implementation only after the final user-facing substitution fact is reconciled.

After a legitimate contract-consistency change, runtime validation must prove:
real degraded/failure event → RunStatus != SUCCESS → actual_success=False → finalized ExperimentRun → metacognitive_evaluation → threshold → OSES finding → AWL adjustment.

Do not jump from this adjudication directly to future-decision influence.

## EPISTEMIC BOUNDARIES

provider HTTP failure != RunStatus.FAILED

RunStatus.SUCCESS != provider-health perfection

provider failure != task failure in every context

metacognitive_evaluation != OSES finding

OSES finding != AWL adjustment

AWL adjustment != future decision influence

N subject-key ExperimentRuns != N independent experiences

runtime report != independently re-executed runtime proof