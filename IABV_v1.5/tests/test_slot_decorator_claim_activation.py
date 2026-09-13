"""Tests para primera activación real de Claim/VerificationEvent.

Demostración experimental: SelfCodeAnalysis.verify_slot_decorators() → Claim + VerificationEvent
sin modificar la lógica del detector original.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
from iabv_v15.services.self_code_analysis import verify_slot_decorators, verify_slot_decorators_with_claim


@pytest.fixture
def workspace():
    """Fixture que usa el workspace real de IABV."""
    return "C:\\Python\\IABV_v1.5"


@pytest.fixture
def cleanup_claims(workspace):
    """Fixture que limpia Claims creadas durante tests."""
    data_dir = Path(workspace) / 'data' / 'evolution'
    db_path = data_dir / 'integrity_claims.sqlite'
    
    # Guardar estado inicial si existe
    claims_before = []
    if db_path.exists():
        db = AppDatabase(str(db_path))
        repo = IntegrityClaimRepository(db)
        claims_before = repo.list_recent(limit=100)
    
    yield
    
    # Cleanup opcional: no limpiar para permitir inspección manual
    # En producción se podría limpiar aquí


def test_original_detector_unchanged_semantics(workspace):
    """Test A.1: El resultado original de verify_slot_decorators() permanece semánticamente equivalente."""
    result = verify_slot_decorators(workspace)
    
    # Verificar que los campos originales existen
    assert 'ok' in result
    assert 'methods_checked' in result
    assert 'qml_calls_found' in result
    assert 'issues' in result
    assert 'summary' in result
    
    # Verificar que la lógica de PASS/FAIL se preserva
    if result['ok']:
        assert len(result['issues']) == 0
    else:
        assert len(result['issues']) > 0


def test_stable_claim_identity(workspace):
    """Test A.2: Dos ejecuciones del mismo estado producen la misma identidad de Claim."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Primera ejecución
    result1 = verify_slot_decorators_with_claim(workspace)
    claim_id_1 = result1.get('claim_id')
    
    # Segunda ejecución
    result2 = verify_slot_decorators_with_claim(workspace)
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
    assert claim.invariant == "QML_PYTHON_BINDING"
    assert claim.origin == "SelfCodeAnalysis.verify_slot_decorators"


def test_multiple_verification_events(workspace):
    """Test A.3: Dos verificaciones de la misma Claim producen dos eventos."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Primera ejecución
    result1 = verify_slot_decorators_with_claim(workspace)
    claim_id = result1.get('claim_id')
    event_id_1 = result1.get('verification_event_id')
    
    # Segunda ejecución
    result2 = verify_slot_decorators_with_claim(workspace)
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
    """Test A.4: El historial puede recuperarse por claim_id."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Ejecutar el detector con Claim
    result = verify_slot_decorators_with_claim(workspace)
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
        assert event.verification_evidence.startswith("source_path:")
        assert event.checked_at is not None


def test_status_matches_detector_result(workspace):
    """Test A.5: El status almacenado coincide con el resultado real del detector."""
    # Ejecutar el detector original
    original_result = verify_slot_decorators(workspace)
    original_ok = original_result['ok']
    
    # Ejecutar el detector con Claim
    claim_result = verify_slot_decorators_with_claim(workspace)
    verification_status = claim_result.get('verification_status')
    
    # El status debe coincidir
    expected_status = "PASS" if original_ok else "FAIL"
    assert verification_status == expected_status
    
    # Verificar que el resultado original sigue siendo equivalente
    assert claim_result['ok'] == original_result['ok']
    assert claim_result['methods_checked'] == original_result['methods_checked']
    assert claim_result['qml_calls_found'] == original_result['qml_calls_found']


def test_claim_metadata_preserved(workspace):
    """Test A.6: La Claim metadata se preserva correctamente."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    result = verify_slot_decorators_with_claim(workspace)
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
    assert "QML-callable methods" in claim.subject
    assert "QML_PYTHON_BINDING" in claim.invariant
    assert "SelfCodeAnalysis" in claim.origin
    assert claim.created_at is not None


def test_current_status_derivation(workspace):
    """Test A.7: El status actual se deriva del VerificationEvent más reciente."""
    from iabv_v15.infra.persistence.database import AppDatabase
    from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
    
    # Ejecutar el detector con Claim
    result = verify_slot_decorators_with_claim(workspace)
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
    expected_status = "PASS" if result['ok'] else "FAIL"
    assert current_status == expected_status
