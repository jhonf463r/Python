# IABV v1.5 — CHAT-ARCH-2026-10-02-010
# META-RUNTIME-07ZM — Publication and Natural Runtime Boundary

## PROVENANCE

Source: user-provided Codex report for `META-RUNTIME-07ZM`.

Technical baseline:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Implementation:
`d01b71f9a7f806bf4d2fa031109cdb1b12c733b2`

Remote branch:
`codex/meta-runtime-07zl-natural-defer-20261002`

The commit is exactly one commit ahead of the technical baseline and changes only:
- `scripts/start_iabv.ps1`
- `src/iabv_v15/__main__.py`
- `src/iabv_v15/cli/pending_intent_commands.py`
- `tests/test_ui_resource_preflight.py`

## VERDICT

The 07ZL implementation is now **REMOTELY PUBLISHED / SOURCE-ATTRIBUTABLE**.

The direct Windows CLI persistence path is **RUNTIME-PROVEN in isolation**:
`persist-startui-defer → PlatformPendingTask → PlatformPendingQueue.upsert() → read-back`.

The natural launcher causal edge remains **OPEN**.

The attempted real launcher run did receive `-StartUI`, but the launcher itself observed `CONTINUE / sufficient_resources`, so the DEFER branch did not execute.

A prior isolated preflight observation of DEFER is not valid evidence for the launcher decision because resource state changed between observations.

## CONTRACT IMPLEMENTATION STATUS

Implemented:
- dedicated `persist-startui-defer` CLI;
- UTF-8 JSON stdin;
- payload validation;
- singleton `startui_defer_ui`;
- launcher invocation GUID as provenance;
- existing `PlatformPendingTask`;
- existing `PlatformPendingQueue.upsert()`;
- explicit failure exit code;
- `resource-preflight` remains separate.

## NATURAL RUNTIME RESULT

The actual launcher execution:

`start_iabv.ps1 -StartUI -SkipHealthChecks -NoAutoPull`

did not enter DEFER.

Observed launcher preflight:
`CONTINUE / sufficient_resources`.

Therefore:
- no persistence CLI invocation from the DEFER branch;
- no natural pending task creation;
- no natural read-back;
- no causal order proof.

The UI launch observed in this run was therefore unrelated to the pending-intent seam and was not caused by a pending task.

The runtime also exposed that the resource condition can change materially between an isolated preflight and the launcher’s own preflight. This is a temporal-qualification issue, not an implementation defect in the persistence seam.

## CURRENT FRONTIER

`natural StartUI DEFER`
→ `actual launcher DEFER branch`
→ `persist-startui-defer`
→ `singleton pending task`
→ `read-back`.

The source seam is implemented and published; only the natural runtime causal transition remains unproven.

## RESOURCE SAFETY

The host later reached approximately:
`1,788 MB available / 88.9% used`.

The report deliberately did not apply additional artificial memory pressure and did not alter thresholds or source to fabricate DEFER.

This is correct epistemic behavior.

## ROUTING

The next actor remains **Codex** because the exact implementation branch/worktree and Windows runtime context are already available, and the missing information is a narrow runtime observation.

The next experiment should NOT be another full unrestricted launcher attempt.

It should execute the exact published launcher code while using external PowerShell debugging control to:

1. allow the real resource preflight to decide naturally;
2. if it reaches DEFER, observe the persistence path and persisted artifact;
3. prevent UI creation if it reaches CONTINUE;
4. prevent the MCP/Cloudflare bridge from becoming the measured outcome;
5. preserve the exact technical source unchanged.

A debugger breakpoint is an external observation/control mechanism, not a production-source mutation. The result must distinguish:
`natural production branch execution`
from
`synthetic function return manipulation`.

## NEXT OPEN EDGE

`real launcher preflight → actual natural DEFER → actual CLI invocation → persisted singleton → read-back`.

After this edge is proven, the next step is independent Sonnet verification of the published artifact and runtime evidence.

## WHAT REMAINS UNPROVEN

- natural launcher DEFER;
- actual launcher→CLI persistence causality;
- natural repeated-DEFER idempotency;
- semantic consumer;
- wake/recheck;
- reauthorization;
- later UI resume;
- learning/future-decision influence.

END OF RECORD.
