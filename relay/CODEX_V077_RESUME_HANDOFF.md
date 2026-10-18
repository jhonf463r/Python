# Codex local — resume R10 v0.7.7 documentary authoring after source-locator correction

**Destination IA:** Codex local.  
**Role:** documentary author and static verifier only.  
**Coordinator:** ChatGPT.  
**Future independent reviewer:** Claude/Sonnet, only after coordinator recheck.  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`.

## Why this is a continuation, not a fresh audit

The prior v0.7.7 attempt stopped correctly because its supplied v0.7.4 URL had an erroneous path:

`.../history/v0.7.3/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`

The immutable Git tree at source commit `ad5c094fa3e7e4d1989079983f8f6c05f3296551` shows the actual v0.7.4 path is `candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip`. The source-locator correction is recorded at [R10 v0.7.7 source URL correction](https://github.com/jhonf463r/Python/blob/handoff/r10-v076-review-20261018/relay/R10_V0_7_7_SOURCE_URL_CORRECTION_2026-10-18.md).

Continue the previously specified bounded corrective task after applying this locator fix. Do not treat the bad URL itself as a source artifact identity mismatch, and do not bypass the actual byte-level checks.

## 1. Correct immutable source URLs and expected identity

Download the bytes and recompute actual size and SHA-256. Each source must match both expected values before any edit.

### Frozen v0.7.5 candidate — authoring base

URL: https://raw.githubusercontent.com/jhonf463r/Python/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/R10_V0_7_5_DOCUMENTARY_CANDIDATE.zip

Expected size: **491,529 bytes**  
Expected SHA-256: `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`

### v0.7.4 — corrected URL

URL: https://raw.githubusercontent.com/jhonf463r/Python/ad5c094fa3e7e4d1989079983f8f6c05f3296551/candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip

Expected size: **86,703 bytes**  
Expected SHA-256: `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`

At commit `ad5c094fa3e7e4d1989079983f8f6c05f3296551`, GitHub's recursive Git tree confirms `candidate/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip` exists, size 86,703, Git blob SHA-1 `51e7a6802a541e6bd73f2c9a382671512c56829e`. This Git blob SHA-1 is only a locator/byte-object identity aid, not a replacement for SHA-256.

### v0.7.3 — unchanged path, verified in the source tree

URL: https://raw.githubusercontent.com/jhonf463r/Python/ad5c094fa3e7e4d1989079983f8f6c05f3296551/history/v0.7.3/R10_V0_7_3_DOCUMENTARY_CANDIDATE.zip

Expected size: **86,835 bytes**  
Expected SHA-256: `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`

### v0.7.2 — unchanged path, verified in the source tree

URL: https://raw.githubusercontent.com/jhonf463r/Python/ad5c094fa3e7e4d1989079983f8f6c05f3296551/source/v0.7.2/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip

Expected size: **50,589 bytes**  
Expected SHA-256: `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`

The complete immutable source tree at `ad5c094...` confirms all three paths: v0.7.4 at `candidate/`, v0.7.3 at `history/v0.7.3/`, and v0.7.2 at `source/v0.7.2/`.

If the corrected v0.7.4 URL still fails, or its actual bytes do not match exactly 86,703 bytes and the expected SHA-256, stop. Do not try arbitrary replacement sources, reconstruct the ZIP or continue by trusting a previously reported hash. Likewise, stop if any other required source fails identity verification.

## 2. Keep v0.7.6 and all historical artifacts immutable

The defective v0.7.6 candidate remains frozen at commit `8ab3f72cc69a745e91450b159aa75d3b776fdeab`. It must not be overwritten, retagged, deleted, or treated as preflight-complete.

The coordinator's confirmed v0.7.6 defect is documented here:

https://github.com/jhonf463r/Python/blob/1e03c3e86851fa787bd346f1ac9e0906b332725d/relay/R10_V0_7_6_COORDINATOR_PREFLIGHT_BLOCKER_2026-10-18.md

It has a 12-column CSV header, but T222–T233 each contain 13 fields. The intended normative basis is in a surplus field 13 while actual field 12 `normative_basis` is empty.

The proper v0.7.7 base is the actual downloaded and verified v0.7.5 ZIP. Do not copy the malformed v0.7.6 matrix as the new authoring base. The v0.7.6 package may be inspected solely to understand the change intent, never to replace missing source bytes or to inherit its malformed CSV.

Use a fresh, isolated workspace outside the protected IABV checkout. Preserve every source ZIP and extracted historical payload byte-for-byte.

## 3. Minimal authorized content changes for v0.7.7

The outer package identity is `R10_V0_7_7_DOCUMENTARY_CANDIDATE.zip`. The logical contract remains v0.7.5 and its canonical contract identity/filename remain `R10_V0_7_5_CONTRACT.md` / `R10_V0_7_5_CONTRACT`.

Apply exactly these repairs to a working copy derived from the verified v0.7.5 ZIP.

### HI-01 — contract identity

Opening contract metadata must state:

`Artifact ID: R10_V0_7_5_CONTRACT`

Do not change normative clauses to make the logical contract version follow the outer ZIP's v0.7.7 package identity.

### HI-02 — T157 recovery oracle

Retain the intended repaired T157 oracle:

- P2 is already committed and has a durable commit marker.
- The crash occurs only after that durable marker.
- After restart/replay, P2 remains committed, C1 remains `RETRACTED`, C2 remains `ACTIVE` for R1.
- Exactly one contribution is visible.
- Recovery reads/replays the existing committed log without reapplying the retraction/substitution and without reviving C1.
- Explicit falsifiers identify duplicate effect application, divergence from committed state and revival of C1.

Do not introduce a pre-marker crash under the existing T157 preconditions. Do not alter unrelated fields or oracles.

### HI-03 — CSV-aware correction of T222–T233

Use a real CSV parser/writer (or an equivalently correct dialect-aware structured transformation) to set the actual twelfth field `normative_basis` to these exact values:

| Test ID | `normative_basis` |
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

For each of those rows: field 12 must carry the intended value and there must be no field 13. T229 deliberately cites §8.2 alone; do not add §17.4 without a clause-specific argument showing it governs the staged/no-marker scenario.

Preserve all other cell contents from frozen v0.7.5. Do not perform append-style cell mutation or broad string replacement.

## 4. Package and evidence records

Create new outer v0.7.7 package metadata and the required documents: README, changelog, consistency/traceability, change map, preflight report, SHA-256 manifest and an updated Claude/Sonnet independent review prompt. Their names must consistently use v0.7.7 for the outer package while retaining the logical contract/matrix names and IDs.

The change map must say that v0.7.6 failed coordinator preflight due to the 13-field rows. Do not claim v0.7.6's prior preflight was valid. Record that v0.7.6 remains frozen and unmodified.

The package's manifest must be recomputed against real payload bytes. It must exclude only the manifest's own recursive hash and record all other applicable payload sizes and hashes. Recalculate the outer ZIP size/SHA-256 after final packaging; do not reuse an earlier ZIP identity.

## 5. Mandatory v0.7.7 static preflight

At minimum:

1. Verify the four source ZIPs' actual downloaded sizes and SHA-256 values against Section 1 before editing.
2. Check ZIP CRC, safe paths, duplicate paths and manifest payloads.
3. Prove historical ZIPs and payloads remain byte-for-byte preserved.
4. Parse the full matrix: exactly 124 records, contiguous unique IDs T123–T246, exactly 12 columns, all statuses `NOT_RUN`.
5. **Assert for every record that row field count equals header field count.** A header-only column-count check is not sufficient.
6. Explicitly report per-row width results for T222–T233 and the exact twelfth-field value in each row.
7. Compare the complete resulting matrix with the frozen v0.7.5 source. Allowed differences are only T157's `crash_retry_conflict_oracle` and `normative_basis` for T222–T233.
8. Confirm HI-01 is the only functional contract metadata difference; no normative clause changed.
9. Check cross-references among README, changelog, change map, traceability report, manifest, prompt and ZIP inventory.
10. Publish the candidate and complete extracted tree to a new isolated relay branch. Check first that the name `handoff/r10-v077-review-20261018` does not already exist; if it does, choose a fresh unique suffix.
11. Download the exact published ZIP back from its immutable GitHub commit; recompute size/SHA-256 and compare to local output bytes.
12. Read back the published CSV as text from that same immutable commit; independently parse it and verify every row has exactly 12 fields. Confirm that the matrix inside the ZIP matches the published extracted matrix bytes, and that the manifest matches the actual ZIP payloads.

Report each check as `PASS`, `FAIL`, `NOT_RUN` or `UNPROVEN` and explain precisely what was checked. Do not call any documentary check a runtime/test pass. All 124 test rows remain `NOT_RUN`.

Do not publish a PR, tag or release. Do not modify PR #467, v0.7.5, v0.7.6, or the canonical main branch. Preserve all relay artifacts.

## 6. Scope prohibitions and completion state

No product code, tests, build, runtime, migrations, integration probes, service actions, dispatcher or bridge activation. Do not access M0A, Packages B–E, the dirty IABV checkout, `data/`, SQLite, or `relay-staging\\IABV_v1.5\\data`. Do not install tools, request new auth, or incur extra costs.

If source identities match and every static/remote-readback check passes, report:

`DOCUMENTARY_CANDIDATE_CREATED_PREFLIGHT_COMPLETE_PENDING_COORDINATOR_RECHECK`

Otherwise stop with a precise `BLOCKED_*` status. Do not hand off to Claude automatically; coordinator must verify the published matrix field count and artifact pointers first.

Retain:

- v0.7.2 = `FAIL`
- v0.7.3/v0.7.4 = `REQUIRES_REPAIRS / NOT_ACCEPTED`
- v0.7.5 = `REQUIRES_REPAIRS / NOT_ACCEPTED`, frozen
- v0.7.6 = failed documentary preflight, frozen
- v0.7.7 = pending creation and coordinator recheck
- F-07/F-10 = `OPEN`
- F-12 = `PROPOSED / UNRESOLVED`
- SC-10 = `PARTIAL`
- tests/build/runtime = `NOT_RUN`
- `BRIDGE_NOT_READY`
- `GOVERNANCE = KEEP_BLOCKED`
