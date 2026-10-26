# M1F PR #531 — R-07 local-only transport reconciliation

Date: 2026-10-26  
Authority: explicit Owner authorization in the active conversation  
Disposition: bounded source reconciliation written to the existing PR candidate branch; not merged

## Decision and reason

The bounded task addressed only R-07. The selected profile is **local-only** because the candidate has no established authenticated remote-transport contract, fixed trusted public hostname, or exact allowed origin. The MCP server's existing local Host/Origin restrictions and DNS-rebinding protection were not weakened. No wildcard allowlist and no disabling of DNS-rebinding protection were introduced.

The bridge service now enforces a loopback bind and rejects any injected `tunnel_runner` with `R07_REMOTE_TUNNEL_PROFILE_NOT_IMPLEMENTED`. Its start/stop lifecycle no longer starts, waits for, or stops a Cloudflare tunnel, and the published `tunnel_url` remains `None`. An authenticated remote profile remains unimplemented; this is not a remote-access enablement.

## Branch and source provenance

- Repository: [jhonf463r/Python](https://github.com/jhonf463r/Python)
- PR: [#531 — Draft review candidate](https://github.com/jhonf463r/Python/pull/531)
- Branch: `codex/iabv-m1f-authz-candidate-review-20261025`
- Original candidate HEAD at task entry: `50cbd2b8b3d643d05726290c76ef13f85731949e`
- Reconciled candidate HEAD: `bc2baf525a70d66628809360a197f25a069aa328`
- Latest source blob read back: `e0e23f62904a2adf2e8b932c96896935fcf0cf6b`
- Latest test blob read back: `c05541fbaa3c2a9757af88a49e18ab4502fd0008`

The three candidate-branch commits are:
1. [`c8b127951f9503a1f2e56cff2f7785074d92f63d`](https://github.com/jhonf463r/Python/commit/c8b127951f9503a1f2e56cff2f7785074d92f63d) — source lifecycle moved to local-only.
2. [`45e1c36dd03e0bd3e1621e5aa8afa76985a2efd8`](https://github.com/jhonf463r/Python/commit/45e1c36dd03e0bd3e1621e5aa8afa76985a2efd8) — service tests updated for the local-only contract and negative R-07 cases.
3. [`bc2baf525a70d66628809360a197f25a069aa328`](https://github.com/jhonf463r/Python/commit/bc2baf525a70d66628809360a197f25a069aa328) — lifecycle comments reconciled with the local-only design.

A comparison from the original candidate HEAD to the reconciled HEAD returned three commits ahead, zero behind, and exactly these two changed paths:
- `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py`
- `IABV_v1.5/tests/test_mcp_bridge_service.py`

## Change inventory

### `mcp_bridge_service.py`
- Enforces `127.0.0.1`, `localhost`, `::1` or `[::1]`; rejects other bind hosts.
- Rejects caller-injected tunnel runners instead of silently enabling the unsupported remote profile.
- Removes bridge-service tunnel start/wait/stop calls and always leaves external tunnel URL unset.
- Preserves the authorization-organ preflight and World Model governance gate. These preflights check dependencies/state; they do not prove provider authenticity or full organ acceptance.
- Preserves start/stop serialization and the “OFF wins” behavior for an in-flight local server start.

### `test_mcp_bridge_service.py`
- Changes positive lifecycle expectations to a local server without a public tunnel.
- Adds negative tests for non-loopback bind hosts and explicit tunnel-runner injection.
- Rewrites race coverage to exercise local server start/stop rather than a public tunnel.
- Keeps authorization-preflight tests in place. The test suite was edited, not executed.

## Verification and limitations

- Both modified files were fetched back from GitHub after writes; their current blob IDs are listed above.
- Static readback confirms the bridge service no longer references `self._tunnel_runner` or tunnel start/stop/wait calls, and that loopback and tunnel-injection guards are present.
- **Python tests, builds and lint/static commands: NOT RUN.** No test PASS is claimed.
- No MCP server, Cloudflare tunnel, production runtime, native Windows ACL/handle path, issuer IPC, or protected read was launched or exercised.
- The separate `IABVMCPServer` Host/Origin allowlist was not changed. Remote transport is intentionally not supported by this reconciliation.
- Production `AppBootstrap` still uses `ReadAuthorizationCoordinator.unconfigured()`; G1/G2/G3 are not established. Trust-root/Owner binding, policy authority, production resolver and the remaining authority/platform prerequisites are untouched. Protected reads remain fail-closed.
- PR #531 was revalidated after the write as `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`, at the reconciled HEAD. No merge action was taken.

## Canonical disposition

```text
TASK=M1F_PR531_R07_LOCAL_ONLY_TRANSPORT_RECONCILIATION
OWNER_AUTHORIZATION=EXPLICIT
R07_TRANSPORT_PROFILE=LOCAL_ONLY_ENFORCED_IN_CANDIDATE_SERVICE
REMOTE_TRANSPORT_PROFILE=NOT_IMPLEMENTED
PUBLIC_TUNNEL=NOT_STARTED; INJECTION_REJECTED
HOST_ORIGIN_ALLOWLIST=UNCHANGED; LOCAL_VALUES_ONLY
PR531=OPEN_DRAFT_UNMERGED
CANDIDATE_HEAD=bc2baf525a70d66628809360a197f25a069aa328
CHANGED_PATHS=2; SERVICE_AND_SERVICE_TESTS_ONLY
TESTS=NOT_RUN
MCP_RUNTIME=NOT_RUN
WINDOWS_NATIVE_ACCEPTANCE=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
BRIDGE=BRIDGE_NOT_READY
ACTIONS_USAGE_BLOCK=UNKNOWN
ACTIONS_COMMUNITY_TRACK=https://github.com/orgs/community/discussions/211346
NEXT_ACTION=RUN_FOCUSED_TESTS_ONLY_IN_AN_APPROVED_ISOLATED_EXECUTOR_THEN_REVIEW_EXACT_HEAD; KEEP_GOVERNANCE_BLOCKED
```

This receipt records a source candidate change, not successful test execution, production readiness, or approval to merge.
