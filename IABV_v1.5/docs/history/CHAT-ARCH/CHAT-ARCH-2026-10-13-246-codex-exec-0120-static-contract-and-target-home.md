# CHAT-ARCH-2026-10-13-246 — Codex exec 0.120.0 static contract and IABV target-home boundary

- **Episode ID:** `CHAT-ARCH-2026-10-13-246`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline at intake:** `main @ d3e17abb488de6b2584c9acfc446c726cf026eb0`
- **Prior input:** Owner-supplied local report `CODEX_EXECUTION_INTERFACE_IDENTIFIED`
- **Related records:** entries 241–245.
- **Adjudication:** `CODEX_EXEC_INTERFACE_CONTRACT_IDENTIFIED_TARGET_POLICY_UNPROVEN`
- **Next edge:** `CODEX_EXEC_TARGET_HOME_AND_EFFECTIVE_POLICY_UNPROVEN`

## 1. Intake, provenance and local-state boundary

Accept the report's static identification for the resolver environment it inspected:

- branch `codex/m0a-safe-ui-boot`, HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`;
- reported 56 modified tracked files and 6 untracked files, including existing `.pyc` modifications;
- reported shim `C:\Users\faber\AppData\Roaming\npm\codex.cmd`, wrapper/package `@openai/codex 0.120.0`, native Windows x64 package `0.120.0-win32-x64`, and `codex.exe` whose metadata reports `0.120.0`;
- the report says no files/worktree were changed and no Codex process, App Server, CLI, tests or external request was executed.

This is **Owner-supplied inspection evidence**, not an independent inspection by this writer. Do not infer that the IABV child process has the same `PATH`, resolves the same binary, or uses the same Codex home. Preserve the entire dirty worktree; do not reset, clean, restore, stage, commit or publish its code.

## 2. Version-matched public CLI contract

Read the public Codex source at the explicit tag `rust-v0.120.0`, not current `main`:

- [`codex-rs/exec/src/cli.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec/src/cli.rs), blob `0225dc1768d4bbeb7514a104e1e1a2b1341653be`, defines `codex exec` as a non-interactive session and declares the options `--sandbox`, `--cd`, `--add-dir`, `--ephemeral`, `--output-schema`, `--output-last-message` and `--json` in its command struct.
- [`codex-rs/utils/cli/src/sandbox_mode_cli_arg.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/utils/cli/src/sandbox_mode_cli_arg.rs), blob `b7d1a248b8d4de45acfffa1ee9036f3030513a0d`, declares CLI mode values `read-only`, `workspace-write` and `danger-full-access`.
- [`codex-rs/utils/cli/src/config_override.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/utils/cli/src/config_override.rs), blob `41be3ca6b69e49964fe15a4983291d58a0b45437`, defines the global `-c/--config key=value` override mechanism.

These source files prove that the named public version declares an `exec` interface, sandbox-mode arguments and output-capture options. They do **not** prove the locally installed executable's runtime behavior, authentication/session availability, plan entitlement/quota/cost, Windows sandbox activation, effective integration/tool surface or an end-to-end artifact round trip.

The official [Codex iterative repair Cookbook](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex) is a useful pattern for separating review, candidate repair and validation, but its published setup pins `@openai/codex@0.130.0`. Do not copy its entire command line to `0.120.0` without checking the whole versioned parser. In particular, `--ask-for-approval` is not declared as a field in the reviewed `ExecCli` struct; acceptance through any other parser layer has not been established by that file. Do not launch the CLI simply to test the flag in this tranche.

## 3. Adjudication

The local route-identity subquestion has advanced from unknown to identified for the inspected shell environment. The broader Windows coding bridge remains blocked.

- `PROVEN_BY_SOURCE`: the `rust-v0.120.0` public source declares non-interactive `exec`, selectable sandbox modes and structured/final-message capture options.
- `OWNER_REPORTED`: the current-session Windows resolver points to package/native binary metadata identifying `0.120.0`; current SafeUI/App Server is integrated as a text/read-only route; the adapter sets `CODEX_HOME` explicitly.
- `UNPROVEN`: the environment actually inherited by IABV; the exact Codex home/config IABV would use; whether that home has a valid existing session; effective approval, sandbox and Windows backend; suppression of MCP/plugins or other external effects; usage entitlement/quota/cost; writable candidate root; complete diff/test artifacts; and ingestion by IABV's existing consumer.
- `UNPROVEN`: whether `--output-last-message` is sufficient for any desired artifact. It captures the agent's final message; it is not itself a verified source diff or provenance receipt.

The observed default config in this session (`sandbox_mode = "danger-full-access"`, `approval_policy = "never"`) belongs to a home that the report did **not** establish as IABV's effective home. It is not an approved configuration for IABV and must not be copied or treated as safe. Do not read or print credentials, session files, tokens or full process environments.

## 4. Next edge and minimum next task

**First open edge:** `CODEX_EXEC_TARGET_HOME_AND_EFFECTIVE_POLICY_UNPROVEN`.

Run one source/config-only inventory, without launching any Codex process or command:

1. Trace the existing IABV source that constructs the child environment and resolves its intended `CODEX_HOME`, `PATH`, working directory and CLI path. Distinguish fixed values, inherited values and fallbacks; do not assume they match the interactive shell used by the previous inventory.
2. Against the versioned `rust-v0.120.0` parser, enumerate the exact `exec` arguments that are actually supported by that version, and separately mark flags shown only in newer examples as unresolved unless the 0.120.0 source confirms them.
3. Locate only the configuration file that IABV would actually designate, if that path can be established from source. Inspect a strict allowlist of **non-secret** policy keys needed for route selection (sandbox mode and Windows sandbox settings, approval policy, config/profile selection, and whether integration sections are present). Report key presence/value only where non-secret; do not dump the file. Do not read credential or session contents, auth databases, API keys, token environment variables, or unrelated MCP/plugin secrets.
4. State whether the intended home is dedicated, inherited, temporary, missing or not statically resolvable. If its identity or effective policy cannot be determined without process execution, stop and name the smallest separately authorized diagnostic that would resolve it.
5. Compare the `exec` path to the existing App Server path for operation authorization, no-extra-spend eligibility, pre-effect containment, network/MCP/plugin policy, task identity, candidate diff receipt, output capture and current-consumer compatibility. Use `PROVEN_BY_SOURCE`, `OWNER_REPORTED`, `INFERRED` and `UNPROVEN` consistently.
6. Give a route decision: continue design of `exec`, keep it blocked, or identify the single missing fact. Do not create another executor or implement anything in this pass.

## 5. Explicit prohibitions and promotion gate

No process launch; no `codex --version`, `--help`, App Server or CLI invocation; no agent turn, external/network request, browser/CDP/UI action, tests, build, source/config edit, install/update/download, credential inspection, new OAuth/API key, billing or spend. Do not touch the existing dirty worktree. No commit, push, automatic promotion or claim of successful IABV→Codex→IABV execution.

A future capability fixture requires separate Owner authorization and must use a disposable candidate, a fixed harmless file change, verifiable baseline/diff/result artifacts, enforced workspace/network/integration restrictions, and owner-only promotion. Keep authentication/entitlement and no-extra-spend as independent gates.

## 6. Durable memory consequence

The identified CLI is a candidate interface, not an operational bridge. The versioned source narrows what can be claimed about `exec`; the next decisive fact is the **effective target home and policy IABV would give it**, not another generic search for a route.

GitHub persistence records external project memory and evidence provenance. It does not demonstrate automatic model-weight learning, autonomous recall, a live coding exchange or causal reuse. Leave those claims open until actual authorized artifacts pass the existing consumer/verifier and later reuse is evidenced.
