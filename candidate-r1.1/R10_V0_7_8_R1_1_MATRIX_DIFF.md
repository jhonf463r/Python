# R10 v0.7.8 R1.1 — exact parsed matrix deltas

R1.1 retains the three scenario/oracle changes in R1 and adds only the two normative-basis changes required by COORD-02/COORD-03. CSV parsing was strict; the comparisons below are field-level parsed values. The contract is not changed.

## R1 → R1.1 (exactly two cells)

| Case | Field | Before | After |
|---|---|---|---|
| T137 | `normative_basis` | `§4.2; §7` | `§4.1; §4.2; §7; §12; §17.1; §17.2` |
| T141 | `normative_basis` | `§4.1; §4.2; §2.2` | `§2.2; §4.1; §4.2; §17.2` |

## Frozen original v0.7.8 → R1.1 (exactly five cells)

| Case | Field | Before | After |
|---|---|---|---|
| T137 | `initial_state_and_preconditions` | `EXECUTION.COMPLETED, captor entrega salida truncada` | `ExecutionState=SUCCEEDED; authenticated execution observer completion receipt binds execution/dispatch, mode and digest of complete output (and authenticated parent turn when conversational); a separate later result-ingress capture for the same execution is truncated.` |
| T137 | `ordered_events_and_oracle` | `Given initial state EXECUTION.COMPLETED and a truncated capture, record CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE before allocation; no result_id or ResultState is created.` | `The authenticated observer receipt binds execution/dispatch, mode and complete-output digest (and authenticated parent turn when conversational); a separate later result-ingress capture for the same execution is truncated. Persist CAPTURE_REJECTED/VALIDATION_EVIDENCE_INCOMPLETE before result allocation; create no result_id, ResultState, AUTO terminal slot, evaluation, adoption, contribution, or effect.` |
| T137 | `normative_basis` | `§4.2; §7` | `§4.1; §4.2; §7; §12; §17.1; §17.2` |
| T141 | `ordered_events_and_oracle` | `Only after all §4.1/§4.2 checks set correlation_status=CORRELATED and accept one slot; any absent check rejects. Nonce/time alone insufficient.` | `Only after all §4.1/§4.2 checks set correlation_status=MATCHED and accept one slot; any absent check rejects. Nonce/time alone insufficient.` |
| T141 | `normative_basis` | `§4.1; §4.2; §2.2` | `§2.2; §4.1; §4.2; §17.2` |

All IDs T123–T246 remain unique and contiguous; 124 records, 12 fields per record, and all execution statuses `NOT_RUN`.
