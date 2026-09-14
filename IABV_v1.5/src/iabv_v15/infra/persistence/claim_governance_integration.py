"""Integración Claim → pr_metadata → AutonomyGovernancePolicy.

Este módulo proporciona la función de producción que conecta el estado
de IntegrityClaim con la metadata de PR usada por AutonomyGovernancePolicy.

El flujo causal es:
1. Production caller (auto-merge, CI, MCP tool) construye pr_metadata base
2. Llama a enrich_pr_metadata_with_claim_status()
3. Si el PR toca rutas UI, consulta IntegrityClaimRepository
4. Agrega qml_python_binding_status al pr_metadata
5. Caller pasa pr_metadata a AutonomyGovernancePolicy.allow_github_merge()
6. La decisión de governance incluye el estado de la Claim
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def enrich_pr_metadata_with_claim_status(
    pr_metadata: dict[str, Any],
    *,
    workspace: str | None = None,
    claim_repository: Any = None,
) -> dict[str, Any]:
    """Enriquece pr_metadata con el estado de IntegrityClaim si aplica.

    Args:
        pr_metadata: Metadata base del PR (pull_number, changed_paths, etc.)
        workspace: Ruta del workspace para localizar la base de datos de Claims
        claim_repository: IntegrityClaimRepository pre-configurado (opcional,
            usado por tests para inyectar repositorio temporal)

    Returns:
        pr_metadata con qml_python_binding_status agregado si el PR toca UI paths
        y existe una Claim en el workspace. Sin modificaciones si no aplica.

    Esta es la función de producción que el test debe usar en lugar de
    inyectar manualmente qml_python_binding_status.
    """
    # Verificar si el PR toca rutas UI relevantes
    changed_paths = pr_metadata.get('changed_paths', [])
    if not isinstance(changed_paths, list):
        return pr_metadata

    # Normalizar paths (compatible con Windows backslash)
    normalized_paths = [
        str(raw_path or '').strip().lstrip('/').replace('\\', '/')
        for raw_path in changed_paths
    ]

    touches_ui = any(
        'src/iabv_v15/ui/viewmodels/' in path or 'src/iabv_v15/ui/qml/' in path
        for path in normalized_paths
    )

    if not touches_ui:
        # No toca UI, no hay Claim relevante
        return pr_metadata

    # El PR toca UI: consultar IntegrityClaimRepository
    if claim_repository is not None:
        # Usar repositorio inyectado (caso de test)
        qml_binding_status = _get_qml_binding_status_from_repo(claim_repository, workspace)
    else:
        # Usar repositorio del workspace (caso de producción)
        qml_binding_status = _get_qml_binding_status_for_pr(workspace)

    if qml_binding_status is not None:
        # Copiar para no mutar el input
        enriched = dict(pr_metadata)
        enriched['qml_python_binding_status'] = qml_binding_status
        return enriched

    # No hay Claim o error de consulta: no agregamos el campo
    # AutonomyGovernancePolicy permite merge si el campo está ausente
    return pr_metadata


def _get_qml_binding_status_for_pr(
    workspace: str | None = None,
) -> str | None:
    """Consulta IntegrityClaimRepository para el estado QML_PYTHON_BINDING.

    Returns:
        'PASS', 'FAIL', or None si no hay Claim o error.
    """
    if not workspace:
        return None

    try:
        from iabv_v15.infra.persistence.database import AppDatabase
        from iabv_v15.infra.persistence.integrity_claim_repository import IntegrityClaimRepository

        data_dir = Path(workspace) / 'data' / 'evolution'
        db_path = data_dir / 'integrity_claims.sqlite'

        if not db_path.exists():
            return None

        db = AppDatabase(str(db_path))
        repo = IntegrityClaimRepository(db)

        current_status = _get_qml_binding_status_from_repo(repo, workspace)
        db.close()

        return current_status
    except Exception:
        # Si falla la consulta, no bloqueamos el merge por Claim
        return None


def _get_qml_binding_status_from_repo(
    repo: Any,
    workspace: str,
) -> str | None:
    """Consulta IntegrityClaimRepository pre-configurado para el estado QML_PYTHON_BINDING.

    Args:
        repo: IntegrityClaimRepository ya configurado
        workspace: Ruta del workspace para calcular claim_id

    Returns:
        'PASS', 'FAIL', or None si no hay Claim o error.
    """
    try:
        # Claim identity estable (mismo esquema que SelfCodeAnalysis)
        claim_identity_input = f"slot_decorators:{workspace}"
        claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]

        current_status = repo.get_current_status(claim_id)
        return current_status
    except Exception:
        # Si falla la consulta, no bloqueamos el merge por Claim
        return None
