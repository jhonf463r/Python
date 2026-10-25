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
