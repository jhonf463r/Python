# CHAT-ARCH-2026-10-13-251 — Codex exec 0.120 permission-profile dispatch path

- **Episode ID:** `CHAT-ARCH-2026-10-13-251`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** `main @ 53459ea69d0e5f15a9755d2dda5e614beecb22ef`
- **Related records:** entries 246–250.
- **Classification:** `CODEX_EXEC_V0120_PROFILE_ROUTE_STATICALLY_IDENTIFIED_LOCAL_BACKEND_UNPROVEN`
- **First open edge:** `CODEX_EXEC_V0120_PROFILE_ROUTE_BACKEND_AND_ENVIRONMENT_UNVERIFIED`

## 1. Why another cloud pass is useful

The pending Owner choice A/B/C is a decision gate for using a home, but it need not stop source-level analysis. The prior cloud audit in entry 250 established that public Codex 0.120 has filesystem permission profiles and Windows backend-dependent policy support. This pass narrows how a future non-interactive `exec` task might select that permission profile without accidentally forcing the legacy sandbox configuration path.

The exact source below is tied to the public tag `rust-v0.120.0`, not current Codex main. It is source evidence only; no local process, binary, authentication state, effective Windows backend or cost/quota was checked here.

## 2. Critical CLI/config interaction found in 0.120.0

### A. The normal `exec` harness forces non-interactive approval semantics

[Public `codex-rs/exec/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec/src/lib.rs), blob `81a0961fa4aec048d573903a3baff69c7c37e510`, constructs its harness `ConfigOverrides` with `approval_policy: Some(AskForApproval::Never)`. Thus `exec` is not a way to ask the user interactively to approve each shell command. Any future coding turn must rely on a pre-authorized exact task plus an enforced sandbox; denied actions must fail closed. A model request or prompt cannot be treated as approval to escape that boundary.

### B. A CLI sandbox flag selects legacy permission interpretation

The same source maps `--sandbox` to a non-empty `sandbox_mode`; `--full-auto` maps to `WorkspaceWrite`, and the dangerous bypass flag maps to `DangerFullAccess`.

[Public `codex-rs/core/src/config/mod.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/config/mod.rs), blob `eac8f9e361d2e6e4ccf28a81e483b523d6c5c40d`, contains `resolve_permission_config_syntax`. It selects `Legacy` immediately whenever `sandbox_mode_override` or a selected profile's `sandbox_mode` is set. Otherwise, it walks config layers from lowest to highest precedence: a layer specifying `sandbox_mode` selects legacy syntax, while a higher layer specifying `default_permissions` selects the permission-profile path. The resulting selected syntax decides whether the loader compiles `[permissions]` profiles to an effective filesystem/network policy.

This yields a decisive configuration rule for the candidate design: **do not use `--sandbox workspace-write`, `--full-auto`, or a `--profile` that declares a sandbox mode when relying on a profile whose purpose is to express exact read/write restrictions**. Those paths can switch permission interpretation to legacy. A future design should instead test, purely after separate authorization, a versioned config-override route that sets `default_permissions` and the corresponding `permissions` profile while leaving the CLI `sandbox_mode` override absent. It must also account for any higher-precedence or managed requirements; the source inspection is not proof that the Owner's effective environment will select that route.

### C. The 0.120 config-override parser permits inline TOML values

[Public `codex-rs/utils/cli/src/config_override.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/utils/cli/src/config_override.rs), blob `41be3ca6b69e49964fe15a4983291d58a0b45437`, parses each `-c/--config key=value` value as TOML when possible and applies dotted override keys. It also tests parsing inline tables. A single `permissions=<inline-table>` override is conceptually safer for a Windows path map than trying to express a path containing periods (such as `.codex`) through dotted override-key syntax.

This is a documented config-override capability, not a recommended exact command line for immediate use. Quoting, final merged configuration, cloud/admin constraints and effective resolution remain to be statically adjudicated before any runtime test.

## 3. Candidate profile shape (design only; no command executed)

The source supports a future **in-memory explicit permission profile** that would be passed to a single authorized `exec` invocation through the CLI config-override mechanism, without editing an existing authenticated home's config file. Exact syntax and precedence still need validation against source, the target configuration layers and the final launch contract.

The profile's intended security semantics are:

- The disposable candidate root is the only writable code workspace. Its canonical path and baseline tree must be bound to the SafeUI authorization before dispatch.
- The profile does not grant a general `:root = read` permission. Omitted paths remain denied under the restricted filesystem policy. This is how sensitive home/config/credential paths would be excluded, rather than adding a `none` carve-out beneath a broad readable root.
- A minimal/system-readable policy may be necessary for standard Windows execution. The exact allowed system/runtime roots must be constrained by the selected version/backend; never substitute full user-profile read access for missing defaults.
- The profile's child-command network permission remains disabled unless an explicit, separately authorized requirement exists. The Codex host's outbound connection to its service is a separate path and does not establish zero cost.
- MCP servers, plugins, app/connector capabilities and other external effects must be absent or disabled before the turn; do not assume a filesystem sandbox alone disables every host-level integration.
- Parent-process authentication and agent-child file access are separate: the Codex host may use a pre-approved session while sandboxed commands are denied access to the home's auth/config tree. If that exact separation cannot be enforced, keep the route blocked.
- A future coding child environment must be explicitly allowlisted. Public IABV `bootstrap.py` loads recognized secrets into its parent `os.environ`, and the public general UI runner has environment-merging launch paths. Do not reuse those semantics wholesale for a Codex executor.
- The executor must not request automatic escalation. Since `exec` sets `approval_policy=Never` in its harness, sandbox denials are to be treated as failures, not prompts to grant more permissions.

The profile route appears to avoid one specific design conflict: it could, in principle, use an existing approved Codex home for host authentication without writing a new `config.toml` or copying credential files. This is not yet a selected A/B route, and it does not prove that the installed backend can enforce the profile on this machine.

## 4. Windows backend feasibility is the remaining hard prerequisite

Entry 250 recorded the versioned [Core Windows sandbox matrix](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/README.md), blob `63d9cba53bfcf91b1cef60861fbe7174376a4afe`:

- The elevated Windows backend supports restricted reads plus explicit readable/writable roots and certain precise split filesystem policies.
- The unelevated restricted-token backend is documented as supporting the legacy full-read model for legacy `read-only`/`workspace-write` and a narrower split-policy subset.
- If a policy cannot be enforced by the selected backend or cannot round-trip without changing semantics, Codex says it fails closed rather than weakening it.

The candidate profile intentionally does **not** rely on broad root-read permissions, because those would make a credential-bearing home available to agent commands. Therefore the first technical discriminator is whether the backend already available on the Owner's Windows machine can enforce the proposed explicit readable-root/candidate-write profile while omitting the selected `CODEX_HOME` and all credential-bearing locations.

Do not assume `elevated` is provisioned merely because the versioned source implements it. Do not install, update, provision a sandbox, alter managed policy, or launch a command to discover this inside the current tranche. If a later non-mutating preflight cannot prove the relevant non-secret mode/policy, the route remains blocked.

## 5. Evidence ledger

| Claim | Classification | Consequence |
|---|---|---|
| Codex `rust-v0.120.0` declares exec `sandbox_mode`/profile inputs and config overrides | `PROVEN_BY_SOURCE` for that tagged code | Candidate design can be version-specific |
| Exec harness sets approval policy to `Never` | `PROVEN_BY_SOURCE` in the tagged `exec/src/lib.rs` | No interactive per-command approval; all writes must be pre-scoped by authorization and enforced policy |
| Non-empty CLI sandbox override forces legacy permission syntax | `PROVEN_BY_SOURCE` from `resolve_permission_config_syntax` | Avoid `--sandbox`/`--full-auto` in the candidate profile route |
| Higher-precedence `default_permissions` layer can select profile syntax when sandbox override/profile mode is absent | `PROVEN_BY_SOURCE` for the selector logic; final local merged result `UNPROVEN` | Static candidate only; config-layer requirements may change final result |
| Existing Windows backend can enforce candidate-only writes and keep selected home unreadable | `UNPROVEN` locally | No runtime authorization |
| Existing Codex home authentication is available with no additional spend | `UNPROVEN` | Keep A/B pending; no credential inspection or live turn |
| External MCP/plugin/app tools are all disabled pre-effect in the future route | `UNPROVEN` | Must be separately specified and verified |
| IABV consumer can verify the produced diff and evidence | `UNPROVEN` | Artifact handoff remains an independent gate |

## 6. First open edge and next action

**First open edge:** `CODEX_EXEC_V0120_PROFILE_ROUTE_BACKEND_AND_ENVIRONMENT_UNVERIFIED`.

Cloud source analysis has narrowed the candidate to a config-selected permission profile, rather than the legacy `--sandbox workspace-write` path. The next bounded task is to finish static analysis of the tagged 0.120 config layer precedence and the exact candidate-profile representation, especially how to keep the `CODEX_HOME` and secret directories out of readable roots while retaining only required Windows/runtime paths.

After this source-only work, a separately authorized local **non-mutating preflight** could check only:
1. the already-installed CLI identity/path (no execution to learn it),
2. the non-secret effective Windows sandbox mode/backend and whether the needed restrictions are already provisioned,
3. the selected candidate path and baseline,
4. whether required configuration/integration policy can be supplied without mutating the existing home,
5. the existing authentication/plan/no-extra-spend path without reading credentials or launching a task.

If the existing backend cannot prove this restriction, or the config route necessarily falls back to full-read legacy policy, retain C/block. This entry does not approve A or B.

## 7. Explicit non-authorization

No CLI/App Server invocation, process, turn, test/build, browser/CDP/UI action, credential/session inspection, local workspace read, configuration mutation, installation/update, new OAuth/API key, extra spend, commit/push or promotion is authorized. Preserve the owner-reported dirty worktree and untracked files.

The canonical writeback is cloud project memory, not evidence of a live local exchange, successful diff handoff, automatic model-weight learning or later causal reuse.
