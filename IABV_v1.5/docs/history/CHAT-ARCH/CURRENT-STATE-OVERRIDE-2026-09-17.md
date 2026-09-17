# IABV v1.5 — CURRENT STATE OVERRIDE — 2026-09-17

## PURPOSE

This is an append-only operational overlay for the 2026-09-17 L5 causal-learning frontier. It supersedes only the stale provenance/routing statements identified below; it does not rewrite historical records.

## CURRENT VERIFIED FACTS

Repository: `jhonf463r/Python`

Canonical technical baseline for this investigation:

`4b04566686c40cc6d48d64edb411b36867c54dcf`

Experimental causal-routing branch:

`2d472ccaaf5a37773fed1d8e389e580812599c03`

World-grounded-learning branch:

`55d3e2c93807202ec5d0177eda163e8de10418ef`

## L5 ARTIFACT PROVENANCE — NOW CLOSED AT PUBLICATION LEVEL

The recovered file:

`IABV_v1.5/tests/test_l5_causal_decision.py`

is remotely preserved on:

`audit/l5-artifact-evidence-2026-09-17`

Branch HEAD:

`f3e8a21c58fd73ad1b09ae11abae0cce915138cb`

Git blob:

`2844537f80c190a1351dac3a95f35f80cf79dc19`

SHA-256:

`E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`

Byte size:

`7392`

Direct GitHub branch read-back and file read-back are now successful.

Therefore the previous status "remote evidence branch not verified" is SUPERSEDED for the publication/provenance question.

## FRESH EXECUTION EVIDENCE

Devin reported a fresh Windows 11 execution of the byte-identical artifact:

`python -m pytest -vv -s tests/test_l5_causal_decision.py::test_l5_verified_experience_changes_selector_scoring`

Reported environment:

- Python `3.14.4`
- pytest `9.0.3`
- result `1 passed in 2.72s`
- exit code `0`
- artifact SHA before = after

Observed report:

Control:

`learned_pattern=0.0`, `total_score=7.545`, `pattern_id=None`

Treatment:

`learned_pattern=1.0`, `total_score=10.095`, `pattern_id` present

This is runtime evidence reported by Devin, not an independent reproduction by this chat.

## CURRENT L5 EPISTEMIC STATUS

`L5 = NOT PROVEN UNDER THE STRONG CANONICAL DEFINITION`

The strongest justified intermediate claim is:

`verified experience fixture → production learning service → persistence → fresh repository reload → internal selector scoring consumes learned state → learned-pattern contribution and total score change`

The test directly invokes:

`InteractionModeSelector._assess_candidate()`

It does not establish:

`normal application selector → multiple competing candidates → future selected decision changes`

The treatment also constructs a `VerifiedTransition` in the test, so the test itself does not independently establish that the experience came from a freshly observed real-world episode. G3 is the relevant prior evidence for legitimate verified-transition persistence.

## REQUIRED NEXT EDGE

The next smallest discriminating experiment is:

`legitimate verified experience`
→ `persist`
→ `reload`
→ `normal production selector`
→ `multiple competing candidates`
→ `selected decision differs`
→ `difference attributable specifically to prior verified experience`

Only after that should L6 address:

`decision change → real behavioral/world effect`

## ROUTING

Next actor: **SONNET** for independent forensic audit of the now-remotely-readable artifact and Devin's fresh execution evidence.

If Sonnet confirms only selector-scoring causality, route the minimal multi-candidate normal-selector experiment to **DEVIN**.

If Sonnet finds a genuine architecture contradiction, route to **OPUS 5**.

Do not use **CODEX** for the already-closed artifact-location/provenance problem unless a new repository/provenance uncertainty appears.

## MEMORY METHOD UPDATE

For future chats, use:

`objective → boundary → relevant memory → current read-back → capability/access fit → experiment → independent verification → knowledge delta → writeback`

The availability of the required filesystem/runtime is part of effective capability fit.

A fixed AI sequence is not canonical.

## SELF / WORLD OBSERVABILITY DIRECTION

When the objective concerns IABV "perceiving itself", the first investigation target should be the composition of existing organs rather than a new monolithic self-model:

`UniversalPerception / PerceptionCrossValidator
→ WorldModel / EnvironmentSelfModel / OrganismStateSnapshot
→ evidence / DecisionAuditTrail / RuntimeAuditTracer
→ governance / decision
→ outcome
→ adaptive update`

`AdaptiveWeightLayer` and related weighting mechanisms should be investigated as candidate state-update substrates, not called a proven universal "space-time reality weight" algorithm.

The project has evidence of distributed self/world observation infrastructure but not of a single unified self-model that is proven to drive system-wide decisions.

## NEGATIVE KNOWLEDGE

`score difference != decision difference`

`internal helper consumption != normal application selection`

`fresh reproduction != historical execution proof`

`artifact publication != L5 proof`

`manual test fixture != real world experience`

`distributed self-observation organs != unified self-model`

`adaptive weighting != proven universal reality weighting`

END OF OVERRIDE
