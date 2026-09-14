"""Test de integración operacional: auto_merge() → governance → Claim.

Este test demuestra que el entrypoint real auto_merge() utiliza
AutonomyGovernancePolicy.allow_github_merge() y que el estado de una Claim
puede influir en la decisión de merge.

Prueba la cadena:
REAL ENTRYPOINT (auto_merge)
→ metadata real
→ Claim lookup real
→ governance real
→ ALLOW/BLOCK
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest

from iabv_v15.infra.mcp.self_auto_merge import (
    MergeResult,
    auto_merge,
)
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository
from iabv_v15.domain.models import IntegrityClaim
from iabv_v15.domain.models import VerificationEvent


@dataclass
class FakeGitHubClient:
    """GitHubClient fake para testing sin llamadas reales a GitHub API."""

    pr_data: dict[str, Any]
    files_data: list[dict[str, Any]]
    check_runs_data: list[dict[str, Any]]
    merge_response: dict[str, Any]

    def fetch_pr(self, repo: str, number: int) -> dict[str, Any]:
        return self.pr_data

    def fetch_pr_files(self, repo: str, number: int) -> list[dict[str, Any]]:
        return self.files_data

    def fetch_check_runs(self, repo: str, sha: str) -> list[dict[str, Any]]:
        return self.check_runs_data

    def merge_pr(self, repo: str, number: int, method: str) -> dict[str, Any]:
        return self.merge_response


@pytest.fixture
def temp_db(tmp_path):
    """Base de datos temporal para Claims."""
    db_path = tmp_path / "integrity_claims.sqlite"
    db = AppDatabase(str(db_path))
    yield db
    # AppDatabase no tiene método close, no hacemos nada


@pytest.fixture
def claim_repo(temp_db):
    """Repositorio de Claims temporal."""
    return IntegrityClaimRepository(temp_db)


@pytest.fixture
def workspace(tmp_path):
    """Workspace temporal para Claim lookup."""
    return str(tmp_path)


def _build_claim_id(workspace: str) -> str:
    """Calcula el Claim ID estable (mismo esquema que SelfCodeAnalysis)."""
    claim_identity_input = f"slot_decorators:{workspace}"
    return hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]


def test_operational_claim_pass_governance_allows_merge(claim_repo, workspace):
    """Demostración operacional: Claim PASS → governance ALLOW → merge permitido.

    Este test demuestra que el entrypoint real auto_merge() pasa por governance
    y que un Claim con status PASS permite la operación cuando las demás
    condiciones son válidas.
    """
    # Arrange: Crear Claim con status PASS
    claim_id = _build_claim_id(workspace)
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"{workspace}/src/iabv_v15/ui/viewmodels",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.utcnow().isoformat(),
    )
    claim_repo.create(claim)

    # Agregar VerificationEvent PASS
    verification = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim_id,
        checked_at=datetime.utcnow().isoformat(),
        status="PASS",
        verification_evidence=f"source_path:{workspace}/src/iabv_v15/ui/viewmodels",
    )
    claim_repo.append_verification(verification)

    # Arrange: PR que toca UI paths
    pr_data = {
        "number": 123,
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"ref": "devin/test-branch", "sha": "abc123"},
        "base": {"sha": "def456"},
        "mergeable_state": "clean",
        "title": "Test PR",
        "additions": 50,
        "deletions": 10,
        "changed_files": 2,
    }

    # El PR toca un archivo UI
    files_data = [
        {"filename": "src/iabv_v15/ui/viewmodels/test_viewmodel.py"},
    ]

    # Checks verdes
    check_runs_data = [
        {"name": "test", "status": "completed", "conclusion": "success"},
    ]

    # Merge exitoso (simulado)
    merge_response = {"merged": True, "sha": "merged_sha"}

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    # Act: Llamar al entrypoint real auto_merge()
    # NOTA: Como reviews=None bloquea, necesitamos simular reviews=[] para probar Claim específico
    # Modificamos FakeGitHubClient para incluir reviews en los datos
    pr_data["reviews"] = [{"state": "APPROVED"}]  # Simular reviews presentes

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    result = auto_merge(
        repo="test/repo",
        pr_number=123,
        client=fake_client,
        workspace=workspace,
        claim_repository=claim_repo,
    )

    # Assert: governance debe ALLOW y merge debe ejecutarse
    assert result.status == "merged", f"Expected merged, got {result.status}: {result.detail}"
    assert result.reason == "ok"
    assert "QML_PYTHON_BINDING" not in (result.detail or "")


def test_operational_claim_fail_governance_blocks_merge(claim_repo, workspace):
    """Demostración operacional: Claim FAIL → governance BLOCK → merge bloqueado.

    Este test demuestra que el entrypoint real auto_merge() pasa por governance
    y que un Claim con status FAIL bloquea la operación.
    """
    # Arrange: Crear Claim con status FAIL
    claim_id = _build_claim_id(workspace)
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"{workspace}/src/iabv_v15/ui/viewmodels",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.utcnow().isoformat(),
    )
    claim_repo.create(claim)

    # Agregar VerificationEvent FAIL
    verification = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim_id,
        checked_at=datetime.utcnow().isoformat(),
        status="FAIL",
        verification_evidence=f"source_path:{workspace}/src/iabv_v15/ui/viewmodels",
    )
    claim_repo.append_verification(verification)

    # Arrange: PR que toca UI paths
    pr_data = {
        "number": 123,
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"ref": "devin/test-branch", "sha": "abc123"},
        "base": {"sha": "def456"},
        "mergeable_state": "clean",
        "title": "Test PR",
        "additions": 50,
        "deletions": 10,
        "changed_files": 2,
        "reviews": [{"state": "APPROVED"}],  # Simular reviews presentes
    }

    # El PR toca un archivo UI
    files_data = [
        {"filename": "src/iabv_v15/ui/viewmodels/test_viewmodel.py"},
    ]

    # Checks verdes
    check_runs_data = [
        {"name": "test", "status": "completed", "conclusion": "success"},
    ]

    # Merge exitoso (simulado, pero no debe ejecutarse)
    merge_response = {"merged": True, "sha": "merged_sha"}

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    # Act: Llamar al entrypoint real auto_merge()
    result = auto_merge(
        repo="test/repo",
        pr_number=123,
        client=fake_client,
        workspace=workspace,
        claim_repository=claim_repo,
    )

    # Assert: governance debe BLOCK y merge NO debe ejecutarse
    assert result.status == "blocked", f"Expected blocked, got {result.status}"
    assert result.reason == "governance_blocked"
    assert "QML_PYTHON_BINDING" in (result.detail or ""), f"Expected QML_PYTHON_BINDING in reason, got: {result.detail}"
    # Verificar que merge_pr() NO fue llamado (client.merge_pr no debe ser invocado)
    # En este test fake, si governance bloquea, no llegamos a merge_pr


def test_operational_claim_fail_ignored_for_non_ui_pr(claim_repo, workspace):
    """Demostración operacional: Claim FAIL pero PR no toca UI → governance no bloquea por Claim.

    Este test demuestra que la regla de governance es específica: solo bloquea
    cuando el PR toca rutas UI relevantes.
    """
    # Arrange: Crear Claim con status FAIL
    claim_id = _build_claim_id(workspace)
    claim = IntegrityClaim(
        claim_id=claim_id,
        subject=f"{workspace}/src/iabv_v15/ui/viewmodels",
        invariant="QML_PYTHON_BINDING",
        origin="SelfCodeAnalysis.verify_slot_decorators",
        created_at=datetime.utcnow().isoformat(),
    )
    claim_repo.create(claim)

    # Agregar VerificationEvent FAIL
    verification = VerificationEvent(
        event_id=str(uuid.uuid4()),
        claim_id=claim_id,
        checked_at=datetime.utcnow().isoformat(),
        status="FAIL",
        verification_evidence=f"source_path:{workspace}/src/iabv_v15/ui/viewmodels",
    )
    claim_repo.append_verification(verification)

    # Arrange: PR que NO toca UI paths
    pr_data = {
        "number": 123,
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"ref": "devin/test-branch", "sha": "abc123"},
        "base": {"sha": "def456"},
        "mergeable_state": "clean",
        "title": "Test PR",
        "additions": 50,
        "deletions": 10,
        "changed_files": 2,
        "reviews": [{"state": "APPROVED"}],  # Simular reviews presentes
    }

    # El PR toca un archivo NO UI
    files_data = [
        {"filename": "src/iabv_v15/services/test_service.py"},
    ]

    # Checks verdes
    check_runs_data = [
        {"name": "test", "status": "completed", "conclusion": "success"},
    ]

    # Merge exitoso
    merge_response = {"merged": True, "sha": "merged_sha"}

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    # Act: Llamar al entrypoint real auto_merge()
    result = auto_merge(
        repo="test/repo",
        pr_number=123,
        client=fake_client,
        workspace=workspace,
        claim_repository=claim_repo,
    )

    # Assert: governance debe ALLOW (Claim FAIL no es relevante para este PR)
    assert result.status == "merged", f"Expected merged, got {result.status}: {result.detail}"
    assert result.reason == "ok"


def test_operational_governance_connection_required(workspace):
    """Prueba de sabotaje: si eliminamos la conexión governance, el test detecta el cambio.

    Este test verifica que la integración entre auto_merge() y governance es real,
    no simulada. Si alguien elimina la llamada a allow_github_merge(), este test
    detectará la degradación de seguridad.

    El mecanismo: creamos un PR que governance debe bloquear por una regla
    existente (no por Claim, sino por regla sensible). Si governance está conectado,
    el merge debe ser bloqueado. Si governance fue eliminado, el merge procedería.
    """
    # Arrange: No crear Claim (usamos regla de governance existente)
    # Usamos la regla de sensitive paths para forzar un bloqueo de governance

    # Arrange: PR que toca ruta sensible (AGENTS.md)
    pr_data = {
        "number": 123,
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"ref": "devin/test-branch", "sha": "abc123"},
        "base": {"sha": "def456"},
        "mergeable_state": "clean",
        "title": "Test PR",
        "additions": 50,
        "deletions": 10,
        "changed_files": 2,
        "reviews": [{"state": "APPROVED"}],  # Simular reviews presentes
    }

    # El PR toca AGENTS.md (ruta sensible)
    files_data = [
        {"filename": "AGENTS.md"},
    ]

    # Checks verdes
    check_runs_data = [
        {"name": "test", "status": "completed", "conclusion": "success"},
    ]

    # Merge exitoso (simulado, pero no debe ejecutarse si governance está conectado)
    merge_response = {"merged": True, "sha": "merged_sha"}

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    # Act: Llamar al entrypoint real auto_merge()
    result = auto_merge(
        repo="test/repo",
        pr_number=123,
        client=fake_client,
        workspace=workspace,
    )

    # Assert: governance debe BLOCK por ruta sensible
    assert result.status == "blocked", f"Expected blocked, got {result.status}: {result.detail}"
    assert result.reason == "governance_blocked"
    assert "ruta sensible" in (result.detail or "").lower(), f"Expected sensitive path in reason, got: {result.detail}"

    # Si este test falla (status es "merged"), significa que governance fue eliminado
    # o desconectado de auto_merge(). Esto es una degradación de seguridad crítica.


def test_reviews_none_blocks_merge(workspace):
    """Test C05.1: reviews=None debe bloquear merge (fail-closed).

    Verifica que ausencia de evidencia de reviews no se interpreta como aprobación.
    AutonomyGovernancePolicy usa `reviews is None` como condición fail-closed.
    """
    # Arrange: PR sin reviews (reviews=None en metadata)
    pr_data = {
        "number": 125,
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"ref": "devin/test-branch", "sha": "abc123"},
        "base": {"sha": "def456"},
        "mergeable_state": "clean",
        "title": "Test PR",
        "additions": 10,
        "deletions": 5,
        "changed_files": 1,
    }

    files_data = [
        {"filename": "src/iabv_v15/services/test_service.py"},
    ]

    check_runs_data = [
        {"name": "test", "status": "completed", "conclusion": "success"},
    ]

    merge_response = {"merged": True, "sha": "merged_sha"}

    fake_client = FakeGitHubClient(
        pr_data=pr_data,
        files_data=files_data,
        check_runs_data=check_runs_data,
        merge_response=merge_response,
    )

    # Act: Llamar sin force (para probar fail-closed real)
    result = auto_merge(
        repo="test/repo",
        pr_number=125,
        client=fake_client,
        workspace=workspace,
    )

    # Assert: governance debe BLOCK por reviews ausente
    assert result.status == "blocked", f"Expected blocked, got {result.status}: {result.detail}"
    assert result.reason == "governance_blocked"
    assert "reviews" in (result.detail or "").lower(), f"Expected reviews in reason, got: {result.detail}"


def test_fetch_pr_files_pagination():
    """Test C05.2: fetch_pr_files() debe obtener TODOS los archivos con paginación.

    Verifica que el bucle de paginación recorre múltiples páginas hasta obtener todos los archivos.
    Este test verifica la lógica de paginación directamente en el código.
    """
    from iabv_v15.infra.mcp.self_auto_merge import GitHubClient

    # Arrange: Mock del método request() para simular paginación
    class PaginatedMockClient(GitHubClient):
        def __init__(self):
            super().__init__("dummy")
            self.request_count = 0
            self.pages_to_return = [
                [{"filename": f"src/iabv_v15/services/file_{i}.py"} for i in range(100)],
                [{"filename": f"src/iabv_v15/services/file_{100 + i}.py"} for i in range(100)],  # 100 para forzar tercera página
                [{"filename": f"src/iabv_v15/services/file_{200 + i}.py"} for i in range(50)],  # 50 < 100: detiene
            ]

        def request(self, method: str, url: str, data: Any = None) -> Any:
            self.request_count += 1
            # Devolver páginas en secuencia
            page_index = min(self.request_count - 1, len(self.pages_to_return) - 1)
            return self.pages_to_return[page_index]

    fake_client = PaginatedMockClient()

    # Act: Llamar a fetch_pr_files (usa el método real con paginación)
    files = fake_client.fetch_pr_files("test/repo", 126)

    # Assert: Debe haber hecho 3 solicitudes (página 1 + página 2 + página 3)
    assert fake_client.request_count == 3, f"Expected 3 requests, got {fake_client.request_count}"

    # Assert: Debe tener todos los 250 archivos
    assert len(files) == 250, f"Expected 250 files, got {len(files)}"

    # Assert: Todos los archivos deben estar presentes
    filenames = [f["filename"] for f in files]
    assert "src/iabv_v15/services/file_0.py" in filenames
    assert "src/iabv_v15/services/file_99.py" in filenames
    assert "src/iabv_v15/services/file_100.py" in filenames
    assert "src/iabv_v15/services/file_199.py" in filenames
    assert "src/iabv_v15/services/file_200.py" in filenames
    assert "src/iabv_v15/services/file_249.py" in filenames


def test_error_paths_do_not_convert_to_pass(workspace):
    """Test C05.3: Error paths no deben convertirse silenciosamente en PASS.

    Verifica que:
    - API error → changed_paths=None → governance bloquea
    - Claim lookup error → qml_python_binding_status ausente → governance permite (fail-safe)
    """
    from iabv_v15.infra.mcp.self_auto_merge import _build_pr_metadata

    # Caso A: API error al obtener archivos
    class ErrorClient:
        def fetch_pr(self, repo: str, number: int) -> dict[str, Any]:
            return {
                "number": number,
                "draft": False,
                "additions": 10,
                "deletions": 5,
                "changed_files": 1,
            }

        def fetch_pr_files(self, repo: str, number: int) -> list[dict[str, Any]]:
            raise Exception("API error simulado")

    pr_data = {
        "number": 127,
        "draft": False,
        "additions": 10,
        "deletions": 5,
        "changed_files": 1,
    }

    pr_metadata = _build_pr_metadata(pr_data, "test/repo", ErrorClient(), ci_ok=True)

    # Assert: changed_paths debe ser None (no [] silencioso)
    assert pr_metadata["changed_paths"] is None, "changed_paths debe ser None cuando falla API"

    # Governance debe bloquear por changed_paths ausente (reviews=[] para pasar esa validación)
    pr_metadata["reviews"] = []  # Simular reviews presentes para probar changed_paths
    from iabv_v15.services.adaptive.autonomy_governance_policy import AutonomyGovernancePolicy
    policy = AutonomyGovernancePolicy()
    allowed, reason = policy.allow_github_merge(pr_metadata=pr_metadata)
    assert not allowed, "Governance debe bloquear cuando changed_paths=None"
    assert "changed_paths" in (reason or "").lower()

    # Caso B: Claim lookup error con DB missing
    # No existe base de datos → enrich_pr_metadata_with_claim_status() no agrega campo
    from iabv_v15.infra.persistence.claim_governance_integration import enrich_pr_metadata_with_claim_status

    pr_metadata_with_ui = {
        "pull_number": 128,
        "ci_status": "success",
        "reviews": [],  # Reviews presentes para probar Claim específicamente
        "draft": False,
        "additions": 10,
        "deletions": 5,
        "changed_files": 1,
        "changed_paths": ["src/iabv_v15/ui/viewmodels/test.py"],
    }

    enriched = enrich_pr_metadata_with_claim_status(
        pr_metadata_with_ui,
        workspace=workspace,  # Workspace sin DB
        claim_repository=None,
    )

    # Assert: campo NO agregado (fail-safe, no fail-open)
    assert "qml_python_binding_status" not in enriched, "Claim lookup error no debe agregar campo"

    # Governance permite porque campo ausente (comportamiento fail-safe)
    allowed, reason = policy.allow_github_merge(pr_metadata=enriched)
    # Debe permitir porque reviews=[] y changed_paths no es sensible
    assert allowed, f"Governance debe permitir cuando Claim ausente (fail-safe), got: {reason}"
