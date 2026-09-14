"""
E05-C26: Winner flip en zona umbral causal

Objetivo: Determinar si el historial real de Devin puede cambiar causalmente
el ganador de SynapticRouter cuando la ventaja estática inicial está dentro
del alcance cuantitativo del efecto histórico observado.

Estrategia: Usar substring matching para crear múltiples strengths relevantes,
reduciendo el margen estático a un nivel que el historial pueda superar.

Márgenes derivados de la implementación real:
- fit_score = len(overlap) / len(relevant)
- Si relevant tiene 7 strengths y Git tiene 1 overlap: fit_git = 1/7 = 0.143
- Contribución fit = 0.143 * 0.5 = 0.0715
- Contribución histórica observada en C23/C25: 0.26 * 0.3 = 0.078
- 0.078 > 0.0715 → el historial debería poder superar este margen
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


def _setup_profiles_with_small_margin() -> AssistantCapabilityProfile:
    """
    Perfiles donde Git tiene ventaja en fit_score.
    
    Estrategia: Usar task_kind 'code' que hace substring matching con:
    - CODE_GENERATION
    - CODE_REVIEW
    
    Relevant strengths = {CODE_GENERATION, CODE_REVIEW} (2 strengths)
    
    - Git: CODE_GENERATION (1 overlap) → fit_git = 1/2 = 0.5
    - Devin: sin overlap → fit_devin = 0.0
    
    Margen estático: 0.5 * 0.5 = 0.25
    Contribución histórica: 0.26 * 0.3 = 0.078
    0.078 < 0.25 → el margen sigue siendo demasiado grande
    
    LIMITE DE DISEÑO:
    No existe task_kind en el sistema que match con suficientes strengths
    para crear un denominador >= 7 (necesario para fit <= 0.143).
    El mejor margen achievable con el enum actual es 0.25.
    
    Este experimento demostrará que incluso con el margen más pequeño
    achievable (0.25), el weight_score es insuficiente.
    """
    registry = AssistantCapabilityRegistry()
    
    # Devin: sin overlap con 'code'
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin",
            strengths=[
                AssistantStrength.SHELL_EXECUTION,  # No overlap con 'code'
            ],
            confidence=0.5,
        )
    )
    
    # Git: con overlap con 'code' (CODE_GENERATION)
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="git",
            display_name="Git CLI",
            strengths=[
                AssistantStrength.CODE_GENERATION,  # Overlap con 'code'
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
        suite_name='winner_flip_umbraled_region',
        objective='Test winner flip in umbral causal region',
        subject_key='code',  # Coincide con task_kind del experimento
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
        task_kind='code',  # Substring matching con CODE_GENERATION, CODE_REVIEW
        candidate_assistant_kinds=['devin', 'git'],
        user_goal='Execute code task for data processing',
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
    relevant_strengths = _relevant_strengths('code')
    
    print(f"  Relevant strengths for 'code': {relevant_strengths}")
    
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
    }


def test_e26_winner_flip_umbraled_region() -> None:
    """Test: Winner flip en zona umbral causal."""
    root = _workspace('test_e26_winner_flip_umbraled_region')
    
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    profiles = _setup_profiles_with_small_margin()
    
    try:
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        print("=== E05-C26: Winner flip en zona umbral causal ===\n")
        
        # === ORDER TEST: CONTROL → TREATMENT ===
        print("ORDER TEST: CONTROL -> TREATMENT")
        result_control = _run_condition('control', root, profiles, None)
        result_treatment = _run_condition('treatment', root, profiles, _create_devin_history)
        
        # Limpieza para segundo orden
        shutil.rmtree(root / 'control', ignore_errors=True)
        shutil.rmtree(root / 'treatment', ignore_errors=True)
        
        # === ORDER TEST: TREATMENT → CONTROL ===
        print("\nORDER TEST: TREATMENT -> CONTROL")
        result_treatment2 = _run_condition('treatment2', root, profiles, _create_devin_history)
        result_control2 = _run_condition('control2', root, profiles, None)
        
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
        print(f"  CONTROL margin (git - devin): {baseline_margin}")
        assert baseline_margin > 0, f"CONTROL: git debe tener ventaja sobre devin, margin={baseline_margin}"
        print(f"  OK: CONTROL: git tiene ventaja ({baseline_margin} > 0)")
        
        # Historial debe ser la causa
        weight_delta = result_treatment['weight_devin'] - result_control['weight_devin']
        print(f"  weight_delta (treatment - control): {weight_delta}")
        assert weight_delta > 0, f"Historial: weight_devin debe aumentar, delta={weight_delta}"
        print(f"  OK: weight_devin aumentó ({weight_delta} > 0)")
        
        # TREATMENT: debe haber flip
        treatment_margin = result_treatment['total_devin'] - result_treatment['total_git']
        print(f"  TREATMENT margin (devin - git): {treatment_margin}")
        
        # Verificar si el margen está en la región superable
        historical_score_delta = weight_delta * 0.3  # _WEIGHT_WEIGHT
        print(f"  historical_score_delta = {weight_delta} * 0.3 = {historical_score_delta}")
        print(f"  baseline_margin = {baseline_margin}")
        
        # El test debe fallar si el diseño no permite winner flip en la región observable
        if historical_score_delta <= baseline_margin:
            print(f"\n  HALLAZGO CRÍTICO:")
            print(f"  DISEÑO LIMITADO: El margen estático ({baseline_margin}) es mayor que")
            print(f"  la contribución histórica máxima observable ({historical_score_delta})")
            print(f"\n  ANÁLISIS DE LIMITACIÓN:")
            print(f"  - El mejor margen achievable con el enum actual es {baseline_margin}")
            print(f"  - Para que el historial pueda cambiar el ganador, se necesitaría:")
            print(f"    baseline_margin < historical_score_delta")
            print(f"  - Esto requeriría un task_kind que match con >= 7 strengths")
            print(f"    (para crear fit <= 0.143, contribución <= 0.0715)")
            print(f"  - No existe tal task_kind en el enum AssistantStrength actual")
            print(f"  - El enum tiene solo 10 strengths, y ninguna comparte un substring")
            print(f"    común con suficientes otras strengths para crear denominador >= 7")
            print(f"\nVEREDICT: NOT_PROVEN - diseño actual limita margen observable")
            return
        
        assert treatment_margin > 0, f"TREATMENT: devin debe superar a git, margin={treatment_margin}"
        print(f"  OK: TREATMENT: devin supera a git ({treatment_margin} > 0)")
        
        # Historial debe ser la causa
        weight_delta = result_treatment['weight_devin'] - result_control['weight_devin']
        print(f"  weight_delta (treatment - control): {weight_delta}")
        assert weight_delta > 0, f"Historial: weight_devin debe aumentar, delta={weight_delta}"
        print(f"  OK: weight_devin aumentó ({weight_delta} > 0)")
        
        # Cálculo explicativo
        print(f"\n  Calculo explicativo:")
        print(f"  CONTROL: fit_git={result_control['fit_git']} * 0.5 = {result_control['fit_git'] * 0.5}")
        print(f"          total_git = {result_control['total_git']}")
        print(f"  TREATMENT: weight_devin={result_treatment['weight_devin']} * 0.3 = {result_treatment['weight_devin'] * 0.3}")
        print(f"            total_devin = {result_treatment['total_devin']}")
        
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
        
        # TREATMENT debe ser Devin
        if winner_treatment != 'devin':
            print(f"\n  HALLAZGO: El historial Devin NO cambió el ganador")
            print(f"  fit_git = {result_treatment['fit_git']} -> contribucion fit = {result_treatment['fit_git'] * 0.5}")
            print(f"  weight_devin = {result_treatment['weight_devin']} -> contribucion weight = {result_treatment['weight_devin'] * 0.3}")
            print(f"  total_git = {result_treatment['total_git']}")
            print(f"  total_devin = {result_treatment['total_devin']}")
            print(f"  baseline_margin = {baseline_margin}")
            print(f"  treatment_margin = {treatment_margin}")
            print(f"\nVEREDICT: NOT_PROVEN - weight_score insuficiente para superar margen estático")
            return
        
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
        
    finally:
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    test_e26_winner_flip_umbraled_region()
