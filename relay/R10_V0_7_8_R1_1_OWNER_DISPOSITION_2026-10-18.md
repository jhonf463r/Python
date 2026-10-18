# R10 v0.7.8 R1.1 — owner disposition (2026-10-18)

## Owner decision

`OWNER_DISPOSITION = KEEP_R1_1_FROZEN_WITH_LIMITATIONS`

The owner directs that R10 v0.7.8 R1.1 remain frozen with documentary disposition `READY_WITH_LIMITATIONS`. This is **not** final artifact acceptance, approval of R10, or authorization to implement or activate the bridge.

No R1.2 is to be created, and R1.1 is not to be modified for non-blocking notes N-1, N-2, or N-3. N-1 and N-2 remain possible clarifications only for a future, separately versioned documentary amendment, each requiring explicit owner authorization. No amendment is authorized by this disposition. N-3 requires no repair.

## Evidence and provenance kept separate

- `CLAUDE_REVIEWER_REPORTED`: the persisted Claude/Sonnet report records `READY_WITH_LIMITATIONS`, no defect in the R1.1 delta, and three non-blocking notes. Its coordinator-added provenance note says the report was persisted from complete reviewer text supplied inline after the named report was absent from three expected GitHub paths; reviewer claims of direct byte checks remain reviewer-reported, not coordinator-reperformed.
- `COORDINATOR_ADJUDICATED`: the coordinator adjudication records no mandatory R1.1 delta repair and retains the limitations below. It does not claim to repeat all reviewer ZIP/member/hash checks.
- `CODEX_LOCAL_CALCULATED`: the binary identity gate records local and downloaded commit-pinned ZIP size/SHA-256 and Git blob SHA-1 calculations, with both copies matching declared identities.
- `COORDINATOR_READBACK_VERIFIED`: the coordinator readback confirms the published binary-gate report and index at its pinned commit, while explicitly not recalculating the ZIP bytes itself.
- R1.1 remains the immutable candidate at artifact commit `23e46401e282acd4f39083fc184fced51770f2fa`.

## Notes retained without repair

- **N-1 — T137 completeness-code mapping:** the review found support for `VALIDATION_EVIDENCE_INCOMPLETE` through completeness and guard-precedence clauses, but no explicit clause mapping that code to truncated ingress capture. This remains a non-blocking traceability clarification; no change to R1.1.
- **N-2 — pre-existing §12 wording:** “or terminal execution” is ambiguous alongside post-`SUCCEEDED` capture. The review describes a consistent reading but leaves the wording as a possible future, separately authorized contract clarification. No change to the frozen contract or R1.1.
- **N-3 — T141 §2.2 citation:** tangential over-citation, assessed as harmless; no repair required.
- **R1 provenance limitation:** the reviewer did not independently establish that the R1 source came from commit `541e150b…`; the reviewer reports checking the R1 ZIP present at artifact commit `23e46401e282acd4f39083fc184fced51770f2fa`, which does not prove earlier-commit provenance. This limitation remains open and is not upgraded by this owner decision.

## Current boundaries

- `R1.1 = READY_WITH_LIMITATIONS / NOT_ACCEPTED`.
- `GOVERNANCE = KEEP_BLOCKED`.
- `BRIDGE_NOT_READY`.
- `T123–T246 = NOT_RUN`.
- No product code, tests, builds, runtime, M0A, dispatcher, or bridge activity is authorized here.
- `NEXT_ACTOR = NONE_FOR_R1_1_PENDING_NEW_OWNER_OBJECTIVE`.

This record does not initiate a new review round or a future amendment. The candidate, historical artifacts, reviewer report, coordinator adjudication, and coordinator readback remain unchanged and retain their separate provenance.