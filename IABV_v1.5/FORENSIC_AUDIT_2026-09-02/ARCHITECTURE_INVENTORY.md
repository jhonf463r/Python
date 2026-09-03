# IABV v1.5 Architecture Inventory
**Date:** 2026-09-02
**HEAD:** ac56cc3684d039c33caede168af53305fa99de35

## BOOTSTRAP

**File:** `src/iabv_v15/bootstrap.py`
**Status:** PRESENT (5626 lines)
**Evidence:** OBSERVED

**Key Components:**
- `_bg_metacognition`: Deferred metacognition thread entry (lines 1922-1994)
- `_startup_self_examination`: Self-examination suboperation
- `_run_startup_common_sense`: Common-sense reasoning suboperation
- `_deferred_auto_install_missing_tools`: Auto-install suboperation (lines 1996-2064)
- `_should_pause_prebuild`: ARO prebuild admission (lines 3963-4202)
- Startup sequencing: Phase A (tool probes), Phase B (deferred metacognition)
- Post-ready transition: `_run_deferred_metacognition_scan()`
- Startup chat bridge: MainWindowBridge integration

## ORCHESTRATION

### AdaptiveTaskOrchestrator
**File:** `src/iabv_v15/services/adaptive/adaptive_task_orchestrator.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### AdaptiveResourceOrchestrator (ARO)
**File:** `src/iabv_v15/services/intelligent_resource_manager.py` (embedded)
**Status:** PRESENT
**Evidence:** OBSERVED
**Note:** ARO is embedded within intelligent_resource_manager.py, not a separate file

### GoalEngine
**File:** `src/iabv_v15/services/adaptive/goal_engine.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### IntentUnderstandingService
**File:** `src/iabv_v15/services/adaptive/intent_understanding_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ExecutionPlaybookService
**File:** `src/iabv_v15/services/adaptive/execution_playbook_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### TaskContextAssembler
**File:** `src/iabv_v15/services/adaptive/task_context_assembler.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### TaskOutcomeRecorder
**File:** NOT_FOUND (may be embedded in other services)
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

## GOVERNANCE

### ControlMasterService
**File:** `src/iabv_v15/services/evolution/control_master_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### AutonomyGovernancePolicy
**File:** `src/iabv_v15/services/adaptive/autonomy_governance_policy.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ApprovalGateService
**File:** `src/iabv_v15/services/adaptive/approval_gate_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### CapabilityReadinessService
**File:** `src/iabv_v15/services/adaptive/capability_readiness_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

## TOOLS / EXPERTS / IA

### ToolRegistry
**File:** `src/iabv_v15/services/tools/tool_registry.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### InteractionModeSelector
**File:** `src/iabv_v15/services/tools/interaction_mode_selector.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ToolTeachService
**File:** `src/iabv_v15/services/tools/tool_teach_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### OllamaExpertProvider
**File:** `src/iabv_v15/services/providers/ollama_expert_provider.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### DevinExpertProvider
**File:** NOT_FOUND
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

### ClaudeExpertProvider
**File:** NOT_FOUND
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

### CodexExpertProvider
**File:** NOT_FOUND
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

### OpenAI / ChatGPT
**File:** NOT_FOUND (may be integrated via other providers)
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

## LEARNING

### ExperimentLab
**File:** `src/iabv_v15/services/lab/experiment_lab.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### AdaptiveProtocol
**File:** `src/iabv_v15/services/adaptive/adaptive_protocol.py`
**Status:** PRESENT (325 lines)
**Evidence:** OBSERVED

**Key Components:**
- `AdaptiveRule`: Learned rule dataclass
- `ProtocolRecommendation`: Recommendation dataclass
- `AdaptiveProtocolService`: Rule management
- Confidence thresholds: 0.7 min confidence, 3 min observations, 0.8 success rate
- Persistence: rules.json in evolution/adaptive_protocol/
- **DEFECT FOUND:** Line 289 has typo `" rule_key"` instead of `"rule_key"` - this will cause deserialization failure

## OBSERVATION

### OperationalSelfExaminationService
**File:** `src/iabv_v15/services/evolution/operational_self_examination_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### WorldModelService
**File:** `src/iabv_v15/services/evolution/world_model_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ResourceMetacognitionService
**File:** `src/iabv_v15/services/evolution/resource_metacognition_service.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### CognitiveMetabolicTick
**File:** `src/iabv_v15/services/evolution/cognitive_metabolic_tick.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### FreezeIncidentReporter
**File:** `src/iabv_v15/services/evolution/freeze_incident_reporter.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### UIHeartbeatWatchdog
**File:** NOT_FOUND (may be embedded in bootstrap.py)
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

## PERSISTENCE

### ObjectiveRepository
**File:** `src/iabv_v15/infra/persistence/objective_repository.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### RunRepository
**File:** `src/iabv_v15/infra/persistence/run_repository.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### EpisodeRepository
**File:** `src/iabv_v15/infra/persistence/episode_repository.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### SessionRepository
**File:** `src/iabv_v15/infra/persistence/adaptive_session_repository.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ApprovalCheckpointRepository
**File:** `src/iabv_v15/infra/persistence/approval_checkpoint_repository.py`
**Status:** PRESENT
**Evidence:** OBSERVED

### ExperienceRepository
**File:** NOT_FOUND
**Status:** NOT_FOUND
**Evidence:** UNKNOWN

## IDENTITY / CAUSALITY

### AgentHandoffTrail
**File:** `src/iabv_v15/services/evolution/agent_handoff_trail.py`
**Status:** PRESENT
**Evidence:** OBSERVED

**Note:** Runtime identity (run_id, execution_id, session_id, episode_id) appears to be managed by repository services but not explicitly inventoried as separate identity service.
