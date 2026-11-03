# IABV local restricted stdio health-check receipt

- **Task:** `IABV_RECORD_LOCAL_STDIO_HEALTH_CHECKPOINT_DOCS_ONLY`
- **Date:** 2026-10-24
- **North Star:** `GOVERNED_IABV_CODEX_BRIDGE`
- **Document status:** historical documentary receipt; branch-only until reviewed and merged.

## Source baseline and preflight

The coordinator verified public `origin/main` at `c3bc9d8b4f727483081cf24650d4e7209687024c` before preparing this record. The candidate documentation branch was created from that exact commit.

At preflight, GitHub reported:

| PR | State | Draft | Base | Head branch | Head SHA |
|---|---|---:|---|---|---|
| [#473](https://github.com/jhonf463r/Python/pull/473) | OPEN | yes | `main` | `codex/iabv-phase1-bridge-hardening-20261023` | `f8d86c134bf5466680262ce2a9ad8c0a8ba40864` |
| [#475](https://github.com/jhonf463r/Python/pull/475) | OPEN | yes | `codex/iabv-phase1-bridge-hardening-20261023` | `codex/iabv-local-stdio-restricted-20261023` | `cb58d7e68ee6cb564753484dbb2d8fea3105f742` |

Both were unmerged at preflight. No PR branch was changed. The reported candidate worktree containing five modified tracked `__pycache__` files was not used, cleaned, or restored for this task.

## Recorded Codex session result

The following result is recorded with its supplied provenance and narrow scope:

```ini
CLIENT_MCP_CONFIGURATION=ALREADY_PRESENT
SERVER_LAUNCH_ROUTE=C:\Users\faber\.codex\worktrees\iabv-local-stdio-restricted-f8d86c\Python\IABV_v1.5\scripts\run_mcp_bridge.ps1
TRANSPORT=STDIO
SERVER_PROFILE=LOCAL_RESTRICTED
CLIENT_HANDSHAKE=CODEX_REPORTED_VERIFIED
EXPOSED_TOOLS=bridge_health
BRIDGE_HEALTH={"status":"ok"}
APPCONTAINER_BOOTSTRAP=NOT_INVOKED
PROTECTED_READS=NOT_INVOKED
NETWORK_TRANSPORTS=NOT_USED_BY_SERVER
SOURCE_CHANGES_DURING_CHECK=NONE
GITHUB_CHANGES_DURING_CHECK=NONE
```

**Evidence provenance:** `CODEX_SESSION_RESULT_SUPPLIED_BY_OWNER; NOT_INDEPENDENTLY_REPRODUCED_BY_CHATGPT`. This task did not repeat the MCP call. The prior result is evidence for the restricted diagnostic's client-visible response only. The status string does not establish that the complete IABV application is healthy.

## Interpretation and limits

The result records a Codex client invocation of the local `stdio` server with profile `local_restricted` and the single exposed tool `bridge_health`. It does not establish or change any trust authority, protected-read permission, target resolver, operation-level authorization, complete application startup, persistence, learning, production runtime, or general bridge readiness.

The checkpoint does not claim a new independent verification or a later causal reuse event. The old candidate worktree and both implementation PRs remain untouched by this documentary record.

## Governance state preserved

```text
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=MAINTAIN_NO_BOOTSTRAP_FAIL_CLOSED; REOPEN_ONLY_ON_GENUINELY_NEW_AUTHORITY_EVIDENCE_OR_EXPLICIT_OWNER_DECISION
```

No runtime, build, authorization, trust, or global governance state is promoted by this receipt.
