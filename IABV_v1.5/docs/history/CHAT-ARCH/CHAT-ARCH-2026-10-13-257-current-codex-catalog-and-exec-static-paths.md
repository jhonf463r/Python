# CHAT-ARCH-2026-10-13-257 — Current Codex catalog and exec surfaces statically reviewed

- **Episode ID:** CHAT-ARCH-2026-10-13-257
- **Date (America/Bogota):** 2026-10-13
- **Canonical remote baseline:** main @ 0456b425ff401927ed0e1bb9cf8b3b61831442df
- **Related records:** entries 247, 249, and 252–256.
- **Mission result:** CURRENT_CODEX_CATALOG_AND_EXEC_SURFACES_SOURCE_VERIFIED
- **Operational posture:** KEEP_BLOCKED
- **First open edge:** CODEX_EXEC_TARGET_VERSION_AUTH_USAGE_AND_CONFINEMENT_UNVERIFIED

## What this source-only pass changes

Entry 256 remains historically accurate within its declared scope: the inspected `rust-v0.120.0` CLI did not establish the catalog-only interface sought in that mission. It must not be generalized to every later CLI version. Public source for the Codex `rust-v0.162.1` release exposes both a catalog debug command and a newer non-interactive `exec` interface. This is source discovery only; it does not prove that the Owner's local or IABV child process resolves to this binary, that it is installed, or that a usable account route exists.

## Evidence ledger

| Claim | Classification | Boundary |
|---|---|---|
| Upstream Codex release tag `rust-v0.162.1` was published on 2026-10-09 | PROVEN_BY_SOURCE | Release metadata for the public OpenAI/Codex repository. It is the latest version examined in this record, not proof of the local installed version. |
| The `0.162.1` CLI source exposes `codex debug models` and a `--bundled` switch | PROVEN_BY_SOURCE | `DebugSubcommand::Models` calls a catalog-rendering function. `--bundled` loads `bundled_models_response()` directly and skips refresh. |
| The default `codex debug models` path can resolve authentication, use an online-if-uncached model manager, contact a remote endpoint and persist catalog cache | PROVEN_BY_SOURCE | The source builds config and an AuthManager, calls `raw_model_catalog(OnlineIfUncached, ...)`, and the manager can fetch/cache remote models. A warm cache may mean no live request. This is not a no-side-effect/read-only guarantee. |
| No `debug models` command or authenticated catalog request was run in this review | OWNER_REPORTED | Source inspection only; no CLI/App Server/IABV process, login or model turn was started. |
| The `0.162.1` bundled catalog includes `gpt-5.6-terra` with minimum client `0.144.0`, and GPT-6 Astra with minimum `0.153.0` | PROVEN_BY_SOURCE | Bundle metadata establishes client minima only; it does not independently establish current account eligibility. |
| OpenAI's current plan documentation lists GPT-5.6 Terra in Codex for Free/Go, subject to plan limits; GPT-6 Astra is for eligible paid plans and requires CLI `0.153.0+` | PROVEN_BY_SOURCE | Official Help Center model/plan documentation. This does not establish the Owner's allowance, balance, credits or absence of additional charges. |
| Earlier inspected local CLI was reported as `0.120.0` | OWNER_REPORTED | It remains the only local inventory reported in the prior record chain. No fresh local runtime inventory was performed. |
| The `0.162.1` exec CLI offers `--ignore-rules`, `--ignore-user-config`, `--ephemeral`, `--json` and `--output-last-message` | PROVEN_BY_SOURCE | These are source-level CLI options, not an approved launch command or proof of effective containment. |
| `--ignore-rules` skips user/project rule files but does not prove that system/managed policy is absent | PROVEN_BY_SOURCE | The policy loader skips only User and Project configuration layers when that flag is set; other layers and managed requirements remain possible. |
| `--ignore-user-config` does not disable authentication lookup through `CODEX_HOME`; `--ephemeral` only promises not to persist session files | PROVEN_BY_SOURCE | CLI help and exec initialization. Neither flag proves isolation from credentials or zero filesystem/network side effects. |
| The current exec flow defaults headless approval policy to `Never`, while an explicit matching execpolicy `Allow` can request sandbox bypass | PROVEN_BY_SOURCE | `exec` must not rely on interactive approval prompts; all effects need a fail-closed, independently validated boundary. |
| IABV resolves this newer CLI, authenticates with an eligible existing identity, constrains the process on Windows, captures and verifies a diff, correlates artifacts to an authorized task, and blocks paid fallback | UNPROVEN | The new source surfaces do not implement or test IABV's governed handoff. These remain independent gates. |

## Design implications

1. **Catalog observation:** `codex debug models --bundled` is a local static catalog inspection in the reviewed source. It cannot answer live entitlement. The default command is only a *candidate* for a catalog-only remote request and may read credentials, use the network and update `models_cache.json`; do not run it under the current restrictions.
2. **Client/model candidate:** the published source supports a potential current compatibility candidate (for example, CLI `0.162.1` with GPT-5.6 Terra where the existing plan permits it). Do not install/update or assume IABV's child path uses that version. The prior `0.120.0` inventory remains below the documented model minimums noted in entries 255–256.
3. **Confinement:** `--ignore-rules` narrows policy inputs but is not a proof that all potentially bypassing rules are absent; the source still loads other policy layers. Headless `approval_policy=Never` makes an interactive prompt no safety net. An explicit `Allow` can bypass Codex's inner sandbox for matching command segments. Require proof of the effective policy and an independently enforced OS boundary before a coding turn.
4. **Artifacts:** JSONL and a last-message file are output formats, not proof of a reviewed patch. The actual IABV integration still needs exact task/authorization binding, candidate-only write scope, captured diff/receipt, independent validation, correlation and owner-gated promotion.

## Sources

- Codex release metadata (published 2026-10-09): https://github.com/openai/codex/releases/tag/rust-v0.162.1
- Catalog command and CLI dispatch: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/cli/src/main.rs
- Bundled model catalog: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/models-manager/models.json
- Model manager, remote refresh and cache behavior: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/models-manager/src/manager.rs
- Exec flags: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/exec/src/cli.rs
- Exec initialization and headless settings: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/exec/src/lib.rs
- Execpolicy loading and explicit-Allow sandbox behavior: https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/exec_policy.rs
- OpenAI Help Center — current models and minimum CLI versions: https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt
- OpenAI Help Center — Codex plan inclusion and usage limits: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- Prior bounded catalog result (entry 256): ./CHAT-ARCH-2026-10-13-256-read-only-model-catalog-path-unavailable.md

## Decision and next discriminating fact

Keep `KEEP_BLOCKED`. The new evidence corrects the breadth of the prior catalog-interface conclusion, but does not close the installed-version, authentication/home, account-allowance/no-extra-spend, Windows confinement, task correlation, diff verification or IABV consumer gates. Entry 249's Owner decision about the permitted launch/auth-home path remains pending; `ok procede` authorizes this continuing static analysis and documentary capture, not a launch, install or choice of A/B/C.

The next edge is `CODEX_EXEC_TARGET_VERSION_AUTH_USAGE_AND_CONFINEMENT_UNVERIFIED`: establish the intended executable/version and the pre-existing permitted auth/usage route; then adjudicate the exact Windows boundary and artifact contract before any separately authorized local preflight or turn. Do not send another query to Codex to rediscover the public catalog interfaces.

No Codex CLI/App Server/IABV process, authenticated request, login, model turn, credential inspection, update/install, code/config/worktree mutation, test/build, spend, promotion or learning claim occurred in this record. This writeback records public-source knowledge only; it is not proof of live account availability or operational IABV-to-Codex learning.
