# R10 v0.7.3 documentary candidate

**Status:** `DOCUMENTARY_CANDIDATE_CREATED_PENDING_INDEPENDENT_DELTA_REVIEW`  
**Governance:** `KEEP_BLOCKED`  
**Execution:** every matrix case is `NOT_RUN`.

This candidate repairs documentary inconsistencies in the supplied v0.7.2 package. It does not implement or demonstrate the R10 runtime, durable store, validator, recovery worker, dispatch bridge, or physical/external effects. The original v0.7.2 artifacts are preserved byte-for-byte under `historical/v0.7.2/` and are not normative for this candidate. The original v0.6 contract and matrix remain `NOT_RECOVERED`.

## Contents

- `R10_V0_7_3_CONTRACT.md`: reconstructed normative contract and explicit documentary corrections.
- `R10_V0_7_3_TEST_MATRIX_T123_T197.csv`: 75 unique proposed cases; all `NOT_RUN`; includes normative basis per row.
- `R10_V0_7_3_CHANGELOG.md`: changes from v0.7.2 and scope boundaries.
- `R10_V0_7_3_CONSISTENCY_AND_TRACEABILITY.md`: M0–M5 repair record, static checks, mapping and unresolved proof obligations.
- `R10_V0_7_3_INDEPENDENT_DELTA_REVIEW_PROMPT.md`: handoff instructions for Claude/Sonnet.
- `historical/v0.7.2/`: all seven source archive entries unchanged.
- `R10_V0_7_3_SHA256.txt`: SHA-256 and byte length for each package file except this manifest itself.

## Source custody

Input archive: `R10_V0_7_2_REPAIR_PACKAGE_FOR_CLAUDE.zip`  
Expected and observed size: 50,589 bytes  
Expected and observed SHA-256: `acfb468f78bebc3794b8ec7eaf81baf65d8c40cb66b3f8c7bd2065ffd07fe14e`  
It contained exactly seven entries. Six payload files matched the six entries in its internal manifest by byte length and SHA-256. Each payload was fully read/decompressed for hashing. The archive's manifest was preserved as the seventh historical entry.

The original ZIP is also retained beside the candidate directory as a separate source-custody copy, not nested in this package. The candidate ZIP is a separate sibling deliverable. Its digest is reported outside its own ZIP to avoid a self-referential manifest.

## Review and acceptance

This is implementer-authored documentary evidence and is pending independent delta review. No acceptance, runtime conformance, recovery safety, exactly-once behavior, or operational readiness is claimed. Keep blocked until Claude/Sonnet reviews the full package and unresolved decisions/proof obligations are handled.
