# CHAT-ARCH-2026-10-13-264 — M0B-R4 blocked: scoped governance diagnostics and target identity are unavailable

- **Episode ID:** CHAT-ARCH-2026-10-13-264
- **Reported time (America/Bogota):** 2026-10-13, 18:19 (Owner-supplied session report)
- **Input:** Owner-supplied result of the authorized governance review request
- **Classification:** `M0B_R4_PRECONDITION_STOP_GOVERNANCE_DIAGNOSTICS_AND_WORKSPACE_TARGET_IDENTITY_UNAVAILABLE`
- **Posture:** `KEEP_BLOCKED`
- **New edges:** `SCOPED_GOVERNANCE_BLOCK_DIAGNOSTIC_OPERATION_MISSING`, `MCP_SERVER_AND_CHECKOUT_IDENTITY_UNRESOLVED`
- **Inherited edges:** `LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED`, `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`, `CODEX_BRIDGE_ROUTE_REASSESSMENT_REQUIRED`, `CHATGPT_AUTOMATIC_TURN_AND_CORRELATED_RETURN_UNRESOLVED`

## 1. Received result

The owner-supplied report concludes that no governance operation exposed to that session met the requested narrow scope.

- `world_model_snapshot` was not invoked because it exposes a broader machine snapshot, including windows, focus, network and tools.
- Repository list/read operations were not invoked as an alternate route around the active block.
- No block metadata was obtained.
- The MCP server identity and target workspace/checkout were not directly confirmed.
- No files, permissions, source code, or runtime processes were changed.

This is evidence about the operations available to the reviewed session. It is **not** proof that no governance implementation exists anywhere in IABV, nor proof about the local checkout's contents.

## 2. Adjudication

Keep the gate closed. Owner consent to a limited read-only inspection remains valid, but consent does not itself change an active runtime governance decision. Do not retry the blocked reader, substitute another reader, infer the target from a tool namespace, query the broad world snapshot, or disable resource-pressure controls.

M0B-R4 has not started: there is still no source evidence from the local M0A checkout and no trustworthy MCP-to-checkout mapping. No Codex bridge choice can be finalized on this result.

## 3. Minimum missing control-plane contract

A supported control-plane capability is needed before retrying the source handoff. The following are **proposed interface requirements**, not claims that these operations already exist:

1. **Scoped active-block diagnostic:** return only the applicable block identifier, category/reason, resource or target scope, state, provenance and expiry (where applicable). It must not return the global world snapshot.
2. **Direct execution-target identity:** return non-secret identity/provenance for the responding MCP server and the exact workspace/checkout it serves (stable server/workspace identifiers and canonical checkout identity). Do not infer identity from the tool name.
3. **Explicit scoped authorization decision:** let the authorized governance mechanism decide whether a time-bounded, read-only, path-allowlisted inspection may proceed, with an auditable decision record. It must preserve unrelated/global safety guards.

If that capability is absent, the gate remains closed until the legitimate control-plane owner exposes it or resolves the issue through an already-supported governance route. Do not retrofit a bypass into the repository reader.

## 4. Next discriminating action

**IA DESTINO:** IABV control-plane/governance maintainer; Codex is the engineering actor only after the real source target and allowed scope are supplied by the supported mechanism.

**First open edge:** expose or identify a supported narrow block-diagnostic + execution-target identity + scoped decision route; then obtain the governance decision and prove the target. Only after that may M0B-R4 perform the previously specified read-only comparison of the local M0A `CodexAppServerToolAdapter` against `ExternalAssistantToolAdapter` + `UIExecutionRunner` + Codex rollout capture, tracing normal dispatch through result validation and the actual consumer.

**Stop conditions:** no approved narrow operation, no direct target proof, or no scoped grant means `KEEP_BLOCKED`. No source edits, test runs, launches, adapter activation, or ChatGPT automation claims.

No code, runtime, permission, or local checkout changed in this adjudication.
