"""
E05-C27: Demostración causal del winner flip por experiencia histórica

Objetivo: Demostrar o refutar que la inclusión de experiencia histórica de Devin,
manteniendo controlados los demás factores, puede cambiar causalmente el ganador
de SynapticRouter.

Región experimental (identificada por auditoría C26):
- relevant strengths = 10 (todas las strengths del enum)
- Git overlap = 2 → fit_git = 2/10 = 0.2
- Devin overlap = 1 → fit_devin = 1/10 = 0.1
- Δfit = 0.1
- fit contribution difference = 0.1 * 0.5 = 0.05
- Historical contribution = 0.26 * 0.3 = 0.078
- 0.078 > 0.05 → el historial debería poder superar el margen

La cadena causal buscada:
CONTROL: Git winner (margin ~0.05)
HISTORIAL → weight Devin aumenta → score Devin aumenta
TREATMENT: Devin winner
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantStrength,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    EvaluationRoute,
    NetworkStatusSnapshot,
    WorldModelSnapshot,
    ToolLiveStatus,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.services.roles.assistant_capability_registry import AssistantCapabilityRegistry
from iabv_v15.services.roles.synaptic_router import SynapticRouter
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer


def _workspace(name: str) -> Path:
    root = Path.cwd() / 'temp_test_workspace' / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _construct_all_matching_task_kind() -> str:
    """
    Construye un task_kind que match con todas las strengths del enum.
    
    Debido al substring matching bidireccional en _relevant_strengths():
    key in strength.value OR strength.value in key
    
    Si usamos un string que contiene todos los substrings únicos de las strengths,
    todas las strengths matchearán.
    
    Substrings únicos de AssistantStrength.values():
    - code (en code_generation, code_review)
    - generation (en code_generation)
    - review (en code_review)
    - long (en long_context_synthesis)
    - context (en long_context_synthesis)
    - synthesis (en long_context_synthesis)
    - shell (en shell_execution)
    - execution (en shell_execution)
    - web (en web_browsing)
    - browsing (en web_browsing)
    - multimodal (en multimodal_vision)
    - vision (en multimodal_vision)
    - structured (en structured_reasoning)
    - reasoning (en structured_reasoning)
    - creative (en creative_writing)
    - writing (en creative_writing)
    - mathematical (en mathematical_reasoning)
    - math (en mathematical_reasoning)
    - retrieval (en retrieval_augmented)
    - augmented (en retrieval_augmented)
    
    Para simplificar, usamos un string que contenga todos los value strings unidos.
    """
    values = [s.value for s in AssistantStrength]
    # Unir con espacios para que cada substring individual esté presente
    task_kind = " ".join(values)
    return task_kind


def _setup_controlled_profiles() -> AssistantCapabilityProfile:
    """
    Perfiles con margen controlado:
    - Git: 2 overlaps de 10 relevant → fit_git = 0.2
    - Devin: 1 overlap de 10 relevant → fit_devin = 0.1
    - Δfit = 0.1
    - fit contribution difference = 0.1 * 0.5 = 0.05
    """
    registry = AssistantCapabilityRegistry()
    
    # Devin: 1 overlap (CODE_GENERATION)
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin",
            strengths=[
                AssistantStrength.CODE_GENERATION,
            ],
            confidence=0.5,
        )
    )
    
    # Git: 2 overlaps (CODE_GENERATION, CODE_REVIEW)
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="git",
            display_name="Git CLI",
            strengths=[
                AssistantStrength.CODE_GENERATION,
                AssistantStrength.CODE_REVIEW,
            ],
            confidence=0.5,
        )
    )
    
    return registry


def _create_devin_history(repository: ExperimentLabRepository) -> None:
    """Crea historial favorable a Devin."""
    run = ExperimentRun(
        run_id=f'test_devin_run_{uuid4().hex}',
        domain=ExperimentDomain.CLOUD_REASONING,
        suite_name='historical_winner_flip',
        objective='Test causal winner flip by historical experience',
        subject_key='all_capabilities',  # Coincide con task_kind del experimento
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


def _run_condition(
    condition_name: str,
    root: Path,
    profiles: AssistantCapabilityProfile,
    create_history_fn,
    task_kind: str,
) -> dict[str, any]:
    """Ejecuta una condición experimental y retorna datos completos."""
    db = AppDatabase(str(root / condition_name / 'app.sqlite'))
    storage = ArtifactStorage(str(root / condition_name / 'tool_teaching'))
    repository = ExperimentLabRepository(db, storage)
    
    # Crear historial si corresponde
    if create_history_fn:
        create_history_fn(repository)
    
    # Verificar runs
    runs = repository.list_runs(limit=10)
    print(f"  Runs en {condition_name}: {len(runs)}")
    for run in runs:
        print(f"    - {run.assistant_kind} (total_score={run.metrics.total_score})")
    
    # SynapticRouter
    synaptic_router = SynapticRouter(
        capability_registry=profiles,
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
    
    # Debug: verificar weights
    weights = synaptic_router._safe_weights()
    print(f"  Weights dict: {weights}")
    
    # Ejecutar routing
    decision = synaptic_router.decide(
        task_kind=task_kind,
        candidate_assistant_kinds=['devin', 'git'],
        user_goal='Execute task requiring all capabilities',
    )
    
    print(f"  Winner: {decision.selected_assistant_kind}")
    print(f"  Reason: {decision.reason}")
    
    # Extraer scores por candidato usando el pipeline real
    from iabv_v15.services.roles.synaptic_router import (
        _weight_score as weight_score_func,
        _fit_score,
        _availability_score,
        _relevant_strengths,
        _FIT_WEIGHT,
        _WEIGHT_WEIGHT,
        _AVAILABILITY_WEIGHT,
    )
    
    weight_devin = weight_score_func('devin', weights)
    weight_git = weight_score_func('git', weights)
    
    world_model = synaptic_router._safe_world_model()
    relevant_strengths = _relevant_strengths(task_kind)
    
    print(f"  Relevant strengths: {relevant_strengths}")
    print(f"  Relevant count: {len(relevant_strengths)}")
    
    fit_devin = _fit_score(profiles.get_or_default('devin'), relevant_strengths)
    fit_git = _fit_score(profiles.get_or_default('git'), relevant_strengths)
    
    availability_devin = _availability_score('devin', world_model)
    availability_git = _availability_score('git', world_model)
    
    # Calcular total_score usando la fórmula real
    total_devin = round(
        fit_devin * _FIT_WEIGHT
        + weight_devin * _WEIGHT_WEIGHT
        + availability_devin * _AVAILABILITY_WEIGHT,
        4
    )
    total_git = round(
        fit_git * _FIT_WEIGHT
        + weight_git * _WEIGHT_WEIGHT
        + availability_git * _AVAILABILITY_WEIGHT,
        4
    )
    
    return {
        'selected_assistant': decision.selected_assistant_kind,
        'fit_devin': fit_devin,
        'fit_git': fit_git,
        'weight_devin': weight_devin,
        'weight_git': weight_git,
        'availability_devin': availability_devin,
        'availability_git': availability_git,
        'total_devin': total_devin,
        'total_git': total_git,
        'grouped_keys': list(grouped.keys()),
        'weights_dict_keys': list(weights.keys()),
        'relevant_count': len(relevant_strengths),
    }


def test_e27_historical_winner_flip() -> None:
    """Test: Demostración causal del winner flip por experiencia histórica."""
    root = _workspace('test_e27_historical_winner_flip')
    
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    profiles = _setup_controlled_profiles()
    task_kind = _construct_all_matching_task_kind()
    
    print(f"=== E05-C27: Demostración causal del winner flip ===")
    print(f"Task kind: {task_kind[:50]}...")
    print()
    
    try:
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        # === ORDER TEST: CONTROL → TREATMENT ===
        print("ORDER TEST: CONTROL -> TREATMENT")
        result_control = _run_condition('control', root, profiles, None, task_kind)
        result_treatment = _run_condition('treatment', root, profiles, _create_devin_history, task_kind)
        
        # Limpieza para segundo orden
        shutil.rmtree(root / 'control', ignore_errors=True)
        shutil.rmtree(root / 'treatment', ignore_errors=True)
        
        # === ORDER TEST: TREATMENT → CONTROL ===
        print("\nORDER TEST: TREATMENT -> CONTROL")
        result_treatment2 = _run_condition('treatment2', root, profiles, _create_devin_history, task_kind)
        result_control2 = _run_condition('control2', root, profiles, None, task_kind)
        
        # === VERIFICACIÓN DE ORDER INDEPENDENCE ===
        print("\n=== ORDER INDEPENDENCE ===")
        
        assert result_control['selected_assistant'] == result_control2['selected_assistant'], \
            "Order independence: CONTROL winner must be identical"
        assert result_treatment['selected_assistant'] == result_treatment2['selected_assistant'], \
            "Order independence: TREATMENT winner must be identical"
        print("OK: Order independence verified")
        
        # === ANÁLISIS DE ATRIBUCIÓN (usando primer orden) ===
        print("\n=== ANALISIS DE ATRIBUCION ===")
        
        print(f"CONTROL (sin historial):")
        print(f"  relevant_count = {result_control['relevant_count']}")
        print(f"  fit_devin = {result_control['fit_devin']}")
        print(f"  fit_git = {result_control['fit_git']}")
        print(f"  weight_devin = {result_control['weight_devin']}")
        print(f"  weight_git = {result_control['weight_git']}")
        print(f"  availability_devin = {result_control['availability_devin']}")
        print(f"  availability_git = {result_control['availability_git']}")
        print(f"  total_devin = {result_control['total_devin']}")
        print(f"  total_git = {result_control['total_git']}")
        print(f"  winner = {result_control['selected_assistant']}")
        
        print(f"\nTREATMENT (con historial Devin):")
        print(f"  relevant_count = {result_treatment['relevant_count']}")
        print(f"  fit_devin = {result_treatment['fit_devin']}")
        print(f"  fit_git = {result_treatment['fit_git']}")
        print(f"  weight_devin = {result_treatment['weight_devin']}")
        print(f"  weight_git = {result_treatment['weight_git']}")
        print(f"  availability_devin = {result_treatment['availability_devin']}")
        print(f"  availability_git = {result_treatment['availability_git']}")
        print(f"  total_devin = {result_treatment['total_devin']}")
        print(f"  total_git = {result_treatment['total_git']}")
        print(f"  winner = {result_treatment['selected_assistant']}")
        
        # === VERIFICACIÓN MATEMÁTICA DEL MARGEN ===
        print("\n=== VERIFICACION MATEMATICA ===")
        
        # CONTROL: debe haber ventaja estática del competidor
        baseline_margin = result_control['total_git'] - result_control['total_devin']
        print(f"  baseline_margin (git - devin): {baseline_margin}")
        assert baseline_margin > 0, f"CONTROL: git debe tener ventaja sobre devin, margin={baseline_margin}"
        print(f"  OK: CONTROL: git tiene ventaja ({baseline_margin} > 0)")
        
        # Verificar que el margen está en la región esperada
        expected_fit_diff = result_control['fit_git'] - result_control['fit_devin']
        expected_margin = expected_fit_diff * 0.5  # _FIT_WEIGHT
        print(f"  fit_diff = {expected_fit_diff}")
        print(f"  expected_margin = {expected_fit_diff} * 0.5 = {expected_margin}")
        
        # Historial debe ser la causa
        weight_delta = result_treatment['weight_devin'] - result_control['weight_devin']
        print(f"  weight_delta (treatment - control): {weight_delta}")
        assert weight_delta > 0, f"Historial: weight_devin debe aumentar, delta={weight_delta}"
        print(f"  OK: weight_devin aumentó ({weight_delta} > 0)")
        
        # Historical score delta
        historical_score_delta = weight_delta * 0.3  # _WEIGHT_WEIGHT
        print(f"  historical_score_delta = {weight_delta} * 0.3 = {historical_score_delta}")
        
        # Verificar que el histórico puede superar el margen
        assert historical_score_delta > baseline_margin, \
            f"HISTORIAL INSUFICIENTE: El margen estático ({baseline_margin}) es mayor que " \
            f"la contribución histórica ({historical_score_delta}). " \
            f"Esto indica que la configuración no está en la región superable."
        print(f"  OK: historical_score_delta > baseline_margin ({historical_score_delta} > {baseline_margin})")
        
        # TREATMENT: debe haber flip
        treatment_margin = result_treatment['total_devin'] - result_treatment['total_git']
        print(f"  treatment_margin (devin - git): {treatment_margin}")
        assert treatment_margin > 0, f"TREATMENT: devin debe superar a git, margin={treatment_margin}"
        print(f"  OK: TREATMENT: devin supera a git ({treatment_margin} > 0)")
        
        # === ASSERTIONS FORMALES CAUSALES ===
        print("\n=== ASSERTIONS CAUSALES ===")
        
        # CONTROL: sin historial
        assert result_control['weight_devin'] == 0.0, f"CONTROL: weight_devin debe ser 0, es {result_control['weight_devin']}"
        assert result_control['weight_git'] == 0.0, f"CONTROL: weight_git debe ser 0, es {result_control['weight_git']}"
        print("OK CONTROL: weights = 0 (sin historial)")
        
        # TREATMENT: con historial Devin
        assert result_treatment['weight_devin'] > 0.0, f"TREATMENT: weight_devin debe ser > 0, es {result_treatment['weight_devin']}"
        assert result_treatment['weight_git'] == 0.0, f"TREATMENT: weight_git debe ser 0, es {result_treatment['weight_git']}"
        print("OK TREATMENT: weight_devin > 0, weight_git = 0 (historial Devin)")
        
        # Availability neutro
        assert result_control['availability_devin'] == result_control['availability_git'], \
            f"CONTROL: availability debe ser idéntico (devin={result_control['availability_devin']}, git={result_control['availability_git']})"
        assert result_treatment['availability_devin'] == result_treatment['availability_git'], \
            f"TREATMENT: availability debe ser idéntico (devin={result_treatment['availability_devin']}, git={result_treatment['availability_git']})"
        print("OK: availability neutro (ambos idénticos)")
        
        # Clave de agrupación
        assert len(result_treatment['grouped_keys']) == 1, f"TREATMENT: debe haber 1 grouped key, hay {len(result_treatment['grouped_keys'])}"
        assert 'devin' in str(result_treatment['grouped_keys'][0]).lower(), \
            f"TREATMENT: grouped key debe contener 'devin', es {result_treatment['grouped_keys'][0]}"
        print("OK TREATMENT: grouped key contiene 'devin'")
        
        # === CAUSALIDAD: El ganador debe cambiar ===
        print("\n=== CAUSALIDAD ===")
        
        winner_control = result_control['selected_assistant']
        winner_treatment = result_treatment['selected_assistant']
        
        print(f"  winner_control = {winner_control}")
        print(f"  winner_treatment = {winner_treatment}")
        
        # CONTROL debe ser git (competidor con ventaja estática)
        assert winner_control == 'git', \
            f"CONTROL: winner debe ser git (competidor con ventaja estática), es {winner_control}"
        print(f"OK CONTROL: winner = git (competidor con ventaja estática)")
        
        # CONTROL: Git debe tener estrictamente mayor score
        assert result_control['total_git'] > result_control['total_devin'], \
            f"CONTROL: total_git debe ser > total_devin, git={result_control['total_git']}, devin={result_control['total_devin']}"
        print(f"OK CONTROL: total_git > total_devin (ventaja estricta)")
        
        # TREATMENT: debe ser Devin
        assert winner_treatment == 'devin', \
            f"TREATMENT: winner debe be Devin, es {winner_treatment}"
        print(f"OK TREATMENT: winner = devin")
        
        # Los ganadores deben ser diferentes
        assert winner_control != winner_treatment, \
            f"Causalidad: winners deben diferir (CONTROL={winner_control}, TREATMENT={winner_treatment})"
        print(f"OK Causalidad: winner cambió de {winner_control} a {winner_treatment}")
        
        # No tie-break
        assert result_treatment['total_devin'] > result_treatment['total_git'], \
            f"TREATMENT: total_devin debe ser > total_git (devin={result_treatment['total_devin']}, git={result_treatment['total_git']})"
        print(f"OK TREATMENT: total_score diferencial (no tie-break)")
        
        # === SOURCE PATH EVIDENCE ===
        print("\n=== SOURCE PATH EVIDENCE ===")
        print("ExperimentRun -> _load_grouped_runs() -> AdaptiveWeightLayer.suggest() -> weights -> _weight_score()")
        print("TREATMENT weights dict keys:", result_treatment['weights_dict_keys'])
        
        # === VEREDICT ===
        print("\n=== VEREDICT ===")
        print("PROVEN - Causalidad histórica sobre el ganador demostrada")
        print("El historial de Devin causó:")
        print("  1. weight_devin > weight_git")
        print("  2. total_devin > total_git")
        print("  3. winner cambió de git a devin")
        print("  4. Sin tie-break, sin inyección manual, sin metadata falsa")
        print("  5. Reproducible en ambos órdenes")
        
    finally:
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    test_e27_historical_winner_flip()
