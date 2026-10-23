# M1A G1–G3 — bounded governance-route implementation in an isolated candidate

## 1. Authorization, destination and pinned base

- **Owner authorization:** received in this ChatGPT conversation on 2026-10-22. Exact scope: implement the G1–G3 governance route only where supported by repository evidence and explicit authority decisions; if the real trusted identity, verifiable issuer, or independent block-release authority is missing, stop and document the dependency rather than invent it.
- **Task ID:** `M1A_G1_G3_AUTHORITY_ROUTE_CANDIDATE_IMPLEMENTATION`.
- **Canonical parent task:** `M1A_V1_0_1_G1_G3_AUTHORITY_EVIDENCE_ROUTE`.
- **Destination:** Codex, in the already-existing UI/session, user-mediated handoff. This document is prepared for that session; it is **not** a claim that the prompt has been dispatched or consumed.
- **Repository:** `jhonf463r/Python`.
- **Pinned public `main` base:** `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db` (observed remote main immediately before creating the candidate branch).
- **Isolated candidate branch created at that exact base:** `codex/m1a-g1-g3-governance-route-candidate-20261022`.
- **Normative contract:** M1A v1.0.1, blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`.
- **Routing/source distinction:** the candidate source branch is pinned at `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`. After that commit, the coordinator updated six documentation-only paths on public `main` to record the explicit Owner authorization and this handoff; the bounded GitHub comparison found no product-source path among those changes. For task routing and the Owner's latest authorization, read the latest public-main `CURRENT-STATE.md` and this handoff, not older routing prose embedded in the pinned candidate snapshot. For product-source edits, use the isolated candidate branch only. Keep these two provenance tracks distinct.
- **Evidence matrix:** eight prerequisite gates, zero closed; G1–G3 are the target of this handoff, while G4–G8 remain separate and must not be silently claimed closed.
- **Scope:** source/documentation inspection and source edits only inside the dedicated, isolated candidate based on the pinned public SHA. Editing the public candidate branch is allowed; changes to main are not.
- **Not yet verified:** the candidate branch's working workspace identity and whether the existing Codex session can safely operate on that branch. Codex must verify it is using a fresh isolated candidate and stop if its workspace is actually the Owner's pre-existing checkout.

## 2. Why this work is being attempted

The existing local MCP read attempt was reported denied under `operational_block_active`. The latest user-supplied Codex session inventory reported reader/list/snapshot metadata but no documented scoped-read decision issuer, trustworthy runtime principal, revocation source, verifiable operation receipt, authoritative versioned operation-to-target resolver, or independent block-release authority. A prior Codex inventory differs on whether the IABV namespace was visible; that catalogue discrepancy remains unresolved and neither report proves global absence.

The purpose of this candidate is to determine whether the public source and existing contracts contain enough grounded implementation primitives to implement G1–G3. It is not permission to invoke the existing reader, authorize a protected read, release the active runtime block, or treat a newly added schema/class name as real authority.

## 3. Copy-ready task prompt for the existing Codex UI session

> **CODEX — IMPLEMENT OR BOUND THE M1A G1–G3 GOVERNANCE ROUTE IN THE ISOLATED CANDIDATE ONLY**
>
> **Authorization and exact target**
>
> The Owner explicitly authorized in this conversation a bounded implementation attempt for G1–G3, on an isolated candidate based on public `main`, subject to the restrictions below. Use repository `jhonf463r/Python`, base SHA `60c8ac6e7ff425c815d9bdc7194bf20ef8d134db`, branch `m1a-g1-g3-governance-route-candidate-20261022`. First verify the current session is operating in a separate candidate created from that exact base. If you are in the Owner's existing/dirty checkout, an unrelated local worktree, or cannot prove candidate identity, stop with `ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED`; do not inspect or alter that workspace.
>
> **Single objective**
>
> Establish, from the pinned public source and adopted M1A v1.0.1 requirements, whether a coherent G1–G3 route can be implemented without inventing authority. Implement only evidence-backed source changes that can operate safely with the actual trusted identity, issuer, catalogue/producer/revocation source, and versioned operation-to-target resolver that the repository demonstrably supplies. If any required real authority or trust root is absent, do not fabricate, hardcode, self-sign, infer or simulate it. Stop at the earliest dependency and provide the exact source paths, missing interface/evidence, and smallest decision or externally supplied artifact required.
>
> **Bounded evidence set**
>
> Start with the canonical public documents: `IABV_v1.5/AGENTS.md`, `IABV_v1.5/docs/history/CHAT-ARCH/README.md`, `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `MEMORY-OPERATING-PROTOCOL.md`, M1A v1.0.1 blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`, its prerequisite matrix, Entry 274 blob `5943a87d907436fc7ecac31534cbfcd31fe7de55`, and exact relevant source files only as needed to assess or implement G1–G3. Do not repeat broad tool inventories or restart the old contract review.
>
> **G1 — authenticated governance principal / trust anchor**
>
> Verify whether the repository provides an actual trust anchor and authenticated principal binding, not just a class name, configuration string, Owner statement, GitHub blob SHA, or caller-supplied identifier. If the real root of trust, key custody/rotation/revocation, principal authentication, or authority binding is missing, do not invent one. Report the exact blocker and stop before making a fake implementation appear operational.
>
> **G2 — catalogue publisher, producer policy, integrity and revocation**
>
> Verify whether a real, authoritative, versioned catalogue and active-set attestation exist; whether publisher and producer classes are authenticated/allowlisted; how integrity and version lifecycle are checked; and whether revocation is authoritative and checked at the appropriate decision boundary. A local hard-coded allowlist without a proven authorized publisher is not equivalent to this authority. If required evidence is absent, stop and report it.
>
> **G3 — server-side versioned operation-to-target resolution**
>
> Verify whether a trusted, versioned registry/resolver binds actual registered operation IDs and implementation/call sites to canonical targets. Do not treat caller-supplied `operation_scope`, a tool description, path strings, prefix matching, or World Model observations as authoritative target resolution. If no evidence-backed resolver exists, do not invent target mappings; document the absent authority and stop.
>
> **Required behavior and result**
>
> - Fail closed for missing, unknown, malformed, untrusted, conflicting, stale, revoked or unsupported evidence.
> - Keep diagnostic observation, human approval evidence, read decision, per-operation reader verification, ledger/receipt, and independent block release as separate authorities. No receipt grants permission.
> - Preserve M1A selector rules already adopted; do not silently change policy semantics or close G4–G8.
> - If a real trust dependency blocks the route, source edits are not mandatory. A precise `BLOCKED_MISSING_G1_TRUST_ANCHOR`, `BLOCKED_MISSING_G2_CATALOGUE_OR_REVOCATION_AUTHORITY`, or `BLOCKED_MISSING_G3_VERSIONED_TARGET_RESOLVER` result is preferable to invented plumbing. If some independently useful, evidence-backed portion can be implemented without implying readiness, explain and isolate it.
> - Deliver a diff or commit on the isolated candidate branch only, with exact base/head SHA, changed-path list, evidence for each claim, unresolved authorities, and a list of work explicitly not done. Do not merge, deploy or write main.
>
> **Strict exclusions**
>
> Do not access or modify the Owner's pre-existing/dirty checkout or unrelated candidate folders. Do not read or access `data/`, SQLite, user/production data, secrets, credentials, or `.env`. Do not invoke `mcp__iabv_v15_rsk01a5__read_repo_file`, `list_repo_directory`, or any local/alternative reader to test or bypass the gate. Do not execute tests, builds, linters that execute project code, probes, IABV, MCP runtime, Codex App Server, Ollama, other application processes, or real transport. Do not change machine security, GPU, model, credential, network or environment configuration. Do not merge, deploy, open the live reader, grant protected read authority, or release any operational block.
>
> Git operations and source edits, if needed to prepare the isolated candidate, must be limited to the exact candidate branch and must not be used to inspect the Owner's existing workspace. If the existing Codex session cannot establish a separate candidate without violating any restriction, stop; do not ask the Owner to run an administrator command as a workaround.
>
> **Final report format**
>
> Return one status:
> - `G1_G3_IMPLEMENTED_IN_CANDIDATE_STATIC_UNVERIFIED` — only if the required real primitives are source-supported and no tests/runtime claims are made;
> - `PARTIAL_CANDIDATE_WITH_EXACT_REMAINING_AUTHORITY_GAP` — useful bounded source changes exist, but one or more G1–G3 dependencies remain;
> - `BLOCKED_MISSING_G1_TRUST_ANCHOR`;
> - `BLOCKED_MISSING_G2_CATALOGUE_OR_REVOCATION_AUTHORITY`;
> - `BLOCKED_MISSING_G3_VERSIONED_TARGET_RESOLVER`;
> - `ISOLATED_CANDIDATE_IDENTITY_UNVERIFIED`.
>
> Include exact evidence paths/revisions, changed paths (if any), exact base/head, whether any tool or command was invoked, and the reason for any stop. Do not say the route is operational, the live block is released, or the bridge is ready.
>
> **Required terminal states**
>
> ```text
> GOVERNANCE=KEEP_BLOCKED
> IMPLEMENTATION=AUTHORIZED_FOR_ISOLATED_CANDIDATE_ONLY
> TESTS=NOT_RUN
> BUILD=NOT_RUN
> RUNTIME=NOT_RUN
> REAL_TRANSPORT=NOT_RUN
> OWNER_PREEXISTING_CHECKOUT=DO_NOT_ACCESS
> PROTECTED_LOCAL_READ=NOT_AUTHORIZED
> MERGE_DEPLOY=NOT_AUTHORIZED
> BLOCK_RELEASE=NOT_AUTHORIZED
> BRIDGE=BRIDGE_NOT_READY
> ```

## 4. Acceptance and stop conditions

- Accept only an exact candidate branch diff/commit tied to the pinned base.
- A set of type definitions, placeholders, default keys, Owner-supplied strings, or successful static edits is not evidence of an authenticated issuer or operational authorization.
- Do not close G1–G3 unless the actual required authority chain is supported by evidence, and do not close G4–G8 from this task.
- No tests/build/runtime/transport will have run under this authorization. A later test authorization, independent candidate review, or live-read/release decision would be a separate task and is not granted here.
- No prompt dispatch or Codex execution receipt is claimed merely because this handoff is saved.

## 5. Status at handoff preparation

```text
TASK=M1A_G1_G3_AUTHORITY_ROUTE_CANDIDATE_IMPLEMENTATION
OWNER_AUTHORIZATION=EXPLICIT_CHAT_AUTHORIZATION_RECEIVED
DESTINATION=CODEX_EXISTING_UI_SESSION
BASE_MAIN_SHA=60c8ac6e7ff425c815d9bdc7194bf20ef8d134db
CANDIDATE_BRANCH=m1a-g1-g3-governance-route-candidate-20261022
CANDIDATE_BRANCH_CREATED=YES
CODEX_PROMPT_DISPATCHED=NO
CANDIDATE_CODE_CHANGES=NONE_BY_COORDINATOR
G1_G2_G3_RUNTIME_AUTHORITY=NOT_ESTABLISHED
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=AUTHORIZED_FOR_ISOLATED_CANDIDATE_ONLY
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
```
