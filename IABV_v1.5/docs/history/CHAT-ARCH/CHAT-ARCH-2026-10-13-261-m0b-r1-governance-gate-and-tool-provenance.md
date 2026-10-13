# CHAT-ARCH-2026-10-13-261 — M0B-R1 stopped at governance gate; tool-target provenance unresolved

- **Episode ID:** CHAT-ARCH-2026-10-13-261
- **Reported time (America/Bogota):** 2026-10-13, 17:35
- **Canonical remote baseline reconciled for this writeback:** `main @ 9c47460559b9cf31de9af54316d87c8b326e6e3f`
- **Input class:** Owner-supplied Codex report + static review of published IABV MCP gate/runbook and historical RSK-01A.5 records
- **Classification:** `M0B_LOCAL_SOURCE_INSPECTION_BLOCKED_BY_GOVERNANCE_GATE`
- **Operational posture:** `KEEP_BLOCKED`
- **Immediate edge:** `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`
- **Technical edge:** `CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED`

## 1. Result received and evidence boundary

The Owner supplied Codex's M0B-R1 report:

`KEEP_BLOCKED — LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED`.

Codex reports that the tool `mcp__iabv_v15_rsk01a5__list_repo_directory`, called for `src/iabv_v15/services/tools`, returned `governance_blocked: true` and no names, content or hashes. It did not retry Git, inspect code, run IABV/Codex, tests or builds, or modify files.

This is **OWNER_REPORTED** for the local invocation. The exact structured `reason`, `detail`, `blocks[]` or pending-gate payload was not included in the report supplied here. Therefore the active runtime block record and its scope/expiry are not independently identified. No local implementation or checkout state was observed.

## 2. Static governance semantics from published main

At the reconciled remote source, `IABV_v1.5/src/iabv_v15/infra/mcp/server.py` routes `read_repo_file` and `list_repo_directory` through `_governance_block_for_route(assistant_kind="audit", requires_network=False)`. The gate is fail-closed and reads the existing `WorldModelSnapshot`; it can block on missing/unavailable/failed world-model state, active applicable `OperationalBlockRecord` entries, or required but ungranted permission gates.

The published `docs/runbooks/audit-tools-runbook.md` gives these possible reasons: `world_model_service_unavailable`, `world_model_read_failed`, `world_model_snapshot_missing`, `operational_block_active`, and `permission_gate_required`. `network_unavailable` is not expected for this audit route because it declares `requires_network=False`.

The supplied wording “por un bloqueo operativo” is a report of the result, not enough to identify the exact block record or its provenance. Do not clear, expire, ignore or work around the gate. Do not reinterpret it as absence of the file or a defect in the adapter.

Sources:
- [MCP server gate](../../src/iabv_v15/infra/mcp/server.py)
- [Audit tools runbook](../../docs/runbooks/audit-tools-runbook.md)
- [MCP bridge governance](../../docs/mcp-bridge.md)

## 3. Cross-workstream provenance correction — RSK-01A.5 is not M0A

The tool namespace contains `rsk01a5`. This is a strong provenance signal that must be reconciled before using that connector as evidence about the M0A local checkout, but the name alone does **not** prove the configured filesystem root.

Historical records 035–036 describe a separate RSK-01A.5 experiment on whether an actual MCP `read_repo_file(CURRENT-STATE.md)` result crosses into IABV's internal context/governance/routing. That experiment's reported target was `C:\\Python\\IABV_v1.5_rsk-01a5` at `3de2bb4eddf4e43d9664e17b935d7a55b6ea9442`; its runtime attempt was blocked before execution because the external MCP client connection was unavailable. It did not establish that memory had no MCP integration.

The current M0A/M0B code-development investigation has a different reported target: checkout `codex/m0a-safe-ui-boot`, previously reported under `C:\\Python\\IABV_v1.5` with local modifications. Those older local details have not been remeasured. Do not infer that the `rsk01a5` tool points to this M0A target, nor infer that it does not; the live server identity/root-to-checkout mapping remains **UNPROVEN**.

Thus the latest result only establishes that one call through the named RSK-01A.5 audit tool was governance-blocked. It does not establish a current M0A source-read failure for every possible authorized channel.

## 4. Symbiotic routing and next discriminating action

Use the operating sequence:

`objective → uncertainty → capability fit → actor → bounded observation → evidence → adjudication → memory/method/routing delta`.

The needed capability has changed from generic source retrieval to **governance-result and tool-target provenance diagnosis**. The next local actor, if the existing Codex session retains the call record and tool metadata, should inspect only:

1. The already-returned structured result for exact `reason`, `detail`, block/gate identifiers, scope and expiry; do not re-call `list_repo_directory` or `read_repo_file`.
2. The currently exposed MCP server/tool identity and documented workspace-root mapping, without reading or printing auth/secret configuration.
3. Whether this connector belongs to the RSK-01A.5 experiment or the intended M0A checkout. Treat all prior local branch/HEAD/count reports as historical/owner-reported, not as current measurements.

Do not use a general `world_model_snapshot` call merely to get the block reason if it returns unrelated window/focus/environment details. Use a narrowly scoped, already-authorized governance diagnostic only if it returns just block/permission metadata. If the raw result and an authorized narrow diagnostic do not reveal the cause, stop and report the exact governance decision or connection metadata that only the owner/authorized Control Center can resolve. Do not approve, clear or bypass governance on the owner's behalf.

No local reader reattempt, shell command, IABV/Codex/App Server launch, test/build, secret inspection, configuration change, code edit or promotion is authorized by this writeback.

## 5. Global objective and current stage

Global north star: IABV as the governed operational “mind” of the laptop, composing existing capabilities to observe, decide, act, verify and improve.

Foundational working objective from the continuity lineage: reliable cross-chat continuity so that new sessions recover the decision frame, prior evidence, negative knowledge and exact frontier without making the owner repeat the history.

Current M0A/M0B technical stage: establish a verified and properly targeted evidence path into the actual local checkout before adjudicating the Codex adapter → registration → SafeUI/ToolTeachService dispatch → result capture/validation → existing consumer chain. This remains a prerequisite to, not proof of, a governed autonomous coding loop.

The separate RSK-01A.5 experiment is related to the broader memory/MCP/routing symbiosis but must not be conflated with the current local code-development bridge.

## 6. Adjudication

- `M0B_LOCAL_SOURCE_INSPECTION_BLOCKED_BY_GOVERNANCE_GATE`: received report; local outcome not independently reproduced here.
- `IABV_AUDIT_GOVERNANCE_GATE_AND_TOOL_TARGET_PROVENANCE_UNRESOLVED`: new immediate edge.
- `LOCAL_DIRTY_WORKTREE_SOURCE_HANDOFF_UNRESOLVED`: remains open; no local source has been obtained.
- `CODEX_CANDIDATE_EXECUTOR_CONFINEMENT_AND_RECEIPT_CONTRACT_UNRESOLVED`: remains the technical architecture frontier.
- `KEEP_BLOCKED`: unchanged.

No source-code claim is made about the local checkout. The result has not demonstrated a working bridge, an absent adapter, an unsafe runtime, or autonomous causal learning.
