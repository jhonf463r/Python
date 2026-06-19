# GitHub Copilot Instructions for IABV v1.5

**This is IABV v1.5** — an autonomy-governed reasoning system with:
- **Local-first operation**: No external dependencies for core logic
- **Operational observability**: Real-time environment and decision tracking  
- **Cumulative learning**: Evidence-based strategy adaptation
- **Portable context**: Session-independent knowledge transfer

## Quick Start for New Agents

1. **Read the main instructions first**: See [AGENTS.md](../AGENTS.md) (500 lines, comprehensive)

2. **One-minute context checklist**:
   - Don't create another orchestrator or brain (we have `AdaptiveTaskOrchestrator`)
   - Always check `WorldModelSnapshot` before external calls
   - Respect P1-P4 closed layers (World Model, Learning, Portable Context, Self-Examination)
   - Verify tools via `ToolRegistry` before using them
   - Mark `UNRESOLVED` if you can't confirm something real

3. **Common operations**:
   - **Run tests**: `$env:PYTHONPATH='C:\Python\IABV_v1.5\src'; & python -m pytest tests/ -q`
   - **Check latest state**: Read `data/evolution/portable_context/latest.json` (compressed session knowledge)
   - **Read self-exam**: `data/evolution/self_examination/latest.md` (what the system learned)
   - **World model**: `data/evolution/world_model/` (live environment snapshot)

4. **Architecture quick reference**:
   - `PerceptionSnapshot` + `AdaptiveTaskOrchestrator` = decision pipeline
   - `WorldModelSnapshot` = live environment state (windows, tools, network, locks)
   - `PortableContextService` = compresses learning across sessions
   - `OperationalSelfExaminationService` = detects patterns, risks, recommendations
   - `DecisionAuditTrail` = logs all cloud reasoning decisions

5. **Don't break these contracts**:
   - No bypassing `AutonomyGovernancePolicy` 
   - No parallel memories (use `PortableContextService`)
   - No ViewModels deciding routes (they only observe)
   - No inventing observations you can't verify

## Full Documentation

See [AGENTS.md](../AGENTS.md) for:
- Complete architecture details
- Closed layers P1-P4 (respect these)
- Operational policies and meta-cognition rules
- Bootstrap and autonomy infrastructure
- Real sources of truth hierarchy

## What This System Does

**Input**: User intent + `PerceptionSnapshot` (environment + windows + available tools)

**Process**:
1. Classify intent via `IntentUnderstandingService`
2. Route to local, cloud, or hybrid via `LocalRoleRouter`
3. Assemble context from `WorldModel`, `EnvironmentSelfModel`, and `PortableContext`
4. Execute via `AdaptiveTaskOrchestrator` (respecting `AutonomyGovernancePolicy`)
5. Record outcomes → `DecisionAuditTrail` → feed learning layers

**Learning loop**:
- `ExperimentLab` compares routes and configurations
- `StrategySelector` weights future decisions by evidence
- `OperationalSelfExaminationService` detects degradations and recommends adjustments
- `PortableContextService` compresses all learning for next session

## Key Restrictions

**You can't**:
- Create new orchestrators or parallel brains
- Override closed layers (P1-P4)
- Use tools without checking `ToolRegistry` and `WorldModel` first
- Claim observability you didn't verify
- Auto-execute external calls without `AutonomyGovernancePolicy` consent

**You must**:
- Check `WorldModelSnapshot` before external calls
- Respect `AutonomyGovernancePolicy` blocklists
- Record decisions → `DecisionAuditTrail` (cloud reasoning only)
- Feed results back → learning layers (ExperimentLab, StrategySelector)
- Mark `UNRESOLVED` when evidence is missing

## Troubleshooting

**"Tool reported as unavailable"**:
- Check `ToolRegistry.current_state()` 
- Verify network via `WorldModel.network_status`
- Check `data/evolution/tool_discovery/latest.json` for last known health

**"Decision seems stuck"**:
- Read `DecisionAuditTrail.self_examination_summary()` (detects failures, timeouts, retry loops)
- Check `OperationalSelfExaminationService._temporal_awareness_findings()` for latency anomalies
- Review `ExperimentLab` to see if a better route exists

**"Not sure if this is allowed"**:
- Read [AGENTS.md § Contratos Que No Debes Romper](../AGENTS.md#contratos-que-no-debes-romper)
- If still unclear, mark the concern as `UNRESOLVED` in your response

## Related Documentation

- [Architecture Deep Dive](../AGENTS.md) — Full system design
- [Self-Examination Examples](../docs/SELF_HEALING.md) — How the system self-corrects
- [MCP Bridge](../docs/mcp-bridge.md) — External tool integration
- [Test Patterns](../tests/) — Example test structure

---

**Remember**: Your job is to **read the real state, respect the architecture, leave each session with better evidence and less redundant work.**
