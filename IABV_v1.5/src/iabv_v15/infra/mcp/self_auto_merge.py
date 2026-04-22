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

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any


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


def auto_merge(
    repo: str,
    pr_number: int,
    *,
    method: str = "squash",
    force: bool = False,
    client: GitHubClient | None = None,
    token: str | None = None,
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
