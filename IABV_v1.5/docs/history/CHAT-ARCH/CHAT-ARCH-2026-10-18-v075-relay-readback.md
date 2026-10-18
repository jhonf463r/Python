# R10 v0.7.5 — Coordinator relay readback and independent-review handoff

**Record ID:** `CHAT-ARCH-2026-10-18-v075-relay-readback`  
**Date:** 2026-10-18 (America/Bogota)  
**Repository:** `jhonf463r/Python`  
**Governance:** `GOVERNANCE = KEEP_BLOCKED`  
**Outcome:** `RELAY_CONTENT_READ_BACK / STATIC_TEXT_SPOT_CHECK_COMPLETE / PENDING_INDEPENDENT_REVIEW`

## 1. Current candidate and relay identity

The owner reports that Codex produced R10 v0.7.5 as a documentary-only candidate and completed source/ZIP/manifest preflight. The candidate is published in this temporary public relay:

- Branch: `handoff/r10-v075-review-20261018`.
- **Immutable candidate artifact commit:** [`db5c8788036b7d1c0ae5df9167bb3ec813da5f85`](https://github.com/jhonf463r/Python/tree/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay).
- **Current relay metadata tip after correcting the reviewer handoff:** [`9c47697acff1b02d36000a3249737f698a931fc2`](https://github.com/jhonf463r/Python/tree/9c47697acff1b02d36000a3249737f698a931fc2/relay).
- Corrected reviewer handoff commit: [`fcecb67a1d222283795b5c0f8e8ce6b93169104b`](https://github.com/jhonf463r/Python/blob/fcecb67a1d222283795b5c0f8e8ce6b93169104b/relay/CLAUDE_REVIEW_HANDOFF.md).
- Index: [current relay index](https://github.com/jhonf463r/Python/blob/9c47697acff1b02d36000a3249737f698a931fc2/relay/RELAY_INDEX.md).
- Candidate ZIP as reported by Codex: 491,529 bytes; SHA-256 `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`.
- Matrix: `R10_V0_7_5_TEST_MATRIX_T123_T246.csv`, expected 124 rows T123–T246.

**Evidence separation:** relay path, commit identities, index, handoff, contract, matrix, changelog, consistency report, README and manifest were retrieved from GitHub through the connector. That is `GITHUB_API_VERIFIED` for the remote text/path readback. The candidate ZIP binary and its SHA-256 remain `CODEX_LOCAL_REPORTED / OWNER_REPORTED` for this coordinator; the connector did not independently download/re-hash the binary. Codex reports it downloaded the published ZIP and computed its hash. Claude must independently verify the ZIP bytes and manifest if its review environment can retrieve binary data.

## 2. Relay handoff mismatch found and corrected

The original `relay/CLAUDE_REVIEW_HANDOFF.md` at the relay tip was stale: it referred to an earlier candidate commit `bf41bd5cae7e03c25dfa07bd54b08ea40411c6e7`, a 489,579-byte ZIP with SHA-256 `ceb9e1619b39e7890c4fdce4cf536973cd9324a7a3975adb967bb931275862e9`, and a matrix range ending at T240.

The actual current candidate reported by Codex, and identified by the relay index, is at `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`, with 491,529 bytes, SHA-256 `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`, and 124 rows T123–T246.

**Coordinator action:** replaced only the relay's reviewer handoff document; candidate ZIP and extracted tree at `db5c878...` were not edited. The corrected handoff now explicitly warns against the old commit/range, points to the exact current candidate, and requests adversarial review. The relay index records that metadata correction. Do not trust the stale values from any previously copied handoff.

## 3. Static text spot-check on the pinned candidate

At artifact commit `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`, the coordinator retrieved and parsed the matrix text. Results:

- 12 distinct columns, no removed redundant columns remain.
- 124 data rows, contiguous unique IDs T123–T246.
- All 124 `execution_status` values are `NOT_RUN`.
- No empty matrix cells across those rows in the parsed text.
- No UTF-8 BOM in the returned text.
- No literal generic `No crash injected` placeholder found.
- Key textual rows confirm the intended distinctions for T134/T223, T179, T184, T200, T205/T233, T210, T212, T221/T222 and the L5b boundary controls T224/T225.
- These are checks of retrieved CSV text; they do not mean any test was executed and do not establish semantic acceptance.

### Observed candidate inconsistency to report, not silently fix

The v0.7.5 contract is titled as a v0.7.5 candidate and §0 describes a v0.7.5 artifact, but its opening metadata still says:

`Artifact ID: R10_V0_7_4_CONTRACT`

The changelog also claims the contract and matrix were reidentified. This mismatch was retrieved directly from the candidate text, so it is a `GITHUB_API_VERIFIED` document inconsistency. Do not edit the frozen candidate; Claude must decide materiality and include the exact required correction in its independent verdict. Additional inconsistencies may exist and must be reviewed independently.

## 4. Immediate next actor: Claude/Sonnet

Claude/Sonnet must independently review the complete v0.7.5 package and preserved v0.7.4/v0.7.3/v0.7.2 inputs. Use the **corrected handoff** pinned to commit `fcecb67a1d222283795b5c0f8e8ce6b93169104b`, but the candidate artifact itself is frozen at `db5c878...`. The review must cover all 124 rows T123–T246, contract/registry identity, changelog/report consistency, all F-01–F-14 states, the required row repairs and any compound paths that remain. It must be independent; author summaries are not acceptance evidence.

Expected verdict: `INDEPENDENT_DELTA_REVIEW_ACCEPTED_WITH_LIMITATIONS`, `REQUIRES_REPAIRS`, or `BLOCKED`, with row/clause-grounded justification. If binary retrieval fails, the reviewer must disclose it and must not claim ZIP-hash verification.

The original Claude v0.7.4 report remains `NOT_RECOVERED / UNRESOLVED`; its reported 42,216-byte size and `d1968df6…` prefix remain `OWNER_REPORTED / HASH_UNVERIFIED`. The regenerated coordinator reconciliation is the authorized documentary substitute basis only.

## 5. Governance and preservation

- v0.7.2 = `FAIL`.
- v0.7.3 and v0.7.4 = `REQUIRES_REPAIRS / NOT_ACCEPTED`.
- v0.7.5 = `PENDING_INDEPENDENT_DELTA_REVIEW`, not accepted.
- F-07/F-10 remain `OPEN`; F-12 is proposed and unresolved pending review; F-04/F-11 are documentary repairs with notes; F-14 source/authority gaps remain.
- T123–T246 = `NOT_RUN`; product code execution, tests, build, runtime, migrations and probes = `NOT_RUN`.
- `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
- Preserve the v0.7.4 relay and the current v0.7.5 relay until Claude's verdict is reconciled and persisted.
- Keep PR #467 `OPEN / DRAFT / UNMERGED`.
- Do not inspect the dirty IABV checkout, `data/`, SQLite, M0A, dispatcher, physical bridge, Packages B–E or `relay-staging\\IABV_v1.5\\data`.
- Do not begin implementation, tests, build or runtime.

## 6. Next canonical writeback

After Claude returns, the coordinator must:
1. Save Claude's full report or a sufficiently detailed provenance-labeled adjudication under the canonical continuity branch.
2. Include the exact artifact commit, relay metadata tip, binary checks that were actually performed, and unresolved issues.
3. Update `CHAT-ARCH-2026-10-18-start-here-current-task.md`, `CURRENT-STATE.md`, `CONTEXT-INDEX.md`, `README.md` and `MEMORY-OPERATING-PROTOCOL.md` with the new verdict/pointer.
4. Read all those files back from GitHub and verify the pinned links.
5. Do not delete the relay refs/staging directory until the independent verdict is reconciled and the durable continuity writeback is verified.

