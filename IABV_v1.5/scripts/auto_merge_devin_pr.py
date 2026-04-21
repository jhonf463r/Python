"""CLI para auto-mergear PRs generados por Devin en ramas ``devin/*``.

Motivacion: reducir el trabajo manual del usuario. En vez de pedirle que
haga click en el boton ``Merge`` cada vez que Devin pushea un fix, este
helper mergea el PR via GitHub API. Esta pensado para correrse desde la
VM de Devin (donde vive ``GITHUB_TOKEN_IABV``); el usuario tipicamente
no lo necesita.

Uso:

    python -m scripts.auto_merge_devin_pr <pr_number> [--repo owner/repo]
                                          [--method squash|merge|rebase]
                                          [--force]

Salvaguardas (por defecto):
- Solo mergea PRs cuya rama empieza con ``devin/`` o ``iabv-auto/``.
  Otra rama requiere ``--force``.
- Solo mergea si ``mergeable_state`` no esta en ``blocked`` / ``dirty``.
- Solo mergea si todas las checks registradas pasan (``conclusion`` en
  ``success`` / ``skipped`` / ``neutral``). Si no hay checks registradas,
  asume OK (el repo IABV no tiene CI en este momento).

Salida:
- Codigo 0: merge ejecutado (o el PR ya estaba merged/closed).
- Codigo 2: salvaguarda bloqueo; imprime razon.
- Codigo 3: error HTTP.

No toca repos ni branches fuera del PR objetivo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_REPO = "jhonf463r/Python"


def _resolve_token() -> str:
    for name in ("GITHUB_TOKEN_IABV", "IABV_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "error: no encontre un token GitHub. Exporta uno de "
        "GITHUB_TOKEN_IABV / IABV_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN."
    )


def _api(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "iabv-auto-merge/1")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"http {exc.code} {method} {url}: {detail[:500]}") from exc
    return json.loads(body) if body else {}


def is_safe_branch(branch: str) -> bool:
    """Politica: solo mergeamos auto ramas generadas por Devin o IABV.

    Pure function para testear sin pegar a GitHub.
    """

    return branch.startswith(("devin/", "iabv-auto/"))


def checks_are_green(check_runs: list[dict[str, Any]]) -> tuple[bool, str]:
    """Evalua la respuesta de ``GET /commits/{sha}/check-runs``.

    Devuelve ``(ok, razon)``. Si no hay checks, ``ok=True`` con razon
    ``no-checks``. Si alguna esta ``in_progress`` / ``queued`` devuelve
    ``False`` porque todavia no se sabe el resultado. Si alguna concluyo
    con ``failure`` / ``timed_out`` / ``cancelled`` devuelve ``False``.
    """

    if not check_runs:
        return True, "no-checks"
    for run in check_runs:
        status = run.get("status")
        if status != "completed":
            return False, f"check pendiente: {run.get('name')} [{status}]"
        conclusion = run.get("conclusion")
        if conclusion not in ("success", "skipped", "neutral"):
            return False, f"check fallo: {run.get('name')} [{conclusion}]"
    return True, "all-green"


def _fetch_pr(repo: str, number: int, token: str) -> dict[str, Any]:
    return _api("GET", f"https://api.github.com/repos/{repo}/pulls/{number}", token)


def _fetch_check_runs(repo: str, sha: str, token: str) -> list[dict[str, Any]]:
    resp = _api("GET", f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100", token)
    return resp.get("check_runs", [])


def auto_merge(repo: str, number: int, method: str, force: bool) -> int:
    token = _resolve_token()
    pr = _fetch_pr(repo, number, token)

    if pr.get("merged"):
        print(f"pr #{number} ya esta merged; nada que hacer.")
        return 0
    if pr.get("state") != "open":
        print(f"pr #{number} esta {pr.get('state')}; no mergeo cerrados.")
        return 0

    head_ref = pr.get("head", {}).get("ref", "")
    head_sha = pr.get("head", {}).get("sha", "")
    mergeable_state = pr.get("mergeable_state")
    title = pr.get("title", "")

    print(f"pr #{number} branch={head_ref} state={mergeable_state} title={title!r}")

    if not force and not is_safe_branch(head_ref):
        print(f"salvaguarda: rama '{head_ref}' no coincide con devin/* o iabv-auto/*; usa --force para saltar.")
        return 2

    if mergeable_state in ("blocked", "dirty", "behind"):
        print(f"salvaguarda: mergeable_state='{mergeable_state}'; GitHub bloquea el merge automatico.")
        return 2

    check_runs = _fetch_check_runs(repo, head_sha, token)
    ok, reason = checks_are_green(check_runs)
    print(f"checks: {reason} ({len(check_runs)} runs)")
    if not ok and not force:
        return 2

    payload = {"merge_method": method}
    result = _api(
        "PUT",
        f"https://api.github.com/repos/{repo}/pulls/{number}/merge",
        token,
        payload,
    )
    if result.get("merged"):
        print(f"pr #{number} merged via {method}: {result.get('sha')}")
        return 0

    print(f"merge API response sin 'merged': {result!r}")
    return 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr_number", type=int)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--method", default="squash", choices=("squash", "merge", "rebase"))
    parser.add_argument("--force", action="store_true", help="saltea salvaguardas de rama/checks")
    args = parser.parse_args(argv)
    return auto_merge(args.repo, args.pr_number, args.method, args.force)


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
