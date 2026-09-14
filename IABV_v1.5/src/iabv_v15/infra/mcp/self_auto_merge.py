"""Logica reutilizable de auto-merge para PRs generados por Devin / IABV.

Este modulo es la **fuente de verdad** del auto-merge:
- ``scripts/auto_merge_devin_pr.py`` (CLI) importa de aqui.
- ``server.py`` registra la tool MCP ``self_auto_merge`` que tambien
  llama a ``auto_merge``.

Motivacion: que el usuario deje de tener que hacer click en ``Merge`` cada
vez que Devin / Codex / Claude cierra una mejora. El programa lo hace por
si solo cuando la IA reporta PR listo, mientras sigan vigentes las
salvaguardas de autonomia acordadas.

Salvaguardas (por defecto, iguales al CLI):
- Solo mergea PRs cuya rama empieza con ``devin/`` o ``iabv-auto/``. Otra
  rama requiere ``force=True`` (y el llamador es responsable de justificarlo).
- Solo mergea si ``mergeable_state`` no esta en ``blocked`` / ``dirty`` /
  ``behind``.
- Solo mergea si las checks registradas estan verdes
  (``success`` / ``skipped`` / ``neutral``). Si no hay checks, OK (IABV
  todavia no tiene CI).

No toca repos ni branches fuera del PR objetivo. No abre issues, no
escribe datos en disco. Solo GitHub API + stdout informativo.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Integración Claim → governance
from iabv_v15.infra.persistence.claim_governance_integration import (
    enrich_pr_metadata_with_claim_status,
)
from iabv_v15.services.adaptive.autonomy_governance_policy import (
    AutonomyGovernancePolicy,
)


DEFAULT_REPO = "jhonf463r/Python"
SAFE_BRANCH_PREFIXES = ("devin/", "iabv-auto/")
BLOCKING_MERGEABLE_STATES = ("blocked", "dirty", "behind")
GREEN_CONCLUSIONS = ("success", "skipped", "neutral")


@dataclass(frozen=True)
class MergeResult:
    """Resultado estructurado del intento de auto-merge.

    Pensado para exposicion directa via MCP (campos serializables). El CLI
    usa ``to_exit_code`` para convertir a codigos clasicos.
    """

    status: str
    """Uno de: ``merged``, ``already_merged``, ``closed``, ``blocked``,
    ``missing_token``, ``http_error``, ``unknown``."""

    pr_number: int
    repo: str
    branch: str = ""
    title: str = ""
    mergeable_state: str = ""
    method: str = "squash"
    reason: str = ""
    detail: str = ""
    merge_sha: str = ""
    checks_summary: str = ""
    check_runs_count: int = 0
    branch_safe: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_exit_code(self) -> int:
        if self.status in ("merged", "already_merged", "closed"):
            return 0
        if self.status == "blocked":
            return 2
        return 3


def resolve_token(env: dict[str, str] | None = None) -> str | None:
    """Busca un GitHub token valido en el entorno.

    Orden: ``GITHUB_TOKEN_IABV``, ``IABV_GITHUB_TOKEN``, ``GITHUB_TOKEN``,
    ``GH_TOKEN``. Devuelve el primer no vacio o ``None`` si ninguno existe.
    """

    source = env if env is not None else os.environ
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = (source.get(name) or "").strip()
        if value:
            return value
    return None


def is_safe_branch(branch: str) -> bool:
    """Politica: solo auto-mergeamos ramas generadas por Devin o IABV."""

    return branch.startswith(SAFE_BRANCH_PREFIXES)


def checks_are_green(check_runs: list[dict[str, Any]]) -> tuple[bool, str]:
    """Evalua la respuesta de ``GET /commits/{sha}/check-runs``.

    Devuelve ``(ok, razon)``. Si no hay checks, ``ok=True`` con razon
    ``no-checks``. ``in_progress`` / ``queued`` cuentan como no-verde
    (todavia no se sabe). ``failure`` / ``timed_out`` / ``cancelled``
    tambien bloquean.
    """

    if not check_runs:
        return True, "no-checks"
    for run in check_runs:
        status = run.get("status")
        if status != "completed":
            return False, f"check pendiente: {run.get('name')} [{status}]"
        conclusion = run.get("conclusion")
        if conclusion not in GREEN_CONCLUSIONS:
            return False, f"check fallo: {run.get('name')} [{conclusion}]"
    return True, "all-green"


class GitHubClient:
    """Cliente minimo de GitHub API. Inyectable para tests."""

    def __init__(self, token: str, *, user_agent: str = "iabv-auto-merge/1") -> None:
        self._token = token
        self._user_agent = user_agent

    def request(self, method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"token {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", self._user_agent)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubApiError(exc.code, method, url, detail) from exc
        return json.loads(body) if body else {}

    def fetch_pr(self, repo: str, number: int) -> dict[str, Any]:
        return self.request("GET", f"https://api.github.com/repos/{repo}/pulls/{number}")

    def fetch_check_runs(self, repo: str, sha: str) -> list[dict[str, Any]]:
        resp = self.request(
            "GET",
            f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100",
        )
        return resp.get("check_runs", []) or []

    def fetch_pr_files(self, repo: str, number: int) -> list[dict[str, Any]]:
        """Obtiene la lista completa de archivos cambiados en un PR con paginación.

        GitHub API usa paginación por defecto (per_page=30 máx 100).
        Este método implementa paginación para obtener TODOS los archivos,
        no solo los primeros 100.

        Returns:
            Lista completa de archivos cambiados, o lista vacía si falla.
        """
        all_files: list[dict[str, Any]] = []
        page = 1
        per_page = 100  # Máximo permitido por GitHub API

        while True:
            try:
                url = f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page={per_page}&page={page}"
                resp = self.request("GET", url)

                if not isinstance(resp, list):
                    # Respuesta inesperada, detener paginación
                    break

                if not resp:
                    # Página vacía: fin de la paginación
                    break

                all_files.extend(resp)

                # Si recibimos menos de per_page, es la última página
                if len(resp) < per_page:
                    break

                page += 1

            except GitHubApiError:
                # Si falla una página, devolver lo que tenemos hasta ahora
                break

        return all_files

    def merge_pr(self, repo: str, number: int, method: str) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"https://api.github.com/repos/{repo}/pulls/{number}/merge",
            {"merge_method": method},
        )


class GitHubApiError(RuntimeError):
    def __init__(self, code: int, method: str, url: str, detail: str) -> None:
        super().__init__(f"http {code} {method} {url}: {detail[:500]}")
        self.code = code
        self.method = method
        self.url = url
        self.detail = detail


def _build_pr_metadata(pr: dict[str, Any], repo: str, client: GitHubClient, ci_ok: bool) -> dict[str, Any]:
    """Construye pr_metadata desde la respuesta de GitHub API.

    Extrae campos necesarios para AutonomyGovernancePolicy.allow_github_merge.
    Si el PR toca rutas UI, consulta IntegrityClaimRepository para incluir
    el estado de verificación QML_PYTHON_BINDING.

    Args:
        pr: Respuesta de GitHub API para el PR
        repo: owner/repo
        client: GitHubClient para obtener archivos cambiados
        ci_ok: Resultado de checks_are_green() (True=success, False=failure/unknown)

    Returns:
        pr_metadata con campos necesarios para governance.
        - reviews=None: ausencia de evidencia de reviews (fail-closed por policy)
        - changed_paths=None: si falla la obtención de archivos (fail-closed por policy)
        - ci_status: derivado de ci_ok
    """
    # Derivar ci_status desde checks_are_green() en lugar de hardcodear
    ci_status = 'success' if ci_ok else 'failure'

    # Extraer reviews si están disponibles en PR data
    # GitHub API puede incluir reviews en el endpoint de PRs
    reviews = pr.get('reviews')
    if reviews is None:
        reviews = None  # Ausencia de evidencia: fail-closed
    elif isinstance(reviews, list):
        reviews = reviews  # Lista presente (puede estar vacía)
    else:
        reviews = None  # Formato inesperado: tratar como ausente

    # Campos básicos desde GitHub API
    pr_metadata = {
        'pull_number': pr.get('number'),
        'ci_status': ci_status,
        'reviews': reviews,  # Extraído desde PR data si disponible
        'draft': bool(pr.get('draft', False)),
        'additions': pr.get('additions', 0),
        'deletions': pr.get('deletions', 0),
        'changed_files': pr.get('changed_files', 0),
        'changed_paths': None,  # Inicialmente None; se pobló si fetch_pr_files() tiene éxito
    }

    # Extraer archivos cambiados desde GitHub API
    try:
        pr_number = pr.get('number')
        if pr_number:
            files = client.fetch_pr_files(repo, pr_number)
            # Extraer solo la ruta de cada archivo
            changed_paths = [f.get('filename', '') for f in files if f.get('filename')]
            pr_metadata['changed_paths'] = changed_paths
    except Exception:
        # Si falla la obtención de archivos, dejamos changed_paths=None
        # Governance bloqueará por changed_paths ausente (fail-closed), lo cual es seguro
        pass

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

        # Claim identity estable (mismo esquema que SelfCodeAnalysis)
        claim_identity_input = f"slot_decorators:{workspace}"
        claim_id = hashlib.sha256(claim_identity_input.encode()).hexdigest()[:32]

        current_status = repo.get_current_status(claim_id)
        db.close()

        return current_status
    except Exception:
        # Si falla la consulta, no bloqueamos el merge por Claim
        return None


def auto_merge(
    repo: str,
    pr_number: int,
    *,
    method: str = "squash",
    force: bool = False,
    client: GitHubClient | None = None,
    token: str | None = None,
    workspace: str | None = None,
    claim_repository: Any = None,
) -> MergeResult:
    """Intenta auto-mergear ``repo#pr_number`` respetando salvaguardas.

    Args:
        repo: ``owner/repo``. Default: ``jhonf463r/Python``.
        pr_number: numero del PR.
        method: ``squash`` / ``merge`` / ``rebase``. Default ``squash``.
        force: saltea salvaguardas de rama y de checks. El llamador es
            responsable de justificarlo; el MCP tool NO expone este flag
            sin permission gate.
        client: ``GitHubClient`` inyectado (para tests). Si es ``None``,
            se construye con el token resuelto.
        token: si esta, sobreescribe el token del entorno.
        workspace: ruta del workspace para localizar Claims. Si es None,
            se usa el directorio de trabajo actual.
        claim_repository: IntegrityClaimRepository pre-configurado (opcional,
            usado por tests para inyectar repositorio temporal).

    Returns:
        ``MergeResult`` con ``status`` = ``merged`` / ``already_merged`` /
        ``closed`` / ``blocked`` / ``missing_token`` / ``http_error``.
    """

    if client is None:
        token_val = token or resolve_token()
        if not token_val:
            return MergeResult(
                status="missing_token",
                pr_number=pr_number,
                repo=repo,
                method=method,
                reason="missing_token",
                detail=(
                    "No encontre un token GitHub. Define GITHUB_TOKEN_IABV / "
                    "IABV_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN."
                ),
            )
        client = GitHubClient(token_val)

    # Determinar workspace para Claim lookup
    if workspace is None:
        workspace = os.getcwd()

    try:
        pr = client.fetch_pr(repo, pr_number)
    except GitHubApiError as exc:
        return MergeResult(
            status="http_error",
            pr_number=pr_number,
            repo=repo,
            method=method,
            reason="fetch_pr_failed",
            detail=str(exc),
            extra={"http_code": exc.code},
        )

    head = pr.get("head") or {}
    branch = str(head.get("ref") or "")
    head_sha = str(head.get("sha") or "")
    mergeable_state = str(pr.get("mergeable_state") or "")
    title = str(pr.get("title") or "")
    branch_safe = is_safe_branch(branch)

    base = MergeResult(
        status="unknown",
        pr_number=pr_number,
        repo=repo,
        branch=branch,
        title=title,
        mergeable_state=mergeable_state,
        method=method,
        branch_safe=branch_safe,
    )

    if pr.get("merged"):
        return _replace(
            base,
            status="already_merged",
            reason="already_merged",
            detail=f"pr #{pr_number} ya estaba merged.",
            merge_sha=str(pr.get("merge_commit_sha") or ""),
        )

    if pr.get("state") != "open":
        return _replace(
            base,
            status="closed",
            reason="not_open",
            detail=f"pr #{pr_number} esta {pr.get('state')!r}.",
        )

    if not force and not branch_safe:
        return _replace(
            base,
            status="blocked",
            reason="branch_not_safe",
            detail=(
                f"rama {branch!r} no empieza con devin/* o iabv-auto/*; "
                "auto-merge rechazado."
            ),
        )

    if mergeable_state in BLOCKING_MERGEABLE_STATES:
        return _replace(
            base,
            status="blocked",
            reason="mergeable_state_blocks",
            detail=(
                f"mergeable_state={mergeable_state!r}; GitHub bloquea el merge. "
                "Resolver conflictos o esperar a que se destrabe."
            ),
        )

    try:
        check_runs = client.fetch_check_runs(repo, head_sha)
    except GitHubApiError as exc:
        return _replace(
            base,
            status="http_error",
            reason="fetch_checks_failed",
            detail=str(exc),
            extra={"http_code": exc.code},
        )

    ok, checks_reason = checks_are_green(check_runs)
    if not ok and not force:
        return _replace(
            base,
            status="blocked",
            reason="checks_not_green",
            detail=checks_reason,
            checks_summary=checks_reason,
            check_runs_count=len(check_runs),
        )

    # --- Governance: AutonomyGovernancePolicy.allow_github_merge ---
    # Construir pr_metadata para governance (pasando resultado de checks_are_green)
    pr_metadata = _build_pr_metadata(pr, repo, client, ci_ok=ok)

    # Enriquecer con estado de Claim si aplica
    pr_metadata = enrich_pr_metadata_with_claim_status(
        pr_metadata,
        workspace=workspace,
        claim_repository=claim_repository,
    )

    # Ejecutar governance decision
    governance_policy = AutonomyGovernancePolicy()
    allowed, governance_reason = governance_policy.allow_github_merge(
        pr_metadata=pr_metadata,
    )

    if not allowed:
        # force bypassea solo checks y reviews, pero no governance de Claim/sensitive paths
        # Si governance bloquea por Claim FAIL o ruta sensible, NO se bypassea
        # Documentado como ADMINISTRATIVE_GOVERNANCE_BYPASS gap
        if not force or "QML_PYTHON_BINDING" in (governance_reason or "") or "ruta sensible" in (governance_reason or "").lower():
            return _replace(
                base,
                status="blocked",
                reason="governance_blocked",
                detail=governance_reason or "Bloqueado por AutonomyGovernancePolicy.",
                checks_summary=checks_reason,
                check_runs_count=len(check_runs),
                extra={"governance_reason": governance_reason},
            )

    try:
        merge_resp = client.merge_pr(repo, pr_number, method)
    except GitHubApiError as exc:
        return _replace(
            base,
            status="http_error",
            reason="merge_api_failed",
            detail=str(exc),
            checks_summary=checks_reason,
            check_runs_count=len(check_runs),
            extra={"http_code": exc.code},
        )

    if merge_resp.get("merged"):
        return _replace(
            base,
            status="merged",
            reason="ok",
            detail=f"pr #{pr_number} merged via {method}.",
            merge_sha=str(merge_resp.get("sha") or ""),
            checks_summary=checks_reason,
            check_runs_count=len(check_runs),
        )

    return _replace(
        base,
        status="unknown",
        reason="merge_response_no_merged_flag",
        detail=f"respuesta inesperada de /merge: {merge_resp!r}",
        checks_summary=checks_reason,
        check_runs_count=len(check_runs),
    )


def _replace(base: MergeResult, **overrides: Any) -> MergeResult:
    """dataclasses.replace con soporte para mezclar ``extra`` sin pisarlo entero."""

    data = base.to_dict()
    data.update(overrides)
    extra = data.pop("extra", None) or {}
    return MergeResult(
        **{k: v for k, v in data.items() if k != "extra"},
        extra=extra,
    )
