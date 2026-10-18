# CHAT-ARCH 2026-10-17 — Targeted evidence result for discovery ↔ sync-pulse

- **Mission:** `R10_SYNC_PULSE_TARGETED_BRIDGE_EVIDENCE_READ_ONLY_2026-10-17`
- **Codex local disposition:** `BRIDGE_NOT_FOUND_IN_BOUNDED_SCOPE`, scoped to the absence of a direct typed adapter from an individual `ToolEvolutionProposal` / `validate_discovery` result to an individual `solution_proposals` item.
- **Review status:** targeted evidence now supplied for the five groups Claude requested. A final adversarial adjudication by Claude Web is still needed.
- **Provenance:** source excerpts and local checkout details in this record are `CODEX_LOCAL_REPORTED / OWNER_REPORTED`; they have not been independently verified against the Windows checkout by this writeback.
- **Governance:** `GOVERNANCE = KEEP_BLOCKED`.

## 1. Checkout and preservation as reported

Codex reported identical start/end identity:
- Root: `C:/temp/IABV_coordination_20261016`
- Branch: `codex/iabv-agent-coordination-20261016`
- HEAD: `3926b1144bb23c1066db579da711d3cdbc1611df`
- Tracked modified paths: 100 at start and end.
- `git diff --name-only`: 100 at start and end.

No untracked paths were enumerated and `data/`/SQLite were not inspected. Preservation of excluded untracked paths was therefore not materially verified.

## 2. E1 — Search protocol and limits

Codex reports that the original mission record contains `rg` searches over `IABV_v1.5/src` and `IABV_v1.5/tests`, excluding `data/`, SQLite databases and JSONL. Reported patterns included `solution_proposals`, `ToolEvolutionStatus`, `ToolEvolutionProposal`, `validate_discovery`, `_sync_pulse`, `_maybe_auto_execute_proposals` and `auto_execute_from_sync_pulse`, plus contextual `rg -n -C` reads on relevant files.

The targeted follow-up added bounded, tracked-file reads of OSES and the relevant route/sandbox/model methods, plus `git diff` hunk review. Codex explicitly cannot claim commands that are absent from the original record. The search did not inspect untracked source paths and does not exclude every possible adapter outside the searched tracked source/test scope. Therefore the negative conclusion must stay scope-bounded.

## 3. Route A — discovery identity reaches persisted ExperimentRun

Codex reports the following working-tree route:

```text
ToolDiscoveryService._signal_for_card
  → ToolDiscoverySignal
  → ToolEvolutionMonitor._proposal_from_discovery_signal
  → ToolEvolutionStatus.proposals
  → AutonomousValidationCycleService.run_once
  → _recommendation_from_proposal
  → SandboxExperimentService.validate_recommendation
  → ExperimentLab.record_outcome
  → ExperimentRun
```

Reported edge evidence:

| Edge | Local file/method/range reported | Fields / interpretation | Label and limit |
|---|---|---|---|
| Signal → proposal | `tool_evolution_monitor.py:_proposal_from_discovery_signal:716–720`; model `models.py:2156` | `signal.signal_id → discovery_signal_id`; `signal.tool_id → original_candidate_tool_id`; proposal key copied; `proposal_id` remains a distinct generated proposal identifier. | `WORKTREE_SOURCE`; reported local source, not independently reviewed here. |
| Proposal → recommendation | `autonomous_validation_cycle.py:_recommendation_from_proposal:1478–1490` | Carries `proposal_id`, `discovery_signal_id`, original tool, domain/subject, and `evidence_refs` as `supporting_run_ids`. | `WORKTREE_SOURCE`; references are strings and their namespace semantics are not proved by this conversion alone. |
| Recommendation → sandbox record | `sandbox_experiment_service.py:validate_recommendation:88–110` | Propagates recommendation/proposal/signal/original-tool fields; `evaluated_candidate_tool_id=None`. | `WORKTREE_SOURCE`; the evaluated ToolCard identity is not authoritatively established here. |
| Sandbox → run | `sandbox_experiment_service.py:_record_sandbox_run:127–171`; `experiment_lab.py:record_outcome:229–269`; `models.py:ExperimentRun:2041–2058` | Persists `experiment_id`, `recommendation_id`, `proposal_id`, `discovery_signal_id`, original/evaluated tool IDs and metadata. The run's `candidate_id` is assigned the sandbox experiment ID; evaluated tool ID is null in this construction. | `WORKTREE_SOURCE`; identity fields are reported present in the persisted model path, but no runtime persistence test was run. |

## 4. Route B — OSES aggregates runs and builds solution proposals

Reported pathway:

```text
recent ExperimentRun records
  → OSES._recent_experiment_runs
  → OSES._solution_proposals
  → SelfExaminationSnapshot.metadata["solution_proposals"]
  → self_examination/latest.json
  → sync-pulse projection
  → actionable filters
  → _maybe_auto_execute_proposals
  → AdaptiveTaskOrchestrator.auto_execute_from_sync_pulse
  → static call site: AutonomousEvolutionService.plan_or_execute
```

### Runs read by OSES

At `operational_self_examination_service.py:_recent_experiment_runs:1317–1324`, the reported implementation reads up to 60 recent runs through `list_runs(limit=60)`; no filter for `proposal_id`, `discovery_signal_id`, domain or provenance was observed in this method. That proves neither which records enter a given runtime window nor whether any specific discovery run is present.

### Proposal keys and ordinary aggregate references

At `_solution_proposals:5562–5587`, reported route-substitution and collaborative-execution proposals aggregate by values including route, assistant kind and configuration signature, and use success/failure counts by assistant. Proposal keys are constructed semantically, for example:

- `route_substitution:{failing_kind}:{best_alt}`
- `collaborative_execution:{primary_kind}:{secondary_kind}`

The calculation uses recommendation type / assistant identities, not the `ToolEvolutionProposal.proposal_key` from Route A. The ordinary route/collaboration `evidence_refs` are summary/count strings, not direct proposal/signal IDs.

### Important unresolved nuance: validated-collaboration references

Codex reports that `_validated_improvements` and the `validated_collaboration` proposal branch can carry run/experiment reference strings derived from:
- `recommendation.supporting_run_ids`
- `validation.last_experiment_id`
- `best_run.run_id`

Relevant reported ranges: `_validated_improvements:4478–4507, 4510–4534, 4536–4562`; `_solution_proposals:5670–5695`.

This finding means it would be too broad to claim that all run identity vanishes at OSES aggregation. Some validated-collaboration variants may preserve an individual run or experiment reference. The bounded report does **not** establish whether each reference uses the exact identifier namespace of `ExperimentRun`, whether it resolves to a run from the discovery Route A, or whether that run's `proposal_id` / `discovery_signal_id` can thereby be recovered. No direct assignment of those proposal/signal IDs into the OSES `evidence_refs` strings was found. This is a specific question for adversarial adjudication, not grounds to assume a working two-hop mapping.

The snapshot is reported serialized with `model_dump` at `build_review:911–931` and persisted around `1236–1252`. The generated artifact itself was not inspected.

## 5. Sync-pulse projection and matching

At `autonomous_validation_cycle.py:_sync_pulse:580–597`, the reported projection copies `type`, `title`, `action_plan`, `estimated_confidence`, and derives `primary_ia` / `secondary_ia` from the plan. It drops `proposal_key`, `evidence_refs` and any proposal/signal IDs not explicitly copied.

At `_sync_pulse:609–642`, reported actionable classification applies confidence (initial threshold `>= 0.5`), primary-assistant availability, at least two available assistants and pressure-dependent constraints. These are coordination filters, not provenance/identity validation.

At `_maybe_auto_execute_proposals:803–820`, auto-execution selection requires `action_ready`, an available orchestrator, confidence `>= 0.6`, title absent from `_auto_executed_keys`, and a callable method. Deduplication is by title in memory, not a stable proposal ID. Title coincidence would be a textual overlap only, not evidence of individual discovery attribution. The report does not establish that any specific Route A proposal and any OSES proposal actually share a title.

## 6. Orchestrator call-site boundary

At `adaptive_task_orchestrator.py:auto_execute_from_sync_pulse:1147–1182`, the reported payload maps `title → user_goal`, `primary_ia → assistant_kind`, and uses `type`/`title` in metadata with source `auto_execute_from_sync_pulse`. It contains a static call site to `plan_or_execute()`.

The method requires an evolution service, confidence `>= 0.6`, and non-empty `primary_ia`; it calls `worker_health_gate` and obtains a result/email, but the reported code does not use that result to block the call. This is a call-site observation only. It does not demonstrate invocation, effective authorization, actual dispatch, successful outcome, or postcondition verification. The body of `plan_or_execute()` was not inspected.

## 7. HEAD versus worktree classification

Codex reports OSES is not modified in the inspected diff and classifies its source as `HEAD_SOURCE`. Models, monitor, discovery service, validation cycle, sandbox, ExperimentLab and orchestrator have relevant working-tree hunks and are classified `WORKTREE_SOURCE`. The reported local diff review was focused on relevant hunks, not a full adjudication of all 100 modified paths.

The public baseline `9e0ce66768aedd7422e0d3551affd398f44a7532` is not interchangeable with local HEAD `3926b1144bb23c1066db579da711d3cdbc1611df`. Previous public source checks covered Route B files only, not these Route A working-tree edges.

## 8. Bounded conclusion and open question for Claude

The following statement is supported within the searched tracked source/test scope:

> No direct typed adapter was found that passes an individual `ToolEvolutionProposal` or `validate_discovery` result into an individual sync-pulse `solution_proposals` item. Run outcomes from sandbox may influence OSES proposal generation indirectly through assistant-level aggregates. Sync-pulse's reported projection drops proposal keys, evidence references and individual IDs.

The conclusion must retain these limits:

1. The search did not inspect untracked source files or every repository path.
2. Some `validated_collaboration` outputs may preserve run/experiment references in `evidence_refs`; whether those references form a resolvable two-hop link through `ExperimentRun.proposal_id` / `discovery_signal_id` remains unverified.
3. A static title match or aggregate assistant score does not establish proposal-level causality.
4. The `plan_or_execute()` call site does not prove execution or authorization.
5. F-04/F-09 from the separate Slice A review remain open; this trace is not evidence that they are resolved.

**Question for Claude Web:** Given these targeted excerpts and limitations, is `TRACE_ACCEPTED_WITH_LIMITATIONS` warranted for the narrow direct-typed-adapter claim, while the two-hop `evidence_refs → ExperimentRun → proposal/signal identity` question remains `UNRESOLVED`? Or does that potential path make the trace claim itself require further targeted evidence? Request only one exact remaining code excerpt if essential; do not restart a broad audit.

## 9. Execution and governance

`CODE_EXECUTION = NOT_RUN` · `TESTS = NOT_RUN` · `BUILD = NOT_RUN` · `RUNTIME = NOT_RUN` · `PROBES = NOT_RUN` · `DATA_DIRECTORY_INSPECTION = NOT_PERFORMED` · `SQLITE_INSPECTION = NOT_PERFORMED` · `GOVERNANCE = KEEP_BLOCKED`.

No dispatcher enablement, Packages B–E, M0A access, or implementation authorization.
