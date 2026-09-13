# IABV v1.5 — Expectation/Contract Design Reconciliation

## Status
Current design remains a hypothesis, not an implementation mandate.

## Established
- `verify_intent_routing()` is a real narrow precedent for EXPECTATION → DISCOVER ACTUAL → COMPARE → DETECT.
- Current organs provide source inspection, runtime evidence, context, state, contradiction reasoning and audit data, but no demonstrated generalized cross-organ expectation/contract representation.
- P040 remains historical evidence of stale source/consumer assumptions discovered only on a real runtime path.
- UK-15 temporal interpretation was superseded: previous recommendation → prediction extraction → current run → new future-facing recommendation is a valid lifecycle.

## Leading hypothesis
A small new representation may be required to make implicit producer/consumer expectations explicit and verifiable, but the exact conceptual split between Expectation, Contract, Observation, Actual and VerificationResult is not yet settled.

## Important epistemic correction
Do not equate evidence source with epistemic truth. `SOURCE_DERIVED` or `RUNTIME_DERIVED` may have high evidence confidence while remaining inference rather than FACT. `FACT / INFERENCE / ASSUMPTION` should not be collapsed into a single confidence scalar without further justification.

## Design risk
The proposed model risks overgrowth through large enumerations of contract kinds, temporal/semantic dictionaries, validity windows, episode scopes and multiple separate records. Before implementation, an adversarial review must minimize the model and prove which concepts are indispensable.

## Current gate
DO NOT IMPLEMENT.

Next required action: adversarially minimize and challenge the conceptual model, especially the distinction Expectation vs Contract vs Observation/Actual vs VerificationResult, provenance/epistemic status, and whether temporal/semantic constraints are model data or verifier behavior.
