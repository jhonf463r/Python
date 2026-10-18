# R10 v0.7.6 documentary relay index

- Repository: `jhonf463r/Python` (public).
- Temporary branch: `handoff/r10-v076-review-20261018`.
- Candidate artifact commit (immutable): `8ab3f72cc69a745e91450b159aa75d3b776fdeab`.
- This index and the Claude handoff are added in a later metadata commit; they do not alter candidate bytes.
- Candidate ZIP: `R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip`; bytes and SHA-256 are given below and are also recorded by readback.
- Full extracted tree: `relay/candidate/extracted/`.
- ZIP entries: 93 total; 92 payloads in the embedded SHA-256 manifest. Full member reads, safe path checks and embedded-manifest byte/hash checks passed locally before publication.
- Matrix: 124 unique contiguous cases T123–T246; 12 columns; all `NOT_RUN`; exact functional delta is T157 oracle plus T222–T233 normative_basis cells.
- The logical contract remains v0.7.5 (`R10_V0_7_5_CONTRACT.md` / `R10_V0_7_5_CONTRACT`); v0.7.6 names the documentary repair package.

## Candidate ZIP identity

| File | Bytes | SHA-256 |
|---|---:|---|
| `R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip` | 1,477,478 | `14353d0185a8460245f2b705558542223a0ed7651ac387fca5dfede47a83732d` |

## Verified source ZIPs

| File | Bytes | SHA-256 |
|---|---:|---|
| v0.7.5 candidate | 491,529 | `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7` |
| v0.7.4 source | 86,703 | `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9` |
| v0.7.3 source | 86,835 | `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049` |
| v0.7.2 source | 50,589 | `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e` |

All source sizes and hashes above were recomputed from downloaded bytes and matched expected identities. The v0.7.5 extracted tree (45 files) and its ZIP were preserved and compared byte-for-byte/hash-for-hash. Historical v0.7.4/v0.7.3/v0.7.2 ZIPs and payload trees remain nested in the preserved v0.7.5 tree and are also available under `relay/source/` for direct downloads.

## Modified top-level candidate payloads

| File | Bytes | SHA-256 |
|---|---:|---|
| `R10_V0_7_5_CONTRACT.md` | 52085 | `bedbe3f10721259c78566d2e846c50494f36f692399ee6eecc826c1aadcb6d3b` |
| `R10_V0_7_5_TEST_MATRIX_T123_T246.csv` | 75092 | `9662fe99bfad55eaf822096a18be14ba4a350043d718db50f83918a5f74c10ef` |
| `R10_V0_7_6_CHANGE_MAP.md` | 2093 | `629cad52bdcec35d6d75c371faa8e5fb12d919f2059b97684bad5460d71c001c` |
| `R10_V0_7_6_CHANGELOG.md` | 1334 | `934d619763fd7e90b1c3f1a8c373e03aa68c21f70a71522ded563c5221dd9eb0` |
| `R10_V0_7_6_CONSISTENCY_AND_TRACEABILITY.md` | 2209 | `8d48a53012ccdf51866bffeaba50a56bd9a164528a49ff2cf9350474361bb365` |
| `R10_V0_7_6_INDEPENDENT_DELTA_REVIEW_PROMPT.md` | 1733 | `d7275e5f8a8dfbbbf2951c998d3672f2939f89348167119fa6b0b3e541913931` |
| `R10_V0_7_6_PREFLIGHT_REPORT.md` | 4692 | `4f2dbcdeb374ba1d4cfe8e90c5367712bca865b5144fe6be07aff4402cf4967e` |
| `R10_V0_7_6_SHA256.txt` | 12403 | `2a08b980a35fa77fe9d0990c7d330dc339433c9ea426133b45943d12aa1ccf3e` |
| `README.md` | 994 | `c53811de6b1cc1eb2d266db14f6c6a723910b6b890f56c00d6dcf8f79517b417` |
## Commit-pinned links

The candidate files below are pinned to the immutable candidate artifact commit:

- Candidate ZIP: `https://raw.githubusercontent.com/jhonf463r/Python/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/R10_V0_7_6_DOCUMENTARY_CANDIDATE.zip`
- Extracted root: `https://github.com/jhonf463r/Python/tree/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted`
- Contract: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_5_CONTRACT.md`
- Matrix T123–T246: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv`
- README: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/README.md`
- Changelog: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_CHANGELOG.md`
- Consistency/traceability: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_CONSISTENCY_AND_TRACEABILITY.md`
- Change map: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_CHANGE_MAP.md`
- Preflight report: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_PREFLIGHT_REPORT.md`
- Manifest: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_SHA256.txt`
- Independent review prompt: `https://github.com/jhonf463r/Python/blob/8ab3f72cc69a745e91450b159aa75d3b776fdeab/relay/candidate/extracted/R10_V0_7_6_INDEPENDENT_DELTA_REVIEW_PROMPT.md`

The source ZIPs are available at `relay/source/` and are pinned to the same commit. See `CLAUDE_REVIEW_HANDOFF.md` for reviewer instructions and the exact candidate commit. Binary-download capability depends on Claude's environment; if ZIP retrieval fails, Claude must disclose this and must not claim byte verification.

## Retained governance

v0.7.2 `FAIL`; v0.7.3/v0.7.4 `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.5 `REQUIRES_REPAIRS / NOT_ACCEPTED` and frozen; v0.7.6 pending independent review. F-07/F-10 `OPEN`; F-12 proposed/unresolved; SC-10 `PARTIAL`; tests/build/runtime `NOT_RUN`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`. PR #467 is untouched by this relay task.