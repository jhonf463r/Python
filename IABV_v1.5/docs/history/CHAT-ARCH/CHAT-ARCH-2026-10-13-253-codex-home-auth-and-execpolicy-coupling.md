# CHAT-ARCH-2026-10-13-253 — Codex home binds authentication lookup and execpolicy rule sources

- **Episode ID:** `CHAT-ARCH-2026-10-13-253`
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** `main @ 6b370dfd82d95be2d6513eb5bfff1e7b69833ccc`
- **Related records:** entries 246–252.
- **Classification:** `CODEX_EXEC_HOME_AUTH_AND_POLICY_COUPLING_SOURCE_CONFIRMED_LOCAL_STORE_MODE_UNPROVEN`
- **First open edge:** `CODEX_EXEC_AUTH_HOME_POLICY_ISOLATION_ROUTE_UNRESOLVED`

## 1. Source facts that couple authentication and policy

This cloud-only pass inspected public Codex source at tag `rust-v0.120.0`.

### A. The selected home determines the authentication lookup

[`codex-rs/login/src/auth/storage.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/login/src/auth/storage.rs), blob `97e801415cabf68a01968d9fa634d16a8ddbc67f`, declares:
- File-backed auth reads/writes `CODEX_HOME/auth.json`.
- Keyring-backed auth calculates a stable key from the **canonical path** of `CODEX_HOME`: SHA-256, truncated to 16 hex characters and prefixed `cli|`.
- The keyring uses service name `Codex Auth` and that home-derived key.

Therefore changing `CODEX_HOME` to a new directory does not automatically reuse the keyring entry associated with the original home. For file storage, a new home likewise has no auth unless it already contains its own valid authorized auth file or some explicit non-copying linkage is designed. No actual Owner store mode or session was inspected. The source fact is confirmed; its local value remains `UNPROVEN`.

Public [`codex-rs/config/src/types.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/config/src/types.rs), blob `9d1626dbd26351894b6b17e73e02e7bd483da6a9`, defines `AuthCredentialsStoreMode::File`, `Keyring`, `Auto` and `Ephemeral`. This documents supported storage modes, not what the Owner's current installation actually uses.

### B. The same selected home/config layers supply execpolicy rules

[ `codex-rs/core/src/exec_policy.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/exec_policy.rs), blob `98bb815e91ab358a074a58401077fd0afb6b9ce4`, walks the applicable `ConfigLayerStack` from low to high precedence, finds each layer's config folder, collects its `rules/*.rules` files and merges their parsed rules. The default user policy path for amendments is `CODEX_HOME/rules/default.rules`; the effective source set is broader than that one file when other config layers contribute folders or policy requirements.

As recorded in entry 252, a matching explicit policy `Allow` can trigger `bypass_sandbox=true`, and the orchestrator can choose `SandboxType::None` for that command attempt.

Therefore a new home can isolate its rule directory from an old home, but may also lose access to that old home's path-keyed keyring entry. Keeping the existing home preserves its authentication lookup but also preserves that home/config layer's rule inputs. A permission profile selected with `-c` does not itself isolate the execpolicy loader.

### C. No dedicated “ignore user execpolicy rules” switch was found in the reviewed 0.120 interface

The reviewed versioned `ExecCli` argument struct in [`codex-rs/exec/src/cli.rs`](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/exec/src/cli.rs), blob `0225dc1768d4bbeb7514a104e1e1a2b1341653be`, does not declare an `--ignore-user-config` or rule-loader isolation option. The reviewed `load_exec_policy` implementation unconditionally collects rules for the layers in its stack. This is a bounded static finding; it does not assert that every possible external/managed configuration layer has been audited.

No CLI, shell command or runtime check was used to discover this.

## 2. Architecture decision implication

The home decision is not simply “dedicated home is safer.” It is a joint policy/authentication choice:

| Candidate | Auth effect | Rule-policy effect | Current decision |
|---|---|---|---|
| Use an existing authenticated home | Reuses its current auth lookup if the installation actually uses that home | Also loads applicable rules from that home's config layers; matching explicit Allow rules can bypass the inner sandbox | Candidate only if effective rule sources are compatible with confinement or an independent outer boundary is established |
| Use an already-existing dedicated authenticated home | Reuses its own already-established auth lookup, without copying credentials | May have a different rule set, which still must be checked | Conditionally attractive, but existence/authentication/rules are all `UNPROVEN` |
| Create/select a new home and expect it to reuse the old keyring entry | Fails as an assumption: the keyring lookup key changes with canonical home path | A new home could separate its rule folder if the rest of the config layers are controlled | Not available without a separately demonstrated, already-authorized auth design; do not launch login or copy credentials |
| Stay blocked | No auth/setup change | No unverified policy effects | Current safe runtime state |

A linked `auth.json` in a separately constructed home is a possible **design question only** for a future file-backed auth case, not an approved recommendation: it changes local filesystem structure and keeps the sensitive source file shared; it would need to be shown readable by the Codex host yet unreadable by agent-spawned commands under the exact Windows backend. It does not solve keyring mode, is not proven compatible with the Owner's config, and must not be created or tried in the current scope.

A second possibility is using an already-existing dedicated home with its own eligible auth. If neither option already exists under the no-new-login/no-copy/no-spend constraints, preserve the block.

## 3. Refined candidate contract for future review

Before dispatch, a future integration must:
1. Resolve and pin the approved executable identity and an explicit `CODEX_HOME`; bind both to the SafeUI authorization.
2. Obtain the final config-layer stack and all `rules/*.rules` sources in scope without disclosing private rule contents. The preflight should report provenance, policy parse status and whether any explicit `Allow` rule can match the permitted command surface. If that cannot be established, fail closed.
3. Avoid `--sandbox`/`--full-auto` when exact profile syntax must be selected, per entry 251; ensure the final config actually selected profile mode.
4. Prove that matching explicit `Allow` rules cannot cause `SandboxType::None`, or use a separately proven outer OS boundary that remains effective through the Codex bypass path.
5. Make the agent-child filesystem profile candidate-only write/minimal read and keep sensitive auth/home paths outside its readable roots. Prove the selected Windows backend can enforce this.
6. Explicitly constrain child-command environment, network and external integrations before turn start; do not inherit IABV's general secret-bearing parent environment or rely on shell prompt text.
7. Verify existing session/plan/no-extra-spend eligibility independently, without reading tokens or invoking a turn.
8. Capture terminal state, baseline and independently computed diff/artifact receipt, then feed the existing IABV consumer/verifier. Owner alone controls promotion.

## 4. Evidence ledger

| Claim | Classification | Consequence |
|---|---|---|
| File auth path is `CODEX_HOME/auth.json` | `PROVEN_BY_SOURCE` in `rust-v0.120.0` | New home does not automatically carry file-backed auth |
| Keyring entry key hashes canonical `CODEX_HOME` | `PROVEN_BY_SOURCE` in `rust-v0.120.0` | Different canonical home means different keyring lookup key |
| Execpolicy merges rules from applicable config-layer folders | `PROVEN_BY_SOURCE` in `rust-v0.120.0` | Inspect full policy-source provenance, not only one file |
| Current Owner's auth store mode/home and existing dedicated home's availability | `UNPROVEN` | Do not choose A/B or infer the local session |
| Current Owner's applicable rules have no matching Allow rule | `UNPROVEN` | No assumption of sandbox protection |
| A non-copying, no-new-login separation between authentication and rule policy already exists | `UNPROVEN` | No route may be selected on this assumption |
| Effective Windows backend contains command sandbox bypasses | `UNPROVEN` locally | Codex inner sandbox cannot be the only assumed boundary |

## 5. Correct first open edge

**First open edge:** `CODEX_EXEC_AUTH_HOME_POLICY_ISOLATION_ROUTE_UNRESOLVED`.

The next cloud-side action is to finish the static versioned contract for config-layer and authentication-store path behavior, including whether any supported `exec` invocation separates rule sources from auth storage without altering the home or credentials. Do not assume an undocumented flag or invent a working command. If the source contract offers no such switch, record that fact and route the next decision to one of two separately authorized options: non-mutating local preflight of a pre-existing home/rule set, or owner-approved design for a non-copying auth/home separation. C remains the operational default until then.

## 6. Explicit non-authorization

No process, CLI/App Server invocation, agent turn, tests/build, credential/session inspection, network access to the Owner's machine, filesystem/config mutation, home creation, symlink, installation, login/OAuth, extra spend, commit, push or promotion is authorized by this record. Preserve all owner-reported dirty/untracked files.

This cloud-side writeback is external project memory, not proof of local state, an authenticated live run, successful artifact ingestion or automatic model-weight learning.
