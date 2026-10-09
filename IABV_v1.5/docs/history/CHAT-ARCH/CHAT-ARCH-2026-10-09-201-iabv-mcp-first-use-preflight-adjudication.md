# CHAT-ARCH-2026-10-09-201 — IABV MCP FIRST-USE PREFLIGHT ADJUDICATION

## PURPOSE AND PROVENANCE

Adjudicate the user-supplied Codex preflight report for the objective: begin using IABV as a supervised tool-assisted collaborator through MCP without bypassing current source, runtime, or observation-authorization boundaries.

Repository: jhonf463r/Python.
Remote main observed by coordinator before writeback: d059f783a24d2166f40247f374164165fba15292.
Pinned executable baseline: 5b1d89022ee4cdc63c1f88e050f086b40a42875c.
Input: user-supplied Codex report, local timestamp 2026-10-09 09:21 America/Bogota.
Evidence boundary: local Windows/process/config observations below are reported by Codex and were not independently observed by this coordinator. The coordinator independently fetched the cited source and canonical memory at the exact remote ref.

## CLASSIFICATION

**ACCEPT `BLOCKED_BY_STARTUP_SIDE_EFFECTS` FOR THE INSPECTED ROUTE. FIRST OPEN EDGE: ATTRIBUTION OF AN EXISTING MCP PROCESS + EFFECTIVE CLIENT EXPOSURE + OBSERVATION PERMISSION. NO MCP INVOCATION AUTHORIZED.**

The preflight correctly did not start, restart, reconnect or invoke IABV. It separates configuration on disk, the existence of OS processes, source that exists in the remote repository, and the tool surface actually available to a given client. None of those alone proves that this ChatGPT conversation or a particular Codex session is receiving tool results from the intended, attributable IABV runtime.

## COORDINATOR-VERIFIED REMOTE SOURCE FACTS

At remote ref `d059f783a24d2166f40247f374164165fba15292`, the source confirms:

- `IABVMCPServer.world_model_snapshot(refresh=False, full=False)` gets `WorldModelService`, calls `current_model()` when `refresh=False`, serializes that snapshot, and attaches `scan_stats`. It does not itself call `request_refresh()` on that branch.
- `WorldModelService.current_model()` reads/decorates the in-memory snapshot. By contrast, `request_refresh()` may schedule or perform a scan, and `scan_now()` persists the new snapshot.
- The `world_model_snapshot` tool body does not call the server's `_governance_block_for_route` helper or an explicit observation-permission gate. The fact that another route enforces governance does not establish permission enforcement on this tool.
- The bridge document describes the observation payload as operational state such as windows, focus, network, tools and blocks. Therefore even a no-refresh read is a real disclosure of local operational state, not an authorization-free generic ping.
- The bootstrap path invokes AppBootstrap and wires services. RQ13 records 108–109 establish that a normal lifecycle can schedule EnvironmentSelfAwareness/WorldModel observations, persist local observational state and conditionally reach provider health checks. `IABV_MCP_SUBPROCESS=1` and deferred tool-probe settings do not by themselves prove those EnvironmentSelfAwareness/provider-health paths are suppressed.
- `orchestrator_preview` is not a substitute for a safe read and must not be invoked to work around this block. Historical RQ13 routing explicitly identified that the preview path may reach observation/refresh and that the normal DecisionContext route is separately authorization-sensitive.

Source links:
- [MCP server at observed main](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/src/iabv_v15/infra/mcp/server.py)
- [WorldModelService at observed main](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py)
- [AppBootstrap at observed main](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/src/iabv_v15/bootstrap.py)
- [RQ13 provider-health authorization boundary](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-108-rq13-provider-health-authorization-boundary.md)
- [RQ13 no-safe-boundary decision](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-109-rq13-no-safe-boundary-authorization-decision.md)
- [RQ13 universal frontier reconciliation](https://github.com/jhonf463r/Python/blob/d059f783a24d2166f40247f374164165fba15292/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-111-universal-frontier-reconciliation.md)

## CODEX-REPORTED LOCAL OBSERVATIONS — NOT INDEPENDENTLY VERIFIED HERE

Codex reports:

- `C:\\Python` is the local Git repository; its checkout is detached at `8425f03eb45abd11951938f6e3234459c1585b55`, tree `1d46e59195d01c1cec6806f264ef75f31541e806`, with 353 tracked changes; `IABV_v1.5/src/iabv_v15/bootstrap.py` is modified.
- Local `main` and `origin/main` refs were stale relative to the observed remote main `d059f783a24d2166f40247f374164165fba15292`.
- The Codex MCP config has `iabv_v15_rsk01a5` enabled and names `world_model_snapshot`, but points to `C:\\Users\\faber\\.codex\\worktrees\\universal-ui-structure\\Python\\IABV_v1.5`, detached at `e46d830...`, with 218 tracked changes including a 15-line change in `infra/mcp/server.py`.
- Two `python.exe -m iabv_v15.infra.mcp.server` processes were observed as children of Codex PID 10600. Their CWD, actual imported source/module, source-as-loaded identity and mapping to a particular client session were not confirmed.
- No IABV UI process and no `cloudflared` process were observed in that check.
- The IABV MCP tools are not available in the effective tool surface of the conversation where the report was made, despite a config entry and live-looking child processes.
- No MCP tool was invoked, no service was started/restarted/reconnected, no endpoint request was sent, and no local files or settings were changed during the preflight.

Coordinator accepts these as actor-reported observations, not direct coordinator measurements. Dirty detached worktrees must not be reset, cleaned, merged, or treated as equivalent to current remote main to solve this problem.

## EVIDENCE / INFERENCE / UNPROVEN

**Verified at source level:** with an already initialized, attributed server, `world_model_snapshot(refresh=False, full=False)` avoids requesting a new refresh in the tool body and reads the in-memory snapshot. It has no explicit observation-permission gate in that entrypoint.

**Reported by Codex:** two candidate MCP subprocesses exist; the configured server points to an alternate dirty detached worktree; the current client tool surface lacks IABV tools.

**Inference:** calling the tool would be a bounded in-memory read only if it is in fact served by the expected already-initialized process. That would still expose local operational state and does not solve the missing permission gate or freshness question.

**Not proven:** exact source/module loaded in either process, process-to-session attribution, actual readiness of bootstrap, current effective MCP tool registration, whether the user’s relevant observation permission is granted, whether the returned snapshot is sufficiently fresh, or safe startup in the existing authorization envelope.

## FIRST OPEN EDGE

Before any tool call, establish a source/process/client chain with enough evidence to distinguish:
`Codex client session → configured server entry → exact live server PID/process command → exact worktree/source identity at process start → effective tool names visible to that same client`.

Do not claim exact in-memory source attribution solely from a server command line or a config entry. If it cannot be proven without reconnection or executing code in the server, report that limitation rather than bypassing it.

In parallel, Human Domain Owner must decide whether this particular first-use probe may disclose the relevant operational snapshot fields (windows/focus/network/tool state). No permission is inferred merely from the tool existing.

## NEXT TASK / ACTOR

**NEXT ACTOR: CODEX — READ-ONLY ATTRIBUTION OF THE EXISTING MCP PROCESS AND CLIENT SURFACE.**

Use the same Windows environment and current Codex session where the preflight was performed. Perform only local, non-mutating process/config/source provenance inspection. Do not invoke an IABV tool or MCP `tools/call`; do not perform an MCP handshake/reconnect/list-tools probe; do not start, stop, restart or reconfigure any server/client; do not touch cloudflared, provider health, WorldModel, EnvironmentSelfAwareness or the UI.

Exact questions:
1. For each of the two reported server PIDs, capture PID/parent PID, executable path, command line, start time, and the narrowest safely obtainable process working-directory/context evidence.
2. Read only the already-known Codex server configuration entry (redact secrets); report server name, command/arguments, non-secret environment selector values, worktree path and expected transport. Do not print arbitrary environment variables.
3. Inspect only the exact configured worktree and exact known paths `server.py`, `bootstrap.py`, `world_model_service.py`; report HEAD, branch/detached state, status, and the diffs/hashes/timestamps of those files compared with the remote `d059f783a24d2166f40247f374164165fba15292` source. Do not search arbitrary temp/worktree directories or change any file.
4. State explicitly whether exact source-as-loaded and mapping to the current Codex session can be proven without interacting with the server. If not, mark them unproven; do not infer them.
5. Report whether the effective tool surface for that Codex session actually exposes IABV tools. Do not call any IABV tool to test it.
6. End with one classification: `EXISTING_SERVER_ATTRIBUTED_AND_TOOLS_EXPOSED`, `CLIENT_TOOL_SURFACE_UNAVAILABLE`, `SERVER_SOURCE_ATTRIBUTION_UNPROVEN`, or `SOURCE_OR_PROCESS_EVIDENCE_UNAVAILABLE`.

Do not write to GitHub from the Codex task. Do not modify Git, local runtime state, config, scripts, database or artifacts. No MCP invocation, provider check, user-task execution, compilation or tests.

## WHAT MAY FOLLOW — NOT YET AUTHORIZED

Only after the above read-only attribution has been adjudicated should the coordinator request a separate human authorization for one call to `world_model_snapshot(refresh=False, full=False)`. That authorization must name the exact client/session and attributed server/worktree, acknowledge that the response can disclose operational details (windows/focus/network/tool state), and prohibit refresh/full scan and all other tools. If exact attribution cannot be established, do not make the call.

If a new server startup or reconnect would be required, stop and present the transitive startup effects first: AppBootstrap/service wiring, EnvironmentSelfAwareness/WorldModel refresh and local persistence, and possible provider health checks under the relevant cache conditions. The old RQ13 findings mean that neither `IABV_MCP_SUBPROCESS=1` nor “read-only target tool” alone proves startup is within scope.

## KNOWLEDGE / METHOD / ROUTING DELTAS

Knowledge Delta
The target tool's non-refresh branch is source-level bounded, but the current route is blocked earlier: no attributable exact server-to-client connection is established and no explicit observation-permission gate exists in the tool entrypoint.

Negative Knowledge
A config entry plus two MCP-like child processes does not prove tool exposure, live service readiness, exact source-as-loaded, or permission. A process command line and clean-looking remote main cannot certify a dirty detached worktree.

Method Delta
Separate four predicates: configured server, OS process, exact source loaded, and effective tool surface in the intended client. Keep observation permission as a fifth independent predicate. Never start/reconnect a server merely to turn an unavailable tool into an available one when startup has unreviewed transitive effects.

Routing Delta
Codex performs bounded existing-process/client attribution only. Coordinator adjudicates; Human Domain Owner then grants or denies the exact single-observation permission. Sonnet/Claude is not needed unless the provenance claim later requires independent challenge.

## PARALLEL FRONTIER — RQ21.200

RQ21.200 remains open and separate: same-process RQ21 consumer design is accepted but not implementation-ready pending owner adjudication of thread impersonation and DLL hash/signature TOCTOU risk, then source-derived JSON/PowerShell-stream contract freeze. No RQ21 consumer implementation or protected DLL operation is authorized by this MCP preflight.

## AUTHORIZATION BOUNDARY

This record adjudicates a bounded preflight report and routes another read-only provenance inspection. It grants no permission to invoke MCP tools, disclose operational state, start/reconnect services, execute providers, alter the repository, or perform RQ21 DLL operations.

END OF RECORD
