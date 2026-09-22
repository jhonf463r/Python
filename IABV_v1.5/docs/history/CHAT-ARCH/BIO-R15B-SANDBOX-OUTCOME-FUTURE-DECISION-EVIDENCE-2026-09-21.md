# BIO-R15B — Sandbox outcome to future adaptive decision

## Scope

This isolated, test-only experiment starts with a formed `SandboxExperiment` and invokes the real production persistence method `SandboxExperimentService._record_sandbox_run()`. It does not execute a tool, call an external assistant, create a `ToolTask`, or alter production code.

The continuation is production code:

```text
SandboxExperiment outcome
  -> ExperimentLab.record_outcome()
  -> ExperimentLabRepository save run + recommendation
  -> fresh ExperimentLabRepository read
  -> fresh TaskContextAssembler experiment_insights
  -> AdaptiveTaskOrchestrator._build_decision_context()
```

## Controlled histories

All cases share the same source subject, sandbox subject, goal, domain, baseline ChatGPT evidence, candidate Codex identity, environment-free fixture, world model, request, intent, and routing fixture. The treatment changes the effective sandbox outcome from `failed/promote=false` to `valid/promote=true`, a production-valid outcome perturbation. The negative control only changes the irrelevant baseline `trace_id`.

| Case | Sandbox verdict | Promote | Fresh recommendation | Historical preference |
| --- | --- | --- | --- | --- |
| Control | `failed` | `false` | ChatGPT / `language_understanding` / `0.964` | ChatGPT / `chatgpt-baseline` |
| Treatment | `valid` | `true` | Codex / `code_agent` / `1.0306` | Codex / `codex-sandbox` |
| Negative control | `failed` | `false` | ChatGPT / `language_understanding` / `0.964` | ChatGPT / `chatgpt-baseline` |

## Persistence and fresh read

Each case writes to an isolated SQLite database and artifact storage. Writer `ExperimentLab`/repository objects are discarded. A new `AppDatabase`, `ExperimentLabRepository`, and `TaskContextAssembler` then load persisted recommendations using the real `list_recommendations()` path. The assembler emits `experiment_insights` and `adaptive_learning_summary`; the orchestrator consumes the former into `historical_preferred_assistant_kind` and `historical_preferred_config_signature`.

The sandbox service writes under `sandbox:{subject_key}`. The request site was intentionally `sandbox:general`, which makes the production fallback comparison scope key exactly that stored subject: `sandbox:general:code-bio-r15b-future-decision`. No insight or recommendation was assigned manually.

## First causal edge and verdict

The first discriminating causal edge is Level 4:

```text
SandboxExperiment outcome
  -> persisted recommendation
  -> fresh experiment_insights
  -> historical assistant/config preference in DecisionContext
```

**CAUSALLY_CONFIRMED** at that boundary. The final operational route remains `project_evolution` in all cases and governance leaves `assistant_kind` empty; this experiment proves the historical adaptive preference, not an externally dispatched tool choice.

## Negative knowledge

- `SandboxExperiment -> external execution`: **NOT_TESTED**
- external effect: **NOT_TESTED**
- external outcome: **NOT_TESTED**
- promotion -> executable production state: **NOT_PROVEN**
- `ToolTask`: **NOT_CREATED / NOT_TESTED**
- development: **NOT_PROVEN**
- evolution: **NOT_PROVEN**

The next open edge is whether the historically preferred assistant/configuration is consumed by a later executable task selection under a separately controlled, non-external test.
