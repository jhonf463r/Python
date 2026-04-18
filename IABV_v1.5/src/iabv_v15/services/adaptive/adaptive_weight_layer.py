from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from iabv_v15.domain.models import ExperimentRun


class AdaptiveWeightLayer:
    """Sugiere preferencias adaptativas a partir de corridas historicas reales."""

    def suggest(
        self,
        *,
        grouped_runs: dict[tuple[object, str, str], list[ExperimentRun]],
    ) -> dict[tuple[object, str, str], dict[str, Any]]:
        return {
            key: self._profile(runs)
            for key, runs in grouped_runs.items()
            if runs
        }

    def update_weights(
        self,
        *,
        historical_runs: list[ExperimentRun],
        latest_run: ExperimentRun,
    ) -> dict[str, Any]:
        matching = [
            run
            for run in historical_runs
            if run.route == latest_run.route
            and str(run.assistant_kind or '').strip().lower() == str(latest_run.assistant_kind or '').strip().lower()
            and str(run.config_signature or '').strip() == str(latest_run.config_signature or '').strip()
        ]
        return self._profile([*matching, latest_run])

    def explain_shift(self, *, previous: Any | None, current: Any | None) -> str:
        if previous is None or current is None:
            return ''
        previous_route = getattr(previous, 'recommended_route', None)
        current_route = getattr(current, 'recommended_route', None)
        previous_assistant = str(getattr(previous, 'recommended_assistant_kind', '') or '').strip().lower()
        current_assistant = str(getattr(current, 'recommended_assistant_kind', '') or '').strip().lower()
        if previous_route == current_route and previous_assistant == current_assistant:
            return ''
        summary = dict(getattr(current, 'metadata', {}) or {}).get('adaptive_learning_summary') or {}
        reasons = [str(item).strip() for item in (summary.get('reasons') or []) if str(item).strip()]
        if reasons:
            return f"Cambio adaptativo hacia {getattr(current_route, 'value', current_route)} con {current_assistant or 'asistente por defecto'}: {'; '.join(reasons[:2])}."
        return (
            f"Cambio adaptativo hacia {getattr(current_route, 'value', current_route)}"
            f" con {current_assistant or 'asistente por defecto'}."
        )

    def _profile(self, runs: list[ExperimentRun]) -> dict[str, Any]:
        ordered_runs = sorted(runs, key=lambda item: item.created_at_utc)
        sample_count = len(ordered_runs)
        success_count = sum(1 for run in ordered_runs if bool(run.success))
        failure_count = sample_count - success_count
        blocked_count = sum(1 for run in ordered_runs if self._is_blocked(run))
        fallback_count = sum(1 for run in ordered_runs if self._used_fallback(run))
        reuse_count = sum(1 for run in ordered_runs if bool(run.reused_later) or float(run.metrics.reuse_score or 0.0) >= 0.45)
        average_score = sum(float(run.metrics.total_score or 0.0) for run in ordered_runs) / max(sample_count, 1)
        average_latency_ms = int(sum(int(run.metrics.execution_ms or 0) for run in ordered_runs) / max(sample_count, 1))
        success_rate = success_count / max(sample_count, 1)
        failure_rate = failure_count / max(sample_count, 1)
        blocked_rate = blocked_count / max(sample_count, 1)
        fallback_rate = fallback_count / max(sample_count, 1)
        reuse_ratio = reuse_count / max(sample_count, 1)
        recency_score = self._recency_score(ordered_runs)
        trend_score = self._trend_score(ordered_runs)
        latency_penalty = min(0.12, average_latency_ms / 4500.0 * 0.12)
        adaptive_weight = (
            success_rate * 0.18
            + reuse_ratio * 0.08
            + recency_score * 0.08
            + trend_score * 0.05
            - failure_rate * 0.18
            - blocked_rate * 0.14
            - fallback_rate * 0.08
            - latency_penalty
        )
        weighted_score = average_score + adaptive_weight
        reasons: list[str] = []
        if success_rate >= 0.66:
            reasons.append(f"historial de exito {success_rate:.0%}")
        if reuse_ratio >= 0.5:
            reasons.append(f"reutilizacion alta {reuse_ratio:.0%}")
        if blocked_rate >= 0.34:
            reasons.append(f"bloqueos frecuentes {blocked_rate:.0%}")
        if fallback_rate >= 0.34:
            reasons.append(f"fallback recurrente {fallback_rate:.0%}")
        if average_latency_ms >= 1200:
            reasons.append(f"latencia promedio {average_latency_ms} ms")
        if trend_score >= 0.12:
            reasons.append('mejora reciente sostenida')
        elif trend_score <= -0.12:
            reasons.append('deterioro reciente')
        return {
            'sample_count': sample_count,
            'success_rate': round(success_rate, 4),
            'failure_rate': round(failure_rate, 4),
            'blocked_rate': round(blocked_rate, 4),
            'fallback_rate': round(fallback_rate, 4),
            'reuse_ratio': round(reuse_ratio, 4),
            'average_score': round(average_score, 4),
            'average_latency_ms': average_latency_ms,
            'recency_score': round(recency_score, 4),
            'trend_score': round(trend_score, 4),
            'adaptive_weight': round(adaptive_weight, 4),
            'weighted_score': round(weighted_score, 4),
            'top_environment_signatures': self._top_values([self._environment_signature(run) for run in ordered_runs]),
            'top_time_buckets': self._top_values([self._time_bucket(run.created_at_utc) for run in ordered_runs]),
            'reasons': reasons[:4],
        }

    def _recency_score(self, runs: list[ExperimentRun]) -> float:
        if not runs:
            return 0.0
        now = datetime.now(timezone.utc)
        total_weight = 0.0
        weighted_outcome = 0.0
        for run in runs:
            age_days = max(0.0, (now - run.created_at_utc).total_seconds() / 86400.0)
            decay = max(0.35, 1.0 - min(age_days, 45.0) / 60.0)
            outcome = 1.0 if run.success else -0.7
            if self._is_blocked(run):
                outcome -= 0.35
            if self._used_fallback(run):
                outcome -= 0.15
            total_weight += decay
            weighted_outcome += outcome * decay
        if total_weight <= 0:
            return 0.0
        normalized = weighted_outcome / total_weight
        return max(-1.0, min(normalized, 1.0))

    def _trend_score(self, runs: list[ExperimentRun]) -> float:
        if len(runs) < 3:
            return 0.0
        ordered_runs = sorted(runs, key=lambda item: item.created_at_utc)
        recent = ordered_runs[-3:]
        older = ordered_runs[:-3]
        if not older:
            return 0.0
        recent_score = sum(float(run.metrics.total_score or 0.0) for run in recent) / len(recent)
        older_score = sum(float(run.metrics.total_score or 0.0) for run in older) / len(older)
        return max(-0.25, min(recent_score - older_score, 0.25))

    def _is_blocked(self, run: ExperimentRun) -> bool:
        metadata = dict(run.metadata or {})
        flags = [str(item).strip().lower() for item in (metadata.get('external_state_flags') or []) if str(item).strip()]
        blockers = {'wrong_thread', 'session_expired', 'account_limited', 'browser_security_verification', 'permission_required'}
        if bool(metadata.get('blocked')) or bool(metadata.get('governance_blocked')):
            return True
        return any(any(token in flag for token in blockers) for flag in flags)

    def _used_fallback(self, run: ExperimentRun) -> bool:
        metadata = dict(run.metadata or {})
        return bool(metadata.get('used_fallback') or metadata.get('fallback_used'))

    def _environment_signature(self, run: ExperimentRun) -> str:
        metadata = dict(run.metadata or {})
        network = str(metadata.get('network_status') or '').strip().lower()
        env_scan = str(metadata.get('environment_scan_status') or '').strip().lower()
        dominant_incident = str(metadata.get('dominant_incident') or '').strip().lower()
        external_flags = [str(item).strip().lower() for item in (metadata.get('external_state_flags') or []) if str(item).strip()]
        parts = [part for part in (network, env_scan, dominant_incident, external_flags[0] if external_flags else '') if part]
        return '|'.join(parts[:3]) if parts else 'default'

    def _time_bucket(self, value: datetime) -> str:
        hour = int(value.astimezone(timezone.utc).hour)
        if 5 <= hour < 12:
            return 'morning'
        if 12 <= hour < 18:
            return 'afternoon'
        if 18 <= hour < 23:
            return 'evening'
        return 'night'

    def _top_values(self, values: list[str]) -> list[str]:
        counts: dict[str, int] = {}
        for item in values:
            probe = str(item or '').strip()
            if not probe:
                continue
            counts[probe] = counts.get(probe, 0) + 1
        ordered = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
        return [value for value, _ in ordered[:3]]
