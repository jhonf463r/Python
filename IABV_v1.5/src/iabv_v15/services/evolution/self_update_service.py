"""SelfUpdateService — auto-aplicacion de parches y verificacion autonoma.

Permite al sistema:
1. Recibir parches de codigo (text replacement)
2. Escribir archivos nuevos
3. Ejecutar pytest para verificar que los cambios no rompen nada
4. Hacer rollback automatico si los tests fallan
5. Registrar resultados en SystemBacklogService

Contrato:
- NO es otro cerebro. Solo aplica cambios de texto y verifica con pytest.
- NO toca capas P1-P4 directamente (protegidas por validacion).
- Backups automaticos antes de cada cambio.
- Los cambios a archivos criticos (bootstrap, OSES, governance) requieren
  que los tests pasen o se revierten.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROTECTED_PATTERNS = [
    'autonomy_governance_policy.py',
    'models.py',
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfUpdateService:
    """Servicio de auto-actualizacion con rollback automatico."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)
        self.backup_dir = self.workspace_root / 'data' / 'evolution' / 'self_update' / 'backups'
        self.log_path = self.workspace_root / 'data' / 'evolution' / 'self_update' / 'update_log.jsonl'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Escritura de archivos
    # ------------------------------------------------------------------

    def write_file(
        self,
        relative_path: str,
        content: str,
        *,
        create_backup: bool = True,
    ) -> dict[str, Any]:
        """Escribe un archivo. Crea backup si ya existe."""
        rel = Path(relative_path)
        full = self.workspace_root / rel
        existed = full.exists()

        # Proteccion: no sobrescribir archivos criticos sin tests
        for pat in PROTECTED_PATTERNS:
            if pat in str(rel):
                return {
                    'success': False,
                    'error': f'Archivo protegido: {pat}. Use self_update_and_test para cambios criticos.',
                    'path': str(rel),
                }

        if existed and create_backup:
            self._backup(rel)

        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding='utf-8')

        result = {
            'success': True,
            'path': str(rel),
            'bytes_written': len(content.encode('utf-8')),
            'was_new': not existed,
            'backup_created': existed and create_backup,
        }
        self._log_event('write_file', result)
        logger.info('self_update: wrote %s (%d bytes)', rel, result['bytes_written'])
        return result

    # ------------------------------------------------------------------
    # Parcheo de texto
    # ------------------------------------------------------------------

    def apply_text_patch(
        self,
        relative_path: str,
        old_text: str,
        new_text: str,
        *,
        create_backup: bool = True,
    ) -> dict[str, Any]:
        """Reemplaza old_text por new_text en un archivo existente."""
        rel = Path(relative_path)
        full = self.workspace_root / rel

        if not full.exists():
            return {
                'success': False,
                'error': f'Archivo no encontrado: {rel}',
                'path': str(rel),
            }

        original = full.read_text(encoding='utf-8')
        if old_text not in original:
            return {
                'success': False,
                'error': 'Texto objetivo no encontrado (ya aplicado?)',
                'path': str(rel),
            }

        count = original.count(old_text)
        if count > 1:
            return {
                'success': False,
                'error': f'Texto objetivo ambiguo ({count} ocurrencias). Proporcione mas contexto.',
                'path': str(rel),
            }

        if create_backup:
            self._backup(rel)

        patched = original.replace(old_text, new_text, 1)
        full.write_text(patched, encoding='utf-8')

        result = {
            'success': True,
            'path': str(rel),
            'chars_removed': len(old_text),
            'chars_added': len(new_text),
        }
        self._log_event('apply_text_patch', result)
        logger.info('self_update: patched %s (-%d/+%d chars)', rel, len(old_text), len(new_text))
        return result

    # ------------------------------------------------------------------
    # Self-update con test y rollback
    # ------------------------------------------------------------------

    def self_update_and_test(
        self,
        patches: list[dict[str, str]],
        *,
        test_suite: str = 'tests/',
        auto_rollback: bool = True,
    ) -> dict[str, Any]:
        """Aplica una lista de parches y verifica con pytest.

        Cada patch: {
            'action': 'write' | 'patch',
            'path': 'relative/path',
            'content': '...',           # solo para 'write'
            'old_text': '...',          # solo para 'patch'
            'new_text': '...',          # solo para 'patch'
        }

        Si los tests fallan y auto_rollback=True, revierte todos los cambios.
        """
        applied: list[dict] = []
        backed_up: list[tuple[str, Path]] = []  # (relative_path, backup_path)

        # 1. Aplicar todos los parches
        for i, patch in enumerate(patches):
            action = patch.get('action', 'patch')
            rel_path = patch.get('path', '')

            if action == 'write':
                backup_path = self._backup(rel_path) if (self.workspace_root / rel_path).exists() else None
                result = self.write_file(rel_path, patch.get('content', ''), create_backup=False)
            elif action == 'patch':
                backup_path = self._backup(rel_path) if (self.workspace_root / rel_path).exists() else None
                result = self.apply_text_patch(
                    rel_path,
                    patch.get('old_text', ''),
                    patch.get('new_text', ''),
                    create_backup=False,
                )
            else:
                result = {'success': False, 'error': f'Accion desconocida: {action}'}
                backup_path = None

            applied.append(result)
            if backup_path:
                backed_up.append((rel_path, backup_path))

            if not result.get('success'):
                if auto_rollback:
                    self._rollback(backed_up)
                    return {
                        'success': False,
                        'phase': 'apply',
                        'failed_at_patch': i,
                        'error': result.get('error', 'unknown'),
                        'rolled_back': True,
                        'patches_applied': applied,
                    }

        # 2. Ejecutar tests
        test_result = self._run_pytest(test_suite)

        if test_result['returncode'] != 0 and auto_rollback:
            self._rollback(backed_up)
            final = {
                'success': False,
                'phase': 'test',
                'test_result': test_result,
                'rolled_back': True,
                'patches_applied': applied,
            }
            self._log_event('self_update_failed', final)
            logger.warning('self_update: tests failed, rolled back %d patches', len(backed_up))
            return final

        final = {
            'success': test_result['returncode'] == 0,
            'phase': 'complete',
            'test_result': test_result,
            'rolled_back': False,
            'patches_applied': applied,
        }
        self._log_event('self_update_success' if final['success'] else 'self_update_failed', final)
        logger.info(
            'self_update: %s — %d patches, %d passed, %d failed',
            'SUCCESS' if final['success'] else 'TESTS_FAILED_NO_ROLLBACK',
            len(applied),
            test_result.get('passed', 0),
            test_result.get('failed', 0),
        )
        return final

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _backup(self, relative_path: str | Path) -> Path | None:
        """Crea backup de un archivo. Retorna path del backup."""
        rel = Path(relative_path)
        full = self.workspace_root / rel
        if not full.exists():
            return None
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup = self.backup_dir / f'{rel.name}.{ts}.bak'
        shutil.copy2(full, backup)
        return backup

    def _rollback(self, backed_up: list[tuple[str, Path]]) -> None:
        """Restaura archivos desde backups."""
        for rel_path, backup_path in reversed(backed_up):
            full = self.workspace_root / rel_path
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, full)
                logger.info('self_update: rolled back %s', rel_path)

    def _run_pytest(self, test_suite: str) -> dict:
        """Ejecuta pytest y retorna resultado."""
        try:
            env = {
                'PYTHONPATH': str(self.workspace_root / 'src'),
                'PATH': subprocess.os.environ.get('PATH', ''),
                'SYSTEMROOT': subprocess.os.environ.get('SYSTEMROOT', ''),
                'TEMP': subprocess.os.environ.get('TEMP', ''),
                'TMP': subprocess.os.environ.get('TMP', ''),
            }
            result = subprocess.run(
                ['python', '-m', 'pytest', test_suite, '-q', '--tb=short', '--no-header'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace_root),
                env={**subprocess.os.environ, 'PYTHONPATH': str(self.workspace_root / 'src')},
            )
            output = result.stdout + result.stderr
            # Parse passed/failed from output
            passed = failed = 0
            for line in output.splitlines():
                if 'passed' in line:
                    import re
                    m = re.search(r'(\d+) passed', line)
                    if m:
                        passed = int(m.group(1))
                if 'failed' in line:
                    import re
                    m = re.search(r'(\d+) failed', line)
                    if m:
                        failed = int(m.group(1))
            return {
                'returncode': result.returncode,
                'passed': passed,
                'failed': failed,
                'output_tail': output[-2000:] if len(output) > 2000 else output,
            }
        except subprocess.TimeoutExpired:
            return {'returncode': -1, 'passed': 0, 'failed': 0, 'output_tail': 'TIMEOUT'}
        except Exception as e:
            return {'returncode': -1, 'passed': 0, 'failed': 0, 'output_tail': str(e)}

    def _log_event(self, event_type: str, data: dict) -> None:
        """Registra evento en log."""
        entry = {'timestamp': _utc_now(), 'event': event_type, **data}
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, default=str) + '\n')
        except Exception:
            pass
