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
