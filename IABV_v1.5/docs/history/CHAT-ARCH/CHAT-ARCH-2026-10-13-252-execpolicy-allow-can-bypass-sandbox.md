# CHAT-ARCH-2026-10-13-252 — Codex 0.120 execpolicy Allow can bypass the selected sandbox

- **Episode ID:** `CHAT-ARCH-2026-10-13-252`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** `main @ 8e525bcc65954001fed388b578401ccea39bf46b`
- **Related records:** entries 246–251.
- **Classification:** `CODEX_EXEC_V0120_POLICY_RULES_CAN_BYPASS_SANDBOX_SOURCE_CONFIRMED_LOCAL_RULESET_UNPROVEN`
- **First open edge:** `CODEX_EXEC_V0120_EFFECTIVE_EXEC_POLICY_RULESET_UNVERIFIED`

## 1. New critical source finding

Entry 251 identified a candidate configuration-profile route. It is **not safe to advance it on the assumption that a permission profile alone forces every command to stay sandboxed**.

The version-matched public source for Codex `rust-v0.120.0` establishes the following chain:

1. [`codex-rs/core/src/exec_policy.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/exec_policy.rs), blob `98bb815e91ab358a074a58401077fd0afb6b9ce4`, loads policy rules from the `rules/*.rules` directories associated with the applicable config-layer folders, in increasing precedence order. The default allow-rule file is `CODEX_HOME/rules/default.rules`; the full loaded set may include other config layers as well.
2. In the same file, an explicit policy match with `Decision::Allow` produces `ExecApprovalRequirement::Skip { bypass_sandbox: true, ... }`. The source tests the matched policy rules; this is distinct from Codex's built-in “known safe command” heuristic, which is not an explicit policy match.
3. [`codex-rs/core/src/tools/sandboxing.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/sandboxing.rs), blob `f5ceca5c2c6ff2cde8f2f785887919146b5d0aea`, maps a request with `bypass_sandbox: true` to `SandboxOverride::BypassSandboxFirstAttempt`.
4. [`codex-rs/core/src/tools/orchestrator.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/orchestrator.rs), blob `fed1ce8b2cb337975acf4a9661d492b300487c0b`, maps that override to `SandboxType::None` for the first attempt.

**Implication:** if the selected home/config layers contain an explicit `allow` rule that matches a model-generated command, that command may execute outside Codex's normal child sandbox even though a restricted filesystem permission profile was selected. That is a source-confirmed behavior in the named public version, not evidence that the Owner's local home actually contains such a rule.

Therefore, the current design may not rely only on `default_permissions`, `workspace-write`, a restricted network setting, or the default `approval_policy=Never`. The effective exec-policy rule set is another independent pre-effect control.

## 2. What remains protected by source semantics

The same version also shows positive policy-aware paths:

- [`codex-rs/core/src/tools/runtimes/apply_patch.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/runtimes/apply_patch.rs), blob `51f0cc83d52c79b656b5f78d8b62b5a93b52455f`, runs its self-invoked patch command under the current `SandboxAttempt` with a minimal environment for local turns.
- [`codex-rs/core/src/tools/handlers/apply_patch.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/handlers/apply_patch.rs), blob `0be920feb31f3f021e538daeb857b86e9067fc1b`, calculates requested write paths against the effective file-system sandbox policy and routes any extra permission needs through the permission machinery.
- [`codex-rs/exec-server/src/local_file_system.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec-server/src/local_file_system.rs), blob `10df5faa3f21c2874c44b5771fecc7eb64d4c18b`, calls sandbox-aware read/write checks for file operations when a sandbox policy is supplied.
- [`codex-rs/core/src/tools/handlers/mod.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/handlers/mod.rs), blob `022e02c39e20b7e991718266d044d2bca3fdf64a`, rejects a fresh additional-permission request under an approval policy other than `OnRequest` unless the requested permissions are already preapproved. In the exec harness, `approval_policy` is set to `Never`.

These are meaningful implementation contracts. They do not remove the execpolicy bypass branch for matching explicit `Allow` rules, and they do not prove the Owner's selected Windows backend actually enforces a future policy.

## 3. Revised design constraints

A future candidate route must satisfy **all** of the following before any coding turn:

1. **Resolve all applicable policy layers.** Determine which config folders contribute `rules/*.rules`, including the chosen Codex home and any higher/lower managed or system layers. Do not assume only `default.rules` applies.
2. **No command-level sandbox bypass.** Prove that no explicit `Allow` rule can match any command available to the agent during this task, or use a separately proven outer OS boundary that still confines the command if Codex sets `SandboxType::None`. If neither is possible, fail closed.
3. **Do not expose rule contents unnecessarily.** A later local preflight should report the number/status/provenance of applicable explicit allow rules and whether any can match the permitted command surface; do not dump private command patterns into ordinary conversation if a boolean/hashed evidence report suffices. Do not inspect credentials.
4. **Preserve approval semantics.** `approval_policy=Never` means there is no interactive approval backstop. Additional permission requests, timeouts and sandbox denials must not grant permissions by default, and no retry may silently change the sandbox.
5. **Keep prior gates.** Explicit candidate-only permission profile; minimal readable roots; selected CODEX_HOME/credential paths excluded from command-child access; restricted command-child network; unapproved MCP/plugin/app effects disabled before the turn; auth/session and zero-extra-spend independently established; correlated diff/consumer verification; Owner-only promotion.

An already-authenticated home could still be considered only if the applicable execpolicy is compatible with confinement or a separate already-provisioned OS boundary contains any policy bypass. A dedicated home is not automatically safe either: it could contain a copied or inherited policy, credentials, or config that re-enables bypass. Do not copy credentials or infer policy absence from a folder name.

## 4. Evidence boundary

| Claim | Classification | Consequence |
|---|---|---|
| Public Codex `rust-v0.120.0` explicit `Allow` rules can set `bypass_sandbox=true` | `PROVEN_BY_SOURCE` for this tag | Permission-profile route alone is insufficient |
| Orchestrator maps bypass to `SandboxType::None` | `PROVEN_BY_SOURCE` for this tag | Must evaluate the full rule set or rely on a separate outer OS boundary |
| Exec loads policy files from rule directories across config layers | `PROVEN_BY_SOURCE` for this tag | Inspect the resolved policy sources, not one file by assumption |
| Owner's actual effective rule set contains or lacks a matching Allow rule | `UNPROVEN` | No local execution claim can be made from cloud source |
| Local Windows backend confines commands even when Codex bypasses its own sandbox | `UNPROVEN` | Do not count Codex's inner sandbox as the outer boundary |
| Local auth/quota/cost and IABV's consumer can complete the handoff | `UNPROVEN` | Continue to block runtime |

## 5. Corrected first open edge and next step

**First open edge:** `CODEX_EXEC_V0120_EFFECTIVE_EXEC_POLICY_RULESET_UNVERIFIED`.

The next cloud-side task is static-only: inspect the remainder of the versioned execpolicy loading/precedence contract and determine whether `rust-v0.120.0` offers any built-in, non-runtime way to exclude user `rules/*.rules` from `exec`, without destroying the already-authenticated session or changing configuration. Do not assume such a switch exists. If no safe exclusion is exposed, the next route is an explicitly verified already-provisioned **outer** Windows boundary, or a local non-mutating preflight of all applicable rule layers. No home selection or coding turn is authorized by this record.

The eventual local preflight requires separate Owner authorization. It must not launch Codex, run commands, expose credentials, alter settings, install/provision software, create login state or incur additional spend. Until rule-driven sandbox bypass is addressed, preserve C/block as the operational default.

## 6. Explicit non-authorization

No process, CLI/App Server invocation, agent turn, test/build, credential/session inspection, network call into the Owner's machine, configuration or source edit, installation, OAuth/API key, extra spend, commit/push or promotion is authorized. Preserve all owner-reported dirty/untracked files.

Cloud source analysis and this writeback are external project memory only. They do not establish the Owner's effective local policy, runtime security, an IABV→Codex→IABV exchange, verified artifact ingestion or automatic model learning.
