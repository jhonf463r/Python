# Coordinator gate — R10 v0.7.6 preflight blocked

Date: 2026-10-18  
Status: `BLOCKED_DOCUMENTARY_PREFLIGHT_DEFECT`  
Governance: `GOVERNANCE = KEEP_BLOCKED`

## Frozen artifact under review

- Candidate artifact commit: `8ab3f72cc69a745e91450b159aa75d3b776fdeab`.
- Relay branch: `handoff/r10-v076-review-20261018`.
- Candidate ZIP path: `relay/candidate/R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip`.
- Published handoff/index tip before this coordinator note: `0874c370befb8d92146131305597156e8ed91c5f`.
- R10 v0.7.5 source candidate remains frozen at `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`.

## Confirmed defect in published matrix text

I read the CSV from the raw commit-pinned GitHub URL:

`https://raw.githubusercontent.com/jhonf463r/Python/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv`

A CSV-aware parse of that returned text establishes:

- Header: 12 columns.
- Data rows: 124, IDs T123–T246.
- Every row remains `NOT_RUN`.
- Exactly twelve rows, T222–T233, contain 13 fields rather than the 12 fields declared by the header.
- In each of T222–T233, field 12 (`normative_basis`) is empty and the purported replacement value is in field 13.

Observed values in the extra thirteenth field:

| Row | Intended normative basis currently placed in field 13 |
|---|---|
| T222 | `§17.7` |
| T223 | `§1.3; §8.3` |
| T224 | `§17.7` |
| T225 | `§17.7` |
| T226 | `§4.1; §17.2` |
| T227 | `§7.1; §17.2` |
| T228 | `§7.1; §17.2` |
| T229 | `§8.2` |
| T230 | `§2.2; §17.2` |
| T231 | `§3.2; §17.1` |
| T232 | `§17.2` |
| T233 | `§8.3; §17.4` |

This contradicts the v0.7.6 change map and preflight report, which state that these references were placed in `normative_basis` and that the entire matrix has exactly 12 columns. Therefore HI-03 is **not closed in the published matrix**, and the asserted static preflight is incomplete or incorrect. A consumer may discard the surplus field or reject the row.

Evidence class: `GITHUB_API_VERIFIED` for the commit-pinned CSV content and tree metadata. The coordinator did not independently verify the candidate ZIP's raw bytes/hash in this environment; the reported ZIP SHA-256 remains author-reported until independently recalculated.

## Required disposition

1. Do not send candidate v0.7.6 to Claude/Sonnet as a preflight-complete candidate.
2. Do not edit, overwrite, delete or retag the frozen v0.7.6 candidate at `8ab3f72cc69a745e91450b159aa75d3b776fdeab`.
3. Route back to Codex local for a **new immutable corrective package** with a distinct outer version/identity (recommended next outer package version: v0.7.7). Keep the logical contract at v0.7.5 unless source evidence requires otherwise.
4. Correct only CSV serialization/field placement for HI-03 and the packaging metadata needed for the distinct new immutable artifact. Each of T222–T233 must have exactly 12 fields; the intended reference must occupy column 12, and no surplus column may remain.
5. Recompute and validate the manifest and new ZIP identity. Re-read the exact published CSV from GitHub and assert per-row column counts for every ID, not only the header. Verify that the ZIP member and commit-pinned extracted tree contain identical matrix bytes. Preserve v0.7.5 and the defective v0.7.6 artifact unchanged.
6. After the coordinator rechecks the published corrective artifact and preflight, send that exact immutable candidate to Claude/Sonnet for independent review.

## Retained governance and frontier

- v0.7.2 = `FAIL`.
- v0.7.3/v0.7.4 = `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- v0.7.5 = `REQUIRES_REPAIRS / NOT_ACCEPTED`, frozen.
- v0.7.6 = preflight blocked by the structural CSV defect above; preserve as historical failed candidate.
- F-07/F-10 = `OPEN`; F-12 = `PROPOSED / UNRESOLVED`; SC-10 = `PARTIAL`.
- Tests/build/runtime/product code/probes/dispatcher/bridge = `NOT_RUN`.
- `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
- PR #467 remains `OPEN / DRAFT / UNMERGED`.

This is a documentary coordinator finding, not semantic acceptance and not implementation evidence.
