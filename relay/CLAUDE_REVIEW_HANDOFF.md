# HOLD — do not start Claude/Sonnet review of R10 v0.7.6 yet

Status: `BLOCKED_DOCUMENTARY_PREFLIGHT_DEFECT`. This file supersedes the earlier ready-to-paste review instructions below/previously published for operational routing. Do not send the v0.7.6 candidate to Claude as a preflight-complete candidate.

## Frozen candidate

- Candidate artifact commit: `8ab3f72cc69a745e91450b159aa75d3b776fdeab`.
- Candidate ZIP: [R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip](https://raw.githubusercontent.com/jhonf463r/Python/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip).
- Extracted matrix: [R10_V0_7_5_TEST_MATRIX_T123_T246.csv](https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv).
- Relay index (gate and candidate provenance): [RELAY_INDEX.md](https://github.com/jhonf463r/Python/blob/handoff/r10-v076-review-20261018/relay/RELAY_INDEX.md).
- Coordinator finding: [R10 v0.7.6 coordinator preflight blocker](https://github.com/jhonf463r/Python/blob/1e03c3e86851fa787bd346f1ac9e0906b332725d/relay/R10_V0_7_6_COORDINATOR_PREFLIGHT_BLOCKER_2026-10-18.md).

## Verified blocker

The published CSV has a 12-column header and 124 data rows (T123–T246), all marked `NOT_RUN`. However, rows T222–T233 each contain 13 fields. Their twelfth field (`normative_basis`) is empty, while the intended basis is in field thirteen. This contradicts the change map and preflight report. HI-03 is therefore not properly applied to the actual CSV schema.

This finding is based on the published commit-pinned GitHub CSV text. The coordinator did not independently recalculate the binary candidate ZIP hash in this environment; the ZIP size/hash remain author-reported here.

## Next actor and action

**Next actor: Codex local**, documentary author only. Create a new, distinct immutable corrective package (recommended outer package version v0.7.7) rather than altering or replacing commit `8ab3f72cc69a745e91450b159aa75d3b776fdeab`. Preserve the logical contract at v0.7.5 unless source evidence dictates otherwise. Correct the CSV field placement for T222–T233 so each row contains exactly 12 fields and each intended reference is in column 12; keep all other authorized HI-01/HI-02/HI-03 content and all historical inputs unchanged.

The corrected candidate must be re-packaged with recalculated manifest/ZIP identities, published to a new unique relay branch, and read back from GitHub. Preflight must assert the field count of every parsed row, not only the header, and verify the package ZIP payload is byte-identical to the corresponding commit-pinned extracted files.

**Coordinator gate:** ChatGPT must independently re-read the published CSV and relay metadata. Only after the row-width defect is closed may Claude/Sonnet receive a commit-pinned independent review prompt. The author cannot self-approve.

## Retained constraints

- v0.7.5 remains frozen: `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- This published v0.7.6 remains frozen as a failed preflight candidate; do not delete or overwrite it.
- F-07/F-10 `OPEN`; F-12 `PROPOSED / UNRESOLVED`; SC-10 `PARTIAL`.
- All documented test rows `NOT_RUN`; no product code, tests, builds, runtime, probes, dispatcher or bridge.
- Do not inspect the dirty IABV checkout, `data/`, SQLite, M0A, Packages B–E or `relay-staging\\IABV_v1.5\\data`.
- PR #467 stays `OPEN / DRAFT / UNMERGED`.
- `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.

This is a routing hold, not a semantic contract verdict or runtime finding.
