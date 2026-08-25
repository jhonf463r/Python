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

# C-2: Import canonical authority components
try:
    from iabv_v15.services.trust.capability_action_bridge import CapabilityActionBridge, ActionRequest
except ImportError:
    CapabilityActionBridge = None
    ActionRequest = None


# ============================================================================
# Core self-update functions (extracted for testing)
# ============================================================================

def _safe_path(workspace_root: Path, relative_path: str) -> Path | None:
    """Resolve and validate a relative path within the workspace."""
    resolved = (workspace_root / relative_path).resolve()
    if not resolved.is_relative_to(workspace_root.resolve()):
        return None  # directory traversal attempt
    return resolved


def write_repo_file_impl(
    workspace_root: Path,
    relative_path: str,
    content: str,
    create_dirs: bool = True,
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
) -> dict[str, Any]:
    """Core implementation of write_repo_file (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for file write"}
    
    if ActionRequest is None:
        # ActionRequest not available - fail closed
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    action_request = ActionRequest(
        lease_id='test_lease',  # Placeholder for testing
        execution_id=f'write_{relative_path}',
        action='WRITE_REPOSITORY_FILE',
        target=f'file:{relative_path}',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for file write"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

    target = _safe_path(workspace_root, relative_path)
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


def apply_text_patch_impl(
    workspace_root: Path,
    relative_path: str,
    old_text: str,
    new_text: str,
    description: str = "",
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
) -> dict[str, Any]:
    """Core implementation of apply_text_patch (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for patch application"}
    
    if ActionRequest is None:
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    action_request = ActionRequest(
        lease_id='test_lease',  # Placeholder for testing
        execution_id=f'patch_{relative_path}',
        action='APPLY_PATCH',
        target=f'file:{relative_path}',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for patch application"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=False,
        )
        if block is not None:
            return block

    target = _safe_path(workspace_root, relative_path)
    if target is None:
        return {"status": "error", "detail": "path escapes workspace (directory traversal)"}

    # Reject sensitive paths
    sensitive = ['.git/config', '.git/hooks', '.env', 'secrets']
    target_str = str(target).replace('\\', '/')
    for s in sensitive:
        if s in target_str:
            return {"status": "error", "detail": f"cannot patch sensitive path containing '{s}'"}

    if not target.exists():
        return {"status": "error", "detail": "file does not exist"}

    try:
        current_content = target.read_text(encoding="utf-8")
        if old_text not in current_content:
            return {"status": "error", "detail": "old_text not found in file"}

        patched_content = current_content.replace(old_text, new_text)
        replacements = current_content.count(old_text)
        target.write_text(patched_content, encoding="utf-8")
        logger.info("apply_text_patch: %d replacements in %s", replacements, relative_path)
        return {
            "status": "ok",
            "path": relative_path,
            "replacements_made": replacements,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def git_commit_and_push_impl(
    workspace_root: Path,
    message: str,
    push: bool = False,
    governance_fn: Any = None,
    capability_action_bridge: Any = None,
) -> dict[str, Any]:
    """Core implementation of git_commit_and_push (extracted for testing)."""
    # C-2: Canonical authority check - REJECT if authority unavailable
    if not capability_action_bridge:
        return {"status": "error", "detail": "Authorization denied: capability_action_bridge required for git commit"}
    
    if ActionRequest is None:
        return {"status": "error", "detail": "Authorization denied: ActionRequest class not available"}
    
    # C-2: Canonical authority check for commit
    action_request = ActionRequest(
        lease_id='test_lease',  # Placeholder for testing
        execution_id=f'commit_{message[:20]}',
        action='GIT_COMMIT',
        target='git:workspace',
        action_context={'requested_scope': 'self_update'},
    )
    auth_result = capability_action_bridge.authorize_action(action_request)
    if not auth_result.get('authorized'):
        return {"status": "error", "detail": "Authorization denied: capability required for git commit"}
    
    # C-2: Canonical authority check for push
    if push:
        action_request = ActionRequest(
            lease_id='test_lease',  # Placeholder for testing
            execution_id=f'push_{message[:20]}',
            action='GIT_PUSH',
            target='git:workspace',
            action_context={'requested_scope': 'self_update'},
        )
        auth_result = capability_action_bridge.authorize_action(action_request)
        if not auth_result.get('authorized'):
            return {"status": "error", "detail": "Authorization denied: capability required for git push"}
    
    if governance_fn:
        block = governance_fn(
            assistant_kind="self_update",
            requires_network=True if push else False,
        )
        if block is not None:
            return block

    if len(message) < 5:
        return {"status": "error", "detail": "commit message too short (min 5 chars)"}

    try:
        # Add all changes
        add_result = subprocess.run(
            ['git', 'add', '-A'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if add_result.returncode != 0:
            return {"status": "error", "detail": f"git add failed: {add_result.stderr}"}

        # Commit
        commit_result = subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if commit_result.returncode != 0:
            if "nothing to commit" in commit_result.stderr or "nothing added to commit" in commit_result.stdout:
                return {"status": "ok", "detail": "nothing to commit"}
            return {"status": "error", "detail": f"git commit failed: {commit_result.stderr}"}

        # Get commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = hash_result.stdout.strip()

        # Get branch name
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=True,
        )
        branch_name = branch_result.stdout.strip()

        result = {
            "status": "ok",
            "commit_hash": commit_hash,
            "branch": branch_name,
            "message": message,
        }

        # Push if requested
        if push:
            push_result = subprocess.run(
                ['git', 'push'],
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if push_result.returncode != 0:
                return {"status": "error", "detail": f"git push failed: {push_result.stderr}"}
            result["pushed"] = True

        logger.info("git_commit_and_push: %s on %s", commit_hash[:8], branch_name)
        return result

    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ============================================================================
# MCP Registration
# ============================================================================

def register_self_update_tools(mcp: Any, workspace_root_fn: Any, governance_fn: Any, to_jsonable_fn: Any, capability_action_bridge: Any = None) -> int:
    """Register write-capable tools on the MCP server.

    Args:
        mcp: The MCP FastMCP instance.
        workspace_root_fn: Callable that returns the workspace root Path.
        governance_fn: Callable for governance gate checks.
        to_jsonable_fn: Callable to convert results to JSON-safe dicts.
        capability_action_bridge: Canonical P0.213 authority bridge (C-2 integration).

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
        # C-2: Canonical authority check
        if capability_action_bridge and ActionRequest:
            action_request = ActionRequest(
                action='WRITE_REPOSITORY_FILE',
                target=f'file:{relative_path}',
                requested_scope='self_update',
                invocation_id=f'write_{relative_path}',
            )
            auth_result = capability_action_bridge.authorize_action(action_request)
            if not auth_result.get('authorized'):
                return {"status": "error", "detail": "Authorization denied: capability required for file write"}
        
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
        # C-2: Canonical authority check
        if capability_action_bridge and ActionRequest:
            action_request = ActionRequest(
                action='APPLY_PATCH',
                target=f'file:{relative_path}',
                requested_scope='self_update',
                invocation_id=f'patch_{relative_path}',
            )
            auth_result = capability_action_bridge.authorize_action(action_request)
            if not auth_result.get('authorized'):
                return {"status": "error", "detail": "Authorization denied: capability required for patch application"}
        
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
        # C-2: Canonical authority check for commit
        if capability_action_bridge and ActionRequest:
            action_request = ActionRequest(
                action='GIT_COMMIT',
                target='git:workspace',
                requested_scope='self_update',
                invocation_id=f'commit_{message[:20]}',
            )
            auth_result = capability_action_bridge.authorize_action(action_request)
            if not auth_result.get('authorized'):
                return {"status": "error", "detail": "Authorization denied: capability required for git commit"}
        
        # C-2: Canonical authority check for push
        if push and capability_action_bridge and ActionRequest:
            action_request = ActionRequest(
                action='GIT_PUSH',
                target='git:workspace',
                requested_scope='self_update',
                invocation_id=f'push_{message[:20]}',
            )
            auth_result = capability_action_bridge.authorize_action(action_request)
            if not auth_result.get('authorized'):
                return {"status": "error", "detail": "Authorization denied: capability required for git push"}
        
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
