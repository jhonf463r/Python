# IABV v1.5 — CHAT-ARCH 2026-09-17-003
## L5 Artifact Reproduction / Decision-Influence Gap

## PURPOSE

Preserve the material knowledge from the fresh Devin reproduction of the recovered L5 artifact and the new forensic distinction between learned scoring influence and an actual future selector decision change.

## ARTIFACT PRESERVATION

Recovered artifact:

`C:\\IABV_WORKTREES\\world-grounded-learning-bridge-runtime\\IABV_v1.5\\tests\\test_l5_causal_decision.py`

Original artifact identity:

- SHA-256: `E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`
- Git blob: `2844537f80c190a1351dac3a95f35f80cf79dc19`
- Original HEAD: `55d3e2c93807202ec5d0177eda163e8de10418ef`
- Original status: untracked

Devin reported an evidence branch:

`audit/l5-artifact-evidence-2026-09-17`

with reported short commit:

`f3e8a21c5`

and byte-for-byte identical file/hash.

IMPORTANT: direct GitHub read-back performed after that report could not resolve the evidence branch or commit (`f3e8a21c5`). Therefore the preservation commit is currently **locally reported but not remotely verified**. This must not be treated as closed provenance until the full commit SHA and remote branch/file are independently readable.

## FRESH WINDOWS REPRODUCTION

Devin reported fresh execution on Windows 11:

- Python `3.14.4`
- pytest `9.0.3`
- command: `python -m pytest -vv -s tests/test_l5_causal_decision.py::test_l5_verified_experience_changes_selector_scoring`
- result: `1 passed in 2.72s`
- exit code: `0`
- stderr: empty
- artifact SHA before = after = `E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`

Observed values:

CONTROL:
- learned_pattern `0.0`
- total_score `7.545`
- pattern_id `None`

TREATMENT:
- learned_pattern `1.0`
- total_score `10.095`
- pattern_id `131e4e82-93f8-4079-b67d-5e73ea52ef5d`

Reported score delta: `+2.55`.

## STRUCTURAL FINDINGS

The test uses real production-layer objects including:

- `ToolRecordRepository`
- `AppDatabase`
- `ArtifactStorage`
- `InteractionLearningService`
- `InteractionModeSelector`
- `ToolRegistry`
- `ToolCard`
- `VerifiedTransition`
- `InteractionPattern`
- `InferenceRequest`

Learning uses production `learn_from_verified_transition()` and real persistence into SQLite/ArtifactStorage according to the report.

Reload uses a new `ToolRecordRepository` / `AppDatabase` / `ArtifactStorage` instance against the same database file after deleting the previous repository/learning-service objects.

The recovered test is therefore substantially stronger than a synthetic counter fixture.

## CRITICAL LIMITATION IDENTIFIED

The test entrypoint is:

`test_l5_verified_experience_changes_selector_scoring(tmp_path)`

The reported control/treatment evaluation calls:

`InteractionModeSelector._assess_candidate()`

and observes its scoring output, with `_best_pattern()` involved in the learned-pattern lookup.

The report does **not** demonstrate a full competitive selection through the ordinary application decision path such as:

`ToolTeachService._select_mode()`
→ `InteractionModeSelector`
→ competitive candidate comparison
→ selected candidate/action

Therefore the current fresh result demonstrates a stronger causal edge than G3, but it does not yet establish the exact historical L5 definition if L5 requires:

`legitimate prior experience → future selector consumes it → future decision changes`

The reproduced test establishes:

`verified experience → persistence → reload → learned-pattern scoring changes`

It does not yet establish:

`verified experience → future competitive selection outcome changes`

## CURRENT EVIDENCE CLASSIFICATION

### Artifact

`PHYSICALLY RECOVERED = YES`

### Byte identity

`CONFIRMED LOCALLY BY MATCHING SHA-256 / GIT BLOB`

### Fresh execution

`WINDOWS RUNTIME REPRODUCED = REPORTED PASS`

### Historical execution

`NOT RECOVERED`

### Persistence

`PROVEN BY REPORTED TEST PATH`

### Reload

`PROVEN BY REPORTED FRESH REPOSITORY INSTANCE`

### Learned-state consumption

`PROVEN AT INTERNAL SCORING LEVEL`

### Normal application selector path

`NOT PROVEN BY THIS TEST`

### Competitive decision difference

`NOT PROVEN`

### L5

`NOT PROVEN UNDER THE CANONICAL DEFINITION`

The current test should be treated as a strong intermediate causal result: **persisted verified experience reaches a reloaded selector scoring function and changes its learned-pattern contribution**.

Do not silently promote this to full L5 merely because the test prints `L5 CAUSALITY CONFIRMED`.

## COGNITIVE INFLECTION TRACE

Current state:

`OBSERVE` = evidenced

`PERSIST` = evidenced

`RELOAD` = evidenced

`CONSUME` = evidenced at internal scoring/helper level

`DECIDE` = not yet evidenced at competitive selection level

`DIFFER` = evidenced as score/pattern-state difference, not yet as selected action difference

`CAUSALLY ATTRIBUTE` = evidenced for learned-pattern score contribution; not yet for a changed real future decision

Therefore the requested inflection remains open at:

`CONSUME → DECIDE → DIFFER → CAUSALLY ATTRIBUTE`

## SYMBIOSIS / MESSAGE ECONOMY DELTA

This episode provides additional capability evidence:

- Codex was highly useful for repository archaeology and physical artifact recovery.
- Devin was highly useful for exact Windows filesystem access, byte-level preservation and fresh runtime reproduction.
- Sonnet was useful in identifying the provenance boundary and correctly refusing to infer inaccessible artifact content.
- The next independent question is methodological/causal, not repository archaeology.

Do not spend another Codex intervention on the already resolved artifact-location problem unless the remote evidence branch must be recovered and cannot be published by the Windows operator.

Relevant qualitative measures:

`ΔK = high`: recovered/reproduced artifact plus clarified scoring-vs-decision boundary

`Δπ = high`: L5 acceptance rule must require actual decision influence, not merely score change

`ΔB = none`: no downstream behavior change shown

`ΔY = none`: no world outcome shown

## NEXT CAUSAL EDGE

The smallest discriminating experiment is now:

`reloaded legitimate learning state`
→ `normal selector/application decision path`
→ `multiple competing candidates`
→ `selected decision differs only because of prior verified experience`

The experiment must preserve Control/Treatment identity and isolate prior verified experience as the causal variable.

## ROUTING

Immediate prerequisite: remotely publish/read back the reported evidence commit if still necessary for independent audit.

After the artifact is remotely accessible, the next independent auditor is **Sonnet**.

If Sonnet validates the current test as an intermediate scoring-level edge, the next implementation/runtime actor is **Devin** for a minimal competitive-selection experiment on Windows.

Use Opus only if Sonnet identifies a genuine architectural contradiction about selector ownership or causal learning semantics.

## NEGATIVE KNOWLEDGE

`score difference != decision difference`

`internal helper consumption != normal application selection`

`fresh reproduction != historical execution proof`

`local evidence branch != remote canonical evidence until read-back`

`test label != epistemic status`

## STOP RULE

Do not claim the IABV cognitive inflection point.

Do not advance to L6.

Do not redesign the learning architecture.

Do not create a replacement test until the current artifact has been independently audited and the remote evidence identity is stable.
