# R10 v0.7.8 R1 — parsed matrix cell delta

Source matrix: immutable original v0.7.8 at commit `aa8ea71578b024c69dba446d010f0ea7b068bee3`. Only the following parsed cells change. Contract bytes, all 124 IDs, 12-column schema and `NOT_RUN` statuses are preserved.

## T137 — `initial_state_and_preconditions`

- Before: `EXECUTION.COMPLETED, captor entrega salida truncada`
- After: `ExecutionState=SUCCEEDED; authenticated execution observer completion receipt binds execution/dispatch, mode and digest of complete output (and authenticated parent turn when conversational); a separate later result-ingress capture for the same execution is truncated.`
- Basis: §§3.3, 12 and 17.1 define `SUCCEEDED` as the result of an authenticated observer receipt binding complete, attributable output. T137's truncated capture is a distinct later ingress event, not the completed output itself.

## T137 — `ordered_events_and_oracle`

- Before: `Given initial state EXECUTION.COMPLETED and a truncated capture, record CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE before allocation; no result_id or ResultState is created.`
- After: `The authenticated observer receipt binds execution/dispatch, mode and complete-output digest (and authenticated parent turn when conversational); a separate later result-ingress capture for the same execution is truncated. Persist CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE before result allocation; create no result_id, ResultState, AUTO terminal slot, evaluation, adoption, contribution, or effect.`
- Basis: §§4.1, 12 and 17.1–17.2; a failed pre-allocation completeness gate is durably rejected and does not allocate result identity/state or downstream effect. T137 stays `NOT_RUN`.

## T141 — `ordered_events_and_oracle`

- Before: `Only after all §4.1/§4.2 checks set correlation_status=CORRELATED and accept one slot; any absent check rejects. Nonce/time alone insufficient.`
- After: `Only after all §4.1/§4.2 checks set correlation_status=MATCHED and accept one slot; any absent check rejects. Nonce/time alone insufficient.`
- Basis: §17.2 names `MATCHED` as the positive correlation disposition.

No other parsed matrix cell was changed.
