# R10 v0.7.8 relay index

Status: documentary candidate published; `GOVERNANCE = KEEP_BLOCKED`. This is not acceptance and does not authorize code, tests, runtime, M0A, dispatcher, or bridge activity.

## Immutable artifact commit

- Repository: [jhonf463r/Python](https://github.com/jhonf463r/Python), public.
- Relay branch: `handoff/r10-v078-review-20261018`.
- Candidate content commit: `aa8ea71578b024c69dba446d010f0ea7b068bee3`.
- Candidate ZIP: 5,236,484 bytes; SHA-256 `82d0c634e6624ba07594e6f8debc21551de4ad9c1366cca4e76c6a91263f6f37`.
- The extracted candidate tree and all historical extracted trees are in the same immutable commit. `.gitattributes` disables text normalization for exact source-byte retention.
- Remote binary/text readback was downloaded and verified against the immutable commit; see `relay/REMOTE_READBACK_REPORT.md` in the relay metadata commit.

## Candidate files — commit-pinned

- [Candidate ZIP (GitHub)](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/R10_V0_7_8_DOCUMENTARY_CANDIDATE.zip) · [raw ZIP](https://raw.githubusercontent.com/jhonf463r/Python/aa8ea71578b024c69dba446d010f0ea7b068bee3/R10_V0_7_8_DOCUMENTARY_CANDIDATE.zip)
- [Contract](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_CONTRACT.md)
- [Matrix T123–T246](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_TEST_MATRIX_T123_T246.csv)
- [README](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/README.md)
- [Changelog](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_CHANGELOG.md)
- [Change map](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_CHANGE_MAP.md)
- [Consistency and traceability](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_CONSISTENCY_AND_TRACEABILITY.md)
- [Static preflight report](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_PREFLIGHT_REPORT.md)
- [Full v0.7.7 → v0.7.8 diff](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_FULL_DIFF_V0_7_7.md)
- [SHA-256 manifest](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_SHA256.txt)
- [Independent Claude/Sonnet review prompt](https://github.com/jhonf463r/Python/blob/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate/R10_V0_7_8_INDEPENDENT_DELTA_REVIEW_PROMPT.md)
- [Complete extracted candidate tree](https://github.com/jhonf463r/Python/tree/aa8ea71578b024c69dba446d010f0ea7b068bee3/candidate)

## Verified source inputs

All five source archives were byte-verified before authoring at immutable source commit `5534761ac877ee2f5b1f56ba354e4b09b760b717`:

| Source | Bytes | SHA-256 | Pinned source |
|---|---:|---|---|
| v0.7.7 | 1,248,405 | `bf4e4b19ffda50bc510bc246349b1e1e06dcfd11c40ba816430b40ee77e34baf` | [ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/candidate/R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip) |
| v0.7.5 | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` | [ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_5_DOCUMENTARY_CANDIDATE.zip) |
| v0.7.4 | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` | [ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip) |
| v0.7.3 | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` | [ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_3_DOCUMENTARY_CANDIDATE.zip) |
| v0.7.2 | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` | [ZIP](https://raw.githubusercontent.com/jhonf463r/Python/5534761ac877ee2f5b1f56ba354e4b09b760b717/relay/source/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip) |

The relay also preserves each source ZIP and its full extracted tree under `candidate/historical/`. The v0.7.6 failed-preflight artifact remains external, frozen, and unchanged.

## Inventory and review limits

The candidate manifest covers 210 payload files (self-entry omitted). The outer ZIP has 211 members: the 210 manifest payloads plus the manifest. Its internal matrix parses to 124 records, each 12 fields, IDs T123–T246, all `NOT_RUN`. The full diff lists every changed contract line and every changed parsed matrix cell.

Please review commit-pinned text directly. If the binary ZIP cannot be downloaded, state that binary verification was not completed. This relay does not prove implementation, tests, runtime, exactly-once effects, operational efficacy, or acceptance. Do not send this package to Claude automatically; coordinator recheck comes first.
