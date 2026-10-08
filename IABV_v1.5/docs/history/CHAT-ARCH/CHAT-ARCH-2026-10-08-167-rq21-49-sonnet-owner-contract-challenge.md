# CHAT-ARCH 2026-10-08-167 — RQ21.49 SONNET 5.5 ADVERSARIAL OWNER-CONTRACT CHALLENGE

## Provenance
Prior canonical documentation main: 0b2b5764787168d6a68a69b5a05343e1b8672ee5
Executable baseline remains 5b1d89022ee4cdc63c1f88e050f086b40a42875c.
Executable tree remains ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61.
Actor: Claude Sonnet 5.5.
Scope: text-only adversarial challenge of the frozen RQ21.48 owner contract; no runtime, no code changes.
Sonnet's local documentation HEAD was 9cc9f1d, therefore its local SHA claim for documentation is UNPROVEN. Remote canonical main had already been verified independently.

## Verdict
RQ21.49 = PASS WITH BOUNDED REPAIRS.

Strongest successful falsification:
a realization could produce PASS-like evidence while merely declaring its own coverage. The contract rejected candidate self-attestation but did not yet prevent the realization from self-declaring the coverage on which its evidence depended. This is circularity.

Other successful or partial falsifications:
1. no positive definition of PASS; failure list alone leaves unspecified failures without a verdict;
2. delegated effects through loopback, IPC, existing local services or UI automation can evade a literal reading of E;
3. temporal window can close before all attributable actors are quiescent;
4. oracle states are not yet an explicit per-category aggregation/acceptance rule;
5. candidate identity is not yet cryptographically bound to the executed artifact;
6. evidence integrity and unlisted host channels remain insufficiently specified.

## Repairs
R1: define PASS positively: containment demonstrated for every declared E category + sufficient protected-effect observation + provenance integrity + X=MATCH; otherwise NOT VALIDATED.
R2: define demonstrated coverage using independent evidence tied to the realization version/configuration and showing claimed controls can actually prevent/observe the relevant effect; this is normative.
R3: define attributable effect and containment boundary, including descendants and external delegation/IPC/loopback, with enforcement outside candidate control; this is normative.
R4: close the observation window only after all attributable actors are terminated/quiescent and final state verification occurs.
R5: define per-event states and per-category verdict/aggregation; distinguish contained, violated and not-covered.
R6: bind evidence to candidate/X/E digests and environment descriptor; evidence integrity against uncontained writers contains a normative component.
R7: closed-world rule: unlisted channels/categories are uncovered; PASS records declared E and non-covered categories.
R8: define deterministic X evaluation with candidate output treated as data; decide whether X must be inaccessible to the candidate; this is normative.

## Owner decisions now open
Only R2, R3 and R8 are explicitly normative in Sonnet's adjudication; R6 also contains a normative integrity requirement.
Primary normative decisions:
R2 — must realization conformance/coverage be demonstrated independently before the realization can claim capability evidence?
R3 — does candidate effect include all descendant effects and delegated IPC/loopback/local-service effects, and is the containment boundary required to be undefeatable by the candidate principal?
R8 — must X be confidential/inaccessible to the candidate, or may the candidate receive X as an input?
Secondary normative clarification:
R6 — how strong must evidence integrity be against writes from executions not subject to the same containment boundary?

## Routing
Current first open causal edge:
owner ratification of R2/R3/R8 (+ R6 integrity boundary) → minimal authorized substrate contract → implementation contract.
Do not send another generic Sonnet/Haiku review before owner closure.
Do not send Codex yet.
Do not choose containment technology yet.

## Epistemic classification
FACT: Sonnet returned PASS WITH BOUNDED REPAIRS and identified the exact successful falsifications and repair set above.
FACT: no runtime or source modifications were made by Sonnet.
INFERENCE: the contract is close enough that owner closure should be the next information-bearing intervention.
UNPROVEN: feasibility of enforcing the four E categories in the actual IABV runtime; integrity of evidence against uncontained writers; exact coverage achievable in the existing Windows substrate.
