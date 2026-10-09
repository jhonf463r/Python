# CHAT-ARCH-2026-10-09-202 — IABV MCP SOURCE ATTRIBUTION STILL UNPROVEN

## PURPOSE AND PROVENANCE

Adjudicate the user-supplied Codex follow-up to record 201. Objective remains first supervised IABV MCP use from Codex, not bridge installation or source implementation.

Repository: `jhonf463r/Python`.
Remote `main` observed before this writeback: `5e3bea0bc4cf5f42dae145458990402c4f391dd8`.
Relevant source baseline previously inspected by coordinator: `d059f783a24d2166f40247f374164165fba15292`.
Prior canonical episode: [CHAT-ARCH-2026-10-09-201](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-201-iabv-mcp-first-use-preflight-adjudication.md).
Input: user-supplied Codex report, local timestamp 2026-10-09 09:43 America/Bogota. Windows/process/worktree evidence is actor-reported; it is not direct coordinator observation.

## CLASSIFICATION

**ACCEPT `SERVER_SOURCE_ATTRIBUTION_UNPROVEN`. CURRENT CODEX TOOL EXPOSURE IS CONFIRMED BY THE ACTOR'S EFFECTIVE CATALOG OBSERVATION, BUT EXACT CODE-AS-LOADED IS NOT PROVEN. NO MCP INVOCATION OR RECONNECT AUTHORIZED.**

This is progress from record 201: the latest Codex observation found one live MCP process as a direct child of the current Codex process, and the same reporting session's effective tool catalog contains all five IABV tools. It does not close exact source identity or make operational observation permissible.

## CODEX-REPORTED PROCESS AND SESSION EVIDENCE

- Codex process PID `10600`, parent PID `13824`, command described as `codex.exe ... app-server ...`, start time `2026-10-09T14:16:10.3637530Z`.
- MCP process PID `16768`, parent PID `10600`, executable `C:\Python314\python.exe`, command `C:\Python314\python.exe -m iabv_v15.infra.mcp.server`, start time `2026-10-09T14:19:10.8312660Z`.
- This check observed one process with that MCP command, not the two reported in the prior check. Treat these as observations from different times; do not infer why the count differed or manipulate processes to reconcile it.
- The parent-child link directly associates PID 16768 with Codex PID 10600 at the time observed. It does not itself prove the server's complete client/session transport or the module bytes loaded.

## CONFIGURATION AND EFFECTIVE TOOL CATALOG

Codex reports that the known entry `iabv_v15_rsk01a5` in `C:\Users\faber\.codex\config.toml` declares:

- Command/arguments: `C:\Python314\python.exe -m iabv_v15.infra.mcp.server`.
- CWD and `IABV_WORKSPACE_ROOT`: `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python\IABV_v1.5`.
- `PYTHONPATH`: the `src` directory of that worktree.
- Five enabled tools: `read_repo_file`, `list_repo_directory`, `git_status_and_log`, `world_model_snapshot`, and `cognitive_frame_translate`.
- No explicit transport, URL or port in that config entry.

The actor reports that the effective tool catalog for this same Codex session exposed those five IABV tools, including `mcp__iabv_v15_rsk01a5__world_model_snapshot`. The agent viewed available tool metadata; it did not call MCP `tools/list` or invoke any IABV tool. On-disk config alone is not the basis for the exposure claim.

## WORKTREE / SOURCE EVIDENCE

Known configured worktree: `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python\IABV_v1.5`, inside repository `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`.

Codex reports:
- HEAD `e46d8304167708bed0764d3bf2be8fd6643e8944`; tree `52e51064967b8923dc7f200c10809971af9c558a`; detached HEAD.
- `git status --porcelain=v1`: 386 entries. Preserve this dirty worktree; do not reset, clean, merge or treat it as equivalent to remote main.
- `server.py` differs from its local HEAD blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`; current file blob `c3b45cc79d90af56ce7d472bf9b0684a0ee81d9c`; current-file SHA-256 `434FEC9BC7C42759424C232FBC8042450218ABFDB6696F80DD6DCFE1FA61687C`; last write `2026-10-05T23:23:52.1980972Z`.
- The 15 added lines reportedly alter the `cognitive_frame_translate` description, add `refresh=False` and `include_portable_context=False`, and include `PerceptionSnapshot` metadata.
- `bootstrap.py` and `world_model_service.py` match their local HEAD blobs; their current SHA-256 values and last-write times were recorded in the actor report.
- Remote object `d059f783a24d2166f40247f374164165fba15292` is unavailable in that local Git object database, so Codex could not calculate an exact three-file comparison against that ref.

The effective tool description visible in this Codex session contains text matching a description change in the local `server.py`. This is **corroborating compatibility evidence, not a cryptographic identity proof** of the full source bytes or of all code already imported in PID 16768. A process command line, configuration, file timestamp, current source hash, and tool description do not independently establish the module bytes loaded into memory.

## EVIDENCE / INFERENCE / UNPROVEN

**Accepted as Codex-reported observation**
- PID 16768 is a child of Codex PID 10600.
- The known configuration points to the identified alternate worktree.
- This Codex session's effective catalog exposes all five IABV tools.
- The worktree is detached and dirty; `server.py` differs from local HEAD.

**Inference**
- The effective tool description is consistent with the configured local source modification.
- The currently observed server process is associated with the current Codex process. A stronger claim about the precise active client/server transport is not established solely by that parent-child relation.

**Not proven**
- The CWD and full effective environment of PID 16768.
- Which exact source/bytecode bytes the running Python process loaded for `iabv_v15.infra.mcp.server`.
- Whether the config currently on disk is byte-for-byte the configuration that launched the session.
- An exact three-file diff against remote `d059f783...`.
- Whether the source identity can be established without in-process inspection, process attachment/dumping, or another intervention.
- Permission to disclose the snapshot of windows, focus, network, tools and other local operational state.

## ADJUDICATION AND SAFETY BOUNDARY

The first-usage route remains **blocked before invocation**. Do not call `world_model_snapshot` yet, even though the tool is exposed. Its source-level no-refresh branch had previously been reviewed at remote `d059f783...`, but that code review does not authenticate the local process's loaded bytes. In addition, the tool entrypoint has no explicit observation-permission gate; tool presence does not equal owner permission.

Do not repeat the process/config/catalog audit and do not reconnect, restart, or execute code inside the process to obtain a convenient attribution. Do not attach a debugger, make a process dump, query any IABV tool, invoke `tools/list`, run provider health checks, refresh WorldModel/EnvironmentSelfAwareness, or inspect the UI. No file/config/Git/runtime mutation was performed by the reported check.

## NEXT TASK / ACTOR

**NEXT ACTOR: CODEX — READ-ONLY FEASIBILITY AND INTERVENTION-IMPACT REVIEW FOR SOURCE-AS-LOADED ATTRIBUTION.** This is not authorization to perform the intervention.

Use the same current Windows/Codex environment. Do not repeat already completed process enumeration or tool-catalog checks. Without making an MCP call, reconnecting, restarting the service, executing code in the target process, attaching a debugger, suspending it, or creating a process dump:

1. Determine whether already-existing, known, non-invasive artifacts (for example, existing logs or startup records already identified in the prior task) can establish the exact source/module identity in PID 16768. Do not perform broad filesystem searches or enumerate arbitrary temp/worktree directories.
2. Separate which evidence could establish (a) configured path, (b) process working directory/environment, (c) Python module origin, (d) exact bytes/code actually loaded, and (e) mapping from this MCP process to the effective tool catalog. Do not promote one layer into another.
3. If the loaded-byte claim cannot be proven from already-existing passive evidence, state that plainly. List only the minimum intervention options that could close the gap, and for each describe what it actually proves, prerequisites, any possible target-process suspension/behavioral disturbance, data exposure, startup/transitive effects and separate human approval needed. Do not perform those options.
4. Review the exact already-known source paths only as needed to explain how the modified `server.py` description could corroborate—but not uniquely prove—the loaded source. Do not modify local files, Git, config, DB, scripts or runtime.

Return a compact options table, the least-invasive technically adequate option (or `NO_PASSIVE_PROOF_IDENTIFIED`), its side-effect inventory, and a final recommendation. Do not write to GitHub from Codex. No MCP invocation, endpoint request, `tools/list`, tool call, restart/reconnect, debugger/attach/dump, code execution in the server, tests, compilation, provider check, refresh or user-task execution.

## WHAT MAY FOLLOW — NOT AUTHORIZED BY THIS RECORD

Only after coordinator review of the feasibility/impact report can the Human Domain Owner decide whether to authorize a specific source-attribution intervention. If source identity is adequately established within an accepted risk boundary, the coordinator must still request a separate explicit permission for exactly one `world_model_snapshot(refresh=False, full=False)` call, naming this client/session and PID/worktree as attributed and acknowledging operational-state disclosure. No other MCP tool, refresh, full scan, provider health check, or startup/reconnect is implied. If any restart or reconnect is needed, first account for AppBootstrap wiring, EnvironmentSelfAwareness/WorldModel scans and local persistence, plus conditional provider health checks.

## KNOWLEDGE / METHOD / ROUTING DELTAS

Knowledge Delta
The effective Codex catalog is now observed to expose IABV tools and the one currently observed MCP process is parented by the current Codex process. The exact code loaded by that process remains unproven.

Negative Knowledge
A changed tool description that matches a local working-tree diff does not prove exact source bytes loaded; parent-child association does not prove full transport/session provenance; a later process count differing from a prior observation does not explain process lifecycle.

Method Delta
Keep configured path, process identity, module origin, exact loaded bytes, client effective exposure and observation permission as distinct predicates. If passive provenance cannot authenticate source-as-loaded, document the gap and request review of intervention risks before acting; do not call the target tool to bootstrap trust in itself.

Routing Delta
Codex performs feasibility/side-effect analysis only. Coordinator adjudicates and then requests distinct, narrow human authorization for any necessary intervention and later for a one-call operational snapshot. No other actor or parallel RQ21 route is required for this edge.

## PARALLEL FRONTIER — RQ21.200

RQ21.200 remains separate: consumer design accepted, not implementation-ready; owner decisions remain open for thread impersonation and DLL hash/signature TOCTOU, then the exact v5 JSON and PowerShell-stream contract. No RQ21 implementation or protected DLL action is authorized here.

## AUTHORIZATION BOUNDARY

This record accepts an attribution report and routes a read-only feasibility/impact review only. It grants no permission to access live operational state, invoke MCP, perform process introspection/attachment/dump, start/reconnect services, run providers, change the repository, or perform RQ21 operations.

END OF RECORD
