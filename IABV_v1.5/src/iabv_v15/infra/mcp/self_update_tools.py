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
        import re as _re
        ws = Path(workspace_root)

        def _pre_commit_validate(file_list: list[str]) -> list[str]:
            """Validacion pre-commit: detecta errores conocidos antes de commitear."""
            errors: list[str] = []
            for fpath in file_list:
                full = ws / fpath
                if not full.exists():
                    continue
                try:
                    text = full.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    continue

                # ── QML: detectar signal duplicado con property ──
                if fpath.endswith('.qml'):
                    props = set()
                    signals = set()
                    for line in text.splitlines():
                        stripped = line.strip()
                        # property <type> <name>
                        m = _re.match(r'property\s+\w+\s+(\w+)', stripped)
                        if m:
                            props.add(m.group(1))
                        # signal <name>(...)
                        m = _re.match(r'signal\s+(\w+)', stripped)
                        if m:
                            signals.add(m.group(1))
                    for sig in signals:
                        # QML auto-genera <prop>Changed para cada property
                        base = sig.replace('Changed', '')
                        if base in props:
                            errors.append(
                                f'QML duplicate signal: {fpath} declara '
                                f'property "{base}" Y signal "{sig}" — '
                                f'QML auto-genera {sig} desde la property. '
                                f'Eliminar la declaracion explicita del signal.'
                            )

                # ── Python: detectar anti-patrones aprendidos ──
                if fpath.endswith('.py'):
                    for i, line in enumerate(text.splitlines(), 1):
                        stripped = line.strip()
                        # Detectar ThreadPoolExecutor en archivos de UI
                        if 'viewmodel' in fpath.lower() or 'view_model' in fpath.lower():
                            if 'with concurrent.futures.ThreadPoolExecutor' in stripped:
                                errors.append(
                                    f'THREADPOOL_UI_BLOCK: {fpath}:{i} usa '
                                    f'"with ThreadPoolExecutor" en ViewModel — '
                                    f'pool.shutdown(wait=True) bloquea la UI. '
                                    f'Usar threading.Thread + threading.Event.'
                                )
                        # Detectar asignacion directa a modelos Pydantic
                        if 'card.' in line and '=' in line and 'card.metadata' not in line:
                            if (_re.match(r'card\.(?!metadata)[a-z_]+\s*=', stripped)
                                    and 'getattr' not in stripped
                                    and '#' not in stripped.split('=')[0]):
                                pass  # Solo warning

            return errors

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

            # ── Pre-commit validation ──
            staged_files = file_list if files else []
            if not staged_files:
                # Get list of staged files from git
                diff_r = subprocess.run(
                    ['git', 'diff', '--cached', '--name-only'],
                    capture_output=True, text=True, cwd=ws,
                )
                staged_files = [f.strip() for f in diff_r.stdout.splitlines() if f.strip()]

            validation_errors = _pre_commit_validate(staged_files)
            if validation_errors:
                # Revert staged changes
                subprocess.run(['git', 'reset', 'HEAD'], cwd=ws, capture_output=True)
                return json.dumps({
                    'success': False,
                    'committed': False,
                    'pushed': False,
                    'validation_errors': validation_errors,
                    'error': f'Pre-commit validation fallo: {len(validation_errors)} error(es) detectados. '
                             f'El programa aprendio de errores anteriores y bloqueo el commit.',
                    'learned_patterns_applied': [
                        'QML_DUPLICATE_SIGNAL: property X auto-genera signal XChanged',
                    ],
                })

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

    @mcp.tool()
    def gpu_diagnostics_and_benchmark(
        benchmark: bool = False,
        pull_model: str = '',
    ) -> str:
        """Diagnostica GPU, modelos Ollama, y opcionalmente benchmarkea.

        Args:
            benchmark: Si True, corre un benchmark rapido de los modelos instalados.
            pull_model: Si se indica, descarga un modelo nuevo de Ollama (ej: 'llama3.2:3b').

        Returns:
            JSON con gpu_info, ollama_models, running_models, y benchmark_results.
        """
        import subprocess
        import time as _time
        import httpx

        result: dict = {'gpu_info': {}, 'ollama_models': [], 'running_models': [], 'benchmark_results': []}

        # 1. GPU detection via nvidia-smi
        try:
            nv = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,driver_version',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10,
            )
            if nv.returncode == 0:
                parts = [p.strip() for p in nv.stdout.strip().split(',')]
                if len(parts) >= 6:
                    result['gpu_info'] = {
                        'name': parts[0],
                        'memory_total_mb': int(parts[1]),
                        'memory_used_mb': int(parts[2]),
                        'memory_free_mb': int(parts[3]),
                        'utilization_pct': int(parts[4]),
                        'driver_version': parts[5],
                        'detected': True,
                    }
                else:
                    result['gpu_info'] = {'detected': True, 'raw': nv.stdout.strip()}
            else:
                result['gpu_info'] = {'detected': False, 'error': nv.stderr.strip()[:200]}
        except Exception as e:
            result['gpu_info'] = {'detected': False, 'error': str(e)[:200]}

        # 2. Ollama models (via REST API, not /v1)
        ollama_base = 'http://127.0.0.1:11434'
        try:
            with httpx.Client(timeout=10) as client:
                tags = client.get(f'{ollama_base}/api/tags')
                if tags.status_code == 200:
                    models = tags.json().get('models', [])
                    for m in models:
                        result['ollama_models'].append({
                            'name': m.get('name', ''),
                            'size_gb': round(m.get('size', 0) / 1e9, 2),
                            'modified': m.get('modified_at', '')[:19],
                            'family': m.get('details', {}).get('family', ''),
                            'parameter_size': m.get('details', {}).get('parameter_size', ''),
                            'quantization': m.get('details', {}).get('quantization_level', ''),
                        })
        except Exception as e:
            result['ollama_models_error'] = str(e)[:200]

        # 3. Currently running models (GPU layers info)
        try:
            with httpx.Client(timeout=10) as client:
                ps = client.get(f'{ollama_base}/api/ps')
                if ps.status_code == 200:
                    running = ps.json().get('models', [])
                    for m in running:
                        result['running_models'].append({
                            'name': m.get('name', ''),
                            'size_gb': round(m.get('size', 0) / 1e9, 2),
                            'size_vram_gb': round(m.get('size_vram', 0) / 1e9, 2),
                            'digest': m.get('digest', '')[:12],
                            'gpu_layers': 'using_gpu' if m.get('size_vram', 0) > 0 else 'cpu_only',
                        })
        except Exception as e:
            result['running_models_error'] = str(e)[:200]

        # 4. Pull model if requested
        if pull_model:
            try:
                with httpx.Client(timeout=300) as client:
                    pull_resp = client.post(f'{ollama_base}/api/pull', json={'name': pull_model, 'stream': False})
                    result['pull_result'] = {'model': pull_model, 'status': pull_resp.json().get('status', 'unknown')}
            except Exception as e:
                result['pull_result'] = {'model': pull_model, 'error': str(e)[:200]}

        # 5. Benchmark if requested
        if benchmark:
            prompt = 'Responde en una linea: cual es la capital de Colombia?'
            for model_info in result['ollama_models'][:5]:
                model_name = model_info['name']
                try:
                    with httpx.Client(timeout=60) as client:
                        start = _time.time()
                        gen = client.post(f'{ollama_base}/api/generate',
                            json={'model': model_name, 'prompt': prompt, 'stream': False},
                            timeout=60)
                        elapsed = round(_time.time() - start, 2)
                        if gen.status_code == 200:
                            data = gen.json()
                            result['benchmark_results'].append({
                                'model': model_name,
                                'time_seconds': elapsed,
                                'eval_count': data.get('eval_count', 0),
                                'eval_duration_ns': data.get('eval_duration', 0),
                                'tokens_per_second': round(data.get('eval_count', 0) / (data.get('eval_duration', 1) / 1e9), 1) if data.get('eval_duration') else 0,
                                'response': data.get('response', '')[:100],
                                'gpu_layers': 'check /api/ps for details',
                            })
                        else:
                            result['benchmark_results'].append({
                                'model': model_name, 'error': f'HTTP {gen.status_code}', 'time_seconds': elapsed,
                            })
                except Exception as e:
                    result['benchmark_results'].append({
                        'model': model_name, 'error': str(e)[:200],
                    })

        return json.dumps(result, indent=2, default=str)

    logger.info('self_update_tools: 5 tools registered (write_repo_file, apply_text_patch, self_update_and_test, git_commit_and_push, gpu_diagnostics_and_benchmark)')
