# PR #473 — Cloudflared CLI access-path closure review

- Date: 2026-10-23 (America/Bogota).
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Base/live `main`: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Prior reviewed candidate HEAD: `e69c4af8d059a9ad12d707f181528f9ebb84c2a9`.
- Implementation under review: current candidate branch `codex/iabv-phase1-bridge-hardening-20261023`; verify live HEAD before relying on this receipt.
- Review mode: bounded static source review and candidate-only code/test changes. No Cloudflared, process, application, MCP server, shell command, network transport, build, or deployment was executed.

## Finding

The existing `LocalCliToolAdapter` guard limited the second token of `cloudflared_cli tunnel` to `list` and `info`, but the ToolCard's general `allowed_verbs` still included `access`. Commands such as `cloudflared access tcp`, `access login`, and `access token` could pass the mutable metadata allowlist and reach `subprocess.run(shell=False)`. These are not `tunnel run`, so the tunnel-subcommand-only guard did not cover them.

A second boundary issue was found in the same path: `ToolTeachService.execute_task()` runs `ToolSandbox` before returning `waiting_approval`; `ToolSandbox` calls the adapter with `sandbox=True`. `LocalCliToolAdapter` previously ignored that flag and invoked the process. Therefore, an allowed Cloudflared inspection command could reach a process during sandbox preflight, before the human approval branch returns. This is a source-derived conditional path, not evidence that any command actually ran.

## Candidate changes

- `LocalCliToolAdapter` now enforces a code-owned allowlist for Cloudflared first verbs: `--version`, `version`, `help`, and `tunnel`. When `tunnel` is used, only `list` and `info` are admitted. The code identifies Cloudflared from the ToolCard ID, resolved executable basename, `command_name`, or `tool_family`; mutable `allowed_verbs` metadata cannot add `access`.
- The `cloudflared_cli` ToolCard removes the `access_info` capability and the `access` verb. The adapter guard is independent of this metadata and is the enforcement boundary.
- If Cloudflared reaches the sandbox phase, the adapter now simulates the permitted inspection and returns without invoking any process. A real inspection remains possible only on the later non-sandbox adapter call after the normal approval gate permits the task.
- Added focused regression tests for `access tcp`, `access login`, `access token` despite deliberately permissive card metadata; a custom ToolCard whose resolved executable is `cloudflared.exe`; and sandbox-mode `tunnel list/info` proving no subprocess call. Existing deny tests for tunnel `run/create/delete/missing-subcommand` and mocked direct `list/info` tests remain.

## Validation provenance

```text
STATIC_REVIEW=PASS_FOR_THE_INSPECTED_CLOUDFLARED_CLI_PATH
ACCESS_VERBS=DENIED_BY_FIXED_ADAPTER_ALLOWLIST
TOOLCARD_METADATA_OVERRIDE=DOES_NOT_EXPAND_FIXED_ALLOWLIST
CLOUDFLARED_SANDBOX=SIMULATED_NO_PROCESS
FOCUSED_TESTS=ADDED_OR_EXTENDED; NOT_RUN_BY_THIS_COORDINATOR
CI_WORKFLOW_RUNS=NONE_RETURNED
COMBINED_STATUS_CHECKS=NONE_RETURNED
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROCESS_OR_TUNNEL_STATE=NOT_INSPECTED
```

No independent test execution is claimed. Run the narrowly selected tests in the existing isolated Windows worktree, reporting the exact interpreter, command, exit code and count. Suggested selection:

```text
IABV_v1.5/tests/test_local_cli_adapter.py
IABV_v1.5/tests/test_tool_teach_service.py::test_generic_shell_tunnel_is_blocked_before_sandbox_or_approval
IABV_v1.5/tests/test_tool_teach_service.py::test_shell_adapter_rejects_commands_in_sandbox_without_subprocess
IABV_v1.5/tests/test_common_sense_tunnel_disabled.py
```

The test selection must remain focused and inert: tests may mock Cloudflared/process calls; do not run Cloudflared, use network transport, launch the app/MCP, access protected data/SQLite/credentials, build, or deploy. Report any failure, including setup/collection failures, without labeling it pre-existing absent a pinned-base comparison.

## Scope and remaining governance

The review closes the identified `cloudflared_cli access` route and pre-approval sandbox process behavior in the inspected adapter. It does not prove every possible launch surface in the entire application is absent, nor determine current process/tunnel state. The fixed CLI guard is not a substitute for transport authentication or independent operation authorization.

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
PR_473=KEEP_OPEN_DRAFT_UNMERGED
NEXT_ACTION=RUN_FOCUSED_UNIT_TESTS_IN_EXISTING_ISOLATED_WINDOWS_WORKTREE; REPORT_RESULTS; THEN_REVIEW_NEW_HEAD
```

Keep PR #473 `OPEN / DRAFT / UNMERGED`. This receipt is a bounded candidate review only; it does not modify live `main`, establish trust authority, close G1–G3, authorize runtime/transport, or release governance blocks.
