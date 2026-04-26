"""API key discovery, testing, comparison and lifecycle management.

This service enables IABV to autonomously:
1. Discover which cloud reasoning providers are available (free/trial).
2. Test existing keys for validity, quota and latency.
3. Compare providers to find the best configuration.
4. Track key expiration and proactively trigger renewal.
5. Persist results so the system learns which providers work best.

Architecture notes:
- This is NOT a second orchestrator. It is a utility service consumed by
  ``CloudReasoningPlannerService`` and ``AutonomousEvolutionService``.
- Respects the Single Window Principle: when user action is needed (e.g.
  creating a key on a provider's website), it returns structured info for
  the UI to open the browser and prompt the user inline.
- Keys are saved via ``save_secret_to_profile()`` — never manually.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider catalog — free / trial tiers available for cloud reasoning
# ---------------------------------------------------------------------------

CLOUD_PROVIDERS: list[dict[str, Any]] = [
    {
        'id': 'groq',
        'name': 'Groq',
        'env_key': 'GROQ_API_KEY',
        'key_prefix': 'gsk_',
        'signup_url': 'https://console.groq.com/keys',
        'api_test_url': 'https://api.groq.com/openai/v1/chat/completions',
        'model': 'llama-3.3-70b-versatile',
        'tier': 'free',
        'daily_limit_info': '14,400 requests/day on free tier',
        'key_expiration': 'no expiration (revocable manually)',
        'strengths': 'fastest inference, free Llama 3.3 70B, low latency',
        'auth_method': 'email/Google/GitHub OAuth',
    },
    {
        'id': 'gemini',
        'name': 'Google Gemini (AI Studio)',
        'env_key': 'GEMINI_API_KEY',
        'key_prefix': 'AIza',
        'signup_url': 'https://aistudio.google.com/apikey',
        'api_test_url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
        'model': 'gemini-2.0-flash',
        'tier': 'free',
        'daily_limit_info': '1,500 requests/day on free tier',
        'key_expiration': 'no expiration (quota resets daily)',
        'strengths': 'strong reasoning, multimodal, large context window',
        'auth_method': 'Google account',
    },
    {
        'id': 'openrouter',
        'name': 'OpenRouter',
        'env_key': 'OPENROUTER_API_KEY',
        'key_prefix': 'sk-or-',
        'signup_url': 'https://openrouter.ai/keys',
        'api_test_url': 'https://openrouter.ai/api/v1/chat/completions',
        'model': 'meta-llama/llama-3.3-70b-instruct:free',
        'tier': 'free',
        'daily_limit_info': '200 requests/day on free models',
        'key_expiration': 'no expiration',
        'strengths': 'many free models, single API for multiple providers',
        'auth_method': 'email/Google/GitHub OAuth',
    },
    {
        'id': 'together',
        'name': 'Together AI',
        'env_key': 'TOGETHER_API_KEY',
        'key_prefix': '',
        'signup_url': 'https://api.together.ai/settings/api-keys',
        'api_test_url': 'https://api.together.xyz/v1/chat/completions',
        'model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
        'tier': 'trial',
        'daily_limit_info': '$5 free credits on signup',
        'key_expiration': 'credits expire after 30 days of inactivity',
        'strengths': 'fast, many open models, good free trial',
        'auth_method': 'email/Google/GitHub OAuth',
    },
]


# ---------------------------------------------------------------------------
# Key health check result
# ---------------------------------------------------------------------------

class KeyTestResult:
    __slots__ = (
        'provider_id', 'env_key', 'valid', 'latency_ms',
        'error', 'model_used', 'quota_info', 'tested_at_utc',
    )

    def __init__(
        self,
        *,
        provider_id: str,
        env_key: str,
        valid: bool = False,
        latency_ms: float = 0.0,
        error: str = '',
        model_used: str = '',
        quota_info: str = '',
    ) -> None:
        self.provider_id = provider_id
        self.env_key = env_key
        self.valid = valid
        self.latency_ms = latency_ms
        self.error = error
        self.model_used = model_used
        self.quota_info = quota_info
        self.tested_at_utc = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            'provider_id': self.provider_id,
            'env_key': self.env_key,
            'valid': self.valid,
            'latency_ms': self.latency_ms,
            'error': self.error,
            'model_used': self.model_used,
            'quota_info': self.quota_info,
            'tested_at_utc': self.tested_at_utc,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ApiKeyDiscoveryService:
    """Discovers, tests, compares and tracks API keys for cloud reasoning."""

    def __init__(self, *, data_root: str | Path = '') -> None:
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_root:
            self._data_root = Path(data_root)
        elif env_dir:
            self._data_root = Path(env_dir)
        else:
            self._data_root = Path.home() / 'IABV_v1.5' / 'data'

    # ------------------------------------------------------------------
    # 1. Discover: which providers have keys configured?
    # ------------------------------------------------------------------

    def scan_configured_keys(self) -> list[dict[str, Any]]:
        """Return info about which providers have keys set in env."""
        results: list[dict[str, Any]] = []
        for provider in CLOUD_PROVIDERS:
            env_key = provider['env_key']
            value = os.environ.get(env_key, '').strip()
            results.append({
                'provider_id': provider['id'],
                'name': provider['name'],
                'env_key': env_key,
                'configured': bool(value),
                'prefix_match': value.startswith(provider['key_prefix']) if value and provider['key_prefix'] else True,
                'signup_url': provider['signup_url'],
                'tier': provider['tier'],
                'daily_limit_info': provider['daily_limit_info'],
                'auth_method': provider['auth_method'],
            })
        return results

    def find_missing_keys(self) -> list[dict[str, Any]]:
        """Return providers that don't have a key configured yet."""
        return [p for p in self.scan_configured_keys() if not p['configured']]

    # ------------------------------------------------------------------
    # 2. Test: validate a single key with a real API call
    # ------------------------------------------------------------------

    def test_key(self, provider_id: str) -> KeyTestResult:
        """Send a minimal test request to validate a provider's key."""
        provider = next((p for p in CLOUD_PROVIDERS if p['id'] == provider_id), None)
        if provider is None:
            return KeyTestResult(
                provider_id=provider_id, env_key='',
                error=f'Unknown provider: {provider_id}',
            )

        env_key = provider['env_key']
        api_key = os.environ.get(env_key, '').strip()
        if not api_key:
            return KeyTestResult(
                provider_id=provider_id, env_key=env_key,
                error=f'{env_key} not set in environment',
            )

        try:
            import httpx
        except ImportError:
            return KeyTestResult(
                provider_id=provider_id, env_key=env_key,
                error='httpx not installed',
            )

        messages = [
            {'role': 'user', 'content': 'Respond with exactly: OK'},
        ]
        payload: dict[str, Any] = {
            'model': provider['model'],
            'messages': messages,
            'temperature': 0.0,
            'max_tokens': 5,
        }

        start = time.monotonic()
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    provider['api_test_url'],
                    json=payload,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 429:
                    return KeyTestResult(
                        provider_id=provider_id, env_key=env_key,
                        valid=True, latency_ms=elapsed_ms,
                        model_used=provider['model'],
                        quota_info='RATE_LIMITED (429) — key valid but quota exceeded',
                    )

                resp.raise_for_status()
                data = resp.json()
                model_used = data.get('model', provider['model'])

                return KeyTestResult(
                    provider_id=provider_id, env_key=env_key,
                    valid=True, latency_ms=elapsed_ms,
                    model_used=model_used,
                    quota_info='OK',
                )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            if '401' in error_msg or 'Unauthorized' in error_msg:
                error_msg = 'INVALID_KEY (401 Unauthorized)'
            elif '403' in error_msg:
                error_msg = 'FORBIDDEN (403) — key may be revoked or wrong scope'
            return KeyTestResult(
                provider_id=provider_id, env_key=env_key,
                latency_ms=elapsed_ms, error=error_msg,
            )

    # ------------------------------------------------------------------
    # 3. Compare: test all configured keys and rank them
    # ------------------------------------------------------------------

    def compare_all(self) -> list[KeyTestResult]:
        """Test all configured providers and return sorted by quality."""
        results: list[KeyTestResult] = []
        for provider in CLOUD_PROVIDERS:
            if os.environ.get(provider['env_key'], '').strip():
                result = self.test_key(provider['id'])
                results.append(result)

        results.sort(key=lambda r: (
            not r.valid,
            'RATE_LIMITED' in (r.quota_info or ''),
            r.latency_ms,
        ))
        return results

    def best_provider(self) -> KeyTestResult | None:
        """Return the best available provider after testing all."""
        results = self.compare_all()
        for r in results:
            if r.valid and 'RATE_LIMITED' not in (r.quota_info or ''):
                return r
        for r in results:
            if r.valid:
                return r
        return None

    # ------------------------------------------------------------------
    # 4. Track: persist test results for learning and monitoring
    # ------------------------------------------------------------------

    def persist_results(self, results: list[KeyTestResult]) -> Path:
        """Append test results to a JSONL log for historical tracking."""
        log_dir = self._data_root / 'evolution' / 'api_key_health'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'key_tests.jsonl'

        with open(log_path, 'a', encoding='utf-8') as f:
            batch_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            for r in results:
                entry = {**r.to_dict(), 'batch_id': batch_id}
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        logger.info('api-key-health: persisted %d results to %s', len(results), log_path)
        return log_path

    # ------------------------------------------------------------------
    # 5. Renewal guidance: structured info for UI / orchestrator
    # ------------------------------------------------------------------

    def renewal_guidance(self) -> list[dict[str, Any]]:
        """Build actionable renewal info for keys that need attention.

        Returns a list of dicts suitable for the UI to present to the user
        or for the orchestrator to create a backlog task.
        """
        guidance: list[dict[str, Any]] = []
        scan = self.scan_configured_keys()
        for item in scan:
            if not item['configured']:
                provider = next((p for p in CLOUD_PROVIDERS if p['id'] == item['provider_id']), {})
                guidance.append({
                    'action': 'create_key',
                    'provider_id': item['provider_id'],
                    'name': item['name'],
                    'env_key': item['env_key'],
                    'signup_url': item['signup_url'],
                    'auth_method': item.get('auth_method', ''),
                    'tier': item['tier'],
                    'instructions': (
                        f"1. Abrir {item['signup_url']}\n"
                        f"2. Iniciar sesion con tu cuenta ({item.get('auth_method', 'email')})\n"
                        f"3. Crear una nueva API key\n"
                        f"4. Pegar el token en IABV cuando lo pida"
                    ),
                    'daily_limit': item['daily_limit_info'],
                    'key_expiration': provider.get('key_expiration', 'unknown'),
                })

        # Check configured keys that might be failing
        for item in scan:
            if item['configured']:
                result = self.test_key(item['provider_id'])
                if not result.valid:
                    guidance.append({
                        'action': 'renew_key',
                        'provider_id': item['provider_id'],
                        'name': item['name'],
                        'env_key': item['env_key'],
                        'signup_url': item['signup_url'],
                        'error': result.error,
                        'instructions': (
                            f"La key de {item['name']} fallo: {result.error}\n"
                            f"1. Abrir {item['signup_url']}\n"
                            f"2. Revocar la key actual y crear una nueva\n"
                            f"3. Pegar la nueva key en IABV"
                        ),
                    })
                elif 'RATE_LIMITED' in (result.quota_info or ''):
                    guidance.append({
                        'action': 'wait_or_upgrade',
                        'provider_id': item['provider_id'],
                        'name': item['name'],
                        'env_key': item['env_key'],
                        'quota_info': result.quota_info,
                        'instructions': (
                            f"{item['name']} esta en rate limit. Opciones:\n"
                            f"1. Esperar a que se reinicie la cuota (generalmente diario)\n"
                            f"2. Usar otro proveedor mientras tanto\n"
                            f"3. Considerar un plan de pago si es critico"
                        ),
                    })

        return guidance

    # ------------------------------------------------------------------
    # 6. Full health report: combine everything
    # ------------------------------------------------------------------

    def full_health_report(self) -> dict[str, Any]:
        """Run a complete health check and return structured results."""
        scan = self.scan_configured_keys()
        configured = [s for s in scan if s['configured']]
        missing = [s for s in scan if not s['configured']]

        test_results = self.compare_all()
        self.persist_results(test_results)

        best = None
        for r in test_results:
            if r.valid and 'RATE_LIMITED' not in (r.quota_info or ''):
                best = r
                break

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_providers': len(CLOUD_PROVIDERS),
            'configured_count': len(configured),
            'missing_count': len(missing),
            'configured': [s['provider_id'] for s in configured],
            'missing': [{'id': s['provider_id'], 'name': s['name'], 'url': s['signup_url']} for s in missing],
            'test_results': [r.to_dict() for r in test_results],
            'best_provider': best.to_dict() if best else None,
            'recommendation': (
                f"Usar {best.provider_id} ({best.latency_ms:.0f}ms)" if best
                else "No hay proveedor funcional. Configurar al menos GROQ_API_KEY."
            ),
            'renewal_needed': [
                r.to_dict() for r in test_results
                if not r.valid or 'RATE_LIMITED' in (r.quota_info or '')
            ],
        }
