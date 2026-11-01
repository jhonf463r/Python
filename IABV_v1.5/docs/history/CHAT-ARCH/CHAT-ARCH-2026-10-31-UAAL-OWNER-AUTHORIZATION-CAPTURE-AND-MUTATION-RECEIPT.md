# UAAL Owner authorization capture and one-shot mutation receipt

- TASK_ID: UAAL_OWNER_AUTHORIZATION_CAPTURE_SINGLE_USE_MUTATION_R1_20261031
- Date: 2026-10-31 (America/Bogota)
- Parent: UAAL-D019 / UAAL-D020 / UAAL-D021 / Space-Time continuity protocol
- Scope: documentation/control-plane method refinement and one observed GitHub documentation merge.
- Base main: f39daa5231c5c85c83a7545879aa522286525fef
- Authorization: Owner instruction in the coordinating conversation to merge PR #588 by squash and verify the result; followed by a request to evolve the observed coordination method.
- Technical product scope: none.

## 1. Observed coordination episode

The coordinator reviewed PR #588 as a documentation-only proposal and then asked one explicit, fully bounded decision:

- Target: jhonf463r/Python, PR #588.
- Action: merge that PR.
- Method: squash.
- Concurrency pin: expected PR head 4afe1749201175ffc5acfd388f1dd05f2c1e0b07.
- Verification included in the proposal: refresh main, inspect the merged PR, resulting commit and changed file/blob state.
- Scope exclusions: no product implementation, runtime activation, tests/build, permissions or repository-governance changes.

The Owner replied: **“si autorizo”**. That reply had one immediate, unambiguous proposal as its antecedent. It was therefore sufficient authorization for the named PR #588 squash merge and the stated verification envelope—not for any other mutation.

## 2. Preflight and observed outcome

~~~text
PRE_MERGE_MAIN=0037ff4f8a92d779c3b9b015ca94b6a642ecc76e
PR=588
PR_STATE_BEFORE=OPEN
PR_MERGEABLE_BEFORE=TRUE
PR_BASE_BEFORE=0037ff4f8a92d779c3b9b015ca94b6a642ecc76e
PR_HEAD_EXPECTED=4afe1749201175ffc5acfd388f1dd05f2c1e0b07
REPOSITORY_ALLOW_SQUASH_MERGE=TRUE
METHOD=squash
EXPECTED_HEAD_GUARD=PASSED
MERGE_API_RESULT=MERGED
RESULTING_COMMIT=f39daa5231c5c85c83a7545879aa522286525fef
POST_MERGE_MAIN=f39daa5231c5c85c83a7545879aa522286525fef
POST_MERGE_PR_STATE=CLOSED
POST_MERGE_PR_MERGED=TRUE
POSTCONDITION_FETCH_BACK=VERIFIED
~~~

The post-merge fetch confirmed that live refs/heads/main pointed to the resulting commit and PR #588 was closed with merged=true. The four PR paths remained the documented scope. The pre-reviewed CURRENT-STATE.md suffix was preserved by the PR change; the merge did not revise the technical route or its gate status.

## 3. Diagnosis: what was and was not the failure

The previous request for explicit permission before merging was **correct**: preparing/reviewing a PR is not automatically permission to mutate main. It would be unsafe to remove that boundary.

The observed method gap was narrower:

1. Existing continuity rules required bounded Owner authorization but did not provide a sufficiently explicit record for binding an elliptical answer (such as “sí, autorizo”) to its one exact conversational antecedent.
2. The methods did not fully operationalize the lifecycle from approval through live preflight, optimistic-concurrency guard, execution, postcondition fetch-back and single-use consumption.
3. Without a durable event, a later session risks either asking the Owner to repeat an already-resolved decision or incorrectly generalizing it to a different mutation.

The correction is therefore **antecedent binding and authorization continuity**, not weaker authorization.

## 4. Adopted method refinement

A short affirmative answer is reusable only if it directly follows one complete proposal that specifies one target object, one action, method, target revision, verification envelope, explicit exclusions and stop condition, with no competing pending proposal. Otherwise ask one targeted clarification.

The authorization event must record:

~~~text
AUTHORIZATION_ID=
TASK_ID=
OWNER_DECISION_SOURCE_AND_TURN=
PROPOSAL_ANTECEDENT=
OWNER_REPLY_OR_DECISION=
TARGET_OBJECT_AND_REPOSITORY=
TARGET_REF_OR_REVISION=
EXPECTED_BASE_SHA=
EXPECTED_HEAD_SHA=
ACTION_AND_METHOD=
AUTHORIZED_INCLUSIONS=
EXPLICIT_EXCLUSIONS=
EXPECTED_POSTCONDITION=
INVALIDATORS_OR_EXPIRY=
STATUS=PROPOSED | OWNER_AUTHORIZED | PREFLIGHT_PASSED | EXECUTED | POSTCONDITION_VERIFIED | CONSUMED | AMBIGUOUS | STALE | BLOCKED | FAILED | NOT_EXECUTED
AUTHORIZATION_CONSUMED=FALSE | TRUE
EVIDENCE_AND_FETCH_BACK=
~~~

Required transaction:

~~~text
PROPOSED
 -> OWNER_AUTHORIZED
 -> PREFLIGHT_PASSED
 -> EXECUTED
 -> POSTCONDITION_VERIFIED
 -> AUTHORIZATION_CONSUMED
~~~

A moved base/head, target, diff or effect scope invalidates the authorization. Pass an expected SHA/ETag/lease where supported. The grant covers one mutation only. Verification expressly named in the proposal is part of the same bounded transaction. A subsequent action requires its own current authority.

## 5. Cross-document adoption

This revision integrates the same rule into the existing organs; it creates no new coordinator, router or memory store:

- AGENTS.md: activation pointer for the capture rule.
- UAAL-D019: anti-loop handling of explicit and elliptical Owner decisions.
- UAAL-D020: authorization fidelity remains a lexicographic hard gate, never a progress score.
- UAAL-D021: durable authorization event ledger, stale-event guard and handoff/receipt fields.
- CONTINUITY-SPACE-TIME-OPERATING-PROTOCOL-v1: authorization-bound domino transaction and acceptance/falsification cases.
- UAAL-NEW-CHAT-BOOT-AND-HANDOFF-KIT: new-chat resolution rule and receipt/checklist fields.

## 6. Preserved boundaries

~~~text
OPTION_D=RATIFIED_NO_BOOTSTRAP
G1/G2/G3=NOT_ESTABLISHED
G4/G5/G6/G7/G8=OPEN
PROTECTED_READS=FAIL_CLOSED
MCP_TOOL_ALLOWLIST=EMPTY
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_IMPLEMENTATION=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
AUTHORIZATION_TO_MERGE_PR_588=CONSUMED
AUTHORIZATION_TO_MERGE_FUTURE_PRS=NOT_GRANTED
REPOSITORY_GOVERNANCE_CHANGES=NOT_AUTHORIZED
~~~

No product source, local checkout, credential, key, protected store, branch-protection setting, ruleset, permission, test, build, runtime, tunnel or deployment was touched. No private credential or personal data is needed by this method.

## 7. Later acceptance and falsification

This is one observed application plus a documented method update, not proof of causal reuse, automatic enforcement or model-weight learning. A later non-identical task must demonstrate:

1. One unambiguous affirmative confirmation is bound without asking the same question again.
2. A multi-action/ambiguous antecedent is not guessed; one targeted clarification is asked.
3. A changed expected revision invalidates the old event before mutation.
4. API success without authoritative fetch-back is not reported as verified.
5. A consumed authorization is not reused for another PR or side effect.
6. The Owner-input ledger preserves the exact scope and prevents both duplicate questions and authorization expansion.

Revise the method if it suppresses a valid authorization, causes a repeat question despite an available unique antecedent, or allows a stale/overbroad mutation. The later trial—not this document's existence—will establish whether the method was causally reused.
