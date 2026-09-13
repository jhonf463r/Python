"""Tests para experimento de influencia causal Claim → AutonomyGovernancePolicy.

Experimento C (v2): ¿Puede una señal generada por un detector real atravesar
Claim + VerificationEvent + SQLite y cambiar causalmente la decisión de governance?

Estrategia:
- Baseline: detector real → PASS → SQLite → governance → ALLOW
- Intervención: detector real → FAIL → SQLite → governance → BLOCK
- Control: detector real → FAIL en PR sin UI → Claim ignorada
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import uuid

import pytest

from iabv_v15.domain.models import IntegrityClaim, VerificationEvent
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
from iabv_v15.services.self_code_analysis import verify_slot_decorators


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
def repo():
    """Fixture que usa base de datos separada para evitar colisiones con otros tests."""
    temp_dir = Path(tempfile.gettempdir())
    db_path = temp_dir / f"test_governance_{uuid.uuid4().hex[:8]}.sqlite"
    db = AppDatabase(str(db_path))
    repo = IntegrityClaimRepository(db)
    yield repo
    # Cleanup
    try:
        db.close()
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass


@pytest.fixture
def pass_workspace():
    """Fixture que crea un workspace temporal donde el detector retorna PASS.
    
    Estructura:
    - src/iabv_v15/ui/viewmodels/test_viewmodel.py con método decorado con @Slot
    - src/iabv_v15/ui/qml/Test.qml que llama a ese método
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="test_pass_workspace_"))
    
    # Crear estructura de directorios
    vm_dir = temp_dir / "src" / "iabv_v15" / "ui" / "viewmodels"
    qml_dir = temp_dir / "src" / "iabv_v15" / "ui" / "qml"
    vm_dir.mkdir(parents=True)
    qml_dir.mkdir(parents=True)
    
    # Crear ViewModel con @Slot decorator (PASS case)
    vm_content = """
from PySide6.QtCore import Slot, QObject

class TestViewModel(QObject):
    @Slot()
    def test_method(self):
        pass
"""
    (vm_dir / "test_viewmodel.py").write_text(vm_content, encoding="utf-8")
    
    # Crear QML que llama al método (patrón debe coincidir con regex del detector)
    qml_content = """
import QtQuick 2.15
import TestViewModel 1.0

Item {
    TestViewModel {
        id: vm
    }
    Button {
        onClicked: TestViewModel.test_method()
    }
"""
    (qml_dir / "Test.qml").write_text(qml_content, encoding="utf-8")
    
    yield str(temp_dir)
    
    # Cleanup
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.fixture
def fail_workspace():
    """Fixture que crea un workspace temporal donde el detector retorna FAIL.
    
    Estructura:
    - src/iabv_v15/ui/viewmodels/test_viewmodel.py con método SIN @Slot
    - src/iabv_v15/ui/qml/Test.qml que llama a ese método
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="test_fail_workspace_"))
    
    # Crear estructura de directorios
    vm_dir = temp_dir / "src" / "iabv_v15" / "ui" / "viewmodels"
    qml_dir = temp_dir / "src" / "iabv_v15" / "ui" / "qml"
    vm_dir.mkdir(parents=True)
    qml_dir.mkdir(parents=True)
    
    # Crear ViewModel SIN @Slot decorator (FAIL case)
    vm_content = """
from PySide6.QtCore import QObject

class TestViewModel(QObject):
    def test_method(self):
        pass
"""
    (vm_dir / "test_viewmodel.py").write_text(vm_content, encoding="utf-8")
    
    # Crear QML que llama al método (patrón debe coincidir con regex del detector)
    qml_content = """
import QtQuick 2.15
import TestViewModel 1.0

Item {
    TestViewModel {
        id: vm
    }
    Button {
        onClicked: TestViewModel.test_method()
    }
"""
    (qml_dir / "Test.qml").write_text(qml_content, encoding="utf-8")
    
    yield str(temp_dir)
    
    # Cleanup
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass


def test_detector_real_pass_to_claim_to_governance_allow(pass_workspace, governance_policy, repo):
    """Test C.1: Detector real → PASS → Claim → SQLite → governance → ALLOW.
    
    CONTROL A:
    - Ejecutar detector real en workspace PASS
    - Persistir Claim + VerificationEvent desde resultado real
    - Recuperar status desde SQLite
    - PR con UI path
    - Expected: allow_github_merge → (True, None)
    """
    import hashlib
    
    # Ejecutar detector real
    detector_result = verify_slot_decorators(pass_workspace)
    assert detector_result['ok'] is True, "Detector should return PASS for this workspace"
    
    # Crear Claim identity estable
    claim_identity_input = f"slot_decorators:{pass_workspace}:detector_real_pass"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({pass_workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent desde resultado real del detector
    status = "PASS" if detector_result['ok'] else "FAIL"
    verification_evidence = f"source_path:{pass_workspace}/src/iabv_v15/ui/viewmodels"
    
    event = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        verification_evidence=verification_evidence,
    )
    repo.append_verification(event)
    
    # Recuperar status desde SQLite
    current_status = repo.get_current_status(claim_id)
    assert current_status == "PASS"
    
    # Construir pr_metadata con UI path
    pr_metadata = {
        'pull_number': 123,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/test_viewmodel.py',
            'src/iabv_v15/ui/qml/Test.qml',
        ],
    }
    
    # Añadir status recuperado desde SQLite
    pr_metadata['qml_python_binding_status'] = current_status
    
    # Ejecutar allow_github_merge
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Verificar resultado esperado
    assert allowed is True
    assert reason is None


def test_detector_real_fail_to_claim_to_governance_block(fail_workspace, governance_policy, repo):
    """Test C.2: Detector real → FAIL → Claim → SQLite → governance → BLOCK.
    
    CONTROL A:
    - Ejecutar detector real en workspace FAIL
    - Persistir Claim + VerificationEvent desde resultado real
    - Recuperar status desde SQLite
    - Mismo pr_metadata que baseline salvo status derivado
    - Expected: allow_github_merge → (False, reason identificando QML_PYTHON_BINDING)
    """
    import hashlib
    
    # Ejecutar detector real
    detector_result = verify_slot_decorators(fail_workspace)
    assert detector_result['ok'] is False, "Detector should return FAIL for this workspace"
    
    # Crear Claim identity estable
    claim_identity_input = f"slot_decorators:{fail_workspace}:detector_real_fail"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({fail_workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent desde resultado real del detector
    status = "PASS" if detector_result['ok'] else "FAIL"
    verification_evidence = f"source_path:{fail_workspace}/src/iabv_v15/ui/viewmodels"
    
    event = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        verification_evidence=verification_evidence,
    )
    repo.append_verification(event)
    
    # Recuperar status desde SQLite
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
            'src/iabv_v15/ui/viewmodels/test_viewmodel.py',
            'src/iabv_v15/ui/qml/Test.qml',
        ],
    }
    
    # Añadir status recuperado desde SQLite
    pr_metadata['qml_python_binding_status'] = current_status
    
    # Ejecutar allow_github_merge
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Verificar resultado esperado
    assert allowed is False
    assert reason is not None
    assert 'QML_PYTHON_BINDING' in reason


def test_detector_real_fail_ignored_for_non_ui_pr(fail_workspace, governance_policy, repo):
    """Test C.3: Control B - Detector real → FAIL pero PR sin UI path → Claim ignorada.
    
    CONTROL B:
    - Ejecutar detector real en workspace FAIL
    - PR NO toca UI path
    - Expected: Claim ignorada, comportamiento de reglas existentes
    """
    import hashlib
    
    # Ejecutar detector real
    detector_result = verify_slot_decorators(fail_workspace)
    assert detector_result['ok'] is False
    
    # Crear Claim identity estable
    claim_identity_input = f"slot_decorators:{fail_workspace}:detector_real_no_ui"
    claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]
    
    # Crear Claim
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({fail_workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim)
    
    # Crear VerificationEvent desde resultado real
    status = "PASS" if detector_result['ok'] else "FAIL"
    event = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32],
        claim_id=claim_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        verification_evidence=f"source_path:{fail_workspace}/src/iabv_v15/ui/viewmodels",
    )
    repo.append_verification(event)
    
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
    assert allowed is True
    assert reason is None


def test_path_normalization_windows_backslash(governance_policy):
    r"""Test C.4: Control E - Windows backslash UI path -> normalizado correctamente.

    CONTROL E:
    - Path con backslash Windows: src\iabv_v15\ui\viewmodels\foo.py
    - Debe comportarse igual que: src/iabv_v15/ui/viewmodels/foo.py
    - Expected: touches_ui = True
    """
    import hashlib
    
    # PR con Windows backslash path
    pr_metadata = {
        'pull_number': 125,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src\\iabv_v15\\ui\\viewmodels\\test_viewmodel.py',
            'src/iabv_v15/ui/qml/Test.qml',
        ],
        'qml_python_binding_status': 'FAIL',
    }
    
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Debe bloquear porque el path con backslash debe normalizarse
    assert allowed is False
    assert reason is not None
    assert 'QML_PYTHON_BINDING' in reason


def test_path_normalization_non_ui_windows_backslash(governance_policy):
    r"""Test C.5: Control F - Non-UI Windows backslash path -> no activa regla.

    CONTROL F:
    - Path con backslash Windows pero no UI: src\iabv_v15\services\foo.py
    - Expected: touches_ui = False, Claim ignorada
    """
    # PR con Windows backslash path no-UI
    pr_metadata = {
        'pull_number': 126,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 20,
        'deletions': 10,
        'changed_files': 2,
        'changed_paths': [
            'src\\iabv_v15\\services\\some_service.py',
        ],
        'qml_python_binding_status': 'FAIL',
    }
    
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Debe ALLOW porque no toca UI path
    assert allowed is True
    assert reason is None


def test_path_normalization_leading_slash(governance_policy):
    r"""Test C.6: Path con leading slash -> normalizado correctamente.

    Verificar que /src/iabv_v15/ui/viewmodels/... se normaliza igual que src/iabv_v15/ui/viewmodels/...
    """
    # PR con leading slash
    pr_metadata = {
        'pull_number': 127,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            '/src/iabv_v15/ui/viewmodels/test_viewmodel.py',
        ],
        'qml_python_binding_status': 'FAIL',
    }
    
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_metadata)
    
    # Debe bloquear
    assert allowed is False
    assert 'QML_PYTHON_BINDING' in reason


def test_causal_chain_detector_to_governance(pass_workspace, fail_workspace, governance_policy, repo):
    """Test C.7: Cadena causal completa detector → Claim → SQLite → governance.
    
    CONTROL C:
    - Detector real PASS → governance ALLOW
    - Detector real FAIL → governance BLOCK
    - Mismo pr_metadata salvo status derivado
    - Confirmar causalidad
    """
    import hashlib
    
    # PR metadata base (idéntico para ambos casos)
    pr_metadata_base = {
        'pull_number': 128,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 50,
        'deletions': 30,
        'changed_files': 3,
        'changed_paths': [
            'src/iabv_v15/ui/viewmodels/test_viewmodel.py',
            'src/iabv_v15/ui/qml/Test.qml',
        ],
    }
    
    # Caso PASS
    detector_result_pass = verify_slot_decorators(pass_workspace)
    assert detector_result_pass['ok'] is True
    
    claim_id_pass = hashlib.sha256(f"slot_decorators:{pass_workspace}:causal_pass".encode()).hexdigest()[:32]
    claim_pass = IntegrityClaim(
        claim_id=claim_id_pass,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({pass_workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim_pass)
    
    event_pass = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id_pass}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32],
        claim_id=claim_id_pass,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="PASS",
        verification_evidence=f"source_path:{pass_workspace}/src/iabv_v15/ui/viewmodels",
    )
    repo.append_verification(event_pass)
    
    metadata_pass = pr_metadata_base.copy()
    metadata_pass['qml_python_binding_status'] = repo.get_current_status(claim_id_pass)
    
    allowed_pass, reason_pass = governance_policy.allow_github_merge(pr_metadata=metadata_pass)
    
    # Caso FAIL
    detector_result_fail = verify_slot_decorators(fail_workspace)
    assert detector_result_fail['ok'] is False
    
    claim_id_fail = hashlib.sha256(f"slot_decorators:{fail_workspace}:causal_fail".encode()).hexdigest()[:32]
    claim_fail = IntegrityClaim(
        claim_id=claim_id_fail,
        subject=f"QML-callable methods in ViewModels have @Slot decorators ({fail_workspace})",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.create(claim_fail)
    
    event_fail = VerificationEvent(
        event_id=hashlib.sha256(f"{claim_id_fail}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32],
        claim_id=claim_id_fail,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status="FAIL",
        verification_evidence=f"source_path:{fail_workspace}/src/iabv_v15/ui/viewmodels",
    )
    repo.append_verification(event_fail)
    
    metadata_fail = pr_metadata_base.copy()
    metadata_fail['qml_python_binding_status'] = repo.get_current_status(claim_id_fail)
    
    allowed_fail, reason_fail = governance_policy.allow_github_merge(pr_metadata=metadata_fail)
    
    # Verificar causalidad
    assert allowed_pass is True
    assert allowed_fail is False
    assert reason_pass is None
    assert reason_fail is not None
    assert 'QML_PYTHON_BINDING' in reason_fail
    
    # Verificar que metadata es idéntico salvo status derivado
    keys_pass = set(metadata_pass.keys())
    keys_fail = set(metadata_fail.keys())
    assert keys_pass == keys_fail
    
    for key in keys_pass:
        if key == 'qml_python_binding_status':
            assert metadata_pass[key] != metadata_fail[key]
        else:
            assert metadata_pass[key] == metadata_fail[key]


def test_preservation_existing_rules(governance_policy):
    """Test C.8: Preservación de reglas existentes de allow_github_merge.
    
    Verificar que las reglas existentes siguen funcionando:
    - draft blocking
    - CI failure blocking
    - changes_requested blocking
    - diff size blocking
    - file count blocking
    - sensitive path blocking
    """
    # Test 1: draft blocking
    pr_draft = {
        'pull_number': 129,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': True,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_draft)
    assert allowed is False
    assert 'draft' in reason.lower()
    
    # Test 2: CI failure blocking
    pr_ci_fail = {
        'pull_number': 130,
        'ci_status': 'failure',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_ci_fail)
    assert allowed is False
    assert 'ci' in reason.lower()
    
    # Test 3: changes_requested blocking
    pr_cr = {
        'pull_number': 131,
        'ci_status': 'success',
        'reviews': [{'state': 'CHANGES_REQUESTED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_cr)
    assert allowed is False
    assert 'changes_requested' in reason.lower()
    
    # Test 4: diff size blocking
    pr_large_diff = {
        'pull_number': 132,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 150,
        'deletions': 100,
        'changed_files': 2,
        'changed_paths': ['src/iabv_v15/ui/viewmodels/test.py'],
    }
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_large_diff)
    assert allowed is False
    assert 'diff' in reason.lower()
    
    # Test 5: sensitive path blocking
    pr_sensitive = {
        'pull_number': 133,
        'ci_status': 'success',
        'reviews': [{'state': 'APPROVED'}],
        'draft': False,
        'additions': 10,
        'deletions': 5,
        'changed_files': 1,
        'changed_paths': ['src/iabv_v15/bootstrap.py'],
    }
    allowed, reason = governance_policy.allow_github_merge(pr_metadata=pr_sensitive)
    assert allowed is False
    assert 'sensible' in reason.lower() or 'bootstrap' in reason.lower()
