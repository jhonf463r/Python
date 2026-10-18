# R10 v0.7.6 documentary preflight report

## Scope and source identities

The source artifacts were fetched from the immutable GitHub artifact commit `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`. Actual local byte measurements before editing:

| Artifact | Bytes | SHA-256 | Result |
|---|---:|---|---|
| v0.7.5 candidate ZIP | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` | MATCH |
| v0.7.4 source ZIP | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` | MATCH |
| v0.7.3 source ZIP | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` | MATCH |
| v0.7.2 source ZIP | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` | MATCH |

Each source matched both its declared byte count and SHA-256. The v0.7.5 archive had 45 unique safe entries; every entry stream was read, and all 44 embedded-manifest payload entries matched the manifest's path, size and SHA-256. No absolute or parent-traversal ZIP paths were found.

## Static checks performed

- **Artifact ID convention:** extracted v0.7.3 and v0.7.4 contracts identify themselves as `R10_V0_7_3_CONTRACT` and `R10_V0_7_4_CONTRACT`; v0.7.5 contract title/body identify logical v0.7.5. The repair uses `R10_V0_7_5_CONTRACT`; outer package remains v0.7.6.
- **Contract content diff:** comparing the entire v0.7.5 contract against the candidate after substituting the one authorized metadata value yielded equality. No normative contract clause changed.
- **Matrix parse:** 124 unique contiguous IDs T123–T246; exactly 12 columns; all execution statuses `NOT_RUN`.
- **Matrix content diff:** field-level comparison of all rows and columns found exactly 13 changed cells: T157 `crash_retry_conflict_oracle`, and `normative_basis` for T222–T233. No other matrix cell changed.
- **T157:** preconditions already require committed P2, durable commit record, C1 retracted and C2 active. The new oracle describes only the post-marker crash and replay; it requires preserved committed state, exactly one visible contribution, no reapplication and no C1 revival. The oracle names duplicate effect, divergence and revival falsifiers. No pre-marker case was added.
- **HI-03 clause support:** T222/T224/T225 use §17.7 (L5b thresholds); T223 uses §1.3 (lineage uniqueness) and §8.3 (tombstones/visibility); T226 uses §4.1 and §17.2 (authenticated correlation/rejection); T227/T228 use §7.1 and §17.2 (validator receipt/outcomes and rejection); T229 uses §8.2 only (PREPARING/no-marker invisibility and pre-commit recovery). Proposed §17.4 does not support T229's staged-plan scenario and was omitted. T230 uses §2.2 and §17.2 (producer idempotency/digest conflict); T231 uses §3.2 and §17.1 (sandbox is not execution; capture/result lifecycle); T232 uses §17.2 (stable precedence); T233 uses §8.3 and §17.4 (tombstone scope and exact counter deltas).
- **Historical preservation:** all 45 files in the v0.7.5 extracted tree were compared by SHA-256 against the copied `historical/v0.7.5/` tree; all matched. The preserved historical v0.7.5 ZIP copy matches the verified source ZIP SHA-256.
- **Manifest:** generated from actual candidate-extracted payload bytes; excludes only its own self-entry to avoid recursion. The outer candidate ZIP digest is recorded outside the ZIP in the relay index.
- **Cross references:** package README, changelog, change map, consistency report, review prompt and manifest use the v0.7.6 package identity while retaining the logical v0.7.5 contract/matrix filenames and status.

The final candidate archive's own entry CRC/path check and its outer SHA-256 are recorded by the relay readback/index because the archive cannot contain its own digest without recursion. The archive check reads every entry stream. Any later remote readback must independently repeat the byte and hash checks against the published commit.

## Change boundary and retained states

Only HI-01, HI-02, HI-03 and non-normative v0.7.6 packaging metadata/documents changed. No other contract clause, matrix cell, oracle, state, delta or result changed. v0.7.5 is frozen and preserved.

All tests, builds, runtime, product-code execution, probes, migrations, services, dispatcher and bridge actions: `NOT_RUN`. This preflight establishes document/archive consistency and byte preservation only, not implementation or operational efficacy.

`v0.7.2 = FAIL`; `v0.7.3/v0.7.4 = REQUIRES_REPAIRS / NOT_ACCEPTED`; `v0.7.5 = REQUIRES_REPAIRS / NOT_ACCEPTED` (frozen); `v0.7.6 = PENDING_INDEPENDENT_DELTA_REVIEW`; `F-07/F-10 = OPEN`; `F-12 = PROPOSED / UNRESOLVED`; `SC-10 = PARTIAL`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.