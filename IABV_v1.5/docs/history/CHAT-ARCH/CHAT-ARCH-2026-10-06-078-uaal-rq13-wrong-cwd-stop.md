# CHAT-ARCH-2026-10-06-078 — UAAL-RQ13 WRONG-CWD RUNTIME STOP

## STATUS

CANONICAL RECONCILIATION / RUNTIME STOP / AUTHORIZATION-BOUNDARY CORRECTION

## OBSERVED

Codex launched the RQ13 runtime with process CWD:

`C:\Python\IABV_v1.5`

while the authorized experiment scope required:

`C:\temp\rq13-e46-artifact-ready\IABV_v1.5`

The process did load the four expected RQ13 source modules from the authorized worktree and their in-process SHA-256 fingerprints matched the expected runtime fingerprints. However, the application runtime was launched from the wrong CWD and therefore the run is not attributable as an execution wholly inside the authorized runtime scope.

AppBootstrap started before the process was interrupted. No `current_package(refresh=True)` or `handle_request` was invoked.

## ADJUDICATION

### FACT

- Authorized worktree: `C:\temp\rq13-e46-artifact-ready\IABV_v1.5`.
- Actual runtime CWD: `C:\Python\IABV_v1.5`.
- Expected source files were imported from the authorized worktree and fingerprinted in-process.
- AppBootstrap started with the wrong CWD.
- The process was interrupted before portable-context preconditioning.
- No `handle_request` ran.
- Process exited; PID `4848` no longer running.

### INFERENCE

Source-file provenance is strong for the imported modules but does not erase the CWD scope violation. Runtime state resolution, relative paths, persistence targets and environment-dependent behavior may depend on CWD.

Therefore this run cannot be promoted to a valid RQ13 runtime observation.

### ASSUMPTION

None.

## AUTHORIZATION

Because AppBootstrap actually started in an unauthorized working-directory scope, the runtime authorization for that attempt is considered consumed.

A fresh authorization is required before the corrected launch.

## FIRST OPEN EDGE

`verified artifact receipt → launch process with exact authorized CWD → in-process provenance → normal bootstrap`

Do not advance to portable context or `handle_request` until exact CWD is proven before application initialization.

## METHOD DELTA

For Windows runtime experiments, provenance must include both:

- import/source identity;
- process execution context identity, including exact CWD.

New invariant:

`correct imported source != complete authorized runtime attribution`.

Authorization scope applies to the execution context, not merely to loaded source files.

## ROUTING

**IA DESTINO: CODEX**

Capability: Windows process-launch control, exact CWD enforcement, in-process provenance.

No new static audit. No architecture change.

## NEGATIVE KNOWLEDGE

This episode does not establish:

- bootstrap completion in the authorized CWD;
- portable-context refresh/reuse;
- P0;
- DecisionContext reconstruction;
- comparison/record behavior;
- downstream governance;
- learning or external-AI symbiosis.
