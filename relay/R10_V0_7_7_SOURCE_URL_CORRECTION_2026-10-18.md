# R10 v0.7.7 source locator correction — 2026-10-18

Status: `SOURCE_LOCATOR_CORRECTED; SOURCE_BYTES_STILL_REQUIRE_ACTOR_VERIFICATION`  
Governance: `GOVERNANCE = KEEP_BLOCKED`

## Why Codex stopped

The previous v0.7.7 prompt supplied this v0.7.4 locator:

`https://github.com/jhonf463r/Python/raw/ad5c094fa3e7e4d1989079983f8f6c05f3296551/history/v0.7.3/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`

That path is wrong for the pinned source commit; Codex correctly stopped when the requested URL returned HTTP 404. Do not use that path again.

## Corrected immutable source locator

Use this URL instead:

`https://raw.githubusercontent.com/jhonf463r/Python/ad5c094fa3e7e4d1989079983f8f6c05f3296551/candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`

The immutable Git tree for commit `ad5c094fa3e7e4d1989079983f8f6c05f3296551` contains:

- Path: `candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`
- Reported Git tree size: `86,703` bytes
- Git blob SHA-1: `51e7a6802a541e6bd73f2c9a382671512c56829e`

The same Git blob SHA-1 and byte size are present under these immutable commits and paths:

- `191803340e1c78c92125b871a6a41589dc874163:candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`
- `db5c8788036b7d1c0ae5df9167bb3ec813da5f85:relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`
- `8ab3f72cc69a745e91450b159aa75d3b776fdeab:relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`

Evidence class for path, Git tree size and Git blob identity: `GITHUB_API_VERIFIED`.

The expected SHA-256 remains `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`. It is a previously reported byte-level identity, not a SHA-256 newly calculated by this coordinator during path discovery. Codex must download the corrected URL and independently recompute byte size and SHA-256 before continuing. The Git blob SHA-1 alone is not a substitute for SHA-256 verification.

## Continuation rule

This correction repairs the locator only; it does not authorize bypassing source preflight. Codex must verify the corrected v0.7.4 ZIP against exactly 86,703 bytes and the expected SHA-256, then verify v0.7.3 and v0.7.2 source ZIPs as instructed. If any source bytes fail identity checks or cannot be downloaded, stop. Do not reconstruct historical packages from extracted files or summaries.

The v0.7.6 candidate remains frozen and blocked because rows T222–T233 have 13 CSV fields despite a 12-column header. The next outer candidate is v0.7.7, based on the frozen v0.7.5 ZIP, fixing only the confirmed CSV field placement and required package metadata while retaining HI-01/HI-02/HI-03.

No tests, builds, product code, runtime, migrations, probes, dispatcher or bridge. Do not inspect the protected IABV checkout, `data/`, SQLite, M0A, Packages B–E or `relay-staging\\IABV_v1.5\\data`. PR #467 remains `OPEN / DRAFT / UNMERGED`.

`BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
