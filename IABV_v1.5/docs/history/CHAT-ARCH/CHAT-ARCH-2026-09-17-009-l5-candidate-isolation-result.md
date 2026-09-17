# IABV v1.5 — CHAT-ARCH 2026-09-17-009
## L5 Candidate Isolation Result — Remote Reconciliation / Next Independent Audit

## PURPOSE

Preserve the material delta from the second Devin experiment and reconcile the reported result against directly readable GitHub state before promoting any L5 conclusion.

## VERIFIED PROVENANCE

Repository: `jhonf463r/Python`

Branch:
`experiment/l5-competitive-selection-2026-09-17`

Remote branch HEAD:
`5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb`

IMPORTANT REPORT DISCREPANCY:
Devin's report contained `5ef1009c1a6728332b3c4a0869b6291e7b3b6586`, which does not match the remote branch HEAD. Direct GitHub branch read-back resolves the actual commit to `5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb`.

This is a report/provenance transcription discrepancy, not an artifact absence: the actual remote commit exists and its message identifies the candidate-isolation experiment.

Test:
`IABV_v1.5/tests/test_l5_candidate_isolation.py`

Reported and remotely embedded SHA-256:
`6879F0B6F6041A5D0724260E0E1C642FA83FAC8419FC3D02C5DA5D36C0B86549`

Direct remote file read-back succeeds and returns the same test content.

Parent:
`d77cbc6015a8358c9005d475c9799efc9791f8f6`

## CURRENT EXPERIMENTAL RESULT

The new test invokes the normal production:

`InteractionModeSelector.select()`

with:

`allowed_tool_ids=["candidate_a", "candidate_b"]`

in both control and treatment.

Control:

`candidate_a = 9.62`
`candidate_b = 8.345`
`winner = candidate_a`

Treatment:

`candidate_a = 9.62`
`candidate_b = 10.895`
`winner = candidate_b`

The decision metadata records only A and B in the candidate ranking after filtering.

The test therefore closes the previous hidden-candidate confound for the exact experiment.

## INDEPENDENT SOURCE RECONCILIATION

Direct source read-back confirms:

1. `allowed_tool_ids` is passed in BOTH arms;
2. `select()` filters candidate cards before scoring;
3. candidate A and B are both present in both arms;
4. the final decision comes from normal selector sorting and `ModeSelectionDecision.selected_tool_id`;
5. the test does not hard-code the winner or inject the final score;
6. treatment uses `InteractionLearningService.learn_from_verified_transition()`;
7. treatment discards the prior repository/registry/learning service and creates fresh repository, registry and selector objects;
8. the `VerifiedTransition` remains manually constructed in the test.

## SCORE FORENSICS

The report's claimed `+2.55` B delta is consistent with the production scoring implementation:

- `learned_pattern`: 0.0 → 1.0 = `+1.8` weighted contribution;
- stability: control baseline 0.55 → treatment 1.0 = `+0.675`;
- frequency: 0.0 → 0.125 = `+0.075`;
- total = `+2.55`.

The report line stating `stability (1.0 → 1.0)` is inconsistent with the production formula for candidate B and should not be propagated. The correct B transition is approximately `0.55 → 1.0`.

Causal attribution should therefore be to the aggregate persisted/reloaded pattern-derived learning state, not to the `learned_pattern` term in isolation.

## EPISTEMIC STATUS

This experiment materially strengthens the causal edge from:

`persisted verified-transition learning input`
→ `reload`
→ `normal competitive selector`
→ `candidate ranking`
→ `selected decision change`

The isolated A/B candidate universe removes the previous methodological confound.

However, the input remains a synthetic `VerifiedTransition` fixture. The test does not itself execute the described world action, create `test.py`, observe filesystem state, or independently verify the result.

Therefore the full strong L5 chain is still not automatically closed if the canonical definition requires:

`legitimate real observed/verified experience`
→ `persistence`
→ `reload`
→ `future production selector decision`
→ `decision difference`
→ `causal attribution`.

Prior G3 evidence remains the separate source for legitimate real-world verified-transition persistence and must not be silently merged with this synthetic fixture as though this experiment alone demonstrated the whole edge.

## CURRENT GATE

The selector-level causal decision gate is now strongly supported, subject to independent audit:

`STATE_CHANGE = PROVEN`
`SCORE_CHANGE = PROVEN`
`DECISION_CHANGE = PROVEN for the isolated synthetic-learning experiment`
`BEHAVIOR_CHANGE = NOT MEASURED`
`WORLD_OUTCOME_CHANGE = NOT MEASURED`

Do not advance to L6 until the L5 definition itself has been independently adjudicated.

## NEW NEGATIVE KNOWLEDGE

- `reported HEAD != remote HEAD until direct read-back`;
- `small numeric reporting errors must be reconciled against source formula`;
- `allowed_tool_ids can be used as a real selector-level candidate isolation boundary when both candidates remain admitted`;
- `candidate-ranking metadata can expose the effective selection universe`;
- `winner flip after isolation is stronger decision evidence than winner flip with hidden candidates`;
- `aggregate learned-state effect != one score term alone`;
- `synthetic VerifiedTransition != real world verified episode`.

Existing negative knowledge remains active:

- `test pass != causal proof`;
- `persistence != learning`;
- `decision change != behavior change`;
- `behavior change != world outcome`;
- `fresh reproduction != historical execution proof`;
- `report != artifact != commit != execution`.

## SYMBIOSIS / CAPABILITY ECONOMY UPDATE

This cycle validates the capability-routing hypothesis:

`bounded test change + Windows runtime`
→ Devin

The hidden-candidate defect was discovered by independent Sonnet/Claude audit and then closed by Devin without Codex.

No current capability gap justifies Codex for this selector-isolation edge.

Three Opus 5 interventions remain reserved for genuine architectural contradiction or higher-order causal ambiguity.

The broader benchmark objective remains active:

`IABV improvement should reduce avoidable external interventions while increasing verification quality`.

## NEXT ACTOR

`SONNET`

Reason:

The implementation/test edge has now been exercised twice, and the exact artifact is remotely readable. The remaining uncertainty is independent adjudication of whether the isolated decision change plus prior G3 legitimate experience can be composed into the chosen L5 claim without an unsupported causal leap.

## NEXT SMALLEST DISCRIMINATING ACTION

Independently audit the remotely readable `5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb` experiment and determine whether the isolated winner flip, together with prior G3 legitimate-transition evidence, is sufficient to close the canonical L5 boundary or whether one additional experiment is required to connect the legitimate real-world experience itself to the future selector decision.

Do not modify production code.
Do not modify the preserved evidence artifacts.
Do not advance to L6 during this audit.

END
