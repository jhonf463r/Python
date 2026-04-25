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


# Domains that indicate an active session for each assistant tool.
_TOOL_SESSION_DOMAINS: dict[str, list[str]] = {
    'chatgpt': ['chatgpt.com', 'chat.openai.com', 'auth0.openai.com'],
    'claude': ['claude.ai', 'anthropic.com'],
    'codex': ['chatgpt.com', 'openai.com'],
    'github': ['github.com'],
    'google': ['accounts.google.com', 'myaccount.google.com'],
}


def scan_browser_sessions() -> dict[str, Any]:
    """Detect which tool services have active cookies in the user's browsers.

    Reads the Chrome/Edge Cookies SQLite database (copy to temp to avoid
    locking) and checks for session cookies from known tool domains.
    This tells the program: "the user has an active ChatGPT session in
    Chrome Profile 2" — which means CDP mode can reuse that session.

    NOTE: Chrome encrypts cookie values on Windows (DPAPI). We do NOT
    read cookie values — we only check if rows EXIST for the domain,
    which is enough to confirm an active session.
    """
    import shutil as _shutil
    import tempfile as _tempfile

    sessions: list[dict[str, Any]] = []
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

        for profile_dir in chrome_dir.iterdir():
            if not profile_dir.is_dir():
                continue
            cookies_db = profile_dir / 'Cookies'
            # Newer Chrome versions use Network/Cookies
            if not cookies_db.exists():
                cookies_db = profile_dir / 'Network' / 'Cookies'
            if not cookies_db.exists():
                continue

            # Copy database to temp to avoid locking issues
            try:
                with _tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                    tmp_path = tmp.name
                _shutil.copy2(str(cookies_db), tmp_path)

                conn = sqlite3.connect(tmp_path)
                conn.execute('PRAGMA journal_mode=WAL')
                cursor = conn.cursor()

                for tool_name, domains in _TOOL_SESSION_DOMAINS.items():
                    for domain in domains:
                        try:
                            cursor.execute(
                                'SELECT COUNT(*) FROM cookies WHERE host_key LIKE ?',
                                (f'%{domain}%',),
                            )
                            count = cursor.fetchone()[0]
                            if count > 0:
                                sessions.append({
                                    'browser': browser_name,
                                    'profile': profile_dir.name,
                                    'tool': tool_name,
                                    'domain': domain,
                                    'cookie_count': count,
                                    'has_session': True,
                                })
                        except Exception:
                            continue

                conn.close()
            except Exception:
                continue
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # Aggregate by tool
    tool_sessions: dict[str, list[dict[str, Any]]] = {}
    for s in sessions:
        tool = s['tool']
        if tool not in tool_sessions:
            tool_sessions[tool] = []
        tool_sessions[tool].append(s)

    return {
        'sessions': sessions,
        'session_count': len(sessions),
        'tools_with_sessions': list(tool_sessions.keys()),
        'by_tool': tool_sessions,
    }


def diagnose_browser_access() -> str:
    """Run a comprehensive diagnostic of browser accounts and sessions.

    Returns a human-readable report that the user can verify.
    The program calls this to self-audit its browser awareness.
    """
    lines: list[str] = ['== DIAGNOSTICO DE ACCESO A NAVEGADORES ==', '']

    # 1. Accounts
    accounts = scan_browser_accounts()
    lines.append(f'Navegadores escaneados: {len(accounts.get("browsers_scanned", []))}')
    for b in accounts.get('browsers_scanned', []):
        lines.append(f'  {b}')
    lines.append(f'\nCuentas detectadas: {accounts["count"]}')
    for acc in accounts.get('accounts', []):
        lines.append(
            f'  [{acc.get("browser", "?")}] {acc.get("profile", "?")} — '
            f'{acc.get("email", "?")} ({acc.get("full_name", "")})'
        )

    # 2. Sessions (cookies)
    lines.append('')
    try:
        sess = scan_browser_sessions()
        lines.append(f'Sesiones activas detectadas: {sess["session_count"]}')
        for tool, tool_sessions in sess.get('by_tool', {}).items():
            lines.append(f'\n  {tool.upper()}:')
            for s in tool_sessions:
                lines.append(
                    f'    [{s["browser"]}] {s["profile"]} — {s["domain"]} '
                    f'({s["cookie_count"]} cookies)'
                )
        if not sess.get('tools_with_sessions'):
            lines.append('  Ninguna sesion activa detectada en cookies')
    except Exception as exc:
        lines.append(f'  Error escaneando cookies: {exc}')

    # 3. APIs
    lines.append('\n== ESTADO DE APIs ==')
    try:
        ollama = scan_ollama_api()
        lines.append(f'  Ollama: {"disponible" if ollama.get("available") else "no disponible"}')
        if ollama.get('available'):
            lines.append(f'    Modelos: {ollama.get("models_count", 0)}')
    except Exception:
        lines.append('  Ollama: error')
    try:
        github = scan_github_api()
        lines.append(f'  GitHub API: {"disponible" if github.get("available") else "no disponible"}')
        if github.get('available'):
            lines.append(f'    Remaining: {github.get("remaining", "?")}/{github.get("rate_limit", "?")}')
    except Exception:
        lines.append('  GitHub API: error')
    try:
        devin = scan_devin_api()
        lines.append(f'  Devin API: {"disponible" if devin.get("available") else "no disponible"}')
    except Exception:
        lines.append('  Devin API: error')

    # 4. Summary
    lines.append('\n== RESUMEN ==')
    if accounts['count'] > 0:
        lines.append(f'El programa VE {accounts["count"]} cuenta(s) del navegador.')
    else:
        lines.append('El programa NO ve cuentas del navegador.')

    try:
        sess_tools = sess.get('tools_with_sessions', [])
        if sess_tools:
            lines.append(
                f'Hay sesiones activas para: {", ".join(t.upper() for t in sess_tools)}. '
                f'Estas se pueden reusar via CDP.'
            )
        else:
            lines.append('No hay sesiones activas detectadas en cookies.')
    except Exception:
        pass

    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────
# Quota Tracker — message limits per account per program
#
# Tracks how many messages each account has used in each tool
# (ChatGPT, Claude, Codex), when free-tier limits reset, and
# which accounts are currently exhausted.  The program uses
# this to avoid querying exhausted accounts and to pick the
# best available account automatically.
#
# Persistence: ``data/evolution/quota_tracker.json``
# ──────────────────────────────────────────────────────────────

# Known free-tier limits (approximate) per tool.
_FREE_TIER_LIMITS: dict[str, dict[str, Any]] = {
    'chatgpt': {
        'messages_per_window': 15,
        'window_hours': 3,
        'label': 'ChatGPT Free (GPT-4o mini)',
    },
    'claude': {
        'messages_per_window': 20,
        'window_hours': 8,
        'label': 'Claude Free (Sonnet)',
    },
    'codex': {
        'messages_per_window': 20,
        'window_hours': 3,
        'label': 'Codex CLI Free',
    },
}


def _quota_file() -> Path:
    """Return the path to the quota tracker JSON file."""
    candidates = [
        Path(os.environ.get('IABV_WORKSPACE', '')) / 'data' / 'evolution' / 'quota_tracker.json',
        Path.home() / 'IABV_v1.5' / 'data' / 'evolution' / 'quota_tracker.json',
    ]
    for p in candidates:
        if p.parent.exists():
            return p
    candidates[0].parent.mkdir(parents=True, exist_ok=True)
    return candidates[0]


def _load_quota_state() -> dict[str, Any]:
    qf = _quota_file()
    if qf.exists():
        try:
            return json.loads(qf.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'accounts': {}}


def _save_quota_state(state: dict[str, Any]) -> None:
    qf = _quota_file()
    try:
        qf.parent.mkdir(parents=True, exist_ok=True)
        qf.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as exc:
        logger.debug('quota_tracker: failed to save state: %s', exc)


def record_message_sent(tool: str, email: str) -> dict[str, Any]:
    """Record that a message was sent via *tool* using *email*.

    Call this every time the program sends a query through an external
    assistant so the tracker can count usage against free-tier limits.
    Returns the updated quota status for the account.
    """
    import time as _time

    state = _load_quota_state()
    key = f'{tool}:{email}'
    entry = state['accounts'].get(key, {
        'tool': tool,
        'email': email,
        'messages': [],
        'total_sent': 0,
    })

    now = _time.time()
    entry['messages'].append(now)
    entry['total_sent'] = entry.get('total_sent', 0) + 1

    # Prune messages outside the current window
    limits = _FREE_TIER_LIMITS.get(tool, {})
    window_secs = limits.get('window_hours', 3) * 3600
    entry['messages'] = [t for t in entry['messages'] if now - t < window_secs]

    state['accounts'][key] = entry
    _save_quota_state(state)

    return _quota_status_for_entry(entry, tool)


def _quota_status_for_entry(entry: dict[str, Any], tool: str) -> dict[str, Any]:
    """Compute quota status for one account+tool entry."""
    import time as _time

    limits = _FREE_TIER_LIMITS.get(tool, {})
    max_msgs = limits.get('messages_per_window', 999)
    window_secs = limits.get('window_hours', 3) * 3600

    now = _time.time()
    recent = [t for t in entry.get('messages', []) if now - t < window_secs]
    used = len(recent)
    remaining = max(0, max_msgs - used)
    exhausted = remaining == 0

    resets_at: str | None = None
    if exhausted and recent:
        oldest_in_window = min(recent)
        reset_ts = oldest_in_window + window_secs
        resets_at = datetime.fromtimestamp(reset_ts, tz=timezone.utc).isoformat()

    return {
        'tool': tool,
        'email': entry.get('email', '?'),
        'used_in_window': used,
        'remaining': remaining,
        'limit': max_msgs,
        'window_hours': limits.get('window_hours', 3),
        'exhausted': exhausted,
        'resets_at': resets_at,
        'total_sent_all_time': entry.get('total_sent', 0),
        'label': limits.get('label', tool),
    }


def get_all_quota_status() -> dict[str, Any]:
    """Return quota status for every tracked account+tool pair."""
    state = _load_quota_state()
    statuses: list[dict[str, Any]] = []
    exhausted_keys: list[str] = []
    available_keys: list[str] = []

    for key, entry in state.get('accounts', {}).items():
        tool = entry.get('tool', key.split(':')[0] if ':' in key else '?')
        status = _quota_status_for_entry(entry, tool)
        statuses.append(status)
        if status['exhausted']:
            exhausted_keys.append(key)
        else:
            available_keys.append(key)

    return {
        'statuses': statuses,
        'total_tracked': len(statuses),
        'exhausted_count': len(exhausted_keys),
        'available_count': len(available_keys),
        'exhausted_keys': exhausted_keys,
        'available_keys': available_keys,
    }


def best_account_for_tool(tool: str) -> dict[str, Any] | None:
    """Pick the best available account for *tool* (least used, not exhausted).

    Returns ``None`` if no accounts are tracked for the tool or all are
    exhausted.  The program calls this before sending a query so it
    automatically rotates to a fresh account.
    """
    all_status = get_all_quota_status()
    candidates = [
        s for s in all_status['statuses']
        if s['tool'] == tool and not s['exhausted']
    ]
    if not candidates:
        return None
    # Pick the one with the most remaining messages
    candidates.sort(key=lambda s: s['remaining'], reverse=True)
    return candidates[0]


def format_quota_report() -> str:
    """Human-readable report of quota status for all tracked accounts."""
    all_status = get_all_quota_status()
    lines: list[str] = ['== ESTADO DE CUOTAS POR CUENTA ==', '']

    if not all_status['statuses']:
        lines.append('No hay cuentas rastreadas todavía.')
        lines.append('El rastreo comienza automáticamente al enviar mensajes.')
        return '\n'.join(lines)

    # Group by tool
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for s in all_status['statuses']:
        by_tool.setdefault(s['tool'], []).append(s)

    for tool, entries in by_tool.items():
        label = _FREE_TIER_LIMITS.get(tool, {}).get('label', tool.upper())
        lines.append(f'{label}:')
        for e in entries:
            status_icon = 'AGOTADA' if e['exhausted'] else 'OK'
            lines.append(
                f'  [{status_icon}] {e["email"]} — '
                f'{e["used_in_window"]}/{e["limit"]} mensajes '
                f'(ventana de {e["window_hours"]}h)'
            )
            if e['exhausted'] and e.get('resets_at'):
                lines.append(f'         Se reactiva: {e["resets_at"]}')
            lines.append(f'         Total histórico: {e["total_sent_all_time"]} mensajes')
        lines.append('')

    lines.append(f'Resumen: {all_status["available_count"]} disponibles, '
                 f'{all_status["exhausted_count"]} agotadas')
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────
# Configured Secrets Detection (names only, never values)
# ──────────────────────────────────────────────────────────────

def scan_configured_secrets() -> dict[str, Any]:
    """Detect which secret/env vars are configured (names only, never values).

    Secrets that are aliases of each other (e.g. GITHUB_TOKEN_IABV and
    GITHUB_TOKEN) are grouped: if ANY alias in the group is configured, the
    whole group is satisfied and none of its members appear as missing.
    """
    # Groups of aliases — if any name in a group is set, the group is OK.
    _alias_groups: list[tuple[str, ...]] = [
        ('GITHUB_TOKEN_IABV', 'IABV_GITHUB_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN'),
        ('DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY', 'DEVIN_API_KEY'),
    ]
    # Standalone secrets (not aliased).
    _standalone = [
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
        'CLOUDFLARE_TUNNEL_TOKEN', 'CLOUDFLARED_TOKEN',
        'IABV_MCP_API_KEY',
    ]
    configured: list[str] = []
    missing: list[str] = []

    for group in _alias_groups:
        found = [name for name in group if os.environ.get(name)]
        if found:
            configured.extend(found)
        else:
            missing.append(group[0])

    for name in _standalone:
        if os.environ.get(name):
            configured.append(name)
        else:
            missing.append(name)

    # Check secrets file — secrets configured here with ANY alias name
    # should satisfy the whole alias group, just like env vars do.
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

    # Cross-reference file-based secrets against alias groups to resolve
    # names that are configured in the file but not yet loaded into env.
    if secrets_from_file:
        file_set = set(secrets_from_file)
        resolved_from_file: list[str] = []
        for primary in list(missing):
            group = next((g for g in _alias_groups if g[0] == primary), None)
            if group:
                found_in_file = [n for n in group if n in file_set]
                if found_in_file:
                    missing.remove(primary)
                    configured.extend(found_in_file)
                    resolved_from_file.extend(found_in_file)
            elif primary in file_set:
                missing.remove(primary)
                configured.append(primary)
                resolved_from_file.append(primary)

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

    # Browser accounts — ALL accounts, grouped by browser
    browser = scan.get('browser_accounts', {})
    if browser.get('count', 0) > 0:
        lines.append(f'  Cuentas de navegador: {browser["count"]}')
        # Group by browser
        by_browser: dict[str, list[dict[str, str]]] = {}
        for acc in browser.get('accounts', []):
            b = acc.get('browser', '?')
            by_browser.setdefault(b, []).append(acc)
        for browser_name, accs in by_browser.items():
            lines.append(f'    [{browser_name}] ({len(accs)} cuentas):')
            for acc in accs:
                name = acc.get('full_name', '')
                profile = acc.get('profile', '')
                email = acc.get('email', '?')
                label = f'{email}'
                if name:
                    label = f'{name} <{email}>'
                if profile and profile != 'Default':
                    label += f' (perfil: {profile})'
                lines.append(f'      - {label}')
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
