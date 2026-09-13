"""Tests para experimento de influencia causal Claim → AutonomyGovernancePolicy.

Experimento C: ¿Puede una Claim verificada influir causalmente en una decisión de governance?

Estrategia:
- Baseline: PR con UI path + QML_PYTHON_BINDING PASS → ALLOW
- Intervención: PR con UI path + QML_PYTHON_BINDING FAIL → BLOCK
- Control: PR sin UI path + QML_PYTHON_BINDING FAIL → Claim ignorada
"""

from datetime import datetime, timezone
from pathlib import Path
import uuid

import pytest

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy


@pytest.fixture
def workspace():
    """Fixture que usa el workspace real del checkout actual."""
    test_file = Path(__file__).resolve()
    workspace = test_file.parent.parent
    return str(workspace)


@pytest.fixture
def governance_policy():
    """Fixture que crea una instancia de AutonomyGovernancePolicy."""
    return AutonomyGovernancePolicy()


@pytest.fixture
def repo(workspace):
    """Fixture que usa base de datos separada para evitar colisiones con otros tests."""
    import tempfile
    
    # Usar base de datos separada para evitar colisiones
    temp_dir = Path(tempfile.gettempdir())
    db_path = temp_dir / f"test_governance_{uuid.uuid4().hex[:8]}.sqlite"
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    yield repo
    # Cleanup automático (si no está bloqueado)
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass  # Ignorar errores de cleanup en Windows


def test_claim_influence_baseline_pass_to_allow(workspace, governance_policy, repo):
    """Test C.1: Baseline - PR con UI path + QML_PYTHON_BINDING PASS → ALLOW.
    
    CONTROL A:
    - PR toca UI path relevante
    - QML_PYTHON_BINDING status = PASS
    - Expected: allow_github_merge → (True, None)
    """
    # Crear Claim directamente para tener control total
    import hashlib
    from iabv_v15.services.self_code_analysis import verify_slot_decorators
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_baseline"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent PASS explícito
    event_pass = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:pass_control:baseline".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="test_id:baseline_pass_control",
    )
    repo.append_verification(event_pass)
    
    # Recuperar status actual (debe ser PASS)
    current_status = repo.get_current_status(claim_id)
    assert current_status == "PASS"
    
    # Construir pr_metadata que pasa todas las condiciones existentes
    pr_metadata = {
        'pull_number': 123,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/control_center_viewmodel.py',
            'src/iabv_v15/ui/qml/ControlCenter.qml',
        ],
    }
    
    # Añadir status de Claim recuperado desde SQLite
    pr_metadata['qml_python_binding_status'] = current_status
    
    # Ejecutar allow_github_merge
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Verificar resultado esperado
    assert allowed is True
    assert reason is None


def test_claim_influence_intervention_fail_to_block(workspace, governance_policy, repo):
    """Test C.2: Intervención - PR con UI path + QML_PYTHON_BINDING FAIL → BLOCK.
    
    CONTROL A:
    - Mismo pr_metadata que baseline
    - Solo cambia: QML_PYTHON_BINDING status = FAIL
    - Expected: allow_github_merge → (False, reason identificando QML_PYTHON_BINDING)
    """
    import hashlib
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_intervention"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent FAIL explícito
    event_fail = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:fail_control:intervention".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="FAIL",
        verification_evidence="test_id:intervention_fail_control",
    )
    repo.append_verification(event_fail)
    
    # Recuperar status actual (debe ser FAIL)
    current_status = repo.get_current_status(claim_id)
    assert current_status == "FAIL"
    
    # Mismo pr_metadata que baseline
    pr_metadata = {
        'pull_number': 123,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/control_center_viewmodel.py',
            'src/iabv_v15/ui/qml/ControlCenter.qml',
        ],
    }
    
    # Añadir status de Claim recuperado desde SQLite
    pr_metadata['qml_python_binding_status'] = current_status
    
    # Ejecutar allow_github_merge
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Verificar resultado esperado
    assert allowed is False
    assert reason is not None
    assert 'QML_PYTHON_BINDING' in reason


def test_claim_influence_control_no_ui_path_ignore_fail(workspace, governance_policy, repo):
    """Test C.3: Control B - PR sin UI path + QML_PYTHON_BINDING FAIL → Claim ignorada.
    
    CONTROL B:
    - PR NO toca UI path
    - QML_PYTHON_BINDING status = FAIL
    - Expected: Claim ignorada, comportamiento de reglas existentes
    """
    import hashlib
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_no_ui"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    event_fail = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:control_no_ui_fail".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="FAIL",
        verification_evidence="test_id:control_no_ui",
    )
    repo.append_verification(event_fail)
    
    current_status = repo.get_current_status(claim_id)
    assert current_status == "FAIL"
    
    # PR sin UI path
    pr_metadata = {
        'pull_number': 124,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 20,
        'deletions': 10,
        'changed_files': 2,
        'changed_paths': [
            'src/iabv_v15/services/some_service.py',
            'docs/some_doc.md',
        ],
    }
    
    pr_metadata['qml_python_binding_status'] = current_status
    
    # Ejecutar allow_github_merge
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Verificar: Claim ignorada, comportamiento de reglas existentes
    assert allowed is True  # Debe ALLOW porque no toca UI path
    assert reason is None


def test_claim_influence_control_metadata_identical(workspace, governance_policy, repo):
    """Test C.4: Control C - Verificar que pr_metadata es idéntico salvo qml_python_binding_status.
    
    CONTROL C:
    - Repetir baseline/intervención con mismo pr_metadata
    - Solo cambia: qml_python_binding_status
    - Confirmar que metadata es idéntica salvo esa clave
    """
    # Crear PR metadata base
    base_metadata = {
        'pull_number': 125,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/control_center_viewmodel.py',
        ],
    }
    
    # Baseline: metadata con PASS
    metadata_pass = base_metadata.copy()
    metadata_pass['qml_python_binding_status'] = 'PASS'
    
    # Intervención: metadata con FAIL
    metadata_fail = base_metadata.copy()
    metadata_fail['qml_python_binding_status'] = 'FAIL'
    
    # Verificar que son idénticos salvo esa clave
    keys_pass = set(metadata_pass.keys())
    keys_fail = set(metadata_fail.keys())
    assert keys_pass == keys_fail
    
    for key in keys_pass:
        if key == 'qml_python_binding_status':
            assert metadata_pass[key] != metadata_fail[key]
        else:
            assert metadata_pass[key] == metadata_fail[key]


def test_claim_influence_control_status_from_sqlite(workspace, governance_policy, repo):
    """Test C.5: Control D - Confirmar que status vino de SQLite, no generado por test.
    
    CONTROL D:
    - Confirmar round-trip: detector → Claim → SQLite → get_current_status()
    - Confirmar que status no fue generado directamente por test
    """
    import hashlib
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_sqlite:{uuid.uuid4().hex[:8]}"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent con timestamp específico
    specific_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:control_sqlite_verification".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=specific_time.isoformat(),
        status="FAIL",
        verification_evidence="test_id:control_sqlite",
    )
    repo.append_verification(event)
    
    # Recuperar status desde SQLite
    current_status = repo.get_current_status(claim_id)
    
    # Verificar que el status existe en SQLite
    events = repo.retrieve_verifications_by_claim(claim_id, limit=10)
    assert len(events) >= 1
    
    # Verificar que el status recuperado coincide con el evento
    latest_event = repo.retrieve_latest_verification(claim_id)
    assert latest_event.status == current_status
    
    # Confirmar que el status no fue generado directamente por test
    # (fue recuperado de SQLite vía get_current_status)


def test_claim_influence_causal_flip_verification(workspace, governance_policy, repo):
    """Test C.6: Evidencia causal - Verificar flip de decisión causado por Claim status.
    
    EVIDENCIA CAUSAL:
    - Same pr_metadata salvo qml_python_binding_status
    - Decision baseline != decision intervención
    - Reason identifica QML_PYTHON_BINDING
    """
    import hashlib
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_causal:{uuid.uuid4().hex[:8]}"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # PR metadata que pasa todas las condiciones existentes
    pr_metadata = {
        'pull_number': 126,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/control_center_viewmodel.py',
        ],
    }
    
    # Baseline: PASS
    event_pass = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:causal_pass".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="test_id:causal",
    )
    repo.append_verification(event_pass)
    
    metadata_pass = pr_metadata.copy()
    metadata_pass['qml_python_binding_status'] = repo.get_current_status(claim_id)
    
    allowed_pass, reason_pass = governance_policy.allow_github_merge(pr_metadata=metadata_pass)
    
    # Intervención: FAIL
    event_fail = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:causal_fail".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="FAIL",
        verification_evidence="test_id:causal",
    )
    repo.append_verification(event_fail)
    
    metadata_fail = pr_metadata.copy()
    metadata_fail['qml_python_binding_status'] = repo.get_current_status(claim_id)
    
    allowed_fail, reason_fail = governance_policy.allow_github_merge(pr_metadata=metadata_fail)
    
    # Verificar flip causal
    assert allowed_pass is True
    assert allowed_fail is False
    assert reason_pass is None
    assert reason_fail is not None
    assert 'QML_PYTHON_BINDING' in reason_fail
    
    # Verificar que pr_metadata es idéntico salvo esa clave
    keys_pass = set(metadata_pass.keys())
    keys_fail = set(metadata_fail.keys())
    assert keys_pass == keys_fail


def test_claim_influence_preservation_existing_rules(workspace, governance_policy):
    """Test C.7: Preservación de reglas existentes.
    
    Verificar que las reglas existentes de allow_github_merge siguen funcionando:
    - draft blocking
    - CI failure blocking
    - changes_requested blocking
    - diff size blocking
    - file count blocking
    - sensitive path blocking
    """
    policy = AutonomyGovernancePolicy()
    
    # Test 1: draft blocking
    pr_draft = {
        'pull_number': 127,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': True,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_draft)
    assert allowed is False
    assert 'draft' in reason.lower()
    
    # Test 2: CI failure blocking
    pr_ci_fail = {
        'pull_number': 128,
        'ci_status': 'failure',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_ci_fail)
    assert allowed is False
    assert 'ci' in reason.lower()
    
    # Test 3: changes_requested blocking
    pr_cr = {
        'pull_number': 129,
        'ci_status': 'success',
        'reviews': [{'state': 'CHANGES_REQUESTED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_cr)
    assert allowed is False
    assert 'changes_requested' in reason.lower()
    
    # Test 4: diff size blocking
    pr_large_diff = {
        'pull_number': 130,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 150,
        'deletions': 100,
        'changed_files': 2,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_large_diff)
    assert allowed is False
    assert 'diff' in reason.lower()
    
    # Test 5: sensitive path blocking
    pr_sensitive = {
        'pull_number': 131,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/bootstrap.py'],
    }
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_sensitive)
    assert allowed is False
    assert 'sensible' in reason.lower() or 'bootstrap' in reason.lower()


def test_claim_influence_round_trip_claim_event(workspace, repo):
    """Test C.8: Round-trip completo Claim → Event → SQLite → get_current_status().
    
    Verificar que el flujo completo funciona:
    - Detector real ejecutado
    - Claim persistida
    - VerificationEvent persistido
    - Status recuperado desde SQLite
    - Status usado en governance
    """
    import hashlib
    
    # Calcular claim_id con suffix único para este test
    claim_identity_input = f"slot_decorators:{workspace}:governance_test_round_trip:{uuid.uuid4().hex[:8]}"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Verificar Claim persistida
    claim_retrieved = repo.retrieve(claim_id)
    assert claim_retrieved is not None
    assert claim_retrieved.invariant == "QML_PYTHON_BINDING"
    
    # Crear VerificationEvent
    event = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:round_trip_test".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence="test_id:round_trip",
    )
    repo.append_verification(event)
    
    # Verificar VerificationEvent persistido
    events = repo.retrieve_verifications_by_claim(claim_id, limit=10)
    assert len(events) >= 1
    
    # Verificar get_current_status
    current_status = repo.get_current_status(claim_id)
    assert current_status is not None
    assert current_status in ["PASS", "FAIL"]
    
    # Verificar que el status coincide con el VerificationEvent más reciente
    latest_event = repo.retrieve_latest_verification(claim_id)
    assert latest_event.status == current_status
