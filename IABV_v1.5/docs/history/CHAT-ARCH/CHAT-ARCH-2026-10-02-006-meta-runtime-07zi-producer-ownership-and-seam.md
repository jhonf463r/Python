# IABV v1.5 — CHAT-ARCH-2026-10-02-006
# META-RUNTIME-07ZI — Natural StartUI DEFER Producer Ownership and Minimum Seam

## PROVENANCE

Source: user-provided Codex forensic/source report for META-RUNTIME-07ZI.

Technical baseline:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Execution type:
static source archaeology; no runtime execution; no production modification.

Canonical parent:
`7145bfe9673612924ac21e586d9e88e89ff843be`.

## VERDICT

07ZI closes the producer-ownership question at source level.

In `5238e85`:

`-StartUI`
→ actual `Invoke-UIResourcePreflight()` call-site
→ Python `resource-preflight`
→ JSON decision
→ PowerShell derives effective `$uiResourceGateDefers`
→ DEFER branch
→ trace/continuation; no queue persistence.

The authoritative component for the effective DEFER state is the PowerShell launcher, not the Python RAM-policy evaluator.

The natural producer is therefore:

`start_iabv.ps1`

and the existing persistence substrate is:

`PlatformPendingQueue.upsert(PlatformPendingTask)`.

There is currently no producer connection between them.

## CURRENT PRODUCER OWNERSHIP

- UI request owner: `start_iabv.ps1` via `$StartUI`.
- Effective DEFER owner: `start_iabv.ps1` after interpreting Python preflight JSON.
- Post-DEFER live process: launcher PowerShell.
- Existing persistent storage owner: `PlatformPendingQueue` in Python.
- `AutonomyCycleService.startup_summary()` remains a context/backlog reader, not semantic owner.
- `PlatformResumeHint` remains checkpoint/context, not a StartUI pending command.

## FIRST OPEN CAUSAL EDGE

`natural StartUI DEFER → durable semantic StartUI intent`.

07ZI narrows this to a cross-process producer seam:

`start_iabv.ps1`
→ existing Python persistence API
→ `PlatformPendingTask`
→ `PlatformPendingQueue.upsert()`.

## EXISTING REPRESENTATION

At the audited baseline, `PlatformPendingTask` already has sufficient generic fields to carry a descriptive StartUI-defer record without introducing a new persistence model:

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

07ZI did NOT establish a new schema.

It also corrected a prior unverified proposal: the identifiers
`requested_action`, `requested_time`, `source_context`, `expires_at`, `cancelled`
are not established fields in the audited contracts and must not be treated as existing.

## IDENTITY / IDEMPOTENCY GAP

The existing queue's default UUID is generated when a `PlatformPendingTask` is constructed.

Therefore:

`UUID default != stable launcher-event identity`.

For safe repeated producer invocation, the implementation contract must decide whether:
- the launcher supplies a stable event/task ID;
- an existing deterministic identity convention can be reused;
- or duplicate insertion is acceptable for the first seam.

07ZI proposed explicit stable identity but did not prove that an existing launcher identity already exists.

This is therefore still a contract question, not yet an implementation fact.

## CROSS-PROCESS BOUNDARY

Existing boundary:

`PowerShell → python -m iabv_v15 resource-preflight → JSON stdout → PowerShell`.

That command currently evaluates RAM/policy and returns JSON. It does not persist pending StartUI intent.

The minimum implementation will necessarily cross or reuse this boundary somehow, but the exact transport mechanism remains to be independently verified before implementation.

## FULL GRAPH

`StartUI → resource preflight → DEFER → durable semantic StartUI intent [OPEN/producer seam]`
→ semantic consumer [open]
→ trigger/wake [open]
→ fresh resource observation [open]
→ policy recomputation [open]
→ reauthorization [open]
→ existing `start_iabv.ps1` launch authority [existing]
→ UI outcome [open].

Only the bold producer seam is in the immediate scope.

## SYMBIOSIS RECONCILIATION

The external-agent result has been converted into:
report → observed source facts → ownership → candidate seam → unresolved contract.

The result is not promoted to implementation truth until independent verification.

GitHub remains the cross-chat canonical continuity substrate; no live IABV runtime ingestion or learning is claimed.

## ROUTING

Next actor by capability-fit:
**SONNET**, for independent contract/ownership verification of the proposed producer seam.

Then, only after Sonnet reconciles the seam:
**DEVIN** for bounded implementation/runtime work if an implementation is justified.

Do not jump directly to Devin from the Codex report.

## REQUIRED NEXT QUESTIONS

1. Is `start_iabv.ps1` conclusively the authoritative producer of the effective DEFER event?
2. Can the existing PowerShell→Python boundary be reused without creating a second ownership model?
3. Is `PlatformPendingTask` semantically adequate for the first producer seam?
4. What is the minimum identity/idempotency contract?
5. Where should the Python persistence entrypoint live, using existing organs only?
6. Can `AutonomyCycleService` be a façade without becoming the owner of the UI decision?
7. What exact code change would be required, without implementing it?

## WHAT REMAINS UNPROVEN

- natural runtime persistence of a StartUI DEFER event;
- existence of a stable pre-existing launcher task identity;
- exact transport/API for PowerShell→Python pending-intent persistence;
- semantic consumer;
- wake/recheck/retry;
- reauthorization;
- automatic UI resume;
- cross-AI runtime ingestion and changed next decision.

END OF RECORD.
