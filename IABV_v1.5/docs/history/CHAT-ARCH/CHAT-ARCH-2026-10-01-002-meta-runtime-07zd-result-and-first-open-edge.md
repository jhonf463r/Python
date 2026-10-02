# IABV v1.5 — CHAT-ARCH-2026-10-01-002
# META-RUNTIME-07ZD Result: Persistent Substrate Reconciled and First Open Causal Edge Identified

## PROVENANCE

Source:
User-uploaded file `Se ha pegado el markdown(20261002-030235).md` containing the Codex response to `META-RUNTIME-07ZD`.

Relation:
This is the evidence-bearing follow-up to `CHAT-ARCH-2026-10-01-001-meta-runtime-continuity-and-causal-verification.md`.

Current canonical base at absorption:
`main@23dc0c73843677a94362363bba98a6685a784e21`.

Codex audited:
production code `5238e85c014ea6bdda2ffd1a14064883bde559f5`;
checkout `4fda92ab0a96d38e637b6581d9fc5f35e53d49f2`;
the latter differs only by the prior test correction.

Codex made no source changes and did not execute IABV.

## 1. VERDICT

`META-RUNTIME-07ZD = COMPLETED / STATIC FORENSIC RECONCILIATION`.

The audit confirms:

`generic persistence exists`

but:

`StartUI DEFER` does **not** write a pending UI task or `PlatformResumeHint`.

No complete chain exists in `5238e85...`:

`DEFER → consumable intent → wake → fresh RAM observation → CONTINUE → UI launch`.

The first open causal edge is:

`StartUI DEFER → PlatformPendingQueue.upsert()`

**with explicit semantics of a UI launch request**.

After that producer edge, additional open edges remain:

`consumer → trigger → fresh observation → policy recomputation → reauthorization → existing launch authority`.

This supersedes the previous status `07ZD = PENDING`, while preserving all earlier closed and negative knowledge.

## 2. WHAT THE AUDIT CLOSED

### 2.1 Generic persistence is real

`PlatformPendingQueue` persists `PlatformPendingTask` as JSON under:

`data/evolution/platform_pending/`

and persists `PlatformResumeHint` under resume-hint storage.

The data survives the process that wrote it.

Therefore the previous formulation:

`no persistence exists`

is incorrect and must never be reused.

The correct formulation is:

> persistence exists, but no semantically defined pending StartUI command is currently produced by the launcher.

### 2.2 Existing consumers are contextual, not executable UI resumers

`PlatformPendingQueue` is written by existing autonomy/bootstrap/MCP flows for backlog findings, permissions, capabilities and related pending work.

`list_actionable()` and resume-hint readers feed startup summaries, incident/context capture and later task/session context.

`PlatformResumeHint` is produced by `TaskOutcomeRecorder` / `AutonomyCycleService` for interrupted or failed adaptive sessions.

No inspected consumer turns these records into a new ControlCenter launch.

Therefore:

`persisted pending state ≠ executable continuation`.

### 2.3 startup_summary() is read/context delivery

`startup_summary()` reads tasks and hints and returns a structured summary.

Its inspected productive consumers:
- write/log the information;
- return it through MCP informational status;
- allow `AdaptiveTaskOrchestrator` to load resume context into a later task/session.

There is no demonstrated path:

`startup_summary() → RAM recheck → StartUI decision → Process.Start`.

Therefore:

`startup_summary() ≠ resume executor`.

### 2.4 StartUI telemetry is not a command

`startup_ui_presence.jsonl` persistently records the UI request/gate result.

OSES reads that file for port-conflict analysis and does not consume `ui_not_started` as a launch instruction.

Therefore:

`telemetry ≠ pending command`.

## 3. PROCESS-LIFETIME RECONCILIATION

`start_iabv.ps1` does not terminate immediately after `DEFER`; it proceeds synchronously to the bridge path.

The bridge starts MCP and keeps Cloudflare in the foreground until its lifecycle ends, after which cleanup stops the MCP child.

However, this temporary process lifetime does not establish continuity because no surviving component:
- owns a durable StartUI intent;
- periodically rechecks the UI RAM gate;
- reacts to resource recovery;
- reauthorizes launch;
- re-enters the existing launch authority.

Static conclusion:

`process survives temporarily ≠ intent ownership ≠ wake ≠ resume`.

No live process observation was performed by Codex in 07ZD.

## 4. RESOURCE OBSERVATION RECONCILIATION

`resource-preflight` is an invocation-scoped observation/policy step.

`BackgroundResourceMonitor` is defined and can sample periodically if instantiated, but no productive instantiation/call into a UI-resume path was found in the audited source.

Bootstrap refresh and Qt timers belong to an already running UI/bootstrap lifecycle.

Therefore:

`observer definition ≠ active monitor ≠ wake`

and:

`resource refresh ≠ deferred-UI continuation`.

## 5. EXISTING LAUNCH AUTHORITY

The established authority remains:

`start_iabv.ps1`

with:

`UI instance detection → bridge ownership checks → Process.Start(... -m iabv_v15 app)`.

MCP has demonstrated existing-UI state/bridge operations, not a replacement UI-creation authority.

Architectural preservation rule:

> Do not introduce a second UI launch authority merely to solve continuity.

## 6. EXACT COMPOSITION STATUS

The strongest existing composition found by 07ZD is:

`existing autonomy/capability work → PlatformPendingQueue / PlatformResumeHint → startup_summary / MCP / task context`

This composes **contextual persistence and delivery**.

It does **not** compose:

`StartUI DEFER → durable UI intent → wake → fresh resource check → policy decision → UI launch`.

The negative graph is:

`start_iabv.ps1 obtains DEFER`

[
ightarrow 	ext{audit trace only}
]

[
-Xightarrow PlatformPendingQueue.upsert(UI intent)
]

[
-Xightarrow resource-triggered consumer
]

[
-Xightarrow post-DEFER preflight/policy
]

[
-Xightarrow existing Process.Start launch authority
]

## 7. CAPABILITY MATRIX

| Capability | Status | Evidence boundary |
|---|---|---|
| Generic pending-task persistence | EXISTS / REUSABLE | JSON durable queue |
| Resume-hint persistence | EXISTS / REUSABLE | JSON checkpoint/context |
| StartUI DEFER telemetry | EXISTS | startup trace |
| Semantic pending StartUI intent | NOT-PRESENT / NOT-PROVEN | launcher does not enqueue one |
| Consumer that executes pending UI | NOT-PRESENT | consumers provide summaries/context |
| Resource wake on recovery | NOT-PRESENT | no connected trigger |
| Post-DEFER fresh RAM recheck | NOT-PRESENT | only new invocation rechecks |
| Post-DEFER policy recomputation | NOT-PRESENT | no connected consumer |
| Automatic reauthorization | NOT-PRESENT | no decision path |
| Automatic UI resume | NOT-PRESENT | no re-entry after DEFER |
| Existing UI protection | WIRED | launcher instance detection/bridge ownership |
| Existing UI launch authority | WIRED | `start_iabv.ps1` / `Process.Start` |

## 8. FIRST OPEN CAUSAL EDGE

The first open edge is now precisely established:

[
oxed{	exttt{StartUI DEFER → durable, semantically defined UI launch request}}
]

The requested reusable substrate already exists.

The missing responsibility is **not** a generic persistence organ.

The missing responsibility is the semantic production of a pending UI intent and, subsequently, its consumer/trigger chain.

Minimum conceptual seam:

`existing StartUI owner`

[
downarrow
]

`PlatformPendingQueue.upsert(StartUI intent)`

[
downarrow
]

`future consumer/trigger`

[
downarrow
]

`fresh resource observation + policy`

[
downarrow
]

`existing start_iabv.ps1 launch authority`.

07ZD explicitly does not justify selecting a scheduler implementation yet.

## 9. KNOWLEDGE DELTA

### Method Delta — CLOSED

Static forensics must answer WHO WRITES / WHO READS / WHAT CONSUMES / WHAT EFFECT follows before calling a persistent object an executor.

### Architecture Delta — CLOSED AT SOURCE LEVEL

IABV already has reusable persistence and resume-context infrastructure.

The absence is narrower than “no persistence”:

`missing semantic StartUI pending-intent producer`

plus later missing trigger/recheck/launch edges.

### Temporal Continuity Delta — CLOSED AT STATIC COMPOSITION LEVEL

The audited composition has no automatic:

`DEFER → wake → reobserve → reauthorize → launch`.

### Negative Knowledge Delta — CLOSED

Do not count:
- `startup_ui_presence.jsonl` as executable intent;
- `PlatformResumeHint` as a UI command;
- `startup_summary()` as an executor;
- `BackgroundResourceMonitor` as active;
- temporary MCP/bridge process lifetime as a wake actor;
- Windows backlog entries as implemented scheduler/autostart capability.

### Routing Delta — OPEN

The next actor must now be selected from the **specific first missing edge**, not from the historical 07ZD actor assignment.

## 10. WHAT REMAINS OPEN

After the first producer edge, the following have not been demonstrated:

1. a productive consumer of the pending UI request;
2. a trigger/wake that invokes it after the resource state changes;
3. a fresh resource observation;
4. policy recomputation;
5. safe re-entry into the existing launch authority;
6. duplicate/UI-instance protection under the resumed path;
7. runtime causal verification across the full chain.

The 07ZD report is static evidence only. It does not prove these future edges at runtime.

## 11. REQUIRED NEXT ROUTING LOGIC

The next action must be derived as:

`first open edge → capability required → actor fit → minimum discriminating experiment`.

The first open edge is now sufficiently concrete that the next actor is **not automatically Codex** and is **not automatically Devin**.

Candidate routing questions for reconciliation:

- If the needed capability is implementation of a minimal existing-organ seam, an implementation/runtime actor may fit.
- If the seam's semantic contract is still ambiguous, an independent contract/architecture actor should adjudicate first.
- If the implementation is trivial but the key risk is causal runtime proof, separate implementation from independent verification.

No actor is selected by this absorption record itself.

## 12. BUILD RESTRAINT

Do not add:
- generic persistence manager;
- generic scheduler;
- `ResourceGuardian`;
- `UIResumeService`;
- duplicate launcher authority;
- broad orchestration/state-machine layer.

First implement/prove only the minimum responsibility supported by the reconciled contract.

## 13. CURRENT FRONTIER

`StartUI DEFER`

→ **durable semantic UI intent**

→ consumer

→ trigger/wake

→ fresh resource observation

→ policy recomputation

→ reauthorization

→ existing launch authority

→ safe UI outcome

The first open causal edge is the bolded one above.

## 14. STATUS

`META-RUNTIME-07ZD = CLOSED / RESULT RECONCILED`.

It is closed as a **static forensic question**.

It does not close the larger UI temporal-continuity objective.

The next material action must start from the first missing producer edge, not repeat 07ZD.

END OF RECORD
