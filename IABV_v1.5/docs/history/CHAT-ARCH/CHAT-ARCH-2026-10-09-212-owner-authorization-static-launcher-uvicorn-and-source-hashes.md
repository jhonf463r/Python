# CHAT-ARCH-2026-10-09-212 — OWNER AUTHORIZATION: STATIC LAUNCHER / UVICORN EVIDENCE AND MISSING SOURCE HASHES

## AUTHORIZATION PROVENANCE

The Human Domain Owner explicitly replied "si" / yes to the coordinator's request for a bounded static supplement following RQ210 adjudication. The owner authorizes only inspection of already-existing local artifacts that may identify launcher interpreter/transport and Uvicorn version/source, and hashing of already-inspected IABV files whose per-file SHA-256 was omitted.

Repository: `jhonf463r/Python`.
Canonical `main` at authorization: `5c5b86df4a5e8ae368055856cf7d5ddaf5fd8f76`.
Prior records:
- [RQ210 owner authorization](https://github.com/jhonf463r/Python/blob/5c5b86df4a5e8ae368055856cf7d5ddaf5fd8f76/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-210-owner-authorization-fastmcp-lifecycle-worldmodel-permission-gates.md)
- [RQ211 adjudication](https://github.com/jhonf463r/Python/blob/5c5b86df4a5e8ae368055856cf7d5ddaf5fd8f76/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-09-211-rq210-adjudication-fastmcp-lifecycle-and-permission-gates.md)

## AUTHORIZED STATIC SUPPLEMENT

### A. Launcher / interpreter / transport / Uvicorn

Within the already-reported dirty/detached Codex worktree, inspect only existing static files that directly identify the launcher command, Python interpreter override/default, transport selection, and locally installed Uvicorn version/source relevant to the RQ210 HTTP cleanup question. May inspect existing project scripts, config and dependency metadata already present in that worktree, plus already-present package source/metadata on disk if directly accessible without running code.

Do not enumerate or inspect live processes, infer actual runtime process state, execute the launcher, import packages, query runtime environments, invoke SDK methods, open a transport, run package managers, install or fetch dependencies, or perform network probes. If existing static artifacts do not establish which interpreter/transport is used for the target process, state that they do not establish it. If exact Uvicorn version/source is absent locally, stop that subtask as blocked.

### B. Missing source hashes for RQ210

Using only already-inspected files present locally in the same worktree, obtain SHA-256 for the IABV source paths cited in the owner-supplied RQ210 report whose hashes were omitted, especially:
- `IABV_v1.5/src/iabv_v15/domain/models.py`
- `IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py`
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`
- `IABV_v1.5/src/iabv_v15/infra/mcp/self_update_tools.py`
- `IABV_v1.5/src/iabv_v15/ui/viewmodels/control_center_viewmodel.py`
- plus any directly cited IABV source file for which RQ210 did not report a SHA-256.

For every file, report current worktree-relative path, line anchor(s), SHA-256, and whether the file is clean/modified relative to the reported worktree HEAD as evidenced by existing status/diff artifacts. Do not hash a remote-main replacement and present it as the local source. If local bytes cannot be reached without a prohibited action, mark the hash unavailable.

The aim is source-provenance completeness, not re-auditing RQ210 or changing its findings. Any change in the source bytes since RQ210 must be called out explicitly.

## PRECONDITION — PRESERVE TARGET WORKTREE

RQ210 reported:
- Worktree: `C:\Users\faber\.codex\worktrees\universal-ui-structure\Python`
- HEAD: `e46d8304167708bed0764d3bf2be8fd6643e8944`
- Tree: `52e51064967b8923dc7f200c10809971af9c558a`
- Detached state, 386 status entries.
- Modified `server.py`, `task_context_assembler.py`, and tracked cache files (as reported).

These are actor-reported identifiers. Reconfirm current worktree identity and status without changing anything. If the worktree identity/status materially differs, stop and report the discrepancy. Never clean, checkout, reset, stash, rebase, or switch worktrees to obtain evidence.

## DELIVERABLE

Return a short, source-anchored supplement with:
1. Confirmed current worktree path, HEAD, tree, branch/detached state and dirty summary.
2. What existing static artifacts say about launcher interpreter defaults/overrides and transport selection, clearly labelled as configuration evidence rather than runtime process attribution.
3. Exact Uvicorn version/path/hash and relevant line anchors only if already installed/source is found locally; otherwise an explicit blocked result.
4. A per-file hash table for each relevant RQ210 IABV file, including line anchors and clean/modified status where locally evidenced.
5. Explicit distinction between demonstrated, conditional and unresolved facts, and any artifact unavailable locally.

Do not modify the worktree and do not write the report there. The coordinator will adjudicate the supplement.

## STRICT PROHIBITIONS

No MCP startup/restart/reconnect, MCP tool listing/calls, runtime/process/window inspection, runtime SDK/package import/calls, transport opening, health checks or network probes, browser/adapter invocation, scans/refresh, environment-value dumps, DB/secrets/operational snapshot reads, tests, builds, compilation, project execution, package installation, package-manager commands, downloads, worktree cleanup/checkout/reset/stash/rebase, file edits, source mutation, commits or pushes by Codex. No broad search or unrelated governance recursion. RQ21.200 remains separate.

This is only a static evidence supplement. It does not authorize runtime attribution, startup, MCP use, snapshot disclosure, code modification, or a readiness/isolation conclusion. Overall classification remains `TRANSITIVE_AUDIT_BLOCKED_BY_FURTHER_DEPENDENCIES`.

END OF RECORD