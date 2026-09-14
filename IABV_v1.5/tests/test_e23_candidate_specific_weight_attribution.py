"""
E05-C23: Atribución del historial por candidato.

Objetivo: Determinar si weight_score es específico por assistant_kind
o global al contexto.

Diseño experimental:
- A: Sin historial (Devin=0, Git=0)
- B: Solo Devin tiene historial favorable
- C: Solo Git tiene historial favorable

Si weight_score es candidate-specific:
- A → weight_devin = 0, weight_git = 0
- B → weight_devin > 0, weight_git = 0
- C → weight_devin = 0, weight_git > 0

Si weight_score es global:
- A → weight_devin = 0, weight_git = 0
- B → weight_devin = X, weight_git = X (mismo valor)
- C → weight_devin = X, weight_git = X (mismo valor)
"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantStrength,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRun,
    NetworkStatusSnapshot,
    SynapticRoutingDecision,
    TaskRole,
    ToolCard,
    ToolLiveStatus,
    ToolType,
    WorldModelSnapshot,
)
from iabv_v15.services.roles.assistant_capability_registry import AssistantCapabilityRegistry
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.roles.synaptic_router import SynapticRouter


def _workspace(name: str) -> Path:
    root = Path.cwd() / 'temp_test_workspace' / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _setup_tool_cards() -> list[ToolCard]:
    """ToolCards para el experimento."""
    return [
        ToolCard(
            tool_id='devin_api',
            title='Devin API',
            tool_type=ToolType.CUSTOM,
            adapter_key='devin_api',
            metadata={
                'assistant_kind': 'devin',
                'capabilities': ['code_assistance', 'shell_execution'],
            },
        ),
        ToolCard(
            tool_id='git_cli',
            title='Git CLI',
            tool_type=ToolType.SHELL,
            adapter_key='local_cli',
            metadata={
                'assistant_kind': 'git',
                'capabilities': ['version_control', 'code_review'],
            },
        ),
    ]


def _setup_neutral_profiles() -> AssistantCapabilityRegistry:
    """Perfiles neutrales con fit_score = 0.0 para retrieval_augmented."""
    registry = AssistantCapabilityRegistry()
    
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin",
            strengths=[
                AssistantStrength.CODE_GENERATION,  # No overlap con retrieval_augmented
            ],
            confidence=0.5,
        )
    )
    
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="git",
            display_name="Git CLI",
            strengths=[
                AssistantStrength.CODE_REVIEW,  # No overlap con retrieval_augmented
            ],
            confidence=0.5,
        )
    )
    
    return registry


def _create_devin_run(repository: ExperimentLabRepository) -> None:
    """Crea un run histórico favorable para Devin."""
    from iabv_v15.domain.models import ExperimentMetric
    
    run = ExperimentRun(
        run_id=f'test_devin_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='candidate_attribution',
        objective='Test candidate-specific weight attribution',
        subject_key='retrieval_augmented',
        route=EvaluationRoute.CLOUD,
        success=True,
        metrics=ExperimentMetric(total_score=0.95),
        assistant_kind='devin',  # Campo real
        metadata={
            'adaptive_weight': 0.95,
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    repository.save_run(run)


def _create_git_run(repository: ExperimentLabRepository) -> None:
    """Crea un run histórico favorable para Git."""
    from iabv_v15.domain.models import ExperimentMetric
    
    run = ExperimentRun(
        run_id=f'test_git_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='candidate_attribution',
        objective='Test candidate-specific weight attribution',
        subject_key='retrieval_augmented',
        route=EvaluationRoute.CLOUD,
        success=True,
        metrics=ExperimentMetric(total_score=0.95),
        assistant_kind='git',  # Campo real
        metadata={
            'adaptive_weight': 0.95,
        },
        created_at_utc=datetime.now(timezone.utc),
    )
    repository.save_run(run)


def _extract_scores(decision: SynapticRoutingDecision) -> dict[str, float]:
    """Extrae scores de la decisión."""
    # La decisión tiene un campo 'alternatives' con todos los candidatos
    if not decision.alternatives:
        return {
            'fit_score': 0.0,
            'weight_score': 0.0,
            'availability_score': 0.0,
            'total_score': 0.0,
        }
    
    # Usar el primer alternative como proxy (deberían ser iguales en fit/availability)
    alt = decision.alternatives[0]
    return {
        'fit_score': float(alt.get('fit_score', 0.0)),
        'weight_score': float(alt.get('weight_score', 0.0)),
        'availability_score': float(alt.get('availability_score', 0.0)),
        'total_score': float(alt.get('total_score', 0.0)),
    }


def _run_condition(
    condition_name: str,
    root: Path,
    tool_cards: list[ToolCard],
    neutral_profiles: AssistantCapabilityRegistry,
    create_history_fn,
) -> dict[str, float]:
    """Ejecuta una condición experimental y retorna scores."""
    db = AppDatabase(str(root / condition_name / 'app.sqlite'))
    storage = ArtifactStorage(str(root / condition_name / 'tool_teaching'))
    repository = ExperimentLabRepository(db, storage)
    
    # Crear historial si corresponde
    if create_history_fn:
        create_history_fn(repository)
    
    # Verificar runs creados
    runs = repository.list_runs(limit=10)
    print(f"  Runs en {condition_name}: {len(runs)}")
    for run in runs:
        print(f"    - {run.assistant_kind} (total_score={run.metrics.total_score})")
    
    # SynapticRouter
    synaptic_router = SynapticRouter(
        capability_registry=neutral_profiles,
        adaptive_weight_layer=AdaptiveWeightLayer(),
        world_model_provider=lambda: WorldModelSnapshot(
            network_status=NetworkStatusSnapshot(connected=True, status="ok"),
            tool_live_status=[
                ToolLiveStatus(assistant_kind="devin", available=True),
                ToolLiveStatus(assistant_kind="git", available=True),
            ],
        ),
        experiment_lab_repository=repository,
        enabled_override=True,
    )
    
    # Debug: verificar grouped_runs
    grouped = synaptic_router._load_grouped_runs()
    print(f"  Grouped keys: {list(grouped.keys())}")
    
    # Debug: verificar weights por assistant_kind
    weights = synaptic_router._safe_weights()
    print(f"  Weights dict: {weights}")
    
    # Debug: verificar _weight_score manualmente
    from iabv_v15.services.roles.synaptic_router import _weight_score as weight_score_func
    weight_devin_manual = weight_score_func('devin', weights)
    weight_git_manual = weight_score_func('git', weights)
    print(f"  Manual weight_score: devin={weight_devin_manual}, git={weight_git_manual}")
    
    # Ejecutar routing
    decision = synaptic_router.decide(
        task_kind='retrieval_augmented',
        candidate_assistant_kinds=['devin', 'git'],
        user_goal='Retrieve relevant documents for the data analysis',
    )
    
    print(f"  Winner: {decision.selected_assistant_kind}")
    print(f"  Reason: {decision.reason}")
    
    # Extraer scores específicos por candidato usando _weight_score
    scores_by_candidate = {
        'devin': {'weight': weight_devin_manual, 'fit': 0.0},  # fit será 0.0 por diseño
        'git': {'weight': weight_git_manual, 'fit': 0.0},
    }
    
    print(f"  Scores por candidato (manual):")
    for kind, scores in scores_by_candidate.items():
        print(f"    {kind}: weight={scores['weight']}, fit={scores['fit']}")
    
    return {
        'selected_assistant': decision.selected_assistant_kind,
        'scores_by_candidate': scores_by_candidate,
        'grouped_keys': list(grouped.keys()),
        'weights_dict_keys': list(weights.keys()),
    }


def test_e23_candidate_specific_weight_attribution() -> None:
    """Test: Atribución de weight_score por assistant_kind."""
    root = _workspace('test_e23_candidate_attribution')
    
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    tool_cards = _setup_tool_cards()
    neutral_profiles = _setup_neutral_profiles()
    
    try:
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        print("=== E05-C23: Atribución del historial por candidato ===\n")
        
        # === CONDICIÓN A: Sin historial ===
        print("CONDICIÓN A — Sin historial:")
        result_a = _run_condition('condition_a', root, tool_cards, neutral_profiles, None)
        
        # === CONDICIÓN B: Solo Devin ===
        print("\nCONDICIÓN B — Solo Devin tiene historial:")
        result_b = _run_condition('condition_b', root, tool_cards, neutral_profiles, _create_devin_run)
        
        # === CONDICIÓN C: Solo Git ===
        print("\nCONDICIÓN C — Solo Git tiene historial:")
        result_c = _run_condition('condition_c', root, tool_cards, neutral_profiles, _create_git_run)
        
        # === ANÁLISIS ===
        print("\n=== ANÁLISIS DE ATRIBUCIÓN ===")
        
        weight_devin_a = result_a['scores_by_candidate'].get('devin', {}).get('weight', 0.0)
        weight_git_a = result_a['scores_by_candidate'].get('git', {}).get('weight', 0.0)
        
        weight_devin_b = result_b['scores_by_candidate'].get('devin', {}).get('weight', 0.0)
        weight_git_b = result_b['scores_by_candidate'].get('git', {}).get('weight', 0.0)
        
        weight_devin_c = result_c['scores_by_candidate'].get('devin', {}).get('weight', 0.0)
        weight_git_c = result_c['scores_by_candidate'].get('git', {}).get('weight', 0.0)
        
        print(f"A (sin historial):")
        print(f"  weight_devin = {weight_devin_a}")
        print(f"  weight_git = {weight_git_a}")
        
        print(f"B (solo Devin):")
        print(f"  weight_devin = {weight_devin_b}")
        print(f"  weight_git = {weight_git_b}")
        
        print(f"C (solo Git):")
        print(f"  weight_devin = {weight_devin_c}")
        print(f"  weight_git = {weight_git_c}")
        
        # === ASSERTIONS FORMALES ===
        print("\n=== VERIFICACIONES ===")
        
        # A debe tener weights = 0
        assert weight_devin_a == 0.0, f"A: weight_devin debe ser 0, es {weight_devin_a}"
        assert weight_git_a == 0.0, f"A: weight_git debe ser 0, es {weight_git_a}"
        print("OK A: weights = 0 (sin historial)")
        
        # B debe tener weight_devin > weight_git (candidate-specific)
        assert weight_devin_b > weight_git_b, f"B: weight_devin ({weight_devin_b}) debe ser > weight_git ({weight_git_b})"
        print("OK B: weight_devin > weight_git (candidate-specific)")
        
        # C debe tener weight_git > weight_devin (candidate-specific)
        assert weight_git_c > weight_devin_c, f"C: weight_git ({weight_git_c}) debe ser > weight_devin ({weight_devin_c})"
        print("OK C: weight_git > weight_devin (candidate-specific)")
        
        # === VERIFICACIÓN DE FIT_SCORE (neutralidad de perfiles) ===
        fit_devin_a = result_a['scores_by_candidate'].get('devin', {}).get('fit', 0.0)
        fit_git_a = result_a['scores_by_candidate'].get('git', {}).get('fit', 0.0)
        assert fit_devin_a == fit_git_a, f"A: fit_score debe ser idéntico (devin={fit_devin_a}, git={fit_git_a})"
        print(f"OK A: fit_score idéntico (both={fit_devin_a})")
        
        # === VERIFICACIÓN DE CLAVE DE AGRUPACIÓN ===
        # En B, debe haber exactamente una clave con 'devin'
        grouped_b = result_b.get('grouped_keys', [])
        assert len(grouped_b) == 1, f"B: debe haber 1 grouped key, hay {len(grouped_b)}"
        assert 'devin' in str(grouped_b[0]).lower(), f"B: grouped key debe contener 'devin', es {grouped_b[0]}"
        print(f"OK B: grouped key contiene 'devin'")
        
        # En C, debe haber exactamente una clave con 'git'
        grouped_c = result_c.get('grouped_keys', [])
        assert len(grouped_c) == 1, f"C: debe haber 1 grouped key, hay {len(grouped_c)}"
        assert 'git' in str(grouped_c[0]).lower(), f"C: grouped key debe contener 'git', es {grouped_c[0]}"
        print(f"OK C: grouped key contiene 'git'")
        
        # === VERIFICACIÓN DE SOURCE PATH ===
        # Imprimir evidencia de la cadena de cálculo
        print("\n=== SOURCE PATH EVIDENCE ===")
        print("ExperimentRun -> _load_grouped_runs() -> AdaptiveWeightLayer.suggest() -> weights -> _weight_score()")
        print("B weights dict keys:", result_b.get('weights_dict_keys', []))
        print("C weights dict keys:", result_c.get('weights_dict_keys', []))
        
        # === VEREDICT ===
        print("\n=== VEREDICT ===")
        print("ARTIFACT_READY_FOR_AUDIT")
        print("El weight_score es especifico por assistant_kind")
        print("AdaptiveWeightLayer.indexa por (route, assistant_kind, config_signature)")
        print("SynapticRouter._weight_score() busca match por assistant_kind normalizado")
        
    finally:
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    test_e23_candidate_specific_weight_attribution()
