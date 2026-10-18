# R10 v0.7.8 change map

## Identity and source basis

The candidate is a new logical/normative version derived from the verified frozen v0.7.5 source package. The verified v0.7.7 candidate is retained byte-for-byte as an authoring-delta reference. Its HI-01 contract identity, HI-02 T157 post-commit replay oracle, and HI-03 T222–T233 field-12 bases remain preserved. The complete text/cell delta is in `R10_V0_7_8_FULL_DIFF_V0_7_7.md`.

## Authorized changes

| Finding | Contract scope | Matrix scope | Exact repair |
|---|---|---|---|
| F1 | §§3.3, 12, 17.1; references in §0/§7.2 | T132, T231 | One ExecutionState machine; explicit terminal writers/evidence/guards; retain SUCCEEDED with an authenticated completion receipt; remove unsupported FAILED/TIMED_OUT/ABORTED states; infrastructure timeout remains diagnostic-only; RESULT_ACCEPTED is separate from execution terminality. |
| F2 | §§3.3, 4.1, 12, 17.1, 17.2 | T136, T137, T138, T176, T244 | ResultState applies only after allocation. Pre-allocation UNCORRELATED/LATE_STALE and ingress failures persist CAPTURE_REJECTED without result_id/ResultState/slot/effect. A later invalid validation of an allocated result is ResultState=REJECTED. RESULT_RECORDED allocates CAPTURED only after ingress gates. |
| F3 | — | T231 normative_basis | Remove unrelated §3.2; cite corrected §12 and §17.1. |
| F4 | — | T221, T222, T224, T225 | Each fixture states supplied scalar lift, `lift >= 0.10`, both sample floors, its own counts/value, and one expected L5b predicate. No raw-data formula is asserted. |
| F5 | — | 20 scenario cells and ordered-oracle cells T137/T139/T146/T149 | Remove only leading embedded coverage/reference labels from the named scenarios. Normalize four initial-state oracle framings. Category and provenance cells are unchanged. |
| T157 title | — | T157 scenario | Clarifies post-commit P2 replay; HI-02 oracle, preconditions and 0/0 deltas remain byte-value-identical to v0.7.7 parsed cells. |
| Version/cross-references | artifact labels and package references | — | Versioned contract/matrix names and Artifact ID become v0.7.8; historical v0.7.5/v0.7.7 references remain historical. |

No other parsed matrix cell or normative contract area is intentionally changed. See full diff for every line and cell.
