# CHAT-ARCH — 2026-09-17 — L5 Identity Normalization Runtime Result

## Objective
Reconcile the Devin result after Opus 5 adjudicated the L5 identity seam and authorized the minimum bridge-level normalization.

## Canonical provenance
The real experiment branch tip is `f35b7bd4c24a5df0605482b72ba8697b932da8ee`, parent `5ef1009c1e97165a62ba04a8dbfaf7f62deb8edb`. The previously reported `5ef1009c1a6728332b3c4a0869b6291e7b3b6586` remains nonexistent. Commit diff contains the production bridge normalization plus `tests/test_l5_real_card_verified_selection.py`.

## Production change
`src/iabv_v15/infra/mcp/server.py` now writes `VerifiedTransition.tool_id = 'mcp_client'` in the G1/G3 learning bridge and preserves the MCP function identity in `metadata['assigned_tool']`. The function-level `action_signature` and execution correlation IDs remain preserved.

This implements the Opus-authorized minimal normalization: learning-pattern `tool_id` is placed in the ToolCard-level selector namespace while `assigned_tool` remains function-level provenance.

## Runtime evidence reported by Devin
Windows 11, Python 3.14.4, pytest 9.0.3. The test passed with real ToolCards `mcp_client` and `aider_coder`, isolated with `allowed_tool_ids` and normal `InteractionModeSelector.select()`.

Control: aider_coder 5.225 > mcp_client 4.845.
Treatment: mcp_client 7.395 > aider_coder 5.225.
Delta for mcp_client: +2.55.
Fresh repository/registry/selector reload recovered the persisted pattern with `tool_id='mcp_client'` and `verified_transition_success_count=1`.

## Critical epistemic boundary
The reported test is NOT a real G3 end-to-end experiment. Its treatment explicitly constructs a synthetic `VerifiedTransition` with `tool_id='mcp_client'` and therefore simulates what the normalized bridge would produce. The actual production G3 execution, MCP action, independent filesystem observation, and bridge-generated transition were NOT exercised by this test.

Therefore:

- identity normalization mechanism: experimentally demonstrated on real ToolCards;
- persisted learning -> cold reload -> normal selector -> decision change: demonstrated;
- real-world verified action -> normalized bridge -> persisted learning -> selector decision: NOT YET demonstrated;
- L5 strong causal closure: remains PARTIALLY PROVEN / NOT CLOSED.

## Additional identity caution
The production change uses the literal `mcp_client` in the G1/G3 bridge. Before accepting this as canonical for all executions, independent audit must verify that this bridge path is semantically and exclusively the `mcp_client` ToolCard execution channel. Do not infer identity solely from the fact that the test passes.

## Selector provenance boundary
`InteractionModeSelector` currently aggregates `success_count + verified_transition_success_count` in learning-related score terms. Thus the selector itself does not distinguish ordinary from verified success. The current experiment controls `success_count=0` so the treatment effect is attributable to the verified counter under experimental control, but this is not evidence that the selector has an intrinsic preference for verified provenance.

## Current gate state
STATE_CHANGE: PROVEN
SCORE_CHANGE: PROVEN
DECISION_CHANGE: PROVEN for real ToolCard competition with synthetic normalized VerifiedTransition
BEHAVIOR_CHANGE: NOT PROVEN
WORLD_OUTCOME_CHANGE: NOT PROVEN
REAL_G3_CAUSAL_CONTINUITY: NOT PROVEN
L5: PARTIALLY PROVEN / NOT CLOSED
L6/L7: must not advance

## Routing
NEXT ACTOR: SONNET.

Sonnet must independently audit:
1. whether the literal `mcp_client` normalization is semantically valid for the actual G1/G3 runtime path;
2. whether the test introduced any hidden asymmetry or false-positive;
3. whether the synthetic treatment means the L5 claim must remain partial;
4. the minimum remaining experiment required to exercise the real G3 path and preserve identity continuity.

Do NOT spend Codex. Do NOT spend the third Opus unless Sonnet uncovers a genuinely unresolved architecture-level contradiction after this result.

## Stop condition
L5 can close only after a real execution produces the VerifiedTransition through the actual G3 verification path, with the same ToolCard identity, persisted and cold-reloaded, followed by normal `select()` and an independently observed decision change. After that artifact exists, Sonnet performs the final forensic adjudication.
