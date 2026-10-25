# Knowledge Delta — Route-Blockage Generalization, Authorization Drift, and All-or-Nothing Bias

- **Knowledge Delta ID:** `IABV_KD_2026-10-24_ROUTE_GATE_CALIBRATION`
- **Observed:** 2026-10-24, America/Bogota
- **Canonical baseline checked:** `main` at `2d2b25cb81f5acf1dc08afad081d4d4af922abcb`
- **Status:** documentation candidate on `docs/iabv-knowledge-delta-route-gate-calibration-20261024` until adopted on live `main` and fetched back
- **Scope:** coordinator reasoning, task routing, authorization reconciliation, and evidence classification
- **Non-effect:** this record does not change the technical route in `CURRENT-STATE.md`, establish a root, close G1–G3, authorize product implementation, or authorize reads/tests/runtime/transport/deployment/spend.

## 1. What failed in the reasoning

The observed failure was not simply that a trust-root review ended blocked. The coordinator did not reliably keep four distinct questions separate:

1. **What is the canonical project state?** Current routing says the qualifying independent root and bindings are not established, governance stays blocked, protected reads stay fail-closed, product implementation is not authorized, and automatic follow-on is false.
2. **What did a specific attempt prove?** A terminal static review failed to establish a qualifying non-circular root. That does not prove trust assets are absent.
3. **What can a particular route do?** A reader, executor, tool, local checkout, or artifact may be unavailable in one surface. That is a route/capability observation, not proof of global technical absence.
4. **What action is authorized now?** A technically possible action is not automatically an allowed action. Independent work still needs an existing permission or a new, bounded explicit authorization.

The coordinator over-generalized a gate-specific failure into project-wide paralysis, while a later proposed implementation prompt made the opposite error: it asked for source implementation without reconciling the canonical `IMPLEMENTATION=NOT_AUTHORIZED` field. Both errors come from not evaluating scope, dependency, and authorization separately before selecting the next step.

## 2. Case facts and provenance

- **DIRECT_GITHUB:** live `main` was fetched at `2d2b25cb81f5acf1dc08afad081d4d4af922abcb`; the five mandatory canonical front doors were read in order.
- **DIRECT_GITHUB:** the canonical route still says `ACTIVE_TASK=M1A_G1_WAIT_FOR_INDEPENDENT_ROOT_EVIDENCE`, `G1/G2/G3=NOT_ESTABLISHED`, `IMPLEMENTATION=NOT_AUTHORIZED`, `AUTOMATIC_FOLLOW_ON=FALSE`, and to maintain fail-closed pending pre-existing independent-root and mandate evidence.
- **OWNER_REPORTED:** a local-only candidate was described on branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, local HEAD `22042285ffef8f4af819e93b6d4283a936bcfde3`. The GitHub connector did not find that branch or commit on remote GitHub; this corroborates that the change is not canonical, but does not inspect the local working tree.
- **OWNER_REPORTED:** the candidate report described PEM format/base64 checking but no cryptographic signature verification; generated nonce/expiry but no persistent one-time replay consumption; no proven Owner-to-Windows principal binding, protected issuer process/ACL/IPC, or reader enforcement; and tests written but not run. These are reported candidate properties, not independently executed findings.
- **Coordinator error:** the subsequent task prompt requested implementation without reconciling the canonical implementation authorization field. This document explicitly records that as an instruction-routing defect.
- **Not established:** no candidate source behavior, signature validation, replay resistance, OS isolation, protected-reader enforcement, tests, or runtime behavior is treated as verified here.

## 3. Corrected invariant: localize the blocker; never dilute authorization

Use this distinction in every future task:

| Blocker class | What it means | What it does not mean | Safe routing consequence |
|---|---|---|---|
| `AUTHORITY_GATE` | Authority, custodian, mandate, or required identity binding is unestablished. | That assets do not exist, or that every possible task is technically impossible. | Keep protected capability and gate claims blocked. Do not fabricate authority. Work elsewhere only if independently authorized and genuinely useful. |
| `ROUTE_SURFACE_MISMATCH` | The required action is unavailable in the current interface or actor. | Global absence of a file, service, or capability. | Record the exact unavailable route. Do not retry a denied reader or use another route to bypass the denial. Consider another route only if policy permits it and it is not a circumvention. |
| `ACTION_UNEXECUTABLE_NO_EVIDENCE` | The actor cannot perform or verify the requested operation with the current tool/permissions. | A successful or failed technical experiment. | Stop claiming execution; identify the exact missing capability and the closest authorized action. |
| `SOURCE_DEFECT` | Accessible source shows a missing or incorrect implementation mechanism. | Runtime confirmation of the defect or permission to modify code. | Static diagnosis may proceed only within scope; implementation requires authorization; tests/runtime require their own permissions. |
| `EVIDENCE_GAP` | Evidence needed to promote a claim/state is missing. | Proof that the claim is false. | Keep the state `UNKNOWN`, `NOT_ESTABLISHED`, `NOT_INSPECTED`, or `NOT_RUN` as appropriate. |
| `AUTHORIZATION_GAP` | Canonical state does not authorize the proposed action. | Permission implied by technical feasibility, a generic “proceed,” or an unrelated documentation request. | Do not execute or delegate the forbidden action. Ask for new authorization only when the Owner can genuinely change the permission and the route requires it. |

**Core rule:** a hard prerequisite for a protected operation blocks that operation. It does not automatically block documentation, evidence reconciliation, or another workstream; however, those workstreams must each fit the current canonical authorization. “Independent” is not a synonym for “authorized.”

## 4. Mandatory decision algorithm

Before proposing, delegating, or executing a step:

1. **Refresh authority:** fetch live `main`; read the five canonical files in their required order; record the exact `CURRENT-STATE.md` route and authorization fields.
2. **Bind action to state:** name the objective, the precise dependency edge, the action's scope, the performer/tool, and the expected evidence that would change state.
3. **Classify the blocker:** authority vs route/capability vs source defect vs evidence gap vs authorization gap. Do not use a vague label such as “blocked” without naming its object and scope.
4. **Check the negative inference:** ask “What does this result actually prove?” Explicitly reject `route unavailable → asset absent`, `signature valid → signer is authorized Owner`, `PR actor merged → Owner-to-Windows identity bound`, `code written → code executed`, and `tests authored → tests passed`.
5. **Reconcile authorization before handoff:** compare the task's proposed side effects against `IMPLEMENTATION`, `TESTS`, `BUILD`, `RUNTIME`, `REAL_TRANSPORT`, `CREDENTIAL_OR_APP_CREATION`, `PUBLIC_TUNNEL`, `COST_POLICY`, and merge/deployment rules in current state. Do not issue an executable prompt that contradicts those fields. A user's authorization applies only to the stated scope; documentation authorization does not imply product-code authorization.
6. **Choose one bounded action:** if allowed, choose the smallest action that creates discriminating evidence or closes a real dependency. If no safe action is authorized, state the precise missing authorization/evidence and stop—do not invent a work item just to look productive.
7. **Verify the transition:** record what actually happened, what was not run, the source revision, outputs, and what remains unresolved. A candidate branch/PR is not canonical.
8. **Persist and fetch back:** only an authorized and reviewed writeback becomes shared project knowledge after it is adopted on `main` and the exact live bytes/state are fetched back.

## 5. Specific trust-boundary lessons

- A cryptographic signature verification can prove that a signature validates under a public key and message, subject to the algorithm and implementation. It does **not** by itself prove the key belongs to the Owner, that the Owner is the relevant Windows principal, that the key holder has the required mandate, or that the request is bound to the exact MCP server and target.
- A GitHub PR merge actor is repository evidence. It is not a substitute for an independent Owner-to-Windows-principal binding or a protected local issuer.
- Nonce generation is not replay protection. Replay protection needs durable, atomic, one-time consumption and defined behavior for missing/corrupt/rolled-back state; these source claims still require tests and later runtime evidence before being promoted.
- A policy check in a bootstrap helper does not mediate a protected reader unless the reader's actual call path enforces the signed, bounded decision before opening/listing the target. A parallel helper alone does not close the enforcement gap.
- G1, G2 and G3 are separate requirements. A positive G1 candidate cannot imply publisher integrity/revocation (G2), canonical target resolution (G3), or close the eight implementation prerequisites.
- Do not bypass a denied reader. Keep the security boundary intact and make the next authorized step explicit.

## 6. Terminal result scope vs global status

A terminal result is terminal for the task, evidence set and authorization scope that produced it. It must not be silently reused as a conclusion about a broader claim.

Conversely, the coordinator must not use this principle to evade the current router: if `CURRENT-STATE.md` selects waiting and says automatic follow-on is false, the coordinator may not autonomously start unrelated technical work. Only a genuinely new qualifying evidence event or an explicit new Owner decision that changes scope can change the route. This is the balance that was missing: **do not globalize a narrow negative finding, and do not treat a narrow permission as blanket authorization.**

## 7. Required handoff fields when Codex returns

When the next Codex result is provided, do not restart broad research and do not assume its candidate is canonical. Evaluate the result against:

- exact destination/session, repository, branch, base SHA and HEAD;
- clean/dirty worktree and exact changed paths/blob hashes;
- source-diff claims tied to concrete code locations;
- which checks/tests were written vs actually run, exact command and exit/result if run;
- which network/runtime/credential/service/deployment effects actually occurred or were not run;
- cryptographic validation (not just PEM shape), challenge binding, durable replay consumption, rollback/corruption behavior, issuer process boundary and IPC authentication, revocation/expiry;
- enforcement on the protected reader before access, including exact server-resolved target and operation binding;
- G2/G3 behavior remaining fail-closed if either is absent;
- differences from the prior candidate, not just a new attempt number;
- authorization consistency with live `CURRENT-STATE.md`.

Do not mark any gate closed from source intent, a written test, an owner-pasted report, or a branch that is not canonical. Static review should examine the returned delta and exact evidence; do not rerun the entire history.

## 8. Current state and expected behavior

This knowledge delta is a coordinator-reasoning correction only. It does not change the current route:

```text
ACTIVE_TASK=M1A_G1_WAIT_FOR_INDEPENDENT_ROOT_EVIDENCE
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED; G2=NOT_ESTABLISHED; G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION=NOT_AUTHORIZED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=MAINTAIN_FAIL_CLOSED_PENDING_PREEXISTING_INDEPENDENT_ROOT_AND_MANDATE_EVIDENCE
```

The next user-supplied Codex result may be inspected for provenance, exact candidate state, and whether any action exceeded the current authorization. That narrow intake check must not automatically reopen the terminal G1 review, designate a new technical review target, or authorize implementation, tests, transport, or release. A fuller source review requires a scope that is allowed by the live router or a new explicit bounded Owner authorization; it must not be treated as canonical adoption. This document is a durable protocol/memory artifact; it does not automatically train model weights or change the running IABV algorithms.
