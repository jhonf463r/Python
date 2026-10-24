# PR #473 — residual tunnel launch paths closed (2026-10-23)

## Identity and authority boundary

- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- Base: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Pre-change candidate HEAD: `fe83a99ed8115d5c034b33cb21e3573769925920`.
- Implementation commit: `003124a7aea63765aafc7915b193a4a9fb79e2d3`.
- PR state observed before changes: `OPEN / DRAFT / UNMERGED`, base and branch matched the values above. Revalidate after publication.
- Worktree was clean before edits. No candidate work was discarded or reconstructed.

This is a candidate-branch record. It does not modify the routing truth on `main`, close trust prerequisites, authorize protected reads, or establish that any tunnel is running.

## Baseline comparison: World Model snapshot tests

Before source edits, the following two test nodes were run separately in fresh detached worktrees at the pinned base and candidate:

```text
tests/test_mcp_server.py::test_world_model_snapshot_returns_current_without_refresh
tests/test_mcp_server.py::test_world_model_snapshot_refresh_triggers_request_refresh
```

Environment: `C:\Users\faber\miniconda3\python.exe`, Python 3.13.2; pytest cache disabled; bytecode disabled; candidate/base `src` supplied with `PYTHONPATH`; no application, MCP server, runtime service, network, or production storage was started or accessed.

Both nodes failed on both revisions (`2 failed in 3.65s` at base, `2 failed in 2.61s` at pre-change candidate; exit code 1 each). Both failures raise `AttributeError` because the fake World Model service in the test lacks `scan_stats`, which the MCP tool reads after `current_model()` or `request_refresh()`. The traceback points to `server.py` line 506 on base and line 484 on the candidate. The exact test outcomes establish that these failures are present on the pinned base and remain on the pre-change candidate; they were not changed or repaired in this tunnel task.

## Residual tunnel-route repair

The Common Sense rule and anomaly previously exposed `start_tunnel` as safe and mapped it to `_exec_start_tunnel()`, which called `subprocess.Popen(..., 'tunnel', 'run')`. The MCP tool calls `run_common_sense_reasoning()` with its default `execute=True`. The repair:

- Removes `_exec_start_tunnel` and its `_ACTION_EXECUTORS` registration.
- Replaces the rule/anomaly action with the non-executable `tunnel_start_prohibited`, marks it unsafe, and records that the public tunnel is prohibited. It has no executor and is returned as skipped.
- Adds a focused test that runs the reasoning pipeline with synthetic tunnel facts and `execute=True`, while asserting `subprocess.Popen` is not called and the prohibition is reported as skipped. Fact extraction, history lookup and ExperimentLab registration are replaced by inert test doubles; this is not runtime evidence.
- Adds fixed adapter enforcement for `cloudflared_cli`: `tunnel` permits only the exact second-token subcommands `list` and `info`. `run`, `create`, `delete`, a missing subcommand, and any other value fail before `subprocess.run`, even if mutable ToolCard metadata lists `run`.
- Adds the ToolCard metadata `allowed_subcommands: {'tunnel': ['list', 'info']}` and corrects its description. Existing `requires_human_approval=True` remains in force. This change does not claim to have exercised the upstream approval flow.
- Corrects `docs/mcp-bridge.md`, which previously said `iabv_bootstrap.ps1` was not modified in this phase. The corrected record distinguishes installing `cloudflared` from launching it.

## Verification actually performed

Focused command on implementation commit `003124a7aea63765aafc7915b193a4a9fb79e2d3`, Python 3.13.2, with pytest cache disabled and bytecode disabled:

```text
tests/test_common_sense_tunnel_disabled.py
tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it
tests/test_local_cli_adapter.py::test_cloudflared_declared_tunnel_inspection_subcommands_reach_mocked_process
tests/test_local_cli_adapter.py::test_cloudflared_card_does_not_whitelist_update_verb
```

Result: `8 passed in 2.06s`, exit code 0. The Common Sense test uses synthetic inputs and a mocked `Popen`; allowed CLI inspection cases use a mocked `subprocess.run`; blocked cases assert `subprocess.run` is never reached. These results do not prove a live transport or operational ingestion.

`git diff --cached --check` passed before the implementation commit. No broader suite, build, PowerShell script, application, AppBootstrap, MCP server, Cloudflare process, network operation, or real transport was run. The base/candidate comparison worktrees were retained; no cleanup or deletion was performed.

## Scope and remaining limits

- The direct Common Sense tunnel-start executor and `cloudflared tunnel run` route through `LocalCliToolAdapter` are statically closed and covered by focused mocked tests.
- Other effects reachable through other ToolCards or externally modified code are outside this bounded change. The adapter restriction applies specifically to `card.tool_id == 'cloudflared_cli'` and a leading `tunnel` token.
- ToolCard persistence/migration behavior for pre-existing stored cards was not tested. Missing `allowed_subcommands` fails closed for `tunnel` commands in the adapter; runtime registration was not launched.
- `PUBLIC_TUNNEL=PROHIBITED`; this repair does not inspect or establish local process/tunnel state.
- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`.
- `G1/G2/G3=NOT_ESTABLISHED`.
- `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`.
- `GOVERNANCE=KEEP_BLOCKED`.
- `READ_LIST=FAIL_CLOSED`.
- `REAL_TRANSPORT=NOT_RUN`.
- `AZURE_BILLING_STATE=NOT_VERIFIED`.
- `COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT`.
- `BRIDGE=BRIDGE_NOT_READY`.
- `PR_473=OPEN_DRAFT_UNMERGED` (revalidation required after push).

The next action is limited to publishing this candidate update on the existing PR branch and verifying the resulting PR refs/state. No merge, review-state promotion, deployment, or subsequent phase is authorized by this record.
