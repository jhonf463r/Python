# Phase 1 MCP transport hardening — targeted static review and new-chat handoff

- Record date: 2026-10-23, America/Bogota.
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- Candidate source revision reviewed: `18feeb0872dfebd583fc1cf70674506277ced09a`.
- Pinned base / live `main` at the time of review: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Review type: coordinator's bounded static review of the two findings recorded in the immediately preceding turn. **This is not a full independent review of every PR change, not test execution by this reviewer, and not acceptance of the PR.**

## 1. Live state and revision boundary

At the time checked, PR #473 was `OPEN`, `DRAFT`, `UNMERGED`, `mergeable=true`; base SHA remained `2a5ac42fabbd7c6a66591d127e379432495ad3bc`; head SHA was `18feeb0872dfebd583fc1cf70674506277ced09a`; 20 files were changed. The branch commits are candidate-only. The canonical `main` tree has not received these Phase 1 source changes; do not treat candidate branch documents as merged/current-main state. Revalidate all refs before relying on these facts in a future chat.

The GitHub status query returned no workflow runs/checks for the reviewed SHA, and no PR review submissions or review threads were returned at that time. This means review/CI evidence was not available in the queried surface; it does **not** prove a failing check or global absence of review.

## 2. Targeted disposition

```text
TARGETED_STATIC_REVIEW=PASS_WITH_LIMITATIONS
SCOPE=POWERHELL_PORT_CLEANUP_REMOVAL_AND_GOVERNANCE_TRI_STATE
FULL_PR_INDEPENDENT_REVIEW=NOT_DONE
OWNER_REPORTED_FOCUSED_TESTS=48_PASSED
COORDINATOR_TEST_EXECUTION=NOT_RUN
GIT_DIFF_CHECK=OWNER_REPORTED_CLEAN; NOT_INDEPENDENTLY_RUN
```

### Finding A — PowerShell bootstrap side effects

Static review of the candidate source confirms `scripts/iabv_bootstrap.ps1` no longer dot-sources `_mcp_port_utils.ps1`, accepts the removed MCP-port argument, invokes `Stop-McpZombies`, calls `start_iabv.ps1`, or advertises a quick-tunnel URL. The new messages distinguish installing `cloudflared` from executing it. The helper file remains unchanged; no process was inspected or killed during this review. The static test `tests/test_iabv_bootstrap_script.py` asserts the removed cleanup/launch patterns are absent and preserves checks that official download sources remain present.

The accompanying `start_iabv.ps1` patch removes the MCP-port cleanup and bridge launcher call; the visible end message states that MCP/tunnel auto-start is disabled. The launcher `run_mcp_bridge.ps1` defaults to local stdio, rejects other transports and invokes Python synchronously; source inspection found no tunnel-launch path in that file. These are source-level conclusions, not PowerShell execution or proof about a process already running on the Owner's machine.

### Finding B — unknown governance state is not reported as clear

The candidate's `MCPBridgeStatus.governance_blocked` has the declared type `bool | None`. `to_dict()` preserves `None`; `_start_locked()` sets that value to `None` and refuses before calling the World Model evaluator or either runner. The ViewModel returns an explicit boolean only when the payload contains a boolean and otherwise preserves the uninspected result as `None` through a `QVariant` property. QML has distinct branches for `true`, `false`, and `null/undefined`; the uninspected branch says governance was not inspected and MCP is unavailable. Static tests cover serialization, ViewModel tri-state pass-through and QML wording. This source review did not launch the UI, so actual Qt/QML runtime representation is unverified.

### Other Phase 1 source observations within the same bounded inspection

- `AppBootstrap` legacy MCP/tunnel subprocess hooks return without launching; the supervisor path is inert in the inspected definitions.
- `infra/mcp/server.py` declares only `stdio` as an accepted transport and rejects other transports before invoking the MCP server run path; the inspected FastMCP constructor no longer disables SDK default transport-security protections or adds wildcard host/origin allowances.
- This keeps the candidate's operational posture fail-closed. It does **not** implement transport authentication, G1/G2/G3, Entry 274's per-operation reader/ledger contract, or a production-ready bridge.

## 3. Verification evidence — provenance preserved

The Owner reports a focused selection of four test modules finished with 48 passed and exit code 0 under Python 3.13.2; the first run had 46 passed plus two overly strict static-assertion failures, after which those assertions were adjusted and the same selection passed 48/48. The Owner also reports `git diff --check` clean. This coordinator did not run those commands and records them as `OWNER_REPORTED`, not independently executed evidence.

The earlier broader run reported 86 passed and two failures in World Model snapshot tests due to a fake fixture lacking `scan_stats`. No exact baseline comparison was run. Those two failures remain `UNRESOLVED`, not proven pre-existing and not attributed to this amendment.

Not run by the Owner for this amendment: PowerShell, application, AppBootstrap, MCP server, Cloudflare, any network transport, build, deployment or real transport. This coordinator likewise did not run them. Actual local process/tunnel state remains `UNVERIFIED`.

## 4. Current governance truth — unchanged

```text
OWNER_DECISION=RATIFIED_OPTION_D_NO_BOOTSTRAP
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION_AUTHORIZATION=BOUNDED_PHASE1_CANDIDATE_ONLY
PUBLIC_TUNNEL=PROHIBITED
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
```

The explicit Owner Option D no-bootstrap decision remains in force. Do not repeat Entra/Authenticator setup, retry the denied reader, invent a trust authority, inspect protected data/secrets/SQLite, create an Entra app or credential, incur costs, launch/reconnect Cloudflare, run the application/transport, merge, deploy or release a governance block. A public tunnel's active state is not established by this static review.

## 5. Exact next action

```text
NEXT_ACTION=FULL_REVIEW_OF_PR_473_DIFF_AND_BASELINE_COMPARE_TWO_WORLD_MODEL_SNAPSHOT_FAILURES
PR_473=KEEP_OPEN_DRAFT; DO_NOT_MERGE
BASE_SHA=2a5ac42fabbd7c6a66591d127e379432495ad3bc
LAST_REVIEWED_SOURCE_HEAD=18feeb0872dfebd583fc1cf70674506277ced09a
FOCUSED_TESTS=OWNER_REPORTED_48_PASSED
WORLD_MODEL_SNAPSHOT_FAILURES=2; BASELINE_COMPARISON=UNRESOLVED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
```

The next bounded review should (1) revalidate live `main` and PR #473 before reading code, (2) reread the canonical five-file preflight in required order, then read this handoff, the Phase 1 owner receipt, the static Entra assessment, the eight-gate matrix, the adopted design/adoption receipt and Entry 274; (3) independently review the **whole current PR diff**, preserving exact source revision and checking for residual launch/bypass paths and unsafe deletions; and (4) compare only the two named World Model snapshot tests on pinned base and current candidate in isolated unit-test context, without application startup, network, protected data or full-suite execution. Do not call the two failures pre-existing unless that comparison supports it.

If the PR head has changed after `18feeb0`, fetch and review the new head rather than reusing this source-level conclusion. This record is a continuity aid, not canonical `main` routing until its containing PR branch is merged.
