# R10 v0.7.7 final relay readback report

Candidate artifact commit: `5534761ac877ee2f5b1f56ba354e4b09b760b717` on temporary branch `handoff/r10-v077-review-20261018`. Relay repository is public `jhonf463r/Python`. This report is a post-publication documentary check; it is not product/runtime validation.

## Check results

| # | Status | Evidence/scope |
|---:|---|---|
| 1 | PASS | Four source ZIPs downloaded from the immutable URLs and recomputed against required byte sizes/SHA-256 before editing. Values are in `RELAY_INDEX.md`. |
| 2 | PASS | `zipfile.testzip()` on all source ZIPs and v0.7.7 candidate; safe relative paths and unique entries checked. |
| 3 | PASS | Root source manifests: v0.7.5 44 entries; v0.7.4 13; v0.7.3 13; v0.7.2 6. New v0.7.7 manifest: 57 payloads; every path/size/SHA-256 matches actual bytes. |
| 4 | PASS | v0.7.5 extracted tree (45 files) byte-preserved; direct v0.7.4/v0.7.3/v0.7.2 archive payloads match corresponding preserved v0.7.5 history files; embedded ZIP copies match source bytes. |
| 5 | PASS | Full candidate matrix parsed with Python `csv.reader(strict=True)`. |
| 6 | PASS | 124 data records; unique contiguous IDs T123–T246. |
| 7 | PASS | Exactly 12 header columns. |
| 8 | PASS | All 124 data records have exactly 12 fields; width distribution is 124×12 and 0 other. |
| 9 | PASS | T222–T233 each have 12 fields; exact field-12 values are listed in `RELAY_INDEX.md`; no field 13. |
| 10 | PASS | Every execution status is `NOT_RUN`. |
| 11 | PASS | Contract Artifact ID is `R10_V0_7_5_CONTRACT`. |
| 12 | PASS | Parsed field-level comparison against frozen v0.7.5 permits only T157 crash oracle and T222–T233 normative bases; contract differs only in Artifact ID. |
| 13 | PASS | ZIP matrix member bytes equal the extracted matrix bytes and the direct commit-pinned GitHub raw matrix bytes. |
| 14 | PASS | All 57 candidate manifest entries match actual payload size/SHA-256; only the manifest self-entry is excluded. |
| 15 | PASS | Candidate ZIP downloaded back from its immutable artifact commit: 1,248,405 bytes; SHA-256 `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf`, equal to local bytes. |
| 16 | PASS | Matrix fetched directly from the immutable GitHub raw URL and parsed independently: 124 rows, 12 columns, every record width 12, all `NOT_RUN`, exact T222–T233 field-12 values. Remote matrix SHA-256 `137d99bfc2154e533bf2ddd87a54629caee52f5b138d03d7f817b7628ffa25d5`; 75,080 bytes. |
| Readback tree | PASS | GitHub commit archive was fetched and unpacked; all 58 files under `relay/candidate/extracted/` matched local extracted bytes. Eight required text files were also fetched individually from raw GitHub and matched. |
| Relay source copies | PASS | Four source ZIPs in `relay/source/` at artifact commit matched their verified SHA-256 values. |

## T222–T233 remote width and field 12

| ID | Width | Field 12 (`normative_basis`) |
|---|---:|---|
| T222 | 12 | `§17.7` |
| T223 | 12 | `§1.3; §8.3` |
| T224 | 12 | `§17.7` |
| T225 | 12 | `§17.7` |
| T226 | 12 | `§4.1; §17.2` |
| T227 | 12 | `§7.1; §17.2` |
| T228 | 12 | `§7.1; §17.2` |
| T229 | 12 | `§8.2` |
| T230 | 12 | `§2.2; §17.2` |
| T231 | 12 | `§3.2; §17.1` |
| T232 | 12 | `§17.2` |
| T233 | 12 | `§8.3; §17.4` |

No tests, builds, product code, runtime, migration, service, probe, dispatcher or bridge were run. Semantic/implementation efficacy remains `UNPROVEN`. The next actor is the coordinator for its independent matrix/artifact pointer recheck. Do not route to Claude/Sonnet until that gate passes. `GOVERNANCE = KEEP_BLOCKED`.
