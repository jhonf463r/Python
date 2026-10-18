# R10 v0.7.7 consistency and traceability

## Provenance

Authoring base: actual v0.7.5 candidate ZIP downloaded from commit `db5c8788036b7d1c0ae5df9167bb3ec813da5f85`, after size/SHA verification. v0.7.4/v0.7.3/v0.7.2 were also downloaded from fixed immutable source URLs and byte-verified. Source identities, ZIP checks and historical comparisons are listed in the preflight report.

The v0.7.6 artifact at commit `8ab3f72cc69a745e91450b159aa75d3b776fdeab` is frozen as a failed preflight artifact. The coordinator's commit-pinned report found T222–T233 with 13 fields while the header has 12; the normative basis was in field 13, leaving field 12 empty. The reported earlier preflight did not validate every record width and is not treated as valid. v0.7.6 was not used as the content base and was not changed.

## Contract and matrix traceability

The logical contract remains v0.7.5. Its `Artifact ID` follows the v0.7.3/v0.7.4 convention and no normative clause is changed. T157 models only a post-durable-marker P2 crash under its committed-state preconditions. T222–T233 values are assigned to the `normative_basis` field by header name and CSV field index; a parser assertion confirms every data row has 12 fields and the expected reference is field 12. T229 retains §8.2 alone because §17.4 does not govern a staged plan lacking a commit marker.

The complete parsed-matrix comparison to frozen v0.7.5 permits only T157 `crash_retry_conflict_oracle` and T222–T233 `normative_basis` differences. Contract comparison permits only the opening Artifact ID value. No other matrix fields or contract clauses change.

## Retained limits and states

All 124 cases remain `NOT_RUN`. Documentary integrity does not prove implementation, runtime behavior, exactly-once effects, validator authority, atomic recovery, operational efficacy or acceptance. Retain v0.7.2 `FAIL`; v0.7.3/v0.7.4 `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.5 `REQUIRES_REPAIRS / NOT_ACCEPTED` and frozen; v0.7.6 failed preflight and frozen; v0.7.7 pending coordinator recheck; F-07/F-10 `OPEN`; F-12 `PROPOSED / UNRESOLVED`; SC-10 `PARTIAL`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`.
