"""InternalMetabolicStateService — unified internal state inspection layer.

Composes (does not duplicate) existing self-inspection services to provide
a truthful model of IABV's current functional state.

This service is a COMPOSER/INSPECTOR, not a new orchestration system.
It reuses:
- OperationalSelfExaminationService for operational findings
- ControlMasterService for work queue and governance state
- EnvironmentSelfAwarenessService for resource state
- CapabilityReadinessService for capability gaps
- Existing repositories and health checks

NEW inspections (not covered by existing services):
- Connection health (component wiring verification)
- Orphaned component detection
- Duplication detection
- Disconnected capability chain detection
- Structured health dimensions

DO NOT:
- Create second orchestration system
- Create second memory system
- Create second provider selector
- Duplicate perception/validation/goal management
- Execute autonomous code modification
- Execute real Devin/Ollama during inspection
- Modify Authority/Capability/Lease
- Perform destructive Git operations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Structured health dimension status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ConnectionStatus(str, Enum):
    """Component connection health status."""
    SOURCE_EXISTS = "SOURCE_EXISTS"
    CONSTRUCTED = "CONSTRUCTED"
    INJECTED = "INJECTED"
    PRODUCTION_CALLER = "PRODUCTION_CALLER"
    RUNTIME_REACHABLE = "RUNTIME_REACHABLE"
    AFFECTS_DECISION = "AFFECTS_DECISION"
    AFFECTS_EXECUTION = "AFFECTS_EXECUTION"
    VALIDATED = "VALIDATED"


class ChainStatus(str, Enum):
    """Capability chain connection status."""
    CONNECTED = "CONNECTED"
    PARTIAL = "PARTIAL"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class ComponentConnection:
    """Connection health for a single component."""
    component_name: str
    source_exists: bool
    constructed: bool
    injected: bool
    production_caller: bool
    runtime_reachable: bool
    affects_decision: bool
    affects_execution: bool
    validated: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class OrphanedComponent:
    """Component that exists but has no production caller."""
    component_name: str
    file_path: str
    why_orphaned: str
    primary_consumer_needed: str
    test_only: bool = False


@dataclass
class DuplicateImplementation:
    """Conceptual duplication among implementations."""
    concept: str
    implementations: list[str]
    primary: str
    secondary: str
    duplicate: bool
    reuse_recommendation: str


@dataclass
class BrokenChain:
    """Disconnected capability chain."""
    chain_name: str
    status: ChainStatus
    first_broken_link: str
    components: list[str]
    notes: list[str] = field(default_factory=list)


@dataclass
class HealthDimension:
    """Structured health dimension."""
    name: str
    status: HealthStatus
    evidence: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class Recommendation:
    """Non-autonomous recommendation."""
    action: str  # integrate, test, remove_duplicate, validate, investigate, use_ollama, use_devin, defer
    target: str
    reason: str
    priority: str  # high, medium, low
    estimated_effort: str  # small, medium, large


@dataclass
class InternalMetabolicState:
    """Unified internal state model."""
    generated_at: datetime
    components: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    goals: dict[str, Any] = field(default_factory=dict)
    current_work: dict[str, Any] = field(default_factory=dict)
    perception_state: dict[str, Any] = field(default_factory=dict)
    resource_state: dict[str, Any] = field(default_factory=dict)
    memory_state: dict[str, Any] = field(default_factory=dict)
    experience_state: dict[str, Any] = field(default_factory=dict)
    provider_state: dict[str, Any] = field(default_factory=dict)
    model_state: dict[str, Any] = field(default_factory=dict)
    validation_state: dict[str, Any] = field(default_factory=dict)
    governance_state: dict[str, Any] = field(default_factory=dict)
    connections: dict[str, ComponentConnection] = field(default_factory=dict)
    disconnected_components: list[str] = field(default_factory=list)
    orphaned_components: list[OrphanedComponent] = field(default_factory=list)
    duplicated_capabilities: list[DuplicateImplementation] = field(default_factory=list)
    degraded_paths: list[str] = field(default_factory=list)
    missing_integrations: list[str] = field(default_factory=list)
    stale_state: list[str] = field(default_factory=list)
    health_dimensions: dict[str, HealthDimension] = field(default_factory=dict)
    broken_chains: list[BrokenChain] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)


class InternalMetabolicStateService:
    """Composer/inspector for internal metabolic state."""

    def __init__(
        self,
        *,
        workspace_root: str,
        operational_self_examination_service: Any | None = None,
        control_master_service: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        capability_readiness_service: Any | None = None,
        role_router: Any | None = None,
        inference_service: Any | None = None,
        adaptive_task_orchestrator: Any | None = None,
        task_context_assembler: Any | None = None,
        reflection_routing_service: Any | None = None,
        resource_aware_controller: Any | None = None,
        unified_memory_layer: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        sandbox_experiment_service: Any | None = None,
        tool_teach_service: Any | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.operational_self_examination_service = operational_self_examination_service
        self.control_master_service = control_master_service
        self.environment_self_awareness_service = environment_self_awareness_service
        self.capability_readiness_service = capability_readiness_service
        self.role_router = role_router
        self.inference_service = inference_service
        self.adaptive_task_orchestrator = adaptive_task_orchestrator
        self.task_context_assembler = task_context_assembler
        self.reflection_routing_service = reflection_routing_service
        self.resource_aware_controller = resource_aware_controller
        self.unified_memory_layer = unified_memory_layer
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.sandbox_experiment_service = sandbox_experiment_service
        self.tool_teach_service = tool_teach_service

        # Cache for bounded inspection
        self._last_inspection: InternalMetabolicState | None = None
        self._last_inspection_time: float = 0.0
        self._cache_ttl_seconds = 60.0

    def inspect(self, *, force_refresh: bool = False) -> InternalMetabolicState:
        """Perform bounded inspection using cached state where possible."""
        import time

        now = time.monotonic()
        if not force_refresh and self._last_inspection is not None:
            if (now - self._last_inspection_time) < self._cache_ttl_seconds:
                logger.debug("Returning cached internal metabolic state")
                return self._last_inspection

        logger.info("Performing internal metabolic state inspection...")
        state = InternalMetabolicState(generated_at=datetime.now(timezone.utc))

        # Compose from existing services
        self._compose_operational_state(state)
        self._compose_control_master_state(state)
        self._compose_resource_state(state)
        self._compose_capability_state(state)
        self._compose_provider_state(state)

        # NEW inspections
        self._inspect_connection_health(state)
        self._inspect_orphaned_components(state)
        self._inspect_duplication(state)
        self._inspect_broken_chains(state)
        self._compute_health_dimensions(state)
        self._generate_recommendations(state)

        self._last_inspection = state
        self._last_inspection_time = now
        return state

    def _compose_operational_state(self, state: InternalMetabolicState) -> None:
        """Compose operational findings from OperationalSelfExaminationService."""
        if self.operational_self_examination_service is None:
            state.validation_state['operational_examination'] = "UNKNOWN: service not available"
            return

        try:
            # Get current review snapshot
            snapshot = getattr(self.operational_self_examination_service, '_current_review', None)
            if snapshot is not None:
                state.validation_state['operational_findings'] = {
                    'total_findings': len(snapshot.findings or []),
                    'severity_counts': self._count_severities(snapshot.findings or []),
                    'last_review_at': snapshot.reviewed_at,
                }
            else:
                state.validation_state['operational_examination'] = "UNKNOWN: no snapshot available"
        except Exception as exc:
            logger.warning(f"Failed to compose operational state: {exc}")
            state.validation_state['operational_examination'] = f"ERROR: {exc}"

    def _compose_control_master_state(self, state: InternalMetabolicState) -> None:
        """Compose work queue and governance state from ControlMasterService."""
        if self.control_master_service is None:
            state.governance_state['control_master'] = "UNKNOWN: service not available"
            state.current_work['work_queue'] = "UNKNOWN"
            return

        try:
            control_state = self.control_master_service.current_state(refresh=False)
            state.governance_state['control_master'] = {
                'active_objective_ids': list(control_state.active_objective_ids or []),
                'completed_objective_ids': list(control_state.completed_objective_ids or []),
                'paused_objective_ids': list(control_state.paused_objective_ids or []),
                'recent_decisions_count': len(control_state.recent_decisions or []),
                'global_rules_count': len(control_state.global_rules or []),
            }
            # backlog and risks may not exist on all ControlMasterState versions
            backlog = getattr(control_state, 'backlog', [])
            risks = getattr(control_state, 'risks', [])
            state.current_work['work_queue'] = {
                'active_objectives': list(control_state.active_objective_ids or []),
                'backlog_count': len(backlog or []),
                'risks_count': len(risks or []),
            }
            state.goals['objectives'] = {
                'active': list(control_state.active_objective_ids or []),
                'paused': list(control_state.paused_objective_ids or []),
                'completed': list(control_state.completed_objective_ids or []),
            }
        except Exception as exc:
            logger.warning(f"Failed to compose control master state: {exc}")
            state.governance_state['control_master'] = f"ERROR: {exc}"

    def _compose_resource_state(self, state: InternalMetabolicState) -> None:
        """Compose resource state from EnvironmentSelfAwarenessService."""
        if self.environment_self_awareness_service is None:
            state.resource_state['environment'] = "UNKNOWN: service not available"
            return

        try:
            env_model = self.environment_self_awareness_service.current_model()
            state.resource_state['environment'] = {
                'ram_available_mb': getattr(env_model, 'ram_available_mb', None),
                'cpu_load_pct': getattr(env_model, 'cpu_load_pct', None),
                'disk_available_gb': getattr(env_model, 'disk_available_gb', None),
                'gpu_available': getattr(env_model, 'gpu_available', None),
                'scan_status': getattr(env_model, 'scan_status', 'unknown'),
            }
        except Exception as exc:
            logger.warning(f"Failed to compose resource state: {exc}")
            state.resource_state['environment'] = f"ERROR: {exc}"

    def _compose_capability_state(self, state: InternalMetabolicState) -> None:
        """Compose capability state from CapabilityReadinessService."""
        if self.capability_readiness_service is None:
            state.capabilities['readiness'] = "UNKNOWN: service not available"
            return

        try:
            # Get recent capability assessments from repository
            repo = getattr(self.capability_readiness_service, 'capability_repository', None)
            if repo is not None:
                recent = repo.list_recent(limit=20)
                state.capabilities['readiness'] = {
                    'recent_assessments': len(recent),
                    'ready_count': sum(1 for c in recent if getattr(c, 'status', None) == 'READY'),
                    'partial_count': sum(1 for c in recent if getattr(c, 'status', None) == 'PARTIAL'),
                    'insufficient_count': sum(1 for c in recent if getattr(c, 'status', None) == 'INSUFFICIENT'),
                }
            else:
                state.capabilities['readiness'] = "UNKNOWN: repository not available"
        except Exception as exc:
            logger.warning(f"Failed to compose capability state: {exc}")
            state.capabilities['readiness'] = f"ERROR: {exc}"

    def _compose_provider_state(self, state: InternalMetabolicState) -> None:
        """Compose provider state from LocalRoleRouter health snapshot."""
        if self.role_router is None:
            state.provider_state['health'] = "UNKNOWN: role_router not available"
            return

        try:
            health = self.role_router.health_snapshot(refresh=False, max_age_seconds=60.0)
            state.provider_state['health'] = {
                'providers': [
                    {
                        'name': h.provider_name,
                        'available': h.available,
                        'status': h.status.value if h.status else 'UNKNOWN',
                    }
                    for h in health
                ],
                'total_providers': len(health),
                'available_count': sum(1 for h in health if h.available),
            }
        except Exception as exc:
            logger.warning(f"Failed to compose provider state: {exc}")
            state.provider_state['health'] = f"ERROR: {exc}"

    def _inspect_connection_health(self, state: InternalMetabolicState) -> None:
        """Inspect connection health for major subsystems."""
        components_to_check = [
            ('ReflectionRoutingService', self.reflection_routing_service),
            ('ResourceAwareController', self.resource_aware_controller),
            ('TaskContextAssembler', self.task_context_assembler),
            ('InferenceService', self.inference_service),
            ('AdaptiveTaskOrchestrator', self.adaptive_task_orchestrator),
            ('UnifiedMemoryLayer', self.unified_memory_layer),
            ('AutonomousValidationCycle', self.autonomous_validation_cycle),
            ('SandboxExperimentService', self.sandbox_experiment_service),
            ('ToolTeachService', self.tool_teach_service),
        ]

        for name, component in components_to_check:
            connection = ComponentConnection(
                component_name=name,
                source_exists=component is not None,
                constructed=component is not None,
                injected=self._is_injected(component),
                production_caller=self._has_production_caller(name),
                runtime_reachable=component is not None,
                affects_decision=self._affects_decision(name),
                affects_execution=self._affects_execution(name),
                validated=self._is_validated(name),
            )
            state.connections[name] = connection

    def _inspect_orphaned_components(self, state: InternalMetabolicState) -> None:
        """Detect orphaned components (exist but no production caller)."""
        # This is a lightweight check - we don't do deep code analysis
        # We flag known potential orphans based on architectural knowledge
        # Real orphan detection would require static analysis which is expensive

        # Example: if UnifiedMemoryLayer exists but TaskContextAssembler doesn't use it
        if self.unified_memory_layer is not None and self.task_context_assembler is None:
            # Check if TaskContextAssembler actually uses UnifiedMemoryLayer
            # This is a placeholder - real check would inspect method calls
            # For now, we mark as UNKNOWN to avoid false positives
            state.orphaned_components.append(
                OrphanedComponent(
                    component_name="UnifiedMemoryLayer",
                    file_path="services/knowledge/unified_memory_layer.py",
                    why_orphaned="UNKNOWN: requires static call graph analysis to verify",
                    primary_consumer_needed="TaskContextAssembler or InferenceService",
                    test_only=False,
                )
            )

    def _inspect_duplication(self, state: InternalMetabolicState) -> None:
        """Detect conceptual duplication among implementations."""
        # Check for resource control duplication
        # ResourceAwareController vs EnvironmentSelfAwarenessService
        if self.resource_aware_controller is not None and self.environment_self_awareness_service is not None:
            state.duplicated_capabilities.append(
                DuplicateImplementation(
                    concept="resource_control",
                    implementations=["ResourceAwareController", "EnvironmentSelfAwarenessService"],
                    primary="ResourceAwareController",
                    secondary="EnvironmentSelfAwarenessService",
                    duplicate=False,  # They serve different purposes (governance vs observation)
                    reuse_recommendation="Keep both: ResourceAwareController for governance decisions, EnvironmentSelfAwarenessService for monitoring",
                )
            )

    def _inspect_broken_chains(self, state: InternalMetabolicState) -> None:
        """Detect disconnected capability chains."""
        # Chain A: ControlMaster -> AdaptiveTaskOrchestrator -> execution
        chain_a_components = ["ControlMasterService", "AdaptiveTaskOrchestrator"]
        chain_a_status = self._check_chain(chain_a_components)
        if chain_a_status != ChainStatus.CONNECTED:
            state.broken_chains.append(
                BrokenChain(
                    chain_name="ControlMaster_to_Execution",
                    status=chain_a_status,
                    first_broken_link=self._find_broken_link(chain_a_components),
                    components=chain_a_components,
                    notes=["ControlMaster work queue must flow to AdaptiveTaskOrchestrator"],
                )
            )

        # Chain D: Memory -> TaskContext -> decision
        chain_d_components = ["UnifiedMemoryLayer", "TaskContextAssembler"]
        chain_d_status = self._check_chain(chain_d_components)
        if chain_d_status != ChainStatus.CONNECTED:
            state.broken_chains.append(
                BrokenChain(
                    chain_name="Memory_to_TaskContext",
                    status=chain_d_status,
                    first_broken_link=self._find_broken_link(chain_d_components),
                    components=chain_d_components,
                    notes=["Memory should inform TaskContext assembly"],
                )
            )

    def _compute_health_dimensions(self, state: InternalMetabolicState) -> None:
        """Compute structured health dimensions."""
        # Perception health
        perception_healthy = (
            self.task_context_assembler is not None
            and self.environment_self_awareness_service is not None
        )
        state.health_dimensions['perception'] = HealthDimension(
            name="perception",
            status=HealthStatus.HEALTHY if perception_healthy else HealthStatus.DEGRADED,
            evidence=["TaskContextAssembler available"] if self.task_context_assembler else ["TaskContextAssembler missing"],
            score=1.0 if perception_healthy else 0.5,
        )

        # Memory health
        memory_healthy = self.unified_memory_layer is not None or self.task_context_assembler is not None
        state.health_dimensions['memory'] = HealthDimension(
            name="memory",
            status=HealthStatus.HEALTHY if memory_healthy else HealthStatus.DEGRADED,
            evidence=["UnifiedMemoryLayer or TaskContextAssembler available"] if memory_healthy else ["No memory layer"],
            score=1.0 if memory_healthy else 0.5,
        )

        # Resource health
        resource_state = state.resource_state.get('environment', {})
        if isinstance(resource_state, dict) and resource_state.get('ram_available_mb'):
            ram_mb = resource_state['ram_available_mb']
            # Ensure ram_mb is a number, not a mock
            if isinstance(ram_mb, (int, float)):
                if ram_mb > 4000:
                    resource_status = HealthStatus.HEALTHY
                    resource_score = 1.0
                elif ram_mb > 2000:
                    resource_status = HealthStatus.DEGRADED
                    resource_score = 0.6
                else:
                    resource_status = HealthStatus.BLOCKED
                    resource_score = 0.2
            else:
                resource_status = HealthStatus.UNKNOWN
                resource_score = 0.0
        else:
            resource_status = HealthStatus.UNKNOWN
            resource_score = 0.0

        state.health_dimensions['resource'] = HealthDimension(
            name="resource",
            status=resource_status,
            evidence=[f"RAM available: {ram_mb}MB"] if isinstance(resource_state, dict) else ["Resource state unknown"],
            score=resource_score,
        )

        # Provider health
        provider_state = state.provider_state.get('health', {})
        if isinstance(provider_state, dict):
            available_count = provider_state.get('available_count', 0)
            total_count = provider_state.get('total_providers', 0)
            if total_count > 0 and available_count == total_count:
                provider_status = HealthStatus.HEALTHY
                provider_score = 1.0
            elif available_count > 0:
                provider_status = HealthStatus.DEGRADED
                provider_score = 0.6
            else:
                provider_status = HealthStatus.BLOCKED
                provider_score = 0.0
        else:
            provider_status = HealthStatus.UNKNOWN
            provider_score = 0.0

        state.health_dimensions['provider'] = HealthDimension(
            name="provider",
            status=provider_status,
            evidence=[f"{available_count}/{total_count} providers available"] if isinstance(provider_state, dict) else ["Provider state unknown"],
            score=provider_score,
        )

        # Governance health
        governance_healthy = self.control_master_service is not None
        state.health_dimensions['governance'] = HealthDimension(
            name="governance",
            status=HealthStatus.HEALTHY if governance_healthy else HealthStatus.DEGRADED,
            evidence=["ControlMasterService available"] if governance_healthy else ["ControlMasterService missing"],
            score=1.0 if governance_healthy else 0.5,
        )

        # Validation health
        validation_healthy = self.operational_self_examination_service is not None
        state.health_dimensions['validation'] = HealthDimension(
            name="validation",
            status=HealthStatus.HEALTHY if validation_healthy else HealthStatus.DEGRADED,
            evidence=["OperationalSelfExaminationService available"] if validation_healthy else ["OperationalSelfExaminationService missing"],
            score=1.0 if validation_healthy else 0.5,
        )

        # Integration health (based on connection health)
        connected_count = sum(1 for c in state.connections.values() if c.runtime_reachable)
        total_count = len(state.connections)
        if total_count > 0 and connected_count == total_count:
            integration_status = HealthStatus.HEALTHY
            integration_score = 1.0
        elif connected_count > total_count * 0.5:
            integration_status = HealthStatus.DEGRADED
            integration_score = 0.6
        else:
            integration_status = HealthStatus.BLOCKED
            integration_score = 0.2

        state.health_dimensions['integration'] = HealthDimension(
            name="integration",
            status=integration_status,
            evidence=[f"{connected_count}/{total_count} components reachable"],
            score=integration_score,
        )

    def _generate_recommendations(self, state: InternalMetabolicState) -> None:
        """Generate non-autonomous recommendations based on state."""
        # Resource constraints
        resource_health = state.health_dimensions.get('resource')
        if resource_health and resource_health.status in (HealthStatus.DEGRADED, HealthStatus.BLOCKED):
            state.recommendations.append(
                Recommendation(
                    action="defer",
                    target="resource_intensive_operations",
                    reason=f"Resource health is {resource_health.status.value}",
                    priority="high",
                    estimated_effort="small",
                )
            )

        # Broken chains
        for chain in state.broken_chains:
            if chain.status == ChainStatus.DISCONNECTED:
                state.recommendations.append(
                    Recommendation(
                        action="integrate",
                        target=chain.first_broken_link,
                        reason=f"Chain '{chain.chain_name}' is disconnected at {chain.first_broken_link}",
                        priority="high",
                        estimated_effort="medium",
                    )
                )

        # Provider issues
        provider_health = state.health_dimensions.get('provider')
        if provider_health and provider_health.status == HealthStatus.BLOCKED:
            state.recommendations.append(
                Recommendation(
                    action="investigate",
                    target="provider_health",
                    reason="No providers available",
                    priority="high",
                    estimated_effort="medium",
                )
            )

        # Integration issues
        integration_health = state.health_dimensions.get('integration')
        if integration_health and integration_health.status == HealthStatus.DEGRADED:
            state.recommendations.append(
                Recommendation(
                    action="validate",
                    target="component_wiring",
                    reason=f"Only {integration_health.evidence[0] if integration_health.evidence else 'some'} components reachable",
                    priority="medium",
                    estimated_effort="medium",
                )
            )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _count_severities(self, findings: list[Any]) -> dict[str, int]:
        """Count findings by severity."""
        from collections import Counter

        severities = [getattr(f, 'severity', 'UNKNOWN') for f in findings]
        return dict(Counter(severities))

    def _is_injected(self, component: Any) -> bool:
        """Check if component is injected (has dependencies)."""
        if component is None:
            return False
        # Simple heuristic: if it has any non-trivial attributes, it's likely injected
        return len([a for a in dir(component) if not a.startswith('_')]) > 5

    def _has_production_caller(self, component_name: str) -> bool:
        """Check if component has production caller (lightweight check)."""
        # This is a placeholder - real check would require static analysis
        # We assume major components have production callers
        major_components = {
            'ReflectionRoutingService',
            'ResourceAwareController',
            'TaskContextAssembler',
            'InferenceService',
            'AdaptiveTaskOrchestrator',
        }
        return component_name in major_components

    def _affects_decision(self, component_name: str) -> bool:
        """Check if component affects decision-making."""
        decision_affecting = {
            'ReflectionRoutingService',
            'ResourceAwareController',
            'TaskContextAssembler',
            'ControlMasterService',
        }
        return component_name in decision_affecting

    def _affects_execution(self, component_name: str) -> bool:
        """Check if component affects execution."""
        execution_affecting = {
            'InferenceService',
            'AdaptiveTaskOrchestrator',
            'ResourceAwareController',
            'ToolTeachService',
        }
        return component_name in execution_affecting

    def _is_validated(self, component_name: str) -> bool:
        """Check if component is validated (has tests)."""
        # Placeholder - real check would look for test files
        return False  # UNKNOWN by default

    def _check_chain(self, components: list[str]) -> ChainStatus:
        """Check if a chain of components is connected."""
        available_count = sum(1 for name in components if self._component_available(name))
        if available_count == len(components):
            return ChainStatus.CONNECTED
        elif available_count > 0:
            return ChainStatus.PARTIAL
        else:
            return ChainStatus.DISCONNECTED

    def _component_available(self, component_name: str) -> bool:
        """Check if a component is available."""
        component_map = {
            'ControlMasterService': self.control_master_service,
            'AdaptiveTaskOrchestrator': self.adaptive_task_orchestrator,
            'UnifiedMemoryLayer': self.unified_memory_layer,
            'TaskContextAssembler': self.task_context_assembler,
            'ReflectionRoutingService': self.reflection_routing_service,
            'ResourceAwareController': self.resource_aware_controller,
            'InferenceService': self.inference_service,
        }
        return component_map.get(component_name) is not None

    def _find_broken_link(self, components: list[str]) -> str:
        """Find the first broken link in a chain."""
        for name in components:
            if not self._component_available(name):
                return name
        return "UNKNOWN"

    def self_development_readiness(self) -> dict[str, bool]:
        """Determine whether INTERNAL_STATE provides enough information for future decision layer."""
        state = self.inspect()

        return {
            'can_identify_current_state': bool(state.components or state.resource_state or state.provider_state),
            'can_identify_work': bool(state.current_work and state.current_work.get('work_queue') != 'UNKNOWN'),
            'can_identify_gaps': bool(state.broken_chains or state.orphaned_components),
            'can_identify_disconnected_systems': bool(state.broken_chains),
            'can_identify_duplication': bool(state.duplicated_capabilities),
            'can_identify_resource_constraints': state.health_dimensions.get('resource', HealthDimension(name='resource', status=HealthStatus.UNKNOWN)).status != HealthStatus.UNKNOWN,
            'can_generate_recommendation': bool(state.recommendations),
        }
