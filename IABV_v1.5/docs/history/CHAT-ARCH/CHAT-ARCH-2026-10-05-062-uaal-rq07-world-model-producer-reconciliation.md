# CHAT-ARCH-2026-10-05-062 — UAAL-RQ07 World Model Producer Reconciliation

**STATUS:** CANONICAL RECONCILIATION / RUNTIME EVIDENCE BOUNDARY

## RQ07 RESULT

RQ07 started a fresh candidate process and directly attributed the loaded source to the RQ05 candidate worktree.

Observed:
- candidate MCP process PID `16424`;
- `bootstrap.py`, `server.py` and `task_context_assembler.py` loaded from the candidate `src`;
- `cognitive_frame_translate` was registered and its handler was invoked in the same process;
- the handler created a fresh `PerceptionSnapshot`;
- `container.world_model_service is container.task_context_assembler.world_model_service` was verified;
- the tool phase recorded zero `request_refresh` calls;
- World Model identity and several fields propagated into the produced snapshot.

However:
- the MCP World Model snapshot had `last_updated=2026-04-20`, roughly 168.9 days old at the experiment;
- `scan_count=0` and `scan_count_full=0`;
- focused window/active windows were empty;
- World Model metadata identified `/home/ubuntu/repos/Python/IABV_v1.5`;
- Environment Self Model identified the Windows candidate workspace.

Therefore the object consumed by the candidate handler is **not demonstrated to be current Windows environmental state**.

## SOURCE-LEVEL EXPLANATION

Canonical `bootstrap.py` intentionally detects:

`IABV_MCP_SUBPROCESS=1`

and constructs `WorldModelService` with:

`bootstrap_scan = False`

in the MCP subprocess.

`WorldModelService.__init__` initializes:

`_current_snapshot = _load_latest_snapshot() or WorldModelSnapshot()`

and stores the persisted snapshot under:

`<workspace>/data/evolution/world_model/latest.json`.

The source comment explicitly states that the MCP subprocess inherits the persisted snapshot from the main UI process and therefore disables its own aggressive bootstrap scan.

This explains the RQ07 mixture:
- Environment Self Model can observe the current Windows runtime;
- MCP World Model can begin from a persisted snapshot;
- if that persisted snapshot is stale or originated from another environment, the two representations can disagree.

## IMPORTANT CORRECTION

Do not conclude:

`WorldModelService cannot observe Windows`.

The service contains a Windows-capable `_build_snapshot` path that can enumerate windows, focused window, network, tools and other state.

The current issue is instead:

`MCP persisted WorldModel provenance/freshness → current Windows producer handoff`.

This is a **producer/freshness seam**, not a missing World Model implementation.

## RQ07 EPISTEMIC STATUS

**FACT / OBSERVED:**
- fresh candidate process and loaded module provenance were established;
- safe candidate handler invocation occurred;
- PerceptionSnapshot was newly created;
- same WorldModelService instance reached the assembler;
- tool phase produced zero `request_refresh` calls.

**FACT / SOURCE-VERIFIED:**
- MCP subprocess sets `bootstrap_scan=False` for WorldModelService when `IABV_MCP_SUBPROCESS=1`;
- WorldModelService loads the latest persisted snapshot when constructing its current model.

**INFERENCE:**
- the RQ07 stale Linux snapshot is plausibly a persisted artifact inherited from a different environment/workspace rather than a newly produced Windows observation.

**NOT PROVEN:**
- which process last produced that persisted snapshot;
- whether the main IABV Windows UI process currently updates the same `latest.json`;
- whether the MCP snapshot is normally fresh under a healthy main UI producer;
- whether live current Windows WorldModel state reaches PerceptionSnapshot in normal product operation.

## CURRENT FIRST OPEN EDGE

The previous edge:

`candidate runtime → PerceptionSnapshot`

is substantially constrained but not sufficient for live-environment closure.

The first open edge is now:

`CURRENT WINDOWS ENVIRONMENT → live WorldModel producer → persisted/current WorldModel consumed by MCP/PerceptionSnapshot`.

More specifically:

`main UI WorldModel producer → fresh Windows snapshot → persistence/handoff → MCP WorldModel → PerceptionSnapshot`.

## NEXT EXPERIMENT

**TARGET ACTOR: CODEX**

Required capability:
`Windows runtime producer/freshness provenance + WorldModel persistence/handoff verification`.

Minimum experiment should first determine whether a **current Windows producer observation already exists** and whether its snapshot is written to the same candidate `data/evolution/world_model/latest.json`.

If no current Windows snapshot exists, the next experiment must explicitly obtain permission for **one read-only WorldModel scan** (no UI interaction, no clicks, no application changes) and then verify:

1. fresh Windows WorldModel is produced;
2. the snapshot path is the expected candidate path;
3. the persisted `latest.json` is updated with Windows provenance/current values;
4. a fresh MCP subprocess consumes that exact fresh snapshot;
5. `cognitive_frame_translate` builds its PerceptionSnapshot from it.

Do not modify the MCP architecture merely to bypass the producer.

## ROUTING CONSEQUENCE

Do not proceed to:
- external-AI delegation;
- account/login training;
- universal unfamiliar-program interpretation;
- Sonnet independent audit;

until the live WorldModel producer/handoff is understood.

The product target remains:

`HUMAN ↔ IABV`

with external AIs as dynamically selected resources. RQ07 is only a prerequisite for trustworthy live environmental cognition.

