# IABV v1.5 — CHAT-ARCH 2026-09-17-005
## L5 Methodological Audit Routing / Selector-Fixture Concern

## PURPOSE

Preserve the new evidence-boundary analysis performed after the L5 artifact was remotely published and independently read back.

This record does not promote L5. It records the exact reasons the next independent audit must inspect the test methodology rather than merely reproduce its passing output.

## CURRENT PROVENANCE STATE

The L5 artifact is remotely preserved and readable at:

`audit/l5-artifact-evidence-2026-09-17`

Commit:

`f3e8a21c58fd73ad1b09ae11abae0cce915138cb`

Artifact:

`IABV_v1.5/tests/test_l5_causal_decision.py`

Git blob:

`2844537f80c190a1351dac3a95f35f80cf79dc19`

SHA-256:

`E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`

Remote read-back: PROVEN.

The earlier artifact-location/provenance contradiction is therefore CLOSED.

## CURRENT FRESH-EXECUTION STATUS

Devin reported a fresh Windows execution of the byte-identical artifact:

`python -m pytest -vv -s tests/test_l5_causal_decision.py::test_l5_verified_experience_changes_selector_scoring`

with:

- Windows 11
- Python 3.14.4
- pytest 9.0.3
- `1 passed in 2.72s`
- exit code 0
- artifact SHA unchanged before/after

This execution remains producer-reported evidence. Historical execution provenance is not recovered.

## METHODOLOGICAL FRONTIER

The artifact does demonstrate a real intermediate edge:

`VerifiedTransition fixture
→ production InteractionLearningService
→ persistence
→ fresh ToolRecordRepository/AppDatabase instance
→ selector internal lookup
→ learned_pattern score changes`

Observed reported values:

Control:

`learned_pattern=0.0`

`total_score=7.545`

Treatment:

`learned_pattern=1.0`

`total_score=10.095`

The score delta `+2.55` is consistent with the production scoring formula at `_assess_candidate()` level:

- `learned_pattern`: `+1.8`
- pattern-derived stability increase: `+0.675`
- pattern-derived frequency increase: `+0.075`
- total: `+2.55`

Therefore the numerical delta is not merely a printed coincidence; the source formula explains it.

However:

`score difference != decision difference`

The test invokes the private helper:

`InteractionModeSelector._assess_candidate()`

and constructs only one candidate.

Therefore it does not itself demonstrate a competitive future selection change.

## NEW FIXTURE-CONSTRUCTION CONCERN

The test creates:

`registry = ToolRegistry(repository, adapters={})`

and later performs:

`del repository`

then creates:

`treatment_repository = ToolRecordRepository(...)`

`treatment_selector = InteractionModeSelector(registry, treatment_repository)`

but continues to obtain the candidate card through:

`registry.get_card('test_tool')`

The `ToolRegistry` retains its original repository reference. Therefore the treatment selector uses the new repository for learned-pattern/scoring lookup, while the candidate card is still retrieved through a registry bound to the original repository object.

The fresh pattern/state read is therefore not equivalent to a fully reconstructed selector+registry+repository object graph.

This does not by itself invalidate the observed score delta, but it is a material methodological issue that the independent auditor must classify explicitly:

`fresh persistence reader != fresh complete selector dependency graph`

The test report did not identify this distinction.

The evidence-preservation branch also reports a modified unrelated file:

`tests/windows_e2e/test_g2_goal_to_action_plan.py`

That unrelated dirty state must not be treated as artifact mutation. Artifact identity must continue to be determined by direct blob/hash read-back, not whole-worktree cleanliness.

## EXISTING PRODUCTION SELECTOR FACTS

At the cited production source (`55d3e2c...` ancestry), `InteractionModeSelector.select()`:

1. builds candidate cards from `self.registry.refresh_card(self.registry.list_cards())`;
2. optionally applies preferred-external selection;
3. otherwise calls `_assess_candidate()` for every candidate;
4. sorts assessments by `total_score` descending;
5. selects the highest-scoring candidate;
6. returns `ModeSelectionDecision` with selected tool metadata and scores.

The independent audit must determine the actual normal application entrypoint that invokes `InteractionModeSelector.select()` for the relevant workflow instead of assuming `ToolTeachService._select_mode()` by name.

## CURRENT L5 STATUS

`L5 = NOT PROVEN UNDER THE STRONG CANONICAL DEFINITION`

Strong canonical target:

`legitimate verified experience
→ persistence
→ reload
→ normal production selector
→ multiple competing candidates
→ selected decision differs
→ difference attributable specifically to prior verified experience`

Current evidence reaches only:

`verified experience fixture
→ persistence
→ reload
→ internal selector scoring
→ score/pattern-state difference`

## NEXT ACTOR

**SONNET**

Reason:

The remaining uncertainty is independent methodological and causal adjudication. Artifact provenance is already closed; repository archaeology should not be repeated.

## SONNET AUDIT MUST ANSWER

1. Is the L5 artifact internally valid as an intermediate scoring experiment?
2. Does the stale `ToolRegistry` repository binding materially affect the treatment measurement?
3. Does the one-candidate design permit any decision-difference claim?
4. Does the test exercise the normal production selector path or only a private helper?
5. Is the `VerifiedTransition` fixture a legitimate experience for the chosen L5 definition, or merely a valid synthetic learning input?
6. Can the `+2.55` delta be causally derived from production scoring code?
7. What exact edge is proven, and what exact edge remains open?
8. Is any minimal correction needed before a future multi-candidate experiment, and can it be isolated from production semantics?

## PROMPT ROUTING RULE

The next prompt must follow:

`OBJECTIVE
→ CURRENT VERIFIED STATE
→ EXACT PROVENANCE
→ CLOSED EDGES
→ OPEN CAUSAL EDGE
→ SPECIFIC FORENSIC QUESTIONS
→ FALSE-POSITIVE CONTROLS
→ STOP CONDITION
→ REQUIRED REPORT
→ NEXT ACTOR`

Do not send a generic “audit L5” request.

Do not request a broad architecture review.

Do not ask for a new CognitiveCore, SymbiosisBrain, universal weighting engine or additional memory subsystem.

## NEGATIVE KNOWLEDGE

- `artifact publication != L5 proof`
- `fresh reproduction != historical execution proof`
- `score difference != decision difference`
- `private helper != normal application selection`
- `one candidate != competitive decision`
- `fresh repository != necessarily fresh full dependency graph`
- `synthetic verified transition fixture != necessarily real observed-world experience`
- `worktree dirty != artifact mutated` when the dirty file is independently unrelated and artifact hash/blob remain fixed

## STOP RULE

Do not promote L5.

Do not advance to L6.

Do not modify the preserved artifact during audit.

Do not repeat provenance recovery.

END
