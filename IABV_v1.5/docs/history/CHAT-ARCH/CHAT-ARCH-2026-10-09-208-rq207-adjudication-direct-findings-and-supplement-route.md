# CHAT-ARCH-2026-10-09-208 — RQ207 ADJUDICATION / DIRECT FINDINGS AND SUPPLEMENT ROUTE

## PURPOSE AND PROVENANCE

Adjudicate the owner-supplied Codex result for RQ207, the read-only completion of RQ206's adapter, self-update governance, transport, and lifecycle edges.

Repository: `jhonf463r/Python`.
Remote `main` observed before this write: `54ad26327288119b1527cd0b3e39402b96ab23e1`; tree `0da3e571aad944e88759992bcf46413ec64cdad1`.
Latest commit before this write: `docs: update active route 207`, dated 2026-10-09T15:46:43Z (10:46:43 America/Bogota). The Codex report supplied by the owner is timestamped 10:51 America/Bogota (15:51 UTC). The remote tip had not moved between the two checks.
Comparison: current remote main is 1 commit ahead of `db8c210456cf9bf222886eb997c30ec35299d047` (the last commit changes README.md by 8 additions only) and 439 commits ahead / 0 behind the pinned executable baseline `5b1d89022ee4cdc63c1f88e050f086b40a42875c`. Do not infer that the full baseline-to-main delta is documentation-only.

Relevant canonical inputs:
- [RQ207](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-207-iabv-mcp-transitive-audit-adjudication-open-direct-edges.md)
- [RQ206 authorization](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-206-iabv-mcp-transitive-audit-symbiosis-metacognition-authorization.md)
- [RQ13-108](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-108-rq13-provider-health-authorization-boundary.md)
- [RQ13-109](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-109-rq13-no-safe-boundary-authorization-decision.md)
- [RQ13-111](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-111-universal-frontier-reconciliation.md)
- [RQ21.200](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-08-200-rq21-p1-consumer-contract-adjudication.md)

## CLASSIFICATION

**ACCEPT `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES` FOR RQ207. DO NOT START/RECONNECT MCP OR READ AN OPERATIONAL SNAPSHOT. ROUTE A TARGETED STATIC SUPPLEMENT WITHIN THE EXISTING RQ206/RQ207 SCOPE BEFORE SEEKING ANY DEEPER SCOPE.**

The result is useful and supports the blocked classification. It is not a complete closure of every direct edge required by RQ207: the `local_cli` adapter was omitted from the adapter table, the `site_explorer` lazy availability route lacks current-worktree hash evidence, some findings lack exact paths/line ranges/hash coverage, and several important source-level lifecycle/mutation implications were not fully adjudicated. These are not reasons to repeat the full audit; the next task is a bounded supplement.

## REMOTE MEMORY / SOURCE PROVENANCE RECONCILIATION

The latest remote `CURRENT-STATE.md`, `MEMORY-OPERATING-PROTOCOL.md`, `CONTEXT-INDEX.md`, `SYMBIOSIS-MAP.md`, `UNRESOLVED-KNOWLEDGE.md`, `ARCHIVE-REGISTRY.md`, and `README.md` were read from GitHub `main`. They route to RQ207 and specifically require the actual adapters wired to the inspected ToolRegistry path, per-handler governance, and transport/shutdown evidence. Canonical RQ201–RQ207 history exists remotely even where the Codex worktree's directed local searches found no local copy; local absence is not canonical absence.

The inspected worktree remains actor-reported as detached at `e46d8304167708bed0764d3bf2be8fd6643e8944`, tree `52e51064967b8923dc7f200c10809971af9c558a`, with 386 status entries and a modified `server.py`. Preserve it. A current local source hash is not proof of code loaded into historical PID `16768`.

For source provenance, keep Git blob SHAs separate from Codex's SHA-256 digests. At remote commit `e46d830...`, the relevant blob SHAs independently read here include:
- `bootstrap.py`: `e4befa6b683fc87aed7481f377f1332f5753e2c3`
- `tool_registry.py`: `17a0f7cc82dfb6722d4f2d7b231ac61551eb7ac2`
- `tool_adapters.py`: `f8ce508342d2da96f30b2152ffa242f08b187987`
- `site_exploration_service.py`: `9b8a596c09bb4912d09b0660000eb6265c8d6ac3`
- `world_model_service.py`: `ba0b5f5d6233330b549e09863975c77c0db735d6`
- `environment_self_awareness_service.py`: `eb276bb7cfec3bf38ee42f79484c0129449d58e7`
- `self_update_tools.py`: `c6ac8d71f8537f0bd07ceefa1b1b5f7c5ec7b45c`
- baseline `server.py` blob: `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`

These remote blob identities do not replace verification of dirty local bytes. Codex reports that bootstrap, adapter, registry, environment, router, and self-update files match its worktree HEAD; its local `server.py` SHA-256 is `434FEC9BC7C42759424C232FBC8042450218ABFDB6696F80DD6DCFE1FA61687C`, while the HEAD blob differs. The dirty `server.py` contents are actor-reported in this adjudication; do not present the remote HEAD copy as the dirty source.

## ADJUDICATED FINDINGS

### 1. Adapter coverage

The report correctly establishes conditional source paths from availability checks to HTTP, local process probes, process/window observation, cache updates, logs/marker files, and persistence. It correctly distinguishes those source paths from observed runtime effects.

Two direct-coverage gaps remain:
- Bootstrap registers `local_cli` at `bootstrap.py:631–671`, but RQ207's table omitted it. In the inspected remote `tool_adapters.py` at `e46d830...`, `LocalCliToolAdapter.is_available()` delegates to `_resolve_executable()`, which checks configured paths, environment-expanded path candidates and `shutil.which`; the direct availability method is not the subprocess task invocation. Codex must bind this finding to the exact current-worktree hash before the row is considered reconciled.
- The `site_explorer` direct path is traceable: bootstrap's `_LazyServiceRef` reaches the `site_exploration_service` property, then `SiteExplorerToolAdapter.is_available()` calls the service's `is_available()`. The remote `e46d830...` version constructs a `SiteExplorationService` holding a controller factory and its availability method checks whether `sync_playwright` is present; that method does not itself start a browser or issue a request. However, RQ207 did not provide the current worktree hash for `site_exploration_service.py`, so this source-level closure must be confirmed against the actual inspected local bytes. Do not inspect the database to discover the live card inventory; that remains an explicitly forbidden/runtime-dependent input.

### 2. Governance and mutation boundary

The Codex report's expression is materially important:
`requires_network and network is not None and not getattr(network, "connected", False)`.

When `requires_network=True` but `network_status` is absent (`None`), this expression does not block. That contradicts the method's stated contract that a network-required route requires `network_status.connected`; it is a source-level fail-open for an unknown state, conditional on the dirty `server.py` containing the same expression described by Codex. The remote HEAD copy at `e46d830...` contains the same predicate, but it is not a substitute for the dirty file's current bytes. The next report must show the exact inspected expression and SHA provenance again.

It is a positive finding that each of the three self-update handlers calls `governance_fn` before its corresponding mutation and does not proceed to mutation if the callback returns a blocking payload or throws. That closes only the explicit guard-error path, not the entire authorization contract.

Additional source-level mutation implications visible in the in-scope `self_update_tools.py` require explicit treatment:
- `write_repo_file` uses a sensitive-path denylist but compares path strings case-sensitively; Windows case variants may bypass those checks.
- `apply_text_patch` performs workspace containment and file-existence checks but does not apply the same sensitive-path denylist. It can therefore target a sensitive file located inside the workspace if governance allows the call.
- `git_commit_and_push(files=".", push=True)` is the default. If invoked against the inspected dirty workspace, it can stage the whole working tree and push unrelated changes; that workspace identity/invocation has not been established, so this is a conditional risk rather than an observed event.
- No per-call human consent is shown directly in these handlers. Whether a required permission gate is guaranteed to exist in the cached WorldModel is not established by handler code alone; retain this as an unresolved policy/enforcement edge rather than inventing a norm.

### 3. Transport, lifecycle, and cleanup

The apparent default transport difference is explained but remains entrypoint-dependent: `server.main()` falls back to `stdio`, while the UI launcher's child environment uses `setdefault('IABV_MCP_TRANSPORT', 'streamable-http')`. An inherited/previous value can override that default. This is not evidence of the transport actually used by PID `16768`.

Source checks against the `e46d830...` bootstrap blob establish material direct lifecycle concerns:
- `AppBootstrap.shutdown()` calls `self.stop()` at line 4137, while the `AppBootstrap` class has no `stop()` method in that file. Unless an outside dynamic injection is demonstrated, this shutdown path raises `AttributeError` after its earlier best-effort closures.
- `EnvironmentSelfAwarenessService.stop()` and `WorldModelService.stop()` exist and signal/join their respective observer threads, but the `AppBootstrap.run()` finalizer at lines 5357–5378 does not call those methods. It stops the MCP supervisor, terminates tracked child-process handles, and closes log handles; it does not demonstrate clean observer shutdown.
- `run()` launches a daemon `_deferred_mcp_start` thread at approximately lines 5218–5228 but does not retain/join/cancel that thread. The worker starts MCP, sleeps, and may start the tunnel afterward. If startup fails or the app exits during that window, the finalizer can clean the handles it currently knows about while the worker later creates a child. This is a conditional race in the direct source path, not proof that a child was orphaned in any run.
- The direct MCP entrypoint calls `self.mcp.run(transport=transport)` without a local `finally` proving container shutdown. Whether the SDK cleans its own transport/container remains `UNRESOLVED`; do not infer SDK failure from the absence of a wrapper-level finally.

### 4. Symbiosis and causal boundaries

RQ13-108/109 continue to block claims that ordinary bootstrap is an authorization-safe way to suppress provider health effects. The new adapter details make the dependency concrete: a refresh can make multiple HTTP calls or local observations before MCP becomes available. RQ13-111 remains independent: observation and snapshot persistence do not prove that live environment evidence causally changes capability selection or future decisions.

RQ21.200 remains an independent DLL-consumer frontier. This RQ208 record does not adjudicate its implementation or authorize its operation.

## WHAT IS CLOSED / WHAT REMAINS OPEN

Source-level conclusions supported by the report plus direct reads:
- available adapter paths may do HTTP, spawn a bounded version-check subprocess, observe local processes/windows, and write cache/marker/card/log state under their respective conditions;
- self-update handlers place the generic governance callback before their mutation statements;
- the network-required predicate described by Codex is not fail-closed for missing network status;
- the direct `AppBootstrap.shutdown()` and asynchronous startup cleanup paths have incomplete source-level lifecycle guarantees.

Still not proven:
- the exact dirty `server.py` code as loaded by any live process;
- the actual persisted ToolCard inventory or which adapters ran in a historical session;
- current secrets/environment/destinations, runtime network results, or any actual subprocess/request/persistence event;
- whether external dynamic code supplies `AppBootstrap.stop`;
- the SDK's internal transport/container cleanup behavior;
- effective per-invocation human authorization for each mutation;
- any safe isolation boundary or historical source identity for PID `16768`.

## NEXT ROUTE

**Next actor: CODEX, bounded static supplement within the existing RQ206/RQ207 source scope.** Do not re-run the entire audit. Fill only the omissions identified above, preserve the dirty/detached worktree, verify exact local hashes for `local_cli`, `site_explorer`'s service implementation and the relevant dirty `server.py` excerpt, add exact line ranges, and adjudicate the shutdown/thread/mutation findings. No tests, compile, process interaction, MCP calls, provider checks, DB/secrets reads, or mutation.

If closing SDK internals or the policy that creates/guarantees WorldModel permission gates requires inspecting a dependency beyond the authorized direct scope, stop and ask the Human Domain Owner for a separate, exact scope decision. Do not start/reconnect MCP or read an operational snapshot. Runtime evidence of live ToolCard inventory or guard execution also requires separate permission.

END OF RECORD
