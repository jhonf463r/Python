# Devin Session Gate - Canonical Classification (P0.164b)

## Classification

**Type**: `support_only`
**Status**: Ready for canonical review as independent support tool
**Scope**: Agent coordination, briefing, and session verification

## What the Gate Does

The `devin_session_gate.py` script is an operational tool for:

1. **Pre-session briefing**: Generates compact briefings before agent sessions
2. **Post-session verification**: Verifies agent delivery after sessions
3. **Human review coordination**: Identifies tasks requiring human review
4. **Evidence exposure**: Exposes existing runtime evidence (portable context, algorithm fitness, runtime knowledge)
5. **Snapshot generation**: Writes its own operational snapshots to `data/evolution/agent_session_gate/latest.*`

## What the Gate Does NOT Do

- **Does NOT decide runtime routes**: It does not replace `PortableContext`, `OSES`, `ExperimentLab`, or `StrategySelector`
- **Does NOT mutate source code**: It only reads and verifies
- **Does NOT orchestrate organism runtime**: It coordinates agent sessions, not organism execution
- **Does NOT introduce new authority**: It is a support tool, not a decision layer

## Operational Snapshots (Gate-Only)

The gate writes its own operational snapshots:

- `data/evolution/agent_session_gate/latest.json` - Pre-session briefing snapshot
- `data/evolution/agent_session_gate/latest.md` - Pre-session briefing markdown
- `data/evolution/agent_session_gate/latest_post.json` - Post-session verification snapshot
- `data/evolution/agent_session_gate/latest_post.md` - Post-session verification markdown
- `data/evolution/agent_session_gate/post_*.json` - Historical post-session snapshots

These are **gate operational artifacts**, not canonical runtime state.

## Runtime Knowledge Bridge (Separate Package)

The `runtime_knowledge_snapshot.py` integration is a **separate read-only bridge**:

- **Function**: `try_runtime_knowledge_snapshot()` exposes compact runtime dossier
- **Behavior**: Read-only, no write operations
- **Purpose**: Observability only, not decision-making
- **Status**: To be reviewed in separate PR/package

**This bridge is NOT part of the canonical gate classification.** It is an optional read-only exposure that can be integrated separately.

## Canonical Core vs Support Only

**Canonical Core** (NOT the gate):
- `PortableContextService`
- `OperationalSelfExaminationService`
- `ExperimentLab`
- `StrategySelector`
- `AlgorithmFitnessContract`
- `ArtifactLifecycleService`
- `CodeAuditTrail`

**Support Only** (the gate):
- `devin_session_gate.py` - Agent coordination and briefing tool
- Writes operational snapshots for session tracking
- Exposes existing evidence for human review
- Does not decide runtime behavior

## Evidence for Codex Audit

### Files in Gate Package
- `scripts/devin_session_gate.py` - Main gate script
- `tests/test_devin_session_gate_p136.py` - Existing gate tests

### Files EXCLUDED from Gate Package
- `src/iabv_v15/services/evolution/runtime_knowledge_snapshot.py` - Separate read-only bridge
- `tests/test_runtime_knowledge_snapshot.py` - Runtime knowledge tests
- `tests/test_devin_session_gate_runtime_knowledge.py` - Bridge integration tests

### Gate Responsibilities
1. Read `platform_pending` tasks
2. Read `portable_context/latest.json`
3. Read `self_examination/latest.json`
4. Read `bootstrap.py` for service wiring
5. Call `AlgorithmFitnessContract.build_algorithm_observation_matrix()` (optional)
6. Call `export_compact_runtime_dossier()` (optional, read-only bridge)
7. Write gate operational snapshots to `agent_session_gate/latest.*`
8. Render markdown briefings
9. Verify post-session file delivery
10. Call `CodeAuditTrail.record_agent_delivery()` for audit trail

### Gate Does NOT
- Decide organism routes
- Activate/deactivate organs
- Modify runtime state
- Replace canonical core services
- Introduce new decision authority

## Separation Strategy

The gate and runtime knowledge bridge are intentionally separated:

1. **Gate PR/Package**: `devin_session_gate.py` as support-only canonical tool
2. **Bridge PR/Package**: `runtime_knowledge_snapshot.py` as read-only exposure layer

This separation allows:
- Independent review of gate operational behavior
- Independent review of runtime knowledge bridge
- Clear boundary between coordination and observability
- No mixing of concerns in single PR

## Test Evidence

### Gate Tests (Canonical)
- `test_devin_session_gate_p136.py` - Existing gate functionality tests

### Bridge Tests (Separate Package)
- `test_runtime_knowledge_snapshot.py` - Runtime knowledge export tests
- `test_devin_session_gate_runtime_knowledge.py` - Bridge integration tests

The bridge tests verify:
- `try_runtime_knowledge_snapshot()` is read-only
- `build_pre_snapshot()` includes runtime knowledge
- `render_pre_markdown()` shows runtime knowledge section
- Gate writes its own snapshots (accepted behavior)

## Conclusion

`devin_session_gate.py` is classified as **support_only** canonical tool for agent coordination and session verification. It is NOT canonical core and does NOT introduce runtime decision authority. The runtime knowledge bridge is a separate read-only exposure layer to be reviewed independently.
