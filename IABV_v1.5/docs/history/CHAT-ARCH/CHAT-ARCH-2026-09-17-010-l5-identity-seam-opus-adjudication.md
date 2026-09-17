# CHAT-ARCH 2026-09-17-010 — L5 Identity Seam / Opus Adjudication

## Objective

Resolve whether the remaining L5 causal gap is only an experiment-design problem or a real production identity discontinuity between MCP function execution and selector ToolCard identity.

## Canonical provenance

- Branch: `experiment/l5-competitive-selection-2026-09-17`
- Actual remote HEAD: `5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb`
- Previously reported `5ef1009c1a6728332b3c4a0869b6291e7b3b6586` does not exist.
- HEAD parent: `d77cbc6015a8358c9005d475c9799efc9791f8f6`

## Independent evidence already established

Sonnet proved the candidate-isolation experiment closes the synthetic learning-to-decision path:

`persisted verified-transition learning state -> fresh reload -> normal InteractionModeSelector.select() -> isolated A/B ranking -> winner change`

The experiment is not sufficient for strong real-world L5 because its `VerifiedTransition` is manually constructed.

Opus 5 then audited the identity seam against the production path.

## Identity model adjudicated by Opus

- `assigned_tool` = MCP server function identity, e.g. `write_repo_file`.
- `ToolCard.tool_id` = selector-level execution-channel/provider identity, e.g. `mcp_client`, `aider_coder`, `shell`.
- `ToolCard.adapter_key` = adapter registry identity.
- `action_signature` = deterministic fingerprint of `(assigned_tool, action, target)`; it is action identity/fingerprint, not candidate identity.
- `InteractionPattern.tool_id` is the selector lookup identity.

G3 currently constructs `VerifiedTransition.tool_id = assigned_tool`, while `_best_pattern()` queries patterns using `card.tool_id`. This is a real production namespace discontinuity.

Opus independently concluded there is no existing canonical binding from MCP function name to ToolCard identity that allows the current real G3 transition to be selected later by the selector.

## Key architectural conclusion

The problem is not merely a missing test harness. The G3 bridge writes an MCP function name into `InteractionPattern.tool_id`, while the selector interprets that column as ToolCard/provider identity.

Therefore the valid minimal repair is a bridge-level normalization so verified learning uses the ToolCard identity of the actual execution channel (`mcp_client` in the current production MCP path), while preserving `assigned_tool` inside the transition/action fingerprint or existing metadata so function-level provenance is not discarded.

No new identity architecture, alias table, selector redesign, or schema expansion is authorized by this adjudication.

## Important second boundary

`InteractionModeSelector` intentionally merges `pattern.success_count + pattern.verified_transition_success_count` for score calculation. Therefore the selector does not itself distinguish ordinary and verified success provenance.

Strong L5 attribution remains experimentally achievable only by controlling `success_count == 0` for the target pattern before treatment, so the observed learning contribution is exclusively from `verified_transition_success_count`.

Do NOT claim that the selector has a native ability to prefer verified evidence over ordinary success.

## Required Devin action

1. Trace the real caller/execution path and establish that the relevant execution channel is the existing `ToolCard(tool_id='mcp_client')` path.
2. Apply only the minimal bridge-level normalization authorized by Opus. Do not hardcode an invented identity if an existing runtime identity can be carried from the real caller.
3. Preserve `assigned_tool` as MCP function provenance.
4. Do not change selector scoring semantics.
5. Do not create synthetic ToolCards named after MCP functions.
6. Re-run L5 using real ToolCards, not `candidate_a/candidate_b`.
7. Exercise the real MCP action/verification path and produce a fresh persistence/reload boundary.
8. Verify target pattern has `success_count == 0` before treatment and `verified_transition_success_count == 1` afterward.
9. Verify real identity continuity: selected card `tool_id == mcp_client`, transition `tool_id == mcp_client`, while `assigned_tool` remains traceable as the executed MCP function.
10. Show control/treatment ranking and winner change through the public `InteractionModeSelector.select()`.

## Gate state

- STATE_CHANGE: PROVEN
- SCORE_CHANGE: PROVEN
- DECISION_CHANGE: PROVEN in isolated synthetic-learning experiment
- REAL VERIFIED EXPERIENCE -> SAME SELECTOR DECISION: NOT YET PROVEN
- L6: NOT ENTERED
- L7: NOT ENTERED
- Codex capability gap: none
- Third Opus intervention: reserved; justified only if normalization exposes a genuine MCP-function-vs-mcp-client granularity contradiction that cannot be resolved by the bounded bridge repair.

## Epistemic rule preserved

`DECLARED STATE != OBSERVED STATE != EFFECTIVE STATE`

A green test or Devin report does not close L5. Independent Sonnet verification is required after the implementation/runtime result.