# M1 — Codex implementation handoff: governed scoped repository read

- Date: 2026-10-22 (America/Bogota).
- Episode: `EP-20261022-M1-GOVERNED-READ-IMPLEMENTATION-01`.
- North star: `GOVERNED_IABV_CODEX_BRIDGE`.
- Active task: `M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.
- Canonical authority: [CURRENT-STATE.md](./CURRENT-STATE.md).
- Owner authorization: the Owner explicitly replied **“ok procede”** to authorize Codex to build the administrative, governed-read route in an isolated candidate. This supersedes Option 2's previous *documentary-only* implementation restriction for this bounded candidate task only.
- Authorization boundary: it does **not** authorize reading/modifying the Owner's existing dirty checkout, inspecting `data/`/SQLite/secrets/`.env, executing tests, builds, processes, IABV, MCP, Codex CLI/App Server, Ollama, deployment or real transport; it does not authorize merging the candidate or claiming the live route is enabled.
- Dispatch truth: this ChatGPT session has no exposed action for executing/controlling the Owner's existing Codex UI session. This document is a prepared canonical handoff, **not evidence that Codex has received or started it**.

## 1. Current source evidence — pinned, bounded

Latest remote `main` observed before this continuity writeback: `7fb9c8bc9febbaa5e83e3c81959775ec1d3afcf8`. Before creating a candidate, Codex must refresh the actual remote `main` head and verify relevant file blobs; documentation-only continuity commits may have advanced the branch.

Relevant published-source files and blob identities observed at that snapshot:

| File | Blob SHA | Proven observation |
|---|---|---|
| `src/iabv_v15/infra/mcp/server.py` | `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c` | Registers `read_repo_file` and `list_repo_directory`; both use `_governance_block_for_route(assistant_kind="audit", requires_network=False)`. |
| `src/iabv_v15/infra/mcp/audit_tools/__init__.py` | `c1e468f4e504f778e7e9c366a05d549d42be84de` | Path helper rejects absolute paths, `..`, paths outside the resolved root and sensitive-name patterns; current path-resolution/open sequence is not by itself proof of race-resistant object containment. |
| `src/iabv_v15/domain/models.py` | `a9033d21052c519e09f482097599c704a62ea916` | `OperationalBlockRecord` contains distinct `assistant_kind` and `target_scope` fields. |
| `src/iabv_v15/services/evolution/world_model_service.py` | `ba0b5f5d6233330b549e09863975c77c0db735d6` | `grant_observation_permission` / `revoke_observation_permission` manage observation grants; `_block_records` produces block records from observed state. No dedicated supported read-decision issuer or audit-block release operation was identified in the inspected paths. |
| `src/iabv_v15/ui/viewmodels/control_center_viewmodel.py` | `628848c631e36b47b4a5b63b9e68d62687625235` | Existing `_grant_pending_observation_permission` path grants `observe_window_content:<assistant>`, then retries an external observation. It is not repository-read authority. |
| `src/iabv_v15/services/evolution/mcp_bridge_service.py` | `340c8f88e198655be86b874fd14c102d486bf8fd` | Controls MCP-server and Cloudflare-tunnel lifecycle. The public docs/source describe an externally reachable tunnel path. |
| `tests/test_mcp_server.py` | `93c11837d39eaee60d2c818e522284f0f9c261d6` | Existing registration and governance-gate regression tests. Tests may be edited for the candidate but **must not be executed under this authorization**. |
| `docs/mcp-bridge.md` | `e53709d10a7a40d089cc8a55c94a4a23f620718e` | Describes the current MCP/tunnel wiring, not an administrative grant path. |

### Confirmed causal gaps

1. The public `main` gate filters active blocks using `assistant_kind` and treats `""` / `"*"` as global; this path does not distinguish a block's specific `target_scope`. A block scoped to an unrelated operation can therefore be over-applied if its `assistant_kind` is empty. This is a proven public-source defect pattern, **not proof that it caused the live checkout's specific denial**.
2. A scope repair exists in candidate commit `b7c3fffaec4ff3b78b1ca03ae64ead949236f504`, branch `fix/iabv-operational-block-target-scope-repair-20261022`. Sonnet's `PASS` is static and candidate-only. The candidate is not merged; no live-server identity/adoption is proven and no test run is authorized here. Inspect and transplant only the applicable explicit-scope logic/tests into the new candidate; do not merge/rebase the old branch wholesale.
3. Existing read/list tools return denial diagnostics from the gate, but there is no dedicated user-facing pending scoped-read request → local owner approval → per-operation read-decision path in the inspected public source.
4. `approve_observation_permission` is not a repository-read grant. The broad `world_model_snapshot` is not a least-privilege replacement for a narrow diagnostic.
5. In `server.py`, the HTTP transport setup attempts to disable DNS-rebinding protection and allows wildcard hosts/origins for tunnel compatibility. Authentication of the active transport was **not verified** in this static review. Therefore, never expose an approval/grant/block-release method as a remotely callable MCP tool merely to make the UI work. Remote MCP requests may request access; only a trusted local UI interaction may approve it.
6. Do not infer that no route can exist globally. This is a bounded source result: no qualifying route was found in the paths above.

Sources: [M1 route proposal](./CHAT-ARCH-2026-10-22-M1-governance-route-minimal-design.md), [Entry 266](./CHAT-ARCH-2026-10-13-266-observation-approval-is-not-audit-release.md), [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md), [target-scope candidate review](./CHAT-ARCH-2026-10-22-candidate-target-scope-repaired-review.md), [issue #470](https://github.com/jhonf463r/Python/issues/470).

## 2. Exact Codex task

**Destination:** the Owner's existing Codex UI session, with the project's normal source-editing capability.  
**Mode:** implementation in a disposable candidate cloned from public GitHub source.  
**Candidate branch:** `codex/m1-governed-scoped-read-route-20261022`.  
**Suggested isolated directory:** `C:\\temp\\IABV_M1_GOVERNED_READ_CANDIDATE_20261022`; if it already exists, do not inspect, reuse or clean it—choose a new unique disposable directory.  
**Do not use:** the Owner's existing dirty checkout or its worktree/index/configuration. Do not try to retrieve local source through another tool.

Copy this task as the Codex instruction:

> Continue the canonical IABV task M1 from `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-22-M1-governed-scoped-read-route-CODEX-implementation-handoff.md` and `CURRENT-STATE.md`. Owner has explicitly authorized implementation in an isolated candidate only. Refresh remote `main`, confirm source blob identities and create a clean isolated clone/worktree and branch `codex/m1-governed-scoped-read-route-20261022`. Never read, write, reset, pull, stash, clean or otherwise touch the Owner's dirty checkout. Do not access `data/`, SQLite, secrets, credentials, `.env`, private runtime state or the live server.
>
> Implement the smallest coherent Control Center + MCP scoped-read workflow, reusing existing patterns where semantically valid:
>
> 1. **Narrow diagnosis:** expose only the metadata needed to explain the applicable read denial (block ID/type/status, `assistant_kind`, `target_scope`, reason and policy/source revision when authoritative). Do not return a full `WorldModelSnapshot` as an admin shortcut and do not read repository content during diagnosis.
> 2. **Request is not approval:** a remote MCP client can submit a finite pending request for a strict allowlisted relative path/set of paths, purpose, target workspace/root, output/byte budget, expiry and one-operation intent. Creating or polling a request must reveal no file content and grant no permission. Never trust a caller-supplied `approved_by`, principal, server ID, checkout ID or scope digest as proof.
> 3. **Local Control Center decision:** add a dedicated, explicit request-review surface using the existing local UI/viewmodel conventions. Show the exact target identity available from the server process, exact paths, purpose, budget, recipient/session evidence actually supported by the SDK, expiry and applicable blocks. Only a fresh explicit local UI approval may create a server-side read decision; the remote MCP surface must not expose the issuer/approval operation. Denial, expiry and revocation must be first-class outcomes. Preserve the already selected RQ224 Model A assumption for the first supervised prototype; do not reopen the A/B decision or invent a new identity subsystem, key issuer, paid service or credentials.
> 4. **Per-operation enforcement:** `read_repo_file` and `list_repo_directory` must require the matching server-side approval on every operation. Bind approval to the exact IABV process/session, workspace root/checkout identity, request ID, explicit relative paths, expiry and bounded budget. Enforce one-time use or atomic consumption. Unknown/mismatched/stale/revoked requests deny. Do not permit wildcard paths, arbitrary reads, a general-purpose builder grant or an alternative-reader bypass.
> 5. **Filesystem containment:** retain sensitive-path/size limits. Verify actual opened objects remain under the bound root; reject symlinks/reparse-point/root substitution and TOCTOU conditions to the degree supported by the platform. If this cannot be established safely without running authorized conformance tests, mark the candidate not ready for local reads and fail closed; do not overclaim safety from `Path.resolve()` alone.
> 6. **Correct block applicability:** transplant the reviewed `target_scope` repair from `b7c3fffaec4ff3b78b1ca03ae64ead949236f504` only after reconciling its exact source diff against current `main`. Keep a finite explicit set of recognized target scopes; unknown scopes fail closed. Treat `assistant_kind` and `target_scope` as separate dimensions. Registered non-applicable block scopes must not block an unrelated audit route; global/wildcard and genuinely applicable audit blocks still block.
> 7. **Separate block decision:** granting a read must never clear a block. A genuinely applicable audit/global block remains terminally denied unless a separate explicit decision from the competent block authority is available and verified. Surface the block and the reason in Control Center. Do not fabricate an authority, auto-release on read approval, or label an unrelated scope as a released block. Where the accepted local Owner/Model-A authority cannot safely support a distinct block decision, use `BLOCK_RELEASE_UNSUPPORTED` and keep reads blocked.
> 8. **Durable evidence:** record request, approval/denial, per-operation pre-effect intent, consumption, result and revocation with correlated IDs, target/path digests, limits, expiry and timestamps. Reuse existing audit persistence only if source evidence shows it fits these semantics; runtime tracer events alone are not automatically an independent immutable ledger. Do not inspect or mutate live `data/` or SQLite. If a trustworthy durable receipt cannot be implemented within the bounded changes, keep access fail-closed and report the exact missing component.
> 9. **Security review of transport:** do not launch or expose the tunnel. Do not add a new remotely callable admin-write tool while active MCP authentication/transport protection is unverified. The local UI is the approval surface; MCP is a request/read consumer only.
> 10. Add focused regression tests as source files if needed, but **do not execute tests, builds, lint, scripts or any commands that run the app** in this authorization. Do not install/update packages. Do not touch GPU, Ollama, model/provider settings, environment variables or unrelated source.
>
> Work only in the isolated candidate. No merge, deployment, release, live local read or transport. Produce a bounded diff and a report with: source baseline/HEAD SHAs, candidate branch/commit, exact files changed, each behavior added, known remaining hard blocks, tests authored but not run, tests/builds/runtime explicitly NOT RUN, and whether object-level containment/receipt integrity remain unproven. Do not claim M1 complete or the bridge ready solely because code has been written. If any mandatory trust boundary cannot be implemented safely within scope, stop that subpath, preserve fail-closed behavior, and report the smallest exact dependency instead of inventing it.

## 3. Required decision logic

A read is allowed only if every necessary predicate is true:

`ALLOW_READ = LOCAL_OWNER_APPROVAL_FRESH ∧ REQUEST_ID_MATCHES ∧ TARGET_IDENTITY_MATCHES ∧ EXACT_PATH_ALLOWED ∧ BUDGET_REMAINING ∧ NOT_EXPIRED ∧ NOT_REVOKED ∧ BLOCK_POLICY_ALLOWS ∧ RECEIPT_INTENT_DURABLE`

This conjunction is an acceptance invariant, not an assertion that its implementation exists. Unknown or unevaluable inputs evaluate to deny. Read approval and block release are distinct decisions. A request ID or audit receipt is evidence/correlation, not authority by itself.

Threat model to use during code review: spoofed client/principal, altered request scope, path escape/symlink/TOCTOU, replay/double-consumption, stale or revoked permission, hidden global block, self-release, receipt loss/rollback, and public-tunnel exposure. Prioritize least privilege, separation of duties, fail-closed semantics and provenance; no broad scan or unrelated refactor.

## 4. Expected candidate outcome and gates

- Candidate implementation: **authorized, isolated only**.
- Source edits on candidate: authorized only within the scope above.
- Candidate test code: may be authored; execution is **NOT AUTHORIZED**.
- Tests/build/lint/runtime/process launch: **NOT AUTHORIZED**.
- Dirty owner checkout/data/secrets/SQLite: **DO NOT ACCESS**.
- Current server/checkout identity: **UNVERIFIED**.
- Live authentication and tunnel policy: **UNVERIFIED**.
- Applicable block release: **UNRESOLVED until a distinct supported authority decision is evidenced**.
- Merge/deployment/real transport: **NOT AUTHORIZED**.
- M1 acceptance: remains open until implementation evidence is independently reviewed and separately authorized verification proves the required route in the intended environment.

## 5. Handoff truth

This file was written from the ChatGPT GitHub connector after bounded public-source inspection. It has not been consumed by Codex in this session. No source code was changed, no branch was created for implementation, no tests/builds/processes were executed, no local checkout/data/secrets were accessed, and no runtime permission or block was changed.
