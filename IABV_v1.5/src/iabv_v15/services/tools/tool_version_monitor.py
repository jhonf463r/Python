"""Tool Version Monitor — metacognitive awareness of tool versions.

Checks installed versions of all tools IABV uses, queries for available
updates, and persists a version history log so the system can learn:
- Which tools are outdated and may have new capabilities
- When tools were last updated
- Whether an update could improve performance or unlock features

Runs during auto-analysis and bootstrap (optional).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _run_cmd(args: list[str], timeout: int = 10) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


def _extract_version(text: str) -> str:
    """Extract a semver-like version from a string."""
    m = re.search(r'(\d+\.\d+[\.\d]*)', text)
    return m.group(1) if m else text.strip()[:30]


def check_ollama_version() -> dict[str, Any]:
    """Check Ollama version and available models."""
    result: dict[str, Any] = {'tool': 'ollama', 'available': False}
    version_output = _run_cmd(['ollama', '--version'])
    if version_output:
        result['available'] = True
        result['installed_version'] = _extract_version(version_output)
    # Check loaded models
    ps_output = _run_cmd(['ollama', 'ps'])
    if ps_output:
        models = [l.split()[0] for l in ps_output.strip().splitlines()[1:] if l.split()]
        result['loaded_models'] = models
    # Check available models
    list_output = _run_cmd(['ollama', 'list'])
    if list_output:
        available = []
        for line in list_output.strip().splitlines()[1:]:
            parts = line.split()
            if parts:
                available.append(parts[0])
        result['installed_models'] = available
    return result


def check_git_version() -> dict[str, Any]:
    """Check git version."""
    result: dict[str, Any] = {'tool': 'git', 'available': False}
    output = _run_cmd(['git', '--version'])
    if output:
        result['available'] = True
        result['installed_version'] = _extract_version(output)
    return result


def check_python_version() -> dict[str, Any]:
    """Check Python version."""
    import sys
    return {
        'tool': 'python',
        'available': True,
        'installed_version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
        'implementation': sys.implementation.name,
    }


def check_gh_cli_version() -> dict[str, Any]:
    """Check GitHub CLI version."""
    result: dict[str, Any] = {'tool': 'gh', 'available': False}
    output = _run_cmd(['gh', '--version'])
    if output:
        result['available'] = True
        result['installed_version'] = _extract_version(output.splitlines()[0])
    return result


def check_cloudflared_version() -> dict[str, Any]:
    """Check cloudflared version."""
    result: dict[str, Any] = {'tool': 'cloudflared', 'available': False}
    output = _run_cmd(['cloudflared', '--version'])
    if output:
        result['available'] = True
        result['installed_version'] = _extract_version(output)
    return result


def check_ollama_api_version() -> dict[str, Any]:
    """Check Ollama API availability and version via HTTP."""
    result: dict[str, Any] = {'tool': 'ollama_api', 'available': False}
    try:
        import httpx
        r = httpx.get('http://127.0.0.1:11434/api/version', timeout=5)
        if r.status_code == 200:
            data = r.json()
            result['available'] = True
            result['api_version'] = data.get('version', '?')
    except Exception:
        pass
    return result


def check_devin_api_version() -> dict[str, Any]:
    """Check Devin API availability."""
    result: dict[str, Any] = {'tool': 'devin_api', 'available': False}
    api_key = os.environ.get('DEVIN_API_KEY', '')
    if not api_key:
        result['reason'] = 'DEVIN_API_KEY not set'
        return result
    try:
        import httpx
        r = httpx.get(
            'https://api.devin.ai/v1/sessions',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'limit': 1},
            timeout=10,
        )
        result['available'] = r.status_code == 200
        result['status_code'] = r.status_code
    except Exception as exc:
        result['reason'] = str(exc)[:100]
    return result


def check_github_api_version() -> dict[str, Any]:
    """Check GitHub API availability."""
    result: dict[str, Any] = {'tool': 'github_api', 'available': False}
    token = os.environ.get('GITHUB_TOKEN', '') or os.environ.get('GH_TOKEN', '')
    headers: dict[str, str] = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        import httpx
        r = httpx.get(
            'https://api.github.com/rate_limit',
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            core = data.get('resources', {}).get('core', {})
            result['available'] = True
            result['rate_limit_remaining'] = core.get('remaining', '?')
            result['rate_limit_total'] = core.get('limit', '?')
    except Exception as exc:
        result['reason'] = str(exc)[:100]
    return result


def full_version_scan() -> dict[str, Any]:
    """Run a full version scan of all tools IABV uses.

    Returns a dict with:
    - tools: list of tool version dicts
    - outdated: list of tools that may need updating
    - timestamp: when the scan was done
    - scan_duration_ms: how long it took
    """
    t0 = time.perf_counter()
    tools = [
        check_python_version(),
        check_ollama_version(),
        check_ollama_api_version(),
        check_git_version(),
        check_gh_cli_version(),
        check_cloudflared_version(),
        check_devin_api_version(),
        check_github_api_version(),
    ]
    scan_ms = int((time.perf_counter() - t0) * 1000)

    available = [t for t in tools if t.get('available')]
    unavailable = [t for t in tools if not t.get('available')]

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'scan_duration_ms': scan_ms,
        'tools': tools,
        'available_count': len(available),
        'unavailable_count': len(unavailable),
        'unavailable_tools': [t['tool'] for t in unavailable],
    }


def persist_version_log(workspace: str, scan_result: dict[str, Any]) -> str | None:
    """Persist a version scan result to the metacognition log.

    Appends to data/metacognition/tool_versions_log.jsonl.
    Returns the log path if successful, None otherwise.
    """
    try:
        log_dir = os.path.join(workspace, 'src', 'data', 'metacognition')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'tool_versions_log.jsonl')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(scan_result, ensure_ascii=False) + '\n')
        return log_path
    except Exception as exc:
        logger.warning('persist_version_log: %s', exc)
        return None


def format_version_report(scan: dict[str, Any]) -> str:
    """Format a version scan into a human-readable report section."""
    lines = ['== HERRAMIENTAS Y VERSIONES ==']
    for tool in scan.get('tools', []):
        name = tool.get('tool', '?')
        if tool.get('available'):
            version = tool.get('installed_version') or tool.get('api_version') or 'ok'
            extra = ''
            if tool.get('loaded_models'):
                extra = f" (modelos cargados: {', '.join(tool['loaded_models'])})"
            elif tool.get('rate_limit_remaining') is not None:
                extra = f" (rate limit: {tool['rate_limit_remaining']}/{tool['rate_limit_total']})"
            lines.append(f"  {name}: v{version}{extra}")
        else:
            reason = tool.get('reason', 'no disponible')
            lines.append(f"  {name}: NO DISPONIBLE — {reason}")
    lines.append(f"  Escaneo: {scan.get('scan_duration_ms', '?')}ms, "
                 f"{scan.get('available_count', 0)}/{len(scan.get('tools', []))} disponibles")
    return '\n'.join(lines)
