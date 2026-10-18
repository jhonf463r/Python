# R10 v0.7.7 static preflight report

Outer package: `R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip`. Logical contract/matrix remain v0.7.5. All checks below are documentary/static and do not verify product execution.

## Source identity preflight

| Source | Bytes observed | SHA-256 observed | Identity |
|---|---:|---|---|
| v0.7.5 candidate | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` | PASS |
| v0.7.4 candidate | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` | PASS |
| v0.7.3 candidate | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` | PASS |
| v0.7.2 package | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` | PASS |

Each ZIP was downloaded from its commit-pinned URL. Sizes and SHA-256 were recomputed from downloaded bytes before editing and matched the required identity.

## Local static checks

| Check | Status | Scope |
|---|---|---|
| Source ZIP CRC/integrity | PASS | All source ZIP entries read; `zipfile.testzip()` returned no corrupt member. |
| Safe and unique source paths | PASS | All four source ZIPs; rejected absolute/drive/parent-traversal paths and duplicate entries. |
| Embedded source manifests | PASS | v0.7.5 44 payloads; v0.7.4 13; v0.7.3 13; v0.7.2 6; actual bytes, size and SHA-256 checked. |
| Historical v0.7.5 extracted tree | PASS | All 45 source files copied without byte changes. |
| Historical source payload comparisons | PASS | v0.7.4 (14 archive entries), v0.7.3 (14), v0.7.2 (7) all match corresponding files in the v0.7.5 preserved history tree; embedded source ZIP copies match downloaded source ZIP bytes. |
| Full CSV parse | PASS | Python `csv.reader(strict=True)` parsed the full matrix with a dialect-aware parser. |
| Record count and IDs | PASS | 124 data rows; unique contiguous IDs T123–T246. |
| Header width | PASS | Exactly 12 unique header fields. |
| Per-record width | PASS | Every data record has exactly 12 fields; width distribution is 124 records at width 12, zero at any other width. |
| T222–T233 normative field | PASS | Exact field-12 results listed below; each row has exactly 12 fields and no field 13. |
| Execution status | PASS | All 124 rows `NOT_RUN`. |
| Contract identity | PASS | Logical contract `Artifact ID` is `R10_V0_7_5_CONTRACT`; only this metadata value differs from frozen v0.7.5 contract. |
| Complete functional diff | PASS | Matrix parsed-cell delta is only T157 `crash_retry_conflict_oracle` plus T222–T233 `normative_basis`; no other cell differs. |
| HI-02 oracle | PASS | Post-durable-commit-only; state and single-visible-contribution requirements retained; no reapplication/revival; all three falsifier classes explicit. |
| Manifest | PASS | Recomputed over actual candidate payload bytes; excludes only itself. |
| Candidate ZIP integrity | PASS | All members read and compared with extracted tree/manifest; safe unique paths and CRC validated after packaging. |
| Remote ZIP download/hash | NOT_RUN AT PACKAGE FREEZE | Must be completed against immutable published artifact commit and recorded in relay readback report. |
| Remote CSV readback/parse | NOT_RUN AT PACKAGE FREEZE | Must independently parse the commit-pinned GitHub text and assert every row width; recorded in relay readback report after publication. |

### T222–T233 field-12 audit

| ID | Field 12 (`normative_basis`) | Width |
|---|---|---|
| T222 | `§17.7` | `PASS` |
| T223 | `§1.3; §8.3` | `PASS` |
| T224 | `§17.7` | `PASS` |
| T225 | `§17.7` | `PASS` |
| T226 | `§4.1; §17.2` | `PASS` |
| T227 | `§7.1; §17.2` | `PASS` |
| T228 | `§7.1; §17.2` | `PASS` |
| T229 | `§8.2` | `PASS` |
| T230 | `§2.2; §17.2` | `PASS` |
| T231 | `§3.2; §17.1` | `PASS` |
| T232 | `§17.2` | `PASS` |
| T233 | `§8.3; §17.4` | `PASS` |

## Delta and provenance

Authoring base was the verified frozen v0.7.5 ZIP. v0.7.6 was not used as a base and remains frozen as a failed-preflight artifact: coordinator readback found T222–T233 each had 13 fields although the header had 12. The intended bases were in field 13, leaving field 12 empty. This package corrects field placement with structured CSV parse/write, not append-style string edits.

Only HI-01, HI-02 and HI-03 functional differences are allowed. CSV quoting may be normalized by the writer; parsed values outside the listed difference set compare equal to v0.7.5. The full outer ZIP size/SHA and remote readback are reported in the relay index/final readback report to avoid recursive self-hashing.

`TESTS = NOT_RUN`; `BUILD = NOT_RUN`; `RUNTIME = NOT_RUN`; `PRODUCT_CODE_EXECUTION = NOT_RUN`; `GOVERNANCE = KEEP_BLOCKED`. Static archive checks are not implementation verification or acceptance.
