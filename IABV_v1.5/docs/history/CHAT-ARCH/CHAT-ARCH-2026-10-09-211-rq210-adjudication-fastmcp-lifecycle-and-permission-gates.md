# CHAT-ARCH-2026-10-09-211 — RQ210 ADJUDICATION: FASTMCP LIFECYCLE AND WORLD MODEL PERMISSION GATES

## PROVENANCE AND CANONICAL RECONCILIATION

Repository: `jhonf463r/Python`. Canonical `main` observed before adjudication: `fb048dcb7a5531df0eefdf5ef68f0604fbce5918`. Prior governing record: [RQ209](https://github.com/jhonf463r/Python/blob/fb048dcb7a5531df0eefdf5ef68f0604fbce5918/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-209-rq207-supplement-adjudication-and-next-scope-decision.md).

The Owner supplied the RQ210 Codex report in this conversation after authorizing exactly two static branches. The report identifies the target worktree as `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`, detached at `e46d8304167708bed0764d3bf2be8fd6643e8944`, tree `52e51064967b8923dc7f200c10809971af9c558a`, with 386 status entries and modified `server.py`, `task_context_assembler.py` and tracked cache files. The user-supplied report says this identity matches RQ207-S. These local-source claims are actor-reported; the coordinator did not independently read/hash the Windows worktree. No files were changed during the reported audit.

## CLASSIFICATION

- Branch A — FastMCP exact lifecycle: `STOPPED_AT_OUT_OF_SCOPE_DEPENDENCY`.
- Branch B — direct `WorldModelSnapshot.permission_gates` producer/use: `COMPLETE_WITH_FINDINGS`, subject to evidence-provenance limits below.
- Global readiness: `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`. Isolation is not established.
- RQ21.200 remains independent.

## BRANCH A — FASTMCP

The report states that the repository `pyproject.toml` and root `requirements.txt` do not pin/declare `mcp`, while bridge documentation asks users to install `mcp uvicorn` without versions. For the inspected default interpreter, local metadata reports `mcp 1.27.0`; `mcp/server/fastmcp/server.py` is reported with SHA-256 `ABD25BD81DF8A0308EEBA90CDE1B728307D852C7EFE0ABB9E0A5C6ACF5B7B9B7`, matching that distribution's `RECORD`. This authenticates only the reported local SDK copy, not every possible launcher/process.

The reported SDK source routes `FastMCP.run()` through `anyio.run(...)`; stdio uses `stdio_server()`, the low-level server has an `AsyncExitStack` for lifespan/session, and the streamable-HTTP app supplies `session_manager.run()` as its Starlette lifespan. That manager's `finally` cancels its task group and clears server instances. The report finds no explicit stop/finally handler on the inspected `FastMCP.run()`, and the IABV bridge wrapper's `stop()` only marks intent/clears references.

The exact Uvicorn source/version was not found under the inspected interpreter's site-packages, and the actual interpreter/SDK/transport of any target process is not established. Consequently Uvicorn shutdown semantics and wrapper-independent HTTP/process cleanup remain unresolved. Do not infer server shutdown from the presence of a session-manager `finally`.

Required next dependency: a separately authorized, source-based identification of the actual launch interpreter/transport and exact Uvicorn implementation/version; do not inspect a live process or open a transport under this record.

Evidence paths reported by Codex: `IABV_v1.5/src/iabv_v15/infra/mcp/server.py:3187`; `IABV_v1.5/scripts/run_mcp_bridge.ps1:7`; installed `mcp/server/fastmcp/server.py:279`; `mcp/server/stdio.py:33`; `mcp/server/streamable_http_manager.py:98`; `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py:151`. The report does not supply SHA-256 values for every file above, so the strict per-file source-integrity requirement is not fully satisfied by the delivered report.

## BRANCH B — PERMISSION-GATE PRODUCER AND ENFORCEMENT

The report states that `WorldModelSnapshot.permission_gates` defaults to an empty list and that `WorldModelService` initializes its permission map empty. During snapshot construction, `_permission_gates()` derives gates from `ToolLiveStatus`, skips `no_requerido`, looks up permission records by scope and emits `requerido` or `concedido`; generated `required_for` values use `consult_<assistant_kind>`. The described probe conditions focus on selected visible Codex/ChatGPT/Claude windows; other routes such as Ollama can resolve to `no_requerido`. This is an observation-permission model, not evidence of a universal self-update approval object.

The reported MCP governance callback reads `current_model()` and blocks only if a gate is `requerido`, not granted, and its `assistant_kind` is empty, `*`, or matches the requested route. Missing/empty/non-required/granted/nonmatching gates do not necessarily block; the function may return `None`. The callback does not check `required_for` or snapshot freshness. It is called before the self-update mutation statements, which demonstrates ordering but not that a valid human approval gate is always present or enforced.

Adjudication: accept Branch B as complete with findings **within the authorized source scope**, based on the supplied report, while recording that owner-visible per-file hashes were omitted for most cited IABV files. The material result is that human approval is conditional, not unconditional; an absent or inapplicable gate may allow the governance callback to continue. No claim is made that a live mutation occurred.

Codex-reported source anchors: `domain/models.py:607`; `services/evolution/world_model_service.py:154` and `:1166`; `infra/mcp/server.py:377`; `infra/mcp/self_update_tools.py:69`; `ui/viewmodels/control_center_viewmodel.py:11843`. Full repo-relative paths are under `IABV_v1.5/src/iabv_v15/` as described in the supplied report. Per-file SHA-256 values are not present in the report for these IABV files; treat them as actor-reported code-reading findings, not independently hash-verified evidence.

## OVERALL SYMBIOSIS / RISK CONCLUSION

1. A known local SDK version does not prove that a target process loads it; interpreter override and transport selection remain relevant.
2. Structured asynchronous/context cleanup is not by itself a guarantee that the enclosing server process stops.
3. The existence of `permission_gates`, a populated observation permission state, or callback-before-mutation is not proof of a required human authorization gate for self-update.
4. A missing/inapplicable gate can yield permissive passage in the reported predicate; this is a demonstrated source-level concern as described, not proof of runtime bypass.
5. No live process, MCP operation, snapshot, database, secret, test, build or code mutation was performed/reported.

## NEXT ROUTE AND PROHIBITIONS

Do not repeat RQ210 wholesale. The next exact issues are (a) establish the relevant launcher/interpreter/transport and exact Uvicorn implementation/version from static existing artifacts if possible, and (b) if strengthening the permission conclusion is necessary, obtain missing per-file source hashes/line ranges from the already inspected worktree without altering it. Stop at any new dependency requiring broader scope.

No MCP start/reconnect, MCP tool listing/calls, SDK runtime import/call, process interaction, probes, scans, refreshes, operational snapshot, DB/secrets reads, tests, compilation, package installation, worktree change, source mutation, commit/push by the inspected Codex task, or RQ21.200 work is authorized by RQ210.

END OF RECORD