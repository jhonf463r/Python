"""MCP tools for self-updating IABV.

Registers write_repo_file, apply_text_patch, and self_update_and_test
on the FastMCP instance passed via ``register(mcp, workspace_root)``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register(mcp: Any, workspace_root: str | Path) -> None:
    """Register self-update tools on the MCP server instance."""
    from iabv_v15.services.evolution.self_update_service import SelfUpdateService

    svc = SelfUpdateService(workspace_root)
    logger.info('self_update_tools: registering write tools on MCP (workspace=%s)', workspace_root)

    @mcp.tool()
    def write_repo_file(relative_path: str, content: str, create_backup: bool = True) -> str:
        """Escribe o crea un archivo en el workspace.

        Args:
            relative_path: Ruta relativa desde el workspace root.
            content: Contenido completo del archivo.
            create_backup: Si True (default), crea backup del archivo original.

        Returns:
            JSON con resultado: {success, path, bytes_written, was_new, backup_created}
        """
        result = svc.write_file(relative_path, content, create_backup=create_backup)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def apply_text_patch(relative_path: str, old_text: str, new_text: str) -> str:
        """Reemplaza un fragmento de texto en un archivo existente.

        El old_text debe existir exactamente una vez en el archivo.
        Se crea backup automatico antes de aplicar.

        Args:
            relative_path: Ruta relativa del archivo a parchear.
            old_text: Texto exacto a reemplazar (debe ser unico).
            new_text: Texto de reemplazo.

        Returns:
            JSON con resultado: {success, path, chars_removed, chars_added}
        """
        result = svc.apply_text_patch(relative_path, old_text, new_text)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def self_update_and_test(patches_json: str, test_suite: str = 'tests/') -> str:
        """Aplica multiples parches y ejecuta pytest. Rollback automatico si falla.

        Cada patch en la lista:
        - action='write': {action, path, content}
        - action='patch': {action, path, old_text, new_text}

        El sistema:
        1. Crea backups de todos los archivos afectados
        2. Aplica todos los parches secuencialmente
        3. Ejecuta pytest en el test_suite indicado
        4. Si los tests pasan: mantiene los cambios
        5. Si los tests fallan: revierte TODOS los cambios automaticamente

        Args:
            patches_json: JSON string con lista de patches.
            test_suite: Ruta del test suite (default: 'tests/').

        Returns:
            JSON con resultado completo incluyendo test output.
        """
        patches = json.loads(patches_json)
        result = svc.self_update_and_test(patches, test_suite=test_suite)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def git_commit_and_push(
        message: str,
        files: str = '',
        branch: str = '',
        remote: str = 'origin',
    ) -> str:
        """Commitea y pushea cambios del programa autonomamente.

        El programa usa esta herramienta para versionarse a si mismo
        sin requerir intervencion humana. Solo opera en ramas
        iabv-auto/* o devin/* por seguridad.

        Args:
            message: Mensaje del commit.
            files: Lista de archivos separados por coma (si vacio, usa git add -A del subdirectorio IABV_v1.5).
            branch: Rama a pushear (si vacio, usa la rama actual).
            remote: Remote (default: origin).

        Returns:
            JSON con resultado: {success, committed, pushed, branch, commit_hash, error}
        """
        import subprocess
        ws = Path(workspace_root)

        try:
            # Detect branch
            if not branch:
                r = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True, text=True, cwd=ws,
                )
                branch = r.stdout.strip() or 'unknown'

            # Safety: only allow iabv-auto/* or devin/* branches
            if not (branch.startswith('iabv-auto/') or branch.startswith('devin/')):
                return json.dumps({
                    'success': False,
                    'error': f'Rama {branch} no permitida para commit autonomo. Solo iabv-auto/* o devin/*.',
                })

            # Git add
            if files:
                file_list = [f.strip() for f in files.split(',') if f.strip()]
                for f in file_list:
                    subprocess.run(['git', 'add', f], cwd=ws, capture_output=True)
            else:
                # Only add tracked/modified files in IABV_v1.5 subtree
                subprocess.run(
                    ['git', 'add', '-u', '.'],
                    cwd=ws, capture_output=True,
                )

            # Check if there's anything to commit
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=ws,
            )
            if not status.stdout.strip():
                return json.dumps({
                    'success': True,
                    'committed': False,
                    'pushed': False,
                    'branch': branch,
                    'commit_hash': None,
                    'note': 'No hay cambios pendientes para commitear.',
                })

            # Git commit
            commit_result = subprocess.run(
                ['git', 'commit', '-m', message],
                capture_output=True, text=True, cwd=ws,
            )
            if commit_result.returncode != 0:
                return json.dumps({
                    'success': False,
                    'committed': False,
                    'error': f'git commit fallo: {commit_result.stderr[:300]}',
                })

            # Get commit hash
            hash_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, cwd=ws,
            )
            commit_hash = hash_result.stdout.strip()

            # Git push
            push_result = subprocess.run(
                ['git', 'push', remote, branch],
                capture_output=True, text=True, cwd=ws,
                timeout=120,
            )
            pushed = push_result.returncode == 0

            return json.dumps({
                'success': True,
                'committed': True,
                'pushed': pushed,
                'branch': branch,
                'commit_hash': commit_hash,
                'push_output': push_result.stdout[:200] + push_result.stderr[:200] if not pushed else 'ok',
            })

        except Exception as exc:
            return json.dumps({
                'success': False,
                'error': str(exc)[:500],
            })

    logger.info('self_update_tools: 4 tools registered (write_repo_file, apply_text_patch, self_update_and_test, git_commit_and_push)')
