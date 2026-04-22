"""CLI para auto-mergear PRs generados por Devin en ramas ``devin/*``.

Este script es un **wrapper CLI** sobre
``iabv_v15.infra.mcp.self_auto_merge.auto_merge``. La logica real
(salvaguardas, llamadas a GitHub API, dataclass de resultado) vive en ese
modulo para poder reusarse tambien como tool MCP ``self_auto_merge``.

Uso:

    python scripts/auto_merge_devin_pr.py <pr_number> [--repo owner/repo]
                                          [--method squash|merge|rebase]
                                          [--force]

Salvaguardas (por defecto):
- Solo mergea PRs cuya rama empieza con ``devin/`` o ``iabv-auto/``.
  Otra rama requiere ``--force``.
- Solo mergea si ``mergeable_state`` no esta en ``blocked`` / ``dirty`` /
  ``behind``.
- Solo mergea si todas las checks registradas pasan (``conclusion`` en
  ``success`` / ``skipped`` / ``neutral``). Si no hay checks registradas,
  asume OK (el repo IABV no tiene CI en este momento).

Salida:
- Codigo 0: merge ejecutado (o el PR ya estaba merged/closed).
- Codigo 2: salvaguarda bloqueo; imprime razon.
- Codigo 3: error HTTP u otro fallo.

No toca repos ni branches fuera del PR objetivo.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Permite correr el script sin ``PYTHONPATH=src`` exportado.

    El repo coloca el codigo bajo ``IABV_v1.5/src/iabv_v15``. Si el CWD
    es la raiz del subproyecto, ``src/`` no esta en ``sys.path`` por
    defecto. Lo agregamos solo para esta ejecucion.
    """

    here = Path(__file__).resolve()
    for candidate in (here.parent.parent / "src", here.parent.parent.parent / "IABV_v1.5" / "src"):
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


_ensure_src_on_path()

from iabv_v15.infra.mcp.self_auto_merge import (  # noqa: E402
    DEFAULT_REPO,
    MergeResult,
    auto_merge,
    checks_are_green,
    is_safe_branch,
    resolve_token,
)


__all__ = [
    "DEFAULT_REPO",
    "MergeResult",
    "auto_merge",
    "checks_are_green",
    "is_safe_branch",
    "resolve_token",
    "main",
]


def _print_result(result: MergeResult) -> None:
    print(
        f"pr #{result.pr_number} branch={result.branch} "
        f"state={result.mergeable_state or 'unknown'} title={result.title!r}"
    )
    if result.checks_summary:
        print(f"checks: {result.checks_summary} ({result.check_runs_count} runs)")
    if result.status == "merged":
        print(f"pr #{result.pr_number} merged via {result.method}: {result.merge_sha}")
    elif result.status == "already_merged":
        print(f"pr #{result.pr_number} ya esta merged; nada que hacer.")
    elif result.status == "closed":
        print(result.detail)
    elif result.status == "blocked":
        print(f"salvaguarda: {result.detail}")
    elif result.status == "missing_token":
        print(f"error: {result.detail}", file=sys.stderr)
    elif result.status == "http_error":
        print(f"error http: {result.detail}", file=sys.stderr)
    else:
        print(f"merge API response sin 'merged': {result.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr_number", type=int)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--method", default="squash", choices=("squash", "merge", "rebase"))
    parser.add_argument("--force", action="store_true", help="saltea salvaguardas de rama/checks")
    args = parser.parse_args(argv)

    token = resolve_token()
    if not token:
        print(
            "error: no encontre un token GitHub. Exporta uno de "
            "GITHUB_TOKEN_IABV / IABV_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN.",
            file=sys.stderr,
        )
        return 3

    result = auto_merge(
        args.repo,
        args.pr_number,
        method=args.method,
        force=args.force,
        token=token,
    )
    _print_result(result)
    return result.to_exit_code()


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
