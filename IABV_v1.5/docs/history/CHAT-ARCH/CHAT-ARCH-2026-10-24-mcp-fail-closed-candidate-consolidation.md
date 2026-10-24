# IABV MCP candidate consolidation and fail-closed profile receipt

**Task:** `IABV_CONSOLIDATE_MCP_CANDIDATES_AND_ENFORCE_FAIL_CLOSED_PROFILE`  
**North Star:** `GOVERNED_IABV_CODEX_BRIDGE`  
**Evidence class:** candidate source and focused unit-test results from the isolated worktree; upstream PR state from GitHub metadata.  
**Owner decision:** `AUTHORIZE_BOUNDED_FAIL_CLOSED_MCP_ENFORCEMENT_AND_CANDIDATE_CONSOLIDATION`.

## Identity and source history

- Verified `main`: `c3bc9d8b4f727483081cf24650d4e7209687024c`.
- PR #473: `OPEN / DRAFT / UNMERGED`; head `f8d86c134bf5466680262ce2a9ad8c0a8ba40864`, based on `main` at `2a5ac42fabbd7c6a66591d127e379432495ad3bc`.
- PR #475: `OPEN / DRAFT / UNMERGED`; head `4a7c611990d56bb02eec926873dd0d4cd4a07d72`, based on the #473 head.
- PR #476: `OPEN / DRAFT / UNMERGED`; head `235b3776c1504c76b7bc56e6f5d5eb5b99d1f04e`, based on verified `main`.
- Worktree: `C:\temp\IABV_MCP_FAIL_CLOSED_CONSOLIDATION_20261024`, branch `codex/iabv-mcp-governed-restricted-consolidation-20261024`, created from verified `main`; sparse checkout excludes `data/`.
- Local merge commits preserving the three candidate histories: #475 merge `29b86c16439d6195f8f98737a185a0f38c09b9db`; #476 merge `a386d8ebedbec6bc9fbafdab8b46883aa09d8539`.
- Remote refs for `main`, #473, #475 and #476 were re-read before the local changes. The new consolidation branch did not exist remotely at the check. None of the existing PR refs were changed.

## Continuity conflict resolution

The #473/#475 merge conflicted in `AGENTS.md`, `CONTEXT-INDEX.md`, `CURRENT-STATE.md` and `README.md`. Three-way resolution retained the verified `main` versions of those four routing/front-door files and preserved the candidate receipts as history. This avoids promoting stale candidate-only “latest” routing into the canonical path. The #476 merge applied without conflict and its receipt and continuity pointers remain present.

The exact `main` routing value is retained:

```text
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

The local `CURRENT-STATE.md` includes only the supplementary checkpoint already supplied by #476 plus this candidate receipt pointer; neither changes that routing value or any gate. `main` itself was not changed.

## Fail-closed MCP profile change

The only MCP profile supported by the public constructor, `create_server()` and `main()` is now `local_restricted`. It is also the constructor and `create_server()` default. The restricted profile registers only `bridge_health`; it does not need `AppBootstrap` or container services. `IABV_MCP_PROFILE=full`, `create_server(profile="full")` and direct construction with `profile="full"` are rejected before bootstrap or public tool registration. `IABVMCPServer.run()` rechecks its profile before any MCP runner call, including a full-profile instance assembled outside the public constructor. The existing transport guard continues to reject `sse` and `streamable-http` before bootstrap.

Legacy full-profile handler behavior remains covered by an explicitly test-only registry fixture that bypasses the public constructor and invokes handlers directly with synthetic dependencies. That fixture is not a server execution path. Tests of production profile selection use the public constructor, factory and `main()`.

The launcher already fixes `IABV_MCP_PROFILE=local_restricted` and `IABV_MCP_TRANSPORT=stdio`; its static tests were included. `docs/mcp-bridge.md` now describes the executable tool surface accurately. Cloudflare, adapter, AppBootstrap and MCPBridgeService restrictions inherited from #473/#475 were preserved and not relaxed.

## Focused verification performed

Environment observed in the isolated candidate:

- Interpreter: `C:\Python314\python.exe`, Python `3.13.2`.
- `pytest`: `9.0.3`.
- `from mcp.server.fastmcp import FastMCP`: import succeeded.
- `PYTHONDONTWRITEBYTECODE=1`; `PYTHONPATH` pointed to this candidate's `IABV_v1.5/src`; pytest cache disabled.

The executed selection covered public constructor/factory/main defaults and rejection, a directly assembled full-profile object's refusal before `mcp.run`, exact restricted tool registration, network-transport rejection, legacy handler registration in the test-only fixture, and the static launcher tests.

Exact PowerShell invocation:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH=(Join-Path (Resolve-Path 'IABV_v1.5').Path 'src'); & 'C:\Python314\python.exe' -m pytest -p no:cacheprovider -c 'IABV_v1.5\pyproject.toml' 'IABV_v1.5\tests\test_mcp_server.py::test_server_registers_core_tools' 'IABV_v1.5\tests\test_mcp_server.py::test_local_restricted_profile_registers_only_static_health_tool' 'IABV_v1.5\tests\test_mcp_server.py::test_local_restricted_profile_rejects_injected_mcp_registry' 'IABV_v1.5\tests\test_mcp_server.py::test_local_restricted_profile_run_skips_dynamic_write_tools' 'IABV_v1.5\tests\test_mcp_server.py::test_server_constructor_defaults_to_local_restricted' 'IABV_v1.5\tests\test_mcp_server.py::test_server_constructor_rejects_full_before_tool_registration' 'IABV_v1.5\tests\test_mcp_server.py::test_create_server_defaults_to_local_restricted_without_bootstrap' 'IABV_v1.5\tests\test_mcp_server.py::test_create_server_rejects_full_before_bootstrap_or_constructor' 'IABV_v1.5\tests\test_mcp_server.py::test_direct_full_profile_instance_cannot_run_mcp' 'IABV_v1.5\tests\test_mcp_server.py::test_main_defaults_to_local_restricted_without_appbootstrap' 'IABV_v1.5\tests\test_mcp_server.py::test_main_rejects_network_transport_before_appbootstrap' 'IABV_v1.5\tests\test_mcp_server.py::test_main_rejects_explicit_full_before_bootstrap_or_server_construction' 'IABV_v1.5\tests\test_mcp_server.py::test_server_rejects_unknown_transport' 'IABV_v1.5\tests\test_mcp_server.py::test_server_rejects_network_transports_before_run' 'IABV_v1.5\tests\test_mcp_server.py::test_server_rejects_full_profile' 'IABV_v1.5\tests\test_mcp_bridge_launcher.py' -q
```

```text
19 passed in 1.46s
FOCUSED_PYTEST_EXIT=0
git diff --check: exit 0
```

The `test_mcp_local_restricted_stdio.py` subprocess test was not run. No MCP server, application, AppBootstrap, Cloudflare, network transport, protected reader, SQLite, build, deployment or real transport was started or accessed. These tests establish only the selected unit contracts; they do not prove a real client handshake, full IABV health or downstream ingestion.

## Governance and limits

```text
RATIFIED_OPTION_D_NO_BOOTSTRAP=REMAINS_IN_FORCE
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
PUBLIC_TUNNEL=PROHIBITED
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_PERFORMED
```

The #476 `bridge_health` result remains `CODEX_SESSION_RESULT_SUPPLIED_BY_OWNER; NOT_INDEPENDENTLY_REPRODUCED_BY_CHATGPT`; the unit tests in this task did not repeat it. Historical World Model test failures remain `UNRESOLVED` because no base-versus-candidate comparison was run here. This receipt and branch are candidate-only pending Draft PR review; they do not change `main`, establish trust, authorize protected reads, or close implementation prerequisites.
