# IABV — New-chat continuity handoff: PR #473 and verification preflight

Updated: 2026-10-23 (America/Bogota).
Repository: jhonf463r/Python.
Primary objective: GOVERNED_IABV_CODEX_BRIDGE.
This is a candidate-branch handoff only. It does not override live main.

## 1. Exact repository state at handoff preparation

    LIVE_MAIN=2a5ac42fabbd7c6a66591d127e379432495ad3bc
    CANDIDATE_BRANCH=codex/iabv-phase1-bridge-hardening-20261023
    CANDIDATE_HEAD_BEFORE_HANDOFF_WRITEBACK=ee3e921e6f2c9496ef0d9f9bea14a3cc8189e67a
    PR=473
    PR_STATE=OPEN
    PR_DRAFT=TRUE
    PR_MERGED=FALSE
    PR_BASE_SHA=2a5ac42fabbd7c6a66591d127e379432495ad3bc
    PR_CHANGED_FILES_AT_PRECHECK=35
    PR_BASE_AND_HEAD=REVALIDATE_AT_NEW_CHAT_START

GitHub's branch ref and PR endpoint agreed at the precheck. The candidate source blobs at that ref were verified by direct fetch:

- IABV_v1.5/src/iabv_v15/services/tools/tool_adapters.py: blob 5217b8deae01f34ec4402b82c651e9995ae94514.
- IABV_v1.5/src/iabv_v15/services/tools/tool_registry.py: blob 0599ae4ecd77d85cdee05a04fadcccaad2d5bea2.
- IABV_v1.5/tests/test_local_cli_adapter.py: blob fe53c660fd723ab82bde96b3077b25ca07cc24c2.

Continuity writes advance the candidate HEAD. These are source blob identities, not a promise that the branch HEAD remains ee3e921...; revalidate before any subsequent operation.

## 2. Canonical preflight completed against live main

The five required files were fetched from main in the mandatory order:

1. IABV_v1.5/AGENTS.md — blob 7fde748574fb8916e94332b99aa512fc44823bcc.
2. IABV_v1.5/docs/history/CHAT-ARCH/README.md — blob af29123091ae6090509b1039176458825e4b1a91.
3. IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md — blob f95f5bc69b98a7039d173089aa9b8d4d929812e9.
4. IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md — blob e073fe2d600c0b7b3051a10711ef21e2897b1ac3.
5. IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md — blob 4e497fb70f58a1a42d29470068e7a13b81cadc2f.

Authority hierarchy: live main/CURRENT-STATE.md alone determines canonical routing and NEXT_ACTION. Candidate-only continuity or older candidate-specific authorizations cannot overrule it. At this preflight, canonical main says:

    OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
    AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
    G1=NOT_ESTABLISHED
    G2=NOT_ESTABLISHED
    G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
    IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
    GOVERNANCE=KEEP_BLOCKED
    READ_LIST=FAIL_CLOSED
    IMPLEMENTATION=NOT_AUTHORIZED
    TESTS=NOT_RUN
    BUILD=NOT_RUN
    RUNTIME=NOT_RUN
    REAL_TRANSPORT=NOT_RUN
    MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
    AZURE_BILLING_STATE=NOT_VERIFIED
    COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
    BRIDGE=BRIDGE_NOT_READY
    AUTOMATIC_FOLLOW_ON=FALSE
    NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION

Entra/Authenticator setup is already owner-reported and must not be repeated. Option D is already ratified; do not ask for it again. Ratification is not proof that trust assets are absent and is not authority to inspect them. Never retry a denied reader or bypass its denial.

## 3. Security work and evidence provenance

### Confirmed by bounded static source review

- Common Sense tunnel-start action was made fail-closed: tunnel_start_prohibited, safe=False, no executor registered for that action.
- The legacy AppBootstrap MCP/tunnel subprocess hooks and supervisor are disabled in the inspected candidate source; source tests use mocked/forbidden Popen.
- MCP server entrypoint allows only stdio; sse and streamable-http are rejected before the server starts.
- ShellToolAdapter.run() unconditionally refuses generic shell execution; ToolTeachService.execute_task() blocks shell_command before adapter availability, sandbox, approval, or adapter invocation. Approval cannot bypass the early denial.
- LocalCliToolAdapter has an adapter-owned Cloudflared first-token allowlist (--version, version, help, tunnel); tunnel is limited to list and info. The guard uses tool ID, executable basename, command name, or tool family, so mutable allowed_verbs cannot simply enable access.
- During sandbox preflight, Cloudflared inspection is simulated and returns without a process invocation. ToolTeachService invokes ToolSandbox before it reaches the approval-waiting branch.
- Regression cases were added for access tcp/login/token, alternate ToolCard identity resolving to cloudflared.exe, Cloudflared sandbox no-process behavior, blocked tunnel run/create/delete/missing, and mock-only direct list/info.

### Tests: do not conflate the prior receipt with the latest candidate

- Owner previously reported 11 focused tests passed for the generic-shell closure at an earlier implementation stage using Python 3.14.4. The coordinator did not independently reproduce those results.
- Later Cloudflared access-verb, executable-identity and sandbox-no-process regression tests were added after that reported run. They are NOT RUN and NOT VERIFIED.
- Latest local Codex attempt stopped correctly because its worktree was clean but stale: local HEAD cb1a8b545bc29b13b6da1ada0f0204601805f7dc; local adapter blob 4e412ab8e5dfdf86af6f93ec04c15b0ed6434ca8; local test blob e9de76b25114e3b243f30e8e4830cdd651d75708. No pytest command ran, no files were modified by that attempt, and interpreter availability was not checked.
- Live GitHub returned no workflow runs or combined status checks for the inspected candidate. This is not evidence that CI is configured or globally absent.
- No app, MCP, Cloudflared, process, real transport, build, or deployment was run. Current process/tunnel state is not inspected.
- GLOBAL_PUBLIC_TUNNEL_PROHIBITION=NOT_ESTABLISHED: bounded source-path closures are not proof that every possible tunnel launch path in the application is absent.

## 4. Why the local preflight stopped, and how not to repeat the loop

The local directory was on the correct branch name and was clean, but at older HEAD cb1a8b5..., not the remote candidate. Its blobs did not match the candidate source/test blobs. This is an identity mismatch, not permission to reset the local checkout.

- Preserve the clean stale worktree unchanged; do not reset, rebase, clean, force-checkout, cherry-pick, or overwrite it.
- At next chat start, revalidate live main, candidate branch, PR #473 and exact blob IDs. Do not rely on a branch HEAD recorded in an old handoff.
- If an Owner explicitly reopens the bounded test scope, create a new empty sibling worktree detached at the freshly revalidated PR HEAD. Verify exact HEAD, source/test blobs, clean status and Python interpreter before any test.
- Under the current canonical main route, stop before pytest. The old candidate-only Phase 1 test authorization is not enough to override current live-main IMPLEMENTATION=NOT_AUTHORIZED / TESTS=NOT_RUN. Do not infer test authorization from a request merely to update continuity.
- Do not run tests until a genuinely new, explicit Owner decision reopens that exact bounded scope.

For a future expressly reauthorized test run, the intended narrow selection is recorded in the worktree mismatch receipt; keep tests mock-bounded with no Cloudflare or network activity.

## 5. Required continuation protocol

At the start of the next chat:

1. Revalidate live main, PR #473, candidate branch HEAD, Draft/unmerged state and source/test blobs.
2. Read the five canonical files from main in the exact order in Section 2; live main/CURRENT-STATE.md is routing authority.
3. Read this handoff and the referenced candidate receipts; keep Owner-reported evidence separate from directly verified GitHub/source evidence and from unrun tests.
4. Preserve the old clean worktree. No test execution unless a new explicit Owner decision changes the canonical authorization boundary.
5. Keep PR #473 open, Draft and unmerged. No app/MCP/Cloudflare, tunnel, transport, deployment, secrets/SQLite/protected-data access, spending or block release.

## 6. Canonical invariants — unchanged

    RATIFIED_OPTION_D_NO_BOOTSTRAP
    AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
    G1/G2/G3=NOT_ESTABLISHED
    IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
    GOVERNANCE=KEEP_BLOCKED
    READ_LIST=FAIL_CLOSED
    PUBLIC_TUNNEL=PROHIBITED
    REAL_TRANSPORT=NOT_RUN
    AZURE_BILLING_STATE=NOT_VERIFIED
    COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
    BRIDGE=BRIDGE_NOT_READY
    AUTOMATIC_FOLLOW_ON=FALSE

This handoff is continuity documentation on the candidate branch only. It neither modifies live main nor grants implementation, test, runtime, transport, merge or deployment authority.
