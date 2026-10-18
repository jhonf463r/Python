# R10 v0.7.4 changelog

- Repaired normative quarantine/restoration, tombstone scopes, result acceptance, correlation, fencing/task-head CAS, and validation evidence clauses.
- Defined fail-closed L0–L5b predicates; validator attestation and runtime capabilities remain UNPROVEN.
- Replaced duplicated invariant map with one table in §14.
- Normalized legacy rows T129,T136,T137,T139,T140,T146,T149,T151,T152,T153,T160,T161,T172; all rows have explicit fixture, oracle, basis, evidence, falsifier and NOT_RUN state.
- Repaired affected existing oracles including T126,T130,T142,T168,T174,T175,T177–T179,T180–T185,T191,T193,T196.
- Preserved T123–T197 identities and added T198–T221 (24 rows) for missing validation/correlation cases, scenario separation, and L0–L5b positive/negative falsifiers. Total 99 contiguous rows.
- Corrected provenance: the claimed 5bab reference is NOT_RECOVERED; the included namespaced reference SHA is stated separately.
- No product code, tests, builds or runtime executed; every matrix case remains NOT_RUN.
