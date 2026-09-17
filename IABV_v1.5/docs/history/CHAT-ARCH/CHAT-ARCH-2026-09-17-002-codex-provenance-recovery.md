# IABV v1.5 — CHAT-ARCH 2026-09-17-002
## Codex Provenance Recovery / Dynamic AI Routing

## PURPOSE

Preserve the material knowledge produced after the Sonnet adversarial audit identified a discrepancy between the reported L5 experiment and the cited Git commit.

This record also captures the message-economy decision: Codex successfully resolved the repository/provenance uncertainty, so another Codex intervention is not currently justified. The next actor is selected from the remaining uncertainty, not from a fixed AI sequence.

## SOURCE CLAIM

Previous L5 report cited:

`codex/world-grounded-learning-bridge = 55d3e2c93807202ec5d0177eda163e8de10418ef`

and claimed a new test:

`tests/test_l5_causal_decision.py`

with reported result:

- control `learned_pattern=0.0`, `total_score=7.545`, selected `None`
- treatment `learned_pattern=1.0`, `total_score=10.095`, selected `8e8f6695-8bdb-4d6b-922d-fa6a11728245`
- `1 passed in 0.98s`

## INDEPENDENT SONNET FINDING

Sonnet verified that the cited remote ref resolves to:

`55d3e2c93807202ec5d0177eda163e8de10418ef`

and that the commit tree did not contain `tests/test_l5_causal_decision.py`.

## CODEX FORENSIC RECOVERY

Codex subsequently recovered the physical artifact in a separate runtime worktree:

`C:\IABV_WORKTREES\world-grounded-learning-bridge-runtime\IABV_v1.5\tests\test_l5_causal_decision.py`

Artifact identity:

- Git blob: `2844537f80c190a1351dac3a95f35f80cf79dc19`
- file SHA-256: `E0DC044C00992034DDE2F826E7A7517B326318060BDB68DF84D06B2F5FF60D5B`
- worktree: `C:\IABV_WORKTREES\world-grounded-learning-bridge-runtime`
- ref: detached `HEAD` at `55d3e2c93807202ec5d0177eda163e8de10418ef`
- status: untracked (`??`)

Therefore the artifact did physically exist, but it was not part of the reported commit tree.

## WHAT REMAINS UNKNOWN

Codex did not recover:

- pytest command;
- stdout/stderr;
- exit code;
- historical test-run artifact;
- proof that the recovered file was the file actually executed for the reported result;
- primary evidence for `7.545`, `10.095`, or the reported pattern UUID.

The recovered file therefore establishes artifact existence and provenance relation, but not execution provenance or result provenance.

## EPISTEMIC STATUS

L5 remains:

`NOT PROVEN`

Reason:

`artifact exists != artifact executed`

and:

`uncommitted artifact != committed branch artifact`

The previous L5 numerical result remains an unverified report.

G3 evidence remains independently valid and must not be silently promoted to L5.

## KNOWLEDGE DELTA

### ΔK

Positive: the prior provenance contradiction is narrowed from "artifact absent everywhere" to "artifact recovered in a distinct uncommitted detached worktree".

### Δπ

Positive: provenance requirements are now stricter. Future experiment reports must bind the executed artifact to an exact worktree/ref and capture execution identity, not only a commit SHA.

### ΔB

None yet for IABV runtime behavior.

### ΔY

None yet for learning-induced world behavior.

## DYNAMIC ROLE / MESSAGE-ECONOMY FINDING

The user has repeatedly required preservation of scarce Codex interventions and use of the strongest demonstrated actor only when needed.

This event provides concrete evidence that Codex has high utility for:

- repository archaeology;
- detached-worktree discovery;
- blob/file identity recovery;
- exact provenance reconciliation.

Devin has stronger established evidence for:

- Windows runtime observation;
- environment startup/integration checks;
- practical runtime experiments;
- scoped implementation/test correction.

Sonnet has stronger established evidence for:

- independent forensic audit;
- adversarial causal challenge;
- false-positive detection;
- artifact/result validity adjudication.

Therefore do not spend another Codex intervention on the current remaining question. The remaining uncertainty is whether the recovered uncommitted artifact actually produced the claimed L5 result and whether its Control/Treatment design is causally valid. That is an independent forensic-audit problem.

## CURRENT ROUTING DECISION

Next actor:

`SONNET`

Reason:

- Codex already removed the provenance-location uncertainty;
- another Codex call would repeat completed repository archaeology;
- Devin would be useful later if a concrete runtime reproduction/fix is required;
- independence is material because the artifact's authorship/execution relationship is part of the question;
- Opus remains reserved for genuine architectural contradiction.

## REQUIRED NEXT EDGE

`recovered artifact
→ actual test execution
→ observed control/treatment result
→ causal attribution
`

Do not advance to L6 until this edge is independently adjudicated.

## STOP / PRESERVATION RULE

Do not delete or overwrite the recovered artifact solely to clean the historical discrepancy. Preserve its exact path, blob hash, file hash and detached-ref relation as evidence.

Do not create a replacement L5 test before the forensic audit of the recovered original is complete.
