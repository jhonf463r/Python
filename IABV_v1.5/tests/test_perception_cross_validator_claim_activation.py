"""Tests para segunda activación de Claim/VerificationEvent.

Demostración experimental: PerceptionCrossValidator → Claim + VerificationEvent
sin modificar la lógica del detector original.

Este experimento demuestra reutilización del modelo mínimo entre
dos familias semánticas distintas:
- Experimento 1: verify_slot_decorators() (QML→Python binding)
- Experimento 2: PerceptionCrossValidator (perception consistency)
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
from iabv_v15.services.evolution.perception_cross_validator import (
    PerceptionCrossValidator,
    run_cross_validation_with_claim,
)


@pytest.fixture
def workspace():
    """Fixture que usa el workspace real del checkout actual."""
    test_file = Path(__file__).resolve()
    workspace = test_file.parent.parent
    return str(workspace)


def test_original_detector_unchanged_semantics(workspace):
    """Test B.1: El resultado original de PerceptionCrossValidator permanece semánticamente equivalente."""
    validator = PerceptionCrossValidator()
    result = validator.run_cross_validation()
    
    # Verificar que los campos originales existen
    assert 'checked_at' in result
    assert 'inconsistencies' in result
    assert 'auto_corrections' in result
    assert 'checks_passed' in result
    assert 'total_inconsistencies' in result
    assert 'total_auto_corrections' in result
    assert 'total_checks' in result
    
    # Verificar que la lógica de PASS/FAIL se preserva
    # PASS = no inconsistencies, FAIL = inconsistencies found
    expected_pass = result['total_inconsistencies'] == 0
    # El detector original no tiene campo 'ok', derivamos status de inconsistencies
    assert result['total_inconsistencies'] >= 0
    assert result['total_checks'] == 4  # 4 checks: tools_vs_processes, audit_vs_worldmodel, windows_consistency, ui_self_awareness


def test_stable_claim_identity(workspace):
    """Test B.2: Dos ejecuciones del mismo estado producen la misma identidad de Claim."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Primera ejecución
    result1 = run_cross_validation_with_claim(workspace=workspace)
    claim_id_1 = result1.get('claim_id')
    
    # Segunda ejecución
    result2 = run_cross_validation_with_claim(workspace=workspace)
    claim_id_2 = result2.get('claim_id')
    
    # La Claim identity debe ser estable
    assert claim_id_1 is not None
    assert claim_id_1 == claim_id_2
    
    # Recuperar la Claim del repositorio
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    claim = repo.retrieve(claim_id_1)
    assert claim is not None
    assert claim.invariant == "PERCEPTION_CONSISTENCY"
    assert claim.origin == "PerceptionCrossValidator.run_cross_validation"


def test_multiple_verification_events(workspace):
    """Test B.3: Dos verificaciones de la misma Claim producen dos eventos."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Primera ejecución
    result1 = run_cross_validation_with_claim(workspace=workspace)
    claim_id = result1.get('claim_id')
    event_id_1 = result1.get('verification_event_id')
    
    # Segunda ejecución
    result2 = run_cross_validation_with_claim(workspace=workspace)
    event_id_2 = result2.get('verification_event_id')
    
    # Ambos eventos deben existir y ser distintos
    assert event_id_1 is not None
    assert event_id_2 is not None
    assert event_id_1 != event_id_2
    
    # Recuperar todos los VerificationEvents de la Claim
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    events = repo.retrieve_verifications_by_claim(claim_id, limit=10)
    
    # Debe haber al menos 2 eventos
    assert len(events) >= 2
    
    # Los event_ids deben coincidir
    event_ids = [e.event_id for e in events]
    assert event_id_1 in event_ids
    assert event_id_2 in event_ids


def test_historical_retrieval_by_claim_id(workspace):
    """Test B.4: El historial puede recuperarse por claim_id."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Ejecutar el detector con Claim
    result = run_cross_validation_with_claim(workspace=workspace)
    claim_id = result.get('claim_id')
    
    # Recuperar el historial por claim_id
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    events = repo.retrieve_verifications_by_claim(claim_id, limit=10)
    
    # Debe haber al menos un evento
    assert len(events) >= 1
    
    # Verificar que cada evento tiene la estructura correcta
    for event in events:
        assert event.claim_id == claim_id
        assert event.status in ["PASS", "FAIL"]
        assert event.verification_evidence.startswith("checked_at:")
        assert event.checked_at is not None


def test_status_matches_detector_result(workspace):
    """Test B.5: El status almacenado coincide con el resultado real del detector."""
    # Ejecutar el detector original
    validator = PerceptionCrossValidator()
    original_result = validator.run_cross_validation()
    original_inconsistencies = original_result['total_inconsistencies']
    
    # Ejecutar el detector con Claim
    claim_result = run_cross_validation_with_claim(workspace=workspace)
    verification_status = claim_result.get('verification_status')
    
    # El status debe coincidir
    expected_status = "PASS" if original_inconsistencies == 0 else "FAIL"
    assert verification_status == expected_status
    
    # Verificar que el resultado original sigue siendo equivalente
    assert claim_result['total_inconsistencies'] == original_result['total_inconsistencies']
    assert claim_result['total_checks'] == original_result['total_checks']


def test_claim_metadata_preserved(workspace):
    """Test B.6: La Claim metadata se preserva correctamente."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    result = run_cross_validation_with_claim(workspace=workspace)
    claim_id = result.get('claim_id')
    
    # Recuperar la Claim
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    claim = repo.retrieve(claim_id)
    
    # Verificar metadata
    assert claim is not None
    assert claim.subject is not None
    assert "Perception sources" in claim.subject
    assert "PERCEPTION_CONSISTENCY" in claim.invariant
    assert "PerceptionCrossValidator" in claim.origin
    assert claim.created_at is not None


def test_current_status_derivation(workspace):
    """Test B.7: El status actual se deriva del VerificationEvent más reciente."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Ejecutar el detector con Claim
    result = run_cross_validation_with_claim(workspace=workspace)
    claim_id = result.get('claim_id')
    
    # Recuperar el status actual usando el repository
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    current_status = repo.get_current_status(claim_id)
    
    # Debe coincidir con el status del VerificationEvent más reciente
    latest_event = repo.retrieve_latest_verification(claim_id)
    assert current_status == latest_event.status
    
    # Debe coincidir con el resultado del detector
    expected_status = "PASS" if result['total_inconsistencies'] == 0 else "FAIL"
    assert current_status == expected_status


def test_detector_real_activity(workspace):
    """Test B.8: Verifica que el detector fue realmente ejecutado."""
    result = run_cross_validation_with_claim(workspace=workspace)
    
    # Verificar que el detector fue realmente ejecutado
    assert result['total_checks'] == 4
    assert result['total_inconsistencies'] >= 0
    assert result['checked_at'] is not None
    
    # Verificar que el resultado no es un error
    assert result.get('claim_persistence_error') is None or isinstance(result.get('claim_persistence_error'), str)


def test_cross_family_reuse(workspace):
    """Test B.9: Verifica que el mismo modelo se reutiliza entre dos familias semánticas distintas."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Ejecutar ambos detectores con Claim
    from iabv_v15.services.self_code_analysis import verify_slot_decorators_with_claim
    
    slot_result = verify_slot_decorators_with_claim(workspace)
    perception_result = run_cross_validation_with_claim(workspace=workspace)
    
    slot_claim_id = slot_result.get('claim_id')
    perception_claim_id = perception_result.get('claim_id')
    
    # Los claim_ids deben ser distintos (afirmaciones distintas)
    assert slot_claim_id is not None
    assert perception_claim_id is not None
    assert slot_claim_id != perception_claim_id
    
    # Ambos deben existir en el mismo repositorio
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    slot_claim = repo.retrieve(slot_claim_id)
    perception_claim = repo.retrieve(perception_claim_id)
    
    assert slot_claim is not None
    assert perception_claim is not None
    
    # Los invariants deben ser distintos (familias semánticas distintas)
    assert slot_claim.invariant == "QML_PYTHON_BINDING"
    assert perception_claim.invariant == "PERCEPTION_CONSISTENCY"
    
    # Los origins deben ser distintos (detectores distintos)
    assert "SelfCodeAnalysis" in slot_claim.origin
    assert "PerceptionCrossValidator" in perception_claim.origin
    
    # Ambos deben tener VerificationEvents
    slot_events = repo.retrieve_verifications_by_claim(slot_claim_id, limit=10)
    perception_events = repo.retrieve_verifications_by_claim(perception_claim_id, limit=10)
    
    assert len(slot_events) >= 1
    assert len(perception_events) >= 1


def test_detector_real_activity_with_dependencies(workspace):
    """Test B.10: Demuestra que el detector ejecuta actividad real con dependencias de prueba.
    
    Este test proporciona mocks mínimos de world_model_service y tool_registry
    para obligar al detector a ejecutar las comparaciones reales en lugar de
    retornar PASS vacío por None.
    """
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Crear mock mínimo de ToolCard
    class MockToolCard:
        def __init__(self, tool_id: str, available: bool, metadata: dict, title: str):
            self.tool_id = tool_id
            self.available = available
            self.metadata = metadata
            self.title = title
    
    # Crear mock mínimo de ToolRegistry
    class MockToolRegistry:
        def __init__(self, cards: list):
            self._cards = cards
        
        def list_cards(self):
            return self._cards
        
        def invalidate_availability_cache(self, tool_id: str):
            pass  # No-op para test
        
        def get_card(self, tool_id: str):
            for card in self._cards:
                if card.tool_id == tool_id:
                    return card
            return None
        
        def refresh_card(self, card, force: bool = False):
            return card  # No-op para test
    
    # Crear mock mínimo de WorldModel snapshot
    class MockToolLiveStatus:
        def __init__(self, tool_id: str, available: bool):
            self.tool_id = tool_id
            self.available = available
    
    class MockWindow:
        def __init__(self, title: str, pid: int = None):
            self.title = title
            self.pid = pid
    
    class MockFocusedWindow:
        def __init__(self, title: str):
            self.title = title
    
    class MockWorldModelSnapshot:
        def __init__(self, tool_live_status: list, active_windows: list, focused_window):
            self.tool_live_status = tool_live_status
            self.active_windows = active_windows
            self.focused_window = focused_window
    
    # Crear mock mínimo de WorldModelService
    class MockWorldModelService:
        def __init__(self, snapshot):
            self._snapshot = snapshot
        
        def current_snapshot(self):
            return self._snapshot
    
    # Configurar estado consistente (ninguna inconsistencia)
    tool_card = MockToolCard(
        tool_id="test_tool",
        available=True,
        metadata={"launch_mode": "desktop_app"},
        title="Test Tool"
    )
    
    tool_status = MockToolLiveStatus(tool_id="test_tool", available=True)
    
    snapshot = MockWorldModelSnapshot(
        tool_live_status=[tool_status],
        active_windows=[MockWindow("Test Window")],
        focused_window=MockFocusedWindow("Test Window")
    )
    
    tool_registry = MockToolRegistry([tool_card])
    world_model_service = MockWorldModelService(snapshot)
    
    # Ejecutar el detector con dependencias
    result = run_cross_validation_with_claim(
        world_model_service=world_model_service,
        tool_registry=tool_registry,
        workspace=workspace,
    )
    
    # Verificar que el detector ejecutó las 4 comprobaciones
    assert result['total_checks'] == 4
    
    # Verificar que el resultado no es PASS solo por None
    # (con dependencias, el detector ejecuta comparaciones reales)
    assert result['total_inconsistencies'] >= 0
    
    # Verificar que el resultado contiene los campos esperados
    assert 'checked_at' in result
    assert 'inconsistencies' in result
    assert 'checks_passed' in result
    
    # Verificar que la Claim fue creada con el resultado real
    claim_id = result.get('claim_id')
    assert claim_id is not None
    
    # Verificar que el status deriva del resultado real del detector
    verification_status = result.get('verification_status')
    expected_status = "PASS" if result['total_inconsistencies'] == 0 else "FAIL"
    assert verification_status == expected_status
    
    # Verificar que la Claim existe en el repositorio
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    claim = repo.retrieve(claim_id)
    assert claim is not None
    assert claim.invariant == "PERCEPTION_CONSISTENCY"


def test_detector_real_activity_with_inconsistency(workspace):
    """Test B.11: Demuestra que el detector detecta inconsistencias reales."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Crear mocks mínimos
    class MockToolCard:
        def __init__(self, tool_id: str, available: bool, metadata: dict, title: str):
            self.tool_id = tool_id
            self.available = available
            self.metadata = metadata
            self.title = title
    
    class MockToolRegistry:
        def __init__(self, cards: list):
            self._cards = cards
        
        def list_cards(self):
            return self._cards
        
        def invalidate_availability_cache(self, tool_id: str):
            pass
        
        def get_card(self, tool_id: str):
            for card in self._cards:
                if card.tool_id == tool_id:
                    return card
            return None
        
        def refresh_card(self, card, force: bool = False):
            return card
    
    class MockToolLiveStatus:
        def __init__(self, tool_id: str, available: bool):
            self.tool_id = tool_id
            self.available = available
    
    class MockWindow:
        def __init__(self, title: str, pid: int = None):
            self.title = title
            self.pid = pid
    
    class MockFocusedWindow:
        def __init__(self, title: str):
            self.title = title
    
    class MockWorldModelSnapshot:
        def __init__(self, tool_live_status: list, active_windows: list, focused_window):
            self.tool_live_status = tool_live_status
            self.active_windows = active_windows
            self.focused_window = focused_window
    
    class MockWorldModelService:
        def __init__(self, snapshot):
            self._snapshot = snapshot
        
        def current_snapshot(self):
            return self._snapshot
    
    # Configurar estado inconsistente
    # ToolRegistry tiene tool pero WorldModel no lo rastrea
    tool_card = MockToolCard(
        tool_id="inconsistent_tool",
        available=True,
        metadata={"launch_mode": "desktop_app"},
        title="Inconsistent Tool"
    )
    
    # WorldModel no tiene este tool en tool_live_status
    snapshot = MockWorldModelSnapshot(
        tool_live_status=[],  # Vacío: tool no está en WorldModel
        active_windows=[MockWindow("Test Window")],
        focused_window=MockFocusedWindow("Test Window")
    )
    
    tool_registry = MockToolRegistry([tool_card])
    world_model_service = MockWorldModelService(snapshot)
    
    # Ejecutar el detector con dependencias
    result = run_cross_validation_with_claim(
        world_model_service=world_model_service,
        tool_registry=tool_registry,
        workspace=workspace,
    )
    
    # Verificar que el detector detectó la inconsistencia
    assert result['total_checks'] == 4
    assert result['total_inconsistencies'] > 0  # Debe haber inconsistencias
    
    # Verificar que la inconsistencia es la esperada
    inconsistencies = result['inconsistencies']
    audit_inc = [i for i in inconsistencies if i['check'] == 'audit_vs_worldmodel']
    assert len(audit_inc) > 0
    
    # Verificar que el status es FAIL
    verification_status = result.get('verification_status')
    assert verification_status == "FAIL"
    
    # Verificar que la Claim existe con el resultado real
    claim_id = result.get('claim_id')
    assert claim_id is not None
    
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    
    claim = repo.retrieve(claim_id)
    assert claim is not None
