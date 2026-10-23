# Codex session tool-surface inventory — metadata found; governance route unresolved

- **Date reported:** 2026-10-22, America/Bogota (as stated in the supplied report).
- **Source provenance:** `OWNER_REPORTED`; the Owner pasted the report into the coordinator conversation. The coordinator did not directly observe the Codex UI capture.
- **Source capture time:** `UNVERIFIABLE`. The report says its session context indicated 2026-10-22 and no capture hour was verifiable.
- **Task:** `M1A_V1_0_1_G1_G3_AUTHORITY_EVIDENCE_ROUTE`.
- **Mode:** metadata-only, documentary. No listed tool was invoked; no repository file was read through Codex, and no local source, runtime, test, build, process, or transport activity occurred.
- **Canonical main snapshot before this record was written:** `d083dcaf1a10dd7651cd37460c5fcb042e09f05d`.
- **Normative design:** M1A v1.0.1 remains adopted for design only; the eight implementation-prerequisite gates remain open.

## Bounded inventory reported by Codex

The supplied report says these names, descriptions, and schemas were visible in that Codex session:

| Exact visible name | Reported schema or description | Relevance to G1–G3 | Limits of evidence |
|---|---|---|---|
| `mcp__iabv_v15_rsk01a5__read_repo_file` | `{ relative_path: string }`; described as UTF-8 workspace read with path, sensitive-file and 1 MiB restrictions | G2: described file-read capability | Does not establish an issuer, authenticated principal, current approval, decision binding, revocation, receipt, enabled state, or authorization |
| `mcp__iabv_v15_rsk01a5__list_repo_directory` | `{ max_entries?: number; relative_path?: string }`; described entry-list limit of 200 | G2: described listing capability | Does not establish a scoped decision, target identity, freshness, revocation, or operation receipt |
| `mcp__iabv_v15_rsk01a5__world_model_snapshot` | `{ full?: boolean; refresh?: boolean }`; described World Model snapshot including windows, focus, network, tools and blocks | G3: observation surface described | Does not establish an authoritative versioned operation-to-target resolver, block administration, independent release authority, or current runtime state |
| `mcp__iabv_v15_rsk01a5__git_status_and_log` | `{ limit?: number }`; described read-only Git status and log | Repository metadata observation only | Does not establish read approval, authority, revocation, or block release |
| `mcp__codex_apps__github_fetch_file` | Repository, path, optional ref and optional line ranges | Remote GitHub file retrieval described | Does not authorize or attest access to the local IABV checkout or release any local operational block |

The visible server prefix `mcp__iabv_v15_rsk01a5__` is a string in the reported tool catalogue only. It does **not** authenticate a live server, its effective configuration, root/checkout, principal or authority.

## Reconciliation and remaining evidence gap

Reported verdict: `RELEVANT_TOOL_METADATA_FOUND`.

The metadata describes readers/listing, Git metadata and World Model observation. It does not expose a documented governance-owned operation for issuing or verifying a scoped read decision, proving a trusted issuer/principal, checking revocation on each operation, producing a verifiable decision/operation receipt, resolving operation-to-target authoritatively, or independently releasing the active operational block.

A prior continuity record reports a different Codex inventory in which the IABV namespace was not visible. No common session identifier or capture receipt has been provided to prove those were the same catalogue snapshot. Preserve `CODEX_SESSION_CATALOGUE_VARIANCE=UNRESOLVED`; do not silently merge the two inventories or infer global absence from either.

This report changes no authorization and closes no implementation gate. Next dependency remains the actual Owner/governance authority or named operator of the runtime authority surface who can identify the supported evidence route and accountable producers for G1–G3.

```text
TASK=M1A_V1_0_1_G1_G3_AUTHORITY_EVIDENCE_ROUTE
CODEX_SESSION_TOOL_METADATA=RELEVANT_TOOL_METADATA_FOUND; OWNER_REPORTED
CODEX_SESSION_GOVERNANCE_DECISION_ROUTE=NOT_EXPOSED_IN_REPORTED_METADATA
CODEX_SESSION_CATALOGUE_VARIANCE=UNRESOLVED
RUNTIME_TRUST_ANCHOR=UNVERIFIED
TRUSTED_CATALOGUE_AND_ACTIVE_SET_ATTESTATION=NOT_ESTABLISHED
TRUSTED_OPERATION_TARGET_RESOLVER=NOT_ESTABLISHED
SUPPORTED_RUNTIME_AUTHORITY_ROUTE=UNRESOLVED
GLOBAL_ROUTE_EXISTENCE=UNRESOLVED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
LOCAL_SOURCE_READ=NOT_RUN
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```
