# Independent delta review request — R10 v0.7.3

Reviewer: Claude/Sonnet. Review the complete candidate directory and ZIP against the preserved seven-entry v0.7.2 source package. This request is for a documentary delta review only; do not treat the author's report as proof.

1. Verify candidate ZIP SHA/size as supplied by the sender, its internal manifest, exact file inventory, and that all seven historical v0.7.2 artifacts are byte-identical to the verified source archive.
2. Read the entire v0.7.3 contract and all 75 CSV rows. Confirm all IDs T123–T197 occur exactly once, every row has a normative basis and `NOT_RUN`, and no row contradicts the normative clauses.
3. Adversarially inspect M0–M5 repairs, especially precedence, correlation, missing `dispatch_turn_id`, state transitions, validator evidence, conflict release versus activation, plan recovery, authorization generation, strict deadline, MANUAL/AUTO separation and tombstone visibility.
4. Identify ambiguous or unsupported semantics and any remaining incompatible matrix oracle. Do not infer runtime behavior, implementation presence, transactionality, recovery, exactly-once or operational readiness from documents.
5. Report each finding with file/section or test ID, exact text, impact, a falsifier or required evidence, and classification. Distinguish `PROVEN_BY_SOURCE`, `CODEX_LOCAL_REPORTED`, `PROPOSED`, `UNPROVEN`, `NOT_RECOVERED`, and `NOT_RUN`.
6. Do not execute code/tests/build/runtime, access IABV `data/` or SQLite, activate M0A/dispatcher/physical bridge, or change the candidate. Keep `GOVERNANCE = KEEP_BLOCKED`.

Acceptance is reserved to the human owner after review. The candidate is not accepted by this prompt.
