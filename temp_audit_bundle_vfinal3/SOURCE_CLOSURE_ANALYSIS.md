# Source Closure Analysis - PART 16

**Date:** 2026-08-23  
**Task:** PART 16 — Complete Source Closure with All Dependencies

---

## Modified Files (Contract Fix)

### Core Authorization Files
1. `src/iabv_v15/services/trust/capability_action_bridge.py` - Contract definition (no changes, reference only)
2. `src/iabv_v15/services/tools/tool_teach_service.py` - Updated to use ActionRequest
3. `src/iabv_v15/services/tools/tool_rollback_manager.py` - Updated to use ActionRequest
4. `src/iabv_v15/services/tools/github_remote_service.py` - Updated to use ActionRequest
5. `src/iabv_v15/services/trust/capability_lifecycle.py` - Updated to use ActionRequest

### Sandbox Fix Files
6. `src/iabv_v15/services/tools/tool_adapters.py` - Fixed ShellToolAdapter and LocalCliToolAdapter sandbox semantics

### Test Files
7. `tests/test_capability_action_bridge_real_signature.py` - New runtime signature test
8. `tests/test_critical2_github_remote_authorization.py` - Updated mock functions to use ActionRequest

---

## Dependency Analysis

### Direct Dependencies

**capability_action_bridge.py:**
- `dataclasses` (ActionRequest, ActionAuthorization)
- `typing` (Any)
- `iabv_v15.services.trust.authority_client` (AuthorityClient)

**tool_teach_service.py:**
- `iabv_v15.services.trust.capability_action_bridge` (CapabilityActionBridge, ActionRequest)
- `iabv_v15.services.trust.capability_lifecycle` (acquire_capability_for_execution)
- `iabv_v15.domain.models` (ToolTask, ToolCard, ToolType, etc.)
- `iabv_v15.services.tools.tool_registry` (ToolRegistry)
- `iabv_v15.services.tools.tool_memory` (ToolMemory)
- `iabv_v15.services.tools.tool_sandbox` (ToolSandbox)
- `iabv_v15.services.tools.tool_validator` (ToolValidator)
- `iabv_v15.services.tools.tool_approval_policy` (ToolApprovalPolicy)
- `iabv_v15.services.tools.tool_rollback_manager` (ToolRollbackManager)
- `iabv_v15.infra.persistence.tool_record_repository` (ToolRecordRepository)

**tool_rollback_manager.py:**
- `iabv_v15.services.trust.capability_action_bridge` (CapabilityActionBridge, ActionRequest)
- `iabv_v15.domain.models` (ToolTask, ToolCard, ToolType, etc.)
- `iabv_v15.services.tools.tool_registry` (ToolRegistry)
- `iabv_v15.services.tools.tool_memory` (ToolMemory)

**github_remote_service.py:**
- `iabv_v15.services.trust.capability_action_bridge` (CapabilityActionBridge, ActionRequest)
- `iabv_v15.domain.models` (ToolTask, ToolCard, ToolType, etc.)
- `iabv_v15.services.tools.tool_adapters` (GitHubApiToolAdapter)
- `iabv_v15.services.governance.autonomy_governance_policy` (AutonomyGovernancePolicy)
- `iabv_v15.services.approval.human_approval_broker` (HumanApprovalBroker)

**capability_lifecycle.py:**
- `iabv_v15.services.trust.capability_action_bridge` (CapabilityActionBridge, ActionRequest)
- `iabv_v15.services.trust.authority_client` (AuthorityClient)
- `iabv_v15.services.trust.trusted_lease` (TrustedLease)

**tool_adapters.py:**
- `iabv_v15.domain.models` (ToolTask, ToolCard, ToolType, etc.)
- `iabv_v15.services.tools.ui_execution_runner` (UIExecutionRunner)
- `iabv_v15.services.inference.inference_service` (InferenceService)
- `iabv_v15.services.providers.llm_provider` (LLMProvider)
- `httpx` (external dependency)

---

## Indirect Dependencies

### Domain Models
- `src/iabv_v15/domain/models.py` - Core domain models

### Infrastructure
- `src/iabv_v15/infra/persistence/tool_record_repository.py` - Database repository
- `src/iabv_v15/infra/persistence/database.py` - Database schema

### Trust Services
- `src/iabv_v15/services/trust/authority_client.py` - Authority IPC client
- `src/iabv_v15/services/trust/trusted_lease.py` - Lease dataclass
- `src/iabv_v15/services/trust/post_action_observer.py` - Post-action observation

### Tool Services
- `src/iabv_v15/services/tools/tool_registry.py` - Tool registry
- `src/iabv_v15/services/tools/tool_memory.py` - Tool memory
- `src/iabv_v15/services/tools/tool_sandbox.py` - Tool sandbox
- `src/iabv_v15/services/tools/tool_validator.py` - Tool validator
- `src/iabv_v15/services/tools/tool_approval_policy.py` - Approval policy
- `src/iabv_v15/services/tools/ui_execution_runner.py` - UI execution runner

### Governance Services
- `src/iabv_v15/services/governance/autonomy_governance_policy.py` - Autonomy governance

### Approval Services
- `src/iabv_v15/services/approval/human_approval_broker.py` - Human approval

### Inference Services
- `src/iabv_v15/services/inference/inference_service.py` - Inference service

### Provider Services
- `src/iabv_v15/services/providers/llm_provider.py` - LLM provider base

---

## Test Dependencies

### Test Files
- `tests/test_f14_negative_execution.py` - F14 negative tests
- `tests/test_f15_autonomous_evolution_execution.py` - F15 tests
- `tests/test_f16_rollback_authorization.py` - F16 tests
- `tests/test_critical2_github_remote_authorization.py` - F17 tests
- `tests/test_f14_real_authority_up_e2e.py` - F14 E2E test
- `src/iabv_v15/services/trust/test_phase3_transport_integration.py` - F11 transaction test

---

## External Dependencies

### Python Standard Library
- `dataclasses`
- `typing`
- `pathlib`
- `time`
- `subprocess`
- `shlex`
- `logging`
- `datetime`

### Third-Party Libraries
- `httpx` - HTTP client for GitHub API
- `pytest` - Test framework

---

## Source Closure Strategy

**For V11 Audit Bundle:**
1. Include all modified source files (8 files)
2. Include all direct dependencies (domain models, infrastructure, trust services, tool services)
3. Include all test files (regression tests, E2E tests)
4. Include audit documents (all .md files created in PART 4-15)
5. Include previous V10 audit bundle (for reference)

**Estimated Total Files:** ~100-150 files

---

## Next Steps

Proceed with:
- PART 17: Verify bundle importability in clean environment
