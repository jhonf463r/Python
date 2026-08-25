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
        'id': 'openai',
        'name': 'OpenAI (ChatGPT)',
        'env_key': 'OPENAI_API_KEY',
        'key_prefix': 'sk-',
        'signup_url': 'https://platform.openai.com/api-keys',
        'api_test_url': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4o',
        'tier': 'paid',
        'daily_limit_info': 'Depends on payment plan',
        'key_expiration': 'no expiration (revocable manually)',
        'strengths': 'state-of-the-art reasoning, multimodal, large context window',
        'auth_method': 'OpenAI account',
    },
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
            'max_tokens': 2,
        }
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    provider['api_test_url'],
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                return KeyTestResult(
                    provider_id=provider_id,
                    env_key=env_key,
                    valid=True,
                    latency_ms=latency_ms,
                    model_used=provider['model'],
                    quota_info='Not exposed by test endpoint',
                )
        except httpx.HTTPStatusError as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return KeyTestResult(
                provider_id=provider_id,
                env_key=env_key,
                latency_ms=latency_ms,
                error=f'HTTP {exc.response.status_code}: {exc.response.text[:200]}',
                valid=False,
            )
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return KeyTestResult(
                provider_id=provider_id,
                env_key=env_key,
                latency_ms=latency_ms,
                error='Request timeout after 10s',
                valid=False,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return KeyTestResult(
                provider_id=provider_id,
                env_key=env_key,
                latency_ms=latency_ms,
                error=str(exc)[:200],
                valid=False,
            )

    # ------------------------------------------------------------------
    # 3. Compare: test all configured keys and rank by latency
    # ------------------------------------------------------------------

    def compare_all_configured(self) -> dict[str, Any]:
        """Test all configured keys and return ranking."""
        configured = [p for p in self.scan_configured_keys() if p['configured']]
        if not configured:
            return {
                'summary': 'No cloud providers configured',
                'tested': [],
                'recommended': None,
            }

        results: list[dict[str, Any]] = []
        for provider in configured:
            test_result = self.test_key(provider['provider_id'])
            results.append({
                **provider,
                'valid': test_result.valid,
                'latency_ms': test_result.latency_ms,
                'error': test_result.error,
                'tested_at_utc': test_result.tested_at_utc,
            })

        # Sort valid by latency
        valid_results = [r for r in results if r['valid']]
        if valid_results:
            valid_results.sort(key=lambda x: x['latency_ms'])
            recommended = valid_results[0]
        else:
            recommended = None

        return {
            'summary': f'Tested {len(results)} provider(s), {len(valid_results)} valid',
            'tested': results,
            'recommended': recommended,
        }

    # ------------------------------------------------------------------
    # 4. Persist: save test results for learning
    # ------------------------------------------------------------------

    def save_test_results(self, results: dict[str, Any]) -> None:
        """Persist test results to data/evolution/autonomous_tasks/api_key_management.json."""
        audit_path = self._data_root / 'evolution' / 'autonomous_tasks' / 'api_key_management.json'
        audit_path.parent.mkdir(parents=True, exist_ok=True)

        existing: list[dict[str, Any]] = []
        if audit_path.exists():
            try:
                existing = json.loads(audit_path.read_text(encoding='utf-8'))
            except Exception:
                pass

        entry = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'results': results,
        }
        existing.append(entry)

        audit_path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
        logger.info('API key test results persisted to %s', audit_path)

    # ------------------------------------------------------------------
    # 5. Lifecycle: check for expiring keys (placeholder)
    # ------------------------------------------------------------------

    def check_key_expiration(self) -> list[dict[str, Any]]:
        """Check for keys that need renewal."""
        # Most free/trial keys don't expire automatically
        # This is a placeholder for future expansion
        return []
