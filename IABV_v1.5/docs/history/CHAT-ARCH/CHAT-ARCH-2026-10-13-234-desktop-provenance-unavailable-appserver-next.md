# CHAT-ARCH-2026-10-13-234 — Desktop provenance unavailable

Date: 2026-10-13 (America/Bogota)
Classification: Owner-supplied preflight result and routing update.
Baseline: remote main at dd62f9c323c0bbdb6da1bfb58692d4de59ec5fe4.
Coverage: the Owner-pasted report only; no independent local inspection or runtime action occurred in this writeback.

## Result

`LAUNCH_PROVENANCE_UNAVAILABLE`.

The report identifies a visible Codex Desktop window titled `ChatGPT`, HWND `0x17B0900`, PID `12476`, running `ChatGPT.exe` under the packaged `OpenAI.Codex` installation path. The parent is reported as `Explorer.exe`. No `CODEX_HOME` argument appears in the command line, which does not establish the launch environment.

The inspected IABV capture source is reported to use `data/tool_teaching/external_assistants/codex_home`, including `state_5.sqlite` and `sessions`. The existing-window path does not demonstrate that PID `12476` uses that home. The Owner stopped because the only remaining contemplated read would access the process's broader environment block, which could not be restricted to one variable in the available method.

This result means **not proven**, not that the home is mismatched. Do not repeat window enumeration or broaden into invasive process inspection just to force a match. No prompt was sent and no code, data or runtime was changed in the reported check.

## Preserved local state

Owner-reported worktree: `C:\Users\faber\.codex\worktrees\m0a-safe-ui-boot\Python`; branch `codex/m0a-safe-ui-boot`; HEAD `5b1d89022ee4cdc63c1f88e050f086b40a42875c`; 56 tracked modifications and 5 untracked files. Preserve all changes, including modified `.pyc` files. These counts were not independently remeasured here and the branch is not remote `main`.

## Route decision

The current Desktop provenance path is blocked within the previously permitted evidence sources. Do not dispatch by this route.

The next useful action is a bounded, read-only source/configuration audit of the known Codex App Server seams; this is **not** permission to launch or invoke App Server. Avoid broad repository archaeology and inspect only the established SafeUI, ToolTeachService, ToolRegistry, App Server adapter/preflight and their direct configuration helpers.

Answer:
1. What does `preflight()` verify, and which requirements are skipped by the normal dispatch path?
2. Does the existing source support use of already-authorized Codex access without a billable API key or additional spending? Static source cannot prove live authentication or entitlement.
3. Can a text-only task prevent tool effects before execution, rather than rejecting tool events only after receipt?
4. For a future code-development task, can effects be bounded to a separately authorized isolated workspace, exact file scope, permitted tools and verification steps, with no push/merge?
5. Does the terminal response retain task/thread/turn correlation, reach the existing consumer, and receive an observed evaluation rather than mere persistence?
6. Which route has the smallest remaining gap, and what exact evidence would close it?

## Limits

No code or configuration edits; no tests/builds; no process start/stop/restart; no App Server invocation; no network, UI or CDP operation; no prompt dispatch; no data cleanup or Git mutation. Do not inspect session database contents or unrelated process data. No API-key request, paid API, installation or model download. Preserve RQ218/RQ223/RQ224 authorization and workspace gates.

A later text-only round-trip would prove transport only. A code-development round-trip additionally requires its own approved workspace/tool scope and bounded execution authority. M0-B and D016 causal reuse remain separate and unproven.

## Current routing

Result: `LAUNCH_PROVENANCE_UNAVAILABLE`.
First open edge: `CODEX_APP_SERVER_PREFLIGHT_AUTH_HOME_AND_TASK_POLICY_UNRESOLVED`.
Next actor/action: Codex, bounded read-only source/configuration audit of the already known App Server path.
No runtime, code change or external prompt is authorized by this record.
