# CHAT-ARCH 2026-10-03-005 — BIO-04 Provider Seam Ownership Still Ambiguous

## PURPOSE

Absorb the latest BIO-04 production-composition archaeology. The universal inference gap remains confirmed, but the exact single production owner for the OSES inference seam is not yet demonstrated.

## VERIFIED FACTS

Code target:
`d1a55897bf7f758914b8237d48ae43f245f06592`.

Production composition:
- AppBootstrap creates local providers and injects them into LocalRoleRouter.
- AppBootstrap creates AdaptiveModelSelector and injects it into CloudReasoningPlannerService and OSES.
- ProviderRouter exists but was not found constructed in `src`; observed constructions are in tests.
- OSES own inference path still uses module-level cloud/local functions rather than ProviderRouter or LocalRoleRouter.
- AdaptiveModelSelector is used by OSES for degradation findings, not for selecting OSES's own inference realization.

## MICRO-RUNTIME EVIDENCE

A provider-level micro-harness used `InferenceRequest` + `OllamaExpertProvider.answer_user()` and observed an initial timeout followed by an internal retry and a consumable `InferenceResult`. This was not an end-to-end bootstrap/OSES run and must not be promoted to end-to-end production evidence.

## OWNERSHIP DELTA

Current candidate owners remain:
- OSES: semantic meaning and response contract;
- InferenceRequest: partial common requirement transport;
- LocalRoleRouter: local role/provider routing in existing production flows;
- AdaptiveModelSelector: narrower cloud/model selection;
- adapters: provider-specific translation;
- no demonstrated single owner yet for universal OSES selection + contract validation + fallback.

Therefore:
`UNIVERSAL GAP CONFIRMED / OWNERSHIP SEAM OPEN`.

## NEGATIVE KNOWLEDGE

Do not:
- activate ProviderRouter merely because it exists;
- promote AdaptiveModelSelector to universal authority;
- insert a new inference orchestrator;
- route OSES directly to adapters as the "solution";
- add provider-specific knobs before the common ownership seam is proven.

## NEXT OPEN EDGE

`OSES requirements/output contract → existing production ownership boundary that can select/configure a realization and return contract-validation state to fallback`.

Next action should remain read-only production-composition/ownership archaeology or a tightly bounded architecture experiment that can distinguish the candidate seams without creating new architecture.
