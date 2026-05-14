"""MCP tools for autonomous self-modification.

Registers write-capable tools that allow the program to:
- Write/create files in its own workspace
- Apply text patches to existing files
- Commit and push changes to GitHub

This module makes the program 100% autonomous: it can detect issues
(via gpu_metacognition_check, self_examination, etc.) AND fix them
(via write_repo_file, apply_text_patch, git_commit_and_push).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register_self_update_tools(mcp: Any, workspace_root_fn: Any, governance_fn: Any, to_jsonable_fn: Any) -> int:
    """Register write-capable tools on the MCP server.

    Args:
        mcp: The MCP FastMCP instance.
        workspace_root_fn: Callable that returns the workspace root Path.
        governance_fn: Callable for governance gate checks.
        to_jsonable_fn: Callable to convert results to JSON-safe dicts.

    Returns:
        Number of tools registered.
    """
    count = 0

    def _safe_path(relative_path: str) -> Path | None:
        """Resolve and validate a relative path within the workspace."""
        ws = Path(workspace_root_fn())
        resolved = (ws / relative_path).resolve()
        if not resolved.is_relative_to(ws.resolve()):
            return None  # directory traversal attempt
        return resolved

    safe_git_prefixes = ('src/', 'tests/', 'scripts/', '.github/', 'docs/', 'assets/')
    safe_git_files = {
        'AGENTS.md',
        'README.md',
        'pyproject.toml',
        'pytest.ini',
        'requirements.txt',
        'requirements-dev.txt',
        '.gitignore',
    }
    broad_git_pathspecs = {'.', './', '*', 'all', '-A', '--all'}

    def _normalize_git_path(path: str) -> str:
        return str(path or '').strip().replace('\\', '/').lstrip('./')

    def _is_broad_git_pathspec(path: str) -> bool:
        raw = str(path or '').strip().replace('\\', '/')
        return raw in broad_git_pathspecs or _normalize_git_path(path) in broad_git_pathspecs

    def _is_safe_git_add_path(path: str) -> bool:
        normalized = _normalize_git_path(path)
        if not normalized or normalized.startswith('-'):
            return False
        if normalized in safe_git_files:
            return True
        return any(normalized == prefix.rstrip('/') or normalized.startswith(prefix) for prefix in safe_git_prefixes)

    def _changed_safe_git_files(ws: Path) -> list[str]:
        """Return changed source/doc files only; never stage data/cache/profile payloads."""
        pathspecs = [
            'src',
            'tests',
            'scripts',
            '.github',
            'docs',
            'assets',
            'AGENTS.md',
            'README.md',
            'pyproject.toml',
            'pytest.ini',
            'requirements.txt',
            'requirements-dev.txt',
            '.gitignore',
        ]
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=all', '--', *pathspecs],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ws),
        )
        if result.returncode != 0:
            return []
        files: list[str] = []
        for raw_line in result.stdout.splitlines():
            if len(raw_line) < 4:
                continue
            path = raw_line[3:].strip()
            if ' -> ' in path:
                path = path.rsplit(' -> ', 1)[-1].strip()
            normalized = _normalize_git_path(path)
            if normalized and _is_safe_git_add_path(normalized):
                files.append(normalized)
        return sorted(set(files))

    def _resolve_git_add_files(files: str, ws: Path) -> tuple[list[str], str]:
        raw_items = [item.strip() for item in str(files or '').split(',') if item.strip()]
        if not raw_items or any(_is_broad_git_pathspec(item) for item in raw_items):
            resolved = _changed_safe_git_files(ws)
            return resolved, 'safe_source_auto_scope'
        normalized = [_normalize_git_path(item) for item in raw_items]
        unsafe = [item for item in normalized if not _is_safe_git_add_path(item)]
        if unsafe:
            return [], f"unsafe_git_add_path:{','.join(unsafe[:5])}"
        return normalized, 'explicit_safe_files'

    # -----------------------------------------------------------------
    # write_repo_file
    # -----------------------------------------------------------------
    @mcp.tool()
    def write_repo_file(
        relative_path: str,
        content: str,
        create_dirs: bool = True,
    ) -> dict[str, Any]:
        """Escribe (crea o sobreescribe) un archivo en el workspace.

        Metacognicion: el programa puede crear o modificar sus propios
        archivos de codigo para auto-mejorarse.

        Args:
            relative_path: ruta relativa desde el workspace root.
            content: contenido completo del archivo.
            create_dirs: crear directorios intermedios si no existen.

        Returns:
            dict con status, path, bytes_written.
        """
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

        target = _safe_path(relative_path)
        if target is None:
            return {"status": "error", "detail": "path escapes workspace (directory traversal)"}

        # Reject sensitive paths (normalize to forward slashes for Windows compat)
        sensitive = ['.git/config', '.git/hooks', '.env', 'secrets']
        target_str = str(target).replace('\\', '/')
        for s in sensitive:
            if s in target_str:
                return {"status": "error", "detail": f"cannot write to sensitive path containing '{s}'"}

        try:
            if create_dirs:
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info("write_repo_file: wrote %d bytes to %s", len(content), relative_path)
            return {
                "status": "ok",
                "path": relative_path,
                "bytes_written": len(content),
            }
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    count += 1

    # -----------------------------------------------------------------
    # apply_text_patch
    # -----------------------------------------------------------------
    @mcp.tool()
    def apply_text_patch(
        relative_path: str,
        old_text: str,
        new_text: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Aplica un parche de texto (buscar y reemplazar) a un archivo.

        Metacognicion: el programa puede corregir bugs en su propio codigo
        de forma precisa sin reescribir archivos completos.

        Args:
            relative_path: ruta relativa al archivo.
            old_text: texto exacto a buscar.
            new_text: texto de reemplazo.
            description: descripcion del cambio (para logging).

        Returns:
            dict con status, replacements_made.
        """
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

        target = _safe_path(relative_path)
        if target is None:
            return {"status": "error", "detail": "path escapes workspace"}
        if not target.is_file():
            return {"status": "error", "detail": f"file not found: {relative_path}"}

        try:
            current = target.read_text(encoding="utf-8")
            occurrences = current.count(old_text)
            if occurrences == 0:
                return {"status": "error", "detail": "old_text not found in file", "file_size": len(current)}

            patched = current.replace(old_text, new_text, 1)
            target.write_text(patched, encoding="utf-8")
            logger.info("apply_text_patch: %s — %s (%d occurrence(s))",
                        relative_path, description or "patch applied", occurrences)
            return {
                "status": "ok",
                "path": relative_path,
                "replacements_made": 1,
                "total_occurrences": occurrences,
                "description": description,
            }
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    count += 1

    # -----------------------------------------------------------------
    # git_commit_and_push
    # -----------------------------------------------------------------
    @mcp.tool()
    def git_commit_and_push(
        message: str,
        files: str = ".",
        push: bool = True,
    ) -> dict[str, Any]:
        """Hace git add + commit + push de los cambios del programa.

        Metacognicion: el programa puede persistir sus auto-mejoras
        en el repositorio remoto sin intervencion humana.

        Args:
            message: mensaje de commit.
            files: archivos a agregar (default: todos los modificados).
            push: si hacer push al remoto (default: True).

        Returns:
            dict con status, commit_hash, branch, push_output.
        """
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=push,
        )
        if block is not None:
            return block

        # Validate commit message
        if not message or len(message) < 5:
            return {"status": "error", "detail": "commit message too short (min 5 chars)"}
        if len(message) > 500:
            return {"status": "error", "detail": "commit message too long (max 500 chars)"}

        ws = Path(workspace_root_fn())
        try:
            # git add
            file_list, scope = _resolve_git_add_files(files, ws)
            if scope.startswith('unsafe_git_add_path'):
                return {
                    "status": "error",
                    "detail": f"{scope}; self-update solo puede preparar codigo/docs seguros, no data/cache/perfiles.",
                }
            if not file_list:
                return {
                    "status": "ok",
                    "detail": "nothing safe to commit",
                    "commit_hash": None,
                    "git_add_scope": scope,
                }
            add_cmd = ["git", "add", "--"] + file_list
            add_result = subprocess.run(
                add_cmd, capture_output=True, text=True,
                timeout=30, cwd=str(ws),
            )
            if add_result.returncode != 0:
                return {"status": "error", "detail": f"git add failed: {add_result.stderr.strip()}"}

            # git commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True, text=True,
                timeout=30, cwd=str(ws),
            )
            if commit_result.returncode != 0:
                stderr = commit_result.stderr.strip()
                if "nothing to commit" in commit_result.stdout.lower() or "nothing to commit" in stderr.lower():
                    return {"status": "ok", "detail": "nothing to commit", "commit_hash": None}
                return {"status": "error", "detail": f"git commit failed: {stderr}"}

            # Extract commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True,
                timeout=10, cwd=str(ws),
            )
            commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else None

            # Get branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True,
                timeout=10, cwd=str(ws),
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

            push_output = None
            if push:
                push_result = subprocess.run(
                    ["git", "push"],
                    capture_output=True, text=True,
                    timeout=60, cwd=str(ws),
                )
                push_output = push_result.stdout.strip() or push_result.stderr.strip()
                if push_result.returncode != 0:
                    return {
                        "status": "partial",
                        "detail": "committed but push failed",
                        "commit_hash": commit_hash,
                        "branch": branch,
                        "push_error": push_output,
                    }

            logger.info("git_commit_and_push: %s on %s — %s", commit_hash, branch, message)
            return {
                "status": "ok",
                "commit_hash": commit_hash,
                "branch": branch,
                "push_output": push_output,
                "message": message,
                "git_add_scope": scope,
                "files": file_list,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "detail": "git operation timed out"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    count += 1

    logger.info("self_update_tools: %d tools registered", count)
    return count
