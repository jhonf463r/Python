#!/usr/bin/env python3
"""Smoke manual de las 5 audit tools MCP sin levantar FastMCP.

El operador humano corre este script (típicamente en Windows) para verificar
que los helpers puros en `iabv_v15.infra.mcp.audit_tools` responden contra
un `workspace_root` real. El script NO habla MCP: importa los helpers y
los invoca directamente, reportando un status `ok | degraded | error` por
cada verificación.

Uso:

    python IABV_v1.5/scripts/smoke_audit_tools.py
    python IABV_v1.5/scripts/smoke_audit_tools.py --json
    python IABV_v1.5/scripts/smoke_audit_tools.py --workspace C:\\Python\\IABV_v1.5 --verbose

Exit code: 0 si no hay `error` (los `degraded` no cuentan), 1 si al menos
una verificación falló con `error`.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# El script se distribuye dentro de IABV_v1.5/scripts/; `src/` queda un
# directorio arriba. Insertamos el path antes de importar para permitir
# correr el archivo "en crudo" sin instalar el paquete.
_REPO_SRC = Path(__file__).resolve().parent.parent / "src"
if _REPO_SRC.is_dir() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from iabv_v15.infra.mcp.audit_tools import (  # noqa: E402
    AuditToolError,
    capture_ui_screenshot,
    git_status_and_log,
    list_repo_directory,
    read_repo_file,
    run_pytest,
)


CHECK_NAMES: tuple[str, ...] = (
    "git_status",
    "list_root",
    "read_file",
    "capture_screenshot",
    "run_pytest",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # "ok" | "degraded" | "error"
    detail: str = ""
    error_code: str = ""
    summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str | dict[str, str]]:
        payload: dict[str, str | dict[str, str]] = {"status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.summary:
            payload["summary"] = dict(self.summary)
        return payload


def detect_workspace_root(start: Path) -> Path:
    """Busca el ancestro con `pyproject.toml`. Si no hay, devuelve `start`."""

    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current


def _degraded_from_error_dict(
    name: str, payload: dict[str, object]
) -> CheckResult | None:
    """Si el helper devolvió `{error: ..., detail: ...}`, mapea a `degraded`."""

    raw_error = payload.get("error")
    if not raw_error:
        return None
    error_code = str(raw_error)
    detail = str(payload.get("detail") or "")
    return CheckResult(
        name=name,
        status="degraded",
        detail=detail,
        error_code=error_code,
    )


def check_git_status(workspace_root: Path) -> CheckResult:
    try:
        payload = git_status_and_log(workspace_root, limit=5)
    except AuditToolError as exc:
        return CheckResult(
            name="git_status",
            status="error",
            detail=exc.detail,
            error_code=exc.code,
        )
    degraded = _degraded_from_error_dict("git_status", payload)
    if degraded is not None:
        return degraded
    branch = str(payload.get("branch") or "")
    commits = payload.get("last_commits") or []
    commit_count = len(commits) if isinstance(commits, list) else 0
    dirty_count = int(payload.get("dirty_count") or 0)
    return CheckResult(
        name="git_status",
        status="ok",
        detail=f"branch={branch!r} commits={commit_count} dirty={dirty_count}",
        summary={
            "branch": branch,
            "commits": str(commit_count),
            "dirty": str(dirty_count),
        },
    )


def check_list_root(workspace_root: Path) -> CheckResult:
    try:
        payload = list_repo_directory(workspace_root, "", max_entries=10)
    except AuditToolError as exc:
        return CheckResult(
            name="list_root",
            status="error",
            detail=exc.detail,
            error_code=exc.code,
        )
    entries = payload.get("entries") or []
    total_listed = int(payload.get("total_listed") or 0)
    total_available = int(payload.get("total_available") or 0)
    truncated = bool(payload.get("truncated"))
    first_names: list[str] = []
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str):
                    first_names.append(name)
    return CheckResult(
        name="list_root",
        status="ok",
        detail=(
            f"listed={total_listed}/{total_available} truncated={truncated} "
            f"first={first_names[:3]}"
        ),
        summary={
            "listed": str(total_listed),
            "available": str(total_available),
            "truncated": str(truncated).lower(),
        },
    )


def check_read_file(workspace_root: Path) -> CheckResult:
    # El workspace_root oficial es `C:\Python\IABV_v1.5` (Windows) o el
    # checkout local equivalente: `AGENTS.md` vive en la raíz del
    # workspace, no dentro de un subdirectorio `IABV_v1.5/`.
    target = "AGENTS.md"
    try:
        payload = read_repo_file(workspace_root, target)
    except AuditToolError as exc:
        return CheckResult(
            name="read_file",
            status="error",
            detail=f"{target}: {exc.detail}",
            error_code=exc.code,
        )
    size = int(payload.get("size") or 0)
    content = payload.get("content")
    first_chars = ""
    if isinstance(content, str):
        first_chars = content.strip().splitlines()[0] if content.strip() else ""
    return CheckResult(
        name="read_file",
        status="ok",
        detail=f"path={target} size={size} first_line={first_chars[:60]!r}",
        summary={"path": target, "size": str(size)},
    )


def check_capture_screenshot() -> CheckResult:
    try:
        payload = capture_ui_screenshot(provider=None)
    except Exception as exc:  # pragma: no cover - defensa
        return CheckResult(
            name="capture_screenshot",
            status="error",
            detail=f"capture_ui_screenshot levantó: {exc!r}",
            error_code="unexpected_exception",
        )
    degraded = _degraded_from_error_dict("capture_screenshot", payload)
    if degraded is not None:
        return degraded
    size_bytes = int(payload.get("size_bytes") or 0)
    fmt = str(payload.get("format") or "")
    region = str(payload.get("region") or "")
    has_b64 = bool(payload.get("bytes_base64"))
    return CheckResult(
        name="capture_screenshot",
        status="ok",
        detail=f"region={region!r} format={fmt} size_bytes={size_bytes} base64={has_b64}",
        summary={
            "region": region,
            "format": fmt,
            "size_bytes": str(size_bytes),
        },
    )


def check_run_pytest(workspace_root: Path) -> CheckResult:
    suite = "tests/test_mcp_audit_tools.py"
    keyword = "is_sensitive_path"
    try:
        payload = run_pytest(workspace_root, suite=suite, keyword=keyword)
    except AuditToolError as exc:
        return CheckResult(
            name="run_pytest",
            status="error",
            detail=exc.detail,
            error_code=exc.code,
        )
    passed = int(payload.get("passed") or 0)
    failed = int(payload.get("failed") or 0)
    errors = int(payload.get("errors") or 0)
    returncode = int(payload.get("returncode") or 0)
    timed_out = bool(payload.get("timed_out"))
    summary = {
        "suite": suite,
        "keyword": keyword,
        "passed": str(passed),
        "failed": str(failed),
        "errors": str(errors),
        "returncode": str(returncode),
        "timed_out": str(timed_out).lower(),
    }
    # El helper es el que ejecuta pytest; para el smoke consideramos `ok`
    # cuando la corrida terminó con tests pasados y sin fallos; si hubo
    # fallos/errores o timeout la corrida se completó pero con
    # resultado negativo — lo marcamos `degraded` para diferenciarlo de
    # un `error` del propio helper.
    if timed_out:
        return CheckResult(
            name="run_pytest",
            status="degraded",
            detail=f"pytest timed out after returncode={returncode}",
            error_code="pytest_timeout",
            summary=summary,
        )
    if failed or errors:
        return CheckResult(
            name="run_pytest",
            status="degraded",
            detail=(
                f"passed={passed} failed={failed} errors={errors} "
                f"returncode={returncode}"
            ),
            error_code="pytest_failures",
            summary=summary,
        )
    if passed == 0 and returncode != 0:
        return CheckResult(
            name="run_pytest",
            status="degraded",
            detail=(
                f"pytest terminó sin tests ejecutados (returncode={returncode})."
            ),
            error_code="pytest_no_tests",
            summary=summary,
        )
    return CheckResult(
        name="run_pytest",
        status="ok",
        detail=f"passed={passed} returncode={returncode}",
        summary=summary,
    )


def run_all_checks(workspace_root: Path) -> list[CheckResult]:
    return [
        check_git_status(workspace_root),
        check_list_root(workspace_root),
        check_read_file(workspace_root),
        check_capture_screenshot(),
        check_run_pytest(workspace_root),
    ]


def _format_text_report(
    workspace_root: Path,
    results: list[CheckResult],
    *,
    verbose: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"workspace_root: {workspace_root}")
    lines.append("")
    for result in results:
        header = f"[{result.status.upper():<8}] {result.name}"
        if result.error_code:
            header += f"  error_code={result.error_code}"
        lines.append(header)
        if result.detail:
            lines.append(f"    detail: {result.detail}")
        if verbose and result.summary:
            for key in sorted(result.summary):
                lines.append(f"    {key}={result.summary[key]}")
    return "\n".join(lines)


def _counts(results: list[CheckResult]) -> tuple[int, int, int]:
    ok = sum(1 for r in results if r.status == "ok")
    degraded = sum(1 for r in results if r.status == "degraded")
    errors = sum(1 for r in results if r.status == "error")
    return ok, degraded, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke manual para las 5 audit tools MCP (sin levantar FastMCP)."
        ),
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help=(
            "Ruta al workspace_root. Si no se provee, se detecta buscando el "
            "pyproject.toml ancestro."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite el resultado como JSON en stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Agrega summary extendido en el reporte de texto.",
    )
    args = parser.parse_args(argv)

    if args.workspace:
        workspace_root = Path(args.workspace).expanduser().resolve()
    else:
        workspace_root = detect_workspace_root(Path.cwd())

    results = run_all_checks(workspace_root)
    ok, degraded, errors = _counts(results)

    payload: dict[str, object] = {
        "workspace_root": str(workspace_root),
        "summary": {
            "ok": ok,
            "degraded": degraded,
            "errors": errors,
            "total": len(results),
        },
    }
    for result in results:
        payload[result.name] = result.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(_format_text_report(workspace_root, results, verbose=args.verbose))
        print("")
        print(
            f"{ok} of {len(results)} ok, {degraded} degraded, {errors} errors"
        )

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
