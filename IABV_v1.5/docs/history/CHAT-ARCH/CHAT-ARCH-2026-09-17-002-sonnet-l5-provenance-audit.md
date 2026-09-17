# IABV v1.5 — 2026-09-17 Sonnet L5 Provenance / Contradiction Audit

## PURPOSE

This record preserves the independent forensic audit of the reported L5 causal-decision experiment. Its primary purpose is to prevent an unverified AI report from being promoted to canonical evidence and to route the contradiction to the actor best positioned to resolve it.

## SOURCE

Independent audit report supplied from Claude Sonnet on 2026-09-17.

Repository independently checked against `jhonf463r/Python`.

## ARTIFACT VERIFICATION

Reported artifact:

`tests/test_l5_causal_decision.py`

Reported branch:

`codex/world-grounded-learning-bridge`

Reported SHA:

`55d3e2c93807202ec5d0177eda163e8de10418ef`

Sonnet verified:

- `origin/codex/world-grounded-learning-bridge` resolves to `55d3e2c...`;
- checkout of that SHA is clean;
- the commit modifies only `tests/windows_e2e/test_g2_goal_to_action_plan.py`;
- `tests/test_l5_causal_decision.py` is absent from the tree at that SHA;
- it is absent from the clean working tree after checkout;
- Sonnet reports no occurrence of the file in the observable repository history or branch set searched.

Therefore the prior report claiming an L5 test at that SHA cannot be promoted as evidence from that artifact.

## CURRENT ADJUDICATION

`L5 = NOT PROVEN`

More precisely: the previously reported L5 experiment is currently **UNVERIFIABLE / ARTIFACT-ABSENT**.

The numeric claims:

- Control `learned_pattern=0.0`, `total_score=7.545`;
- Treatment `learned_pattern=1.0`, `total_score=10.095`;
- `pattern_id=8e8f6695-8bdb-4d6b-922d-fa6a11728245`;
- `pytest: 1 passed in 0.98s`;

have no independently recoverable primary artifact under the reported provenance and therefore are not accepted as causal evidence.

## WHAT REMAINS VALID

The underlying G3 mechanism remains independently relevant:

`real planner → real filesystem mutation → independent observation/SHA verification → VerifiedTransition → SQLite persistence → fresh repository/database reader → verified_transition_success_count 0→1`

This does not, by itself, prove a future selector decision was changed by the concrete prior experience.

The production source also contains both `InteractionModeSelector._best_pattern()` and `ToolTeachService._select_mode()`, but their existence is source evidence only until the exact L5 artifact/path is recovered and audited.

## CONTRADICTION

`REPORT: L5 test exists and passed`

versus

`REPOSITORY READ-BACK: no L5 test exists at reported SHA, branch, working tree, or observable history searched`

This contradiction is itself canonical knowledge and must not be silently resolved by assuming an unreported artifact.

## EPISTEMIC RULES REINFORCED

`report != evidence`

`commit SHA != working-tree artifact`

`source trace != runtime causality`

`persistence != reuse`

`selector capability != selector invocation`

`decision difference != causal decision difference`

## ROUTING DECISION

The current bottleneck is not experiment design and not L6 execution. It is artifact/provenance reconciliation.

Next actor: **Codex**, because the disputed report and cited branch/commit are attributed to Codex work and the first required action is to account for the missing primary artifact or retract the claim.

Codex must not be asked to redesign L5. It must first establish one of these states with verifiable repository evidence:

1. a real branch/ref + commit SHA containing `tests/test_l5_causal_decision.py`, with the exact artifact recoverable; or
2. a documented explanation of the actual artifact/runtime location used, including provenance sufficient for independent checkout/reproduction; or
3. an explicit retraction that the reported L5 experiment did not occur as described.

No new L5 interpretation should be promoted until one of those conditions is satisfied.

## NEXT CAUSAL EDGE

`report → primary artifact provenance`

Only after this edge is closed should the system continue to:

`artifact → exact experiment path → persistence → reload → selector → controlled decision difference`

## NO IMPLEMENTATION AUTHORIZED BY THIS RECORD

This checkpoint is an evidence/provenance adjudication only. It does not authorize production changes.
