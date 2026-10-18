# R10 v0.7.8 R1.1 — automated binary identity gate (2026-10-18)

## Decision

`BINARY_GATE_HASH_MATCHED_BY_CODEX_LOCAL_PENDING_COORDINATOR_REVIEW`.

This is a Codex local byte-identity report for coordinator readback. It is not acceptance, does not authorize Claude/Sonnet review, and does not change `GOVERNANCE = KEEP_BLOCKED`, `BRIDGE_NOT_READY`, or `T123–T246 = NOT_RUN`.

## Identity and calculated evidence

- Immutable artifact commit: `23e46401e282acd4f39083fc184fced51770f2fa`.
- Relay branch at time of inspection: `handoff/r10-v078-t137-repair-20261018`; prior relay HEAD inspected: `a30da81d0fc2f71547c765b12bd58597dc286070`.
- Local path: `C:\temp\R10_v0_7_8_r11_fixup_20261018\R10_V0_7_8_DOCUMENTARY_CANDIDATE_R1_1.zip`.
- Pinned remote URL: `https://raw.githubusercontent.com/jhonf463r/Python/23e46401e282acd4f39083fc184fced51770f2fa/R10_V0_7_8_DOCUMENTARY_CANDIDATE_R1_1.zip`.
- Local bytes: **5,249,358**; SHA-256 `f4e67a512adf8afeab8d40e7cb6c134d7d53dedb6740c7f38c94151ba0920352`.
- Downloaded pinned remote bytes: **5,249,358**; SHA-256 `f4e67a512adf8afeab8d40e7cb6c134d7d53dedb6740c7f38c94151ba0920352`.
- Git blob SHA-1 computed over downloaded bytes: `7b6d636cf7522936c98f5e56500d869360567e1e`.

## Comparisons

| Check | Result |
|---|---|
| Local size equals expected 5,249,358 | MATCH |
| Local SHA-256 equals declared SHA-256 | MATCH |
| Downloaded pinned remote size equals expected 5,249,358 | MATCH |
| Downloaded pinned remote SHA-256 equals declared SHA-256 | MATCH |
| Local and remote SHA-256 equal | MATCH |
| Computed Git blob SHA-1 equals published blob SHA-1 | MATCH |

## Method and provenance

Codex checked the named local file using PowerShell `Get-Item` and `Get-FileHash -Algorithm SHA256`. Codex downloaded the exact commit-pinned raw URL using `Invoke-WebRequest -OutFile` into a newly generated unique directory under `C:\temp`, then used `Get-Item`, `Get-FileHash`, and an in-memory Git blob preimage (`blob <byte-count> NUL <file-bytes>`) hashed with SHA-1. The local source ZIP was not overwritten or modified. No `git fetch` was run.

Provenance labels:
- `CODEX_LOCAL_CALCULATED`: local and downloaded-file sizes, SHA-256 values, their equality, and Git blob SHA-1 above.
- `GITHUB_PINNED_URL`: remote bytes were retrieved from the raw URL pinned to artifact commit `23e46401e282acd4f39083fc184fced51770f2fa`.
- `GITHUB_RELAY_BRANCH_OBSERVED`: `git ls-remote` reported prior relay branch HEAD `a30da81d0fc2f71547c765b12bd58597dc286070`; a fresh clone at that HEAD supplied the index and coordinator report read.
- `PREVIOUSLY_DECLARED`: expected size, SHA-256, and Git blob SHA-1 are the identities stated in the task and existing relay records; calculations above independently match them.

Commands used for the byte check:

```powershell
Test-Path -LiteralPath $localZip
Get-Item -LiteralPath $localZip
Get-FileHash -LiteralPath $localZip -Algorithm SHA256
Invoke-WebRequest -Uri $url -OutFile $remoteFile
Get-Item -LiteralPath $remoteFile
Get-FileHash -LiteralPath $remoteFile -Algorithm SHA256
```

The Git blob SHA-1 was calculated in memory from the Git blob header and downloaded bytes. There were no errors. No product code, tests, builds, runtime, migrations, services, probes, protected checkout, `data/`, or SQLite were accessed.

## Next action

`NEXT_ACTOR = CHATGPT_COORDINATOR_READBACK`. The coordinator must review this exact evidence and make its own adjudication. Claude/Sonnet remains pending that decision.