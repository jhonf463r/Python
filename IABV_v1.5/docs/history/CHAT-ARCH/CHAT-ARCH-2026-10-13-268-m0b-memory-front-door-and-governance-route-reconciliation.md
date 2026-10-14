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



## 7. Reusable next-agent prompt — Codex / public-source-only

Use this exact bounded task for the next Codex handoff:

### M0B-R5 — Static code-facing contract for audit diagnosis and scoped read decision

**Target actor:** Codex as code-contract analyst.  
**Mode:** read-only inspection of published GitHub source and continuity records.  
**Status:** KEEP_BLOCKED.  
**Not authorized:** local M0A read, blocked MCP-reader retry, alternate-reader bypass, IABV/Codex/App Server launch, commands, tests/builds, runtime, source/config/document edits, commits/pushes, installation/update, new authentication, credentials, paid API/credits or extra spend.

#### Continuity bootstrap — mandatory
Read in order:
1. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
2. `CURRENT-STATE.md`
3. `CONTEXT-INDEX.md`
4. `MEMORY-OPERATING-PROTOCOL.md`
5. Entry 268, then Entries 267, 266, 265 and 264 only as needed
6. Reconcile the exact relevant records in Entries 219–226; do not reopen unrelated historic work.

At start, verify the live main SHA and the source-file blob SHAs relevant to this issue. Entry 268's documentation baseline is `a9eb37d929dae5658b5f1a7e03d40edeb76c50db`; the audited code baseline is `559f4ea20a9a9163cd9a9839b11d9991933f8c07`. The two intervening updates are documentation-only, but verify source blobs rather than assume. If code differs, pin and report the actual source revision.

#### Owner-decision reconciliation
Current-State already records **RQ224 Model A selected for the first supervised MCP prototype**. Do not ask the Owner to select A/B again. This is a threat-model assumption only; it does not close RQ224, prove an authority/receipt implementation, authorize broad identity exploration, or grant repository-read access. The observation grant `observe_window_content:codex` is not a repository-read decision.

#### Mission
Produce the smallest source-grounded, reuse-first, code-facing contract and **unexecuted** test specification for the missing bounded repository-audit access decision. No implementation.

#### Inspect only relevant public paths
- `infra/mcp/server.py`: `_governance_block_for_route`, the registration and gate path for `read_repo_file` and `list_repo_directory`, the blocked response fields, and `autonomy_status` / `autonomy_update_task`.
- `services/evolution/world_model_service.py`: `grant_observation_permission`, `revoke_observation_permission`, operational block production, and whether an existing operation explicitly releases an audit-reader block.
- `ui/viewmodels/control_center_viewmodel.py` and its relevant QML/tests: the approval action, call chain, permission scope, retry, and any evidence of an audit-read release.
- Directly relevant models, runbook, and canonical Entries 219–226 only.

Do not do broad source archaeology. Do not claim that absence in this bounded inspection proves global absence. The existing reader's blocked response can contain reason/detail/block metadata; that is not equivalent to a dedicated diagnostic plus a separate access decision.

#### Required output
A. Compact source map: symbol/file, pinned blob SHA, line anchors, caller, callee, scope and returned evidence.
B. A clear adjudication of whether an existing supported public path already performs both (1) a narrow diagnostic and (2) a separately authorized audit-read decision. Keep those two functions distinct.
C. Minimum proposed contract:
   - Diagnostic returns only applicable block/permission metadata; it never grants access.
   - Decision binds a directly proven server/workspace/checkout identity; operation class; explicit relative-path allowlist; limits; expiry; authority/provenance; and decision ID.
   - Unknown/missing/mismatched/stale/denied identity or decision, unavailable state, path outside allowlist, or expired authority fails closed.
   - No observation permission is promoted to repository-read authority.
   - Reuse current WorldModel/Control Center/gate/approval machinery where semantically correct. Do not invent a trust root or a second governance system. Identify any new seam only as PROPOSED.
D. Non-executed discriminating tests for: block diagnostic reveals only applicable fields; diagnostic never releases gate; observation grant does not satisfy audit read; exact target and path binding; expiry/replay/mismatch; global active block preserved; unknown scope fails closed; disconnected and unknown network state where relevant; existing path traversal/secret/path limits remain enforced.
E. Reconcile the proposed read-only decision with Entries 219–226. Respect their actual scope. State explicitly where mutation authorization differs from read-only audit access. Record Model A accurately and identify only genuinely missing owner decisions; do not re-ask settled questions.
F. End with a small dependency table: PROVEN_BY_SOURCE / OWNER_REPORTED / PROPOSED / UNPROVEN, then name exactly one next edge. Do not propose implementation or a new architecture unless source proves existing organs cannot express the contract.

#### Out of scope
Do not modify the known unrelated gate semantics for `target_scope` or unknown `network_status` in this task. If encountered, record them as separate static risks and do not attribute them to the active local M0A block without runtime evidence. Do not select the Codex App Server vs Desktop route here; that comparison still requires legitimate local-source provenance. Do not claim the bridge is operational.

Return the compact report to ChatGPT/coordinator for independent source reconciliation. The coordinator—not this report alone—will decide whether the canonical trace needs a further knowledge/method/routing delta.
