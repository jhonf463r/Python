# CHAT-ARCH-2026-10-09-205 — MCP STARTUP PLAN BLOCKED BY UNRESOLVED TRANSITIVE EFFECTS

## PURPOSE AND PROVENANCE

Adjudicate the user-supplied Codex result for the owner-authorized read-only static startup-impact/isolation plan in RQ204.

Repository: `jhonf463r/Python`.
Remote `main` before this write: `26c3be00173ab82f36a95291b3e3fd343f7fc86f`.
Canonical predecessor: [RQ204 — authorized read-only startup impact plan](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-204-iabv-mcp-prospective-startup-impact-plan-authorization.md).
Input: user-supplied Codex report, local timestamp 2026-10-09 09:53 America/Bogota. Source/Windows facts are actor-reported and have not been independently observed here.

## CLASSIFICATION

**ACCEPT `STATIC_PLAN_BLOCKED_BY_UNRESOLVED_TRANSITIVE_EFFECTS`. DO NOT START OR RECONNECT MCP. NEXT GATE: EXPLICIT OWNER AUTHORIZATION FOR A NARROW, READ-ONLY FOLLOW-ON AUDIT OF THE SPECIFIC EFFECTFUL DEPENDENCIES ALREADY IDENTIFIED.**

The plan found meaningful direct effects in the authorized source set, but the allowed files are insufficient to guarantee a safe isolation boundary. This is not evidence that the software is malicious or necessarily defective; it means the reviewed boundary cannot prove the absence of prohibited side effects.

## EVIDENCE ACCEPTED FROM CODEX REPORT

### Worktree identity

Codex reports the inspected worktree:
`C:\Users\faber\.codex\worktrees\universal-ui-structure\Python\IABV_v1.5`, Git root `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`, detached HEAD `e46d8304167708bed0764d3bf2be8fd6643e8944`, tree `52e51064967b8923dc7f200c10809971af9c558a`, 386 porcelain-status entries. The worktree is not equivalent to remote `main`; preserve it. The reported current SHA-256 values:
- `server.py`: `434FEC9BC7C42759424C232FBC8042450218ABFDB6696F80DD6DCFE1FA61687C` (modified versus local HEAD)
- `bootstrap.py`: `ACAAAD95C15423192F6E88ABAEC6744B84A92514B336C79C24A7A793737E1D0A`
- `world_model_service.py`: `1EC9D521B560F06165D84D320FEBE82E1671FF80068CD045A13F8B6EEA29209F`
- `docs/mcp-bridge.md`: `BCED3217183650E5205EB67299532F9F7687518A47A0CE751F5B8A1CECE372A2`

The authorized RQ13-108 and RQ13-109 records were not present in that worktree. Codex correctly did not broaden the search; EnvironmentSelfAwareness behavior therefore remains unresolved where it depends on those unavailable implementations/records.

### Direct and conditional effects found

Codex reports, at the reviewed source/line ranges:
- `server.main()` calls `AppBootstrap`, constructs the MCP server and calls `server.run()`; effective transport remains ambiguous because the source fallback is `stdio`, while bridge docs describe `streamable-http` as default. A future launch must explicitly fix the intended transport.
- `AppBootstrap.__init__()` reads `~/.iabv_secrets.ps1` into `os.environ`, loads configuration, creates directories, and configures logging/timeline/tracing before or while wiring services.
- Bootstrap creates `AppDatabase`, `ArtifactStorage` and repositories; deeper initialization/write effects are unresolved.
- `IABV_DEFER_TOOL_PROBE` and `IABV_MCP_SUBPROCESS` guard particular branches, not the entire bootstrap or all later scans.
- `EnvironmentSelfAwarenessService` is constructed with `bootstrap_scan=not _defer_scans`; bootstrap later calls `request_refresh(reason='role_router_ready', full=False)`. Whether that implementation scans, persists, or runs health checks remains unresolved.
- `WorldModelService` suppresses a synchronous initial scan when `IABV_MCP_SUBPROCESS=1`, but still starts a background thread outside test mode; bootstrap still requests a refresh. The refresh/monitor path can call `scan_now()` and persist `world_model/latest.json`.
- `_build_snapshot()` invokes EnvironmentSelfModel, window/focus collection, network connectivity probe, ToolCards refresh, and process enumeration.
- When no recent network result is cached, the source attempts TCP to `1.1.1.1:53`, TCP to `8.8.8.8:443`, then HTTP HEAD to `www.google.com`; light mode does not by itself suppress this call.
- Windows collection may read visible window titles/focus and process IDs. Background-process inspection may execute PowerShell or fall back to `tasklist`.
- Tool-card refresh reaches `ToolRegistry.refresh_card()` and `UniversalPerceptionService.scan_tool_context()`; their transitive effects remain unresolved.
- A Codex tool card may read `state_5.sqlite` and select thread metadata including paths, timestamps, CWD and titles.
- The MCP server registers tools and invokes the SDK transport, but deeper SDK/registrar effects are unresolved.
- The inspected `main()` path did not demonstrate a call to the boot-profile persistence method; do not claim such persistence occurs from that path without further evidence.

These are accepted at the level reported by Codex, not independently measured here.

## ADJUDICATION

The current environment flags do not establish a side-effect-free startup:
- `IABV_MCP_SUBPROCESS=1` disables the synchronous initial WorldModel bootstrap scan in the examined route, but does not prove that it prevents the thread, requested refresh, later scan, network probe or persistence.
- `IABV_DEFER_TOOL_PROBE=1` omits one availability-check branch, but does not suppress ToolCards refresh and all perception paths.
- A source comment or config entry is not proof of effective environment for a future process.
- A worktree separation by itself does not isolate host windows, processes, user secrets, shared profile data or network. A true OS-level boundary could change what can be observed and still requires source/effect review.

The combination of direct scan/observation/persistence routes and unresolved transitive dependencies prevents the coordinator from declaring the proposed startup sufficiently contained. No launch, reconnect, process interaction or MCP call is authorized.

## NEXT EDGE — NEW SCOPE REQUIRES EXPLICIT OWNER AUTHORIZATION

RQ204 authorized inspection of six exact files/records. The next recommended step expands scope and therefore requires a new approval; the prior approval must not be treated as blanket authorization.

Proposed bounded read-only scope:
1. Follow only import/call-site evidence from the RQ204 files to identify exact implementation paths for `EnvironmentSelfAwarenessService`; `ToolRegistry.refresh_card()`; `UniversalPerceptionService.scan_tool_context()`; `AppDatabase`; `ArtifactStorage`; relevant configuration/secrets loading; logging/tracing setup; MCP self-update registration and transport startup.
2. Inspect only the implementations of those named symbols and the directly invoked effectful helpers needed to classify network, persistence, subprocess, host observation and secret access.
3. Do not search the disk broadly, inspect arbitrary worktrees, query runtime state, read the database or secret file, execute code, run tests, compile, contact providers, invoke MCP, or modify anything.
4. If auditing a symbol requires expanding beyond those named direct dependencies, record the next path/symbol and its unresolved effect; stop and request another scope decision instead of recursively exploring the repository.

Deliver exact paths/refs, dirty-worktree identity, line-referenced call/effect graph, demonstrated/conditional/unresolved labels, possible redacted data classes, and a revised isolation/abort proposal. Codex must not write to GitHub for that task.

## FUTURE STARTUP GATE — STILL CLOSED

After any follow-on static audit, coordinator review and a separate owner decision remain mandatory. Any future start/reconnect authorization must specify the exact source/ref, client session, transport, operating-system isolation boundary, allowed/forbidden effects, persistence paths, network/provider policy, secret access policy, logging policy, preflight, abort criteria and rollback.

Even a contained new process provides prospective provenance only; it cannot retroactively prove what historical PID `16768` loaded. A future `world_model_snapshot(refresh=False, full=False)` call has its own independent disclosure permission gate because its response can contain windows/focus/network/tool state and its reviewed entrypoint lacks an explicit observation-permission gate.

## AUTHORIZATION BOUNDARY

This record accepts the read-only static plan and recommends a follow-on scope proposal. It authorizes no further audit outside RQ204's file set, no MCP call/list, process inspection/attachment/dump, startup/reconnect, refresh, provider health check, user-state observation, test, compilation, source/config/Git/database/runtime mutation, or RQ21 operation.

END OF RECORD
