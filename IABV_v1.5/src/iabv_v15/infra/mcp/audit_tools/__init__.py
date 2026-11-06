"""Helpers puros para las tools de auditoría humana del MCP server.

Esta capa concentra la lógica que NO depende de FastMCP:

- normalización/validación de rutas dentro del `workspace_root`
  (rechaza `..`, paths absolutos, o subir fuera del workspace);
- blacklist de archivos sensibles (secrets, credenciales, llaves);
- whitelist y ejecución segura de la batería `pytest` oficial;
- inspección read-only de `git` (`status --porcelain` + `log`);
- listado de directorios con `{name, type, size, mtime}`;
- captura de screenshot con degradación explícita cuando la UI no está
  mapeada (el caso típico de los tests Linux headless).

Los tests que consumen estos helpers no necesitan instanciar `IABVMCPServer`
ni levantar el container; eso es parte del contrato "fácil de testear".

El paquete contiene submódulos adicionales para tools nuevas (ej.
``probe_assistant_login``); los helpers core viven en este ``__init__``
para preservar la API pública existente (``audit_tools.run_pytest``,
``audit_tools.AuditToolError``, etc.).
"""

from __future__ import annotations

import base64
import fnmatch
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

# Submódulos nuevos — importados acá para que sean accesibles como
# ``audit_tools.probe_assistant_login`` y compañía sin forzar a los
# callers a conocer la estructura interna del paquete.
from iabv_v15.infra.mcp.audit_tools.probe_assistant_login import (  # noqa: E402,F401
    known_assistant_kinds,
    probe_assistant_login,
)
from iabv_v15.infra.mcp.audit_tools.audit_capability import (  # noqa: E402,F401
    audit_capability,
    build_browser_capture_runner,
    build_llm_external_runner,
    build_llm_local_ollama_runner,
    build_ui_execution_runner,
    known_capability_ids,
    policy_for_capability,
)
from iabv_v15.infra.mcp.audit_tools.compare_perception_vs_ground_truth import (  # noqa: E402,F401
    compare_perception_vs_ground_truth,
)


# ----------------------------------------------------------------------
# Constantes públicas

MAX_READ_BYTES = 1 * 1024 * 1024  # 1 MiB — rechaza binarios grandes
MAX_LIST_ENTRIES = 200
DEFAULT_LIST_MAX = 200
DEFAULT_GIT_LOG_LIMIT = 10
MAX_GIT_LOG_LIMIT = 100
PYTEST_TIMEOUT_SECONDS = 15 * 60  # 15 min para la batería completa
GIT_TIMEOUT_SECONDS = 20.0

# Patrones sensibles. Se aplican con `fnmatch` sobre el `Path.name` y
# también sobre el path relativo completo, así `config/.env.local` queda
# bloqueado aunque viva en un subdirectorio.
SENSITIVE_GLOB_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.env",
    "credentials",
    "credentials.*",
    "credentials*.json",
    "*.key",
    "*.pem",
    "*.pfx",
    "*.p12",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "secrets.json",
    "secrets.*.json",
    "mcp_bridge.json",  # puede contener token de named tunnel
)

# Whitelist de suites/paths aceptables para `run_pytest`. Aceptamos:
# - None o vacío → batería completa (`tests/`);
# - un directorio debajo de `tests/` (ej. `tests/`, `tests/ui/`);
# - un archivo `tests/test_*.py`.
# Se rechaza cualquier otro valor para evitar ejecución arbitraria.
_SUITE_PATTERN = re.compile(
    r"^tests(?:/[A-Za-z0-9_.\-]+)*/?$"
)
_SUITE_TESTFILE_PATTERN = re.compile(
    r"^tests(?:/[A-Za-z0-9_\-]+)*?/test_[A-Za-z0-9_\-]+\.py$"
)
_KEYWORD_PATTERN = re.compile(r"^[A-Za-z0-9_\-:\[\]\. ]{1,200}$")


# ----------------------------------------------------------------------
# Excepciones específicas


class AuditToolError(Exception):
    """Error de validación o ejecución de una audit tool.

    Se convierte en payload `{error: ..., detail: ...}` a nivel MCP; no se
    propaga como excepción al cliente para no filtrar stacks.
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail

    def to_payload(self) -> dict[str, str]:
        return {"error": self.code, "detail": self.detail}


# ----------------------------------------------------------------------
# Workspace path resolution


def resolve_workspace_path(workspace_root: str | os.PathLike[str], relative_path: str) -> Path:
    """Resuelve `relative_path` dentro de `workspace_root`.

    Reglas:
    - `relative_path` no puede ser absoluto.
    - No puede contener `..` fuera del workspace.
    - Tras `resolve()`, tiene que estar dentro de `workspace_root`.

    Devuelve el `Path` canonicalizado. Lanza `AuditToolError` si falla.
    """

    if relative_path is None:
        raise AuditToolError("invalid_path", "relative_path no puede ser None")
    text = str(relative_path).strip()
    if not text:
        raise AuditToolError("invalid_path", "relative_path vacío")

    # Rechaza paths que empiezan con separador POSIX ("/foo") o Windows ("\\foo"),
    # incluso cuando `Path.is_absolute()` devuelve False. En Windows un path como
    # "/etc/passwd" no se considera absoluto por la API estándar (no tiene drive
    # letter), pero a efectos de seguridad sigue siendo un intento de escape del
    # workspace y debe tratarse como "absolute_path_forbidden" igual que en POSIX.
    if text.startswith(("/", "\\")):
        raise AuditToolError(
            "absolute_path_forbidden",
            f"relative_path debe ser relativo al workspace_root; recibido: {text!r}",
        )

    candidate = Path(text)
    if candidate.is_absolute():
        raise AuditToolError(
            "absolute_path_forbidden",
            f"relative_path debe ser relativo al workspace_root; recibido: {text!r}",
        )
    if any(part == ".." for part in candidate.parts):
        raise AuditToolError(
            "parent_traversal_forbidden",
            f"relative_path no puede contener '..'; recibido: {text!r}",
        )

    root = Path(workspace_root).resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AuditToolError(
            "outside_workspace",
            f"relative_path cae fuera de workspace_root ({root}): {text!r}",
        ) from exc
    return resolved


def is_sensitive_path(relative_path: str | os.PathLike[str]) -> bool:
    """Devuelve True si el path coincide con alguna entrada de la blacklist."""

    text = str(relative_path).replace(os.sep, "/")
    name = text.rsplit("/", 1)[-1]
    lowered_name = name.lower()
    lowered_text = text.lower()
    for pattern in SENSITIVE_GLOB_PATTERNS:
        pat = pattern.lower()
        if fnmatch.fnmatchcase(lowered_name, pat):
            return True
        if fnmatch.fnmatchcase(lowered_text, pat):
            return True
        # también comparamos contra cualquier componente del path
        for part in lowered_text.split("/"):
            if fnmatch.fnmatchcase(part, pat):
                return True
    return False


# ----------------------------------------------------------------------
# read_repo_file


def read_repo_file(
    workspace_root: str | os.PathLike[str],
    relative_path: str,
    *,
    max_bytes: int = MAX_READ_BYTES,
) -> dict[str, Any]:
    """Lee un archivo dentro del workspace como texto UTF-8.

    Devuelve `{path, size, content}` si es seguro; levanta `AuditToolError`
    en cualquier otra ruta.
    """

    resolved = resolve_workspace_path(workspace_root, relative_path)
    relative_norm = str(relative_path).replace(os.sep, "/")
    while relative_norm.startswith("./"):
        relative_norm = relative_norm[2:]
    if is_sensitive_path(relative_norm) or is_sensitive_path(resolved.name):
        raise AuditToolError(
            "sensitive_file_blocked",
            f"Lectura bloqueada por blacklist de secrets: {relative_path!r}",
        )
    if not resolved.exists():
        raise AuditToolError("not_found", f"Archivo no existe: {relative_path!r}")
    if resolved.is_dir():
        raise AuditToolError(
            "is_directory",
            f"{relative_path!r} es un directorio; usá list_repo_directory.",
        )
    size = resolved.stat().st_size
    if size > max_bytes:
        raise AuditToolError(
            "file_too_large",
            f"Archivo {relative_path!r} pesa {size} bytes; tope {max_bytes}.",
        )
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AuditToolError(
            "binary_not_supported",
            f"Archivo {relative_path!r} no es UTF-8 decodable ({exc.reason}).",
        ) from exc
    return {
        "path": relative_norm,
        "size": size,
        "content": content,
    }


# ----------------------------------------------------------------------
# list_repo_directory


def _entry_type(path: Path) -> str:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return "unknown"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def list_repo_directory(
    workspace_root: str | os.PathLike[str],
    relative_path: str = "",
    *,
    max_entries: int = DEFAULT_LIST_MAX,
) -> dict[str, Any]:
    """Lista entradas de un directorio dentro del workspace."""

    rel = relative_path.strip() if relative_path else ""
    if rel in ("", "."):
        resolved = Path(workspace_root).resolve()
    else:
        resolved = resolve_workspace_path(workspace_root, rel)
    if not resolved.exists():
        raise AuditToolError("not_found", f"Directorio no existe: {rel!r}")
    if not resolved.is_dir():
        raise AuditToolError("not_a_directory", f"{rel!r} no es un directorio.")

    cap = max(1, min(int(max_entries or DEFAULT_LIST_MAX), MAX_LIST_ENTRIES))
    entries: list[dict[str, Any]] = []
    names = sorted(os.listdir(resolved))
    truncated = False
    for name in names:
        if len(entries) >= cap:
            truncated = True
            break
        child = resolved / name
        sensitive = is_sensitive_path(name)
        try:
            st = child.lstat()
            size = int(st.st_size) if stat.S_ISREG(st.st_mode) else 0
            mtime = float(st.st_mtime)
        except OSError:
            size = 0
            mtime = 0.0
        entries.append(
            {
                "name": name,
                "type": _entry_type(child),
                "size": size,
                "mtime": mtime,
                "sensitive": bool(sensitive),
            }
        )

    root = Path(workspace_root).resolve()
    # Normalizar a forward slash para ser consistentes con read_repo_file
    # (en Windows `Path.relative_to` devuelve backslashes; el contrato MCP
    # expone siempre `/` y los clientes que comparan ambos tools no
    # deberían ver formatos distintos).
    path_field = (
        str(resolved.relative_to(root)).replace(os.sep, "/")
        if resolved != root
        else ""
    )
    return {
        "path": path_field,
        "entries": entries,
        "truncated": truncated,
        "total_listed": len(entries),
        "total_available": len(names),
    }


# ----------------------------------------------------------------------
# run_pytest


def validate_pytest_suite(suite: str | None) -> str:
    """Valida/normaliza el argumento `suite` para `run_pytest`.

    Devuelve la ruta que se pasará a pytest. `None` o vacío → `tests/`.
    """

    if suite is None:
        return "tests/"
    text = suite.strip()
    if not text:
        return "tests/"
    # rechazar absoluto, `..`, caracteres raros
    if text.startswith("/") or text.startswith("\\"):
        raise AuditToolError("invalid_suite", f"suite no puede ser absoluto: {suite!r}")
    if ".." in text.replace("\\", "/").split("/"):
        raise AuditToolError(
            "invalid_suite",
            f"suite no puede contener '..'; recibido: {suite!r}",
        )
    norm = text.replace("\\", "/")
    if not (_SUITE_PATTERN.match(norm) or _SUITE_TESTFILE_PATTERN.match(norm)):
        raise AuditToolError(
            "invalid_suite",
            (
                "suite debe ser 'tests/' o 'tests/subdir/...' o 'tests/test_*.py'; "
                f"recibido: {suite!r}"
            ),
        )
    return norm


def validate_pytest_keyword(keyword: str | None) -> str | None:
    if keyword is None:
        return None
    text = keyword.strip()
    if not text:
        return None
    if not _KEYWORD_PATTERN.match(text):
        raise AuditToolError(
            "invalid_keyword",
            f"keyword sólo puede contener [A-Za-z0-9_.:\\[\\]\\- ]; recibido: {keyword!r}",
        )
    return text


def validate_pytest_executable(python_executable: str | None) -> str | None:
    """Valida el path del intérprete Python antes de usarlo como comando.

    Defensa en profundidad: aunque el MCP tool público no acepta este
    parámetro (se resuelve server-side), cualquier caller interno que pase
    un valor debe cumplir:

    - ser un path existente;
    - no contener separador de pipe/shell (``;``, ``|``, ``&``, backticks, ``$(``);
    - apuntar a un ejecutable cuyo basename comience con ``python`` o
      ``pypy`` (o termine en ``python.exe``/``pypy.exe``).

    Devuelve el path canonicalizado (string absoluto) o ``None`` si el
    argumento es ``None``/vacío. Lanza ``AuditToolError`` con código
    ``invalid_python_executable`` si el valor no es aceptable.
    """

    if python_executable is None:
        return None
    text = str(python_executable).strip()
    if not text:
        return None
    # Rechazar cualquier char de shell metachar que no tiene sentido en un
    # path a un ejecutable — esto evita `python.exe; rm -rf /` o similares
    # si el caller olvidó shell=False.
    forbidden = (";", "|", "&", "`", "$(", "\n", "\r", "\"", "'", "*", "?", "<", ">")
    for token in forbidden:
        if token in text:
            raise AuditToolError(
                "invalid_python_executable",
                f"python_executable contiene un caracter prohibido {token!r}: {python_executable!r}",
            )
    candidate = Path(text)
    if not candidate.is_absolute():
        # no obligamos absoluto (sys.executable suele serlo) pero sí que se
        # resuelva a un path real en disco.
        candidate = Path(text).resolve()
    if not candidate.exists() or not candidate.is_file():
        raise AuditToolError(
            "invalid_python_executable",
            f"python_executable no apunta a un archivo existente: {python_executable!r}",
        )
    basename = candidate.name.lower()
    if basename.endswith(".exe"):
        stem = basename[: -len(".exe")]
    else:
        stem = basename
    if not (stem.startswith("python") or stem.startswith("pypy")):
        raise AuditToolError(
            "invalid_python_executable",
            (
                "python_executable debe apuntar a un binario cuyo nombre comience con "
                f"'python' o 'pypy' (recibido: {candidate.name!r})"
            ),
        )
    return str(candidate)


class SubprocessRunner(Protocol):
    def __call__(
        self,
        *,
        cmd: list[str],
        cwd: str,
        env: dict[str, str],
        timeout_s: float,
    ) -> "SubprocessResult":
        ...


@dataclass(frozen=True)
class SubprocessResult:
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False


def default_subprocess_runner(
    *,
    cmd: list[str],
    cwd: str,
    env: dict[str, str],
    timeout_s: float,
) -> SubprocessResult:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return SubprocessResult(
            returncode=-1,
            stdout=stdout,
            stderr=stderr,
            duration_s=duration,
            timed_out=True,
        )
    duration = time.monotonic() - start
    return SubprocessResult(
        returncode=int(completed.returncode),
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_s=duration,
        timed_out=False,
    )


_PYTEST_SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+)\s+passed)|(?:(?P<failed>\d+)\s+failed)|(?:(?P<errors>\d+)\s+error)",
)


def _parse_pytest_counts(output: str) -> tuple[int, int, int]:
    """Extrae `(passed, failed, errors)` de la línea resumen de pytest.

    Si no encuentra resumen devuelve ceros; los callers deben usar
    `returncode` como señal de "run válida" adicional.
    """

    passed = failed = errors = 0
    for line in output.splitlines()[::-1]:
        if "passed" in line or "failed" in line or "error" in line:
            for match in _PYTEST_SUMMARY_RE.finditer(line):
                if match.group("passed"):
                    passed = int(match.group("passed"))
                elif match.group("failed"):
                    failed = int(match.group("failed"))
                elif match.group("errors"):
                    errors = int(match.group("errors"))
            if passed or failed or errors:
                return passed, failed, errors
    return passed, failed, errors


def run_pytest(
    workspace_root: str | os.PathLike[str],
    *,
    suite: str | None = None,
    keyword: str | None = None,
    python_executable: str | None = None,
    extra_env: dict[str, str] | None = None,
    runner: SubprocessRunner | None = None,
    timeout_s: float = PYTEST_TIMEOUT_SECONDS,
    output_tail_chars: int = 4000,
    persist_evidence: bool = False,
    linked_pending_task: str = "",
    changed_files: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Ejecuta la batería oficial y resume resultados.

    Comando equivalente a:
        python -m pytest -p no:cacheprovider <suite> [-k <keyword>] -q

    Devuelve `{passed, failed, errors, returncode, duration_s, timed_out,
    suite, keyword, output_tail}`.

    P0.29: when ``persist_evidence=True``, writes a compact
    ``TestEvidence`` JSON to ``data/evolution/test_evidence/latest.json``
    (no logs, no PII) and updates ControlMaster ``current_tests_state``.
    """

    normalized_suite = validate_pytest_suite(suite)
    normalized_keyword = validate_pytest_keyword(keyword)
    normalized_executable = validate_pytest_executable(python_executable)

    root = Path(workspace_root).resolve()
    if not root.exists() or not root.is_dir():
        raise AuditToolError("workspace_missing", f"workspace_root no válido: {root}")

    # Si `python_executable` vino por argumento ya pasó la validación.
    # Si no, probamos la env var `IABV_PYTEST_PYTHON` con el mismo chequeo
    # estricto pero tragándonos el error para poder caer a `sys.executable`
    # (la env var es config del host, no input del MCP client, pero puede
    # estar mal escrita y no queremos que eso rompa la batería completa).
    python_exe = normalized_executable
    if python_exe is None:
        try:
            python_exe = validate_pytest_executable(os.environ.get("IABV_PYTEST_PYTHON"))
        except AuditToolError:
            python_exe = None
    if python_exe is None:
        python_exe = sys.executable
    cmd: list[str] = [
        python_exe,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        normalized_suite,
        "-q",
    ]
    if normalized_keyword:
        cmd.extend(["-k", normalized_keyword])

    env = dict(os.environ)
    # En el workspace oficial, `pythonpath=src` ya está en pytest.ini; dejamos
    # la copia del env pero permitimos override extra para Windows.
    if extra_env:
        env.update(extra_env)
    # Siempre apuntamos PYTHONPATH al src del workspace_root si no está.
    pythonpath = env.get("PYTHONPATH", "")
    src_path = str(root / "src")
    if src_path not in pythonpath.split(os.pathsep):
        env["PYTHONPATH"] = (
            src_path if not pythonpath else f"{src_path}{os.pathsep}{pythonpath}"
        )

    provenance_before = (
        _collect_test_git_provenance(root)
        if persist_evidence
        else None
    )
    run = runner or default_subprocess_runner
    result = run(cmd=cmd, cwd=str(root), env=env, timeout_s=float(timeout_s))
    provenance_after = (
        _collect_test_git_provenance(root)
        if persist_evidence
        else None
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    passed, failed, errors = _parse_pytest_counts(output)
    tail = output[-int(max(0, output_tail_chars)):] if output_tail_chars > 0 else ""
    payload = {
        "suite": normalized_suite,
        "keyword": normalized_keyword,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "returncode": int(result.returncode),
        "duration_s": float(result.duration_s),
        "timed_out": bool(result.timed_out),
        "output_tail": tail,
    }

    if persist_evidence:
        provenance = _reconcile_test_git_provenance(
            provenance_before or {},
            provenance_after or {},
        )
        payload["evidence_persistence"] = _persist_test_evidence(
            workspace_root=root,
            payload=payload,
            command=" ".join(cmd),
            linked_pending_task=linked_pending_task,
            changed_files=list(changed_files or []),
            provenance=provenance,
        )

    return payload


# -- P0.29 helpers ----------------------------------------------------------


_TEST_EVIDENCE_SUBDIR = "data/evolution/test_evidence"
_TEST_EVIDENCE_MAX_AGE_S = 86400.0  # 24 h
_TEST_EVIDENCE_FUTURE_SKEW_S = 60.0


def _collect_test_git_provenance(workspace_root: Path) -> dict[str, Any]:
    """Capture the exact repository revision and cleanliness for a test run.

    Generated TestEvidence and ControlMaster projections are excluded from
    the worktree check because this helper runs immediately before persisting
    those outputs. No remote URL, credentials, or environment secrets are read.
    """
    import hashlib as _hashlib
    import re as _re

    unknown = {
        "commit_sha": "",
        "branch": "",
        "worktree_clean": None,
        "provenance_status": "UNKNOWN",
        "worktree_status_sha256": "",
    }
    try:
        root = Path(workspace_root).resolve()
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if top.returncode != 0 or not top.stdout.strip():
            return unknown
        repo_root = Path(top.stdout.strip()).resolve()

        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if commit.returncode != 0:
            return unknown
        commit_sha = commit.stdout.strip().lower()
        if not _re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit_sha):
            return unknown

        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if branch_result.returncode != 0:
            return unknown
        branch_name = branch_result.stdout.strip() or "DETACHED"

        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if status_result.returncode != 0:
            return unknown

        relevant_status: list[str] = []
        for line in status_result.stdout.splitlines():
            if not line.strip():
                continue
            relative_path = line[3:].strip().replace("\\", "/").strip('"')
            normalized = f"/{relative_path.lstrip('/')}"
            if normalized.endswith("/data/evolution/test_evidence/latest.json"):
                continue
            if "/data/evolution/control_master/" in normalized:
                continue
            relevant_status.append(line)

        status_text = "\n".join(relevant_status)
        clean = not relevant_status
        return {
            "commit_sha": commit_sha,
            "branch": branch_name,
            "worktree_clean": clean,
            "provenance_status": "COMMIT_BOUND_CLEAN" if clean else "COMMIT_BOUND_DIRTY",
            "worktree_status_sha256": _hashlib.sha256(status_text.encode("utf-8")).hexdigest(),
        }
    except Exception:
        return unknown


def _test_evidence_payload_sha256(evidence: dict[str, Any]) -> str:
    """Hash the canonical evidence fields, excluding their own digest field."""
    import hashlib as _hashlib
    import json as _json

    payload = dict(evidence)
    payload.pop("payload_sha256", None)
    canonical = _json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return _hashlib.sha256(canonical).hexdigest()


def _test_evidence_has_stable_provenance_pair(
    metadata: Any,
    *,
    commit_sha: Any,
    branch: Any,
    worktree_status_sha256: Any,
) -> bool:
    """Require both clean pre/post snapshots to match the persisted identity."""
    import re as _re

    if not isinstance(metadata, dict):
        return False
    before = metadata.get("provenance_before")
    after = metadata.get("provenance_after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if (
        not isinstance(commit_sha, str)
        or not _re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", commit_sha)
        or not isinstance(branch, str)
        or not branch.strip()
        or not isinstance(worktree_status_sha256, str)
        or not _re.fullmatch(r"[0-9a-f]{64}", worktree_status_sha256)
    ):
        return False
    for snapshot in (before, after):
        snapshot_commit = snapshot.get("commit_sha")
        snapshot_branch = snapshot.get("branch")
        snapshot_digest = snapshot.get("worktree_status_sha256")
        if (
            snapshot.get("provenance_status") != "COMMIT_BOUND_CLEAN"
            or snapshot.get("worktree_clean") is not True
            or not isinstance(snapshot_commit, str)
            or not _re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", snapshot_commit)
            or snapshot_commit.lower() != commit_sha.lower()
            or not isinstance(snapshot_branch, str)
            or not snapshot_branch.strip()
            or snapshot_branch != branch
            or not isinstance(snapshot_digest, str)
            or not _re.fullmatch(r"[0-9a-f]{64}", snapshot_digest)
            or snapshot_digest != worktree_status_sha256
        ):
            return False
    return True


def _reconcile_test_git_provenance(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Bind evidence only when revision and cleanliness are stable across pytest."""
    identity_fields = ("commit_sha", "branch", "worktree_status_sha256")
    before_clean = (
        before.get("provenance_status") == "COMMIT_BOUND_CLEAN"
        and before.get("worktree_clean") is True
    )
    after_clean = (
        after.get("provenance_status") == "COMMIT_BOUND_CLEAN"
        and after.get("worktree_clean") is True
    )
    same_identity = all(
        bool(before.get(field))
        and before.get(field) == after.get(field)
        for field in identity_fields
    )
    if before_clean and after_clean and same_identity:
        status = "COMMIT_BOUND_CLEAN"
        clean: bool | None = True
    elif before.get("worktree_clean") is False or after.get("worktree_clean") is False:
        status = "COMMIT_BOUND_DIRTY"
        clean = False
    elif before_clean and after_clean and not same_identity:
        status = "SOURCE_CHANGED_DURING_TEST"
        clean = False
    else:
        status = "UNKNOWN"
        clean = None
    return {
        "commit_sha": str(before.get("commit_sha") or ""),
        "branch": str(before.get("branch") or ""),
        "worktree_clean": clean,
        "provenance_status": status,
        "worktree_status_sha256": str(before.get("worktree_status_sha256") or ""),
        "metadata": {
            "provenance_before": dict(before),
            "provenance_after": dict(after),
        },
    }


def _persist_test_evidence(
    *,
    workspace_root: Path,
    payload: dict[str, Any],
    command: str,
    linked_pending_task: str,
    changed_files: list[str],
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a commit-bound TestEvidence atomically and return its receipt."""
    import hashlib as _hashlib
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    from uuid import uuid4

    evidence_dir = workspace_root / _TEST_EVIDENCE_SUBDIR
    temporary: Path | None = None
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        git_provenance = dict(provenance or _collect_test_git_provenance(workspace_root))
        if (
            git_provenance.get("provenance_status") == "COMMIT_BOUND_CLEAN"
            and not _test_evidence_has_stable_provenance_pair(
                git_provenance.get("metadata"),
                commit_sha=git_provenance.get("commit_sha"),
                branch=git_provenance.get("branch"),
                worktree_status_sha256=git_provenance.get("worktree_status_sha256"),
            )
        ):
            git_provenance.update({
                "commit_sha": "",
                "branch": "",
                "worktree_clean": None,
                "provenance_status": "UNKNOWN",
                "worktree_status_sha256": "",
            })
        evidence = {
            "evidence_id": str(uuid4()),
            "command": command,
            "suite": str(payload.get("suite") or ""),
            "keyword": str(payload.get("keyword") or ""),
            "passed": int(payload.get("passed") or 0),
            "failed": int(payload.get("failed") or 0),
            "errors": int(payload.get("errors") or 0),
            "duration_s": float(payload.get("duration_s") or 0.0),
            "returncode": int(payload.get("returncode") or 0),
            "timed_out": bool(payload.get("timed_out")),
            "timestamp": _dt.now(_tz.utc).isoformat(),
            "linked_pending_task": linked_pending_task,
            "changed_files": changed_files[:20],
            "commit_sha": str(git_provenance.get("commit_sha") or ""),
            "branch": str(git_provenance.get("branch") or ""),
            "worktree_clean": git_provenance.get("worktree_clean"),
            "provenance_status": str(git_provenance.get("provenance_status") or "UNKNOWN"),
            "worktree_status_sha256": str(git_provenance.get("worktree_status_sha256") or ""),
            "metadata": dict(git_provenance.get("metadata") or {}),
        }
        evidence["payload_sha256"] = _test_evidence_payload_sha256(evidence)
        serialized = _json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        artifact_sha256 = _hashlib.sha256(serialized).hexdigest()
        latest = evidence_dir / "latest.json"
        temporary = evidence_dir / f".latest.{uuid4().hex}.tmp"
        with temporary.open("xb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, latest)
        temporary = None

        control_master_receipt = _sync_control_master_tests_state(
            workspace_root=workspace_root,
            evidence=evidence,
        )
        return {
            "status": "PERSISTED",
            "path": str(Path(_TEST_EVIDENCE_SUBDIR) / "latest.json").replace(os.sep, "/"),
            "artifact_sha256": artifact_sha256,
            "payload_sha256": evidence["payload_sha256"],
            "commit_sha": evidence["commit_sha"],
            "provenance_status": evidence["provenance_status"],
            "control_master_sync": control_master_receipt,
        }
    except Exception as exc:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "status": "WRITE_FAILED",
            "error_type": type(exc).__name__,
        }


def _sync_control_master_tests_state(
    *,
    workspace_root: Path,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Best-effort ControlMaster projection; the TestEvidence file is canonical."""
    try:
        from iabv_v15.domain.models import ControlMasterState, utc_now
        from iabv_v15.infra.persistence.control_master_repository import (
            ControlMasterRepository,
        )
        from iabv_v15.infra.persistence.storage import ArtifactStorage

        passed = int(evidence.get("passed") or 0)
        failed = int(evidence.get("failed") or 0)
        errors = int(evidence.get("errors") or 0)
        total = passed + failed + errors
        provenance_clean = (
            evidence.get("provenance_status") == "COMMIT_BOUND_CLEAN"
            and evidence.get("worktree_clean") is True
            and bool(evidence.get("commit_sha"))
        )
        run_failed = (
            failed > 0
            or errors > 0
            or int(evidence.get("returncode") or 0) != 0
            or bool(evidence.get("timed_out"))
        )
        health = "red" if run_failed else ("green" if provenance_clean else "unknown")
        tests_state = {
            "health": health,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total": total,
            "suite": str(evidence.get("suite") or ""),
            "timestamp": str(evidence.get("timestamp") or ""),
            "duration_s": float(evidence.get("duration_s") or 0.0),
            "returncode": int(evidence.get("returncode") or 0),
            "timed_out": bool(evidence.get("timed_out")),
            "linked_pending_task": str(evidence.get("linked_pending_task") or ""),
            "evidence_id": str(evidence.get("evidence_id") or ""),
            "commit_sha": str(evidence.get("commit_sha") or ""),
            "branch": str(evidence.get("branch") or ""),
            "worktree_clean": evidence.get("worktree_clean"),
            "provenance_status": str(evidence.get("provenance_status") or "UNKNOWN"),
            "payload_sha256": str(evidence.get("payload_sha256") or ""),
        }
        repository = ControlMasterRepository(
            ArtifactStorage(workspace_root / "data" / "evolution")
        )
        state = repository.load_latest_state() or ControlMasterState()
        evidence_links = list(dict.fromkeys([
            *list(state.evidence_links or []),
            "data/evolution/test_evidence/latest.json",
        ]))
        repository.save_state(
            state.model_copy(
                update={
                    "current_tests_state": tests_state,
                    "evidence_links": evidence_links,
                    "last_updated": utc_now(),
                }
            )
        )
        return {"status": "SYNCED"}
    except Exception as exc:
        return {"status": "SYNC_FAILED", "error_type": type(exc).__name__}


def load_latest_test_evidence(
    workspace_root: str | os.PathLike[str],
    *,
    max_age_s: float = _TEST_EVIDENCE_MAX_AGE_S,
) -> dict[str, Any] | None:
    """Load TestEvidence only when its digest, freshness and current Git state agree."""
    import json as _json
    import re as _re
    from datetime import datetime as _dt, timezone as _tz

    try:
        root = Path(workspace_root).resolve()
        latest = root / _TEST_EVIDENCE_SUBDIR / "latest.json"
        raw = latest.read_bytes()
        data = _json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return None

        timestamp = data.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            return None
        recorded_at = _dt.fromisoformat(timestamp)
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=_tz.utc)
        age = (_dt.now(_tz.utc) - recorded_at).total_seconds()
        if age < -_TEST_EVIDENCE_FUTURE_SKEW_S or age > float(max_age_s):
            return None

        commit_sha = data.get("commit_sha")
        branch_name = data.get("branch")
        if not isinstance(commit_sha, str) or not _re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", commit_sha):
            return None
        if not isinstance(branch_name, str) or not branch_name.strip():
            return None
        if data.get("worktree_clean") is not True:
            return None
        if data.get("provenance_status") != "COMMIT_BOUND_CLEAN":
            return None

        worktree_status_sha = data.get("worktree_status_sha256")
        if not isinstance(worktree_status_sha, str) or not _re.fullmatch(r"[0-9a-f]{64}", worktree_status_sha):
            return None
        if not _test_evidence_has_stable_provenance_pair(
            data.get("metadata"),
            commit_sha=commit_sha,
            branch=branch_name,
            worktree_status_sha256=worktree_status_sha,
        ):
            return None
        expected_payload_sha = data.get("payload_sha256")
        if not isinstance(expected_payload_sha, str) or not _re.fullmatch(r"[0-9a-f]{64}", expected_payload_sha):
            return None
        if _test_evidence_payload_sha256(data) != expected_payload_sha:
            return None
        for count_field in ("passed", "failed", "errors"):
            count_value = data.get(count_field)
            if not isinstance(count_value, int) or isinstance(count_value, bool) or count_value < 0:
                return None

        current = _collect_test_git_provenance(root)
        if (
            current.get("provenance_status") != "COMMIT_BOUND_CLEAN"
            or current.get("worktree_clean") is not True
            or str(current.get("commit_sha") or "").lower() != commit_sha.lower()
            or str(current.get("branch") or "") != branch_name
            or str(current.get("worktree_status_sha256") or "") != worktree_status_sha
        ):
            return None
        return data
    except Exception:
        return None


# ----------------------------------------------------------------------
# capture_ui_screenshot


class UIScreenshotProvider(Protocol):
    """Contrato mínimo para quien pueda devolver un screenshot PNG.

    El container puede exponer un provider (ej. en Windows con la ventana
    IABV mapeada). Si no hay provider, la tool degrada a `ui_not_running`.
    """

    def capture(self, region: str) -> bytes:
        ...


def capture_ui_screenshot(
    provider: UIScreenshotProvider | None,
    *,
    region: str = "control_center",
) -> dict[str, Any]:
    """Captura un screenshot de la ventana IABV.

    Devuelve `{region, format, bytes_base64, size_bytes}` si el provider
    responde con bytes PNG; `{error: 'ui_not_running', ...}` si el provider
    no está disponible o falla.
    """

    if provider is None:
        return {
            "error": "ui_not_running",
            "detail": (
                "No hay UIScreenshotProvider registrado en el container; "
                "probablemente la UI IABV no está corriendo o el host es headless."
            ),
            "region": region,
        }
    try:
        raw = provider.capture(region)
    except Exception as exc:  # pragma: no cover - defensa
        return {
            "error": "ui_not_running",
            "detail": f"Provider levantó excepción: {exc!r}",
            "region": region,
        }
    if not isinstance(raw, (bytes, bytearray, memoryview)) or not raw:
        return {
            "error": "ui_not_running",
            "detail": "Provider devolvió vacío o no-bytes.",
            "region": region,
        }
    data = bytes(raw)
    return {
        "region": region,
        "format": "png",
        "size_bytes": len(data),
        "bytes_base64": base64.b64encode(data).decode("ascii"),
    }


# ----------------------------------------------------------------------
# git_status_and_log


@dataclass(frozen=True)
class GitCommit:
    sha: str
    short_sha: str
    author: str
    date_iso: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author": self.author,
            "date_iso": self.date_iso,
            "message": self.message,
        }


def _parse_porcelain(text: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for raw in text.splitlines():
        if len(raw) < 3:
            continue
        status = raw[:2]
        path = raw[3:]
        files.append({"status": status.strip() or status, "path": path})
    return files


def _parse_branch_ab(text: str) -> tuple[str, int, int]:
    """Parsea la línea `## branch...origin/branch [ahead N, behind M]`."""

    branch = ""
    ahead = behind = 0
    for line in text.splitlines():
        if not line.startswith("##"):
            continue
        payload = line[2:].strip()
        if "..." in payload:
            branch = payload.split("...", 1)[0].strip()
            rest = payload.split("...", 1)[1]
        else:
            branch = payload.split(" ", 1)[0].strip()
            rest = payload[len(branch):]
        m_ahead = re.search(r"ahead\s+(\d+)", rest)
        m_behind = re.search(r"behind\s+(\d+)", rest)
        if m_ahead:
            ahead = int(m_ahead.group(1))
        if m_behind:
            behind = int(m_behind.group(1))
        break
    return branch, ahead, behind


_LOG_FIELD_SEP = "\x1f"
_LOG_RECORD_SEP = "\x1e"


def _parse_git_log(text: str) -> list[GitCommit]:
    commits: list[GitCommit] = []
    for record in text.split(_LOG_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(_LOG_FIELD_SEP)
        if len(parts) < 5:
            continue
        sha, short_sha, author, date_iso, message = parts[:5]
        commits.append(
            GitCommit(
                sha=sha,
                short_sha=short_sha,
                author=author,
                date_iso=date_iso,
                message=message,
            )
        )
    return commits


def git_status_and_log(
    workspace_root: str | os.PathLike[str],
    *,
    limit: int = DEFAULT_GIT_LOG_LIMIT,
    runner: SubprocessRunner | None = None,
    git_executable: str = "git",
    timeout_s: float = GIT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Lee estado y últimos N commits del repo `workspace_root`.

    Es read-only: sólo ejecuta `git status --porcelain -b` y
    `git log --pretty=...`. Si el workspace no es un repo, devuelve
    `{error: 'not_a_git_repo', ...}` sin tirar.
    """

    root = Path(workspace_root).resolve()
    if not root.exists() or not root.is_dir():
        raise AuditToolError("workspace_missing", f"workspace_root no válido: {root}")
    capped_limit = max(1, min(int(limit or DEFAULT_GIT_LOG_LIMIT), MAX_GIT_LOG_LIMIT))
    run = runner or default_subprocess_runner
    env = dict(os.environ)

    # `git rev-parse` para confirmar que estamos en un repo
    probe = run(
        cmd=[git_executable, "rev-parse", "--is-inside-work-tree"],
        cwd=str(root),
        env=env,
        timeout_s=float(timeout_s),
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return {
            "error": "not_a_git_repo",
            "detail": probe.stderr.strip() or probe.stdout.strip() or "rev-parse falló",
        }

    status_result = run(
        cmd=[git_executable, "status", "--porcelain=1", "--branch"],
        cwd=str(root),
        env=env,
        timeout_s=float(timeout_s),
    )
    if status_result.returncode != 0:
        return {
            "error": "git_status_failed",
            "detail": status_result.stderr.strip() or status_result.stdout.strip(),
        }
    branch, ahead, behind = _parse_branch_ab(status_result.stdout)
    # archivos dirty: todas las líneas menos la primera ##
    body_lines = [
        line for line in status_result.stdout.splitlines() if not line.startswith("##")
    ]
    dirty_files = _parse_porcelain("\n".join(body_lines))

    log_format = _LOG_FIELD_SEP.join(["%H", "%h", "%an <%ae>", "%aI", "%s"]) + _LOG_RECORD_SEP
    log_result = run(
        cmd=[
            git_executable,
            "log",
            f"-n{capped_limit}",
            f"--pretty=format:{log_format}",
        ],
        cwd=str(root),
        env=env,
        timeout_s=float(timeout_s),
    )
    if log_result.returncode != 0:
        return {
            "error": "git_log_failed",
            "detail": log_result.stderr.strip() or log_result.stdout.strip(),
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "dirty_files": dirty_files,
        }
    commits = [c.to_dict() for c in _parse_git_log(log_result.stdout)]
    return {
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "dirty_files": dirty_files,
        "dirty_count": len(dirty_files),
        "last_commits": commits,
    }


__all__ = [
    "AuditToolError",
    "DEFAULT_GIT_LOG_LIMIT",
    "DEFAULT_LIST_MAX",
    "GitCommit",
    "MAX_GIT_LOG_LIMIT",
    "MAX_LIST_ENTRIES",
    "MAX_READ_BYTES",
    "PYTEST_TIMEOUT_SECONDS",
    "SENSITIVE_GLOB_PATTERNS",
    "SubprocessResult",
    "SubprocessRunner",
    "UIScreenshotProvider",
    "audit_capability",
    "build_browser_capture_runner",
    "build_llm_external_runner",
    "build_llm_local_ollama_runner",
    "build_ui_execution_runner",
    "capture_ui_screenshot",
    "compare_perception_vs_ground_truth",
    "default_subprocess_runner",
    "git_status_and_log",
    "is_sensitive_path",
    "known_assistant_kinds",
    "known_capability_ids",
    "list_repo_directory",
    "policy_for_capability",
    "probe_assistant_login",
    "read_repo_file",
    "resolve_workspace_path",
    "run_pytest",
    "validate_pytest_executable",
    "validate_pytest_keyword",
    "validate_pytest_suite",
]
