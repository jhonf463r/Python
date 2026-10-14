# CHAT-ARCH-2026-10-13-268 — Supermemory front-door repair and M0B governance-route reconciliation

- **Episode ID:** CHAT-ARCH-2026-10-13-268
- **Reported local time (America/Bogota):** 2026-10-13, approximately 20:32–20:35
- **Public documentation baseline before this write:** main at ea2b16ae3b5d2e553897b769fee3c067e4bf29c5
- **Pinned source-code baseline used for the focused audit:** 559f4ea20a9a9163cd9a9839b11d9991933f8c07; the intervening commits are documentation-only
- **Input:** Owner request to reconcile the full continuity trail, explain the apparent cross-chat memory disconnect, and select the next AI/task
- **Classification:** CONTINUITY_FRONT_DOOR_REPAIRED; EXISTING_AUDIT_RELEASE_PATH_NOT_FOUND_IN_INSPECTED_PUBLIC_SURFACES; NEXT_CODE_FACING_CONTRACT_SPEC_READY
- **Posture:** KEEP_BLOCKED for local M0A reads, implementation, tests/runtime, and Codex/App Server launch

## 1. Root cause of the apparent cross-chat memory disconnect

The canonical project-memory front door is `IABV_v1.5/docs/history/CHAT-ARCH/README.md`, not only the repository-root `README.md` or `IABV_v1.5/README.md`. The latter two paths return 404, but the canonical CHAT-ARCH README exists.

After Entry 267, `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md`, `ARCHIVE-REGISTRY.md` and `AGENTS.md` were updated, but the canonical CHAT-ARCH README was not. Its first routing record therefore remained Entry 266 while the other top-level route files pointed to Entry 267. This is a real navigation/continuity inconsistency and explains why a new agent following the required README-first protocol could start from a stale route. It does not mean all project memory was absent; the route pointers were only partially reconciled.

Entry 268 prepends the current record to the canonical CHAT-ARCH README and the other routing/method files so the route now agrees. The required recovery order remains:
`CHAT-ARCH/README → CURRENT-STATE → CONTEXT-INDEX → MEMORY-OPERATING-PROTOCOL → relevant canonical entries/source`.
Do not infer that root README 404s mean the canonical memory README is absent.

## 2. Focused source audit requested by Entry 266

The following public paths were read at pinned source baseline 559f4ea20a9a9163cd9a9839b11d9991933f8c07; no local checkout was involved.

- `infra/mcp/server.py`: `_governance_block_for_route` applies to audit reads; registered `read_repo_file` and `list_repo_directory` use that gate. The existing refusal payload can carry `reason`, `detail` and applicable `blocks` / `permission_gates`. This is a diagnostic embedded in a refused operation, not a separate narrow diagnostic tool plus a grant.
- `services/evolution/world_model_service.py`: the relevant public mutation methods are `grant_observation_permission` and `revoke_observation_permission`. They mutate observation-permission records; the inspected path does not expose a separate operation to release a repository-audit block or authorize a particular checkout read.
- `ui/viewmodels/control_center_viewmodel.py`: `_grant_pending_observation_permission` resolves a pending assistant observation scope through `grant_observation_permission`, clears observation artifacts and retries the external consultation. It is not an audit-reader release.
- `tests/test_control_center_viewmodel.py`: the inspected test binds that action to `observe_window_content:codex`; this is evidence for the observation scope, not a repository read grant.
- `autonomy_status` and `autonomy_update_task` are task/continuity surfaces; the inspected public contracts do not grant source-reading authority.
- Targeted public symbol searches for audit-release/scoped-read grant terms did not identify a separate registered operation in these inspected surfaces.

**Bounded conclusion:** an explicit supported audit-release + checkout-scoped read decision was **NOT FOUND IN THE INSPECTED PUBLIC PATHS**. This is not a claim of global absence across every branch or the local checkout. The previous local MCP call's exact gate payload and its server/workspace target remain unavailable; do not retry or bypass it.

## 3. Important owner-decision correction: RQ224 Model A is already recorded

The latest `CURRENT-STATE.md` contains the 2026-10-11 Owner adjudication: **Model A was accepted for the first supervised IABV MCP prototype**, as a stated process/code-integrity assumption. That decision supersedes the old RQ224 document's request to choose A or B for this phase.

Do **not** ask the Owner to choose between A and B again. Do **not** misstate Model B as the current selection. Equally, Model A does not close RQ224, prove an enrolled Owner identity/receipt source, authorize implementation, or permit a broader identity-source investigation outside the prior bounded scope. The read-only repository-audit gate is also a distinct operational question and cannot inherit mutation authority from RQ224.

## 4. Current causal model and open edges

The project-memory route and task state are now separated explicitly:

1. **Continuity/navigation edge — repaired by this documentation write:** canonical README, CURRENT-STATE, CONTEXT-INDEX, method protocol and agent overlay point to Entry 268.
2. **Governance contract edge — next public-static task:** no dedicated diagnostic + separate checkout/path-scoped read decision was found in the inspected public route; an existing reader refusal is not a grant.
3. **Local source/provenance edge — still blocked:** the active MCP server/connection is not directly proven to target the intended dirty M0A checkout. Owner consent alone does not change the effective gate.
4. **Bridge implementation edge — still unimplemented/unverified:** R10's correlated return contract remains the target; ToolResult identity/attempt/stage, eligible-final-success metrics, and durable idempotent adaptive-consumer receipt have not been implemented or runtime-proven.
5. **Codex route edge — unresolved:** compare the local App Server candidate with the published desktop/UI/rollout route only after legitimate source access; do not choose a transport from public evidence alone.
6. **ChatGPT turn/return edge — unresolved:** shared MCP tool exposure does not prove IABV can start a ChatGPT turn and retrieve a correlated response.
7. **Causal learning edge — unresolved:** a saved response/pattern does not demonstrate that later routing changed because of it or that the result improved.

The Entry 267 sandbox-learning finding remains valid at the pinned public source: a successful sandbox result can reach ToolMemory/InteractionLearningService before the later external response and can be eligible for success metrics/pattern learning under the inspected conditions. No live incident is claimed.

## 5. Next actor and next task

**Next AI: Codex, as read-only code-contract analyst, using published GitHub source only.** The task is not to launch Codex/App Server, inspect local M0A, retry the blocked reader, run tests, edit source, install/update, authenticate, or spend additional money. Provide the prompt in the next handoff; execute only within the established current session/authorization.

Produce a compact, code-facing contract and non-executed test specification for:
- a narrow audit-gate diagnostic that returns only applicable block metadata and never grants access;
- a separate, auditable read-only decision bound to exact server/workspace/checkout identity, operation, explicit allowlisted relative paths, limits, expiry and authority provenance;
- reuse of the existing WorldModel/Control Center/approval structures where semantically correct;
- fail-closed behavior for missing, stale, mismatched, unknown or denied identity/decision;
- no use of observation permission as repository-read authority;
- reconciliation against existing records 219–226, explicitly respecting the already-selected Model A and the separate read-only gate;
- proposed test cases, without executing them;
- exact unresolved owner decisions, if any, without reopening the already-decided A/B choice.

Do not implement the proposed route, create a new trust root, expand into an unbounded identity audit, or read the local checkout. Keep existing resource blockers intact. Where the code/source cannot prove something, mark it UNPROVEN.

After Codex returns, ChatGPT/coordinator performs an independent source-grounded reconciliation and records only material knowledge/method/routing deltas. Codex must not self-certify the result as complete.

## 6. Verification boundary

This episode used read-only GitHub source/document retrieval and wrote documentation only. It did not inspect local M0A, invoke the blocked MCP reader, launch Codex/IABV/App Server, run tests/builds, modify source code/configuration, access credentials, authenticate, install/update software, or incur AI/API spending. The new GitHub commit itself must be verified remotely after publication.

---

