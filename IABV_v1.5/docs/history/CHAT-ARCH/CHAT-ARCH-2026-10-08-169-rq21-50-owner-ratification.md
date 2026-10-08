# CHAT-ARCH 2026-10-08-169 — RQ21.50 HUMAN DOMAIN OWNER RATIFICATION

## Provenance

Promoted from the explicit Human Domain Owner decisions supplied in the current continuity turn.

Parent canonical frontier:
CHAT-ARCH-2026-10-08-168-cross-chat-continuity-reconciliation-rq21-49.md

Remote main verified before this writeback:
4e4bdde029b03f2a281f7612a14fbf755d360bcf

Pinned executable experiment baseline remains:
5b1d89022ee4cdc63c1f88e050f086b40a42875c

Tree:
ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61

## Owner decisions

### R2 — Independent conformance evidence
YES.

Interpretation: a realization cannot establish capability satisfaction merely by asserting or producing a PASS-like result. The validation contract requires evidence with sufficient objective/tangible verifiability; conformance/coverage claims are not self-authenticating.

### R3 — Attributable effects and containment boundary
YES.

Interpretation: attributable effects include direct effects plus effects produced through descendants and delegated paths such as IPC, loopback, local services, or other causally attributable processes/channels. The containment boundary must not be bypassable by delegation.

### R8 — Candidate access to X
YES.

Interpretation: X, the expected-behaviour specification / validation oracle input, must remain inaccessible/hidden from the candidate during validation so the candidate cannot tailor behaviour to the hidden test criterion.

This is an anti-gaming requirement, not a claim that the candidate must be unaware of its general task objective.

### R6 — Evidence integrity
YES.

Interpretation: validation evidence must be protected against unauthorized modification by actors outside the evidence trust/containment boundary. Tangibility alone is insufficient if an external actor can rewrite, delete, or forge the evidence.

## Epistemic reconciliation

FACT
- Machine capability identity remains capability.sandbox.dynamic_validation.
- candidate, X, and E remain validation/task-envelope inputs.
- R2/R3/R8/R6 are now explicit Human Domain Owner decisions.

INFERENCE
- The implementation must provide protected evidence, attributable-effect accounting, and a non-candidate-accessible representation of X.
- A second independent judge is not necessarily required merely because R2=YES; the requirement is independently verifiable evidence/conformance rather than a self-authenticating realization claim.

ASSUMPTION
- Exact technology for containment, evidence protection, and X secrecy is not yet selected.

UNPROVEN
- Actual Windows/IABV enforceability of the resulting containment and evidence boundary.
- Runtime proof that delegated effects are fully captured.
- Runtime proof that X remains inaccessible to the candidate.
- Runtime/implementation proof that evidence cannot be altered by uncontained writers.

## Verdict

RQ21.50 = CLOSED / OWNER RATIFIED.

The normative owner boundary is no longer open.

## Routing

Current first open edge:
owner-ratified R2/R3/R8/R6 → minimal executable substrate contract → independent focused challenge → Codex implementation

NEXT ACTOR: CHATGPT

No Codex implementation yet.
No Devin runtime.
No generic repeat audit.

Implementation proof and runtime proof remain separate.