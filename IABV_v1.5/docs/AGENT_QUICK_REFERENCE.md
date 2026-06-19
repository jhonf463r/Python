# IABV v1.5 — Agent Quick Reference

Quick lookup for common agent operations and patterns.

## Essential Files & Paths

| What | Where | Purpose |
|------|-------|---------|
| **System wiring** | `src/iabv_v15/bootstrap.py` | Service initialization, lazy loading |
| **Domain contracts** | `src/iabv_v15/domain/models.py` | Data contracts, enums, immutable structures |
| **Last session context** | `data/evolution/portable_context/latest.json` | Compressed knowledge for new sessions |
| **What system learned** | `data/evolution/self_examination/latest.md` | Patterns, risks, recommendations from execution |
| **Live environment state** | `data/evolution/world_model/` | Current windows, focus, tools, network, locks |
| **Cloud decision log** | `data/evolution/decision_audit/decisions.jsonl` | Each cloud reasoning call (provider, latency, result) |
| **Tool health** | `data/evolution/tool_discovery/latest.json` | Last known state of all external tools |
| **Tests** | `tests/` | Run `pytest tests/ -q` |

## Common Service Patterns

### Before Using Any External Tool

```python
# 1. Check if it's available
from iabv_v15.services.tools import ToolRegistry
registry = bootstrap().tool_registry()
tool_state = registry.current_state(tool_name='github')

# 2. Check world model for blockers
from iabv_v15.services.evolution import WorldModelService
wm = bootstrap().world_model_service()
snapshot = wm.current_snapshot()
if snapshot.network.blocked or snapshot.active_locks.get(tool_name):
    # → blocked, don't proceed

# 3. Check governance policy
governance = bootstrap().autonomy_governance_policy()
if not governance.can_execute_external(intent_type, tool_name):
    # → not allowed, explain and stop
```

### Recording a Decision (Cloud Reasoning)

```python
# After using cloud reasoning:
from iabv_v15.services.evolution import DecisionAuditTrail
audit = bootstrap().decision_audit_trail()

audit.record(
    intent_key='classify_code_pattern',
    provider='gemini',
    latency_ms=450,
    confidence=0.85,
    result_type='success',
    recommendation=None  # or suggest next step
)
```

### Checking What The System Learned

```python
# 1. Read portable context
import json
ctx = json.load(open('data/evolution/portable_context/latest.json'))
print(ctx['cloud_reasoning']['health_score'])  # 0.0-1.0
print(ctx['adaptive_learning_summary'])  # top strategies

# 2. Read self-exam snapshot
exam = json.load(open('data/evolution/self_examination/latest.json'))
print(exam['degradation_warnings'])  # risks detected
print(exam['adjustment_recommendations'])  # what to improve
```

### Running Tests Safely

```powershell
# 1. Set up environment
$env:PYTHONPATH='C:\Python\IABV_v1.5\src'

# 2. Run focused test on your change
& python -m pytest tests/test_my_feature.py -v

# 3. Run regression on related module
& python -m pytest tests/test_orchestrator.py tests/test_world_model.py -q

# 4. Full suite (only after passing above)
& python -m pytest tests/ -q
```

## Architecture Decision Tree

**Need to route a user request?**
- → Use `IntentUnderstandingService` (classify intent)
- → Use `LocalRoleRouter` (which provider is best?)
- → Check `AutonomyGovernancePolicy` (is it allowed?)
- → Use `AdaptiveTaskOrchestrator` (execute)

**Need to check if a tool works?**
- → Read `WorldModelSnapshot` first (is network up? are we blocked?)
- → Check `ToolRegistry.current_state()`
- → If still unsure, read `tool_discovery/latest.json` (last known state)

**Need to learn from past decisions?**
- → Read `portable_context/latest.md` (compressed learning)
- → Read `self_examination/latest.md` (patterns and risks)
- → Read `decision_audit/decisions.jsonl` (detailed cloud calls)

**Need to improve a strategy?**
- → Check `ExperimentLab` (which routes performed best?)
- → Update weights in `AdaptiveWeightLayer` based on evidence
- → Record result in `DecisionAuditTrail`
- → Let `PortableContextService` export for next session

## Common Mistakes to Avoid

| Mistake | Why | Fix |
|---------|-----|-----|
| Using a tool without checking `WorldModelSnapshot` | Tool might be blocked or network down | Always read world model first |
| Creating a new orchestrator | Violates P1 architecture | Extend `AdaptiveTaskOrchestrator` instead |
| Inventing observability you didn't verify | False positives break learning | Mark `UNRESOLVED` if unsure |
| Bypassing `AutonomyGovernancePolicy` | Breaks governance | Check policy before executing |
| Storing learning in a parallel memory | Splits knowledge | Use `PortableContextService` only |
| Making ViewModels decide routes | UI shouldn't control logic | Keep ViewModels read-only |

## Closed Layers (Don't Touch!)

| Layer | What | Why | Status |
|-------|------|-----|--------|
| **P1** | `WorldModelSnapshot` + `WorldModelService` | Source of truth for environment state | Closed ✓ |
| **P2** | `ExperimentLab`, `StrategySelector`, `AdaptiveWeightLayer` | Learning from real evidence | Closed ✓ |
| **P3** | `PortableContextService` | Session-independent knowledge | Closed ✓ |
| **P4** | `OperationalSelfExaminationService` | Pattern detection and risk assessment | Closed ✓ |

## One-Liners for Key Tasks

```bash
# View last session's learning
cat data/evolution/portable_context/latest.md | head -20

# See what went wrong recently
tail -20 data/evolution/decision_audit/decisions.jsonl | jq '.result_type' | sort | uniq -c

# Check test coverage
pytest tests/ --cov=src/iabv_v15 --cov-report=term-missing

# Run only tests matching a pattern
pytest -k "test_cloud_reasoning" -v

# See what strategies are winning
cat data/evolution/portable_context/latest.json | jq '.adaptive_learning_summary'
```

## Resources

- **Full guide**: [AGENTS.md](../AGENTS.md)
- **Troubleshooting**: See section "Pendientes Reales" in AGENTS.md
- **Bootstrap details**: [scripts/iabv_bootstrap.ps1](../scripts/iabv_bootstrap.ps1)
- **Test examples**: [tests/](../tests/)

---

**Principle**: Real state > Contracts > Portable Context > Tests > History > Guesses
