# IABV v1.5 — CHAT-ARCH 2026-09-17-007
## L5 Competitive Selection Result — Pending Independent Audit

## PURPOSE

Preserve the new competitive-selection experiment result before independent Sonnet adjudication, while keeping epistemic status separate from the test's local PASS status.

## PROVENANCE

- experiment branch: `experiment/l5-competitive-selection-2026-09-17`
- HEAD: `d77cbc6015a8358c9005d475c9799efc9791f8f6`
- experiment file: `IABV_v1.5/tests/test_l5_competitive_selection.py`
- file SHA-256: `FC516313BF125F0D52FEF3DB8B9762108DE6DE0E3471301C218A79072D3705EC`
- experiment commit parent: `f3e8a21c58fd73ad1b09ae11abae0cce915138cb`
- working tree reported clean

## EXPERIMENT

The new test exercises the normal production `InteractionModeSelector.select()` path with two competing candidates.

CONTROL:

- candidate A has the stronger baseline history;
- candidate B has no prior success history;
- winner is candidate A.

TREATMENT:

- same candidate universe and request;
- same availability and adapter;
- candidate B receives one `VerifiedTransition` through `InteractionLearningService.learn_from_verified_transition()`;
- treatment creates a fresh repository, registry, and selector;
- winner is candidate B.

The test does not directly invoke `_assess_candidate()` as its decision boundary, does not force the winner, does not hard-code the score, and does not use a preferred-tool shortcut.

Reported Windows execution:

- Windows 11
- Python 3.14.4
- pytest 9.0.3
- exact test: `tests/test_l5_competitive_selection.py::test_l5_competitive_selection_winner_changes`
- result: PASS
- exit code: 0
- stderr: empty

## CURRENT EVIDENCE DELTA

The experiment establishes, subject to independent audit, this downstream chain:

`persisted verified-transition learning state`
→ `fresh repository/registry/selector`
→ `InteractionModeSelector.select()`
→ `two-candidate competitive ranking`
→ `winner changes`

The production selector source confirms that `select()` refreshes cards, builds assessments, sorts by `total_score` descending, and returns `ModeSelectionDecision.selected_tool_id`.

The current scoring implementation gives `learned_pattern` a +1.8 weighted contribution and also derives pattern-based stability/frequency from the same learning state. Therefore the observed winner change should be attributed to the full learned-pattern state contribution unless an audit isolates the individual terms.

## EPISTEMIC BOUNDARY

The test constructs `VerifiedTransition` manually. Fields such as `verification_status='verified'`, `action_result_observed=True`, and `observed_state_source='independent_filesystem_observation'` are fixture declarations inside the test; the test itself does not perform the claimed real-world write and independent filesystem observation.

Therefore the strongest currently safe claim is:

`a persisted verified-transition learning input can causally change a competitive selector decision through the normal InteractionModeSelector.select() path after reload.`

This is stronger than the prior score-only artifact, but it does NOT by itself prove the full real-world experience → independent observation/verification → learning → selection L5 loop.

## STATUS PENDING SONNET

Required independent checks:

1. verify branch/commit/file identity and exact test execution provenance;
2. verify both arms have identical non-learning candidate/request/availability conditions;
3. verify the candidate ranking and score delta are produced by production selector logic;
4. rule out hidden selector shortcuts or stale state;
5. assess whether the causal attribution should be to `learned_pattern` specifically or to the aggregate persisted pattern-derived state;
6. assess the synthetic `VerifiedTransition` legitimacy boundary;
7. classify evidence into STATE_CHANGE / SCORE_CHANGE / DECISION_CHANGE / BEHAVIOR_CHANGE / WORLD_OUTCOME_CHANGE;
8. assign an independent L5 status without treating pytest PASS as epistemic proof.

## NEXT ACTOR

Sonnet — independent forensic adjudication.

No Codex intervention is currently justified. No Opus 5 intervention is justified unless Sonnet identifies a genuine architecture-level contradiction that the smallest experiment cannot resolve.
