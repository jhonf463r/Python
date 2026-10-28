# Continuity algorithms — static wiring and freshness audit

- Date: 2026-10-24, America/Bogota
- Inspected baseline: live main `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`
- Method: bounded GitHub source/code-artifact inspection only
- Status: `STATIC_REVIEW`; no source tests, build, runtime, or live IABV process was executed
- Purpose: assess whether the existing continuity/learning organs are present, connected in source, and demonstrably delivering current task context to external AI sessions

## Executive result

The repository contains and source-wires the principal organs for learning and portable context. The available evidence does **not** establish that the entire end-to-end loop is currently operational or that every external AI receives a fresh, goal-bound briefing automatically.

Three classes of result must remain distinct:

- **Source-present/source-wired:** the code instantiates and passes the relevant objects.
- **Static risk identified:** an observable source ordering or freshness policy can create a stale or misaligned context.
- **Runtime unverified:** whether the active local instance persists and delivers a correct package is not established by this GitHub inspection.

## Source wiring verified in main

### Observation and learning
- `DecisionAuditTrail` in `src/iabv_v15/services/evolution/decision_audit_trail.py` writes decision records to an append-only JSONL file (`record`) and exposes `self_examination_summary()`.
- `AppBootstrap` constructs `OperationalSelfExaminationService` at `bootstrap.py:913`, providing repositories, WorldModel, validation cycle, adaptive weight layer, and token-rotation ledger.
- `AppBootstrap` constructs `PortableContextService` at `bootstrap.py:1083`, injecting the self-examination service, WorldModel, validation cycle, objective repository, and related services.
- `TaskContextAssembler` is constructed at `bootstrap.py:1375` and receives WorldModel, environment self-awareness, validation-cycle and portable-context dependencies.
- `AdaptiveTaskOrchestrator` is constructed at `bootstrap.py:1488` with the task context assembler and learning/governance dependencies.
- `PortableContextService.build_package()` aggregates context, builds an `assistant_brief`, then persists `latest.json`, `latest.md` and history using the configured storage layer.
- `SessionStartBriefingService` is constructed at `bootstrap.py:1142` with the portable-context service. Delivery depends on injected external `session_creator` / `message_sender` callables; Bootstrap supplies these only when the Devin API adapter is present.

These are static source connections, not proof that the active user process executed them successfully.

## Continuity gaps or risks visible in source

### 1. Persisted package freshness can lag the current task
In `infra/mcp/server.py:724-765`, `portable_context_get(refresh=False)` raises the effective age threshold to at least 86,400 seconds (24 hours) and prefers the persisted `latest.json`. The code comment explicitly says this avoids rebuilding with no active `task_context`, which can produce empty sections. It also means a non-refresh read can intentionally return an older package rather than a current, objective-bound package.

This is a trade-off, not automatically a defect: preserving a richer old package is better than returning an empty one, but it does not satisfy a strict freshness/current-objective guarantee. The contract should later expose provenance, age, objective/site identity and refresh/degradation status to the consumer, instead of silently presenting a stale package as current.

### 2. Repository snapshots do not prove current live state
At this baseline, the tracked `data/evolution/portable_context/latest.json` blob `36ea8b5da1a7b981d5c5fb6e6616ec07dcc59b9d` contains `created_at_utc=2026-04-18T16:43:21.614937Z`. The tracked `data/evolution/self_examination/latest.json` blob `a543b448edf57b323fd6a897d8d86ad4c942455f` contains `created_at_utc=2026-04-18T16:43:42.749368Z`.

Those are stale repository artifacts relative to this October baseline. They show that GitHub's committed snapshots may be old if an agent reads them directly; they do **not** prove the live Windows workspace's generated files are equally old. Agents must not substitute these tracked files for fresh live observation without labeling age and provenance.

### 3. Active goal may arrive after initial perception construction
In `services/adaptive/adaptive_task_orchestrator.py`, `_handle_request_body` builds the initial perception/context via `TaskContextAssembler.build_perception_snapshot()` (around lines 1482-1485), then later calls `GoalEngine.attach_session_goal_context()` (around lines 1623-1626). This ordering creates a source-level risk that the first perception snapshot was assembled before the goal materialized in the session. The archive contains previous RQ13 investigations of this exact family of issue; do not restart broad archaeology. Before changing this path, reuse the terminal RQ13 receipts and determine the latest accepted scope/result.

### 4. Briefing support is not universal automatic delivery
`SessionStartBriefingService.build_briefing()` reads the current portable package, while `deliver_to_existing_session()` requires a session id and configured `message_sender`; it returns an explicit unresolved failure when the sender is absent. Bootstrap wires the transport callables only when a Devin API adapter is available. This establishes a supported delivery mechanism for that adapter, not automatic delivery to every AI (Codex, ChatGPT, Claude, etc.) or proof that every new session receives the briefing.

The coordinator's GitHub continuity protocol does provide a durable front door to coding agents through `AGENTS.md`, `CURRENT-STATE.md`, the context index and memory protocol. That is a different delivery channel from IABV's runtime briefing service and must not be conflated with it.

## Required next-stage verification, not executed here

Once the current trust-organ source slice is reviewed and the relevant authorization is available:

1. Inspect runtime-generated package identity, timestamp, active objective/site, unresolved entries, and freshness in the actual Windows workspace—not only Git-tracked artifacts.
2. Verify that the exact objective/task is bound before the first context/perception snapshot, or capture evidence that the accepted design intentionally stages the goal later and downstream consumers re-read it before decisions.
3. Verify the producer → persistence → loader → briefing → actual external session delivery chain for one named destination, with delivery receipt and package ID preserved.
4. Verify stale-package behavior: stale content must be explicitly labeled and must not be mistaken for current goal state.
5. Compare the result with the existing RQ13 terminal receipts; do not repeat the old experiment if the exact scope is already terminal.

These steps need their own bounded authorization and, where execution is necessary, permission for test/runtime observation. No code test or runtime claim is implied by this document.

## Priority and routing interaction

This audit does not replace or reorder the current trust-organ source task. The immediate source task remains `M1A_G1_REGISTER_READ_AUTHORIZATION_IN_APPBOOTSTRAP`. The audit identifies a separate continuity workstream to schedule after that task reaches a reviewed candidate result and its gates/permissions are reconciled.

The purpose is to prevent two opposite errors: declaring the continuity organs functional from class/wiring existence alone, and disregarding existing architecture by inventing another memory/orchestrator. First verify the existing links end-to-end; then repair the smallest proven gap in the owning component.


---

## Supplemental reconciliation — Control Master super-sync source vs persisted backlog (2026-10-28)

- Current verified main at review: `9a8738565ac2d100bcd4af906081c00f3cf15384`.
- Scope: bounded source/backlog reconciliation; no local Windows access, command execution, tests, build, runtime, MCP invocation or product-code modification.
- Status: `SOURCE_STATIC_RECONCILIATION`; live local Control Master state remains `UNKNOWN`.

### Findings

| Area | Live source evidence | Persisted objective/backlog claim | Reconciled status |
|---|---|---|---|
| Digest CLI | `cli/control_master.py` defines `cm export-digest`, supports JSON/Markdown, and defines `set-vision`, `add-objective`, `mark-objective`, `record-decision`, and `mark-unresolved`. `__main__.py` dispatches the `cm` namespace. | `obj-super-sync-cli-export` says the CLI entrypoint is missing and gives the obsolete command `python -m iabv_v15 export-digest`. | The CLI route is present in source. The documented command should be `python -m iabv_v15 cm export-digest --format markdown`. Runtime behavior is `NOT_RUN`; do not mark the objective completed from source presence alone. |
| Write bridge | The CLI exposes write commands which call `ControlMasterService` / `ObjectiveRepository`. | `obj-super-sync-write-bridge` says the CLI write affordance is missing. | CLI affordances exist in source. Whether they are safely and automatically callable by each external AI session, and whether the UI path is complete, remains `UNKNOWN`. |
| Outcome loop | `TaskOutcomeRecorder.record()` persists the session then calls `_propagate_to_control_master()`; `bootstrap.py` injects `control_master_service`. The source test file `tests/test_control_master_outcome_loop.py` specifies terminal-status propagation, unresolved propagation, and recorder resilience. | `obj-super-sync-outcome-loop` says that this wiring is absent. | Wiring and matching tests exist in source. Tests/runtime were not executed in this review; objective completion is not established here. |
| Active Control Master snapshot | Tracked `data/evolution/control_master/latest.json` still lists `obj-super-sync-cli-export`, `obj-super-sync-write-bridge`, and `obj-super-sync-outcome-loop` as active and has no completed objectives. The three tracked objective JSON files retain summaries describing the missing source functions. | Backlog and source disagree. | This is a verified tracked-data/source inconsistency, not proof of what the live local database currently contains. Do not modify objective status by hand or directly through GitHub. |
| Context export side effects | `cmd_export_digest()` calls `_bootstrap()`, which creates `AppBootstrap`. Its constructor calls `_auto_load_secrets()`, loads application configuration, creates workspace directories and configures logging before the export method is called. | The CLI docstring describes use without booting the UI; that does not make the path side-effect-free. | Do not execute the command as if it were a pure/read-only export. Runtime remains `NOT_RUN`. Design a narrower, side-effect-bounded export path before authorizing any invocation from an agent workflow. |
| Cross-agent bridge | The documented Dropbox bridge exists at `/IABV-IA-BRIDGE/`; its observed INBOX/OUTBOX contents are from 2026-10-25/26, with no current 2026-10-28 Control Master handoff in the listed folders. | The vision in tracked `latest.json` expects automatic session-entry reading and structured writeback at session close. | A shared exchange path and historical artifacts exist, but automatic current context injection into every ChatGPT/Codex session and automatic closeout writeback are not established. |

### Source identities fetched from live main

- `src/iabv_v15/cli/control_master.py`: `077557fa07c08d4c00834a03daa5670f97e6bcbd`.
- `src/iabv_v15/__main__.py`: `6710dd5600fbc35c298b88afc83183ef759615ca`.
- `src/iabv_v15/services/adaptive/task_outcome_recorder.py`: `fddf3f90e15b4ec74ad813441ceeac18458e0118`.
- `src/iabv_v15/bootstrap.py`: `e4befa6b683fc87aed7481f377f1332f5753e2c3`.
- `tests/test_control_master_outcome_loop.py`: `ce106628c8a21d750385dc29f71d2fb9ee055c66`.
- `tests/test_control_master_integration.py`: `da023e74bb71518cb1ad9b985724d2cb8874e6cf`.
- `data/evolution/control_master/latest.json`: `d76d521e6f8d73e874a21ffe1b720dcdbcd48293`.
- `data/evolution/objectives/obj-super-sync-cli-export.json`: `f2bd144eef17d25e7e7a14ca79f1ca39bb9e9d38`.
- `data/evolution/objectives/obj-super-sync-write-bridge.json`: `03ca22f21981a3be1fe349ecaaadf73a67edf88f`.
- `data/evolution/objectives/obj-super-sync-outcome-loop.json`: `ea075ba37d4a139e28074b321731f9e722a73ee3`.

### Corrective route

1. Preserve the existing objective IDs and current persisted objective states for now; do not manufacture completion evidence or edit the data files directly around `ControlMasterService`.
2. Prepare a design for a **bounded, side-effect-free Control Master context export** that does not instantiate the full `AppBootstrap`, load credentials/secrets, create directories, start background services, or mutate objective state.
3. Define explicit envelope metadata for source state ID, generation/update time, age/freshness, active objective IDs, objective-source links, unresolved state and provenance. Clearly distinguish source data from derived cache/freshness metadata.
4. Specify an explicit external-agent handoff/acknowledgement and session-close writeback contract. A shared Dropbox folder or CLI alone does not prove every AI session is connected.
5. Only after a separate implementation/runtime authorization, validate the command in the intended local workspace and use the existing Control Master service path to reconcile objective statuses. No status is changed by this static report.

```text
CONTROL_MASTER_CLI=SOURCE_PRESENT; RUNTIME_NOT_RUN
CONTROL_MASTER_WRITE_COMMANDS=SOURCE_PRESENT; UNIVERSAL_EXTERNAL_AI_ACCESS_UNKNOWN
TASK_OUTCOME_LOOP=WIRING_AND_TEST_SOURCE_PRESENT; TESTS_NOT_RUN
TRACKED_OBJECTIVE_SUMMARIES=STALE_VS_SOURCE
LIVE_LOCAL_CONTROL_MASTER_STATE=UNKNOWN
NEXT_ACTION=DESIGN_SIDE_EFFECT_BOUNDED_CONTEXT_EXPORT_AND_EXPLICIT_CROSS_AGENT_HANDOFF
IMPLEMENTATION=NOT_AUTHORIZED
TESTS/BUILD/RUNTIME=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```
