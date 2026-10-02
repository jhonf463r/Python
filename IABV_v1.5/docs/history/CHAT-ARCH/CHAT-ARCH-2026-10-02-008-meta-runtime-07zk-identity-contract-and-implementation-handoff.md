# IABV v1.5 — CHAT-ARCH-2026-10-02-008
# META-RUNTIME-07ZK — Identity Contract, Persistence Boundary and Implementation Handoff

## PROVENANCE

Source: user-provided Sonnet report for META-RUNTIME-07ZK.

Technical baseline:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Canonical memory HEAD contrasted by the report:
`d525a50674ea4ca139f4891fad95b2f761e4e004`

Scope: read-only source/contract verification; no runtime and no production modification.

## VERDICT

07ZK closes the contract decision required before implementation.

At `5238e85`:
- `resource-preflight` is intentionally stateless and remains pure observation/policy;
- `app` is full application launch;
- `cm` has no pending-task persistence API;
- direct PowerShell JSON serialization would duplicate Python schema ownership;
- no reusable generic pending-task CLI/API exists.

The smallest remaining composition is:

`start_iabv.ps1 DEFER`
→ dedicated minimal Python persistence entrypoint
→ `PlatformPendingTask`
→ `PlatformPendingQueue.upsert()`.

## IDENTITY CONTRACT

The selected semantic model is:

**one pending StartUI availability intent per queue/workspace**.

This is not one task per launcher invocation.

A launcher invocation should carry a separate `launcher_invocation_id` as provenance/correlation, but that invocation identifier is not the task identity.

The task identity is a stable singleton key for the pending UI-availability intent.

Do NOT use:
- default random UUID as semantic identity;
- PID;
- learning `episode_id`;
- date+hostname hashes;
- other time-bucket identities.

Reason: repeated legitimate requests could duplicate or collide incorrectly.

## IDEMPOTENCY CONTRACT

- First natural DEFER creates the singleton pending intent.
- Retry of persistence for the same invocation uses the same task identity and invocation correlation.
- Another invocation while the UI remains deferred updates the same singleton intent rather than creating another pending UI task.
- Later CONTINUE does not itself resolve the record; resolution belongs to a future semantic consumer that will observe and verify actual UI state.

These are contract rules, not runtime-proven behavior.

## ENTRYPOINT CONTRACT

Recommended entrypoint:

`python -m iabv_v15 persist-startui-defer`

Transport:

UTF-8 JSON over stdin.

The command should:
1. validate input;
2. construct the existing `PlatformPendingTask`;
3. assign the stable singleton task identity;
4. set `category=startui_defer`;
5. set `status=PENDING`;
6. preserve DEFER reason and resource observations in descriptive fields/metadata;
7. call existing `PlatformPendingQueue.upsert()`;
8. return JSON acknowledgement on stdout only after successful persistence;
9. send diagnostics to stderr;
10. return nonzero on validation/storage failure.

It must not construct `AppBootstrap` and must not contaminate `resource-preflight`.

## PAYLOAD

Minimum semantic payload:
- queue/workspace location;
- `launcher_invocation_id`;
- effective `DEFER`;
- `ui_requested=true`;
- UTC timestamp;
- defer reason;
- available resource metrics/thresholds;
- source/origin `start_iabv.ps1`.

Existing `PlatformPendingTask` fields are sufficient; no schema expansion is currently justified.

Do not treat `next_action` as executable.

## OWNERSHIP

- `start_iabv.ps1`: owns StartUI request and effective DEFER.
- Python resource preflight: evaluates and returns policy only.
- persistence entrypoint: transports the already-decided fact to the persistence owner.
- `PlatformPendingQueue`: owns durable storage.
- `AutonomyCycleService.startup_summary()`: remains a generic context reader, not producer owner and not semantic StartUI dispatcher.
- existing `start_iabv.ps1` launch path remains the launch authority.

## CONCURRENCY / ATOMICITY BOUNDARY

`upsert()` replacing the same task ID is not proof of atomicity or safe concurrent writers because the implementation uses file `write_text`.

Implementation must therefore:
- avoid introducing concurrent writers;
- document or preserve current serialization assumptions;
- not claim strong concurrency guarantees without evidence.

Do not redesign the queue in this seam.

## IMPLEMENTATION SCOPE

Expected source changes:
- `src/iabv_v15/__main__.py` for the dedicated command;
- `scripts/start_iabv.ps1` in the natural DEFER branch;
- a small CLI adapter/module if needed;
- existing queue/model only as required to call the existing `upsert()`.

No new persistence service or schema.

## FUTURE OPEN EDGE

After successful natural persistence:

`durable StartUI intent`
→ semantic consumer
→ wake/trigger
→ fresh resource observation
→ policy recomputation
→ reauthorization
→ existing launch authority
→ verified UI outcome.

None of these should be implemented in the current seam.

## ROUTING

The contract is sufficiently closed for a bounded implementation/runtime actor.

Next actor:
**DEVIN**

Required work:
- implement exactly the persistence seam above;
- exercise the natural DEFER path on Windows;
- read back the persisted task;
- prove that repeated DEFER does not create unintended duplicates;
- preserve the existing pure `resource-preflight` path;
- keep the existing UI launch authority unchanged.

After Devin publication/runtime evidence, route to Sonnet for independent verification of coverage, provenance and causal behavior.

## WHAT REMAINS UNPROVEN

- natural runtime persistence from the actual DEFER branch;
- actual stdin/CLI transport behavior under Windows/PowerShell quoting/environment;
- idempotency under real repeated invocations;
- file write failure behavior in the launcher;
- concurrent writer safety;
- semantic consumer;
- wake/recheck/retry/reauthorization;
- automatic UI resume;
- cross-AI runtime ingestion and changed next decision.

END OF RECORD.
