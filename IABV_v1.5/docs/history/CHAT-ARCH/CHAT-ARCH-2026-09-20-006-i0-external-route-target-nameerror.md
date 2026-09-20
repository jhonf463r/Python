# IABV v1.5 — I0 EXTERNAL ROUTE TARGET NAMEERROR

## DATE
2026-09-20

## RESULT

A new runtime interaction produced:

`name 'target' is not defined`

The error is directly explained by the exact implementation at:

`4710a668541225ffe3b9d1335d31bb5da8b1e685`.

## VERIFIED CODE CAUSE

In `LocalRoleRouter.worker_health_gate()`:

- `target_assistant_normalized` is defined;
- the canonical ToolRegistry resolution executes;
- production bootstrap injects a non-null `AccountApprovalLedger` into `LocalRoleRouter`;
- when the ranked list reaches the approval-account path, the method calls:

`self._resolve_approved_account(target_assistant=target, ranked=ranked)`

- `target` is not defined in this method.

The same undefined variable is later referenced by logging in the same block.

Therefore the observed runtime error is a genuine reachable production defect, not merely a report inconsistency.

## CAUSAL INTERPRETATION

The observed chain is:

`external request accepted → worker health / account-approval path → undefined target → NameError → fallback/local continuation`.

The precise external route is therefore **blocked by a runtime code defect before any credential/authentication conclusion can be drawn from this interaction**.

This is separate from the previously observed missing Devin credential.

## PRIOR AUDIT CORRECTION

A prior Sonnet audit had reported that no undefined `target` remained in the bounded I0 router seam. The exact remote read-back of the target revision now contradicts that statement.

The earlier router tests did not exercise the `account_approval_ledger` path strongly enough to expose this reachable defect.

Preserve this as negative knowledge:

`adjacent green router tests ≠ complete production-path coverage`.

## SCOPE

Do not reopen ToolCard/ToolRegistry ownership.

The canonical assistant↔tool/resource-resolution seam remains closed.

Do not yet classify credential availability as the first break for this external-route interaction.

## REQUIRED NEXT ACTION

**DEVIN**: minimal bounded fix of the undefined variable in `worker_health_gate()`, plus a regression test that uses a real/non-null `AccountApprovalLedger` and actually invokes the affected path.

Required behavior should use the already-defined normalized target variable; do not introduce a new authority or mapping.

Then run the narrow runtime path again.

**SONNET**: independent audit of the fix and runtime evidence.

Only after the external-route NameError is removed should the experiment resume the credential/authentication boundary.

## NEGATIVE KNOWLEDGE

Not proven by this incident:

- real Devin credential availability;
- Devin authentication;
- authorization success;
- real external execution;
- I1;
- I2;
- external-world effect;
- verified outcome;
- cognitive influence.

