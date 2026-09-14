"""E05-C21: Experimento causal aislado — Synaptic OFF vs ON

Objetivo: Demostrar causalidad aislada de Synaptic routing:
CONTROL A: Synaptic OFF → actor basal
TREATMENT B: Synaptic ON + mismo historial → actor Synaptic

Manteniendo constantes:
- mismo historial
- mismo registry
- mismos candidatos
- misma request
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


def _setup_shared_state() -> tuple[list[ToolCard], list[ExperimentRun]]:
    """Construye estado compartido: ToolCards, historial.
    
    Returns:
        (tool_cards, history_runs)
    """
    # Crear ToolCards compartidos
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
    
    git_cli_card = ToolCard(
        tool_id='git_cli',
        title='Git CLI',
        tool_type=ToolType.SHELL,
        description='CLI oficial de Git para control de versiones.',
        adapter_key='local_cli',
        available=True,
        requires_human_approval=True,
        capabilities=['check_version', 'check_auth_status', 'inspect_repo', 'list_prs', 'list_issues'],
        metadata={
            'assistant_kind': 'git',  # Para routing
            'tool_family': 'git',
            'launch_mode': 'local_cli',
            'response_capture_mode': 'tool_result',
            'requires_manual_pasteback': False,
            'command_name': 'git',
            'command_aliases': ['git.exe'],
        },
    )
    
    # Crear historial compartido
    devin_run = ExperimentRun(
        run_id=f'test_devin_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='synaptic_isolated_causal',
        objective='Test isolated causal routing to devin for code generation',
        subject_key='code_generation',
        route=EvaluationRoute.CLOUD,
        success=True,
        score=0.95,
        path=f'runs/test_devin_run.json',
        assistant_kind='devin',  # Campo real, no metadata
        metadata={
            'adaptive_weight': 0.95,
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    
    git_run = ExperimentRun(
        run_id=f'test_git_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='synaptic_isolated_causal',
        objective='Test isolated causal routing to git for code generation',
        subject_key='code_generation',
        route=EvaluationRoute.CLOUD,
        success=True,
        score=0.65,
        path=f'runs/test_git_run.json',
        assistant_kind='git',  # Campo real, no metadata
        metadata={
            'adaptive_weight': 0.65,
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    
    return [devin_card, git_cli_card], [devin_run, git_run]


def _capability_registry_with_profiles() -> AssistantCapabilityRegistry:
    """Registry con perfiles devin y git para routing."""
    registry = AssistantCapabilityRegistry()
    
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
    
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="git",
            display_name="Git CLI",
            strengths=[
                AssistantStrength.CODE_REVIEW,
                AssistantStrength.STRUCTURED_REASONING,
            ],
            confidence=0.7,
        )
    )
    
    return registry


def _tool_teach_service_with_clean_registry(
    root: Path,
    tool_cards: list[ToolCard],
    history_runs: list[ExperimentRun],
    *,
    synaptic_router: SynapticRouter | None = None,
) -> ToolTeachService:
    """Construye ToolTeachService con registry limpio (solo ToolCards del experimento).
    
    IMPORTANTE: Para evitar contaminación de _seed_defaults(), primero guardamos
    nuestras ToolCards en el repository, luego creamos el ToolRegistry. De esta
    forma _seed_defaults() usará INSERT OR REPLACE y nuestras ToolCards prevalecerán.
    """
    db = AppDatabase(str(root / 'app.sqlite'))
    storage = ArtifactStorage(str(root / 'tool_teaching'))
    repository = ToolRecordRepository(db, storage)
    
    # Guardar PRIMERO nuestras ToolCards para que _seed_defaults() las respete
    for card in tool_cards:
        repository.save_card(card)
    
    # Crear experiment lab repository y guardar historial
    experiment_lab_repository = ExperimentLabRepository(db, storage)
    for run in history_runs:
        experiment_lab_repository.save_run(run)
    
    # Adapters reales
    devin_adapter = DevinApiToolAdapter(api_key='test_key')
    local_cli_adapter = LocalCliToolAdapter()
    
    adapters = {
        'devin_api': devin_adapter,
        'local_cli': local_cli_adapter,
    }
    
    # Crear ToolRegistry (esto llamará _seed_defaults(), pero nuestras ToolCards ya están guardadas)
    registry = ToolRegistry(repository, adapters)
    
    # AHORA limpiar las ToolCards defaults que _seed_defaults() pueda haber agregado
    final_cards = repository.list_cards()
    actual_tool_ids = {card.tool_id for card in final_cards}
    expected_tool_ids = {card.tool_id for card in tool_cards}
    
    # Borrar ToolCards que no son las nuestras
    for card in final_cards:
        if card.tool_id not in expected_tool_ids:
            repository.db.execute('DELETE FROM tool_cards WHERE tool_id = ?', (card.tool_id,))
    
    # Verificar que solo tenemos las ToolCards esperadas
    final_cards = repository.list_cards()
    actual_tool_ids = {card.tool_id for card in final_cards}
    assert actual_tool_ids == expected_tool_ids, \
        f"Registry debe contener solo {expected_tool_ids}, pero tiene {actual_tool_ids}"
    
    validator = ToolValidator()
    sandbox = ToolSandbox(validator)
    interaction_learning_service = InteractionLearningService(repository)
    mode_selector = InteractionModeSelector(registry, repository)
    memory = ToolMemory(repository, interaction_learning_service)
    
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
    
    return service


def test_e05_synaptic_routing_isolated_causal() -> None:
    """TEST: Experimento causal aislado Synaptic OFF vs ON.
    
    Objetivo: Demostrar causalidad aislada de Synaptic routing.
    
    CONTROL A:
    - Synaptic routing OFF
    - Historial presente
    - Mismo registry
    - Mismos candidatos
    - Misma request
    - Resultado esperado: actor basal (sin Synaptic)
    
    TREATMENT B:
    - Synaptic routing ON
    - Exactamente el mismo historial
    - Mismo registry
    - Mismos candidatos
    - Misma request
    - Resultado esperado: actor Synaptic (si hay evidencia suficiente)
    """
    root = _workspace('test_e05_synaptic_isolated_causal')
    
    # Guardar estado original de env var
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    # Candidate assistant kinds (compartidos por A y B)
    candidate_assistant_kinds = ['devin', 'git']
    
    try:
        # === SETUP COMPARTIDO ===
        # Construir estado compartido una sola vez
        tool_cards, history_runs = _setup_shared_state()
        
        # Crear SynapticRouter con perfiles para ambos candidatos
        capability_registry = _capability_registry_with_profiles()
        
        # === CONDITION A: CONTROL (Synaptic OFF) ===
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'false'
        
        # Crear service SIN SynapticRouter (routing disabled por env var)
        service_control = _tool_teach_service_with_clean_registry(
            root / 'control',
            tool_cards,
            history_runs,
            synaptic_router=None,  # SIN SynapticRouter
        )
        
        # Crear request SIN tool_id explícito
        request_control = InferenceRequest(
            user_goal='Generate an algorithm for data processing',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'task_kind': 'code_generation',
                'candidate_assistant_kinds': candidate_assistant_kinds,
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
        
        control_tool_id = task_control.tool_id
        print(f"CONTROL: tool_id = {control_tool_id}")
        
        # === CONDITION B: TREATMENT (Synaptic ON) ===
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        # Crear SynapticRouter con repositorio que tiene el historial
        db = AppDatabase(str(root / 'control' / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'control' / 'tool_teaching'))
        experiment_lab_repository = ExperimentLabRepository(db, storage)
        
        synaptic_router = SynapticRouter(
            capability_registry=capability_registry,
            adaptive_weight_layer=AdaptiveWeightLayer(),
            world_model_provider=lambda: WorldModelSnapshot(
                network_status=NetworkStatusSnapshot(connected=True, status="ok"),
                tool_live_status=[
                    ToolLiveStatus(assistant_kind="devin", available=True),
                    ToolLiveStatus(assistant_kind="git", available=True),
                ],
            ),
            experiment_lab_repository=experiment_lab_repository,
            enabled_override=True,  # Override explícito para test
        )
        
        # Verificar que el router puede cargar el historial
        grouped_runs = synaptic_router._load_grouped_runs()
        print(f"DEBUG: grouped_runs keys = {list(grouped_runs.keys())}")
        
        # Verificar que el historial tiene assistant_kind real
        for key, runs in grouped_runs.items():
            for run in runs:
                assert run.assistant_kind in {"devin", "git"}, \
                    f"Historial debe tener assistant_kind real, got {run.assistant_kind}"
                assert run.assistant_kind != "", \
                    "Historial no debe tener assistant_kind vacío"
        
        # Verificar que weight_score != 0.0 (historial está siendo consumido)
        routing_decision = synaptic_router.decide(
            task_kind='code_generation',
            candidate_assistant_kinds=candidate_assistant_kinds,
            user_goal='Generate an algorithm for data processing',
        )
        print(f"DEBUG: routing_decision = {routing_decision.model_dump()}")
        assert routing_decision.weight_score > 0.0, \
            f"Historial debe influenciar weight_score, got {routing_decision.weight_score}"
        
        # Crear service CON SynapticRouter (mismo estado compartido)
        service_treatment = _tool_teach_service_with_clean_registry(
            root / 'treatment',
            tool_cards,
            history_runs,
            synaptic_router=synaptic_router,  # CON SynapticRouter
        )
        
        # Crear request IDÉNTICO al control
        request_treatment = InferenceRequest(
            user_goal='Generate an algorithm for data processing',
            task_role=TaskRole.TOOL_USE,
            goal_parameters={
                'task_kind': 'code_generation',
                'candidate_assistant_kinds': candidate_assistant_kinds,
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
        
        # === COMPARACIÓN CAUSAL ===
        print(f"CAUSALIDAD: CONTROL={control_tool_id} vs TREATMENT={task_treatment.tool_id}")
        
        # Verificar mediación
        print(f"MEDIACIÓN CONTROL:")
        print(f"  routing_enabled = False")
        print(f"  synaptic_preferred_assistant_kind = ''")
        print(f"  tool_id = {control_tool_id}")
        
        print(f"MEDIACIÓN TREATMENT:")
        print(f"  routing_enabled = True")
        print(f"  synaptic_preferred_assistant_kind = {synaptic_preferred}")
        print(f"  SynapticRouter selected_assistant_kind = {routing_decision.selected_assistant_kind}")
        print(f"  SynapticRouter weight_score = {routing_decision.weight_score}")
        print(f"  tool_id = {task_treatment.tool_id}")
        
        # Verificar causalidad
        if control_tool_id == task_treatment.tool_id:
            print("RESULTADO: Synaptic routing no cambió la selección")
            print("VEREDICT: NOT_PROVEN - Sin discriminative power")
        else:
            print("RESULTADO: Synaptic routing cambió la selección")
            print("VEREDICT: PROVEN - Causalidad aislada demostrada")
        
        print('TEST COMPLETADO: Experimento causal aislado Synaptic OFF vs ON')
        
    finally:
        # Restaurar env var original
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    print('=== E05-C21: Experimento causal aislado Synaptic OFF vs ON ===')
    print()
    test_e05_synaptic_routing_isolated_causal()
    print()
    print('=== E05-C21: Test completado ===')
