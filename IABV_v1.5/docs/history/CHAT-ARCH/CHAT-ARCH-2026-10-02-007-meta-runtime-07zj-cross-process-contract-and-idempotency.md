# IABV v1.5 — CHAT-ARCH-2026-10-02-007
# META-RUNTIME-07ZJ — Cross-Process DEFER Persistence Contract and Idempotency Frontier

## PROVENANCE

Source: user-provided Sonnet verification result for META-RUNTIME-07ZJ, independently checked against `5238e85c014ea6bdda2ffd1a14064883bde559f5`.

Technical baseline:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Current canonical parent:
`fa01f5466cea9c5ffb909127cf0dd66e16fc23e6`.

No production code was modified by this verification.

## VERDICT

07ZJ closes the existing-boundary inventory at source level:

- `resource-preflight` is intentionally stateless and should not become a persistence endpoint;
- `app` is full application launch, not an appropriate pending-intent persistence command;
- `cm` controls objectives/decisions and has no pending-task persistence subcommand;
- no existing generic pending-task CLI/API was found in `__main__.py` or `cm`;
- direct PowerShell JSON writing would duplicate Python-side schema ownership.

Therefore the candidate producer seam is:

`start_iabv.ps1`
→ small Python persistence entrypoint
→ `PlatformPendingTask`
→ `PlatformPendingQueue.upsert()`.

This is a **candidate implementation seam**, not yet implementation authorization, because identity/idempotency and exact CLI contract remain open.

## PRIMARY EDGE

`natural StartUI DEFER → durable semantic StartUI intent`

Current status:
**SOURCE-LEVEL SEAM IDENTIFIED / IMPLEMENTATION CONTRACT NOT YET CLOSED**.

## REJECTED OPTIONS

### A — PowerShell serializes queue JSON directly

Rejected because the authoritative `PlatformPendingTask` schema and serialization semantics belong to Python. Direct PowerShell serialization would duplicate schema ownership.

### B — reuse existing pending-task CLI/API

Unavailable in the audited baseline.

### C — add persistence side effects to `resource-preflight`

Rejected because `resource-preflight` is intentionally isolated before application imports and performs observation/policy evaluation only.

### D — add a small Python persistence entrypoint

Currently the only remaining architectural option consistent with:
- single schema authority;
- pure resource-preflight;
- existing `PlatformPendingQueue`;
- no new service/organ.

## EXACT BASELINE CONFIRMATION

The exact `5238e85` `__main__.py` currently exposes only:
- `app`
- `cm`
- `resource-preflight`.

The `resource-preflight` path imports only the resource manager functions, evaluates the RAM policy, prints JSON and returns its status code. It does not construct `AppBootstrap` or import `PlatformPendingQueue`.

## IDENTITY FRONTIER

No existing StartUI/launcher invocation identifier was found that can safely serve as stable pending-intent identity.

`episode_id` exists elsewhere but is semantically bound to captured learning episodes and is not a launcher invocation identity.

Therefore:

`UUID default != idempotent deferred-request identity`.

The implementation contract still needs a policy for whether repeated `StartUI DEFER` observations:
- update one logical pending UI intent,
- or create independent pending intents.

A date+hostname+event hash is **not** accepted as an implementation decision because it can collapse distinct legitimate requests occurring within the same time bucket.

## AUTONOMYCYCLESERVICE

`AutonomyCycleService.startup_summary()` remains a context/backlog reader.

It should not become the semantic owner merely because it already reads the queue.

No evidence requires moving the original DEFER decision from PowerShell into ACS.

## PLATFORMPENDINGTASK

The existing model can carry a descriptive StartUI-defer record without a new schema:
- `id`
- `title`
- `description`
- `reason`
- `status`
- `category`
- `created_at`
- `updated_at`
- `resume_hint`
- `metadata`.

No claim is made that these fields already have StartUI execution semantics.

## FULL GRAPH

`StartUI`
→ resource preflight
→ effective `DEFER`
→ **Python persistence boundary [OPEN]**
→ durable semantic intent
→ semantic consumer [OPEN]
→ wake/trigger [OPEN]
→ fresh resource observation [OPEN]
→ policy recomputation [OPEN]
→ reauthorization [OPEN]
→ existing `start_iabv.ps1` launch authority
→ UI outcome [OPEN].

## ROUTING

Because transport selection is source-reconciled but identity semantics can still change the implementation contract, the next actor should perform a narrow contract/design verification of the identity and persistence-entrypoint choice before implementation.

Selected actor:
**CODEX**

Required capability:
- source/provenance archaeology;
- exact CLI/entrypoint contract validation;
- identity/idempotency semantics;
- no runtime implementation.

After this contract is closed, route to **DEVIN** only for bounded implementation/runtime verification.

## REQUIRED NEXT QUESTION

What is the smallest identity contract that is semantically correct for repeated launcher invocations, while reusing existing state and without inventing a new session/episode domain?

This must be answered before implementing the new Python persistence entrypoint.

## WHAT REMAINS UNPROVEN

- whether one logical StartUI request should map to one singleton pending task or multiple request records;
- exact stable identity strategy;
- exact stdin/argv contract for the new entrypoint;
- runtime persistence from natural DEFER;
- semantic consumer;
- wake/recheck/retry/reauthorization/automatic UI resume;
- cross-AI runtime ingestion and changed next decision.

END OF RECORD.
