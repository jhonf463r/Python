# R10 v0.7.8 changelog

## Documentary candidate; pending coordinator recheck and independent review

- Introduces `R10_V0_7_8_CONTRACT` and the v0.7.8 matrix filenames because normative clauses change.
- Reconciles execution lifecycle and result/correlation lifecycle in §§3.3, 4.1, 12, 17.1 and 17.2. `RESULT_ACCEPTED` never terminalizes execution. `UNCORRELATED` and pre-allocation `LATE_STALE` never become ResultState values.
- Retains `SUCCEEDED` only with an authenticated, identity-bound completion receipt. Retains `ABANDONED` only with the previously frozen strict deadline and `SUPERSEDED` only when a later attempt is durably active. `FAILED`, `ABORTED`, and `TIMED_OUT` have no supported terminal writer/trigger and are excluded. Infrastructure timeout remains diagnostic-only.
- Clarifies T132, T136, T137, T138, T176, T231 and T244 against those state contracts.
- Makes the L5b scalar metric and sample floors explicit in T221/T222/T224/T225.
- Normalizes the 20 specified scenario labels and four initial-state oracle framings. Retitles T157 without altering its v0.7.7 HI-02 oracle, preconditions or deltas.
- Retains all 124 IDs T123–T246 and all statuses `NOT_RUN`.

This is a proposed documentary repair, not implementation evidence, test execution, runtime verification, acceptance, exactly-once proof, or bridge authorization. v0.7.7 remains frozen and `REQUIRES_REPAIRS / NOT_ACCEPTED`.

## Documentary revision R1 — T137 consistency repair

- Corrects T137's noncanonical `EXECUTION.COMPLETED` wording to `ExecutionState=SUCCEEDED`, grounded in §§3.3, 12 and 17.1. The fixture distinguishes the authenticated observer completion receipt binding the complete-output digest from a later, separate truncated result-ingress capture; the oracle remains durable pre-allocation `CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE` with no result identity/state, slot, evaluation, adoption, contribution or effect.
- The bounded vocabulary sweep also found T141's `correlation_status=CORRELATED`; §17.2 permits `MATCHED` as the positive correlation disposition, so T141 is corrected to `MATCHED`.
- Only three parsed matrix cells changed: T137 `initial_state_and_preconditions`, T137 `ordered_events_and_oracle`, and T141 `ordered_events_and_oracle`. The contract, IDs T123–T246 and `NOT_RUN` statuses are preserved.
- This is a documentary revision only. No tests, product code, builds, runtime, integrations, dispatcher, M0A or bridge were executed or authorized. `GOVERNANCE = KEEP_BLOCKED`.
