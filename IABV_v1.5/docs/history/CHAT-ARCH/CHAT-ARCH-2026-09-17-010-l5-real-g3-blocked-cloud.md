# IABV v1.5 — CHAT-ARCH-2026-09-17-010

## L5 REAL G3 STATUS

At HEAD `f35b7bd4c24a5df0605482b72ba8697b932da8ee`, the production identity normalization is committed and independently audited. The synthetic real-card selector experiment is also committed and proves C1/C2-level claims: real ToolCards, isolated `allowed_tool_ids`, normal `InteractionModeSelector.select()`, persistence/cold reload, and winner change (+2.55).

## CRITICAL PROVENANCE FACT

The reported file `tests/windows_e2e/test_l5_real_g3_causal_closure.py` is NOT present in remote HEAD `f35b7bd4c24a5df0605482b72ba8697b932da8ee`. Devin's report showed it as `??` (untracked), while `server.py` was the only committed production change relative to parent. Therefore the G3 causal-closure test currently exists only in Devin's worktree and is not yet a remotely auditable artifact.

## CURRENT EPISTEMIC STATE

- Identity normalization: PROVEN (source + committed change + synthetic real-card experiment)
- C1 (normalized pattern found by real ToolCard selector): PROVEN
- C2 (persisted verified-learning state changes future selector decision): PROVEN, bounded to synthetic VerifiedTransition input
- Real MCP/G1 execution: NOT PROVEN by the current committed L5 experiment
- Independent filesystem observation in the L5 experiment: NOT PROVEN
- G3-produced VerifiedTransition: NOT PROVEN
- C3 (real independently verified world experience changes future selector decision): NOT PROVEN
- L5: PARTIALLY PROVEN
- L6/L7: blocked; do not advance

## CURRENT BLOCKER

Devin reports the new Windows E2E G3 test skips because CloudReasoningPlannerService has no configured provider/API key. This is an environment/runtime capability blocker, not yet an architectural contradiction.

## ROUTING

Next actor: SONNET 5 LOW.

Reason: the remaining question is focused: independently verify the committed state, the uncommitted-test provenance issue, and whether cloud-provider availability is merely an external runtime prerequisite or whether an existing non-cloud production-compatible route can execute the real G1/G3 chain without new architecture.

If Sonnet finds no new contradiction, next actor returns to DEVIN for the smallest real-runtime execution step. Sonnet MEDIUM is reserved only if the audit reveals a new confound or ambiguity. OPUS #3 remains reserved; CODEX not justified.

## STOP CONDITION

L5 can close only after one remotely/auditably attributable runtime chain exists:
real MCP action -> independent world observation -> real G3 verification -> bridge-produced VerifiedTransition with normalized ToolCard identity -> persistence -> cold reload -> normal select() -> observed decision change.
