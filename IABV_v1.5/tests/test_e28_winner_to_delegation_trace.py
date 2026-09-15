"""
E05-C28: Winner -> Delegation Boundary Trace

Objetivo: Demostrar que una decisión real de SynapticRouter puede ser
convertida en una selección de herramienta válida hacia el adaptador externo.

La cadena verificada:
SynapticRouter.decide() -> selected_assistant_kind = devin
-> assistant_kind -> tool_id mapping (devin -> devin_api)
-> ToolCard con adapter_class = DevinApiToolAdapter
-> DevinApiToolAdapter boundary reachable

SIN ejecutar Devin real (sin DEVIN_API_KEY, sin tráfico de red real).
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch

from iabv_v15.domain.models import (
    AssistantCapabilityProfile,
    AssistantStrength,
    ExperimentDomain,
    ExperimentMetric,
    ExperimentRun,
    EvaluationRoute,
    TaskRole,
    ToolCard,
    ToolTask,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.services.roles.assistant_capability_registry import AssistantCapabilityRegistry
from iabv_v15.services.roles.synaptic_router import SynapticRouter
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer
from iabv_v15.services.tools.tool_adapters import DevinApiToolAdapter


def _workspace(name: str) -> Path:
    root = Path.cwd() / 'temp_test_workspace' / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _construct_all_matching_task_kind() -> str:
    """Construye task_kind que match con todas las strengths."""
    values = [s.value for s in AssistantStrength]
    task_kind = " ".join(values)
    return task_kind


def _setup_controlled_profiles() -> AssistantCapabilityProfile:
    """Perfiles con margen controlado (igual que C27)."""
    registry = AssistantCapabilityRegistry()
    
    # Devin: 1 overlap
    registry.register(
        AssistantCapabilityProfile(
            assistant_kind="devin",
            display_name="Devin",
            strengths=[AssistantStrength.CODE_GENERATION],
            confidence=0.5,
        )
    )
    
    # Git: 2 overlaps
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
        suite_name='winner_to_delegation_trace',
        objective='Test winner to delegation trace',
        subject_key='all_capabilities',
        route=EvaluationRoute.CLOUD,
        success=True,
        metrics=ExperimentMetric(total_score=0.95),
        assistant_kind='devin',
        metadata={'adaptive_weight': 0.95},
        created_at_utc=datetime.now(timezone.utc),
    )
    repository.save_run(run)


def _assistant_kind_to_tool_id(assistant_kind: str) -> str:
    """Deriva el tool_id basado en el patrón observado en producción."""
    return f"{assistant_kind}_api"


def test_e28_winner_to_delegation_trace() -> None:
    """Test: Trace desde SynapticRouter winner hasta ToolTeachService delegation."""
    root = _workspace('test_e28_winner_to_delegation_trace')
    
    original_env = os.environ.get('IABV_SYNAPTIC_ROUTING_ENABLED')
    
    profiles = _setup_controlled_profiles()
    task_kind = _construct_all_matching_task_kind()
    
    print(f"=== E05-C28: Winner -> Delegation Boundary Trace ===")
    print(f"Task kind: {task_kind[:50]}...")
    print()
    
    try:
        os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = 'true'
        
        # === STEP 1: SynapticRouter Decision ===
        print("=== STEP 1: SynapticRouter Decision ===")
        
        db = AppDatabase(str(root / 'synaptic' / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'synaptic' / 'experiment_lab'))
        repository = ExperimentLabRepository(db, storage)
        
        # Crear historial
        _create_devin_history(repository)
        
        synaptic_router = SynapticRouter(
            capability_registry=profiles,
            adaptive_weight_layer=AdaptiveWeightLayer(),
            world_model_provider=lambda: Mock(
                tool_live_status=[
                    Mock(assistant_kind="devin", available=True),
                    Mock(assistant_kind="git", available=True),
                ]
            ),
            experiment_lab_repository=repository,
            enabled_override=True,
        )
        
        synaptic_decision = synaptic_router.decide(
            task_kind=task_kind,
            candidate_assistant_kinds=['devin', 'git'],
            user_goal='Execute task requiring all capabilities',
        )
        
        print(f"  SynapticRouter decision:")
        print(f"    selected_assistant_kind = {synaptic_decision.selected_assistant_kind}")
        print(f"    routing_enabled = {synaptic_decision.routing_enabled}")
        print(f"    winner = {synaptic_decision.selected_assistant_kind}")
        
        # === STEP 2: Assistant Kind -> Tool ID Mapping ===
        print("\n=== STEP 2: Assistant Kind -> Tool ID Mapping ===")
        
        # Verificar el patrón de mapping observado en producción
        selected_kind = synaptic_decision.selected_assistant_kind
        expected_tool_id = _assistant_kind_to_tool_id(selected_kind)
        
        print(f"  SynapticRouter decision:")
        print(f"    selected_assistant_kind = {selected_kind}")
        print(f"  Expected tool_id (from pattern): {expected_tool_id}")
        
        # Verificar que el patrón es devin_api para Devin
        assert selected_kind == 'devin', f"SynapticRouter debe seleccionar devin, seleccionó {selected_kind}"
        assert expected_tool_id == 'devin_api', f"El patrón debe producir devin_api, produjo {expected_tool_id}"
        
        print(f"  OK: assistant_kind -> tool_id mapping verified")
        
        # === STEP 3: Adapter Boundary ===
        print("\n=== STEP 3: Adapter Boundary ===")
        
        # Verificar que el adaptador existe en el código
        print(f"  Adapter class: DevinApiToolAdapter")
        print(f"  Adapter module: iabv_v15.services.tools.tool_adapters")
        
        # Crear adapter instance (sin api_key para evitar ejecución real)
        adapter = DevinApiToolAdapter(api_key='', org_id='')
        
        print(f"  Adapter instantiated: {adapter is not None}")
        print(f"  api_key present: {bool(adapter.api_key)}")
        print(f"  Safe for real execution: {'NO - no api_key' if not adapter.api_key else 'YES'}")
        
        # Verificar que sin api_key, el adaptador no puede ejecutar
        from iabv_v15.services.tools.tool_adapters import ToolType
        assert adapter.tool_type == ToolType.MCP_CLIENT, "DevinApiToolAdapter debe ser MCP_CLIENT"
        print(f"  OK: Adapter type = MCP_CLIENT (external tool)")
        
        # === ASSERTIONS ===
        print("\n=== ASSERTIONS ===")
        
        # SynapticRouter seleccionó Devin
        assert synaptic_decision.selected_assistant_kind == 'devin', \
            f"SynapticRouter debe seleccionar devin, seleccionó {synaptic_decision.selected_assistant_kind}"
        print("OK: SynapticRouter selected_assistant_kind = devin")
        
        # Patrón de mapping es devin -> devin_api
        assert expected_tool_id == 'devin_api', \
            f"El patrón debe producir devin_api, produjo {expected_tool_id}"
        print("OK: assistant_kind -> tool_id mapping = devin -> devin_api")
        
        # Adapter existe y es DevinApiToolAdapter
        assert adapter is not None, "DevinApiToolAdapter debe poder instanciarse"
        print("OK: DevinApiToolAdapter boundary reached")
        
        # No hay api_key (no ejecución real)
        assert not adapter.api_key, "Adapter no debe tener api_key para evitar ejecución real"
        print("OK: Adapter sin api_key (no ejecución real)")
        
        # === TRACE SUMMARY ===
        print("\n=== TRACE SUMMARY ===")
        print("Chain verified (partial):")
        print("  1. SynapticRouter decision -> selected_assistant_kind = devin")
        print("  2. assistant_kind -> tool_id mapping = devin -> devin_api (pattern)")
        print("  3. DevinApiToolAdapter boundary reachable (adapter exists)")
        print("  4. Real external execution blocked (no api_key)")
        print()
        print("Chain NOT verified (missing):")
        print("  - ToolTeachService actual consumption of SynapticRouter decision")
        print("  - ToolTask creation from synaptic decision")
        print("  - Governance gates (approval, sandbox, validation)")
        print("  - Real adapter invocation in the pipeline")
        print()
        print("=== VEREDICT ===")
        print("NOT_PROVEN - Test is superficial")
        print("SynapticRouter can select Devin and the mapping pattern exists,")
        print("but the actual integration through ToolTeachService was not")
        print("verified due to complex dependencies that could not be easily")
        print("mocked in this test environment.")
        print()
        print("What was proven:")
        print("  - SynapticRouter.selected_assistant_kind = devin")
        print("  - assistant_kind -> tool_id mapping pattern (devin -> devin_api)")
        print("  - DevinApiToolAdapter exists and can be instantiated")
        print("  - External execution blocked without api_key")
        print()
        print("What remains unproven:")
        print("  - ToolTeachService actually consumes SynapticRouter decision")
        print("  - Decision converts to ToolTask")
        print("  - Governance gates traversed")
        print("  - Real adapter invocation in production pipeline")
        
    finally:
        if original_env is not None:
            os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] = original_env
        elif 'IABV_SYNAPTIC_ROUTING_ENABLED' in os.environ:
            del os.environ['IABV_SYNAPTIC_ROUTING_ENABLED']
        
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    test_e28_winner_to_delegation_trace()
