"""Full System Metacognition — inventario inteligente del ecosistema completo.

Este modulo implementa metacognicion COMPLETA: el programa sabe TODO lo que
tiene disponible en el sistema, con configuraciones optimas para cada caso.

Escanea:
- Navegadores instalados + perfiles + cuentas + extensiones
- Programas instalados (registro Windows + winget + filesystem)
- Modelos de IA disponibles + configuracion optima por tarea
- GPU/CPU/RAM y configuracion optima de inferencia
- Herramientas de desarrollo + configuracion

Cada elemento detectado incluye:
- Estado: instalado / corriendo / logueado / configurado
- Configuracion actual vs optima
- Mejor uso recomendado por tipo de tarea
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_ACCOUNT_EMAIL_RE = re.compile(r'(^.).*(@.*$)')


def _safe_account_label(value: str) -> str:
    cleaned = str(value or '').strip()
    if not cleaned:
        return ''
    if '@' not in cleaned:
        return cleaned[:2] + '***' if len(cleaned) > 2 else '***'
    return _ACCOUNT_EMAIL_RE.sub(r'\1***\2', cleaned)


# ──────────────────────────────────────────────────────────────
# 1. BROWSER DEEP SCAN
# ──────────────────────────────────────────────────────────────

def scan_installed_browsers() -> list[dict[str, Any]]:
    """Detect ALL installed browsers, their profiles, accounts, and config."""
    browsers: list[dict[str, Any]] = []
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    appdata = os.environ.get('APPDATA', '')
    program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')

    browser_defs = [
        {
            'name': 'Google Chrome',
            'id': 'chrome',
            'exe_paths': [
                Path(program_files) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(program_files_x86) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(local_appdata) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            ],
            'profile_root': Path(local_appdata) / 'Google' / 'Chrome' / 'User Data',
            'process_name': 'chrome.exe',
        },
        {
            'name': 'Microsoft Edge',
            'id': 'edge',
            'exe_paths': [
                Path(program_files) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
                Path(program_files_x86) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            ],
            'profile_root': Path(local_appdata) / 'Microsoft' / 'Edge' / 'User Data',
            'process_name': 'msedge.exe',
        },
        {
            'name': 'Mozilla Firefox',
            'id': 'firefox',
            'exe_paths': [
                Path(program_files) / 'Mozilla Firefox' / 'firefox.exe',
                Path(program_files_x86) / 'Mozilla Firefox' / 'firefox.exe',
            ],
            'profile_root': Path(appdata) / 'Mozilla' / 'Firefox' / 'Profiles',
            'process_name': 'firefox.exe',
        },
        {
            'name': 'Brave',
            'id': 'brave',
            'exe_paths': [
                Path(program_files) / 'BraveSoftware' / 'Brave-Browser' / 'Application' / 'brave.exe',
                Path(local_appdata) / 'BraveSoftware' / 'Brave-Browser' / 'Application' / 'brave.exe',
            ],
            'profile_root': Path(local_appdata) / 'BraveSoftware' / 'Brave-Browser' / 'User Data',
            'process_name': 'brave.exe',
        },
        {
            'name': 'Opera',
            'id': 'opera',
            'exe_paths': [
                Path(program_files) / 'Opera' / 'opera.exe',
                Path(local_appdata) / 'Programs' / 'Opera' / 'opera.exe',
            ],
            'profile_root': Path(appdata) / 'Opera Software' / 'Opera Stable',
            'process_name': 'opera.exe',
        },
        {
            'name': 'Vivaldi',
            'id': 'vivaldi',
            'exe_paths': [
                Path(local_appdata) / 'Vivaldi' / 'Application' / 'vivaldi.exe',
            ],
            'profile_root': Path(local_appdata) / 'Vivaldi' / 'User Data',
            'process_name': 'vivaldi.exe',
        },
    ]

    for bdef in browser_defs:
        installed = False
        exe_found = None
        for exe in bdef['exe_paths']:
            if exe.exists():
                installed = True
                exe_found = str(exe)
                break

        profile_root = bdef['profile_root']
        profiles = _scan_browser_profiles(profile_root, bdef['id'])

        # Check if running
        running = _is_process_running(bdef['process_name'])

        browser_info: dict[str, Any] = {
            'name': bdef['name'],
            'id': bdef['id'],
            'installed': installed,
            'exe_path': exe_found,
            'running': running,
            'profile_root': str(profile_root) if profile_root.exists() else None,
            'profiles': profiles,
            'profile_count': len(profiles),
            'accounts_detected': sum(1 for p in profiles if p.get('accounts')),
            'extensions_count': sum(len(p.get('extensions', [])) for p in profiles),
        }

        # Only include if installed or has profile data
        if installed or profile_root.exists():
            browsers.append(browser_info)

    return browsers


def _scan_browser_profiles(profile_root: Path, browser_id: str) -> list[dict[str, Any]]:
    """Scan browser profile directories for accounts and extensions."""
    profiles: list[dict[str, Any]] = []
    if not profile_root.exists():
        return profiles

    if browser_id == 'firefox':
        # Firefox uses profiles.ini
        for entry in profile_root.iterdir():
            if entry.is_dir():
                profile: dict[str, Any] = {
                    'name': entry.name,
                    'path': str(entry),
                    'accounts': [],
                    'extensions': [],
                }
                # Check logins.json for saved accounts
                logins_file = entry / 'logins.json'
                if logins_file.exists():
                    try:
                        logins_data = json.loads(logins_file.read_text(encoding='utf-8', errors='replace'))
                        for login in logins_data.get('logins', []):
                            hostname = login.get('hostname', '')
                            if hostname:
                                profile['accounts'].append({
                                    'site': hostname,
                                    'has_saved_login': True,
                                    'secret_extracted': False,
                                })
                    except Exception:
                        pass
                profiles.append(profile)
    else:
        # Chromium-based (Chrome, Edge, Brave, Opera, Vivaldi)
        profile_dirs = ['Default']
        for entry in profile_root.iterdir():
            if entry.is_dir() and entry.name.startswith('Profile '):
                profile_dirs.append(entry.name)

        for pdir_name in profile_dirs:
            pdir = profile_root / pdir_name
            if not pdir.exists():
                continue

            profile = {
                'name': pdir_name,
                'path': str(pdir),
                'accounts': [],
                'extensions': [],
                'preferences': {},
            }

            # Read Preferences for account info
            prefs_file = pdir / 'Preferences'
            if prefs_file.exists():
                try:
                    prefs = json.loads(prefs_file.read_text(encoding='utf-8', errors='replace'))
                    # Google account info
                    account_info = prefs.get('account_info', [])
                    for acc in account_info:
                        email = str(acc.get('email') or '')
                        profile['accounts'].append({
                            'email_label': _safe_account_label(email),
                            'full_name_label': _safe_account_label(str(acc.get('full_name') or '')),
                            'type': 'google' if 'google' in acc.get('email', '').lower() or '@gmail' in acc.get('email', '') else 'microsoft' if 'outlook' in acc.get('email', '').lower() or 'hotmail' in acc.get('email', '').lower() else 'other',
                            'secret_extracted': False,
                        })
                    # Check for AI-related extensions
                    extensions = prefs.get('extensions', {}).get('settings', {})
                    for ext_id, ext_data in extensions.items():
                        if isinstance(ext_data, dict):
                            manifest = ext_data.get('manifest', {})
                            ext_name = manifest.get('name', ext_data.get('name', ''))
                            if ext_name and not ext_name.startswith('__'):
                                profile['extensions'].append({
                                    'id': ext_id,
                                    'name': ext_name,
                                    'version': manifest.get('version', ''),
                                })
                    # GPU acceleration config
                    profile['preferences']['hardware_acceleration'] = prefs.get('hardware_acceleration', {}).get('enabled', True) if isinstance(prefs.get('hardware_acceleration'), dict) else True
                except Exception:
                    pass

            profiles.append(profile)

    return profiles


def build_safe_session_presence(browsers: list[dict[str, Any]], ai_ecosystem: dict[str, Any]) -> dict[str, Any]:
    assistant_domains = {
        'chatgpt': ['chatgpt.com', 'openai.com'],
        'claude': ['claude.ai', 'anthropic.com'],
        'gemini': ['gemini.google.com', 'bard.google.com'],
        'copilot': ['copilot.microsoft.com', 'github.com'],
        'devin': ['app.devin.ai', 'devin.ai'],
    }
    detected: dict[str, list[dict[str, Any]]] = {kind: [] for kind in assistant_domains}
    for browser in browsers:
        for profile in browser.get('profiles') or []:
            account_sites = [
                str(account.get('site') or '').lower()
                for account in (profile.get('accounts') or [])
                if account.get('has_saved_login')
            ]
            for kind, domains in assistant_domains.items():
                if any(domain in site for domain in domains for site in account_sites):
                    detected[kind].append(
                        {
                            'browser_id': browser.get('id', ''),
                            'profile_name': profile.get('name', ''),
                            'presence': 'saved_login_hint',
                            'secret_extracted': False,
                        }
                    )
    actions: list[dict[str, Any]] = []
    cloud_assistants = ai_ecosystem.get('cloud_assistants') if isinstance(ai_ecosystem, dict) else []
    for assistant in cloud_assistants or []:
        kind = str(assistant.get('kind') or '').strip().lower()
        if not kind:
            continue
        has_presence = bool(detected.get(kind))
        actions.append(
            {
                'assistant_kind': kind,
                'recommended_route': 'use_existing_session' if has_presence else 'request_login_or_api_key',
                'approval_required': not has_presence,
                'safe_automation_boundary': 'no_passwords_no_cookies_no_tokens_extracted',
            }
        )
    return {
        'detected_session_hints': detected,
        'recommended_actions': actions,
        'secret_policy': 'presence_only_no_cookie_password_or_token_extraction',
        'unresolved_fields': [
            'UNRESOLVED:visible_account_state_requires_user_permission',
        ],
    }


# ──────────────────────────────────────────────────────────────
# 2. INSTALLED PROGRAMS SCAN
# ──────────────────────────────────────────────────────────────

def scan_installed_programs() -> list[dict[str, Any]]:
    """Detect ALL installed programs via Windows registry + winget."""
    programs: list[dict[str, Any]] = []

    # Method 1: Windows Registry
    try:
        import winreg
        uninstall_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]
        seen_names: set[str] = set()
        for hkey, subkey in uninstall_keys:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as app_key:
                                name = _reg_value(app_key, 'DisplayName')
                                if name and name not in seen_names:
                                    seen_names.add(name)
                                    programs.append({
                                        'name': name,
                                        'version': _reg_value(app_key, 'DisplayVersion') or '',
                                        'publisher': _reg_value(app_key, 'Publisher') or '',
                                        'install_location': _reg_value(app_key, 'InstallLocation') or '',
                                        'source': 'registry',
                                    })
                        except OSError:
                            break
                        i += 1
            except OSError:
                pass
    except ImportError:
        # Not on Windows, try alternative
        pass

    # Method 2: winget list (supplement)
    try:
        result = subprocess.run(
            ['winget', 'list', '--accept-source-agreements', '--disable-interactivity'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Parse winget output (skip header lines)
            for line in lines[4:]:  # Skip header
                parts = line.strip()
                if parts and len(parts) > 10:
                    # winget list format varies, just capture the line
                    name = parts.split('  ')[0].strip() if '  ' in parts else parts[:50]
                    if name and name not in {p['name'] for p in programs}:
                        programs.append({
                            'name': name,
                            'source': 'winget',
                        })
    except Exception:
        pass

    return programs


def _reg_value(key: Any, name: str) -> str | None:
    """Read a registry value safely."""
    try:
        import winreg
        value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip() if value else None
    except (OSError, ImportError):
        return None


# ──────────────────────────────────────────────────────────────
# 3. AI MODELS & CONFIGURATION SCAN
# ──────────────────────────────────────────────────────────────

def scan_ai_ecosystem() -> dict[str, Any]:
    """Scan all AI models and their optimal configurations."""
    ecosystem: dict[str, Any] = {
        'local_models': [],
        'cloud_assistants': [],
        'task_routing': {},
    }

    # 3a. Ollama models with detailed info
    try:
        result = subprocess.run(
            ['ollama', 'list'], capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    model_name = parts[0]
                    model_id = parts[1] if len(parts) > 1 else ''
                    size = parts[2] + ' ' + parts[3] if len(parts) > 3 else ''

                    # Get model details
                    model_info = _get_ollama_model_info(model_name)

                    ecosystem['local_models'].append({
                        'name': model_name,
                        'id': model_id,
                        'size': size,
                        'details': model_info,
                        'optimal_config': _get_optimal_config(model_name, model_info),
                    })
    except Exception as exc:
        logger.warning('ollama list failed: %s', exc)

    # 3b. Check ollama ps for currently loaded models
    try:
        result = subprocess.run(
            ['ollama', 'ps'], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            ecosystem['loaded_models'] = result.stdout.strip()
    except Exception:
        pass

    # 3c. Cloud assistants awareness
    ecosystem['cloud_assistants'] = [
        {
            'name': 'ChatGPT',
            'kind': 'chatgpt',
            'models_available': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            'best_for': ['general_qa', 'creative_writing', 'code_explanation'],
            'config_recommendations': {
                'temperature': {'coding': 0.2, 'creative': 0.8, 'analysis': 0.3},
                'max_tokens': {'coding': 4096, 'creative': 2048, 'analysis': 4096},
            },
            'access_method': 'web_browser',
            'login_required': True,
        },
        {
            'name': 'Claude',
            'kind': 'claude',
            'models_available': ['claude-3.5-sonnet', 'claude-3-opus', 'claude-3-haiku'],
            'best_for': ['code_review', 'debugging', 'language_understanding', 'long_context'],
            'config_recommendations': {
                'temperature': {'coding': 0.1, 'creative': 0.7, 'analysis': 0.2},
                'max_tokens': {'coding': 4096, 'creative': 2048, 'analysis': 8192},
            },
            'access_method': 'web_browser',
            'login_required': True,
        },
        {
            'name': 'Codex (OpenAI)',
            'kind': 'codex',
            'best_for': ['code_generation', 'code_completion', 'refactoring'],
            'access_method': 'desktop_app',
            'login_required': True,
        },
        {
            'name': 'Devin',
            'kind': 'devin',
            'best_for': ['autonomous_coding', 'full_stack_development', 'ci_cd'],
            'access_method': 'api',
            'login_required': True,
        },
    ]

    # 3d. Task routing recommendations
    ecosystem['task_routing'] = {
        'code_generation': {
            'primary': 'codex',
            'fallback': 'qwen2.5-coder:7b (local)',
            'reason': 'Codex tiene perfil de codigo especializado; qwen2.5-coder es el mejor local para codigo',
            'local_config': {'temperature': 0.2, 'num_ctx': 8192, 'gpu_layers': -1},
        },
        'code_review': {
            'primary': 'claude',
            'fallback': 'qwen2.5-coder:7b (local)',
            'reason': 'Claude excede en comprension profunda de codigo y deteccion de bugs',
            'local_config': {'temperature': 0.1, 'num_ctx': 8192, 'gpu_layers': -1},
        },
        'debugging': {
            'primary': 'claude',
            'fallback': 'qwen3:8b (local)',
            'reason': 'Claude analiza stack traces y razona sobre flujo de ejecucion mejor',
            'local_config': {'temperature': 0.1, 'num_ctx': 4096, 'gpu_layers': -1},
        },
        'explanation': {
            'primary': 'chatgpt',
            'fallback': 'gemma3:4b (local)',
            'reason': 'ChatGPT explica conceptos de forma clara y accesible',
            'local_config': {'temperature': 0.5, 'num_ctx': 4096, 'gpu_layers': -1},
        },
        'creative_writing': {
            'primary': 'chatgpt',
            'fallback': 'qwen3:8b (local)',
            'reason': 'ChatGPT tiene mejor creatividad y variedad de estilos',
            'local_config': {'temperature': 0.8, 'num_ctx': 4096, 'gpu_layers': -1},
        },
        'quick_local_query': {
            'primary': 'gemma3:4b (local)',
            'fallback': None,
            'reason': 'Mas rapido (~50 tok/s en RTX 4050), cabe completo en 6GB VRAM',
            'local_config': {'temperature': 0.3, 'num_ctx': 4096, 'gpu_layers': -1},
        },
        'complex_reasoning': {
            'primary': 'qwen3:8b (local)',
            'fallback': 'claude',
            'reason': 'qwen3:8b tiene mejor razonamiento, pero OJO: 5.95GB puede causar CPU fallback parcial en 6GB VRAM',
            'local_config': {'temperature': 0.2, 'num_ctx': 4096, 'gpu_layers': -1},
            'warning': 'MODEL_TOO_LARGE_SILENT_CPU_FALLBACK: 5.95GB modelo en 6GB VRAM = 61%/39% CPU/GPU split',
        },
    }

    return ecosystem


def _get_ollama_model_info(model_name: str) -> dict[str, Any]:
    """Get detailed model info from ollama show."""
    try:
        result = subprocess.run(
            ['ollama', 'show', model_name],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            info: dict[str, Any] = {'raw': result.stdout[:500]}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, _, val = line.partition(':')
                    key = key.strip().lower().replace(' ', '_')
                    val = val.strip()
                    if key in ('parameters', 'quantization', 'family', 'parameter_size', 'context_length'):
                        info[key] = val
            return info
    except Exception:
        pass
    return {}


def _get_optimal_config(model_name: str, model_info: dict[str, Any]) -> dict[str, Any]:
    """Determine optimal configuration for a model based on available hardware."""
    config: dict[str, Any] = {
        'gpu_layers': -1,  # use all GPU layers by default
        'num_ctx': 4096,
    }

    name_lower = model_name.lower()

    # Size-based recommendations for RTX 4050 (6GB VRAM)
    if 'gemma3' in name_lower and '4b' in name_lower:
        config.update({
            'fits_in_vram': True,
            'expected_tps': '~50 tok/s',
            'best_for': ['quick_queries', 'simple_code', 'chat'],
            'temperature_default': 0.3,
            'num_ctx': 4096,
        })
    elif 'qwen2.5-coder' in name_lower and '7b' in name_lower:
        config.update({
            'fits_in_vram': True,
            'expected_tps': '~30 tok/s',
            'best_for': ['code_generation', 'code_review', 'refactoring'],
            'temperature_default': 0.2,
            'num_ctx': 8192,
        })
    elif 'qwen3' in name_lower and '8b' in name_lower:
        config.update({
            'fits_in_vram': False,
            'warning': 'MODEL_TOO_LARGE_SILENT_CPU_FALLBACK',
            'detail': '5.95GB model on 6GB VRAM = silent 61%/39% CPU/GPU split',
            'expected_tps': '~15-25 tok/s (degraded)',
            'best_for': ['complex_reasoning', 'analysis'],
            'temperature_default': 0.2,
            'num_ctx': 4096,
            'recommendation': 'Use gemma3:4b or qwen2.5-coder:7b for better GPU performance',
        })

    return config


# ──────────────────────────────────────────────────────────────
# 4. DEV TOOLS SCAN
# ──────────────────────────────────────────────────────────────

def scan_dev_tools() -> list[dict[str, Any]]:
    """Scan development tools and their configurations."""
    tools: list[dict[str, Any]] = []

    tool_checks = [
        ('git', ['git', '--version'], {'best_for': 'version_control'}),
        ('gh', ['gh', '--version'], {'best_for': 'github_operations'}),
        ('python', [sys.executable, '--version'], {'best_for': 'scripting'}),
        ('node', ['node', '--version'], {'best_for': 'javascript_runtime'}),
        ('npm', ['npm', '--version'], {'best_for': 'package_management'}),
        ('docker', ['docker', '--version'], {'best_for': 'containerization'}),
        ('pip', [sys.executable, '-m', 'pip', '--version'], {'best_for': 'python_packages'}),
        ('conda', ['conda', '--version'], {'best_for': 'python_env_management'}),
        ('cloudflared', ['cloudflared', '--version'], {'best_for': 'tunneling'}),
        ('winget', ['winget', '--version'], {'best_for': 'windows_package_management'}),
        ('ollama', ['ollama', '--version'], {'best_for': 'local_llm'}),
        ('code', ['code', '--version'], {'best_for': 'code_editor'}),
        ('aider', ['aider', '--version'], {'best_for': 'ai_pair_programming'}),
    ]

    for name, cmd, meta in tool_checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            version = result.stdout.strip() or result.stderr.strip()
            tools.append({
                'name': name,
                'installed': True,
                'version': version[:100],
                'command': cmd[0],
                **meta,
            })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            tools.append({
                'name': name,
                'installed': False,
                **meta,
            })
        except Exception:
            tools.append({'name': name, 'installed': False, **meta})

    return tools


# ──────────────────────────────────────────────────────────────
# 5. MAIN REPORT
# ──────────────────────────────────────────────────────────────

def full_system_metacognition_report() -> dict[str, Any]:
    """Generate a COMPLETE metacognition report of the entire system.

    This is the "super scanner" — it inventories everything and provides
    optimal configurations for each resource.
    """
    report: dict[str, Any] = {}

    # Browsers
    try:
        report['browsers'] = scan_installed_browsers()
        report['browsers_summary'] = {
            'total_installed': sum(1 for b in report['browsers'] if b['installed']),
            'total_running': sum(1 for b in report['browsers'] if b['running']),
            'total_profiles': sum(b['profile_count'] for b in report['browsers']),
            'total_accounts': sum(b['accounts_detected'] for b in report['browsers']),
        }
    except Exception as exc:
        report['browsers'] = []
        report['browsers_error'] = str(exc)

    # AI ecosystem
    try:
        report['ai_ecosystem'] = scan_ai_ecosystem()
    except Exception as exc:
        report['ai_ecosystem'] = {}
        report['ai_ecosystem_error'] = str(exc)

    try:
        report['safe_session_presence'] = build_safe_session_presence(
            report.get('browsers', []),
            report.get('ai_ecosystem', {}),
        )
    except Exception as exc:
        report['safe_session_presence'] = {'error': str(exc)}

    # Dev tools
    try:
        report['dev_tools'] = scan_dev_tools()
        report['dev_tools_summary'] = {
            'total_installed': sum(1 for t in report['dev_tools'] if t['installed']),
            'total_checked': len(report['dev_tools']),
        }
    except Exception as exc:
        report['dev_tools'] = []
        report['dev_tools_error'] = str(exc)

    # Installed programs (from registry/winget)
    try:
        all_programs = scan_installed_programs()
        # Categorize
        ai_programs = [p for p in all_programs if any(kw in p['name'].lower() for kw in
            ['chatgpt', 'claude', 'openai', 'copilot', 'codex', 'cursor', 'windsurf',
             'ollama', 'aider', 'continue', 'codeium', 'tabnine', 'replit'])]
        browser_programs = [p for p in all_programs if any(kw in p['name'].lower() for kw in
            ['chrome', 'firefox', 'edge', 'brave', 'opera', 'vivaldi', 'safari'])]
        dev_programs = [p for p in all_programs if any(kw in p['name'].lower() for kw in
            ['visual studio', 'vscode', 'git', 'node', 'python', 'docker',
             'postman', 'jetbrains', 'intellij', 'pycharm', 'sublime', 'notepad++'])]

        report['installed_programs'] = {
            'total': len(all_programs),
            'ai_related': ai_programs,
            'browsers': browser_programs,
            'development': dev_programs,
            'all_names': sorted(set(p['name'] for p in all_programs)),
        }
    except Exception as exc:
        report['installed_programs'] = {'error': str(exc)}

    # GPU metacognition (cross-reference)
    try:
        from iabv_v15.services.gpu_metacognition import gpu_metacognition_report
        report['gpu'] = gpu_metacognition_report()
    except Exception as exc:
        report['gpu'] = {'error': str(exc)}

    # Metacognition gaps identified
    report['metacognition_gaps'] = _identify_gaps(report)

    # Save report
    try:
        data_dir = Path(os.environ.get('IABV_WORKSPACE', '.')) / 'src' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        report_path = data_dir / 'full_system_metacognition_report.json'
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        report['report_saved_to'] = str(report_path)
    except Exception:
        pass

    return report


def _identify_gaps(report: dict[str, Any]) -> list[dict[str, str]]:
    """Identify metacognition gaps based on the scan results."""
    gaps: list[dict[str, str]] = []

    # Check if browsers have accounts but program doesn't know
    browsers = report.get('browsers', [])
    for b in browsers:
        if b.get('installed') and not b.get('profiles'):
            gaps.append({
                'category': 'browser_profile_scan',
                'detail': f"{b['name']} instalado pero sin perfiles escaneados",
                'recommendation': 'Agregar escaneo de perfil para este navegador',
            })

    # Check AI ecosystem gaps
    ai = report.get('ai_ecosystem', {})
    for model in ai.get('local_models', []):
        config = model.get('optimal_config', {})
        if config.get('warning') == 'MODEL_TOO_LARGE_SILENT_CPU_FALLBACK':
            gaps.append({
                'category': 'gpu_model_fit',
                'detail': f"{model['name']}: modelo muy grande para VRAM disponible",
                'recommendation': config.get('recommendation', ''),
            })

    # Check if audit_capability only covers 1 tool
    gaps.append({
        'category': 'audit_coverage',
        'detail': 'audit_capability solo tiene registrado llm_local_ollama (1 de 18 tools)',
        'recommendation': 'Registrar audits para shell, git, playwright, etc.',
    })

    # Check synaptic_route task_kind coverage
    gaps.append({
        'category': 'routing_profiles',
        'detail': 'synaptic_route no tiene perfiles para explain_concept, debug_error (task_kind_unknown)',
        'recommendation': 'Agregar perfiles de routing para todos los task_kinds comunes',
    })

    return gaps


# ──────────────────────────────────────────────────────────────
# 6. UTILITY
# ──────────────────────────────────────────────────────────────

def _is_process_running(process_name: str) -> bool:
    """Check if a process is running by name."""
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # Fallback: use tasklist on Windows
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                capture_output=True, text=True, timeout=10,
            )
            return process_name.lower() in result.stdout.lower()
        except Exception:
            pass
    return False
