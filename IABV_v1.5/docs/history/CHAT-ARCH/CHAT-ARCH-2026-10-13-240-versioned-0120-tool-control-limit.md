# CHAT-ARCH-2026-10-13-240 — Versioned 0.120.0 protocol has no general turn-level tools-off control

Date: 2026-10-13 (America/Bogota)
Classification: Supplementary independent read-only upstream source review, version tag `rust-v0.120.0`; local CLI identity remains unproven.
IABV canonical baseline at intake: `main @ b92115ba3711a4ef42f19084342ffb9d55a4519a`.
No local IABV source, local executable, process, test or runtime was inspected/executed in this supplementary check.

## 1. Decision

The earlier Owner report expects user-agent version `0.120.0` but says the actual CLI is selected dynamically from `PATH` and is not pinned by reviewed manifests. To refine (not replace) that result, the public OpenAI Codex repository's version tag `rust-v0.120.0` was inspected directly.

The tagged public protocol does not expose a generic all-tools-off field in `ThreadStartParams` or `TurnStartParams`. Its typed `ToolsV2` config covers `web_search` and `view_image`, not a complete model/tool registry. The source also has selective feature controls such as `include_apply_patch_tool`; this is not a universal no-tools guarantee.

Therefore, the expected version's public schema does not supply a demonstrated one-field solution to the requirement. Keep App Server blocked for the proposed text-only turn. This does **not** prove that the actual local executable is version 0.120.0 or that all possible internal/configuration paths have been exhausted.

## 2. Version-tagged source reviewed

- [ThreadStartParams.ts at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartParams.ts), blob `904487e81cf433b7edd7928fe024eabc1d02d389`. It includes parameters such as model, cwd, approval policy, approvals reviewer, sandbox, config and instructions; it declares no general `tools` or `availableTools` list.
- [TurnStartParams.ts at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/app-server-protocol/schema/typescript/v2/TurnStartParams.ts), blob `8f57a5e68bb76e4904a9bbf7d13658cc3836dce6`. It includes thread/input, cwd, approval policy, approvals reviewer, sandbox policy, model and reasoning/output settings; it declares no general tool-disable/list field.
- [ToolsV2.ts at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/app-server-protocol/schema/typescript/v2/ToolsV2.ts), blob `784991f017d63de06b54b92882b9e7d5992e52ea`. It declares only `web_search` and `view_image` settings.
- [Config.ts at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/app-server-protocol/schema/typescript/v2/Config.ts), blob `508fe84e92f82fa3f63fb19568c43c8daeac733b`, places `tools: ToolsV2 | null` within config.
- [core/src/config/mod.rs at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/config/mod.rs), blob `eac8f9e361d2e6e4ccf28a81e483b523d6c5c40d`, exposes a selective `include_apply_patch_tool` configuration value; no single general all-tools-off control was found in the reviewed typed config.
- [core/src/tools/spec.rs at rust-v0.120.0](https://github.com/openai/codex/blob/rust-v0.120.0/codex-rs/core/src/tools/spec.rs), blob `bfad3cdb3531df694c1684f70cda5dae2c1cbbc5`, includes handlers for built-in capabilities such as apply-patch, dynamic tools, image viewing, MCP and shell-related functions; tool registration is not a turn-level list supplied by the adapter.

These public files are a reproducible reference for the named tag; their absence claims are limited to the reviewed protocol/config structures, not every runtime behavior. The actual local executable and effective configuration remain `UNPROVEN`.

## 3. Cross-check with Owner-supplied IABV source audit

The Owner reports:
- expected `userAgent` version 0.120.0 at `tool_adapters.py:2453, 2523`;
- dynamic resolver choosing `codex.cmd`, `codex.ps1` or `codex` from `PATH` at `:2613`;
- no version pin in the reviewed manifests;
- normal SafeUI dispatch bypasses adapter `preflight()` (`:3147, 3414`);
- no explicit empty tool list is sent (`:3512, 4029`);
- preflight counts MCP inventory but does not fail closed on non-empty inventory (`:3135, 3174, 4017`);
- request settings ask for sandbox/restricted read-only behavior and an approval policy, while client-side rejections happen after request/event receipt (`:3794, 4086`).

These are `OWNER_REPORTED` static-source observations, not independently remeasured local facts in this supplement. The earlier reported task-ID fix remains a separate, synthetically tested edge; it does not grant runtime authority.

## 4. Evidence adjudication

| Property | State |
|---|---|
| Public `rust-v0.120.0` thread/turn typed structs have no generic tool-list/all-tools-off field | `PROVEN_BY_SOURCE` for those tagged schemas |
| Public typed `ToolsV2` has specific web-search/image settings only | `PROVEN_BY_SOURCE` for that type |
| A selective config toggle disables every effect-capable built-in/MCP/app capability | `UNPROVEN`; no such global toggle shown |
| The local executable is in fact 0.120.0 and speaks the matching contract | `UNPROVEN` (resolver is dynamic per Owner report) |
| Normal IABV dispatch verifies an effective zero-tool surface | `UNPROVEN` (Owner report says preflight is skipped and no explicit empty tools list is sent) |
| Authentication/session/quota/cost and real consumer evaluation | `UNPROVEN` |

## 5. Revised next step — route decision, not another broad search

Current blocker: `CODEX_APP_SERVER_NO_GLOBAL_TOOL_DISABLE_IN_EXPECTED_0120_CONTRACT`.

Do not repeat generic upstream-schema searches. The next bounded source-only task should decide whether a safe implementation route exists among the existing organs:

1. Review only the already identified `CodexAppServerToolAdapter` request/config construction and relevant target-version tool registry/config semantics. Determine whether existing configuration can actually remove all effect-capable tools before the turn, rather than only disabling web search or apply-patch.
2. Determine whether the normal IABV path can fail closed on unexpected MCP/app/plugin inventory and if that would be sufficient for the intended surface. Do not assume it removes built-in shell/exec or other capabilities.
3. If no global text-only mode exists, explicitly classify the App Server adapter as **not suitable for a tool-free text-only transport under the contract reviewed**. Do not invent an unrecognized protocol parameter.
4. Offer only evidence-grounded architectural choices: use an existing genuinely text-only provider for text consultation, or design a distinct guarded coding-task mode where only intended effects are possible inside an isolated candidate workspace with explicit workspace and network boundaries. Do not implement either route in this read-only tranche.
5. Keep actual CLI version/auth state as an independent open fact. Do not run the CLI to discover it, read credentials, or send a real turn.

## 6. Limits and routing

No code or configuration change, local CLI execution, App Server invocation, prompt, process, tests/builds, network, UI/CDP, credential inspection or spending occurred in this review.

Result: `APP_SERVER_STATICALLY_BLOCKED`.
Next edge: `CODEX_APP_SERVER_NO_GLOBAL_TOOL_DISABLE_IN_EXPECTED_0120_CONTRACT`.
No real turn is authorized. Preserve the dirty local worktree and distinguish remote documentation updates from local code changes.
