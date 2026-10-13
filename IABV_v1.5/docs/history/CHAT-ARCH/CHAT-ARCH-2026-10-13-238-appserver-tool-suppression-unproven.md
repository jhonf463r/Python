# CHAT-ARCH-2026-10-13-238 — App Server pre-effect tool suppression remains unproven

Date: 2026-10-13 (America/Bogota)
Classification: Owner-supplied static source audit plus supplementary public upstream protocol-schema review; result `APP_SERVER_STATICALLY_BLOCKED`.
Canonical remote baseline at intake: `main @ 3266aa73ecebabdb92bf2b4ada82b62d8523af4b`.
No local code/runtime was inspected or executed by this documentation writeback. Upstream schema links below describe upstream `main` at lookup time, not a proven match for the local CLI build.

## 1. Owner objective and decision

The objective remains a governed `IABV → Codex → IABV` handoff, followed by a separate D016 controlled code-evolution loop. The report confirms that the task-identity repair is integrated into the normal SafeUI route according to local source. It does not establish a real exchange.

**Decision: do not authorize a real App Server turn yet.** A safe text-only consultation still requires a demonstrable server-side guarantee that no tools capable of effects are made available/executable before IABV can intervene. Prompt wording, requested sandbox fields, or rejection of approval/events after receipt do not establish that guarantee.

## 2. Worktree and evidence provenance

The Owner reports this inspected state:
- Worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`
- Branch: `codex/m0a-safe-ui-boot`
- HEAD: `5b1d89022ee4cdc63c1f88e050f086b40a42875c`
- 56 tracked files modified and 6 untracked files.
- All changes, including existing `.pyc` modifications, were preserved; no files changed in this audit.

These are Owner-reported audit observations and are not measurements of remote `main`. Preserve the whole dirty worktree. No reset, clean, restore, commit, push, branch switch, implementation, runtime or test is authorized by this record.

## 3. Source findings supplied by the Owner

| Claim | Evidence reported | Adjudication |
|---|---|---|
| Config flows `IABV_CODEX_HOME` to adapter | `infra/config.py:55`; `bootstrap.py:666` | `PROVEN_BY_SOURCE` in the supplied audit; session validity and quota remain `UNPROVEN`. |
| Child receives restricted environment with `CODEX_HOME` | `services/tools/tool_adapters.py:2844` | `PROVEN_BY_SOURCE`; no credential or entitlement proof. |
| Task ID / approved destination / prompt and digest are bound before normal dispatch | `ui/viewmodels/control_center_viewmodel.py:11749`; `services/tools/tool_teach_service.py:612, 794` | `PROVEN_BY_SOURCE` per supplied audit. Focused test result remains `OWNER_REPORTED` (32 passed in the prior report), not independently rerun here. ToolRegistry and the adapter do not independently replace those pre-dispatch guards in the reported path. |
| Normal SafeUI dispatch does not invoke adapter `preflight()` | Definition `tool_adapters.py:3147`; normal `run()` path `tool_adapters.py:3414` enters `_exchange()` | `PROVEN_BY_SOURCE` in the supplied audit. |
| Preflight reports config/MCP inventory but does not block on non-empty inventory | `tool_adapters.py:3135, 3174` | `PROVEN_BY_SOURCE` per report; not a guarantee that tool capabilities are absent. |
| Turn requests read-only/restricted sandbox and network disabled | `tool_adapters.py:3512, 4029` | Requested parameters are `PROVEN_BY_SOURCE`; effective server enforcement is `UNPROVEN`. |
| Client rejects JSON-RPC approval requests and disallowed event types | `tool_adapters.py:3794, 4086` | Client-side rejection is `PROVEN_BY_SOURCE`; it happens after the message/event is received and cannot by itself prove no server-side effect already occurred. |
| Terminal correlation checks thread/turn IDs and one final message | `tool_adapters.py:4076` | Validation logic is `PROVEN_BY_SOURCE` per report; actual correlation is `UNPROVEN` until a permitted real exchange is observed. |
| Result persistence and consumer ingestion are wired | `tool_teach_service.py:986`; `tool_memory.py:31`; `control_center_viewmodel.py:15314` | Wiring is `PROVEN_BY_SOURCE` per report; received response, actual ingestion and evaluation are `UNPROVEN`. |

The Owner's report itself says no process, external call, prompt, test, or file modification occurred during this audit.

## 4. Authentication and cost

The adapter reportedly launches the local CLI App Server over stdio with a configured `CODEX_HOME`. Its restricted child environment contains `CODEX_HOME`, and the source path described does not create or pass an API key. That does **not** prove a valid pre-existing login, which account/path actually grants access, remaining quota, or zero charges.

Authentication/session/entitlement/cost therefore remain `UNPROVEN`. Do not read credential contents or infer free access from the command name or home path.

## 5. Supplementary upstream protocol evidence (not a local-version match)

Current upstream schema/source pages observed on 2026-10-13:

- [Codex App Server v2 TurnStartParams](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/typescript/v2/TurnStartParams.ts) describes `disabledPluginIds` as replacing a thread's disabled plugin IDs and exposes `approvalPolicy` and `sandboxPolicy`; it does not expose a generic `disableAllTools` parameter in that turn-start shape.
- [Codex App Server README — Thread plugin settings](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md) states that saving the disabled-plugin selection does not yet filter plugin capabilities.
- [Codex App Server v2 config schema source](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/v2/config.rs) defines `ToolsV2` as containing a web-search tool configuration, but this declaration alone is not evidence of a comprehensive all-tool suppression contract for the local adapter.

This public upstream evidence reinforces the blocker: plugin selection, approval routing and sandbox restrictions must not be treated as a proven all-tools-off switch. However, upstream `main` is mutable and the local adapter's exact CLI version/protocol compatibility was not established by this static report. These links are supplementary direction, not proof that no implementation-specific configuration or newer/older interface exists in the local build.

## 6. Minimum blocker and next action

Current edge: `CODEX_APP_SERVER_SERVER_ENFORCED_TOOL_SUPPRESSION_UNAVAILABLE_OR_UNPROVEN`.

Next step is **version-/contract-matched, bounded read-only protocol analysis**, not a runtime experiment or immediate code change:

1. From existing source/manifests only, establish whether the adapter pins a Codex CLI version or protocol revision. Do not execute the CLI merely to discover its version.
2. Trace the exact `thread/start` and `turn/start` request shapes in the current adapter and compare them to the schema/contract it actually targets.
3. Determine whether that exact server contract has a control that removes every effect-capable tool from the model-visible and server-executable surface before a turn starts, covering built-ins, MCP servers and app/plugin capabilities as applicable.
4. Verify from existing implementation that a non-empty MCP/app/tool inventory fails closed if the intended mode requires no tools. The current reported preflight merely counts inventory and is not used by normal SafeUI dispatch.
5. If no version-matched, server-enforced no-tools control can be proven, keep App Server blocked for a text-only turn. Do not invent a flag, rely on prompt instructions, or treat `disabledPluginIds`, approval policy or sandbox mode as equivalent.
6. Only after a design contract survives this review should a separately authorized source-only implementation/test tranche be considered. No such implementation authority is granted here.

A future coding turn would require a distinct scope: isolated candidate workspace, explicit tool allowlist, pre-effect authorization and rollback/promotion gates. Do not combine it with text-only transport.

## 7. Evidence ladder and routing

- Task-identity path: reported source-integrated and previously synthetically tested; not a live round-trip.
- Auth/home/cost: `UNPROVEN`.
- Adapter preflight coverage: absent from normal dispatch according to the supplied source audit.
- Server-enforced tool suppression before effects: `UNPROVEN`; primary blocker.
- Terminal response, consumer ingestion/evaluation: `UNPROVEN`.
- M0-B and D016 causal reuse: not established.

Result: `APP_SERVER_STATICALLY_BLOCKED`.

Do not start App Server, send any prompt, inspect credentials, run tests/builds, use network/UI/CDP, or modify local code in the next read-only audit. Preserve all changes. If no proven no-tools contract exists, select a genuinely tool-free text transport for text consultation or defer the Codex bridge until the server capability is available; do not bypass this gate.
