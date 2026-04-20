#!/usr/bin/env python3
"""Ejecuta `SelfAuditService.run()` contra un workspace IABV v1.5 real.

Es el camino directo (sin MCP ni transport) para validar en Windows que la
auditoría operativa produce el snapshot esperado y deja los artefactos en
disco:

- `data/evolution/self_audit/latest.json`
- `data/evolution/self_audit/latest.md`
- `data/evolution/self_audit/history/<ISO>.json`

El script bootstrappea `AppBootstrap(workspace_root=...)` y llama al service
wireado en el container; **no** arranca UI ni `MCPBridgeService`. Cero
side effects fuera del directorio `data/evolution/self_audit/`.

Uso:

    python IABV_v1.5/scripts/run_self_audit.py
    python IABV_v1.5/scripts/run_self_audit.py --reason "validación post-merge"
    python IABV_v1.5/scripts/run_self_audit.py --workspace C:\\Python\\IABV_v1.5 --json
    python IABV_v1.5/scripts/run_self_audit.py --print-md

Exit code: 0 siempre que el service responda (audit es read-only y degrada
graciosamente); 1 si `SelfAuditService.run()` levanta una excepción no
capturada.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# El script se distribuye dentro de IABV_v1.5/scripts/; `src/` queda un
# directorio arriba. Insertamos el path antes de importar para permitir
# correr el archivo "en crudo" sin instalar el paquete.
_REPO_SRC = Path(__file__).resolve().parent.parent / "src"
if _REPO_SRC.is_dir() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))


@dataclass(frozen=True)
class RunSummary:
    generated_at: str
    reason: str
    tool_checks_total: int
    tool_checks_available: int
    environment_matched: bool
    environment_mismatches: int
    pending_issues: int
    summary_markdown_chars: int
    latest_json: str
    latest_md: str
    history_file: str

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "reason": self.reason,
            "tool_checks": {
                "total": self.tool_checks_total,
                "available": self.tool_checks_available,
            },
            "environment_match": {
                "matched": self.environment_matched,
                "mismatches": self.environment_mismatches,
            },
            "pending_issues": self.pending_issues,
            "summary_markdown_chars": self.summary_markdown_chars,
            "artifacts": {
                "latest_json": self.latest_json,
                "latest_md": self.latest_md,
                "history_file": self.history_file,
            },
        }


def detect_workspace_root(start: Path) -> Path:
    """Busca el ancestro con `pyproject.toml`. Si no hay, devuelve `start`.

    Idéntico al helper del smoke para mantener la misma convención.
    """

    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current


def _expected_history_file(workspace_root: Path, generated_at: object) -> Path:
    """Reconstruye la ruta del archivo de historial tal como la calcula el service.

    El service usa `snapshot.generated_at.strftime("%Y%m%dT%H%M%S%fZ")`.
    """

    from datetime import datetime

    history_dir = Path(workspace_root) / "data" / "evolution" / "self_audit" / "history"
    stamp: str
    if isinstance(generated_at, datetime):
        stamp = generated_at.strftime("%Y%m%dT%H%M%S%fZ")
    else:
        stamp = "<unknown>"
    return history_dir / f"{stamp}.json"


def run(
    workspace_root: Path,
    *,
    reason: str | None = None,
) -> tuple[RunSummary, str]:
    """Bootstrappea el container, corre el audit y devuelve un resumen + md."""

    # Import diferido: `AppBootstrap` arrastra todo el contenedor y algunos
    # módulos pesados (sqlite, numpy vía embeddings, etc.). Importarlo acá
    # mantiene `--help` barato.
    from iabv_v15.bootstrap import AppBootstrap  # noqa: PLC0415

    app = AppBootstrap(workspace_root=str(workspace_root))
    service = app.self_audit_service
    snapshot = service.run(reason=reason)

    workspace = Path(workspace_root).resolve()
    root = workspace / "data" / "evolution" / "self_audit"
    latest_json = root / "latest.json"
    latest_md = root / "latest.md"
    history_file = _expected_history_file(workspace, snapshot.generated_at)

    available = sum(
        1 for check in snapshot.tool_checks if getattr(check, "available", False)
    )
    mismatches = len(getattr(snapshot.environment_match, "mismatches", []) or [])
    generated_at_iso = (
        snapshot.generated_at.isoformat()
        if hasattr(snapshot.generated_at, "isoformat")
        else str(snapshot.generated_at)
    )

    summary = RunSummary(
        generated_at=generated_at_iso,
        reason=snapshot.reason or "",
        tool_checks_total=len(snapshot.tool_checks),
        tool_checks_available=available,
        environment_matched=bool(getattr(snapshot.environment_match, "matched", False)),
        environment_mismatches=mismatches,
        pending_issues=len(snapshot.pending_issues),
        summary_markdown_chars=len(snapshot.summary_markdown or ""),
        latest_json=str(latest_json),
        latest_md=str(latest_md),
        history_file=str(history_file),
    )
    return summary, snapshot.summary_markdown or ""


def _format_text(summary: RunSummary, *, markdown: str | None) -> str:
    lines: list[str] = [
        "=== IABV v1.5 SelfAudit ===",
        f"generated_at       : {summary.generated_at}",
        f"reason             : {summary.reason or '(sin razón)'}",
        f"tool_checks        : {summary.tool_checks_available}/{summary.tool_checks_total} available",
        (
            f"environment_match  : matched={summary.environment_matched} "
            f"mismatches={summary.environment_mismatches}"
        ),
        f"pending_issues     : {summary.pending_issues}",
        f"summary chars      : {summary.summary_markdown_chars}",
        "--- artifacts ---",
        f"latest.json        : {summary.latest_json}",
        f"latest.md          : {summary.latest_md}",
        f"history file       : {summary.history_file}",
    ]
    if markdown is not None:
        lines.extend(["--- summary_markdown ---", markdown])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help=(
            "Raíz del workspace IABV v1.5. Default: busca `pyproject.toml` "
            "desde el directorio del script."
        ),
    )
    parser.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Texto libre que se guarda en el snapshot como `reason`.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el resumen como JSON (machine-readable).",
    )
    parser.add_argument(
        "--print-md",
        action="store_true",
        help="Imprime el `summary_markdown` completo del snapshot.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Alias de --print-md para consistencia con smoke_audit_tools.",
    )
    args = parser.parse_args(argv)

    workspace_root = (
        args.workspace
        if args.workspace is not None
        else detect_workspace_root(Path(__file__).resolve().parent)
    )

    try:
        summary, markdown = run(workspace_root, reason=args.reason)
    except Exception as exc:  # noqa: BLE001 - defensa, reportamos y salimos 1
        print(f"ERROR: SelfAuditService.run() levantó: {exc!r}", file=sys.stderr)
        return 1

    show_md = args.print_md or args.verbose
    if args.json:
        payload = summary.to_dict()
        if show_md:
            payload["summary_markdown"] = markdown
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_format_text(summary, markdown=markdown if show_md else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
