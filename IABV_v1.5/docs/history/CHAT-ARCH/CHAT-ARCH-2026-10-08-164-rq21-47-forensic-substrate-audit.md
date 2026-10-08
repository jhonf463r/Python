# CHAT-ARCH 2026-10-08-164 — RQ21.47 FORENSIC REALIZATION-SUBSTRATE AUDIT

## Result
RQ21.47 = **CLOSED-C / BOUNDED NEW SUBSTRATE REQUIRED**.

Independent Sonnet/Claude audit confirms Codex's RQ21.46 stop condition was valid in essence. Partial reusable infrastructure exists, especially for comparison/transport, but no current executable mechanism closes the complete dynamic-validation predicate.

Closed capability remains `capability.sandbox.dynamic_validation`. The capability meaning, E/X semantics and dedicated validation-step boundary remain unchanged.

## Provenance
Auditor report:
- baseline `5b1d89022ee4cdc63c1f88e050f086b40a42875c`;
- tree `ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`;
- static `git show` / `git grep`;
- no source modification;
- no IABV execution;
- no runtime evidence.

The auditor's local clone could not resolve documentation main `0e482b45…`, but independent remote verification establishes current GitHub main as `0e482b458f5f7ca40d214d1623644444ae732b72`. The executable source remains identical to the pinned baseline. This is a clone-freshness/provenance discrepancy, not demonstrated executable divergence.

## Current executable findings
Containment remains insufficient:
- `ToolSandbox.run()` passes `sandbox=True` without changing execution semantics.
- `ShellToolAdapter.run()` still executes `subprocess.run(..., shell=True)`; `BLOCKED_TOKENS` is textual policy, not containment.
- `AiderToolAdapter` substitutes `aider --version`.
- `PlaywrightToolAdapter` performs the same task actions.
- MCP/Devin sandbox branches abstain/simulate rather than contain an arbitrary candidate.
- No current own-code OS containment primitive was identified in the audited scope.

Protected-effect observation E is insufficient:
`ExecutionState` contains booleans/metadata only; no structured oracle records attempted/allowed/occurred/absent protected effects. No network/process effect oracle was established.

X validation is insufficient:
`ToolValidator` does not consume `expected_outcome` or `expected_signal` as the behavioral predicate. `ExperimentLab` is current and reusable only as a partial textual comparator; it is not a structured E/X validator and is not on the normal sandbox path.

Historical authority/trusted-execution artifacts are **HISTORICAL ONLY** on the audited baseline. `ExternalActionAuthorization` and `ToolApprovalPolicy` are current but insufficient because authorization/policy is not containment or effect observation.

## Adjudication
**C — partial reusable infrastructure + genuinely missing bounded substrate.**

Why not B: no composition of current pieces closes:
`effective containment of E → observation of E → comparison against X`.

The missing substrate is not the whole routing architecture.

## Minimum realization gap
1. Effective candidate containment that materially restricts the protected effect set E during dynamic execution, at least across the filesystem/network/child-process boundaries defined by the owner-approved envelope.
2. Protected-effect observation producing structured attributable evidence of attempted, allowed, occurred and absent effects.
3. Structured X validation with provenance; existing `ExperimentLab` may be reused as a comparator component where semantically appropriate, but is not complete capability proof.

## Owner authorization boundary
Explicit owner/domain authorization is required before introducing the new containment/security substrate because it determines:
- protected-effect scope E;
- threat model;
- minimum isolation guarantees;
- relevant filesystem/network/process-child boundaries;
- evidence/oracle contract required for valid capability realization.

Technology choice follows that normative decision.

## Epistemic status
**FACT:** current ToolSandbox/Shell/Validator behavior is insufficient; ExperimentLab is current but partial; historical authority implementations do not survive as current executable source in the audited baseline; no implementation/runtime occurred.

**INFERENCE:** a bounded new realization substrate is required.

**UNPROVEN:** exact technology, exact E taxonomy/oracle instrumentation, owner-approved threat model, runtime containment, actual capability evidence.

## Method Delta
Add:
`implementation stop due to substrate contradiction → independent forensic reuse audit → owner authorization when a new containment/security boundary is required`.

Preserve:
`partial reusable comparator ≠ complete realization`.

## Routing Delta
Current first open edge:
`bounded containment/effect-observation gap → owner authorization / realization contract → minimal substrate design → implementation`

**NEXT ACTOR: CHATGPT / HUMAN DOMAIN OWNER**

Next task: **RQ21.48 — owner decision on the bounded realization-substrate contract.**

No Codex implementation yet. No Devin runtime. No semantic capability reopening.
