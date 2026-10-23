# UAAL-D018 — Execution-to-Evidence Stage Separation and Projection Observability

- **Date:** 2026-10-23 (America/Bogota)
- **Task:** `UAAL_D018_EXECUTION_TO_EVIDENCE_STAGE_SEPARATION_METHOD_REFINEMENT`
- **Parent concept:** `UAAL-D014 Meta-Method Plasticity / Failure-to-Evolution Loop`
- **Root:** `UAAL-ROOT-001 Universal Adaptive Algorithm`
- **Type:** Documentary method refinement; not a second coordinator or algorithm
- **Trigger:** Repeated TPM preflight receipts reported command success while the useful projected values remained `UNKNOWN`
- **Status:** `DOCUMENTED_METHOD_NOT_RUNTIME_PROVEN`
- **Source baseline:** `9746f70f2fd330e9632c80630a844cdd08eb2bed`
- **Authorization boundary:** Static method/knowledge update only; no new TPM command, local Windows access, product implementation, tests, build, runtime, real transport or release

## 1. North Star and whole-system dependency

The primary outcome remains `GOVERNED_IABV_CODEX_BRIDGE`: an IABV contextual request must use an existing governed dispatch route, receive a correlated Codex response, ingest it safely, persist/reload evidence, and later demonstrate an appropriate decision effect.

The current G1 frontier remains a prerequisite, not a replacement goal:

`Owner authority → authenticated Windows principal → independently trusted issuer credential → exact IABV server-instance binding → independent reader enforcement → authoritative revocation → governed action`.

The TPM query was only a diagnostic subtask in this dependency chain. Its failed projection must not displace the end-to-end goal or trigger another broad trust-bootstrap inventory.

## 2. Evidence and provenance

**OWNER_REPORTED:** The latest preflight receipt says `Get-Tpm` was available and completed with `SUCCESS` exactly once, but `TPM_PRESENT`, `TPM_READY`, `TPM_ENABLED`, `TPM_ACTIVATED`, and `TPM_OWNED` stayed `UNKNOWN`. The recovery check found only the sanitized projection, not the original object/output. EK inspection and chain validation were not run.

**CONFIRMED_BY_SOURCE:** Microsoft documents `Get-Tpm` as returning a `TpmObject` with the named properties ([Get-Tpm](https://learn.microsoft.com/en-us/powershell/module/trustedplatformmodule/get-tpm?view=windowsserver2025-ps)). `Get-TpmEndorsementKeyInfo` returns an endorsement-key object with a manufacturer-certificate collection ([Get-TpmEndorsementKeyInfo](https://learn.microsoft.com/en-us/powershell/module/trustedplatformmodule/get-tpmendorsementkeyinfo)).

**UNRESOLVED:** The actual target-host invocation, executable capture mechanism, original object shape, projection code, JSON transfer layer and actual failure stage were not supplied to the coordinator. No independent Windows-host observation occurred during this review.

This record does not claim the TPM is present or absent, does not claim the root cause has been found, and does not claim runtime learning.

## 3. Failure pattern converted into a general invariant

The repeated failure conflated distinct events:
- a prompt was drafted versus a destination was actually invoked;
- a command returned without error versus its result was retained correctly;
- a source object existed versus requested properties were available;
- properties were read versus a safe projection was constructed;
- the projection was constructed versus it was serialized and transported;
- a receipt existed versus the coordinator independently correlated and reconciled it;
- a document was written versus it was fetched back and later causally reused.

A task name like `RETRY_CAPTURE_FIX` is not evidence that the mechanism changed. Corrective work must name the changed artifact/precondition and specify an observable acceptance test.

**New invariant:** `SUCCESS` is stage-local. It MUST NOT propagate to a later stage unless that later stage has its own evidence.

## 4. Execution-to-evidence state model

| Stage | Required fact | Closure evidence / status |
|---|---|---|
| E0 — Objective/route | Action serves the North Star and current task | Task ID, baseline SHA, expected dependency edge |
| E1 — Authority | Exact action is authorized; exclusions are explicit | Authority source, scope and stop conditions |
| E2 — Destination capability | Real destination and supported invocation route exist | `AVAILABLE / UNAVAILABLE / UNRESOLVED`; a prompt draft proves none |
| E3 — Exact input | Actual script/input/contract is bounded and reproducible | Inline artifact or pinned source, revision/digest when available |
| E4 — Invocation | Intended actor/tool actually ran | `NOT_RUN / ATTEMPTED / CORRELATED`; use host-provided correlation ID if any |
| E5 — Source execution | Source-boundary result/error | `SUCCESS / ERROR / NOT_RUN / UNKNOWN` |
| E6 — Output shape | Count, type and required structure | Sanitized cardinality/type/property-presence metadata |
| E7 — Field projection | Each field extracted safely and with correct type | Per-field `CAPTURED / MISSING / NULL / TYPE_MISMATCH / ACCESS_ERROR / UNKNOWN` |
| E8 — Serialization/transport | Safe projection serialized and reached the coordinator intact | Separate `EMITTED / RECEIVED / CORRELATED / MISSING / INVALID` states |
| E9 — Reconciliation | Receipt matches authorized action/task/schema | Field reconciliation, provenance and verdict |
| E10 — Persistence/fetch-back | Canonical record and route pointers were stored and reread | Commit/ref, changed paths, fetched blobs and read-back result |
| E11 — Causal reuse | A later relevant decision consumes the delta and changes behavior | Later non-identical objective, retrieved record, changed decision and outcome |

A stage may be `NOT_APPLICABLE` only with a reason. A successful stage does not imply the next one succeeded. “Tool says success” cannot close E6–E9; “prompt exists” cannot close E4; “commit succeeded” does not close E10 until fetch-back; saved method text does not close E11.

## 5. Mandatory receipt contract

For consequential structured operations, require a receipt that distinguishes at least:

`TASK / PARENT_TASK / TARGET_CONTEXT / ACTION_AUTHORITY / DESTINATION / INVOCATION_STATUS / INVOCATION_ID_IF_AVAILABLE / CALL_COUNT / SOURCE_RESULT / OUTPUT_COUNT / OBJECT_TYPE / PROJECTION_RESULT / PER_FIELD_CAPTURE_STATE / SERIALIZATION_STATUS / RECEIPT_CORRELATION / SIDE_EFFECTS / STOP_REASON / NEXT_OPEN_EDGE`.

Never invent an invocation ID. If the host does not supply one, use `NOT_AVAILABLE`. If a source object can contain secrets, introspect and project an explicit allowlist; never serialize the full object merely to diagnose it. Raw credentials, secret-bearing objects, private identifiers, raw exception text and non-allowlisted fields are excluded.

For TPM-specific capture, the candidate implementation is documented in the prior [TPM projection-capture static review](./CHAT-ARCH-2026-10-23-M1A-G1-TPM-projection-capture-mechanism-static-review.md). That candidate was **not** executed or integrated.

## 6. State transitions and fail-closed routing

- `NOT_RUN` is not `FAILED`; it means the operation did not occur.
- Source-command `SUCCESS` does not imply `PROJECTION_COMPLETE`.
- Missing, null, mistyped, ambiguous or uncorrelated data is never silently converted to `false` or `true`.
- An AI-reported result remains `OWNER_REPORTED` until correlated to a supported invocation record or independently verifiable artifact.
- Same-route retry is prohibited unless a named precondition or corrective artifact changed, the retry can discriminate the prior failure, authority remains valid, and the attempt budget/receipt/stop criteria are explicit.
- Failure during projection/transport must not trigger a downstream operation such as EK query, write, install, credential creation, tests, build, runtime or release.
- Never bypass a denied permission with another reader or execution channel.
- Keep one active task and one next action. A blocked local operation does not authorize replacing the bridge North Star with an adjacent investigation.

## 7. Multi-perspective causal localization, without parallel brains

For a repeated failure, activate only the perspectives that may change the decision:
1. **Objective/dependency:** which end-to-end edge is blocked?
2. **Authority/governance:** which exact action is authorized?
3. **Executor/capability:** does the destination/session/tool exist and support invocation?
4. **Observation/data:** did the source object exist, and what count/type/field states were present?
5. **Serialization/transport:** did the safe observation survive the return channel?
6. **Coordinator/memory:** was the receipt reconciled, persisted, and fetched back?
7. **Causal learning:** what method delta should change a later decision, and what would prove reuse?

These are viewpoints inside the existing `UAAL-ROOT-001` loop and Development Control Tower, not seven new services, agents, or routers. Apply sparse activation: expand a view only if its evidence could change the next action.

## 8. Acceptance cases

These are **future conformance specifications, not executed tests**.

| ID | Condition | Required disposition |
|---|---|---|
| OBS-01 | Prompt written, destination not invoked | `INVOCATION_STATUS=NOT_RUN`; never claim dispatch |
| OBS-02 | Source command succeeds, projection unknown | Preserve source success and separate incomplete projection |
| OBS-03 | Exactly one object with a Boolean property | `CAPTURED` with actual Boolean type |
| OBS-04 | Property absent | `MISSING`, not false-by-default |
| OBS-05 | Property null | `NULL`; effective value unknown |
| OBS-06 | Property type unexpected | `TYPE_MISMATCH`; no unjustified coercion |
| OBS-07 | Zero/multiple objects when exactly one required | `CARDINALITY_ERROR`; no downstream call |
| OBS-08 | Projection exists but JSON serialization fails | Serialization `ERROR`; no complete receipt claim |
| OBS-09 | JSON emitted but absent from coordinator response | Receipt `MISSING/UNKNOWN`; no fabricated result |
| OBS-10 | Same failing route with no changed precondition | `STOP_NO_REPEAT` |
| OBS-11 | Corrective artifact changes and separate authority exists | One bounded discriminating attempt may be prepared; invocation still needs a supported executor |
| OBS-12 | Commit created but branch/read-back not verified | Persistence `UNVERIFIED` |
| OBS-13 | Record fetched back but no later decision used it | `DOCUMENTED_AND_FETCHED_BACK`; causal reuse `NOT_PROVEN` |

## 9. Knowledge Delta, falsifier and next open edge

**Knowledge Delta:** Route a repeated output failure to the earliest stage whose evidence is missing. This reduces uninformative retries and prevents source-command success from becoming a claim of complete observation. The corrective artifact must be explicit, not implied by a task name or prose.

**Falsifier/refinement condition:** If a future correlated run proves that the source object, typed fields and safe projection were complete, but a downstream transport/sanitization stage replaced values with `UNKNOWN`, relocate the causal diagnosis to that later stage while retaining the stage-separation invariant.

**Next open edge:** Owner decision on one bounded execution using the concrete capture candidate, or closure of the TPM preflight branch. The current authorization covers protocol refinement only and does **not** authorize another TPM invocation.

## 10. Reconciled state

```text
UAAL-D018=DOCUMENTED_METHOD_NOT_RUNTIME_PROVEN
CAPTURE_ROOT_CAUSE=UNRESOLVED
TPM_AVAILABILITY=UNVERIFIED
GOVERNANCE=KEEP_BLOCKED
G1=NOT_ESTABLISHED
BRIDGE=BRIDGE_NOT_READY
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
AUTOMATIC_FOLLOW_ON=FALSE
```
