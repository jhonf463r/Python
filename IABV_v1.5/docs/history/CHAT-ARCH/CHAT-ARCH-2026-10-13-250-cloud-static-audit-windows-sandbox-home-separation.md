# CHAT-ARCH-2026-10-13-250 — Cloud-side static audit: Windows sandbox and authenticated-home separation

- **Episode ID:** `CHAT-ARCH-2026-10-13-250`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote `main` verified before this writeback:** `1383bbb5a8f430379408c29882834289ceef915e`
- **Prior canonical decision:** entry 249, `CODEX_EXEC_OWNER_DECISION_PACKAGE_REVIEWED_NO_SELECTION`
- **Related records:** entries 243–249.
- **Classification:** `CODEX_EXEC_CLOUD_DESIGN_AUDIT_CONTINUES_LOCAL_EFFECTIVENESS_UNPROVEN`
- **First open edge:** `CODEX_EXEC_WINDOWS_HOME_READ_DENIAL_FEASIBILITY_UNVERIFIED`

## 1. Why analysis can continue in the cloud, and where the boundary actually is

Cloud-side work is not blocked. This pass independently read the current GitHub `main`, the versioned public Codex source at `rust-v0.120.0`, and the canonical entries 246–249. That supports source-level architecture analysis and documentation writeback.

It does not create a remote execution channel into the Owner's Windows workstation. A GitHub connector can read/write repository files; it cannot observe the effective environment of a local IABV process, the local contents of the dirty worktree, the Windows sandbox backend already provisioned on that computer, a live Codex authentication session, or the user's available plan/quota/cost. Those are local/runtime facts and must not be inferred from public source or docs.

The latest current `main` tip before this writeback is `1383bbb5a8f430379408c29882834289ceef915e`. Comparing `d2fcbd3ecf43e08d2341c3851af74bb7be6614fd` to `main` shows nine commits changing only documentation, with entry 249 and its continuity projections; no application-source edits were published in that interval. A GitHub search for remote branch `codex/m0a-safe-ui-boot` returned no branch. Therefore the modified source cited from the Owner's local branch remains `OWNER_REPORTED` here and is not available for direct remote inspection. Do not treat the main source base as a byte-for-byte substitute for that worktree.

## 2. New version-matched upstream evidence

The following evidence is specifically from public Codex source tagged `rust-v0.120.0`, matching the package version identified by the earlier Owner-supplied local inventory. This is source-contract evidence, not local runtime proof.

### A. CLI and configuration surfaces

- [`codex-rs/exec/src/cli.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec/src/cli.rs), blob `0225dc1768d4bbeb7514a104e1e1a2b1341653be`: the `exec` command declares `--sandbox`, `--cd`, `--add-dir`, `--ephemeral`, `--output-schema`, `--output-last-message`, `--json` and config overrides through `-c/--config`.
- [`codex-rs/config/src/config_toml.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/config/src/config_toml.rs), blob `f33d491800fdf4c726e3533325d0d13fd6e79ce7`: the configuration model declares `sandbox_mode`, `sandbox_workspace_write`, named `permissions` profiles and `default_permissions`.
- [`codex-rs/config/src/types.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/config/src/types.rs), blob `9d1626dbd26351894b6b17e73e02e7bd483da6a9`: declares Windows sandbox modes `elevated` and `unelevated`, the workspace-write fields (writable roots/network access) and the child-shell environment policy.
- [`codex-rs/config/src/permissions_toml.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/config/src/permissions_toml.rs), blob `fcc3e006b165d6eb4daa8dec1bba650efd04c4b9`: permission profiles can express filesystem and network policy.
- [`codex-rs/protocol/src/permissions.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/protocol/src/permissions.rs), blob `f101f8bef07ae8c7dbe032ef27e5df587883c7b7`: the policy model has file access modes `read`, `write` and `none`, plus a filesystem sandbox policy.
- [`codex-rs/core/README.md`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/README.md), blob `63d9cba53bfcf91b1cef60861fbe7174376a4afe`: describes differences between the elevated Windows backend, which supports restricted read access and more precise filesystem policy, and the unelevated restricted-token backend, which supports the legacy full-read model and a narrower set of split policies. The README explicitly says policies needing unreadable carve-outs that a selected backend cannot enforce fail closed instead of being weakened.

These declarations materially improve design specificity: the versioned contract includes more than just a writable-root flag. But the fact that a mode/configuration exists does not prove the local binary selects, provisions or successfully enforces it.

### B. The crucial distinction: Codex host access versus agent-spawned command access

A viable design may be able to use an already-authenticated Codex home **only if** the Codex host can use it while agent-spawned commands cannot read its credential/configuration contents. The parent CLI's ability to use a home and the sandboxed commands' ability to read that home are different security questions.

The candidate design should therefore require all of the following, rather than assume a dedicated home alone solves isolation:

1. Explicitly approved absolute CLI executable, with expected version and file identity; no implicit interactive-shell `PATH` resolution.
2. Explicit `CODEX_HOME` for the Codex host; no credential copying, new login/OAuth setup or credential inspection.
3. A version-supported effective Windows policy that permits writes only under a disposable candidate and denies read access to sensitive home/credential roots from agent-spawned processes. Verify the actual selected Windows backend supports that exact denial; otherwise fail closed.
4. A separate process-environment policy for agent-spawned commands. Versioned `ShellEnvironmentPolicyToml` defaults to inheriting `All`, with name-based exclusions for variables containing `KEY`, `SECRET` or `TOKEN`; those exclusions do not constitute filesystem isolation, and `CODEX_HOME` does not match those patterns. The future contract should use an explicit allowlist/minimal environment and must not depend on default pattern exclusions.
5. Explicitly deny unapproved MCP/plugin/app integrations before the turn. A sandbox policy on shell commands alone does not establish that all other host-level integration processes or tools are unavailable.
6. Distinguish parent network needed to contact the Codex service from child-command network access. The configured `workspace-write.network_access` applies to sandboxed execution; it must not be misrepresented as proof of the whole parent process has no network, nor that the service-connection path costs nothing.

### C. A source-level environment risk in the published IABV base

The published `main` source in [`bootstrap.py`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/bootstrap.py) contains `_auto_load_secrets()`, which parses `~/.iabv_secrets.ps1` and injects recognized values into the parent Python process's `os.environ`. The published `UIExecutionRunner` in [`ui_execution_runner.py`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/services/tools/ui_execution_runner.py) has launch paths that merge `os.environ` with a launch-environment overlay. This is not evidence that the local App Server adapter follows that exact path, and it is not a claim that existing code has already leaked secrets. It establishes a design hazard for any new child process: **do not reuse a general environment-merging launcher as the Codex executor and do not inherit the entire IABV environment by default**. Construct a small explicit environment and validate the downstream shell-command environment independently.

The published `main` [`infra/config.py`](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/src/iabv_v15/infra/config.py) does not declare `IABV_CODEX_HOME`, and the published `tool_adapters.py` does not contain the local-reported `CodexAppServerToolAdapter` class. This is a publication boundary, not a rebuttal of the Owner's report: those findings refer to the dirty local branch, which has not been published to `main`. The unrelated `_isolated_codex_home()` in the published external-assistant rollout-capture code merely constructs a path/directory for capture; it must not be treated as proof of an authenticated CLI home.

## 3. Impact on options A/B/C

The decision is no longer best represented as “dedicated home automatically safe” versus “ordinary home automatically unsafe.” The decisive distinction is whether the *host* can use a previously authorized session while the *spawned coding commands* are effectively denied access to credentials and disallowed external capabilities.

- **A — existing authenticated home:** technically remains a candidate *in design* if an already-supported Windows backend can enforce a path-specific read denial around sensitive home/credential roots for the agent-spawned commands, with candidate-only writes and independent network/integration policy. This is not proven locally. It still requires explicit Owner approval and proof of no-extra-spend eligibility.
- **B — already-existing dedicated authenticated home:** remains conditionally preferable when it already exists and meets no-copy/no-new-login/no-extra-spend constraints, but a separate home by itself is not enough: the sandboxed commands still must not read its credentials, and the candidate must be elsewhere with candidate-only write permission.
- **C — remain blocked:** remains the operative safe default unless A or B satisfies all gates. This is a temporary decision under incomplete evidence, not a claim the product route is impossible.

Do not ask the Owner to choose a home by name before a candidate route and the minimum non-secret evidence required for that route are specified. Conversely, do not interpret this design analysis as Owner approval of A or B.

## 4. Current evidence ledger

| Claim | Classification | Consequence |
|---|---|---|
| `main` at intake is `1383bbb5a8f430379408c29882834289ceef915e`; nine commits since `d2fcbd3...` affect documentation only | `PROVEN_BY_SOURCE` via GitHub compare | Remote records are updated; local source edits remain unpublished |
| Remote branch search returned no `codex/m0a-safe-ui-boot` branch | `PROVEN_BY_SOURCE` within the search | Dirty worktree source not directly inspectable through GitHub in this pass |
| Codex `rust-v0.120.0` defines the listed CLI/config and Windows sandbox policy structures | `PROVEN_BY_SOURCE` for that tag | A narrower policy design is plausible; no local effectiveness conclusion |
| Published IABV bootstrap loads recognized secrets into parent `os.environ` | `PROVEN_BY_SOURCE` on current remote main | New executor must use explicit environment construction |
| `UIExecutionRunner` has subprocess paths that overlay onto `os.environ` | `PROVEN_BY_SOURCE` on current remote main | Do not reuse its general launch semantics without a separate reviewed child-environment contract |
| Existing installed backend supports exact read-denial policy and is already provisioned on the Owner's Windows machine | `UNPROVEN` | Cannot approve execution from cloud docs alone |
| Existing home is authenticated, entitled and usable with no additional cost | `UNPROVEN` | Do not launch or imply zero cost |
| Local candidate-branch Codex adapter source matches published `main` | `UNPROVEN`; current source inventory indicates a mismatch | Request source evidence or future approved publication path before a direct line-by-line audit |
| Artifact diff can be generated and evaluated by the existing consumer | `UNPROVEN` | Separate consumer/verifier gate persists |

## 5. Correct next step: continue cloud analysis; no runtime yet

The prior interaction stopped too early at “wait for A/B/C.” More cloud-side analysis is available and was performed here. It yields the following refined recommendation:

1. Keep C as the current operational state, but continue investigating A/B technically without requiring the Owner to identify a local home or reveal secrets.
2. Treat path-specific read denial for sensitive home/credential roots, in the exact Windows backend supported by 0.120.0, as the first technical discriminator. If only the unelevated full-read backend is available, or the chosen policy cannot enforce `none` on the sensitive roots, A/B must not advance as a safe route.
3. Keep the executor's environment allowlist and host-versus-child security split explicit. Do not inherit IABV's secret-bearing parent environment wholesale.
4. Keep the source-publication boundary explicit: source-only conclusions about the dirty adapter must be supplied by the Owner's local audit unless that code is separately made inspectable. Do not push the dirty branch just to make it visible.
5. Next writeback should define the exact preflight evidence checklist and owner approval contract for a later separate non-mutating local preflight. That preflight would only inspect the approved executable path, non-secret config values, selected sandbox backend/read/write/network policy and candidate path; it must not read credentials or start a Codex turn. It still requires separate Owner authorization and is not authorized by this record.

## 6. First open edge and non-authorization

**First open edge:** `CODEX_EXEC_WINDOWS_HOME_READ_DENIAL_FEASIBILITY_UNVERIFIED`.

Cloud-side specification is advancing; local effectiveness remains unproven. Required evidence in a future separately authorized preflight is whether the existing Codex 0.120.0 Windows backend is already provisioned and can enforce the exact sensitive-home read denial and candidate-only writes without installation/setup/spend, plus whether the approved existing auth path has an eligible no-extra-cost mode. If it cannot be demonstrated, remain blocked.

This entry does not authorize CLI/App Server invocation, process launch, an agent turn, tests/builds, runtime UI/CDP, credential/session inspection, installation, login/OAuth setup, extra spend, local or source edits, commit, push or promotion. Preserve all dirty and untracked local work. No live IABV→Codex→IABV exchange, successful artifact ingestion, automatic model learning or later causal reuse is claimed.
