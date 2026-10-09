# CHAT-ARCH-2026-10-09-204 — AUTHORIZED READ-ONLY MCP STARTUP IMPACT / ISOLATION PLAN

## PURPOSE AND PROVENANCE

Record the Human Domain Owner's explicit approval to prepare a bounded, read-only static analysis of a prospective controlled MCP start/client association. This authorization is for planning only. It authorizes no start, restart, reconnect, process inspection, MCP interaction, operational-state disclosure, or mutation.

Repository: `jhonf463r/Python`.
Remote `main` observed before this write: `2a00d77c8f4234115b90b068a07ed07c0526ba47`.
Prior canonical decision: [RQ203 — No passive source-as-loaded proof](https://github.com/jhonf463r/Python/blob/main/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-203-iabv-mcp-no-passive-source-proof-owner-decision.md).
Owner response: explicit “sí” to the coordinator's exact bounded read-only startup-impact/isolation-plan proposal.

## AUTHORIZATION SCOPE

Authorized: Codex may inspect only the already-known source/document paths listed below, read-only, to build a source-based direct/transitive startup-effect inventory and isolation/abort plan for a possible future controlled attribution run.

Authorized paths:
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`
- `IABV_v1.5/src/iabv_v15/bootstrap.py`
- `IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py`
- `IABV_v1.5/docs/mcp-bridge.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-108-rq13-provider-health-authorization-boundary.md`
- `IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-06-109-rq13-no-safe-boundary-authorization-decision.md`

Codex must state which exact checkout/ref and working-tree state were inspected and capture read-only identity evidence (HEAD, dirty/detached status, file hashes, known diffs). Do not reset, clean, merge, stash, switch branches, or claim a dirty worktree equals remote main. If a referenced transitive function is outside these paths and known records, list it as unresolved instead of broadening to arbitrary source discovery.

## STRICTLY NOT AUTHORIZED

- No IABV MCP tool, `tools/list`, `tools/call`, endpoint request, handshake, reconnect or client registration.
- No process enumeration or interaction for this task; no attach/debugger, memory dump, suspension, injection or code execution in a running server.
- No start/stop/restart of MCP, Codex, IABV UI, cloudflared or any provider; no launch of a “test”/shadow server.
- No WorldModel or EnvironmentSelfAwareness refresh, provider health check, external network request, user-task execution, UI observation or operational snapshot read.
- No tests, compilation, subprocess experiments, benchmarks or generated runtime artifacts.
- No edits to source, config, Git state, database, files or runtime; no GitHub write by Codex.
- No broad filesystem/worktree searches, secret/environment dumps, credential access, or inspection of unlisted source paths. Redact any incidental sensitive values.

## REQUIRED ANALYSIS

1. Trace startup entrypoints and direct calls across the authorized files; distinguish guaranteed calls from conditional calls and unresolved transitive calls.
2. Inventory potential effects by category:
   - service/container construction and provider initialization;
   - EnvironmentSelfAwareness and WorldModel scans/refreshes;
   - disk/database/local snapshot persistence;
   - provider health checks and their cache/condition prerequisites;
   - network/IPC activity;
   - UI/window/focus/network observation;
   - MCP transport/session exposure and client reconnect.
3. For each effect, cite exact source path and symbol/line range where available; label as `DEMONSTRATED`, `CONDITIONAL`, or `UNRESOLVED`. Do not infer that `IABV_MCP_SUBPROCESS=1` or deferred probes disable all effects unless the reviewed code proves it.
4. Evaluate possible isolation strategies only as proposals: e.g. offline/static-only validation, test-double construction, explicit startup-mode gates, or a separate worktree/process with denied network/provider access. Do not implement or execute them. For each, say what it would isolate, what could leak through, what would need additional source review, and whether it can still use the intended real Codex client.
5. Specify preflight conditions and abort criteria for a future plan: what evidence must be collected before launch; how to avoid touching the existing PID/worktree; how to ensure no unintended refresh/persistence/provider request; and what observable condition requires immediate abort. If the authorized source set cannot support a safe guarantee, say so; do not invent one.
6. Distinguish a prospective attribution run (new server/process) from retroactive attribution of historical PID 16768. Do not imply the former proves the latter.
7. End with a recommendation: `STATIC_PLAN_READY_FOR_OWNER_REVIEW`, `STATIC_PLAN_BLOCKED_BY_UNRESOLVED_TRANSITIVE_EFFECTS`, or `ISOLATION_NOT_ESTABLISHED`.

## REQUIRED OUTPUT

- Scope/revision and dirty-worktree identity.
- Call/effect table with evidence, conditions and unresolved dependencies.
- Isolation-option comparison, including residual risks and compatibility with the intended Codex client.
- Minimal future preflight checklist and fail-closed abort conditions.
- Final classification and explicit list of things not proven.

## NEXT GATE

Coordinator reviews the read-only plan and then returns it to the Human Domain Owner. Any future startup/reconnect requires a separate, fresh, explicit authorization naming the exact source/revision, client/session, effects permitted and forbidden, isolation envelope, rollback/abort criteria and logging. Even after that, a single `world_model_snapshot(refresh=False, full=False)` disclosure requires another separate permission naming the exact session and the operational fields that may be exposed.

This record does not authorize the future start itself.

END OF RECORD
