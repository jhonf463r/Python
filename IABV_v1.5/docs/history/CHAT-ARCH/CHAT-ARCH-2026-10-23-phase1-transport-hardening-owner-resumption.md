# Phase 1 MCP transport hardening — Owner resumption receipt

Date: 2026-10-23
Candidate branch: `codex/iabv-phase1-bridge-hardening-20261023`
Base: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`

## Owner decision and scope

The Owner explicitly authorized `AUTHORIZE_PHASE1_STATIC_PRESCAN_SUBSTITUTE_AND_RESUME` in the attached instruction. It authorizes bounded source changes and focused unit tests only in the existing isolated candidate. `RATIFIED_OPTION_D_NO_BOOTSTRAP` remains in force. This authorization does not establish G1, G2 or G3 and does not permit protected reads, Entra/bootstrap, production data access, full application startup, MCP startup, real transport, tunnels, deployment, spend or governance-block release.

## Pre-scan substitute

The Owner authorized a static-only substitute for this slice because the existing full pre-scan requires dynamic or persisted state. The substitute covers the directly relevant source, contracts, transport configuration and unit tests, and identifies the service-owned startup routes. `DecisionAuditTrail`, OSES, `PortableContextService`, validation cycles and `ExperimentLab` were not invoked. Dynamic/adaptive/persisted state is `NOT_INSPECTED`; no inference is made about its existence or health. `AGENTS.md` now describes both the full and authorized static-limited modes and explicitly prevents the latter from granting access or closing dynamic requirements.

## Candidate identity and source findings

Continuation preflight verified the existing isolated worktree at:

`C:\Users\faber\.codex\worktrees\iabv-phase1-transport-hardening\Python`

Branch: `codex/iabv-phase1-bridge-hardening-20261023`
HEAD/base before this slice: `2a5ac42fabbd7c6a66591d127e379432495ad3bc`
The base matched `refs/remotes/origin/main` at the time checked, and the tree was clean before this slice. The candidate was reused; no checkout was recreated.

Static source review found four relevant launch surfaces plus the application
autostart caller:

1. `infra/mcp/server.py`: the server accepted stdio, SSE and streamable HTTP, and an optional SDK security configuration disabled DNS-rebinding checks while allowing wildcard hosts/origins. The candidate now accepts stdio only and uses the SDK's default security configuration; network transports fail before server startup.
2. `scripts/run_mcp_bridge.ps1`: the script defaulted to streamable HTTP, launched the server in the background, then launched a quick Cloudflare tunnel. It now defaults to local stdio, rejects other configured transports, runs synchronously, derives the workspace from the script location unless explicitly provided, and contains no tunnel launch path.
3. `MCPBridgeService._start_locked()`: the UI service independently launched the MCP server and tunnel. It now retains the governance check, then fails closed before invoking either runner because it cannot own a client-managed stdio pipe and network authorization is absent.
4. `scripts/start_iabv.ps1`: this wrapper invoked `run_mcp_bridge.ps1` synchronously and first killed processes on its MCP port. It now does not invoke the bridge or kill by that port, and it reports that MCP/tunnel auto-start is disabled. The unrelated UI option and other existing startup behaviors were not exercised.

`AppBootstrap` also schedules `MCPBridgeService.ensure_started()` when the application UI initializes. That path reaches the guarded `_start_locked()` method and now fails before either runner. `scripts/iabv_bootstrap.ps1` calls `start_iabv.ps1`, so its subsequent wrapper path no longer starts MCP/tunnel; the bootstrap's separate installation/configuration steps and its own pre-cleanup were not executed or modified.

No Entra login or fictitious authority was implemented. The service may still persist the user's enabled preference, but its state is failed and neither runner is started. This static/source-level change does not establish runtime behavior.

## Verification record

Focused tests use fakes, temporary directories and static script inspection;
they do not start the application, MCP server, network or tunnel. The combined
focused rerun passed: `tests/test_mcp_bridge_service.py` plus
`tests/test_mcp_bridge_launcher.py`: 16 passed; the selected transport checks in
`tests/test_mcp_server.py`: 3 passed, 69 deselected (19 focused passes total). A
broader run of those three files collected 88 tests and reported 86 passed, 2 failed. Both failures
were existing world-model fixture mismatches (`test_world_model_snapshot_returns_current_without_refresh` and
`test_world_model_snapshot_refresh_triggers_request_refresh`): the fake lacks
`scan_stats`, accessed by production tool code. They are outside this transport
slice and were not repaired. No full suite was run. The final candidate SHA,
changed-file inventory and review-PR reference are reported in the completion
message and commit-pinned PR; this receipt is not a self-referential hash
manifest. The focused commands used Python 3.14.4 with `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=<candidate>/IABV_v1.5/src`, and pytest cache disabled. Current status:

```text
TESTS=FOCUSED_PASS_WITH_UNRELATED_MODULE_FAILURES
FOCUSED_TESTS=19_PASSED
BROADER_MCP_MODULE_RUN=86_PASSED; 2_UNRELATED_FIXTURE_FAILURES
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
DATA_CONTENTS_OR_SQLITE_READ=NO
DATA_PATH_NAMES_ENUMERATED_INCIDENTALLY=YES
DATA_FILES_MODIFIED=NO
PROTECTED_READS=NOT_AUTHORIZED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
PUBLIC_TUNNEL=PROHIBITED
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=SUBMIT_REVIEW_PR_WITHOUT_MERGE; THEN_REQUEST_INDEPENDENT_REVIEW
```

During exploration, one broad `rg --files` inventory command inadvertently
enumerated path names under `data/`. No file content, database or SQLite was
opened, and no data path was modified. Later searches were limited to source,
scripts, tests and named documentation. This metadata-only scope deviation is
disclosed rather than represented as no data-directory contact.

This receipt describes only the bounded candidate work and its evidence. It is
not an independent review, acceptance, merge, deployment or release of any
governance gate.
