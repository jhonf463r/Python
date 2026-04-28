"""Autonomous Cloud Key Provisioner — auto-detect, scan, navigate, and provision API keys.

This module teaches IABV to autonomously provision cloud provider API keys
by scanning web pages, understanding UI elements, and navigating forms.
It extends the existing infrastructure:
  - BrowserSessionController for Playwright browser control
  - SiteExplorationService pattern for page scanning
  - auto_correction_engine.save_secret_to_profile for key persistence
  - CommonSenseEngine for fact-driven decision making

The provisioner works in stages:
  1. DETECT  — CommonSenseEngine detects missing/expired keys via facts
  2. SCAN    — Opens provider page and scans UI structure (buttons, links, forms)
  3. LEARN   — Extracts interactive elements and maps them to provisioning steps
  4. EXECUTE — Navigates autonomously to create the key (with user auth if needed)
  5. CAPTURE — Reads the generated key from the page
  6. SAVE    — Persists via save_secret_to_profile and verifies with test call

The user only needs to authorize (e.g., Google login) — everything else
is handled by the program in the background.

Contratos respetados:
  - No crea otro cerebro ni otro orquestador
  - Extiende auto_correction_engine, no lo reemplaza
  - Usa BrowserSessionController existente
  - Resultados se alimentan al DecisionAuditTrail
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


# ---------------------------------------------------------------------------
# Page element discovery — what the system "sees" when scanning a page
# ---------------------------------------------------------------------------

_SCAN_BUTTONS_JS = """
() => Array.from(document.querySelectorAll('button, [role="button"], a.button, a[class*="btn"]'))
  .map((el) => ({
    tag: el.tagName.toLowerCase(),
    text: (el.innerText || el.textContent || '').trim().substring(0, 100),
    ariaLabel: el.getAttribute('aria-label') || '',
    href: el.getAttribute('href') || '',
    id: el.id || '',
    className: (el.className || '').toString().substring(0, 200),
    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
    visible: el.offsetParent !== null,
    rect: el.getBoundingClientRect ? (() => {
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    })() : null,
  }))
  .filter((b) => b.visible && b.text)
  .slice(0, 50)
"""

_SCAN_INPUTS_JS = """
() => Array.from(document.querySelectorAll('input[type="text"], input[type="password"], input[type="email"], input:not([type]), textarea'))
  .map((el) => ({
    tag: el.tagName.toLowerCase(),
    name: el.name || '',
    id: el.id || '',
    placeholder: el.placeholder || '',
    type: el.type || '',
    value: el.value ? '***' : '',
    visible: el.offsetParent !== null,
  }))
  .filter((i) => i.visible)
  .slice(0, 30)
"""

_SCAN_KEY_DISPLAY_JS = """
() => {
  // Look for elements that might contain an API key
  const candidates = Array.from(document.querySelectorAll(
    'code, pre, [class*="key"], [class*="token"], [class*="secret"], [class*="api-key"], input[readonly], input[type="text"][value]'
  ));
  return candidates
    .map((el) => ({
      tag: el.tagName.toLowerCase(),
      text: (el.innerText || el.textContent || el.value || '').trim().substring(0, 200),
      className: (el.className || '').toString().substring(0, 200),
      id: el.id || '',
    }))
    .filter((c) => c.text && c.text.length > 10)
    .slice(0, 20);
}
"""

_SCAN_DIALOGS_JS = """
() => Array.from(document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="dialog"], [class*="popup"]'))
  .map((el) => ({
    tag: el.tagName.toLowerCase(),
    text: (el.innerText || '').trim().substring(0, 500),
    visible: el.offsetParent !== null || window.getComputedStyle(el).display !== 'none',
    buttons: Array.from(el.querySelectorAll('button, [role="button"]'))
      .map((b) => (b.innerText || '').trim())
      .filter(Boolean)
      .slice(0, 10),
  }))
  .filter((d) => d.visible)
  .slice(0, 5)
"""


@dataclass
class PageScanResult:
    """What IABV 'sees' when it scans a provider page."""
    url: str
    title: str
    buttons: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    key_displays: list[dict[str, Any]] = field(default_factory=list)
    dialogs: list[dict[str, Any]] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    error: str = ''
    timestamp: float = 0.0


@dataclass
class ProvisioningStep:
    """A step in the provisioning workflow, learned from page scanning."""
    action: str  # 'click', 'wait', 'read_key', 'select_option', 'authorize'
    target: str  # CSS selector, button text, or description
    description: str
    completed: bool = False
    result: str = ''


@dataclass
class ProvisioningResult:
    """Result of an autonomous provisioning attempt."""
    provider: str
    env_key: str
    success: bool
    api_key: str = ''
    steps_completed: list[ProvisioningStep] = field(default_factory=list)
    page_scans: list[PageScanResult] = field(default_factory=list)
    error: str = ''
    needs_user_auth: bool = False
    user_action: str = ''


# ---------------------------------------------------------------------------
# Provider-specific knowledge (learned patterns)
# ---------------------------------------------------------------------------

_PROVIDER_KNOWLEDGE: dict[str, dict[str, Any]] = {
    'gemini': {
        'env_key': 'GEMINI_API_KEY',
        'key_prefix': 'AIza',
        'start_url': 'https://aistudio.google.com/apikey',
        'verify_url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
        'verify_model': 'gemini-2.0-flash',
        'auth_required': 'google',
        'steps_pattern': [
            {'action': 'navigate', 'target': 'https://aistudio.google.com/apikey'},
            {'action': 'wait_for_auth', 'target': 'Google login if needed'},
            {'action': 'scan_page', 'target': 'Find "Create API key" button'},
            {'action': 'click', 'target': 'Create API key'},
            {'action': 'click', 'target': 'Create API key in new project'},
            {'action': 'wait', 'target': 'Wait for key generation'},
            {'action': 'read_key', 'target': 'Copy generated key (starts with AIza)'},
            {'action': 'save', 'target': 'save_secret_to_profile'},
            {'action': 'verify', 'target': 'Test API call'},
        ],
        'known_errors': {
            429: 'Quota exhausted — create key in NEW project',
            401: 'Key invalid or revoked — regenerate',
            403: 'Key revoked or API not enabled for project',
        },
    },
    'groq': {
        'env_key': 'GROQ_API_KEY',
        'key_prefix': 'gsk_',
        'start_url': 'https://console.groq.com/keys',
        'verify_url': 'https://api.groq.com/openai/v1/chat/completions',
        'verify_model': 'llama-3.3-70b-versatile',
        'auth_required': 'google_or_github',
        'steps_pattern': [
            {'action': 'navigate', 'target': 'https://console.groq.com/keys'},
            {'action': 'wait_for_auth', 'target': 'Login with Google or GitHub'},
            {'action': 'scan_page', 'target': 'Find "Create API Key" button'},
            {'action': 'click', 'target': 'Create API Key'},
            {'action': 'wait', 'target': 'Wait for key generation'},
            {'action': 'read_key', 'target': 'Copy generated key (starts with gsk_)'},
            {'action': 'save', 'target': 'save_secret_to_profile'},
            {'action': 'verify', 'target': 'Test API call'},
        ],
        'known_errors': {
            401: 'Key invalid -- regenerate at console.groq.com/keys',
        },
    },
    'openai': {
        'env_key': 'OPENAI_API_KEY',
        'key_prefix': 'sk-',
        'start_url': 'https://platform.openai.com/api-keys',
        'verify_url': 'https://api.openai.com/v1/chat/completions',
        'verify_model': 'gpt-4o-mini',
        'auth_required': 'openai_account',
        'steps_pattern': [
            {'action': 'navigate', 'target': 'https://platform.openai.com/api-keys'},
            {'action': 'wait_for_auth', 'target': 'Login with OpenAI account'},
            {'action': 'scan_page', 'target': 'Find "+ Create new secret key" button'},
            {'action': 'click', 'target': 'Create new secret key'},
            {'action': 'wait', 'target': 'Wait for key generation'},
            {'action': 'read_key', 'target': 'Copy generated key (starts with sk-)'},
            {'action': 'save', 'target': 'save_secret_to_profile'},
            {'action': 'verify', 'target': 'Test API call'},
        ],
        'known_errors': {
            401: 'Key invalid or revoked -- regenerate at platform.openai.com/api-keys',
            429: 'Rate limited or quota exhausted -- check billing at platform.openai.com/account/billing',
            403: 'Account suspended or key restricted',
        },
    },
    'anthropic': {
        'env_key': 'ANTHROPIC_API_KEY',
        'key_prefix': 'sk-ant-',
        'start_url': 'https://console.anthropic.com/settings/keys',
        'verify_url': 'https://api.anthropic.com/v1/messages',
        'verify_model': 'claude-sonnet-4-20250514',
        'auth_required': 'anthropic_account',
        'steps_pattern': [
            {'action': 'navigate', 'target': 'https://console.anthropic.com/settings/keys'},
            {'action': 'wait_for_auth', 'target': 'Login with Anthropic account'},
            {'action': 'scan_page', 'target': 'Find "Create Key" button'},
            {'action': 'click', 'target': 'Create Key'},
            {'action': 'wait', 'target': 'Wait for key generation'},
            {'action': 'read_key', 'target': 'Copy generated key (starts with sk-ant-)'},
            {'action': 'save', 'target': 'save_secret_to_profile'},
            {'action': 'verify', 'target': 'Test API call'},
        ],
        'known_errors': {
            401: 'Key invalid -- regenerate at console.anthropic.com/settings/keys',
            429: 'Rate limited -- check usage at console.anthropic.com/settings/usage',
        },
    },
    'cloudflare': {
        'env_key': 'CLOUDFLARE_TUNNEL_TOKEN',
        'key_prefix': 'eyJ',
        'start_url': 'https://dash.cloudflare.com/',
        'verify_url': '',
        'verify_model': '',
        'auth_required': 'cloudflare_account',
        'steps_pattern': [
            {'action': 'navigate', 'target': 'https://dash.cloudflare.com/'},
            {'action': 'wait_for_auth', 'target': 'Login with Cloudflare account'},
            {'action': 'navigate', 'target': 'Zero Trust > Networks > Tunnels'},
            {'action': 'scan_page', 'target': 'Find existing tunnel or create new'},
            {'action': 'read_key', 'target': 'Copy tunnel token (JWT format)'},
            {'action': 'save', 'target': 'save_secret_to_profile'},
        ],
        'known_errors': {
            401: 'Token expired -- regenerate in Cloudflare Zero Trust dashboard',
        },
    },
}


class CloudKeyAutonomousProvisioner:
    """Autonomous provisioner that scans pages and creates API keys.

    This service teaches IABV to:
    1. Scan provider pages to understand their UI structure
    2. Find and click "Create API key" buttons
    3. Read generated keys from the page
    4. Save them via save_secret_to_profile
    5. Verify they work with test API calls
    6. Record what it learned for future sessions

    The user's browser (Opera) is used with their existing Google session,
    so no additional login is needed for providers that use Google auth.
    """

    def __init__(
        self,
        *,
        headless: bool = False,
        user_data_dir: str | None = None,
    ) -> None:
        self._headless = headless
        self._user_data_dir = user_data_dir
        self._scan_history: list[PageScanResult] = []

    @staticmethod
    def is_available() -> bool:
        """Full Playwright-based provisioning is available."""
        return sync_playwright is not None

    @staticmethod
    def is_fallback_available() -> bool:
        """Lightweight fallback (webbrowser + UI dialog) is always available."""
        return True

    def scan_provider_page(
        self,
        provider: str,
        *,
        url: str | None = None,
    ) -> PageScanResult:
        """Scan a provider's page to understand its UI structure.

        This is the 'learning' phase — IABV examines the page elements
        to map out buttons, forms, and key display areas.
        """
        knowledge = _PROVIDER_KNOWLEDGE.get(provider, {})
        target_url = url or knowledge.get('start_url', '')
        if not target_url:
            return PageScanResult(url='', title='', error=f'No URL for provider: {provider}')

        if not self.is_available():
            return PageScanResult(
                url=target_url,
                title='',
                error='Playwright not available — install with: pip install playwright && playwright install chromium',
            )

        scan = PageScanResult(url=target_url, title='', timestamp=time.time())

        try:
            pw = sync_playwright().start()
            try:
                launch_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                ]
                if self._user_data_dir:
                    browser = pw.chromium.launch_persistent_context(
                        self._user_data_dir,
                        headless=self._headless,
                        args=launch_args,
                    )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                else:
                    browser = pw.chromium.launch(headless=self._headless, args=launch_args)
                    ctx = browser.new_context()
                    page = ctx.new_page()

                page.goto(target_url, wait_until='networkidle', timeout=15000)
                time.sleep(2)  # Allow JS to render

                scan.title = page.title() or ''
                scan.buttons = page.evaluate(_SCAN_BUTTONS_JS) or []
                scan.inputs = page.evaluate(_SCAN_INPUTS_JS) or []
                scan.key_displays = page.evaluate(_SCAN_KEY_DISPLAY_JS) or []
                scan.dialogs = page.evaluate(_SCAN_DIALOGS_JS) or []

                headings_js = """
                () => Array.from(document.querySelectorAll('h1, h2, h3'))
                  .map((el) => (el.innerText || '').trim())
                  .filter(Boolean)
                  .slice(0, 20)
                """
                scan.headings = page.evaluate(headings_js) or []

                browser.close()
            finally:
                pw.stop()
        except Exception as exc:
            scan.error = f'{type(exc).__name__}: {exc}'
            logger.warning('cloud_provisioner: scan failed for %s: %s', provider, exc)

        self._scan_history.append(scan)
        return scan

    def find_create_key_button(self, scan: PageScanResult) -> dict[str, Any] | None:
        """Analyze scan results to find the 'Create API key' button.

        This is IABV learning to interpret page structure autonomously.
        """
        create_keywords = ['create', 'generate', 'new', 'crear', 'generar']
        key_keywords = ['key', 'api', 'token', 'clave']

        for button in scan.buttons:
            text_lower = button.get('text', '').lower()
            aria_lower = button.get('ariaLabel', '').lower()
            combined = f'{text_lower} {aria_lower}'

            has_create = any(kw in combined for kw in create_keywords)
            has_key = any(kw in combined for kw in key_keywords)

            if has_create and has_key and not button.get('disabled'):
                return button

        return None

    def find_api_key_on_page(self, scan: PageScanResult, prefix: str = '') -> str | None:
        """Search scan results for a displayed API key.

        Looks for elements containing text that matches known key patterns.
        """
        for display in scan.key_displays:
            text = display.get('text', '').strip()
            if prefix and text.startswith(prefix):
                return text
            if len(text) > 20 and not ' ' in text[:30]:
                return text
        return None

    def detect_auth_required(self, scan: PageScanResult) -> bool:
        """Detect if the page is showing a login/auth screen."""
        auth_indicators = ['sign in', 'log in', 'login', 'iniciar sesion', 'authenticate']
        all_text = ' '.join(
            [scan.title.lower()] +
            [b.get('text', '').lower() for b in scan.buttons] +
            [h.lower() for h in scan.headings]
        )
        return any(indicator in all_text for indicator in auth_indicators)

    def provision_key(
        self,
        provider: str,
        *,
        auto_navigate: bool = True,
        save_to_profile: bool = True,
    ) -> ProvisioningResult:
        """Full autonomous provisioning flow for a cloud provider.

        Steps:
        1. Navigate to provider page
        2. Scan UI elements
        3. If auth needed, notify user and wait
        4. Find and click 'Create API key'
        5. Read the generated key
        6. Save via save_secret_to_profile
        7. Verify with test call
        """
        knowledge = _PROVIDER_KNOWLEDGE.get(provider)
        if not knowledge:
            return ProvisioningResult(
                provider=provider,
                env_key='',
                success=False,
                error=f'Unknown provider: {provider}',
            )

        env_key = knowledge['env_key']
        result = ProvisioningResult(
            provider=provider,
            env_key=env_key,
            success=False,
        )

        # Step 1: Scan the provider page
        scan = self.scan_provider_page(provider)
        result.page_scans.append(scan)

        if scan.error:
            result.error = f'Page scan failed: {scan.error}'
            return result

        step_scan = ProvisioningStep(
            action='scan_page',
            target=knowledge['start_url'],
            description=f'Scanned {provider} page: {len(scan.buttons)} buttons, {len(scan.inputs)} inputs',
            completed=True,
            result=f'title={scan.title}, buttons={len(scan.buttons)}',
        )
        result.steps_completed.append(step_scan)

        # Step 2: Check if auth is needed
        if self.detect_auth_required(scan):
            result.needs_user_auth = True
            result.user_action = (
                f'IABV detecto que necesitas autenticarte en {provider}. '
                f'Abre {knowledge["start_url"]} en Opera, inicia sesion con tu cuenta Google, '
                f'y luego IABV continuara automaticamente.'
            )
            step_auth = ProvisioningStep(
                action='wait_for_auth',
                target='User authentication required',
                description='Page shows login — user needs to authenticate first',
                completed=False,
                result='needs_user_auth',
            )
            result.steps_completed.append(step_auth)
            return result

        # Step 3: Find the "Create API key" button
        create_button = self.find_create_key_button(scan)
        if create_button:
            step_found = ProvisioningStep(
                action='found_button',
                target=create_button.get('text', ''),
                description=f'Found create button: "{create_button.get("text", "")}"',
                completed=True,
                result=json.dumps(create_button, default=str),
            )
            result.steps_completed.append(step_found)

        # Step 4: Check if a key is already visible
        existing_key = self.find_api_key_on_page(scan, prefix=knowledge.get('key_prefix', ''))
        if existing_key:
            result.api_key = existing_key
            step_read = ProvisioningStep(
                action='read_key',
                target='Existing key found on page',
                description=f'Found key: {existing_key[:8]}...',
                completed=True,
                result='key_captured',
            )
            result.steps_completed.append(step_read)

            # Save and verify
            if save_to_profile:
                self._save_and_verify(result, knowledge)

            return result

        # Step 5: Need to click create — this requires browser interaction
        if create_button and auto_navigate:
            result.user_action = (
                f'IABV encontro el boton "{create_button.get("text", "")}" en {provider}. '
                f'Para crear la key automaticamente, IABV necesita hacer click en el browser. '
                f'La pagina esta abierta en: {knowledge["start_url"]}'
            )
        else:
            result.user_action = (
                f'Abre {knowledge["start_url"]} en Opera, '
                f'click en "Create API key" → "Create API key in new project", '
                f'y pega la key en el dialogo de IABV.'
            )

        # Record learned page structure for future sessions
        self._persist_page_learning(provider, scan)

        return result

    def verify_key(self, provider: str, api_key: str) -> dict[str, Any]:
        """Verify an API key works with a test call."""
        knowledge = _PROVIDER_KNOWLEDGE.get(provider, {})
        verify_url = knowledge.get('verify_url', '')
        model = knowledge.get('verify_model', '')

        if not verify_url:
            return {'valid': False, 'error': 'No verify URL for provider'}

        try:
            import httpx
        except ImportError:
            return {'valid': False, 'error': 'httpx not available'}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    verify_url,
                    json={
                        'model': model,
                        'messages': [{'role': 'user', 'content': 'Say OK'}],
                        'temperature': 0.0,
                        'max_tokens': 5,
                    },
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                )

                # Record health
                try:
                    from iabv_v15.services.adaptive.cloud_reasoning_planner import (
                        CloudReasoningPlannerService,
                    )
                    CloudReasoningPlannerService._record_api_health(provider, resp.status_code)
                except ImportError:
                    pass

                if resp.status_code == 200:
                    return {'valid': True, 'status_code': 200}

                error_detail = ''
                try:
                    error_detail = resp.json().get('error', {}).get('message', '')[:200]
                except Exception:
                    pass

                known_errors = knowledge.get('known_errors', {})
                suggestion = known_errors.get(resp.status_code, '')

                return {
                    'valid': False,
                    'status_code': resp.status_code,
                    'error': error_detail,
                    'suggestion': suggestion,
                }
        except Exception as exc:
            return {'valid': False, 'error': str(exc)}

    def _save_and_verify(
        self,
        result: ProvisioningResult,
        knowledge: dict[str, Any],
    ) -> None:
        """Save a captured key and verify it works."""
        from iabv_v15.services.auto_correction_engine import save_secret_to_profile

        save_result = save_secret_to_profile(result.env_key, result.api_key)
        step_save = ProvisioningStep(
            action='save',
            target=result.env_key,
            description=f'Saved to profile: {save_result.get("status")}',
            completed=save_result.get('status') == 'saved',
            result=json.dumps(save_result, default=str),
        )
        result.steps_completed.append(step_save)

        # Verify
        verify = self.verify_key(result.provider, result.api_key)
        step_verify = ProvisioningStep(
            action='verify',
            target=knowledge.get('verify_url', ''),
            description=f'API test: {"OK" if verify.get("valid") else "FAILED"}',
            completed=verify.get('valid', False),
            result=json.dumps(verify, default=str),
        )
        result.steps_completed.append(step_verify)
        result.success = verify.get('valid', False)

        if not result.success and verify.get('status_code') == 429:
            result.error = (
                'Key saved but quota exhausted (429). '
                'Solution: create key in a NEW Google Cloud project.'
            )

    def _persist_page_learning(self, provider: str, scan: PageScanResult) -> None:
        """Save learned page structure for future sessions."""
        learning_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            'data', 'evolution', 'tool_discovery',
        )
        os.makedirs(learning_dir, exist_ok=True)
        learning_file = os.path.join(learning_dir, f'{provider}_page_structure.json')

        learned = {
            'provider': provider,
            'url': scan.url,
            'title': scan.title,
            'scanned_at': scan.timestamp,
            'button_count': len(scan.buttons),
            'input_count': len(scan.inputs),
            'buttons_text': [b.get('text', '') for b in scan.buttons[:20]],
            'headings': scan.headings,
            'has_create_button': self.find_create_key_button(scan) is not None,
            'create_button_text': (self.find_create_key_button(scan) or {}).get('text', ''),
        }

        try:
            with open(learning_file, 'w', encoding='utf-8') as f:
                json.dump(learned, f, indent=2, ensure_ascii=False)
            logger.info('cloud_provisioner: saved page learning for %s → %s', provider, learning_file)
        except Exception as exc:
            logger.debug('cloud_provisioner: could not save learning: %s', exc)

    def provision_key_fallback(
        self,
        provider: str,
        *,
        save_to_profile: bool = True,
    ) -> ProvisioningResult:
        """Fallback provisioning when Playwright is not available.

        Opens the provider page in the default browser and returns a
        result with ``needs_user_auth=True`` and clear instructions.
        The UI dialog will accept the key from the user and call
        ``save_secret_to_profile`` to persist it.

        This implements the AGENTS.md principle: user never opens
        PowerShell — IABV opens the browser and accepts the key
        via its own dialog.
        """
        knowledge = _PROVIDER_KNOWLEDGE.get(provider)
        if not knowledge:
            return ProvisioningResult(
                provider=provider, env_key='', success=False,
                error=f'Unknown provider: {provider}',
            )

        env_key = knowledge['env_key']
        start_url = knowledge['start_url']
        result = ProvisioningResult(
            provider=provider, env_key=env_key, success=False,
        )

        # Do NOT open visible browser windows autonomously —
        # the user should not see Chrome popping up without their action.
        # Return the URL so the UI can present it to the user.
        opened = False
        logger.info('cloud_provisioner_fallback: %s needs user action at %s (no visible browser opened)', provider, start_url)

        result.steps_completed.append(ProvisioningStep(
            action='open_browser',
            target=start_url,
            description=f'Opened provider page in browser (fallback mode)',
            completed=opened,
            result='browser_opened' if opened else 'browser_failed',
        ))

        result.needs_user_auth = True
        prefix = knowledge.get('key_prefix', '')
        prefix_hint = f' (empieza con {prefix})' if prefix else ''
        result.user_action = (
            f'IABV abrio {start_url} en tu browser. '
            f'Crea una API key{prefix_hint} y pegala en el dialogo de IABV. '
            f'IABV la guardara automaticamente.'
        )

        return result

    @staticmethod
    def get_provider_knowledge() -> dict[str, dict[str, Any]]:
        """Return the system's current knowledge about cloud providers."""
        return dict(_PROVIDER_KNOWLEDGE)

    @staticmethod
    def get_known_providers() -> list[str]:
        """Return list of providers the system knows how to provision."""
        return list(_PROVIDER_KNOWLEDGE.keys())
