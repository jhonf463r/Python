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
    # RESOURCE GUARD: Check if API scan is allowed
    try:
        from iabv_v15.services.resource_guard import get_resource_guard
        guard = get_resource_guard()
        decision = guard.check_action_allowed(
            action="account_resource_scan_github",
            estimated_ram_mb=10,
            goal_required=False,
            essential=False,
        )
        if not decision.allowed:
            return {
                'available': False,
                'reason': 'resource_guard',
                'detail': decision.reason,
                'ram_pressure': decision.pressure.value,
            }
    except Exception:
        # If guard fails, proceed (fail-safe)
        pass

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

def _chromium_browser_dirs() -> list[tuple[str, Path]]:
    """Return ``(browser_name, user_data_dir)`` for all Chromium-based browsers."""
    dirs: list[tuple[str, Path]] = []
    if os.name == 'nt':
        local_app = os.environ.get('LOCALAPPDATA', '')
        if not local_app:
            return dirs
        base = Path(local_app)
        candidates: list[tuple[str, Path]] = [
            ('Chrome', base / 'Google' / 'Chrome' / 'User Data'),
            ('Edge', base / 'Microsoft' / 'Edge' / 'User Data'),
            ('Brave', base / 'BraveSoftware' / 'Brave-Browser' / 'User Data'),
            ('Opera', Path(os.environ.get('APPDATA', '')) / 'Opera Software' / 'Opera Stable'),
            ('Opera GX', Path(os.environ.get('APPDATA', '')) / 'Opera Software' / 'Opera GX Stable'),
            ('Vivaldi', base / 'Vivaldi' / 'User Data'),
        ]
        for name, path in candidates:
            if path.exists():
                dirs.append((name, path))
    else:
        home = Path.home()
        candidates = [
            ('Chrome', home / '.config' / 'google-chrome'),
            ('Chromium', home / '.config' / 'chromium'),
            ('Edge', home / '.config' / 'microsoft-edge'),
            ('Brave', home / '.config' / 'BraveSoftware' / 'Brave-Browser'),
            ('Vivaldi', home / '.config' / 'vivaldi'),
            ('Opera', home / '.config' / 'opera'),
        ]
        for name, path in candidates:
            if path.exists():
                dirs.append((name, path))
    return dirs


def _firefox_accounts() -> list[dict[str, str]]:
    """Detect Firefox accounts from profile signedInUser.json files."""
    accounts: list[dict[str, str]] = []
    if os.name == 'nt':
        ff_root = Path(os.environ.get('APPDATA', '')) / 'Mozilla' / 'Firefox' / 'Profiles'
    else:
        ff_root = Path.home() / '.mozilla' / 'firefox'
    if not ff_root.exists():
        return accounts
    for profile_dir in ff_root.iterdir():
        if not profile_dir.is_dir():
            continue
        signed_in = profile_dir / 'signedInUser.json'
        if not signed_in.exists():
            continue
        try:
            data = json.loads(signed_in.read_text(encoding='utf-8', errors='replace'))
            acct = data.get('accountData', {})
            email = acct.get('email', '')
            if email:
                accounts.append({
                    'browser': 'Firefox',
                    'profile': profile_dir.name,
                    'email': email,
                    'full_name': acct.get('displayName', ''),
                })
        except Exception:
            continue
    return accounts


def scan_browser_accounts() -> dict[str, Any]:
    """Detect active browser sessions/accounts from all supported browsers.

    Scans: Chrome, Edge, Brave, Opera, Opera GX, Vivaldi (Chromium-based)
    and Firefox (signedInUser.json).
    """
    accounts: list[dict[str, str]] = []
    browsers_scanned: list[str] = []

    for browser_name, chrome_dir in _chromium_browser_dirs():
        browsers_scanned.append(str(chrome_dir))
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
                signin = prefs.get('google', {}).get('services', {}).get('signin', {})
                if signin.get('allowed') and not account_info:
                    accounts.append({
                        'browser': browser_name,
                        'profile': profile_dir.name,
                        'email': 'signed_in (details unavailable)',
                    })
            except Exception:
                continue

    # Firefox accounts
    ff_accounts = _firefox_accounts()
    if ff_accounts:
        accounts.extend(ff_accounts)
        if os.name == 'nt':
            browsers_scanned.append(str(Path(os.environ.get('APPDATA', '')) / 'Mozilla' / 'Firefox'))
        else:
            browsers_scanned.append(str(Path.home() / '.mozilla' / 'firefox'))

    return {
        'accounts': accounts,
        'count': len(accounts),
        'browsers_scanned': browsers_scanned,
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

    for browser_name, chrome_dir in _chromium_browser_dirs():
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


def governed_quota_rotation(
    tool: str,
    current_email: str = '',
) -> dict[str, Any]:
    """Sovereign rotation policy: pick the next account when quota exhausts.

    Respects AutonomyGovernancePolicy (read-only) by never modifying it.
    The policy is:
      1. If current account still has quota, keep it.
      2. Otherwise, rotate to the account with the most remaining messages.
      3. If ALL accounts are exhausted, report the earliest reset time.
      4. Never auto-switch without traceability — every rotation is logged.

    Returns a dict with:
    - ``action``: 'keep' | 'rotate' | 'wait' | 'no_accounts'
    - ``current``: status of current account (or None)
    - ``next``: recommended next account (or None)
    - ``wait_until``: ISO timestamp when the earliest account resets (if waiting)
    - ``reason``: human-readable explanation
    - ``rotation_trace``: audit-friendly record of the decision
    """
    import time as _time

    tool_lower = tool.strip().lower()
    all_status = get_all_quota_status()

    tool_accounts = [
        s for s in all_status['statuses']
        if s['tool'] == tool_lower
    ]

    if not tool_accounts:
        return {
            'action': 'no_accounts',
            'current': None,
            'next': None,
            'wait_until': None,
            'reason': f'No hay cuentas rastreadas para {tool_lower}.',
            'rotation_trace': {
                'tool': tool_lower,
                'decision': 'no_accounts',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        }

    current_status = None
    if current_email:
        current_status = next(
            (s for s in tool_accounts if s['email'].lower() == current_email.lower()),
            None,
        )

    if current_status and not current_status['exhausted']:
        return {
            'action': 'keep',
            'current': current_status,
            'next': None,
            'wait_until': None,
            'reason': (
                f'Cuenta actual {current_email} tiene '
                f'{current_status["remaining"]}/{current_status["limit"]} msgs.'
            ),
            'rotation_trace': {
                'tool': tool_lower,
                'decision': 'keep',
                'email': current_email,
                'remaining': current_status['remaining'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        }

    available = [s for s in tool_accounts if not s['exhausted']]
    available.sort(key=lambda s: s['remaining'], reverse=True)

    if available:
        next_account = available[0]
        logger.info(
            'governed_quota_rotation: rotating %s from %s to %s (remaining=%d)',
            tool_lower, current_email or '(none)', next_account['email'],
            next_account['remaining'],
        )
        return {
            'action': 'rotate',
            'current': current_status,
            'next': next_account,
            'wait_until': None,
            'reason': (
                f'Rotando a {next_account["email"]} con '
                f'{next_account["remaining"]}/{next_account["limit"]} msgs.'
            ),
            'rotation_trace': {
                'tool': tool_lower,
                'decision': 'rotate',
                'from_email': current_email or '',
                'to_email': next_account['email'],
                'remaining': next_account['remaining'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        }

    # All exhausted — find earliest reset
    reset_times: list[str] = []
    for s in tool_accounts:
        if s.get('resets_at'):
            reset_times.append(s['resets_at'])
    earliest_reset = min(reset_times) if reset_times else None

    return {
        'action': 'wait',
        'current': current_status,
        'next': None,
        'wait_until': earliest_reset,
        'reason': (
            f'Todas las cuentas de {tool_lower} agotadas. '
            f'{"Reactivación más temprana: " + earliest_reset if earliest_reset else "Sin hora de reset conocida."}'
        ),
        'rotation_trace': {
            'tool': tool_lower,
            'decision': 'wait',
            'exhausted_count': len(tool_accounts),
            'earliest_reset': earliest_reset,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        },
    }


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
# Brecha 2.3 — Web session status & refresh tracking
# ──────────────────────────────────────────────────────────────

def _web_session_state_path() -> Path:
    """Path to the web session state JSON file."""
    env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
    base = Path(env_dir) if env_dir else Path.home() / 'IABV_v1.5' / 'data'
    return base / 'evolution' / 'web_sessions' / 'session_state.json'


def _load_web_session_state() -> dict[str, Any]:
    path = _web_session_state_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'sessions': {}}


def _save_web_session_state(state: dict[str, Any]) -> None:
    path = _web_session_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')


def get_web_session_status(tool: str) -> dict[str, Any]:
    """Get the current web session status for a tool.

    Checks cookie validity, session age, and whether re-auth is needed.
    Combines persisted state (from record_web_session_refresh) with live
    browser cookie scanning.
    """
    tool_lower = tool.lower().replace('-', '_')
    state = _load_web_session_state()
    entry = state.get('sessions', {}).get(tool_lower, {})

    # Live cookie check via auto_correction_engine
    try:
        from iabv_v15.services.auto_correction_engine import (
            check_web_session_health,
        )
        health = check_web_session_health(tool_lower)
    except Exception:
        health = {
            'provider': tool_lower,
            'status': 'unknown',
            'expires_hint': None,
            'needs_human': False,
            'reason': 'Health check unavailable',
        }

    last_refresh = entry.get('last_refresh_utc')
    last_email = entry.get('account_email', '')
    refresh_count = entry.get('refresh_count', 0)

    return {
        'tool': tool_lower,
        'session_status': health.get('status', 'unknown'),
        'needs_human': health.get('needs_human', False),
        'expires_hint': health.get('expires_hint'),
        'reason': health.get('reason', ''),
        'last_refresh_utc': last_refresh,
        'account_email': last_email,
        'refresh_count': refresh_count,
    }


def record_web_session_refresh(tool: str, account_email: str) -> None:
    """Record that a web session was refreshed (user re-logged in)."""
    tool_lower = tool.lower().replace('-', '_')
    state = _load_web_session_state()
    sessions = state.setdefault('sessions', {})
    entry = sessions.get(tool_lower, {})
    entry['last_refresh_utc'] = datetime.now(timezone.utc).isoformat()
    entry['account_email'] = account_email
    entry['refresh_count'] = entry.get('refresh_count', 0) + 1
    sessions[tool_lower] = entry
    _save_web_session_state(state)
    logger.info(
        'web_session_refresh: %s refreshed for %s (count=%d)',
        tool_lower, account_email, entry['refresh_count'],
    )


# ──────────────────────────────────────────────────────────────
# Fix 32: Account↔Session Cross-Reference
# ──────────────────────────────────────────────────────────────

def verify_account_sessions() -> dict[str, Any]:
    """Cross-reference browser accounts with detected tool sessions.

    For each account email found in browser profiles, check which tool
    sessions (ChatGPT, Claude, Codex, GitHub) exist in the SAME browser
    profile.  This tells the orchestrator: "account X has an active
    ChatGPT session in Chrome Default — we can route queries through it."
    """
    accounts = scan_browser_accounts()
    sessions = scan_browser_sessions()

    # Index sessions by (browser, profile) for fast lookup
    session_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for s in sessions.get('sessions', []):
        key = (s.get('browser', ''), s.get('profile', ''))
        session_index.setdefault(key, []).append(s)

    verified: list[dict[str, Any]] = []
    for acc in accounts.get('accounts', []):
        browser = acc.get('browser', '')
        profile = acc.get('profile', '')
        email = acc.get('email', '')
        full_name = acc.get('full_name', '')
        key = (browser, profile)
        profile_sessions = session_index.get(key, [])

        tools_access: list[dict[str, Any]] = []
        tools_available: list[str] = []
        for tool_name in ('chatgpt', 'claude', 'codex', 'github'):
            matching = [s for s in profile_sessions if s.get('tool') == tool_name]
            has_session = len(matching) > 0
            tools_access.append({
                'tool': tool_name,
                'has_session': has_session,
                'cookie_count': sum(s.get('cookie_count', 0) for s in matching),
            })
            if has_session:
                tools_available.append(tool_name)

        verified.append({
            'email': email,
            'full_name': full_name,
            'browser': browser,
            'profile': profile,
            'tools': tools_access,
            'tools_available': tools_available,
            'tool_count': len(tools_available),
        })

    # Fix 38: For browsers with sessions but NO detected Google accounts,
    # create anonymous workers so the pool doesn't miss active sessions.
    matched_profiles = {(acc.get('browser', ''), acc.get('profile', '')) for acc in accounts.get('accounts', [])}
    for (browser, profile), profile_sessions in session_index.items():
        if (browser, profile) in matched_profiles:
            continue
        # This browser/profile has sessions but no Google account detected
        tools_access = []
        tools_available = []
        for tool_name in ('chatgpt', 'claude', 'codex', 'github'):
            matching = [s for s in profile_sessions if s.get('tool') == tool_name]
            has_session = len(matching) > 0
            tools_access.append({
                'tool': tool_name,
                'has_session': has_session,
                'cookie_count': sum(s.get('cookie_count', 0) for s in matching),
            })
            if has_session:
                tools_available.append(tool_name)

        if tools_available:
            verified.append({
                'email': f'(sesion activa en {browser})',
                'full_name': '',
                'browser': browser,
                'profile': profile,
                'tools': tools_access,
                'tools_available': tools_available,
                'tool_count': len(tools_available),
            })

    # Summary: which tools have at least one account with an active session
    tools_with_accounts: dict[str, list[str]] = {}
    for v in verified:
        for t in v['tools_available']:
            tools_with_accounts.setdefault(t, []).append(v['email'])

    return {
        'accounts': verified,
        'account_count': len(verified),
        'tools_with_accounts': tools_with_accounts,
        'total_sessions_found': sessions.get('session_count', 0),
    }


# ──────────────────────────────────────────────────────────────
# Fix 33: Worker Pool Estimation
# ──────────────────────────────────────────────────────────────

def estimate_available_workers() -> dict[str, Any]:
    """Build a worker pool: accounts with sessions + remaining free messages.

    Each "worker" is an account+tool pair that has:
    1. An active session (cookies detected)
    2. Free messages remaining (not exhausted in the quota window)

    The orchestrator calls this to decide how to distribute tasks.
    """
    verified = verify_account_sessions()
    all_quota = get_all_quota_status()

    # Build quota lookup by (tool, email)
    quota_lookup: dict[str, dict[str, Any]] = {}
    for s in all_quota.get('statuses', []):
        key = f"{s['tool']}:{s['email']}"
        quota_lookup[key] = s

    workers: list[dict[str, Any]] = []
    exhausted_workers: list[dict[str, Any]] = []

    for acc in verified.get('accounts', []):
        email = acc['email']
        for tool_info in acc.get('tools', []):
            tool = tool_info['tool']
            if not tool_info['has_session']:
                continue

            # Check quota status
            quota_key = f"{tool}:{email}"
            quota = quota_lookup.get(quota_key)
            limits = _FREE_TIER_LIMITS.get(tool, {})
            max_msgs = limits.get('messages_per_window', 999)

            if quota:
                remaining = quota['remaining']
                exhausted = quota['exhausted']
                used = quota['used_in_window']
            else:
                # No tracking data yet — assume full quota available
                remaining = max_msgs
                exhausted = False
                used = 0

            worker = {
                'email': email,
                'full_name': acc.get('full_name', ''),
                'tool': tool,
                'browser': acc['browser'],
                'profile': acc['profile'],
                'remaining_messages': remaining,
                'used_in_window': used,
                'limit': max_msgs,
                'window_hours': limits.get('window_hours', 3),
                'exhausted': exhausted,
                'label': limits.get('label', tool),
                'resets_at': quota.get('resets_at') if quota else None,
            }

            if exhausted:
                exhausted_workers.append(worker)
            else:
                workers.append(worker)

    # Sort available workers by remaining messages (most available first)
    workers.sort(key=lambda w: w['remaining_messages'], reverse=True)

    # Group available workers by tool
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for w in workers:
        by_tool.setdefault(w['tool'], []).append(w)

    total_remaining = sum(w['remaining_messages'] for w in workers)

    return {
        'workers': workers,
        'exhausted': exhausted_workers,
        'available_count': len(workers),
        'exhausted_count': len(exhausted_workers),
        'by_tool': by_tool,
        'total_remaining_messages': total_remaining,
        'tools_available': list(by_tool.keys()),
    }


def format_worker_pool_report() -> str:
    """Human-readable report of the worker pool for chat UI."""
    pool = estimate_available_workers()
    lines: list[str] = ['== POOL DE ASISTENTES DISPONIBLES ==', '']

    if not pool['workers'] and not pool['exhausted']:
        lines.append('No hay asistentes con sesión activa detectados.')
        lines.append('Para activar asistentes, inicia sesión en ChatGPT, Claude o Codex')
        lines.append('en cualquier navegador (Chrome, Edge, Opera, Firefox, Brave, Vivaldi).')
        return '\n'.join(lines)

    if pool['workers']:
        lines.append(f"Asistentes disponibles ({pool['available_count']}):")
        for tool, tool_workers in pool['by_tool'].items():
            label = _FREE_TIER_LIMITS.get(tool, {}).get('label', tool.upper())
            lines.append(f'\n  {label}:')
            for w in tool_workers:
                name = w.get('full_name', '')
                email_label = f"{name} <{w['email']}>" if name else w['email']
                lines.append(
                    f"    [{w['remaining_messages']}/{w['limit']} msgs] "
                    f"{email_label} — [{w['browser']}] {w['profile']}"
                )
        lines.append(f"\nCapacidad total: {pool['total_remaining_messages']} mensajes disponibles")
    else:
        lines.append('Todos los asistentes están agotados.')

    if pool['exhausted']:
        lines.append(f"\nAgotados ({pool['exhausted_count']}):")
        for w in pool['exhausted']:
            reset = f" — se reactiva: {w['resets_at']}" if w.get('resets_at') else ''
            lines.append(f"  {w['tool'].upper()}: {w['email']}{reset}")

    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────
# Account Inventory Snapshot — formal typed snapshot
# ──────────────────────────────────────────────────────────────

def build_inventory_snapshot(
    *,
    block_signals: dict[str, list[str]] | None = None,
) -> 'AccountInventorySnapshot':
    """Build a formal ``AccountInventorySnapshot`` from live scanner data.

    Composes ``verify_account_sessions``, ``get_all_quota_status``, and
    ``rank_workers_for_target`` into a single typed contract that Control
    Master, PortableContext and the UI can consume directly.

    The ``continuity_queue`` is the ranked subset of non-exhausted entries
    sorted by composite score (quota × block risk).  The first entry is
    the recommended next account.  **No account is used without explicit
    user approval.**
    """
    from iabv_v15.domain.models import (
        AccountInventoryEntry,
        AccountInventorySnapshot,
        AccountStatus,
        AccountType,
        utc_now,
    )

    pool = estimate_available_workers()
    all_quota = get_all_quota_status()

    # Build quota lookup
    quota_lookup: dict[str, dict[str, Any]] = {}
    for s in all_quota.get('statuses', []):
        quota_lookup[f"{s['tool']}:{s['email']}"] = s

    entries: list[AccountInventoryEntry] = []
    now = utc_now()

    # Process all workers (available + exhausted)
    all_workers = [*pool.get('workers', []), *pool.get('exhausted', [])]
    for w in all_workers:
        email = w.get('email', '')
        tool = w.get('tool', '')
        exhausted = w.get('exhausted', False)
        remaining = w.get('remaining_messages', 0)
        limit = w.get('limit', 0)

        resets_at = None
        if w.get('resets_at'):
            try:
                resets_at = datetime.fromisoformat(str(w['resets_at']))
            except (ValueError, TypeError):
                pass

        # Determine status
        if exhausted:
            status = AccountStatus.EXHAUSTED
        elif remaining > 0:
            status = AccountStatus.ACTIVE
        else:
            status = AccountStatus.UNRESOLVED

        unresolved: list[str] = []
        quota_key = f"{tool}:{email}"
        if quota_key not in quota_lookup:
            unresolved.append(
                'UNRESOLVED:quota_never_tracked — cuota real desconocida'
            )

        entry = AccountInventoryEntry(
            email=email,
            browser=w.get('browser', ''),
            profile=w.get('profile', ''),
            tool=tool,
            has_session=True,
            session_verified_at=now,
            quota_remaining=remaining,
            quota_limit=limit,
            quota_resets_at=resets_at,
            exhausted=exhausted,
            account_type=AccountType.UNKNOWN,
            block_signals=[],
            score=0.0,
            status=status,
            unresolved=unresolved,
            metadata={
                'full_name': w.get('full_name', ''),
                'window_hours': w.get('window_hours', 0),
                'label': w.get('label', ''),
                'used_in_window': w.get('used_in_window', 0),
            },
        )
        entries.append(entry)

    # Compute scores via ranking engine (reuses existing block signal logic)
    scored_workers = rank_workers_for_target(
        '', pool=pool, block_signals=block_signals,
    )
    score_lookup: dict[str, float] = {}
    risk_lookup: dict[str, list[str]] = {}
    for sw in scored_workers:
        key = f"{sw['tool']}:{sw['email']}:{sw.get('browser', '')}:{sw.get('profile', '')}"
        score_lookup[key] = sw.get('score', 0.0)
        # Gather active block signals for this worker
        if block_signals:
            resolved = _resolve_worker_signals(sw, block_signals)
            if resolved:
                risk_lookup[key] = resolved

    # Apply scores and block signals to entries
    for entry in entries:
        key = f"{entry.tool}:{entry.email}:{entry.browser}:{entry.profile}"
        entry.score = score_lookup.get(key, 0.0)
        if key in risk_lookup:
            entry.block_signals = risk_lookup[key]

    # Build continuity queue: non-exhausted, sorted by score desc
    continuity_queue = sorted(
        [e for e in entries if e.status == AccountStatus.ACTIVE],
        key=lambda e: e.score,
        reverse=True,
    )

    # Aggregate counts
    active_count = sum(1 for e in entries if e.status == AccountStatus.ACTIVE)
    exhausted_count = sum(1 for e in entries if e.status == AccountStatus.EXHAUSTED)
    expired_count = sum(1 for e in entries if e.status == AccountStatus.EXPIRED)
    unresolved_count = sum(1 for e in entries if e.status == AccountStatus.UNRESOLVED)
    total_remaining = sum(e.quota_remaining for e in entries if not e.exhausted)
    tools_available = sorted(set(e.tool for e in entries if e.status == AccountStatus.ACTIVE))

    # Aggregate universal resource counts (for generic external resources)
    resource_count = len(entries)  # Total count of all resources (accounts + generic)
    resource_by_type: dict[str, int] = {}
    resource_by_provider: dict[str, int] = {}
    resource_by_health: dict[str, int] = {}
    resource_by_availability: dict[str, int] = {}

    for e in entries:
        # Count by resource type
        rtype = e.resource_type or "account"
        resource_by_type[rtype] = resource_by_type.get(rtype, 0) + 1

        # Count by provider
        provider = e.provider_name or e.tool or "unknown"
        resource_by_provider[provider] = resource_by_provider.get(provider, 0) + 1

        # Count by health state
        health = e.health_state or "unknown"
        resource_by_health[health] = resource_by_health.get(health, 0) + 1

        # Count by availability state
        availability = e.availability_state or "unknown"
        resource_by_availability[availability] = resource_by_availability.get(availability, 0) + 1

    # Collect all unresolved items
    all_unresolved: list[str] = []
    for e in entries:
        all_unresolved.extend(e.unresolved)
    all_unresolved.append(
        'UNRESOLVED:visible_account_state_requires_user_permission'
    )

    return AccountInventorySnapshot(
        entries=entries,
        continuity_queue=continuity_queue,
        scanned_at=now,
        active_count=active_count,
        exhausted_count=exhausted_count,
        expired_count=expired_count,
        unresolved_count=unresolved_count,
        total_remaining_messages=total_remaining,
        tools_available=tools_available,
        resource_count=resource_count,
        resource_by_type=resource_by_type,
        resource_by_provider=resource_by_provider,
        resource_by_health=resource_by_health,
        resource_by_availability=resource_by_availability,
        unresolved_items=list(dict.fromkeys(all_unresolved)),
    )


# ──────────────────────────────────────────────────────────────
# Worker Ranking — score and sort workers for a target assistant
# ──────────────────────────────────────────────────────────────

# Known block-signal weights.  Each signal penalises the worker score.
# Values closer to 1.0 mean the signal is a harder block.
# Unknown signals default to ``_DEFAULT_SIGNAL_WEIGHT``.
_BLOCK_SIGNAL_WEIGHTS: dict[str, float] = {
    'no_disponible': 0.80,
    'wrong_thread': 0.40,
    'awaiting_response': 0.30,
    'capture_unverified': 0.20,
    'rate_limited': 0.60,
    'auth_expired': 0.90,
}
_DEFAULT_SIGNAL_WEIGHT = 0.30
_MAX_BLOCK_RISK = 0.95


def _resolve_worker_signals(
    worker: dict[str, Any],
    block_signals: dict[str, list[str]],
) -> list[str]:
    """Find the most specific signal list that matches *worker*.

    Lookup order (most-specific first):
      1. ``email:tool``   — e.g. ``"user@t.com:chatgpt"``
      2. ``browser:profile:tool`` — e.g. ``"Chrome:Default:chatgpt"``
      3. ``tool``          — e.g. ``"chatgpt"``  (backward-compatible)

    The first key that exists in *block_signals* wins; there is no merging
    across levels.  All keys are compared lower-case.
    """
    tool = str(worker.get('tool', '')).strip().lower()
    email = str(worker.get('email', '')).strip().lower()
    browser = str(worker.get('browser', '')).strip().lower()
    profile = str(worker.get('profile', '')).strip().lower()

    # Normalise block_signals keys once
    norm: dict[str, list[str]] = {k.strip().lower(): v for k, v in block_signals.items()}

    # 1. email:tool
    if email and tool:
        key = f"{email}:{tool}"
        if key in norm:
            return norm[key]

    # 2. browser:profile:tool
    if browser and profile and tool:
        key = f"{browser}:{profile}:{tool}"
        if key in norm:
            return norm[key]

    # 3. tool (fallback — original behaviour)
    return norm.get(tool, [])


def _compute_block_risk(
    worker: dict[str, Any],
    block_signals: dict[str, list[str]] | None,
) -> float:
    """Return a block-risk penalty in [0.0, ``_MAX_BLOCK_RISK``].

    *block_signals* maps a **key** to a list of active signal names.
    Keys are resolved with per-worker granularity via
    :func:`_resolve_worker_signals` (email:tool → browser:profile:tool
    → tool fallback).

    Hook: callers can inject any signal name.  Unknown names receive
    ``_DEFAULT_SIGNAL_WEIGHT`` so new signals degrade gracefully.
    """
    if not block_signals:
        return 0.0
    signals = _resolve_worker_signals(worker, block_signals)
    if not signals:
        return 0.0
    # Complementary product: risk = 1 - ∏(1 - weight_i)
    survival = 1.0
    for sig in signals:
        weight = _BLOCK_SIGNAL_WEIGHTS.get(sig, _DEFAULT_SIGNAL_WEIGHT)
        survival *= (1.0 - weight)
    risk = 1.0 - survival
    return min(round(risk, 4), _MAX_BLOCK_RISK)


def _score_worker(
    worker: dict[str, Any],
    *,
    block_signals: dict[str, list[str]] | None = None,
) -> float:
    """Compute a composite score for a single worker.

    score = quota_ratio × (1 - block_risk)

    - quota_ratio:  remaining_messages / limit  (0.0 .. 1.0)
    - block_risk:   penalty derived from active block signals for
                    the worker's tool (0.0 .. 0.95)

    Workers with ``exhausted=True`` always score 0.0.
    Returns a float in [0.0, 1.0].  Higher is better.
    """
    if worker.get('exhausted', True):
        return 0.0
    limit = max(worker.get('limit', 1), 1)
    remaining = max(worker.get('remaining_messages', 0), 0)
    quota_ratio = min(remaining / limit, 1.0)
    block_risk = _compute_block_risk(worker, block_signals)
    return round(quota_ratio * (1.0 - block_risk), 4)


def rank_workers_for_target(
    target_assistant: str,
    *,
    pool: dict[str, Any] | None = None,
    block_signals: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Rank available workers for *target_assistant* by composite score.

    Parameters
    ----------
    target_assistant:
        Tool name to filter by (e.g. ``'chatgpt'``, ``'claude'``,
        ``'codex'``).  Case-insensitive.  Empty string returns all.
    pool:
        Pre-computed pool from ``estimate_available_workers()``.
        If ``None``, a fresh scan is performed.
    block_signals:
        Optional dict mapping tool name (lower-case) to a list of active
        block signal names.  Signals penalise the composite score so
        blocked workers rank lower.

    Returns
    -------
    list of dicts, each with the original worker fields plus ``'score'``
    and ``'block_risk'``, sorted descending by score.  Exhausted workers
    are excluded.
    """
    if pool is None:
        pool = estimate_available_workers()

    target = target_assistant.strip().lower()
    workers = pool.get('workers', [])

    if target:
        candidates = [
            w for w in workers
            if str(w.get('tool', '')).strip().lower() == target
            and not w.get('exhausted', True)
        ]
    else:
        candidates = [w for w in workers if not w.get('exhausted', True)]

    scored: list[dict[str, Any]] = []
    for w in candidates:
        entry = dict(w)
        entry['block_risk'] = _compute_block_risk(w, block_signals)
        entry['score'] = _score_worker(w, block_signals=block_signals)
        scored.append(entry)

    scored.sort(key=lambda w: w['score'], reverse=True)
    return scored


def top_worker_for_target(
    target_assistant: str,
    *,
    pool: dict[str, Any] | None = None,
    block_signals: dict[str, list[str]] | None = None,
) -> dict[str, Any] | None:
    """Return the single best worker for *target_assistant*, or ``None``.

    Convenience wrapper around :func:`rank_workers_for_target`.
    """
    ranked = rank_workers_for_target(
        target_assistant, pool=pool, block_signals=block_signals,
    )
    return ranked[0] if ranked else None


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


# ──────────────────────────────────────────────────────────────
# Dual-brain intent classifier (Fix 37 + Fix 40-41)
#
# Architecture:
#   1. Patterns (0ms) — fast hardcoded check, done by caller
#   2. Local model (Ollama, ~200ms) — always available, no quotas
#   3. Cloud model (ChatGPT/Claude, ~1s) — best quality, limited
#
# Strategy:
#   - When internet + free messages available: query both in parallel
#   - Compare results; if local disagrees with cloud, save the cloud
#     answer as a training example so local learns over time
#   - When no internet or no messages: use local only (already trained)
#   - Training examples persist to data/evolution/intent_training.jsonl
# ──────────────────────────────────────────────────────────────

_INTENT_CLASSIFIER_PROMPT = """\
Eres un clasificador de intenciones para IABV, un programa de IA local.
Tu UNICA tarea: dado un mensaje del usuario, decidir a cual categoria pertenece.

CATEGORIAS:
- "account_resource": pregunta que pide LISTAR o ESCANEAR cuentas de navegador,
  sesiones activas, cuotas de mensajes, asistentes disponibles, pool de workers,
  navegadores detectados, correos. Ejemplos: "que cuentas tienes", "escanea
  navegadores", "cuantos mensajes me quedan", "que asistentes hay".
  NO incluye preguntas sobre una API key especifica o un proveedor concreto
  (groq, gemini, openrouter, ollama). Esas son "general".
- "self_awareness": pregunta sobre el estado del sistema, que es IABV, como
  funciona, auto-examen, examinate, que sabes de ti, como estas.
- "learning": pregunta sobre aprendizaje, que has aprendido, historial,
  experimentos, evidencia acumulada.
- "general": cualquier otra cosa, incluyendo preguntas sobre API keys
  especificas ("la api key de groq la esta usando?", "estas usando gemini?",
  "que modelo usas?"), conversacion, tareas, preguntas puntuales.

RESPONDE SOLO con un JSON asi (sin explicacion, sin markdown):
{"category": "account_resource", "confidence": 0.85}
"""


def _intent_training_path() -> Path:
    """Path to the intent training examples file."""
    data_dir = Path(os.environ.get('IABV_DATA_DIR', 'data'))
    training_dir = data_dir / 'evolution'
    training_dir.mkdir(parents=True, exist_ok=True)
    return training_dir / 'intent_training.jsonl'


def _load_training_examples() -> list[dict[str, str]]:
    """Load persisted training examples for the local model."""
    path = _intent_training_path()
    if not path.exists():
        return []
    examples: list[dict[str, str]] = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return examples


def _save_training_example(message: str, category: str, source: str) -> None:
    """Persist a training example from a cloud classification."""
    from datetime import datetime, timezone
    path = _intent_training_path()
    record = {
        'message': message,
        'category': category,
        'source': source,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        pass


def _build_enriched_prompt(base_prompt: str) -> str:
    """Add recent training examples to the system prompt so the local
    model learns from cloud corrections."""
    examples = _load_training_examples()
    if not examples:
        return base_prompt
    # Use last 20 examples as few-shot demonstrations
    recent = examples[-20:]
    few_shot = '\n\nEJEMPLOS DE CLASIFICACIONES CONFIRMADAS:\n'
    for ex in recent:
        few_shot += f'Mensaje: "{ex["message"]}" → {{"category": "{ex["category"]}"}}\n'
    return base_prompt + few_shot


def _query_local_model(message: str) -> dict[str, Any] | None:
    """Query the local Ollama model for intent classification."""
    base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1')
    model = os.environ.get('IABV_OLLAMA_MODEL', 'qwen3:8b')

    try:
        import httpx
    except ImportError:
        return None

    enriched_prompt = _build_enriched_prompt(_INTENT_CLASSIFIER_PROMPT)
    messages = [
        {'role': 'system', 'content': enriched_prompt},
        {'role': 'user', 'content': message},
    ]
    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
        'temperature': 0.1,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f'{base_url}/chat/completions', json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw_text = data['choices'][0]['message']['content'].strip()
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        json_match = re.search(r'\{[\s\S]*?\}', raw_text)
        if json_match:
            result = json.loads(json_match.group())
            if 'category' in result:
                result['source'] = 'local'
                return result
        return None
    except Exception as exc:
        logger.debug('local intent classifier failed: %s', exc)
        return None


def _query_cloud_model(message: str) -> dict[str, Any] | None:
    """Query a cloud model for intent classification.

    Supports OpenAI (ChatGPT) and Anthropic (Claude) with their
    respective API formats.

    Returns None if internet is unavailable, no API key, or quota exhausted.
    """
    api_key = os.environ.get('OPENAI_API_KEY', '')
    use_anthropic = False

    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if api_key:
            use_anthropic = True
        else:
            return None

    try:
        import httpx
    except ImportError:
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            if use_anthropic:
                model = 'claude-3-haiku-20240307'
                resp = client.post(
                    'https://api.anthropic.com/v1/messages',
                    json={
                        'model': model,
                        'max_tokens': 100,
                        'system': _INTENT_CLASSIFIER_PROMPT,
                        'messages': [{'role': 'user', 'content': message}],
                    },
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json',
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = ''
                for block in data.get('content', []):
                    if block.get('type') == 'text':
                        raw_text = block.get('text', '')
                        break
            else:
                model = 'gpt-4o-mini'
                resp = client.post(
                    'https://api.openai.com/v1/chat/completions',
                    json={
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': _INTENT_CLASSIFIER_PROMPT},
                            {'role': 'user', 'content': message},
                        ],
                        'stream': False,
                        'temperature': 0.1,
                        'max_tokens': 100,
                    },
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data['choices'][0]['message']['content'].strip()

        json_match = re.search(r'\{[\s\S]*?\}', raw_text)
        if json_match:
            result = json.loads(json_match.group())
            if 'category' in result:
                result['source'] = 'cloud'
                result['model'] = model
                return result
        return None
    except Exception as exc:
        logger.debug('cloud intent classifier failed: %s', exc)
        return None


def _query_web_browser_model(message: str) -> dict[str, Any] | None:
    """Query a cloud model via the user's browser sessions (CDP).

    Connects to an existing browser via Chrome DevTools Protocol, opens
    a new tab to ChatGPT or Claude, sends the classification prompt,
    reads the response, and closes the tab.

    This allows using cloud models FOR FREE via existing browser sessions
    without needing API keys.

    **Permission check**: per AGENTS.md observation policy, interacting with
    visible external windows requires explicit permission.  The env var
    ``IABV_ALLOW_BROWSER_CLASSIFIER`` must be ``1`` (set by the UI when
    the user grants permission).

    Returns ``{"category": str, "confidence": float, "source": "web_browser",
    "model": str}`` or ``None`` on failure.
    """
    if os.environ.get('IABV_ALLOW_BROWSER_CLASSIFIER', '') != '1':
        logger.debug('web_browser_classifier: skipped — IABV_ALLOW_BROWSER_CLASSIFIER not set')
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    # Check which sessions are available
    sessions = scan_browser_sessions()
    session_tools = {s.get('tool', '').lower() for s in sessions.get('sessions', [])}

    # Prefer ChatGPT, fallback to Claude
    providers = []
    if 'chatgpt' in session_tools:
        providers.append({
            'name': 'chatgpt',
            'url': 'https://chatgpt.com/',
            'input_selector': '#prompt-textarea',
            'submit_method': 'enter',
            'response_selector': '[data-message-author-role="assistant"]',
        })
    if 'claude' in session_tools:
        providers.append({
            'name': 'claude',
            'url': 'https://claude.ai/new',
            'input_selector': '[contenteditable="true"]',
            'submit_method': 'enter',
            'response_selector': '[data-testid="chat-message-content"]',
        })

    if not providers:
        return None

    cdp_url = os.environ.get('IABV_SHARED_CDP_URL', 'http://localhost:29229')
    prompt_text = (
        'Clasifica este mensaje en una categoria. '
        'Responde SOLO con JSON asi: {"category": "account_resource", "confidence": 0.85}\n'
        'Categorias: account_resource, self_awareness, learning, general.\n'
        f'Mensaje: "{message}"'
    )

    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(cdp_url)
        contexts = list(getattr(browser, 'contexts', []) or [])
        if not contexts:
            return None
        context = contexts[0]

        for provider in providers:
            page = None
            try:
                page = context.new_page()
                page.goto(provider['url'], timeout=15000)
                page.wait_for_timeout(3000)

                # Type the classification prompt
                input_el = page.query_selector(provider['input_selector'])
                if input_el is None:
                    continue

                input_el.click()
                input_el.fill(prompt_text)
                page.keyboard.press('Enter')

                # Wait for response (up to 30 seconds)
                page.wait_for_timeout(5000)
                response_el = page.query_selector_all(provider['response_selector'])
                if not response_el:
                    page.wait_for_timeout(10000)
                    response_el = page.query_selector_all(provider['response_selector'])

                if response_el:
                    # Get the last response (most recent)
                    raw_text = response_el[-1].inner_text()
                    json_match = re.search(r'\{[\s\S]*?\}', raw_text)
                    if json_match:
                        result = json.loads(json_match.group())
                        if 'category' in result:
                            result['source'] = 'web_browser'
                            result['model'] = provider['name']
                            logger.info(
                                'web_browser_classifier: %s responded category=%s',
                                provider['name'], result['category'],
                            )
                            return result
            except Exception as exc:
                logger.debug(
                    'web_browser_classifier: %s failed: %s',
                    provider['name'], exc,
                )
            finally:
                if page is not None:
                    try:
                        page.close()
                    except Exception:
                        pass

        return None
    except Exception as exc:
        logger.debug('web_browser_classifier: CDP connection failed: %s', exc)
        return None
    finally:
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass


def classify_chat_intent(message: str) -> dict[str, Any] | None:
    """Dual-brain intent classifier.

    Strategy (cascading, with parallel execution):
    1. Always query local model (Ollama) — instant, no quotas
    2. If cloud API key available → query cloud API in parallel
    3. If no API key but browser sessions exist → query via CDP/web
    4. Cloud/web wins and trains local via saved examples
    5. If only local responds, use it (enriched with past cloud examples)

    Returns ``{"category": str, "confidence": float, "source": str}``
    or ``None`` on failure.
    """
    import concurrent.futures

    local_result: dict[str, Any] | None = None
    cloud_result: dict[str, Any] | None = None

    # Check cloud availability: API key first, then browser sessions
    has_api_key = bool(
        os.environ.get('OPENAI_API_KEY')
        or os.environ.get('ANTHROPIC_API_KEY')
    )

    # Check if browser sessions are available (for web-based queries)
    has_browser_sessions = False
    if not has_api_key:
        try:
            sessions = scan_browser_sessions()
            session_tools = {
                s.get('tool', '').lower()
                for s in sessions.get('sessions', [])
            }
            has_browser_sessions = bool(
                session_tools & {'chatgpt', 'claude'}
            )
        except Exception:
            pass

    if has_api_key:
        # API key path: fastest, most reliable
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            local_future = pool.submit(_query_local_model, message)
            cloud_future = pool.submit(_query_cloud_model, message)
            try:
                local_result = local_future.result(timeout=16)
            except Exception:
                pass
            try:
                cloud_result = cloud_future.result(timeout=11)
            except Exception:
                pass
    elif has_browser_sessions:
        # Browser session path: free, uses existing logins
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            local_future = pool.submit(_query_local_model, message)
            web_future = pool.submit(_query_web_browser_model, message)
            try:
                local_result = local_future.result(timeout=16)
            except Exception:
                pass
            try:
                cloud_result = web_future.result(timeout=35)
            except Exception:
                pass
    else:
        # Local only — no cloud access
        local_result = _query_local_model(message)

    # Decision logic + Fix 44: benchmark tracking
    if cloud_result and cloud_result.get('category'):
        cloud_cat = cloud_result['category']
        local_cat = local_result.get('category') if local_result else None

        agreed = local_cat == cloud_cat
        if not agreed:
            _save_training_example(message, cloud_cat, cloud_result.get('model', 'cloud'))
            logger.info(
                'intent_dual_brain: local=%s cloud=%s → training local with cloud answer',
                local_cat, cloud_cat,
            )
        else:
            logger.debug(
                'intent_dual_brain: both agree on %s', cloud_cat,
            )

        # Record benchmark comparison for ExperimentLab consumption
        _record_classifier_benchmark(
            message=message,
            local_category=local_cat,
            cloud_category=cloud_cat,
            cloud_model=cloud_result.get('model', 'unknown'),
            local_confidence=float(local_result.get('confidence', 0)) if local_result else 0,
            cloud_confidence=float(cloud_result.get('confidence', 0)),
            agreed=agreed,
        )

        return cloud_result

    if local_result and local_result.get('category'):
        return local_result

    return None


def _classifier_benchmark_path() -> Path:
    """Path to the classifier benchmark log."""
    data_dir = Path(os.environ.get('IABV_DATA_DIR', 'data'))
    bench_dir = data_dir / 'evolution'
    bench_dir.mkdir(parents=True, exist_ok=True)
    return bench_dir / 'classifier_benchmarks.jsonl'


def _record_classifier_benchmark(
    *,
    message: str,
    local_category: str | None,
    cloud_category: str,
    cloud_model: str,
    local_confidence: float,
    cloud_confidence: float,
    agreed: bool,
) -> None:
    """Record a benchmark comparison between local and cloud classifiers.

    This data feeds into OperationalSelfExaminationService and can be
    consumed by ExperimentLab to determine which model performs best
    on IABV's cognitive metadata.
    """
    from datetime import datetime, timezone
    path = _classifier_benchmark_path()
    record = {
        'message': message[:200],
        'local_category': local_category,
        'cloud_category': cloud_category,
        'cloud_model': cloud_model,
        'local_confidence': round(local_confidence, 3),
        'cloud_confidence': round(cloud_confidence, 3),
        'agreed': agreed,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        pass


def get_classifier_benchmark_summary() -> dict[str, Any]:
    """Summarize classifier benchmark results for self-examination.

    Returns agreement rate, per-model accuracy stats, and which model
    is performing best on IABV's cognitive metadata.
    """
    path = _classifier_benchmark_path()
    if not path.exists():
        return {'total_comparisons': 0, 'agreement_rate': 0.0}

    records: list[dict[str, Any]] = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return {'total_comparisons': 0, 'agreement_rate': 0.0}

    if not records:
        return {'total_comparisons': 0, 'agreement_rate': 0.0}

    total = len(records)
    agreed = sum(1 for r in records if r.get('agreed'))
    agreement_rate = agreed / total if total > 0 else 0.0

    # Per cloud model stats
    by_model: dict[str, dict[str, int]] = {}
    for r in records:
        model = r.get('cloud_model', 'unknown')
        by_model.setdefault(model, {'total': 0, 'agreed': 0})
        by_model[model]['total'] += 1
        if r.get('agreed'):
            by_model[model]['agreed'] += 1

    model_stats = {
        model: {
            'total': stats['total'],
            'agreement_rate': round(stats['agreed'] / stats['total'], 3) if stats['total'] > 0 else 0,
        }
        for model, stats in by_model.items()
    }

    # Average confidences
    avg_local = sum(r.get('local_confidence', 0) for r in records) / total
    avg_cloud = sum(r.get('cloud_confidence', 0) for r in records) / total

    return {
        'total_comparisons': total,
        'agreement_rate': round(agreement_rate, 3),
        'avg_local_confidence': round(avg_local, 3),
        'avg_cloud_confidence': round(avg_cloud, 3),
        'model_stats': model_stats,
        'local_learning_improving': agreement_rate > 0.7,
    }


# ──────────────────────────────────────────────────────────────
# Fix 46: Auto-benchmark of available models
# ──────────────────────────────────────────────────────────────

_BENCHMARK_TEST_CASES: list[dict[str, str]] = [
    {'message': 'que cuentas tengo', 'expected': 'account_resource'},
    {'message': 'te falto las demas cuentas en los demas navegadores', 'expected': 'account_resource'},
    {'message': 'que asistentes hay disponibles', 'expected': 'account_resource'},
    {'message': 'examinate', 'expected': 'self_awareness'},
    {'message': 'como estas funcionando', 'expected': 'self_awareness'},
    {'message': 'que has aprendido hasta ahora', 'expected': 'learning'},
    {'message': 'ayudame a programar un script en python', 'expected': 'general'},
    {'message': 'cual es la capital de francia', 'expected': 'general'},
]


def run_model_benchmark() -> dict[str, Any]:
    """Benchmark all available local models on intent classification.

    Tests each Ollama model with a set of known-answer test cases to
    determine which model classifies IABV's cognitive metadata best.

    Returns a summary with per-model accuracy and the recommended model.
    """
    import time as _time
    base_url = os.environ.get('IABV_OLLAMA_BASE_URL', 'http://127.0.0.1:11434/v1')

    # Discover available models
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            resp = client.get('http://127.0.0.1:11434/api/tags')
            resp.raise_for_status()
            models = [m.get('name', '') for m in resp.json().get('models', [])]
    except Exception:
        models = [os.environ.get('IABV_OLLAMA_MODEL', 'qwen3:8b')]

    results: dict[str, dict[str, Any]] = {}

    for model_name in models:
        if not model_name or 'embedding' in model_name.lower():
            continue  # skip embedding models

        correct = 0
        total = len(_BENCHMARK_TEST_CASES)
        total_latency = 0.0
        errors = 0

        for test_case in _BENCHMARK_TEST_CASES:
            try:
                import httpx as _httpx
                start = _time.monotonic()
                messages = [
                    {'role': 'system', 'content': _INTENT_CLASSIFIER_PROMPT},
                    {'role': 'user', 'content': test_case['message']},
                ]
                payload = {
                    'model': model_name,
                    'messages': messages,
                    'stream': False,
                    'temperature': 0.1,
                }
                with _httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f'{base_url}/chat/completions', json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                elapsed = _time.monotonic() - start
                total_latency += elapsed

                raw_text = data['choices'][0]['message']['content'].strip()
                raw_text = re.sub(
                    r'<think>.*?</think>', '', raw_text, flags=re.DOTALL,
                ).strip()
                json_match = re.search(r'\{[\s\S]*?\}', raw_text)
                if json_match:
                    result = json.loads(json_match.group())
                    if result.get('category') == test_case['expected']:
                        correct += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

        accuracy = correct / total if total > 0 else 0
        avg_latency = total_latency / total if total > 0 else 0

        results[model_name] = {
            'correct': correct,
            'total': total,
            'accuracy': round(accuracy, 3),
            'avg_latency_ms': round(avg_latency * 1000),
            'errors': errors,
        }

    # Determine best model
    best_model = ''
    best_accuracy = 0.0
    for model_name, stats in results.items():
        if stats['accuracy'] > best_accuracy:
            best_accuracy = stats['accuracy']
            best_model = model_name

    # Persist benchmark results
    benchmark_result = {
        'models': results,
        'best_model': best_model,
        'best_accuracy': best_accuracy,
        'test_cases_count': len(_BENCHMARK_TEST_CASES),
    }

    from datetime import datetime, timezone
    bench_path = _classifier_benchmark_path().parent / 'model_benchmark_results.json'
    try:
        with open(bench_path, 'w', encoding='utf-8') as f:
            json.dump(
                {**benchmark_result, 'timestamp': datetime.now(timezone.utc).isoformat()},
                f, ensure_ascii=False, indent=2,
            )
        logger.info(
            'model_benchmark: best=%s accuracy=%.1f%% (%d models tested)',
            best_model, best_accuracy * 100, len(results),
        )
    except Exception:
        pass

    return benchmark_result
