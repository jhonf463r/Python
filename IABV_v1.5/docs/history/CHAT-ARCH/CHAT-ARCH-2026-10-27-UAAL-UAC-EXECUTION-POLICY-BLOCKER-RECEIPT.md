# UAAL — UAC execution-policy blocker receipt

- Date: 2026-10-27 (America/Bogota).
- Repo: `jhonf463r/Python`.
- Scope: record one blocked read-only TPM/Secure Boot probe and update automation-first behavior.
- Source of local result: Owner/Codex supplied report; the local execution-tool log was not independently retrieved in ChatGPT.

## Observed result

The attempted command route using `Start-Process -Verb RunAs` was rejected by the execution tool before PowerShell started:

- `UAC_REQUEST=BLOCKED_BY_EXECUTION_TOOL_POLICY`
- `UAC_UI=NOT_SHOWN`
- `ELEVATED_CHILD=NOT_STARTED`
- `GET_TPM=NOT_RUN`
- `TPM_WMI=NOT_RUN`
- `SECURE_BOOT=NOT_RUN`
- `TEMP_ARTIFACTS_CREATED=NO`
- `SYSTEM_OR_REPO_CHANGES=NO`
- `TPM=UNKNOWN`
- `SECURE_BOOT=UNKNOWN`

This is neither user refusal nor an operating-system UAC rejection, because the process request was blocked before the UI could appear.

## Protocol decision

Do not retry the same call, attempt a bypass, suppress UAC, or shift console/UI operation to the Owner. ChatGPT lacks a local Windows desktop execution channel; Codex's attempted route was blocked by its execution policy. Continue with independent source-level authority design and fail-closed acceptance planning. Hardware-backed-provider selection stays unresolved until a supported local evidence path exists.

Do not extend the read-only probe permission to key provisioning, TPM configuration, services, IPC/ACL changes, Entra configuration, protected reads, tunnel/runtime activation or merge.

## Preserved gates

```text
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
```

Canonical route: [CURRENT-STATE.md](./CURRENT-STATE.md).

Method: [UAAL-CFCP-001](./CHAT-ARCH-2026-10-27-UAAL-EVIDENCE-TO-CAUSAL-FRONTIER-CONTINUITY-PROTOCOL-v1.md).
