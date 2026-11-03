# PR #473 — generic shell execution fail-closed closure

- Date: 2026-10-23 (America/Bogota).
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- Base: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Candidate before this change: `795a44ae90ac5ebe8735ac804f52c969d0fb9c49`.
- Implementation commit: `e4bef794e336a84d538b99dcac3d959cf0c81573`.
- Review mode: bounded implementation and focused unit tests in the existing isolated worktree. No application, MCP server, Cloudflare, shell command, network transport, build, or deployment was started.

## Change

`ToolTeachService.execute_task()` now rejects `shell_command` immediately after resolving its ToolCard and before adapter availability checks, approval evaluation, `ToolSandbox`, or adapter invocation. It records a blocked result and audit event. The `approved` argument cannot bypass this rule.

`ShellToolAdapter.run()` now always returns `generic_shell_execution_disabled`, regardless of the `sandbox` argument. It no longer invokes `subprocess.run(..., shell=True)`. This disables benign generic shell commands as well as tunnel commands: the existing generic shell contract has no robust command-level authorization, and a textual denylist cannot safely constrain arbitrary shell syntax. The existing `LocalCliToolAdapter` guard for `cloudflared_cli` was not changed; its allowed tunnel subcommands remain `list` and `info`, while absent, `run`, `create`, `delete`, and other subcommands remain rejected before process execution.

## Focused evidence

The affected focused selection executed with `python -m pytest -p no:cacheprovider`:

```text
IABV_v1.5/tests/test_tool_teach_service.py::test_generic_shell_tunnel_is_blocked_before_sandbox_or_approval[False]
IABV_v1.5/tests/test_tool_teach_service.py::test_generic_shell_tunnel_is_blocked_before_sandbox_or_approval[True]
IABV_v1.5/tests/test_tool_teach_service.py::test_shell_adapter_rejects_commands_in_sandbox_without_subprocess
IABV_v1.5/tests/test_common_sense_tunnel_disabled.py
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it[run]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it[create]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it[delete]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_tunnel_run_is_blocked_even_if_card_metadata_lists_it[]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_declared_tunnel_inspection_subcommands_reach_mocked_process[list]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_declared_tunnel_inspection_subcommands_reach_mocked_process[info]
IABV_v1.5/tests/test_local_cli_adapter.py::test_cloudflared_card_does_not_whitelist_update_verb
```

Result: `11 passed in 1.56s`, exit code `0`, Python `3.14.4` at `C:\Python314\python.exe`. The test run used mocks for process creation; the two `list`/`info` cases reached only a mocked process. A first collection attempt failed because the new test module lacked `import pytest`; that import was added and the focused selection above then passed. Test-generated tracked `.pyc` changes were restored to their pre-test content; the final implementation commit contains only the two source files and the test file.

`git diff --check` passed before commit. No full suite, build, runtime, real command, tunnel, or transport was run.

## Scope and remaining limits

- The generic `shell_command` route through `ToolTeachService` and direct `ShellToolAdapter` execution are statically fail-closed.
- The existing Common Sense tunnel prohibition and fixed `cloudflared_cli` subcommand guard were retained and their targeted regression tests passed.
- This does not prove the absence of every other tunnel-launch path in the application or current process state. No tunnel was launched or queried.
- `RATIFIED_OPTION_D_NO_BOOTSTRAP=REMAINS_IN_FORCE`.
- `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`.
- `G1/G2/G3=NOT_ESTABLISHED`.
- `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`.
- `GOVERNANCE=KEEP_BLOCKED`.
- `READ_LIST=FAIL_CLOSED`.
- `PUBLIC_TUNNEL=PROHIBITED`.
- `REAL_TRANSPORT=NOT_RUN`.
- `AZURE_BILLING_STATE=NOT_VERIFIED`.
- `COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT`.
- `BRIDGE=BRIDGE_NOT_READY`.
- PR #473 must remain `OPEN / DRAFT / UNMERGED`; no deployment or automatic follow-on is authorized.

```text
GENERIC_SHELL_SERVICE_GATE=BLOCKED_BEFORE_AVAILABILITY_SANDBOX_APPROVAL_AND_ADAPTER
GENERIC_SHELL_ADAPTER=UNCONDITIONALLY_DISABLED
APPROVAL_BYPASS=BLOCKED
COMMON_SENSE_TUNNEL_GUARD=FOCUSED_TEST_PASS
CLOUDFLARED_CLI_FIXED_SUBCOMMAND_GUARD=FOCUSED_TEST_PASS
FOCUSED_TESTS=11_PASSED
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
PR_473=KEEP_OPEN_DRAFT; DO_NOT_MERGE
```
