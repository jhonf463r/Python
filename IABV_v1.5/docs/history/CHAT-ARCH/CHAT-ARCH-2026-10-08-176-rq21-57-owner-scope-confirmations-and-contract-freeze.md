# CHAT-ARCH-2026-10-08-176 — RQ21.57 OWNER SCOPE CONFIRMATIONS + FINAL MINIMAL CONTRACT FREEZE

## PROVENANCE

Repository: `jhonf463r/Python`.

Verified remote main before this writeback:
`70a2265233a788d91baaff8d997e6f0b4aa652b1`.

Parent canonical records:
- `CHAT-ARCH-2026-10-08-171-rq21-53-owner-authorization-and-minimal-substrate-contract.md`
- `CHAT-ARCH-2026-10-08-172-rq21-54-sonnet-focused-substrate-verification.md`
- `CHAT-ARCH-2026-10-08-175-rq21-56-windows-substrate-research-adjudication.md`

Pinned executable baseline:
`5b1d89022ee4cdc63c1f88e050f086b40a42875c`
Executable tree:
`ed1abcdaa7811582e26d7f5a0e2d7a2e82826b61`

## OWNER DECISION — RECEIVED

The Human Domain Owner explicitly confirmed both remaining RQ21.54 scope points and authorized ChatGPT to reconcile them, freeze the minimal contract and update canonical memory.

### Decision A — R8 partition: ACCEPTED

The confidentiality guarantee for hidden reference criterion `X` is partitioned into:

1. **Substrate guarantees:** prevent candidate access to `X` through substrate-controlled resources and interfaces; protect reads as well as writes; prevent X-derived diagnostics/evidence from leaking X back to the candidate.
2. **Caller/interface obligations:** the caller must not disclose `X` through the prompt, task context, model/session context, logs, side channels, exposed diagnostics, feedback or other candidate-accessible interfaces.
3. **Declared residuals:** model/session memory, external generator state and cross-run adaptive feedback are not automatically protected by a process sandbox. They must be explicitly declared outside the substrate boundary unless brought under enforceable control.

**Failure rule:** any relevant channel that remains unknown, uncovered or not verifiably protected prevents PASS. If confidentiality of X cannot be demonstrated for the claimed scope, result = `NOT VALIDATED`. Partitioning responsibility does not weaken the required predicate.

### Decision B — adversary temporal scope: ACCEPTED

The first guarantee covers the malicious/adversarial candidate, all actors within the authoritative validation boundary, and candidate-controlled/delegated activities throughout the complete validation window.

The observation window may close only after:
- every attributable actor is terminated or demonstrably quiescent;
- delegated/cross-boundary activity is denied or accounted for within the declared boundary;
- the final relevant state is checked;
- terminal evidence is produced and sealed.

A still-active or unaccounted attributable actor prevents closure and therefore prevents PASS.

Post-window activity of a promoted candidate is outside this specific validation window and must be covered by a separate validation or operational control when relevant. This does not retroactively grant trust to the candidate.

## CONTRACT FREEZE

RQ21.57 reconciles the prior owner authorization with RQ21.54 repairs. The minimal bounded contract is now frozen at the normative/scope level.

The substrate must provide all seven owner-authorized guarantees:

1. Effective containment of candidate and attributable effects, including descendants and delegated IPC/loopback/local-service paths.
2. Structured observation of each declared protected effect category/channel in `E`; unknown/uncovered channels cannot support PASS.
3. Evidence custody with authenticated origin and protection of integrity, completeness and non-erasure against actors outside the evidence trust boundary.
4. Hidden custody of `X`, with the R8 substrate/caller/residual partition above.
5. Deterministic comparison of candidate-observed output against reference `X`, where reference truth is fixed outside the realization.
6. Observation closure only after authoritative boundary-membership accounting, quiescence/termination and final-state verification.
7. Evidence binding to exact candidate artifact digest/version, relevant configuration and environment descriptor.

### Evidence authority / PASS contract

- The evidence producer and acceptor are separated.
- The reference truth is fixed outside the candidate realization.
- The acceptor is deterministic and oriented to refutation/authentication.
- Conformance claims cannot be accepted solely because the realization asserts that it is compliant.
- Authenticated origin, completeness, non-erasure, start/terminal records and post-quiescence sealing are distinct evidence requirements.
- Hashing alone does not establish authority or protect evidence from a writer who can rewrite evidence and recompute the hash.
- Lineage follows authoritative validation-boundary membership, not parent PID or timestamp correlation alone.
- The seven guarantees must be demonstrated positively; missing, ambiguous or uncovered evidence yields `NOT VALIDATED`, never PASS-by-omission.

### Threat boundary

The initial guarantee covers a malicious candidate and candidate-controlled/delegated activity during the validation window. Compromise of the OS/kernel trust base or host administrative authority operating outside this boundary remains explicitly out of scope. PASS is conditional on the integrity of the declared trusted base.

### Technology status

The contract does **not** select a technology. Microsoft's `Experimental_CreateProcessInSandbox` APIs remain candidate primitives only. Their presence on the target build and their sufficiency/composition against the seven guarantees remain unproven.

## WHERE THIS CAPABILITY BELONGS IN IABV

This is a **dedicated dynamic-validation task/capability**, not a general mode that should activate for every chat or every tool call.

Machine capability identity:
`capability.sandbox.dynamic_validation`

Task envelope:
- candidate artifact to execute;
- hidden expected behavior/reference `X`;
- declared protected effect set `E`;
- exact candidate/configuration/environment identity;
- declared channels and limitations;
- evidence/acceptance contract.

The existing IABV tool path has `ToolSandbox`, `ToolValidator`, adapters, `ToolTeachService`, `ToolRegistry`, plus partial experimentation infrastructure (`ExperimentLab` / `SandboxExperimentService`). These are reuse/composition candidates, not proof of the full capability.

The audited current code is insufficient:
- `ToolSandbox.run()` forwards a `sandbox=True` flag;
- `ShellToolAdapter` still invokes `subprocess.run(..., shell=True)`;
- `ToolValidator` does not compare against `X` or verify complete protected effects `E`;
- current evidence persistence is not an independent, authenticated completeness/custody mechanism;
- `SandboxExperimentService` is a partial comparator, not the complete containment/evidence substrate.

Therefore the capability is **authorized and contract-defined, but not yet implemented or proven**.

## NEXT OPEN EDGE / ROUTING

RQ21.57 closes the owner-scope/contract-freeze edge. It does not close feasibility or realization.

Next:
1. focused, source-audited feasibility/composition review of the experimental Windows process-sandbox API and existing IABV organs against each of the seven guarantees;
2. if the candidate is relevant, exact-target API availability/behavior check using a proven execution channel, without running a malicious workload merely to test symbol presence;
3. independent verification of the resulting coverage matrix;
4. only then, Codex implementation of the smallest viable bounded substrate if feasible and readiness requirements are met;
5. runtime attack/evidence tests only under the frozen experiment contract and prepared oracle.

Do not rerun generic Deep Research. Do not route directly to implementation. Do not use Devin as a substitute for a source-contract audit; its runtime role is downstream of a precise execution/evidence contract. Do not change the contract merely to match a convenient API.

## EPISTEMIC STATUS

FACT:
- Owner accepted both scope confirmations in the current conversation.
- RQ21.53 authorizes the seven guarantees and first threat boundary.
- RQ21.54 identified the two scope points now resolved by the Owner.
- Current audited code does not demonstrate the complete dynamic-validation predicate.

INFERENCE:
- A bounded new realization substrate remains necessary unless a concrete Windows/IABV composition is positively shown to satisfy all seven guarantees.

UNPROVEN:
- Exact target API availability/behavior on `10.0.26300.0`.
- Complete guarantee coverage by any proposed composition.
- Implementation correctness and runtime evidence.

## DELTAS

Knowledge Delta:
R8 responsibilities and the temporal threat window are now explicitly owner-confirmed. The first normative contract boundary is closed.

Method Delta:
Technology selection must follow an explicit seven-guarantee composition/feasibility audit. Presence of an API, sandbox flag, event stream, signature or hash cannot stand in for end-to-end validation proof.

Routing Delta:
Human Domain Owner is no longer the next actor for these two scope points. The next edge is focused technology/source feasibility, followed by exact-target readiness and independent verification; implementation remains conditional.

END OF RECORD
