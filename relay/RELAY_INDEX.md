# R10 v0.7.7 corrective documentary relay index

- Repository: `jhonf463r/Python` (public).
- Temporary branch: `handoff/r10-v077-review-20261018`.
- Immutable candidate artifact commit: `5534761ac877ee2f5b1f56ba354e4b09b760b717`.
- Candidate ZIP: 1,248,405 bytes; SHA-256 `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf`.
- Extracted tree: `relay/candidate/extracted/`; 58 files including the 57-payload manifest.
- Matrix T123–T246: 124 records; 12 columns; every record width 12; all `NOT_RUN`. T222–T233 intended basis is field 12; no field 13.
- Logical contract remains v0.7.5; outer package is v0.7.7.
- v0.7.6 remains frozen and failed coordinator preflight; its 13-field T222–T233 defect is documented in the change map/report. It was not altered and was not used as the authoring base.

## Verified source ZIP identities

| Source ZIP | Bytes | SHA-256 |
|---|---:|---|
| v0.7.5 candidate | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` |
| v0.7.4 candidate | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` |
| v0.7.3 candidate | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` |
| v0.7.2 package | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` |

## Modified payload hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `R10_V0_7_5_CONTRACT.md` | 52085 | `bedbe3f10721259c78566d2e846c50494f36f692399ee6eecc826c1aadcb6d3b` |
| `R10_V0_7_5_TEST_MATRIX_T123_T246.csv` | 75080 | `137d99bfc2154e533bf2ddd87a54629caee52f5b138d03d7f817b7628ffa25d5` |
| `README.md` | 1046 | `35508ca1abecf66b7c6f1b08e9b52fd580d3c77e64053c04802b2f59b54eb986` |
| `R10_V0_7_7_CHANGELOG.md` | 1276 | `191fb109827d7cac173c96cf624170d52be0e934cdea0d0fe6acf44676e6b64d` |
| `R10_V0_7_7_CHANGE_MAP.md` | 2166 | `cea30e2431e7462f9e4136eb0802fda2410b1f2dbd70cb04d3b753eff737c8ab` |
| `R10_V0_7_7_CONSISTENCY_AND_TRACEABILITY.md` | 2169 | `1ade15bf4710dc95aa6bcf2e3f83f04b1acec82c13ceba2a68c0714f8567c290` |
| `R10_V0_7_7_PREFLIGHT_REPORT.md` | 4754 | `e6925664c5bfe26004e19bf1bc4e59101d3307da463f561e9bf619e7f90e57a9` |
| `R10_V0_7_7_SHA256.txt` | 7839 | `acb2f1e93fee062b5fc428a88e5724890577ae0d459d3ba792201d948bde952a` |
| `R10_V0_7_7_INDEPENDENT_DELTA_REVIEW_PROMPT.md` | 1687 | `5a453d618a015cc68f531cbed3435bf6ad50c2d58fca6b4099b723ef0fb4704d` |

## Immutable commit-pinned links

- Candidate ZIP: https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip
- Extracted tree: https://github.com/jhonf463r/Python/tree/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted
- Contract: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_5_CONTRACT.md
- Matrix: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv
- README: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/README.md
- Changelog: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CHANGELOG.md
- Change map: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CHANGE_MAP.md
- Consistency/traceability: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_CONSISTENCY_AND_TRACEABILITY.md
- Preflight report: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_PREFLIGHT_REPORT.md
- Manifest: https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_SHA256.txt
- Independent review prompt (not yet routed): https://github.com/jhonf463r/Python/blob/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/extracted/R10_V0_7_7_INDEPENDENT_DELTA_REVIEW_PROMPT.md
- Final readback report: `relay/R10_V0_7_7_FINAL_READBACK_REPORT.md` (relay metadata commit).

## Retained state

v0.7.2 `FAIL`; v0.7.3/v0.7.4 `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.5 `REQUIRES_REPAIRS / NOT_ACCEPTED`, frozen; v0.7.6 failed preflight/frozen; v0.7.7 pending coordinator recheck. F-07/F-10 `OPEN`; F-12 `PROPOSED / UNRESOLVED`; SC-10 `PARTIAL`; tests/build/runtime `NOT_RUN`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`. No PR/tag/release created.
