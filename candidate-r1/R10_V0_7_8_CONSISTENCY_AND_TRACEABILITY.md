# R10 v0.7.8 consistency and traceability

## Provenance and classification

The five required ZIP sources were downloaded from immutable commit `5534761ac877ee2f5b1f56ba354e4b09b760b717` and their received byte counts and SHA-256 values were recomputed before authoring. The v0.7.5 package is the logical source. v0.7.7 is preserved as a verified prior delta candidate; its three HI repairs are retained. v0.7.4/v0.7.3/v0.7.2 packages and their extracted trees are preserved in the historical directory. v0.7.6 remains a frozen external failed-preflight artifact; this package does not re-verify its ZIP or alter it.

All v0.7.8 normative language is `PROPOSED` and requires independent review. Contract and matrix presence prove only documentary content. No product implementation capability is verified.

## Execution lifecycle

§3.3, the §12 closed writer/transition tables, and §17.1 contain the same machine: `PLANNED → CRITERIA_FROZEN → DISPATCHED → EXECUTION_STARTED → SUCCEEDED`, plus `DISPATCHED|EXECUTION_STARTED → ABANDONED` and `DISPATCHED|EXECUTION_STARTED → SUPERSEDED`. `EXECUTION_SUCCEEDED` requires an authenticated execution observer receipt binding execution, dispatch receipt, mode, complete output digest, and authenticated parent turn in conversational mode. It asserts normal attributed completion only; result validation, task success, eligibility and learning remain separate.

`ABANDONED` uses the already specified strict frozen deadline. `SUPERSEDED` requires a durably active later attempt. No deterministic accepted writer/trigger exists for FAILED, ABORTED or TIMED_OUT, so they are excluded. Infrastructure timeout and process failure are diagnostics and do not produce negative learning. T132 specifies the diagnostic-only case and explicitly says no terminal event was accepted.

## Result allocation and correlation

`ResultState` is limited to allocated results: CAPTURED, ACCEPTED, REJECTED. `RESULT_RECORDED` allocates the result ID and CAPTURED only after authenticated correlation, identity, completeness, attestation and slot gates pass. Pre-allocation ingress failures produce durable `CAPTURE_REJECTED`, typed correlation/rejection disposition, and no result ID, ResultState, slot, evaluation or effect. An allocated result later rejected by validation retains its ID and changes to REJECTED. §§4.1/12/17.1/17.2 and T136/T137/T138/T176/T231/T244 state these boundaries. There is no shared transaction or exactly-once claim across stores.

## Fixture and traceability boundaries

T221/T222/T224/T225 each state the fixture-supplied scalar `lift`, the inclusive `lift >= 0.10` comparator, `n_treatment >= 20`, `n_control >= 20`, their observed values and one intended predicate. No formula for deriving lift from raw observations is specified. The scenario labels in the 20 named rows are removed without changing category/provenance. T137/T139/T146/T149 oracle framing is normalized. T157's label is narrowed to post-commit P2 replay; its HI-02 crash oracle, preconditions and numeric deltas are retained.

The complete contract line diff and parsed matrix field delta are provided in `R10_V0_7_8_FULL_DIFF_V0_7_7.md`. The parser audit requires 124 unique contiguous IDs, 12 fields per record, and all statuses `NOT_RUN`.

## Retained frontier

v0.7.2 remains `FAIL`; v0.7.3/v0.7.4/v0.7.5 remain `REQUIRES_REPAIRS / NOT_ACCEPTED`; v0.7.6 remains failed-preflight/frozen; v0.7.7 remains `REQUIRES_REPAIRS / NOT_ACCEPTED`. F-07/F-10 remain `OPEN`; F-12 remains `PROPOSED / UNRESOLVED`; SC-10 remains `PARTIAL`; `BRIDGE_NOT_READY`; `GOVERNANCE = KEEP_BLOCKED`. All 124 cases remain `NOT_RUN`.


## R1 bounded matrix consistency delta

The original immutable candidate at commit `aa8ea71578b024c69dba446d010f0ea7b068bee3` used the undefined execution label `EXECUTION.COMPLETED` in T137 twice. R1 uses `ExecutionState=SUCCEEDED` only for an already completed, authenticated execution observer receipt that binds execution/dispatch, mode and complete-output digest (and the parent turn when conversational). A later, separate result-ingress capture is explicitly truncated and fails the completeness gate. The oracle remains `CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE` before allocation and creates no `result_id`, `ResultState`, AUTO slot, evaluation, adoption, contribution or effect. This distinction follows §§3.3, 4.1, 12 and 17.1–17.2; it does not assert test execution.

A bounded search of the matrix's explicit correlation-status assignments also found `CORRELATED` in T141. §17.2 lists the allowed correlation dispositions as `MATCHED`, `UNCORRELATED`, `LATE_STALE` and `CONFLICT_DETECTED`; R1 changes the positive value to `MATCHED`. Other searched references to `UNCORRELATED`/`LATE_STALE` remain rejection/correlation dispositions and are not represented as `ResultState` values. T231 keeps `RESULT_ACCEPTED` separate from execution terminality. This is a targeted vocabulary consistency review, not proof of implementation or exhaustive semantic correctness.
