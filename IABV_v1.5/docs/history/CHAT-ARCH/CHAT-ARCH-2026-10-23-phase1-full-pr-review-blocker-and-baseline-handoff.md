# PR #473 full static review — residual tunnel executor and World Model baseline handoff

- Review date: 2026-10-23, America/Bogota.
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- Live `main` SHA at preflight and closeout: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Current PR HEAD at review start: `846c597b604bb1bd19b4cd18e58c5a7e119b0081`.
- Code baseline reviewed: `18feeb0872dfebd583fc1cf70674506277ced09a`. GitHub compare shows the commits between `18feeb0` and `846c597` changed continuity documents only; no intervening source-code change was observed.
- Scope: all 21 changed-file patches in PR #473, startup/transport call paths, relevant UI/status propagation, relevant tests, and targeted searches for remaining tunnel-launch routes.
- Disposition: **`FULL_PR_STATIC_REVIEW=FAIL`**. Do not merge or mark ready. A remaining source-level route can start a Cloudflare tunnel through the Common Sense reasoning tool, contrary to `PUBLIC_TUNNEL=PROHIBITED`.

## 1. Canonical and PR state

The five-file canonical preflight was read from live `main` in the required order. Live `main` is still `2a5ac42fabbd7c6a66591d127e379432495ad3bc`. Its `CURRENT-STATE.md` remains the sole routing authority and says `NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION`. The bounded Phase 1 authorization and this receipt are candidate-branch records only; they do not alter the authority truth on `main`.

PR #473 remains `OPEN`, `DRAFT`, `UNMERGED`, base `main`, with 21 changed files. GitHub returned no PR review submissions, review threads, or commit status checks for the inspected HEAD. This is absence of evidence in the queried surfaces, not proof of global absence of review or CI.

The current PR diff includes changes to the startup scripts, `bootstrap.py`, `infra/mcp/server.py`, `MCPBridgeService`, ViewModel/QML, focused tests, and candidate continuity. The later four commits from `18feeb0` to `846c597` are documentation-only; the source-level conclusions below therefore apply to the same code source revision, with the candidate HEAD revalidated.

## 2. Canonical continuity and normative inputs reconciled

These records were fetched and reconciled during this review; they remain distinct evidence sources and authority boundaries:

- [Prior Phase 1 targeted-review handoff](./CHAT-ARCH-2026-10-23-phase1-transport-hardening-independent-review-handoff.md) — reviewed code SHA `18feeb0`, prior targeted scope, Owner-reported test provenance, and the exact requested full-review/baseline-comparison next action.
- [Original Phase 1 Owner resumption receipt](./CHAT-ARCH-2026-10-23-phase1-transport-hardening-owner-resumption.md) — bounded authorization and static pre-scan exception; no authority gate closes.
- [M1A G1 Entra no-cost static assessment](./CHAT-ARCH-2026-10-23-M1A-G1-Entra-no-cost-integration-static-assessment.md) — identity provider is only a candidate; IABV authority and HTTP endpoint protection are not implemented/proven.
- [M1A v1.0.1 eight-prerequisite evidence-gate matrix](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md) — eight implementation gates remain open.
- [Adopted M1A v1.0.1 operational-block scope contract](./CHAT-ARCH-2026-10-22-M1A-consolidated-operational-block-scope-contract-v1_0_1-candidate.md) — normative design artifact blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`; its historical candidate wording is preserved and interpreted with the later adoption receipt.
- [M1A v1.0.1 explicit Owner adoption receipt](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-explicit-owner-adoption-receipt.md) — adoption is normative design only, not implementation permission or runtime proof.
- [Entry 274 consolidated repository-read decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md) — unknown, malformed, unsupported or partially evaluable scope fails closed; trusted server-side target identity and independent authority cannot be fabricated from a test matrix or caller input.

Canonical `main` preflight files were read in required order. Candidate Phase 1 documents do not override `main` while PR #473 is unmerged. This review does not retry denied readers, inspect protected state, or reinterpret `SUPPORTED_ROUTE_NOT_FOUND` as a global claim that no route/assets exist.

## 3. Confirmed blocker — Common Sense can still start a public tunnel

The PR disables its direct bootstrap/service tunnel paths, but does not change `IABV_v1.5/src/iabv_v15/services/common_sense_engine.py`.

Static source evidence in the current candidate:

- `common_sense_engine.py:150-157` registers `tunnel_installed_not_running` with action `start_tunnel` and `safe=True`.
- `common_sense_engine.py:1385-1404`, `_exec_start_tunnel()`, calls `subprocess.Popen([... 'tunnel', 'run'])` on Windows when the portable binary is present and calls `subprocess.Popen(['cloudflared', 'tunnel', 'run'])` on other platforms.
- `common_sense_engine.py:1712` registers `'start_tunnel': _exec_start_tunnel` in `_ACTION_EXECUTORS`.
- `common_sense_engine.py:1801-1804` executes a registered action when `is_safe and execute_safe`. The anomaly route also produces a `safe=True` `start_tunnel` action at lines 766-774 and executes safe anomaly actions at lines 1879-1883.
- `run_common_sense_reasoning()` defaults `execute=True` (signature at approximately lines 2065-2077).
- `infra/mcp/server.py:2788-2803` exposes `common_sense_reasoning_tool(dry_run=False)`; it calls `run_common_sense_reasoning(..., dry_run=dry_run)` without overriding `execute`, so the default remains `True`.

Therefore a caller of the currently permitted local `stdio` MCP tool can reach an automatically executable rule/anomaly whose executor starts `cloudflared tunnel run` when its prerequisites fire. This is a concrete launch path in code, not evidence that the action fired or that a tunnel is currently active. Runtime tunnel/process state remains `UNVERIFIED`.

**Required correction before accepting Phase 1:** disable/remove the `start_tunnel` executor and its auto-executable rule/anomaly (or replace them with a non-launching, explicitly denied result) and add a focused regression test that proves the Common Sense route cannot invoke `Popen` for Cloudflare even with `execute=True`. Do not run the executor as a test.

## 3. Additional transport/tunnel and restart hazards

### Secondary CLI route (requires follow-up on approval boundary)

`services/tools/tool_registry.py:560-585` declares the `cloudflared_cli` ToolCard with `requires_human_approval=True`, but its `allowed_verbs` includes the broad first token `tunnel`; the note describes `tunnel list/info` inspection only. `services/tools/tool_adapters.py:2669-2694` validates only the first command token and its listed blocked tokens do not reject `run`; therefore `tunnel run` passes the adapter's local first-token/blocked-token checks if it reaches the adapter. Whether an upstream approval gate prevents that exact invocation was not verified here. Tighten the allowed subcommands/argument validation to inspection-only and test rejection of `tunnel run`. No CLI was invoked.

### Inert AppBootstrap path and remaining explicit helper

In the changed `bootstrap.py`, the ordinary `run()` path no longer probes the MCP port, schedules the deferred server/tunnel start, or starts its supervisor. The legacy subprocess hooks return `None`; the legacy supervisor is inert. The PowerShell entry points no longer kill processes by port or launch the tunnel wrapper; `run_mcp_bridge.ps1` defaults to `stdio`, rejects non-stdio transports and has no Cloudflare launch path. `server.py` accepts only `stdio` and no longer disables SDK DNS-rebinding defaults or installs wildcard host/origin allowances. These are static source findings only.

The explicitly invoked `scripts/mcp_hot_reload.py` remains a separate manual helper that can spawn/restart the server when someone runs that helper. The inspected server guard still rejects HTTP/SSE; no public-transport bypass through this helper was demonstrated. Do not describe this as proof that all possible server processes are absent.

### Governance service and UI

`MCPBridgeService._start_locked()` sets `governance_blocked=None` and refuses before a World Model read or runner call. Static tests preserve tri-state serialization and ViewModel/QML presentation of the uninspected state. QML/Qt runtime behavior was not executed.

`_governance_gate_block()` remains defined and returns `None` when its World Model is absent, unavailable or errors (around lines 305-337). No active caller was found in the current `MCPBridgeService` file because the start path rejects before consulting it. Record this as a latent fail-open helper, not a proven current service bypass; remove or harden before any future reactivation.

### Documentation and test-deletion assessment

`IABV_v1.5/docs/mcp-bridge.md` says `iabv_bootstrap.ps1` “no se ejecutó ni se modificó en esta fase”, but that file is in this PR's changed-file list and its patch removes port cleanup and bridge launch. Correct that statement so the record matches the code.

The old `MCPBridgeService` tests for successful server/tunnel startup, URL publication, live teardown and start/stop races were removed alongside the production launch implementation. That deletion aligns with the new prohibited-start posture. However, tests do not cover the still-registered Common Sense tunnel executor or the broad CLI `tunnel` subcommand route; those are material coverage gaps.

## 4. Requested World Model test comparison — not executed here

The two named tests are located in `IABV_v1.5/tests/test_mcp_server.py` in both the pinned base and candidate:
- `test_world_model_snapshot_returns_current_without_refresh` (around line 292).
- `test_world_model_snapshot_refresh_triggers_request_refresh` (around line 302).

The test function snippets are present in both source revisions, but static similarity does not prove whether either test fails or whether the failure is pre-existing.

Coordinator execution was blocked: there is no repository checkout in the execution environment, and `git ls-remote https://github.com/jhonf463r/Python.git` failed because the environment could not resolve `github.com`. GitHub connector reads can retrieve the source but cannot run these unit tests. No test was claimed as executed.

```text
TEST_world_model_snapshot_returns_current_without_refresh=UNRESOLVED; NOT_RUN_HERE
TEST_world_model_snapshot_refresh_triggers_request_refresh=UNRESOLVED; NOT_RUN_HERE
BASELINE_COMPARISON=UNRESOLVED
OWNER_REPORTED_FOCUSED_TESTS=48_PASSED; NOT_INDEPENDENTLY_REPRODUCED
CI_STATUS_CHECKS=NONE_RETURNED_FOR_REVIEWED_HEAD
PR_REVIEW_SUBMISSIONS=NONE_RETURNED
```

A failure may be labelled pre-existing only after the exact test is run on the pinned base and its output is captured. Run only those two test nodes against base and candidate, in isolated unit-test worktrees, before editing the candidate source. Do not run a full suite or any runtime/network operation.

## 5. Governance truth — unchanged

```text
RATIFIED_OPTION_D_NO_BOOTSTRAP=REMAINS_IN_FORCE
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
```

No application, AppBootstrap, MCP process, PowerShell script, Cloudflare process, network transport, build or deployment was run. No local process/tunnel status was read. Protected data, SQLite, credentials and `.env` were not accessed. G1, G2, G3 and all eight implementation prerequisites remain unestablished/open.

## 6. Exact next action

```text
NEXT_ACTION=RUN_ONLY_THE_TWO_WORLD_MODEL_TESTS_ON_PINNED_BASE_AND_CURRENT_CANDIDATE_BEFORE_SOURCE_EDITS; THEN_DISABLE_COMMON_SENSE_AND_CLI_TUNNEL_START_PATHS_WITH_REGRESSION_TESTS_IN_THE_SAME_PR
PR_473=KEEP_OPEN_DRAFT; DO_NOT_MERGE
BASE_SHA=2a5ac42fabbd7c6a66591d127e379432495ad3bc
PRE_REPAIR_CANDIDATE_SHA=846c597b604bb1bd19b4cd18e58c5a7e119b0081
FULL_PR_STATIC_REVIEW=FAIL
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
```

Next actor: Codex in the existing isolated Windows worktree/branch and same PR. First capture the two exact test outcomes on the pinned base and on candidate SHA `846c597b604bb1bd19b4cd18e58c5a7e119b0081`, without modifying source. Then apply only the tunnel-path closure above plus precise regression tests and the documentation correction; preserve all prohibitions, update this continuity record/routing with the new SHA, and leave PR #473 Draft and unmerged. No Entra setup, protected reads, app/transport launch, Cloudflare, deployment or spend.

This receipt is a new append-only review record, not a rewrite of earlier review history and not canonical `main` state while PR #473 remains unmerged.
