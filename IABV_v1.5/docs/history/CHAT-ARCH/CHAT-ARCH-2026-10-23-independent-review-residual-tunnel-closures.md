# PR #473 — independent review of residual tunnel-route closures

- Review date: 2026-10-23 (America/Bogota; GitHub updates may display UTC date 2026-10-24).
- Repository: `jhonf463r/Python`.
- PR: [#473 — Harden Phase 1 MCP bridge transport](https://github.com/jhonf463r/Python/pull/473).
- Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`.
- `main` verified before review: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- PR head reviewed: `686c7ad9c4be5b86b757e2b9da68e1df97e3d337`.
- Product-code commit reviewed: `003124a7aea63765aafc7915b193a4a9fb79e2d3`.
- Continuity commit reviewed: `686c7ad9c4be5b86b757e2b9da68e1df97e3d337`.
- Review mode: independent static review of published diffs and relevant in-repository call paths. No test, application, MCP, shell, PowerShell, or tunnel was executed by this reviewer.
- Disposition: `TARGETED_PATCH_REVIEW=PASS_WITH_LIMITATIONS`; `GLOBAL_PUBLIC_TUNNEL_PROHIBITION=NOT_ESTABLISHED` because a separate generic local shell path still executes arbitrary commands without enforcing its sandbox argument. Do not represent the application-wide no-tunnel invariant as proven.

## 1. Refs, patch and receipt verified

At review start, live `main` remained `2a5ac42fabbd7c6a66591d127e379432495ad3bc`. PR #473 was `OPEN / DRAFT / UNMERGED`, based on that SHA, with branch `codex/iabv-phase1-bridge-hardening-20261023` at `686c7ad9c4be5b86b757e2b9da68e1df97e3d337`.

GitHub commit comparison confirms:
- `fe83a99...` → implementation commit `003124a...`: six files, product/source/test/documentation changes.
- `003124a...` → continuity commit `686c7ad...`: three documentation files only.
- Combined change matches the stated nine files: Common Sense engine, local CLI adapter, ToolCard, two test files, bridge documentation, and three continuity files.

The residual-tunnel closure receipt is present at [`CHAT-ARCH-2026-10-23-phase1-residual-tunnel-closures.md`](./CHAT-ARCH-2026-10-23-phase1-residual-tunnel-closures.md). Its claims remain attributable to that receipt unless independently corroborated below.

## 2. Targeted Common Sense closure — static pass

In `services/common_sense_engine.py`:
- The `tunnel_installed_not_running` rule now emits action/conclusion `tunnel_start_prohibited` and is marked `safe=False`.
- The corresponding anomaly emits `tunnel_start_prohibited` and is marked `safe=False`.
- `_exec_start_tunnel()`, which previously called `subprocess.Popen(..., 'tunnel', 'run')`, is removed.
- The `start_tunnel` registration is absent from `_ACTION_EXECUTORS`.

The new `test_common_sense_reasoning_never_launches_tunnel_even_when_execute_true` uses synthetic facts and patches `Popen`; statically, its expected assertion corresponds to the new no-executor behavior. This directly addresses the previous Common Sense launch finding. It does not prove runtime state or eliminate other command-execution surfaces.

## 3. Targeted Cloudflared CLI closure — static pass with scope limit

In `LocalCliToolAdapter.run()`, after tokenization, the fixed check for `card.tool_id == 'cloudflared_cli'` and leading token `tunnel` accepts only second-token `list` or `info`. The fixed class constant—not mutable ToolCard `allowed_subcommands` metadata—is the enforcement source, so adding `run` to that metadata alone does not override the check. Missing, `run`, `create`, `delete`, and other second-token values are rejected before `subprocess.run`.

The new parameterized blocked test and the two allowed inspection tests match that behavior in static review. The production ToolCard still has `requires_human_approval=True`, and its description/notes now say only list/info are allowed. The external/upstream approval flow has not been invoked or independently verified; approval behavior is not treated as proven. The source guard is keyed to the exact tool ID and the `tunnel` leading-token form, so it is not itself a universal policy for every ToolCard that might launch an executable.

## 4. Additional finding — generic ShellToolAdapter leaves a separate launch surface

This is outside the files modified by commit `003124a`, but it matters if `PUBLIC_TUNNEL=PROHIBITED` is intended as an application-wide guarantee.

Source references on the reviewed candidate:
- `services/tools/tool_registry.py:190-198`: the default `shell_command` ToolCard uses adapter key `shell` and declares `run_command`; it does not set `requires_human_approval=True`.
- `domain/models.py:1239-1250`: `ToolCard.requires_human_approval` defaults to `False` and `supports_write` defaults to `False`.
- `services/tools/tool_adapters.py`, `ShellToolAdapter.run()`: accepts a `RUN_COMMAND` action (or `task.metadata['command']`), checks only a short blocklist that does not include Cloudflare/tunnel launch, then calls `subprocess.run(command, ..., shell=True)`. The method does not refuse to execute when `sandbox=True`.
- `services/tools/tool_teach_service.py:749-895`: `execute_task()` runs `self.sandbox.run(..., adapter=adapter)` before its approval-required check, then invokes the adapter again for the final run. `ToolSandbox.run()` passes `sandbox=True` to the adapter; the generic ShellToolAdapter ignores that flag.

Consequently, if the local ToolTeachService receives a `ToolTask` targeting `shell_command` whose RUN_COMMAND is `cloudflared tunnel run`, the generic adapter path can execute the command; the supposed sandbox call does not prevent it. This is a static conditional path, not proof it was invoked, and no shell command was run during review. I did not find a direct MCP tool in the reviewed `server.py` that dispatches arbitrary ToolTeachService shell tasks; therefore this is recorded as a broader local-application execution gap, not as a demonstrated bypass through the current stdio MCP interface.

The global invariant that public tunnel creation/launch is prohibited is therefore **not enforced across the entire local tool layer by this PR**. The two specifically targeted routes are closed, but the application-wide guarantee remains unestablished until the generic shell/sandbox path is guarded or an independently verified upstream invariant is shown to block the operation before the adapter executes it.

Recommended bounded follow-up in the same isolated candidate, subject to the existing Phase 1 scope: make the generic shell adapter actually non-executing under sandbox mode and require appropriate approval for shell tasks; ensure the prohibited Cloudflare tunnel invocation is denied before any subprocess call. Add mocked tests proving no command runs during the sandbox preflight and no tunnel command executes without the permitted explicit route. Do not run Cloudflare or a shell command to test the prohibition.

## 5. Test and verification provenance

The closure receipt records `8 passed in 2.06s` on Python 3.13.2, including the two new targeted test areas. The implementation commit's source and test patches are verified on GitHub, but **I did not independently execute these tests** in this review environment. No GitHub status checks were returned for the reviewed PR head at the queried status surface.

The receipt also records that the two World Model snapshot tests failed identically on the pinned base and pre-change candidate due to a fake missing `scan_stats`. I inspected that receipt but did not repeat the executions; their run results remain `OWNER_REPORTED_IN_RECEIPT` here. That historical failure must not be described as independently rerun by this reviewer.

```text
TARGETED_COMMON_SENSE_TUNNEL_CLOSURE=STATIC_PASS
TARGETED_CLOUDFLARED_CLI_SUBCOMMAND_GUARD=STATIC_PASS_FOR_CLOUDFLARED_CLI_ID
OWNER_REPORTED_FOCUSED_TESTS=8_PASSED; NOT_INDEPENDENTLY_EXECUTED
WORLD_MODEL_BASELINE_COMPARISON=REPORTED_IN_RECEIPT; NOT_RERUN_BY_THIS_REVIEWER
GENERIC_SHELL_COMMAND_LAUNCH_SURFACE=OPEN_IN_SOURCE; NOT_EXECUTED
MCP_DIRECT_SHELL_DISPATCH=NOT_FOUND_IN_REVIEWED_SERVER_TOOL_SURFACE; NO_GLOBAL_ABSENCE_CLAIM
GLOBAL_PUBLIC_TUNNEL_PROHIBITION=NOT_ESTABLISHED
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
PR_473=KEEP_OPEN_DRAFT; DO_NOT_MERGE
```

## 6. Exact next action

```text
NEXT_ACTION=GUARD_GENERIC_SHELL_SANDBOX_AND_CLOUDFLARED_TUNNEL_LAUNCH_BEFORE_ANY_SUBPROCESS; ADD_NARROW_MOCKED_TESTS; THEN_INDEPENDENTLY_REVIEW_NEW_HEAD
PR_473=KEEP_OPEN_DRAFT; DO_NOT_MERGE
BASE_SHA=2a5ac42fabbd7c6a66591d127e379432495ad3bc
REVIEWED_IMPLEMENTATION_COMMIT=003124a7aea63765aafc7915b193a4a9fb79e2d3
REVIEWED_PR_HEAD=686c7ad9c4be5b86b757e2b9da68e1df97e3d337
FULL_GLOBAL_NO_TUNNEL_GUARANTEE=NOT_ESTABLISHED
```

Next actor: Codex in the existing isolated worktree and same PR. Do not launch IABV, MCP, Cloudflare, PowerShell, shell commands for reproduction, network transport or any deployment. First make the generic shell sandbox actually fail closed before process creation, and make the tunnel prohibition effective even when a task is routed to `shell_command`; add mocked regression tests. Preserve the existing Cloudflared-specific fixed guard. Then run only the affected unit tests (no full suite), record actual outputs and new SHA, update continuity and request another independent static review. Do not promote the PR, merge, or claim the global tunnel invariant is closed until evidence supports it.

This is an append-only independent review receipt on the candidate branch. It does not change `main`, authorize additional trust/read gates, or establish that a tunnel is running.
