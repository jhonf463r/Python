# Claude/Sonnet — independent adversarial review handoff: R10 v0.7.7

## Routing gate

**Destination IA:** Claude/Sonnet, separate reviewer conversation.  
**Role:** independent adversarial documentary reviewer; not package author.  
**Coordinator gate:** `COORDINATOR_RECHECK_PASS_WITH_BINARY_HASH_LIMITATION`.  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`.

The coordinator has now independently fetched and parsed the commit-pinned matrix from GitHub and verified its exact byte hash against the manifest. The matrix has 124 unique contiguous records T123–T246, a 12-column header, exactly 12 fields on every record, all statuses `NOT_RUN`, and the required HI-03 references in field 12. The parsed matrix differs from frozen v0.7.5 only at the expected 13 cells: T157 crash oracle and T222–T233 normative bases. Contract comparison shows only the opening Artifact ID differs.

**Binary limitation:** the coordinator's GitHub connector cannot retrieve the binary ZIP payload for independent SHA-256 calculation in this environment. The ZIP's Git tree size and Git blob SHA-1 are verified, and Codex's final readback report declares that the remote ZIP was downloaded and its size/SHA-256 matched local bytes. Do not treat the coordinator as having independently recomputed that ZIP SHA-256. You must independently download and verify the archive bytes if your environment permits; disclose the limitation if not.

## Freeze exact candidate identity

Repository: `jhonf463r/Python`  
Temporary relay branch: `handoff/r10-v077-review-20261018`  
Candidate artifact commit: `5534761ac877ee2f5b1f56ba354e4b09b760b717`  
Relay metadata tip at handoff preparation: `5715533f4952e58ba0e4a9f75e2558147d76087b` (this metadata tip may advance to add this handoff and index pointer; candidate artifact commit must remain fixed).

Candidate ZIP expected from author/readback report: **1,248,405 bytes**, SHA-256 `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf`. GitHub's recursive tree reports that ZIP at 1,248,405 bytes with Git blob SHA-1 `f9d20193d2c318fd998a5ffb2660cd5c489d450c`.

### Commit-pinned candidate inputs

- [Candidate ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip)
- [Complete extracted tree](https://github.com/jhonf463r/Python/tree/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted)
- [Logical contract v0.7.5](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_5_CONTRACT.md)
- [Matrix T123–T246](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv)
- [Changelog](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CHANGELOG.md)
- [Change map](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CHANGE_MAP.md)
- [Consistency and traceability](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CONSISTENCY_AND_TRACEABILITY.md)
- [Preflight report](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_PREFLIGHT_REPORT.md)
- [SHA-256 manifest](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_SHA256.txt)
- [Packaged independent review prompt](https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_INDEPENDENT_DELTA_REVIEW_PROMPT.md)
- [Coordinator's final readback report](https://github.com/jhonf463r/Python/blob/5715533f4952e58ba0e4a9f75e2558147d76087b/relay/R10_V0_7_7_FINAL_READBACK_REPORT.md)
- [Relay index and source package identities](https://github.com/jhonf463r/Python/blob/5715533f4952e58ba0e4a9f75e2558147d76087b/relay/RELAY_INDEX.md)

### Preserved source ZIPs, pinned at candidate commit

- v0.7.5, expected 491,529 bytes; SHA-256 `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_5_DOCUMENTARY_CANDIDATE.zip
- v0.7.4, expected 86,703 bytes; SHA-256 `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip
- v0.7.3, expected 86,835 bytes; SHA-256 `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_3_DOCUMENTARY_CANDIDATE.zip
- v0.7.2, expected 50,589 bytes; SHA-256 `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip

The original Claude/Sonnet v0.7.4 report remains `NOT_RECOVERED / UNRESOLVED`. The coordinator's regenerated reconciliation is only a documentary substitute basis; it is not the missing original report.

## Required independent review

1. Independently download the actual v0.7.7 ZIP and the four preserved source ZIPs where possible. Recompute their actual byte sizes and SHA-256; verify ZIP CRC, safe unique paths, embedded manifest, payload sizes/hashes, and historical preservation. If a ZIP cannot be downloaded or verified, label that precise check unresolved and continue only with explicitly bounded text review. Never claim binary verification without the bytes.
2. Read the entire contract and all 124 matrix rows. Compare the candidate row-by-row and clause-by-clause with frozen v0.7.5.
3. HI-01: confirm logical contract identity `R10_V0_7_5_CONTRACT` is supported by historical naming convention, while v0.7.7 is only the outer package identity.
4. HI-02: confirm T157's preconditions already place P2 after durable commit, and the crash oracle is strictly post-marker; C1 remains `RETRACTED`, C2 remains `ACTIVE`, exactly one contribution remains visible; no duplicate application or revival; the three falsifier classes are explicit.
5. HI-03: parse every data row, not just the header. Confirm exactly 124 data records T123–T246, 12 header columns, exactly 12 fields on every row, every row `NOT_RUN`, and exact field-12 references T222–T233. T229 cites §8.2 only; assess whether that clause supports its exact staged/no-marker scenario.
6. Verify all differences against frozen v0.7.5: contract changes only the Artifact ID metadata value; matrix changes only T157 `crash_retry_conflict_oracle` and the twelve `normative_basis` cells T222–T233. Check that CSV quoting/newline normalization does not alter other parsed values.
7. Confirm the v0.7.6 malformed artifact remains frozen and accurately recorded as failed preflight: T222–T233 had 13 fields with a 12-column header. Do not silently relabel or alter it.
8. Verify README/change map/changelog/consistency/preflight/manifest and relay metadata against actual files; verify historical source preservation and fixed commit links.
9. Report a row/clause-grounded semantic verdict: `INDEPENDENT_DELTA_REVIEW_ACCEPTED_WITH_LIMITATIONS`, `REQUIRES_REPAIRS`, or `BLOCKED`. Enumerate severity, exact file/section/test IDs, counterexample, minimum repair and evidence class for every finding.

The coordinator's text checks are preliminary evidence for your review, not a substitute for it. No semantic acceptance is implied by a valid CSV or valid manifest.

## Governance and preserved state

- v0.7.2 = `FAIL`.
- v0.7.3/v0.7.4 = `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- v0.7.5 = `REQUIRES_REPAIRS / NOT_ACCEPTED`, frozen.
- v0.7.6 = failed documentary preflight due to CSV row width; frozen and unchanged.
- v0.7.7 = candidate passed coordinator's independent text/matrix/pointer recheck with a disclosed binary-hash limitation; independent review pending.
- F-07/F-10 = `OPEN`; F-12 = `PROPOSED / UNRESOLVED`; SC-10 = `PARTIAL`.
- All 124 cases remain `NOT_RUN`; no product code, tests, builds, runtime, probes, migration, services, dispatcher or bridge actions.
- Do not inspect the dirty IABV checkout, `data/`, SQLite, M0A, Packages B–E or `relay-staging\\IABV_v1.5\\data`.
- PR #467 remains `OPEN / DRAFT / UNMERGED`.
- `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.

Next actor after Claude/Sonnet returns: ChatGPT/coordinator to reconcile the exact verdict, persist it to GitHub, and update relay/current-state pointers before another chat transition.
