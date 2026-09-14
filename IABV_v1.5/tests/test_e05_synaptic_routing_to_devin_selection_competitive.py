"""E05-C20: Prueba causal competitiva — SynapticRouter → devin_api

Demostrar causalidad competitiva fuerte:
CONDICIÓN A: Synaptic OFF → actor ≠ devin_api
CONDICIÓN B: Synaptic ON + evidencia Devin → actor = devin_api

Manteniendo constantes:
- mismo ToolRegistry
- mismos ToolCards (devin_api + gh_cli)
- misma request
- mismos candidatos
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantStrength,
    ExperimentDomain,
    ExperimentRun,
    EvaluationRoute,
    InferenceRequest,
    TaskRole,
    WorldModelSnapshot,
    NetworkStatusSnapshot,
    ToolLiveStatus,
    ToolCard,
    ToolType,
    ToolTask,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.services.tools.tool_registry import ToolRegistry
from iabv_v15.services.tools.tool_validator import ToolValidator
from iabv_v15.services.tools.tool_sandbox import ToolSandbox
from iabv_v15.services.tools.tool_approval_policy import ToolApprovalPolicy
from iabv_v15.services.tools.tool_rollback_manager import ToolRollbackManager
from iabv_v15.services.tools.tool_teach_service import ToolTeachService
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter, LocalCliToolAdapter
from iabv_v15.services.tools.interaction_learning_service import InteractionLearningService
from iabv_v15.services.tools.interaction_mode_selector import InteractionModeSelector
from iabv_v15.services.tools.tool_memory import ToolMemory
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.experiment_lab import ExperimentLab
from iabv_v15.services.lab.strategy_selector import StrategySelector
from iabv_v15.services.evolution.live_audit_supervisor import LiveAuditSupervisor
from iabv_v15.services.roles.assistant_capability_registry import AssistantCapabilityRegistry
from iabv_v15.services.roles.synaptic_router import SynapticRouter
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tool_teach_service_with_cards(
    root: Path,
    *,
    synaptic_router: SynapticRouter | None = None,
) -> ToolTeachService:
    """Construye ToolTeachService real con ToolCards devin_api y gh_cli."""
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    
    # Adapters reales
    devin_adapter = DevinApiToolAdapter(api_key='test_key')
    local_cli_adapter = LocalCliToolAdapter()
    
    adapters = {
        'devin_api': devin_adapter,
        'local_cli': local_cli_adapter,
    }
    
    registry = ToolRegistry(repository, adapters)
    validator = ToolValidator()
    sandbox = ToolSandbox(validator)
    interaction_learning_service = InteractionLearningService(repository)
    mode_selector = InteractionModeSelector(registry, repository)
    memory = ToolMemory(repository, interaction_learning_service)
    
    experiment_lab_repository = ExperimentLabRepository(db, storage)
    experiment_lab = ExperimentLab(
        repository=experiment_lab_repository,
        registry=AlgorithmBenchmarkRegistry(),
        scoring_engine=DecisionScoringEngine(),
        strategy_selector=StrategySelector(),
    )
    
    approval_policy = ToolApprovalPolicy()
    rollback_manager = ToolRollbackManager()
    
    service = ToolTeachService(
        registry=registry,
        memory=memory,
        sandbox=sandbox,
        validator=validator,
        approval_policy=approval_policy,
        rollback_manager=rollback_manager,
        adapters=adapters,
        workspace_root=str(root),
        interaction_learning_service=interaction_learning_service,
        mode_selector=mode_selector,
        experiment_lab=experiment_lab,
        live_audit_supervisor=LiveAuditSupervisor(tool_record_repository=repository, experiment_lab=experiment_lab),
        synaptic_router=synaptic_router,
    )
    
    # Crear ToolCard devin_api
    devin_card = ToolCard(
        tool_id='devin_api',
        title='Devin (Cognition AI)',
        tool_type=ToolType.MCP_CLIENT,
        description='Sesion autonoma via API REST de Devin para tareas de codigo, shell y navegacion.',
        adapter_key='devin_api',
        available=True,
        requires_human_approval=True,
        capabilities=['code_assistance', 'shell_execution', 'web_browsing', 'structured_reasoning'],
        metadata={
            'assistant_kind': 'devin',
            'task_affinities': ['long_implementation', 'pr_creation', 'refactor', 'test_writing', 'ci_fix'],
            'interaction_cost': 'low',
            'manual_effort': 'none',
            'long_running_capable': True,
            'live_desktop_validation_capable': False,
            'repo_patch_capable': True,
            'reasoning_synthesis_capable': True,
            'response_capture_mode': 'tool_result',
            'requires_manual_pasteback': False,
            'session_scope': 'api_session',
            'background_capture_mode': 'devin_api',
            'launch_mode': 'api',
        },
    )
    service.memory.repository.save_card(devin_card)
    
    # Crear ToolCard gh_cli con assistant_kind para routing
    gh_cli_card = ToolCard(
        tool_id='gh_cli',
        title='GitHub CLI',
        tool_type=ToolType.SHELL,
        description='CLI oficial de GitHub para operar auth, repos, PRs e issues desde linea de comandos.',
        adapter_key='local_cli',
        available=True,
        requires_human_approval=True,
        capabilities=['check_version', 'check_auth_status', 'inspect_repo', 'list_prs', 'list_issues'],
        metadata={
            'assistant_kind': 'github',  # Para routing competitivo
            'tool_family': 'github',
            'launch_mode': 'local_cli',
            'response_capture_mode': 'tool_result',
            'requires_manual_pasteback': False,
            'command_name': 'gh',
            'command_aliases': ['gh.exe'],
        },
    )
    service.memory.repository.save_card(gh_cli_card)
    
    return service


def _capability_registry_with_profiles() -> AssistantCapabilityRegistry:
    """Registry con perfiles devin y github para routing competitivo."""
    registry = AssistantCapabilityRegistry()
    
    # Perfil Devin
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.SHELL_EXECUTION,
                AssistantStrength.WEB_BROWSING,
            ],
            confidence=0.9,
        )
    )
    
    # Perfil GitHub (competidor)
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="github",
            display_name="GitHub CLI",
            strengths=[
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            confidence=0.7,
        )
    )
    
    return registry


def _create_devin_history(
    repository: ExperimentLabRepository,
    root: Path,
) -> None:
    """Crea historial Devin que lo favorezca sobre github."""
    # Devin run exitoso con high score
    devin_run = ExperimentRun(
        run_id=f'test_devin_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='synaptic_routing_competitive',
        objective='Test competitive routing to devin for code generation',
        subject_key='code_generation',
        route=EvaluationRoute.CLOUD,
        success=True,
        score=0.95,
        path=f'runs/test_devin_run.json',
        metadata={
            'assistant_kind': 'devin',
            'adaptive_weight': 0.95,  # High weight para favorecer selección
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    repository.save_run(devin_run)
    
    # GitHub run exitoso pero con lower score
    github_run = ExperimentRun(
        run_id=f'test_github_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='synaptic_routing_competitive',
        objective='Test competitive routing to github for code generation',
        subject_key='code_generation',
        route=EvaluationRoute.CLOUD,
        success=True,
        score=0.65,  # Lower score
        path=f'runs/test_github_run.json',
        metadata={
            'assistant_kind': 'github',
            'adaptive_weight': 0.65,  # Lower weight
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    repository.save_run(github_run)


def test_e05_synaptic_routing_to_devin_selection_competitive_causal() -> None:
    """TEST: Causal competitiva SynapticRouter → devin_api.
    
    CONDITION A — CONTROL (Synaptic OFF):
    - Sin routing enabled
    - Sin historial especial Devin
    - Mismo registry (devin_api + gh_cli)
    - Mismos candidatos (devin, github)
    - Resultado esperado: actor ≠ devin_api
    
    CONDITION B — TREATMENT (Synaptic ON + evidencia Devin):
    - Con routing enabled
    - Historial Devin que lo favorezca sobre github
    - Mismo registry
    - Mismos candidatos
    - Resultado esperado: actor = devin_api
    """
    root = _workspace('test_e05_synaptic_routing_competitive')
    
    # Guardar estado original de env var
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    # Candidate assistant kinds (compartidos por A y B)
    candidate_assistant_kinds = ['devin', 'github']
    
    try:
        # === CONDITION A: CONTROL (Synaptic OFF) ===
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'false'
        
        # Crear service SIN SynapticRouter
        service_control = _tool_teach_service_with_cards(root / 'control', synaptic_router=None)
        
        # Crear request SIN tool_id explícito
        request_control = InferenceRequest(
            user_goal='Generate an algorithm for data processing',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'task_kind': 'code_generation',
                'candidate_assistant_kinds': candidate_assistant_kinds,  # Mismos candidatos en A y B
                # NO tool_id aquí
            },
        )
        
        # Verificar FP1: goal_parameters['tool_id'] no existe
        assert 'tool_id' not in request_control.goal_parameters, 'FP1: tool_id no debe existir en goal_parameters'
        
        # Construir task desde request
        task_control = service_control.build_task_from_request(request_control)
        
        # Verificar resultado CONTROL
        assert task_control.metadata.get('synaptic_preferred_assistant_kind', '') == '', \
            'CONTROL: synaptic_preferred_assistant_kind debe ser vacío con routing disabled'
        
        # Verificar que control NO selecciona devin_api (discriminative power)
        control_tool_id = task_control.tool_id
        print(f"CONTROL: tool_id = {control_tool_id}")
        assert control_tool_id != 'devin_api', \
            f'CONTROL: tool_id debe ser diferente de devin_api para demostrar discriminative power, pero es {control_tool_id}'
        
        # === CONDITION B: TREATMENT (Synaptic ON + evidencia Devin) ===
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        # Crear db y storage para historial
        db = AppDatabase(str(root / 'treatment' / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'treatment' / 'tool_teaching'))
        repository = ExperimentLabRepository(db, storage)
        
        # Crear historial Devin que lo favorezca sobre github
        _create_devin_history(repository, root / 'treatment')
        
        # Crear SynapticRouter con perfiles para ambos candidatos
        capability_registry = _capability_registry_with_profiles()
        synaptic_router = SynapticRouter(
            capability_registry=capability_registry,
            adaptive_weight_layer=AdaptiveWeightLayer(),
            world_model_provider=lambda: WorldModelSnapshot(
                network_status=NetworkStatusSnapshot(connected=True, status="ok"),
                tool_live_status=[
                    ToolLiveStatus(assistant_kind="devin", available=True),
                    ToolLiveStatus(assistant_kind="github", available=True),
                ],
            ),
            experiment_lab_repository=repository,
            enabled_override=True,  # Override explícito para test
        )
        
        # Verificar que el router puede cargar el historial
        grouped_runs = synaptic_router._load_grouped_runs()
        print(f"DEBUG: grouped_runs keys = {list(grouped_runs.keys())}")
        
        # Verificar que el router está habilitado
        assert synaptic_router._routing_enabled() == True, 'Router debe estar habilitado'
        
        # Verificar que el router selecciona devin sobre github
        routing_decision = synaptic_router.decide(
            task_kind='code_generation',
            candidate_assistant_kinds=candidate_assistant_kinds,  # Mismos candidatos en A y B
            user_goal='Generate an algorithm for data processing',
        )
        print(f"DEBUG: routing_decision = {routing_decision.model_dump()}")
        assert routing_decision.routing_enabled == True, 'Routing debe estar enabled'
        assert routing_decision.selected_assistant_kind == 'devin', \
            f'SynapticRouter debe seleccionar devin sobre github, pero seleccionó {routing_decision.selected_assistant_kind}'
        
        # Crear service CON SynapticRouter
        service_treatment = _tool_teach_service_with_cards(
            root / 'treatment',
            synaptic_router=synaptic_router,
        )
        
        # Verificar que el service tiene el router inyectado
        assert service_treatment.synaptic_router is not None, 'Service debe tener synaptic_router inyectado'
        assert service_treatment.synaptic_router._routing_enabled() == True, 'Router en service debe estar habilitado'
        
        # Crear request IDÉNTICO al control
        request_treatment = InferenceRequest(
            user_goal='Generate an algorithm for data processing',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'task_kind': 'code_generation',
                'candidate_assistant_kinds': candidate_assistant_kinds,  # Mismos candidatos en A y B
                # NO tool_id aquí - misma condición que control
            },
        )
        
        # Verificar FP1: goal_parameters['tool_id'] no existe
        assert 'tool_id' not in request_treatment.goal_parameters, 'FP1: tool_id no debe existir en goal_parameters'
        
        # Verificar FP6: user_goal no contiene "devin"
        assert 'devin' not in request_treatment.user_goal.lower(), 'FP6: user_goal no debe mencionar devin'
        
        # Construir task desde request
        task_treatment = service_treatment.build_task_from_request(request_treatment)
        
        # Verificar resultado TREATMENT
        synaptic_preferred = task_treatment.metadata.get('synaptic_preferred_assistant_kind', '')
        
        # Debug
        print(f"DEBUG: synaptic_preferred_assistant_kind = {synaptic_preferred}")
        print(f"DEBUG: task_treatment.tool_id = {task_treatment.tool_id}")
        
        # Verificar que synaptic routing seleccionó devin
        assert synaptic_preferred == 'devin', \
            f'TREATMENT: synaptic_preferred_assistant_kind debe ser devin, pero es {synaptic_preferred}'
        
        # Verificar FP4: La selección de devin_api proviene de SynapticRouter
        assert task_treatment.tool_id == 'devin_api', \
            f'TREATMENT: tool_id debe ser devin_api, pero es {task_treatment.tool_id}'
        
        # Verificar ToolCard metadata
        card = service_treatment.registry.pick_card_for_task(task_treatment)
        assert card is not None, 'FP4: ToolCard debe ser resuelto por ToolRegistry'
        assert card.metadata.get('assistant_kind') == 'devin', \
            f'ToolCard metadata assistant_kind debe ser devin, pero es {card.metadata.get("assistant_kind")}'
        assert card.adapter_key == 'devin_api', \
            f'ToolCard adapter_key debe ser devin_api, pero es {card.adapter_key}'
        
        # Verificar causalidad competitiva
        print(f"CAUSALIDAD: CONTROL={control_tool_id} ≠ TREATMENT={task_treatment.tool_id}")
        assert control_tool_id != task_treatment.tool_id, \
            'CAUSALIDAD: Control y Treatment deben producir diferentes tool_ids para demostrar discriminative power'
        
        print('TEST PASS: Causal competitiva SynapticRouter → devin_api demostrada')
        print('  CONTROL: Synaptic OFF → tool_id ≠ devin_api')
        print('  TREATMENT: Synaptic ON + evidencia Devin → tool_id = devin_api')
        print('  CAUSALIDAD: Discriminative power demostrado')
        
    finally:
        # Restaurar env var original
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    print('=== E05-C20: Prueba causal competitiva SynapticRouter → devin_api ===')
    print()
    test_e05_synaptic_routing_to_devin_selection_competitive_causal()
    print()
    print('=== E05-C20: Test completado ===')
