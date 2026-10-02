# IABV v1.5 — CHAT-ARCH-2026-10-02-011
# META-RUNTIME-07ZN — Natural-DEFER Runtime Control Result

## PROVENANCE

Source: user-provided Codex runtime report for `META-RUNTIME-07ZN`.

Technical baseline:
`5238e85c014ea6bdda2ffd1a14064883bde559f5`

Implementation:
`d01b71f9a7f806bf4d2fa031109cdb1b12c733b2`

Remote branch:
`codex/meta-runtime-07zl-natural-defer-20261002`

Execution:
`730c41e8-bb90-480e-8cd5-e2a005b6b030`

## VERDICT

07ZN is **COMPLETED / ENVIRONMENT-BLOCKED FOR NATURAL DEFER**.

The published producer seam remains source-attributable and the isolated CLI persistence remains runtime-proven.

The real launcher received `-StartUI`, but its own resource preflight returned:

`CONTINUE / sufficient_resources`

with approximately 5,115 MB available and 68.2% RAM used.

Therefore the actual DEFER branch did not execute and no natural launcher→persistence causal evidence was produced.

## EXPERIMENTAL CONTROL FINDING

External PowerShell breakpoints were installed before:
- UI `Process.Start`;
- bridge execution.

The breakpoint actions did not terminate the script on this host.

Therefore the breakpoint mechanism is not a valid execution barrier for future experiments on this host.

Method delta:

`breakpoint observed state != breakpoint-enforced stop`.

Do not reuse that control mechanism as causal evidence.

## RUNTIME CONSEQUENCE

The launcher created UI PID 24096 and reached the bridge because the actual decision was CONTINUE.

No pending StartUI task was created.

A pre-launch DEFER observed in a separate resource check is not transferable to the launcher decision because RAM state changed between observations.

The report correctly stopped further attempts rather than artificially increasing memory pressure.

## CURRENT FRONTIER

The only immediate runtime edge remains:

`same real launcher invocation: resource-preflight → DEFER → persistence CLI → singleton task → read-back`.

The source seam itself is already published.

## ROUTING

The next experiment may remain with **Codex**, because it still has exact branch/workspace and Windows runtime access.

However, do not repeat the failed breakpoint approach.

Preferred control:

- external supervisor/watchdog;
- real launcher source unchanged;
- no synthetic DEFER;
- no threshold modification;
- no artificial memory pressure;
- first inspect current real resource state;
- only launch when the actual host is already naturally below the production DEFER threshold;
- observe the launcher's own `resource_gate_result`;
- if DEFER, capture `startui_defer_persistence_succeeded` and read back the singleton;
- if CONTINUE, terminate the launcher externally as early as safely possible and classify the run as non-discriminating.

The external supervisor must not alter the decision inputs.

## WHAT REMAINS UNPROVEN

- natural launcher DEFER;
- actual launcher→persistence causal chain;
- natural repeated-DEFER behavior;
- semantic consumer;
- wake/recheck/reauthorization;
- automatic UI resume;
- learning/future decision change.

END OF RECORD.
