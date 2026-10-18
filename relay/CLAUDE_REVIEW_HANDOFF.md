# Claude/Sonnet — independent adversarial delta review of R10 v0.7.5

## Exact routing and identity

- **Destination IA:** Claude/Sonnet, in a separate reviewer conversation.
- **Mode:** independent static documentary review only; reviewer must not author or repair the candidate it is reviewing.
- **Repository:** `jhonf463r/Python`, public.
- **Branch:** `handoff/r10-v075-review-20261018`.
- **Immutable candidate artifact commit:** `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`.
- **Current relay metadata tip before this handoff correction:** `4749ec598353de9980e16260452e34e825a6e3ad`. The candidate artifact commit remains the one above; subsequent commits only correct relay documentation.
- **Expected candidate ZIP:** `491529` bytes; SHA-256 `dcad3ba31415f7204b9422b39cb0342862196c7d002468bed27fef02c6f3a6a7`.
- **Governance:** `GOVERNANCE = KEEP_BLOCKED`.
- **Next actor after your review:** ChatGPT/coordinator for row-by-row reconciliation and canonical GitHub writeback.

## Important routing warning

An earlier version of this handoff file incorrectly referred to candidate commit `bf41bd5cae7e03c25dfa07bd54b08ea40411c6e7`, a 489,579-byte ZIP, and matrix ending at T240. **That was not the current candidate. Do not use the earlier commit/hash/range.** Review only the exact artifact commit `db5c8788036b7d1c0ae5df9167bb3ec813da5f85` and all 124 rows T123–T246 listed below.

## Commit-pinned inputs

Candidate ZIP:
https://raw.githubusercontent.com/jhonf463r/Python/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/R10_V0_7_5_DOCUMENTARY_CANDIDATE.zip

Candidate text:
- Contract: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_CONTRACT.md
- Matrix T123–T246: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_TEST_MATRIX_T123_T246.csv
- Changelog: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_CHANGELOG.md
- Consistency/traceability: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_CONSISTENCY_AND_TRACEABILITY.md
- SHA-256 manifest: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_SHA256.txt
- README: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/README.md
- Embedded review prompt: https://github.com/jhonf463r/Python/blob/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/candidate/extracted/R10_V0_7_5_INDEPENDENT_DELTA_REVIEW_PROMPT.md

Historical ZIPs, all pinned to the same artifact commit:
- v0.7.4: https://raw.githubusercontent.com/jhonf463r/Python/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/source/R10_V0_7_4_DOCUMENTARY_CANDIDATE.zip — expected 86,703 bytes; SHA-256 `dff898c9fb7e515ffdc698992475384873995cf50469da88d769072269e1c0e9`.
- v0.7.3: https://raw.githubusercontent.com/jhonf463r/Python/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/source/R10_V0_7_3_DOCUMENTARY_CANDIDATE.zip — expected 86,835 bytes; SHA-256 `1ace1d9331ee943a35fc4663855a09451919ae7b0e8619c799416b48bdae4049`.
- v0.7.2: https://raw.githubusercontent.com/jhonf463r/Python/db5c8788036b7d1c0ae5df9167bb3ec813da5f85/relay/source/R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip — expected 50,589 bytes; SHA-256 `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`.

Historical extracted trees are available under:
- `relay/candidate/extracted/historical/v0.7.4/`
- `relay/candidate/extracted/historical/v0.7.3/`
- `relay/candidate/extracted/historical/v0.7.2/`

## Binary and source verification

From actual downloadable bytes, compute each ZIP's size and SHA-256, check archive integrity, unique/safe paths, internal manifests, and equality of extracted payloads to ZIP members. Compare preserved historical artifacts with their source packages byte-for-byte when possible.

If binary download/access fails, declare the exact limitation and review commit-pinned text only. Do not imply SHA verification merely from the manifest or GitHub text access.

The coordinator has independently read back the pinned text from GitHub and confirmed that the candidate matrix parses to 124 unique contiguous IDs T123–T246, all `NOT_RUN`, with no duplicated columns, no UTF-8 BOM, and no literal generic “No crash injected” placeholders. This is a source-text spot-check, not a binary SHA-256 check or independent semantic acceptance.

## Explicit observation to adjudicate

The current v0.7.5 contract begins with:

`Artifact ID: R10_V0_7_4_CONTRACT`

despite being named `R10_V0_7_5_CONTRACT.md`, introducing itself as an R10 v0.7.5 candidate, and the changelog claiming the candidate contract was reidentified. Treat this as an **observed candidate inconsistency requiring a documented disposition**; do not silently correct the frozen candidate. Identify its impact on package/version identity and whether it independently requires repair.

## Required review scope

Perform an independent adversarial review of the entire contract and all 124 matrix rows T123–T246 against preserved v0.7.4/v0.7.3/v0.7.2 artefacts. Do not accept the author's summary or the coordinator's spot-check as a substitute for reading the evidence.

At minimum verify:

1. Candidate and historical ZIP identities, entries, manifests, and byte-preservation claims.
2. Contract package/version identity and all document names, row ranges, changelog, README, manifest and report consistency.
3. Every matrix row's one-setup/one-discriminating-oracle quality; exact counter deltas; control/falsifier quality; normative-basis references; status `NOT_RUN`.
4. Repairs at T134, T179, T184, T200, T205, T210, T212, T221–T246, including positive/negative control pairing and coverage accounting.
5. Full-row adversarial frontier for F-07 and F-10; proposed F-12 lifecycle semantics; F-04/F-11 qualifications; F-14 provenance/authority caveats.
6. `RESULT_RECORDED` versus `RESULT_ACCEPTED`; ExecutionState versus ResultState; event writers, terminality, evidence immutability, abandonment/supersession, eligibility, diagnostics.
7. Correlation semantics, duplicate claims, `UNCORRELATED` versus `CONFLICT_DETECTED`, deterministic rejection precedence, evidence/validator/dispatch receipt binding.
8. Tombstone scopes `CONTRIBUTION_ONLY` versus `RESULT_AND_LEARNING` and task/contribution/pointer deltas.
9. Crash/recovery or explicit scenario-specific recovery non-applicability; no unproven cross-store exactly-once claim.
10. I1–I12 and L0–L5b coverage, policy/profile/history/score semantics and all compound predicates that remain.
11. Every assertion in the changelog and consistency/traceability report, including actual row/section links.

Pay particular attention to whether removing duplicated columns and splitting cases actually gives independent evidence, or only reorganizes text. Check each new row's setup and outcome independently. Check counts and row references rather than accepting coverage statements.

## Required output

Return one explicit verdict:

- `INDEPENDENT_DELTA_REVIEW_ACCEPTED_WITH_LIMITATIONS`
- `REQUIRES_REPAIRS`
- `BLOCKED`

Do not use a generic PASS.

For every finding, include:
- severity/materiality;
- exact file, section and row ID;
- source text/oracle involved;
- counterexample or semantic impact;
- smallest required repair;
- evidence class: `GITHUB_API_VERIFIED`, `BYTE_HASH_VERIFIED`, `OWNER_REPORTED`, `PROPOSED`, `UNPROVEN`, `NOT_RUN`, `UNRESOLVED`.

State expressly that all 124 cases remain `NOT_RUN` and that static contract review does not prove writer implementation or runtime behavior. Do not author a repair candidate, modify repository content, publish commits, request new credentials, or clean up either relay.

## Preserved limitations and governance

- The original Claude v0.7.4 independent report is still `NOT_RECOVERED / UNRESOLVED`; its 42,216-byte size and `d1968df6…` prefix are `OWNER_REPORTED / HASH_UNVERIFIED`.
- The owner-authorized regenerated coordinator reconciliation is a documentary substitute only, not the original report and not acceptance of v0.7.4.
- Literal v0.6 and the claimed `5bab` reference remain `NOT_RECOVERED`; SC-10 authority remains `UNPROVEN`.
- F-07/F-10 remain open; F-12 is proposed and pending independent review.
- Do not inspect the dirty IABV checkout, `data/`, SQLite or `relay-staging\\IABV_v1.5\\data`. No product code, tests, build, runtime, migrations, probes, dispatcher, physical bridge, M0A or Packages B–E.
- Keep PR #467 `OPEN / DRAFT / UNMERGED`.
- Do not delete this relay, the v0.7.4 relay, or staging artefacts before the independent verdict is reconciled and persisted in canonical GitHub continuity.
- Governance remains `KEEP_BLOCKED`.

**Next actor after your response:** ChatGPT/coordinator; it must reconcile your exact verdict and write a pinned continuity record to GitHub before the next chat transition.
