R10 v0.7.2 — Candidate C audit readme

Governance: KEEP_BLOCKED. Status: PROPOSED. Independent review required.

Candidate C follows Candidate B commit e2876e8e015078d81dd9e1592d2a98122c430b2c. Candidate B and PR #465 remain unchanged; the contract and IDs T123–T196 are preserved. All test statuses remain NOT_RUN.

Artifacts: TEST_MATRIX_T123_T196.csv; MATRIX_REPAIR_DELTA_C.md; MATRIX_REPAIR_REPORT_C.md; SUPPLEMENTAL_TESTS_T197_PLUS_PROPOSED.md (proposals only); MATRIX_REPAIR_CANDIDATE_C_SHA256.txt; OWNER_DECISIONS_REQUIRED.md.

T130/T131 withdraw unsupported strategy rules; T138 separates nonce TTL from execution deadline; T142 uses the platform-attested parent-link rule; T152 removes score determinism; T162/T184 distinguish conflict/event identities and gate restoration; T193 separates fencing token/generation; T194 tests MANUAL/AUTO isolation only.

The §0 reference mismatch is disclosed, not silently repaired. The reconstructed contract is unchanged. This static package proves no runtime, CAS, atomicity, platform attestation or learning. Do not merge/promote.
