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
        ws = workspace_root_fn()
        resolved = (ws / relative_path).resolve()
        if not str(resolved).startswith(str(ws.resolve())):
            return None  # directory traversal attempt
        return resolved

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

        # Reject sensitive paths
        sensitive = ['.git/config', '.git/hooks', '.env', 'secrets']
        for s in sensitive:
            if s in str(target):
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

        ws = workspace_root_fn()
        try:
            # git add
            file_list = [f.strip() for f in files.split(",") if f.strip()]
            add_cmd = ["git", "add"] + file_list
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
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "detail": "git operation timed out"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    count += 1

    logger.info("self_update_tools: %d tools registered", count)
    return count
