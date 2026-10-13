# CHAT-ARCH-2026-10-13-244 — Official Codex Windows sandbox docs refine the shortest coding-bridge route

- **Episode ID:** `CHAT-ARCH-2026-10-13-244`
- **Timestamp (America/Bogota):** `2026-10-13T12:20:05-05:00`
- **Timestamp (UTC):** `2026-10-13T17:20:05Z`
- **Canonical remote baseline at intake:** `main @ e7a5062357e53e19fe637b52bea72ffc6a75b5b5`
- **Prior technical report/adjudication:** [entry 243](./CHAT-ARCH-2026-10-13-243-codex-bounded-development-mode-blocked.md)
- **Classification:** Supplementary official-documentation review and route refinement; no local machine or product runtime inspected.

## 1. New externally verified information

Current official Codex documentation states that:
- Codex uses a native Windows sandbox when run in PowerShell; WSL2 uses the Linux sandbox implementation.
- The sandbox applies to commands spawned by the agent and their child processes, including commands such as git, package managers and test runners.
- The Windows sandbox enforces active filesystem and network permissions for those commands. It distinguishes sandbox permission mode from approval policy.
- `workspace-write` allows read/write operations in the approved workspace and routine local commands; `read-only` is not appropriate for code changes; `danger-full-access` removes filesystem/network boundaries.
- Current Windows implementations include `mxc`, `elevated` and `unelevated`. MXC availability is OS/build/policy-dependent; the docs identify Windows 11 24H2 build requirements and a one-command compatibility test in Codex CLI 0.162.0 and later. Legacy `elevated` requires administrator-approved setup; `unelevated` has weaker network isolation and lacks denied-read-path support.

Official sources:
- [Codex sandboxing](https://developers.openai.com/codex/security)
- [Windows sandbox](https://developers.openai.com/codex/windows)
- [Configuration basics](https://developers.openai.com/codex/config-basic)

These documents describe product capabilities. They do **not** establish which CLI binary is installed on the Owner's machine, whether native sandbox setup is present or effective, or whether the existing IABV App Server adapter requests a scope that maps to it.

## 2. Reconcile entry 243 without erasing its finding

Entry 243 remains accepted for the **current adapter composition**: its reported scope is an empty-root read-only consultation, its result is text/metadata rather than a candidate diff, and the reported Job Object is process containment—not by itself a file/network isolation mechanism. The existing route has not been shown to support a coding task.

This new documentation refines the *next investigation*: do not jump directly to designing a completely separate sandbox before checking whether Codex's existing Windows-native command sandbox is already a viable enforcement substrate.

The shortest candidate, if the exact local contract and effective configuration support it, is:

`normal SafeUI authorization → exact disposable candidate worktree → App Server coding turn with workspace-write sandbox → native Windows command/file/network enforcement → terminal task/thread/turn result → candidate diff/test artifacts → existing consumer + independent verifier → Owner promotion decision`.

This is a candidate architecture, **not an implementation or authorization to run it**.

## 3. Compatibility and enforcement gates still open

The Owner-supplied report states that IABV expects a Codex user-agent `0.120.0` but dynamically resolves an executable/shim from `PATH`. Actual CLI/protocol identity is therefore still `UNPROVEN`. The current MXC compatibility-probe docs mention CLI 0.162.0 and later; that does not by itself rule out older legacy sandbox modes, nor prove the older binary safely supports the needed App Server request.

The next source/design check must determine:
1. Whether the exact existing App Server protocol/adapter can request `workspace-write` against a named candidate root, while leaving the remote model/control connection functional and constraining agent-spawned commands.
2. Whether the existing Windows config already selects an effective implementation (`mxc`, `elevated` or `unelevated`) without requiring installation, new setup, permission changes or additional spending. If host version/config facts are unavailable under the allowed source-only scope, mark them `UNPROVEN`; do not run commands to discover them.
3. Whether the file and command boundary excludes the original worktree, unrelated user files and credentials, and whether network denial/allowlisting applies to spawned commands.
4. Whether MCP servers, apps/plugins, browser/computer-use and other effects are absent or constrained **before turn execution**. Native command sandboxing does not automatically prove that independently hosted integrations are disabled.
5. Whether the adapter can deliberately allow required coding actions inside the authorized sandbox instead of rejecting all command/file events, while still denying every effect outside scope.
6. Whether a deterministic, evidence-bearing candidate diff/tree digest and relevant test output can be captured and delivered to the existing `ToolResult`/consumer path.
7. Whether exact owner authority binds the destination, task ID, prompt/digest, baseline, candidate root, allowed paths/commands, network/integration policy, one-use semantics and explicit no-publication boundary.
8. Authentication mode, plan/quota/usage and cost remain separate gates; no credential contents, new OAuth, API key or charge is permitted.

## 4. Refined route choice

**Primary candidate to evaluate first:** reuse the current App Server transport with a distinct coding-task mode and Codex's existing Windows-native sandbox, only if the previous gates can be source-/configuration-proven for the actual supported contract.

**Fallback:** a distinct OS-enforced candidate executor only if the existing App Server/native sandbox combination cannot prove the needed boundary or return verifiable artifacts. Do not choose a VM, Windows Sandbox, AppContainer or other primitive solely because its documentation sounds safer; check compatibility with existing ChatGPT-plan authentication and the no-additional-spend constraint.

Neither path is ready to execute. No local version/config/sandbox setup is proven by this documentation review.

## 5. Next edge and action

Updated first open edge: `CODEX_NATIVE_WINDOWS_SANDBOX_IN_APP_SERVER_MODE_UNVERIFIED`.

Next task: bounded **source-only compatibility/design audit**, using the current IABV source that the Owner reported and the official version/platform sources above. Inspect the existing adapter's request construction, actual task CWD/root and sandbox policy, executable resolver/protocol expectations, existing Windows sandbox-related configuration handling, MCP/app registration and result/artifact capture. Do not perform broad upstream schema searches, run the CLI, query Windows capabilities, read secrets or alter configuration.

The deliverable must choose: (A) the smallest viable extension of the existing App Server path using the built-in Windows sandbox, with every enforcement layer and unresolved host fact listed, or (B) keep App Server coding mode blocked and specify the minimal distinct executor boundary. No coding implementation in this task.

## 6. Evidence/learning boundary

The current adapter remains `CODEX_BOUNDED_DEV_MODE_STATICALLY_BLOCKED` for code modification as reported. The official docs provide a new candidate realization, not proof it is available or active locally. GitHub writeback records the route refinement; this is external persistent memory, not autonomous model-weight change or causal learning.

No source edits, tests, process launches, local diagnostics, network calls from IABV, credentials, OAuth/API setup, install/download, cost, commit/push of product code or promotion are authorized by this record.
