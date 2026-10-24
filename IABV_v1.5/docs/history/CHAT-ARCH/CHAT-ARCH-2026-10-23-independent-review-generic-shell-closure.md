# PR #473 — independent review of generic shell execution closure

- Review date: 2026-10-23 (America/Bogota).
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Base/main SHA: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- Reviewed HEAD: `cb1a8b545bc29b13b6da1ada0f0204601805f7dc`.
- Prior candidate HEAD: `795a44ae90ac5ebe8735ac804f52c969d0fb9c49`.
- Implementation commit: `e4bef794e336a84d538b99dcac3d959cf0c81573`.
- Continuity commit: `cb1a8b545bc29b13b6da1ada0f0204601805f7dc`.
- Review mode: bounded read-only static review of the published diff and relevant source. No source changes made by this review.

## Disposition

```text
GENERIC_SHELL_TOOLTEACH_GATE=STATIC_PASS
SHELL_ADAPTER_DIRECT_EXECUTION=STATIC_PASS
CLOUDflARED_CLI_FIXED_SUBCOMMAND_GUARD=STATIC_PASS_FOR_CLOUDFlARED_CLI_CARD
COMMON_SENSE_TUNNEL_START_ROUTE=STATIC_PASS_FOR_INSPECTED_RULE_AND_EXECUTOR_MAP
TARGETED_GENERIC_SHELL_CLOSURE=STATIC_PASS_WITH_SCOPE_LIMITS
GLOBAL_PUBLIC_TUNNEL_PROHIBITION=NOT_ESTABLISHED
FOCUSED_TESTS=OWNER_REPORTED_11_PASSED; NOT_INDEPENDENTLY_EXECUTED
CI_WORKFLOW_RUNS=NONE_RETURNED
COMBINED_STATUS_CHECKS=NONE_RETURNED
PR_REVIEW_SUBMISSIONS=NONE_RETURNED
PROCESS_OR_TUNNEL_STATE=NOT_INSPECTED
```

## Source findings

1. `ToolTeachService.execute_task()` resolves the ToolCard and then checks `card.tool_id == 'shell_command'` before adapter lookup, `is_available()`, approval evaluation, task synchronization, `ToolSandbox.run()`, and adapter execution. It returns a blocked `ToolResult`, records a blocked audit event and saves the result. The incoming `approved` argument is not applied before this denial, so approval cannot bypass this guard.
2. `ShellToolAdapter.run()` unconditionally returns `generic_shell_execution_disabled`; the method no longer calls `subprocess.run`. This also disables benign commands. That conservative behavior is justified while arbitrary shell syntax has no separately governed command-level authorization.
3. The prior Common Sense guard remains present: the tunnel-related rule/anomaly uses `tunnel_start_prohibited` with `safe=False`, and that action has no entry in `_ACTION_EXECUTORS` in the inspected source. The fixed `LocalCliToolAdapter` guard allows only the exact `cloudflared_cli` tunnel subcommands `list` and `info` and rejects other/missing subcommands before its process call.
4. The three new test cases cover the service gate with `approved=False` and `approved=True`, and direct adapter rejection in sandbox mode. Assertions verify that the service does not query adapter availability, execute the sandbox, evaluate approval, invoke the adapter, or call the patched process function.

## Test provenance and limits

The Owner's published receipt reports 11 focused tests passed in 1.56 seconds, exit code 0, using Python 3.14.4 at `C:\\Python314\\python.exe`; the two `list`/`info` cases reached only a mocked process. It also reports that a missing `pytest` import was added after the first collection attempt and that `git diff --check` passed. These test and worktree results were **not independently reproduced** in this review.

GitHub returned no workflow runs, no combined status checks, no review submissions, and no review threads for the reviewed head at inspection time. Those empty results do not prove a CI system is configured or globally absent.

A non-blocking documentation inconsistency remains in the `LocalCliToolAdapter` class docstring: it still describes `ShellToolAdapter` as executing free commands with `shell=True`, which is no longer true after this change. This review did not modify it.

## Boundary and required disposition

This review confirms only the identified generic-shell route through `ToolTeachService` and direct `ShellToolAdapter` calls are fail-closed in the inspected source. It does not establish the absence of every possible launch route in the whole application, nor whether any process/tunnel is currently running. No application, MCP server, Cloudflare CLI, shell command, network transport, build, deployment, or process inspection was run.

The live `main` route remains authoritative and unchanged: `RATIFIED_OPTION_D_NO_BOOTSTRAP`, `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`, `G1/G2/G3=NOT_ESTABLISHED`, `IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`, `GOVERNANCE=KEEP_BLOCKED`, `READ_LIST=FAIL_CLOSED`, `PUBLIC_TUNNEL=PROHIBITED`, `REAL_TRANSPORT=NOT_RUN`, `BRIDGE=BRIDGE_NOT_READY`.

Keep PR #473 `OPEN / DRAFT / UNMERGED`. This receipt is continuity evidence only; it is not acceptance, merge approval, runtime verification, authority evidence, or permission to continue implementation automatically.
