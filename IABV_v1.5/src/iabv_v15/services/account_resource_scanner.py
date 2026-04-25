"""Account & Resource Scanner — control de cuentas, APIs y recursos disponibles.

Escanea qué cuentas y recursos tiene IABV a su disposición:
  - Cuentas de navegador (cookies activas, sesiones abiertas)
  - APIs configuradas y su estado (Devin, GitHub, OpenAI, Ollama)
  - Cuotas y límites de APIs (rate limits, créditos restantes)
  - Herramientas externas y su disponibilidad
  - Credenciales/secretos configurados (sin exponer valores)

El programa debe saber qué tiene disponible para elegir la mejor
herramienta/ruta. Si algo no está disponible, debe notificar al
usuario en vez de quedarse bloqueado.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 8


def _safe_request(url: str, headers: dict[str, str] | None = None,
                  timeout: int = _HTTP_TIMEOUT) -> dict[str, Any]:
    """Make an HTTP GET request using urllib (no external deps)."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return {
                'status': resp.status,
                'ok': 200 <= resp.status < 300,
                'body': body,
                'headers': dict(resp.headers),
            }
    except urllib.error.HTTPError as exc:
        return {
            'status': exc.code,
            'ok': False,
            'body': exc.read().decode('utf-8', errors='replace')[:500],
            'error': str(exc),
        }
    except Exception as exc:
        return {'status': 0, 'ok': False, 'error': str(exc)}


# ──────────────────────────────────────────────────────────────
# API / Service Status Scanners
# ──────────────────────────────────────────────────────────────

def scan_github_api() -> dict[str, Any]:
    """Check GitHub API access and rate limits."""
    token = os.environ.get('GITHUB_TOKEN_IABV') or os.environ.get('GITHUB_TOKEN') or ''
    if not token:
        return {
            'available': False,
            'reason': 'no_token',
            'detail': 'GITHUB_TOKEN_IABV ni GITHUB_TOKEN están configurados',
        }

    resp = _safe_request(
        'https://api.github.com/rate_limit',
        headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'},
    )
    if not resp.get('ok'):
        return {
            'available': False,
            'reason': 'api_error',
            'detail': resp.get('error', f'HTTP {resp.get("status")}'),
        }

    try:
        data = json.loads(resp['body'])
        core = data.get('resources', {}).get('core', {})
        return {
            'available': True,
            'rate_limit': core.get('limit', 0),
            'remaining': core.get('remaining', 0),
            'reset_at': datetime.fromtimestamp(
                core.get('reset', 0), tz=timezone.utc
            ).isoformat() if core.get('reset') else None,
            'usage_pct': round(
                (1 - core.get('remaining', 0) / max(core.get('limit', 1), 1)) * 100, 1
            ),
        }
    except Exception as exc:
        return {'available': False, 'reason': 'parse_error', 'detail': str(exc)}


def scan_devin_api() -> dict[str, Any]:
    """Check Devin API access."""
    token = os.environ.get('DEVIN_API_KEY_IABV') or os.environ.get('DEVIN_API_KEY') or ''
    if not token:
        return {
            'available': False,
            'reason': 'no_token',
            'detail': 'DEVIN_API_KEY_IABV ni DEVIN_API_KEY están configurados',
        }

    resp = _safe_request(
        'https://api.devin.ai/v1/sessions',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
    )
    return {
        'available': resp.get('ok', False),
        'status_code': resp.get('status', 0),
        'detail': 'ok' if resp.get('ok') else resp.get('error', f'HTTP {resp.get("status")}'),
    }


def scan_ollama_api() -> dict[str, Any]:
    """Check Ollama local API and loaded models."""
    resp = _safe_request('http://localhost:11434/api/tags', timeout=5)
    if not resp.get('ok'):
        return {
            'available': False,
            'reason': 'not_running',
            'detail': resp.get('error', 'Ollama no responde en localhost:11434'),
        }

    try:
        data = json.loads(resp['body'])
        models = data.get('models', [])
        return {
            'available': True,
            'models_count': len(models),
            'models': [
                {
                    'name': m.get('name', ''),
                    'size_gb': round(m.get('size', 0) / (1024**3), 1),
                }
                for m in models[:10]
            ],
        }
    except Exception as exc:
        return {'available': True, 'models_count': 0, 'parse_error': str(exc)}


# ──────────────────────────────────────────────────────────────
# Browser Account Detection
# ──────────────────────────────────────────────────────────────

def scan_browser_accounts() -> dict[str, Any]:
    """Detect active browser sessions/accounts from Chrome profiles."""
    accounts: list[dict[str, str]] = []
    chrome_dirs: list[Path] = []

    if os.name == 'nt':
        local_app = os.environ.get('LOCALAPPDATA', '')
        if local_app:
            chrome_dirs.append(Path(local_app) / 'Google' / 'Chrome' / 'User Data')
        edge_dir = Path(local_app) / 'Microsoft' / 'Edge' / 'User Data' if local_app else None
        if edge_dir and edge_dir.exists():
            chrome_dirs.append(edge_dir)
    else:
        home = Path.home()
        chrome_dirs.append(home / '.config' / 'google-chrome')
        chrome_dirs.append(home / '.config' / 'chromium')

    for chrome_dir in chrome_dirs:
        if not chrome_dir.exists():
            continue

        browser_name = 'Chrome'
        if 'edge' in str(chrome_dir).lower():
            browser_name = 'Edge'
        elif 'chromium' in str(chrome_dir).lower():
            browser_name = 'Chromium'

        # Check profile preferences for logged-in accounts
        for profile_dir in chrome_dir.iterdir():
            if not profile_dir.is_dir():
                continue
            prefs_file = profile_dir / 'Preferences'
            if not prefs_file.exists():
                continue
            try:
                prefs = json.loads(prefs_file.read_text(encoding='utf-8', errors='replace'))
                account_info = prefs.get('account_info', [])
                for acc in account_info:
                    email = acc.get('email', '')
                    if email:
                        accounts.append({
                            'browser': browser_name,
                            'profile': profile_dir.name,
                            'email': email,
                            'full_name': acc.get('full_name', ''),
                        })
                # Also check signin info
                signin = prefs.get('google', {}).get('services', {}).get('signin', {})
                if signin.get('allowed') and not account_info:
                    accounts.append({
                        'browser': browser_name,
                        'profile': profile_dir.name,
                        'email': 'signed_in (details unavailable)',
                    })
            except Exception:
                continue

    return {
        'accounts': accounts,
        'count': len(accounts),
        'browsers_scanned': [str(d) for d in chrome_dirs if d.exists()],
    }


# ──────────────────────────────────────────────────────────────
# Configured Secrets Detection (names only, never values)
# ──────────────────────────────────────────────────────────────

def scan_configured_secrets() -> dict[str, Any]:
    """Detect which secret/env vars are configured (names only, never values)."""
    known_secrets = [
        'GITHUB_TOKEN_IABV', 'GITHUB_TOKEN',
        'DEVIN_API_KEY_IABV', 'DEVIN_API_KEY',
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
        'CLOUDFLARE_TUNNEL_TOKEN', 'CLOUDFLARED_TOKEN',
        'IABV_MCP_API_KEY',
    ]
    configured: list[str] = []
    missing: list[str] = []
    for name in known_secrets:
        if os.environ.get(name):
            configured.append(name)
        else:
            missing.append(name)

    # Check secrets file
    secrets_file = Path.home() / '.iabv_secrets.ps1'
    secrets_from_file: list[str] = []
    if secrets_file.exists():
        try:
            content = secrets_file.read_text(encoding='utf-8', errors='replace')
            for line in content.splitlines():
                m = re.match(r'\$env:(\w+)\s*=', line)
                if m:
                    secrets_from_file.append(m.group(1))
        except Exception:
            pass

    return {
        'configured': configured,
        'missing': missing,
        'configured_count': len(configured),
        'missing_count': len(missing),
        'secrets_file_exists': secrets_file.exists(),
        'secrets_in_file': secrets_from_file,
    }


# ──────────────────────────────────────────────────────────────
# Cloudflare Tunnel Status
# ──────────────────────────────────────────────────────────────

def scan_cloudflare_tunnel() -> dict[str, Any]:
    """Check if cloudflared tunnel is running."""
    try:
        r = subprocess.run(
            ['cloudflared', 'version'],
            capture_output=True, text=True, timeout=5,
        )
        version = r.stdout.strip() if r.returncode == 0 else 'unknown'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {'available': False, 'reason': 'cloudflared not installed'}

    # Check if tunnel process is running
    running = False
    if os.name == 'nt':
        try:
            r = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq cloudflared.exe', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=5,
            )
            running = 'cloudflared' in r.stdout.lower()
        except Exception:
            pass
    else:
        try:
            r = subprocess.run(['pgrep', '-f', 'cloudflared'], capture_output=True, timeout=5)
            running = r.returncode == 0
        except Exception:
            pass

    return {
        'available': True,
        'version': version,
        'tunnel_running': running,
    }


# ──────────────────────────────────────────────────────────────
# Full Account & Resource Report
# ──────────────────────────────────────────────────────────────

def account_resource_scan() -> dict[str, Any]:
    """Full scan of all accounts, APIs, and resources available to IABV."""
    github = scan_github_api()
    devin = scan_devin_api()
    ollama = scan_ollama_api()
    browser = scan_browser_accounts()
    secrets = scan_configured_secrets()
    tunnel = scan_cloudflare_tunnel()

    # Calculate overall resource health
    total_resources = 6
    available_count = sum(1 for r in [github, devin, ollama, tunnel]
                         if r.get('available'))
    available_count += 1 if secrets['configured_count'] > 0 else 0
    available_count += 1 if browser['count'] > 0 else 0

    alerts: list[str] = []
    if not github.get('available'):
        alerts.append(f'GitHub API: {github.get("detail", "no disponible")}')
    elif github.get('remaining', 5000) < 100:
        alerts.append(f'GitHub API: solo quedan {github["remaining"]} requests (se reinicia {github.get("reset_at", "?")})')
    if not devin.get('available'):
        alerts.append(f'Devin API: {devin.get("detail", "no disponible")}')
    if not ollama.get('available'):
        alerts.append(f'Ollama: {ollama.get("detail", "no disponible")}')
    if secrets['missing_count'] > 2:
        alerts.append(f'Secretos faltantes: {", ".join(secrets["missing"][:3])}...')

    return {
        'github_api': github,
        'devin_api': devin,
        'ollama': ollama,
        'browser_accounts': browser,
        'secrets': secrets,
        'cloudflare_tunnel': tunnel,
        'summary': {
            'total_resources': total_resources,
            'available': available_count,
            'coverage_pct': round(available_count / max(total_resources, 1) * 100),
            'alerts': alerts,
            'alert_count': len(alerts),
        },
    }


def format_account_resource_report(scan: dict[str, Any]) -> str:
    """Format account/resource scan for the auto-analysis report."""
    lines: list[str] = ['== CUENTAS Y RECURSOS DISPONIBLES ==']
    summary = scan.get('summary', {})

    # APIs
    gh = scan.get('github_api', {})
    if gh.get('available'):
        lines.append(f'  GitHub API: OK (rate limit: {gh.get("remaining", "?")}/{gh.get("rate_limit", "?")})')
    else:
        lines.append(f'  GitHub API: NO DISPONIBLE — {gh.get("detail", "?")}')

    dv = scan.get('devin_api', {})
    if dv.get('available'):
        lines.append('  Devin API: OK')
    else:
        lines.append(f'  Devin API: NO DISPONIBLE — {dv.get("detail", "?")}')

    ol = scan.get('ollama', {})
    if ol.get('available'):
        lines.append(f'  Ollama: OK ({ol.get("models_count", 0)} modelos disponibles)')
        for m in ol.get('models', [])[:3]:
            lines.append(f'    - {m["name"]} ({m["size_gb"]} GB)')
    else:
        lines.append(f'  Ollama: NO DISPONIBLE — {ol.get("detail", "?")}')

    # Tunnel
    tun = scan.get('cloudflare_tunnel', {})
    if tun.get('available'):
        status = 'corriendo' if tun.get('tunnel_running') else 'instalado pero no corriendo'
        lines.append(f'  Cloudflare Tunnel: {status}')
    else:
        lines.append(f'  Cloudflare Tunnel: {tun.get("reason", "no disponible")}')

    # Browser accounts
    browser = scan.get('browser_accounts', {})
    if browser.get('count', 0) > 0:
        lines.append(f'  Cuentas de navegador: {browser["count"]}')
        for acc in browser.get('accounts', [])[:5]:
            lines.append(f'    - [{acc.get("browser", "?")}] {acc.get("email", "?")}')
    else:
        lines.append('  Cuentas de navegador: ninguna detectada')

    # Secrets
    sec = scan.get('secrets', {})
    lines.append(f'  Secretos configurados: {sec.get("configured_count", 0)}/{sec.get("configured_count", 0) + sec.get("missing_count", 0)}')
    if sec.get('missing'):
        lines.append(f'    Faltantes: {", ".join(sec["missing"][:4])}')

    # Alerts
    alerts = summary.get('alerts', [])
    if alerts:
        lines.append(f'  ALERTAS ({len(alerts)}):')
        for a in alerts:
            lines.append(f'    ! {a}')

    lines.append(f'  Cobertura de recursos: {summary.get("coverage_pct", 0)}%')

    return '\n'.join(lines)
