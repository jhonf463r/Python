"""Adaptive model selector: auto-selects the best model (cloud or local)
based on observed latency, error rates, and task type.

Architecture note: this is NOT a new brain or orchestrator. It extends the
existing SynapticRouter + ExperimentLab + DecisionAuditTrail chain to make
model selection data-driven rather than hardcoded.

Flow:
1. Before each inference, ``select_best_provider()`` is called
2. It reads recent performance from DecisionAuditTrail
3. Scores each available provider by: latency, success rate, quota status
4. Returns the best provider for the current task type
5. After inference, the result feeds back via DecisionAuditTrail

The selector also detects degradation patterns:
- Model responding too slowly (latency > 2x baseline)
- Quota exhaustion (429 errors)
- Repeated failures on same provider
- Local model underperforming vs cloud baseline
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

# Provider performance thresholds
_SLOW_LATENCY_MS = 8000.0  # > 8s is "slow"
_VERY_SLOW_LATENCY_MS = 15000.0  # > 15s triggers auto-switch
_MIN_SUCCESS_RATE = 0.5  # below 50% success = degraded
_QUOTA_COOLDOWN_SECONDS = 3600  # 1h cooldown after quota exhaustion
_HISTORY_WINDOW = 20  # last N decisions to consider
_LOW_QUOTA_THRESHOLD = 5  # warn when remaining messages < this


class ProviderScore:
    """Scoring for a single provider based on recent performance."""

    __slots__ = (
        'provider_id', 'available', 'avg_latency_ms', 'success_rate',
        'recent_errors', 'quota_exhausted', 'last_used_ts', 'total_score',
        'reason',
    )

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        self.available = True
        self.avg_latency_ms = 0.0
        self.success_rate = 1.0
        self.recent_errors: list[str] = []
        self.quota_exhausted = False
        self.last_used_ts = 0.0
        self.total_score = 0.0
        self.reason = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'provider_id': self.provider_id,
            'available': self.available,
            'avg_latency_ms': round(self.avg_latency_ms, 1),
            'success_rate': round(self.success_rate, 3),
            'recent_errors': self.recent_errors[:3],
            'quota_exhausted': self.quota_exhausted,
            'total_score': round(self.total_score, 4),
            'reason': self.reason,
        }


class AdaptiveModelSelector:
    """Selects the best available model/provider based on live performance data.

    Does NOT replace SynapticRouter or LocalRoleRouter. Instead, it provides
    a ``select_best_provider()`` method that CloudReasoningPlannerService and
    the orchestrator can consult before making an API call.
    """

    def __init__(
        self,
        *,
        data_dir: str | Path = '',
        experiment_lab_repository: Any | None = None,
    ) -> None:
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_dir:
            self._data_dir = Path(data_dir)
        elif env_dir:
            self._data_dir = Path(env_dir)
        else:
            self._data_dir = Path.home() / 'IABV_v1.5' / 'data'
        self._experiment_lab_repository = experiment_lab_repository
        self._performance_log = self._data_dir / 'evolution' / 'model_selection' / 'performance.jsonl'
        self._performance_log.parent.mkdir(parents=True, exist_ok=True)
        self._quota_cooldowns: dict[str, float] = {}  # provider_id -> monotonic timestamp

    # ------------------------------------------------------------------
    # Core: select best provider
    # ------------------------------------------------------------------

    def select_best_provider(
        self,
        *,
        task_type: str = 'general',
        exclude: list[str] | None = None,
        world_model: Any | None = None,
    ) -> dict[str, Any]:
        """Select the best available provider for the given task type.

        Returns dict with:
        - provider_id: selected provider
        - reason: why it was selected
        - scores: all provider scores for transparency
        - fallback_chain: ordered list of providers to try
        """
        exclude_set = set(exclude or [])
        scores = self._score_all_providers(task_type, exclude_set, world_model=world_model)

        # Emit low-quota warnings before ranking
        self._check_low_quota_warnings(scores, world_model)

        # Sort by total_score descending
        ranked = sorted(scores, key=lambda s: s.total_score, reverse=True)
        available = [s for s in ranked if s.available and s.provider_id not in exclude_set]

        if not available:
            return {
                'provider_id': 'ollama_local',
                'reason': 'all_cloud_providers_unavailable_or_excluded',
                'scores': [s.to_dict() for s in ranked],
                'fallback_chain': ['ollama_local'],
                'best_account': None,
                'quota_rotation_applied': False,
            }

        selected = available[0]
        fallback_chain = [s.provider_id for s in available]
        best_account = self._best_account_for_tool(selected.provider_id, world_model)

        return {
            'provider_id': selected.provider_id,
            'reason': selected.reason,
            'scores': [s.to_dict() for s in ranked],
            'fallback_chain': fallback_chain,
            'best_account': best_account,
            'quota_rotation_applied': best_account is not None,
        }

    # ------------------------------------------------------------------
    # Record: track provider performance after each call
    # ------------------------------------------------------------------

    def record_result(
        self,
        *,
        provider_id: str,
        task_type: str = 'general',
        latency_ms: float = 0.0,
        success: bool = True,
        error: str = '',
        status_code: int = 200,
        model_used: str = '',
    ) -> None:
        """Record the result of a provider call for future scoring."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'provider_id': provider_id,
            'task_type': task_type,
            'latency_ms': round(latency_ms, 1),
            'success': success,
            'error': error[:200] if error else '',
            'status_code': status_code,
            'model_used': model_used,
        }

        # Detect quota exhaustion
        if status_code == 429 or 'quota' in error.lower() or 'rate limit' in error.lower():
            self._quota_cooldowns[provider_id] = time.monotonic()
            entry['quota_exhausted'] = True
            logger.warning(
                'adaptive_model_selector: %s quota exhausted (status=%d) — '
                'cooldown %ds, switching to next provider',
                provider_id, status_code, _QUOTA_COOLDOWN_SECONDS,
            )

        try:
            with open(self._performance_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Detect: identify slow/degraded models
    # ------------------------------------------------------------------

    def detect_degradation(self) -> list[dict[str, Any]]:
        """Detect providers that are degraded (slow, failing, quota exhausted).

        Returns list of degradation findings suitable for OSES consumption.
        """
        recent = self._read_recent_performance()
        findings: list[dict[str, Any]] = []

        by_provider: dict[str, list[dict[str, Any]]] = {}
        for entry in recent:
            pid = entry.get('provider_id', '')
            by_provider.setdefault(pid, []).append(entry)

        for pid, entries in by_provider.items():
            successes = sum(1 for e in entries if e.get('success'))
            total = len(entries)
            success_rate = successes / total if total > 0 else 1.0
            latencies = [e.get('latency_ms', 0) for e in entries if e.get('success')]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

            if avg_latency > _VERY_SLOW_LATENCY_MS:
                findings.append({
                    'provider_id': pid,
                    'type': 'very_slow',
                    'avg_latency_ms': avg_latency,
                    'recommendation': f'{pid} promedia {avg_latency:.0f}ms — considerar '
                                      f'cambiar a un modelo mas rapido o usar cloud',
                })

            if success_rate < _MIN_SUCCESS_RATE and total >= 3:
                errors = [e.get('error', '') for e in entries if not e.get('success')]
                findings.append({
                    'provider_id': pid,
                    'type': 'high_failure_rate',
                    'success_rate': success_rate,
                    'recent_errors': errors[:3],
                    'recommendation': f'{pid} tiene {success_rate:.0%} de exito — '
                                      f'verificar key, cuota o conectividad',
                })

            quota_entries = [e for e in entries if e.get('quota_exhausted')]
            if quota_entries:
                findings.append({
                    'provider_id': pid,
                    'type': 'quota_exhausted',
                    'count': len(quota_entries),
                    'recommendation': f'{pid} cuota agotada — rotar a otra cuenta o '
                                      f'esperar reset diario',
                })

        return findings

    # ------------------------------------------------------------------
    # Recommend: suggest Ollama model based on task and hardware
    # ------------------------------------------------------------------

    def recommend_local_model(
        self,
        *,
        task_type: str = 'general',
        available_models: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recommend the best local Ollama model for the task type.

        Uses heuristics based on model size and task requirements.
        """
        if not available_models:
            available_models = self._list_ollama_models()

        # Model scoring heuristics
        model_scores: list[dict[str, Any]] = []
        for model in available_models:
            score = 0.0
            reason_parts: list[str] = []
            name_lower = model.lower()

            # Size-based scoring
            if '70b' in name_lower or '20b' in name_lower:
                score += 0.3
                reason_parts.append('large_model')
            elif '7b' in name_lower or '8b' in name_lower:
                score += 0.6
                reason_parts.append('balanced_size')
            elif '4b' in name_lower or '3b' in name_lower or '1b' in name_lower:
                score += 0.8
                reason_parts.append('fast_small_model')

            # Task-type specific scoring
            if task_type in ('coding', 'code_review', 'debugging'):
                if 'coder' in name_lower or 'code' in name_lower:
                    score += 0.4
                    reason_parts.append('code_specialized')
            elif task_type in ('reasoning', 'planning', 'analysis'):
                if any(kw in name_lower for kw in ('qwen', 'llama', 'gemma')):
                    score += 0.2
                    reason_parts.append('general_reasoning')

            # Embedding models shouldn't be used for chat
            if 'embedding' in name_lower or 'embed' in name_lower:
                score = 0.0
                reason_parts = ['embedding_model_not_for_chat']

            model_scores.append({
                'model': model,
                'score': round(score, 2),
                'reason': '+'.join(reason_parts) if reason_parts else 'default',
            })

        model_scores.sort(key=lambda x: x['score'], reverse=True)

        best = model_scores[0] if model_scores else {'model': 'qwen2.5-coder:7b', 'score': 0.5, 'reason': 'default'}
        return {
            'recommended': best['model'],
            'reason': best['reason'],
            'task_type': task_type,
            'all_scores': model_scores,
        }

    # ------------------------------------------------------------------
    # Internal: scoring logic
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # WorldModel-aware checks for web and quota
    # ------------------------------------------------------------------

    def _is_web_provider_allowed(
        self,
        provider_id: str,
        world_model: Any | None,
    ) -> tuple[bool, str]:
        """Check if a web provider can be used based on WorldModel gates.

        Returns (allowed, reason).
        """
        if world_model is None:
            return False, 'no_world_model'

        gates = getattr(world_model, 'permission_gates', []) or []
        kind_map = {
            'chatgpt_web': 'chatgpt',
            'claude_web': 'claude',
            'gemini_web': 'gemini',
        }
        assistant_kind = kind_map.get(provider_id, provider_id.replace('_web', ''))

        matching_gate = None
        for gate in gates:
            if getattr(gate, 'assistant_kind', '') == assistant_kind:
                matching_gate = gate
                break

        if matching_gate is None:
            return False, 'no_permission_gate'
        if not getattr(matching_gate, 'granted', False):
            return False, 'permission_not_granted'

        return True, 'permitted'

    def _is_web_session_active(
        self,
        provider_id: str,
    ) -> tuple[bool, str]:
        """Check if the web provider has an active browser session.

        Returns (active, reason).  When the health check is unavailable
        (import error, scanner crash) the provider is allowed through
        (fail-open) so existing behaviour is preserved.
        """
        try:
            from iabv_v15.services.auto_correction_engine import (
                check_web_session_health,
            )
            health = check_web_session_health(provider_id)
        except Exception:
            return True, 'session_check_unavailable'

        status = health.get('status', 'unknown')
        if status == 'expired':
            return False, 'web_session_expired'
        return True, f'web_session_{status}'

    _TOOL_MAP: dict[str, str] = {
        'gemini': 'gemini',
        'groq': 'groq',
        'chatgpt_web': 'chatgpt',
        'claude_web': 'claude',
        'gemini_web': 'gemini',
        'openrouter': 'openrouter',
        'together': 'together',
    }

    def _is_quota_available(
        self,
        provider_id: str,
        world_model: Any | None,
    ) -> tuple[bool, str]:
        """Check if quota is available for this provider via worker_pool_snapshot.

        Returns (available, reason).
        """
        if world_model is None:
            return True, 'no_world_model_assume_available'

        pool = getattr(world_model, 'worker_pool_snapshot', {}) or {}
        tools = pool.get('tools', {})

        tool_name = self._TOOL_MAP.get(provider_id, provider_id)
        tool_info = tools.get(tool_name, {})

        if not tool_info:
            return True, 'no_quota_data_assume_available'

        usable = tool_info.get('usable', True)
        if not usable:
            return False, 'quota_exhausted'
        return True, 'quota_available'

    def _quota_remaining_for_provider(
        self,
        provider_id: str,
        world_model: Any | None,
    ) -> int | None:
        """Return remaining messages for the top worker of this provider.

        Returns ``None`` when quota data is unavailable (backward compat).
        """
        if world_model is None:
            return None
        pool = getattr(world_model, 'worker_pool_snapshot', {}) or {}
        tools = pool.get('tools', {})
        tool_name = self._TOOL_MAP.get(provider_id, provider_id)
        tool_info = tools.get(tool_name, {})
        if not tool_info:
            return None
        top = tool_info.get('top_worker')
        if top and isinstance(top, dict):
            score = top.get('score')
            if isinstance(score, (int, float)):
                return int(score)
        available = tool_info.get('available_accounts', 0)
        if available > 0:
            return None  # have accounts but no detailed score
        return 0

    def _best_account_for_tool(
        self,
        provider_id: str,
        world_model: Any | None,
    ) -> dict[str, Any] | None:
        """Return the best account for this provider from worker_pool_snapshot.

        If the primary account is exhausted but another exists, returns
        the alternative account info.  Returns ``None`` when no account
        data is available.
        """
        if world_model is None:
            return None
        pool = getattr(world_model, 'worker_pool_snapshot', {}) or {}
        tools = pool.get('tools', {})
        tool_name = self._TOOL_MAP.get(provider_id, provider_id)
        tool_info = tools.get(tool_name, {})
        if not tool_info:
            return None
        top = tool_info.get('top_worker')
        if top and isinstance(top, dict) and tool_info.get('usable'):
            return {
                'email': top.get('email', ''),
                'remaining': top.get('score', 0),
                'tool': tool_name,
            }
        return None

    def _check_low_quota_warnings(
        self,
        scores: list[ProviderScore],
        world_model: Any | None,
    ) -> None:
        """Emit WARNING logs for providers with quota below threshold."""
        if world_model is None:
            return
        pool = getattr(world_model, 'worker_pool_snapshot', {}) or {}
        tools = pool.get('tools', {})
        for ps in scores:
            if not ps.available or ps.provider_id == 'ollama_local':
                continue
            tool_name = self._TOOL_MAP.get(ps.provider_id, ps.provider_id)
            tool_info = tools.get(tool_name, {})
            if not tool_info:
                continue
            top = tool_info.get('top_worker')
            if top and isinstance(top, dict):
                remaining = top.get('score', 999)
                if isinstance(remaining, (int, float)) and remaining < _LOW_QUOTA_THRESHOLD:
                    logger.warning(
                        'adaptive_model_selector: %s has only %d messages remaining '
                        '(threshold=%d) — consider rotating account',
                        ps.provider_id, int(remaining), _LOW_QUOTA_THRESHOLD,
                    )

    # ------------------------------------------------------------------
    # Internal: scoring logic
    # ------------------------------------------------------------------

    def _score_all_providers(
        self,
        task_type: str,
        exclude: set[str],
        *,
        world_model: Any | None = None,
    ) -> list[ProviderScore]:
        """Score all known providers based on recent performance."""
        recent = self._read_recent_performance()
        now_mono = time.monotonic()

        # Group by provider
        by_provider: dict[str, list[dict[str, Any]]] = {}
        for entry in recent:
            pid = entry.get('provider_id', '')
            by_provider.setdefault(pid, []).append(entry)

        # All known providers (API cloud + web + local)
        all_providers = [
            'gemini', 'groq', 'openrouter', 'together',     # API cloud
            'chatgpt_web', 'claude_web', 'gemini_web',       # Web (browser)
            'ollama_local',                                    # Local
        ]
        scores: list[ProviderScore] = []

        for pid in all_providers:
            ps = ProviderScore(pid)
            entries = by_provider.get(pid, [])

            # --- Web providers: check permission gate + session health ---
            if pid.endswith('_web'):
                allowed, reason = self._is_web_provider_allowed(pid, world_model)
                if not allowed:
                    ps.available = False
                    ps.reason = reason
                    ps.total_score = 0.0
                    scores.append(ps)
                    continue
                # Brecha 2.3: penalize expired web sessions
                session_ok, session_reason = self._is_web_session_active(pid)
                if not session_ok:
                    ps.available = False
                    ps.reason = session_reason
                    ps.total_score = 0.0
                    scores.append(ps)
                    continue

            # --- API cloud providers: check API key ---
            elif pid != 'ollama_local':
                env_map = {
                    'gemini': 'GEMINI_API_KEY',
                    'groq': 'GROQ_API_KEY',
                    'openrouter': 'OPENROUTER_API_KEY',
                    'together': 'TOGETHER_API_KEY',
                }
                env_key = env_map.get(pid, '')
                if not os.environ.get(env_key, '').strip():
                    ps.available = False
                    ps.reason = 'no_api_key_configured'
                    ps.total_score = 0.0
                    scores.append(ps)
                    continue

            # --- Quota check (all cloud/web, not local) ---
            if pid != 'ollama_local':
                quota_ok, quota_reason = self._is_quota_available(pid, world_model)
                if not quota_ok:
                    ps.available = False
                    ps.reason = quota_reason
                    ps.total_score = 0.0
                    scores.append(ps)
                    continue

            # Check quota cooldown (in-memory, from record_result)
            cooldown_ts = self._quota_cooldowns.get(pid, 0.0)
            if cooldown_ts > 0 and (now_mono - cooldown_ts) < _QUOTA_COOLDOWN_SECONDS:
                ps.quota_exhausted = True
                ps.available = False
                ps.reason = 'quota_cooldown'
                ps.total_score = 0.0
                scores.append(ps)
                continue

            # Calculate metrics from history
            if entries:
                successes = sum(1 for e in entries if e.get('success'))
                ps.success_rate = successes / len(entries)
                latencies = [e['latency_ms'] for e in entries if e.get('success') and 'latency_ms' in e]
                ps.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 5000.0
                ps.recent_errors = [e.get('error', '') for e in entries if not e.get('success')][-3:]
            else:
                # No history — give it a neutral score (try it!)
                ps.success_rate = 0.8
                ps.avg_latency_ms = 2000.0 if pid != 'ollama_local' else 4000.0

            # Score components
            latency_score = max(0, 1.0 - (ps.avg_latency_ms / 20000.0))
            success_score = ps.success_rate
            freshness_bonus = 0.1 if not entries else 0.0

            # Tiered cloud bonus: API > web > local
            if pid.endswith('_web'):
                cloud_bonus = 0.05
            elif pid != 'ollama_local':
                cloud_bonus = 0.15
            else:
                cloud_bonus = 0.0

            # Quota-based penalization: low remaining → lower score
            quota_penalty = 0.0
            remaining = self._quota_remaining_for_provider(pid, world_model)
            if remaining is not None and pid != 'ollama_local':
                if remaining <= 0:
                    quota_penalty = 1.0  # fully penalize
                elif remaining < _LOW_QUOTA_THRESHOLD:
                    quota_penalty = 1.0 - (remaining / _LOW_QUOTA_THRESHOLD)

            raw_score = (
                latency_score * 0.3
                + success_score * 0.4
                + cloud_bonus
                + freshness_bonus
            )
            ps.total_score = round(
                raw_score * (1.0 - quota_penalty * 0.5),
                4,
            )
            ps.reason = f'latency={ps.avg_latency_ms:.0f}ms success={ps.success_rate:.0%}'

            if remaining is not None and remaining < _LOW_QUOTA_THRESHOLD:
                ps.reason += f' LOW_QUOTA({remaining})'
            if ps.success_rate < _MIN_SUCCESS_RATE:
                ps.reason += ' DEGRADED'
            if ps.avg_latency_ms > _SLOW_LATENCY_MS:
                ps.reason += ' SLOW'

            scores.append(ps)

        return scores

    def _read_recent_performance(self) -> list[dict[str, Any]]:
        """Read last N entries from performance log."""
        try:
            if not self._performance_log.exists():
                return []
            lines = self._performance_log.read_text(encoding='utf-8').strip().split('\n')
            recent = lines[-_HISTORY_WINDOW:]
            return [json.loads(line) for line in recent if line.strip()]
        except Exception:
            return []

    def _list_ollama_models(self) -> list[str]:
        """List locally available Ollama models."""
        try:
            import subprocess
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return []
            models = []
            for line in result.stdout.strip().split('\n')[1:]:  # skip header
                parts = line.split()
                if parts:
                    models.append(parts[0])
            return models
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Summary for OSES / portable context
    # ------------------------------------------------------------------

    def performance_summary(self) -> dict[str, Any]:
        """Generate a summary of model selection performance for metacognition."""
        recent = self._read_recent_performance()
        if not recent:
            return {
                'status': 'no_data',
                'message': 'No model selection history yet',
            }

        by_provider: dict[str, list[dict[str, Any]]] = {}
        for entry in recent:
            pid = entry.get('provider_id', '')
            by_provider.setdefault(pid, []).append(entry)

        provider_stats: list[dict[str, Any]] = []
        for pid, entries in by_provider.items():
            successes = sum(1 for e in entries if e.get('success'))
            latencies = [e['latency_ms'] for e in entries if e.get('success') and 'latency_ms' in e]
            provider_stats.append({
                'provider_id': pid,
                'calls': len(entries),
                'success_rate': round(successes / len(entries), 3) if entries else 0,
                'avg_latency_ms': round(sum(latencies) / len(latencies), 1) if latencies else 0,
                'quota_issues': sum(1 for e in entries if e.get('quota_exhausted')),
            })

        provider_stats.sort(key=lambda x: x.get('avg_latency_ms', 99999))

        return {
            'status': 'ok',
            'total_decisions': len(recent),
            'providers': provider_stats,
            'best_provider': provider_stats[0]['provider_id'] if provider_stats else 'unknown',
            'active_cooldowns': {
                pid: round(_QUOTA_COOLDOWN_SECONDS - (time.monotonic() - ts))
                for pid, ts in self._quota_cooldowns.items()
                if (time.monotonic() - ts) < _QUOTA_COOLDOWN_SECONDS
            },
        }
