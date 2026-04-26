"""Decision audit trail for cloud reasoning and provider selection.

Records every decision the system makes about:
- Which cloud provider was used and why
- What plan was generated, with what confidence
- Whether the plan executed successfully or failed at which step
- Latency, quality signals, user approval/rejection
- Historical trends: is this configuration improving or degrading?

Architecture:
- Append-only JSONL persistence in ``data/evolution/decision_audit/``
- NOT a second orchestrator — purely observational and analytical
- Consumed by ``OperationalSelfExaminationService`` and the UI
- The UI exposes summaries via chat commands (``auditar decisiones``)
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision outcome types
# ---------------------------------------------------------------------------

class DecisionOutcome(str, Enum):
    SUCCESS = 'success'
    PARTIAL = 'partial'
    FAILED = 'failed'
    REJECTED_BY_USER = 'rejected_by_user'
    RATE_LIMITED = 'rate_limited'
    TIMEOUT = 'timeout'
    FALLBACK_USED = 'fallback_used'


class DecisionPhase(str, Enum):
    PROVIDER_SELECTION = 'provider_selection'
    PLAN_GENERATION = 'plan_generation'
    PLAN_EXECUTION = 'plan_execution'
    KEY_VALIDATION = 'key_validation'
    KEY_RENEWAL = 'key_renewal'


# ---------------------------------------------------------------------------
# Decision record
# ---------------------------------------------------------------------------

class DecisionRecord:
    """A single auditable decision made by the system."""

    __slots__ = (
        'decision_id', 'phase', 'timestamp_utc',
        'provider_id', 'model_used', 'user_goal',
        'outcome', 'latency_ms', 'confidence',
        'steps_total', 'steps_completed', 'steps_failed',
        'fallback_chain', 'error_detail',
        'user_action', 'quality_signal',
        'metadata',
    )

    def __init__(
        self,
        *,
        decision_id: str = '',
        phase: DecisionPhase = DecisionPhase.PLAN_GENERATION,
        provider_id: str = '',
        model_used: str = '',
        user_goal: str = '',
        outcome: DecisionOutcome = DecisionOutcome.SUCCESS,
        latency_ms: float = 0.0,
        confidence: float = 0.0,
        steps_total: int = 0,
        steps_completed: int = 0,
        steps_failed: int = 0,
        fallback_chain: list[str] | None = None,
        error_detail: str = '',
        user_action: str = '',
        quality_signal: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.decision_id = decision_id or now.strftime('%Y%m%dT%H%M%S%f')
        self.phase = phase
        self.timestamp_utc = now.isoformat()
        self.provider_id = provider_id
        self.model_used = model_used
        self.user_goal = user_goal
        self.outcome = outcome
        self.latency_ms = latency_ms
        self.confidence = confidence
        self.steps_total = steps_total
        self.steps_completed = steps_completed
        self.steps_failed = steps_failed
        self.fallback_chain = fallback_chain or []
        self.error_detail = error_detail
        self.user_action = user_action
        self.quality_signal = quality_signal
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'phase': self.phase.value,
            'timestamp_utc': self.timestamp_utc,
            'provider_id': self.provider_id,
            'model_used': self.model_used,
            'user_goal': self.user_goal,
            'outcome': self.outcome.value,
            'latency_ms': self.latency_ms,
            'confidence': self.confidence,
            'steps_total': self.steps_total,
            'steps_completed': self.steps_completed,
            'steps_failed': self.steps_failed,
            'fallback_chain': self.fallback_chain,
            'error_detail': self.error_detail,
            'user_action': self.user_action,
            'quality_signal': self.quality_signal,
            'metadata': self.metadata,
        }


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------

class ProviderTrend:
    """Aggregated trend for a single provider over recent decisions."""

    __slots__ = (
        'provider_id', 'total_decisions', 'success_count',
        'failure_count', 'rate_limited_count', 'fallback_count',
        'avg_latency_ms', 'avg_confidence', 'success_rate',
        'trend_direction', 'recent_errors',
    )

    def __init__(
        self,
        *,
        provider_id: str,
        total_decisions: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        rate_limited_count: int = 0,
        fallback_count: int = 0,
        avg_latency_ms: float = 0.0,
        avg_confidence: float = 0.0,
        success_rate: float = 0.0,
        trend_direction: str = 'stable',
        recent_errors: list[str] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.total_decisions = total_decisions
        self.success_count = success_count
        self.failure_count = failure_count
        self.rate_limited_count = rate_limited_count
        self.fallback_count = fallback_count
        self.avg_latency_ms = avg_latency_ms
        self.avg_confidence = avg_confidence
        self.success_rate = success_rate
        self.trend_direction = trend_direction
        self.recent_errors = recent_errors or []

    def to_dict(self) -> dict[str, Any]:
        return {
            'provider_id': self.provider_id,
            'total_decisions': self.total_decisions,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'rate_limited_count': self.rate_limited_count,
            'fallback_count': self.fallback_count,
            'avg_latency_ms': round(self.avg_latency_ms, 1),
            'avg_confidence': round(self.avg_confidence, 3),
            'success_rate': round(self.success_rate, 3),
            'trend_direction': self.trend_direction,
            'recent_errors': self.recent_errors[:5],
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DecisionAuditTrail:
    """Append-only audit trail for cloud reasoning decisions.

    Persists to ``data/evolution/decision_audit/decisions.jsonl``.
    Provides trend analysis and self-examination summaries.
    """

    def __init__(self, *, data_root: str | Path = '') -> None:
        import os
        env_dir = os.environ.get('IABV_DATA_DIR', '').strip()
        if data_root:
            self._data_root = Path(data_root)
        elif env_dir:
            self._data_root = Path(env_dir)
        else:
            self._data_root = Path.home() / 'IABV_v1.5' / 'data'

    @property
    def _audit_dir(self) -> Path:
        d = self._data_root / 'evolution' / 'decision_audit'
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def _log_path(self) -> Path:
        return self._audit_dir / 'decisions.jsonl'

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record(self, decision: DecisionRecord) -> None:
        """Append a decision record to the audit log."""
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + '\n')
        logger.info(
            'decision-audit: recorded %s [%s] provider=%s outcome=%s latency=%.0fms',
            decision.decision_id, decision.phase.value,
            decision.provider_id, decision.outcome.value, decision.latency_ms,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load the most recent decision records."""
        if not self._log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def analyze_provider_trends(self, limit: int = 200) -> list[ProviderTrend]:
        """Analyze trends per provider from recent decisions."""
        entries = self.load_recent(limit)
        if not entries:
            return []

        by_provider: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            pid = entry.get('provider_id', 'unknown')
            if pid:
                by_provider.setdefault(pid, []).append(entry)

        trends: list[ProviderTrend] = []
        for provider_id, records in by_provider.items():
            total = len(records)
            successes = sum(1 for r in records if r.get('outcome') == 'success')
            failures = sum(1 for r in records if r.get('outcome') == 'failed')
            rate_limited = sum(1 for r in records if r.get('outcome') == 'rate_limited')
            fallbacks = sum(1 for r in records if r.get('outcome') == 'fallback_used')

            latencies = [r.get('latency_ms', 0) for r in records if r.get('latency_ms', 0) > 0]
            confidences = [r.get('confidence', 0) for r in records if r.get('confidence', 0) > 0]

            errors = [r.get('error_detail', '') for r in records if r.get('error_detail')]

            success_rate = successes / total if total > 0 else 0.0

            # Trend: compare first half vs second half success rates
            trend_direction = 'stable'
            if total >= 6:
                mid = total // 2
                first_half = records[:mid]
                second_half = records[mid:]
                sr_first = sum(1 for r in first_half if r.get('outcome') == 'success') / len(first_half)
                sr_second = sum(1 for r in second_half if r.get('outcome') == 'success') / len(second_half)
                if sr_second > sr_first + 0.1:
                    trend_direction = 'improving'
                elif sr_second < sr_first - 0.1:
                    trend_direction = 'degrading'

            trends.append(ProviderTrend(
                provider_id=provider_id,
                total_decisions=total,
                success_count=successes,
                failure_count=failures,
                rate_limited_count=rate_limited,
                fallback_count=fallbacks,
                avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
                avg_confidence=statistics.mean(confidences) if confidences else 0.0,
                success_rate=success_rate,
                trend_direction=trend_direction,
                recent_errors=errors[-5:],
            ))

        trends.sort(key=lambda t: (-t.success_rate, t.avg_latency_ms))
        return trends

    # ------------------------------------------------------------------
    # Self-examination summary
    # ------------------------------------------------------------------

    def self_examination_summary(self) -> dict[str, Any]:
        """Generate a summary suitable for OperationalSelfExaminationService.

        Returns a structured dict with:
        - overall health score (0-1)
        - per-provider trends
        - actionable recommendations
        - whether the system is improving or degrading overall
        """
        trends = self.analyze_provider_trends()
        entries = self.load_recent(200)

        if not trends:
            return {
                'status': 'no_data',
                'message': 'No hay decisiones registradas aun. Usa "soluciona X" para generar el primer plan.',
                'health_score': 0.0,
                'overall_trend': 'unknown',
                'trends': [],
                'recommendations': ['Configurar al menos GROQ_API_KEY y ejecutar un plan de prueba'],
            }

        total_decisions = sum(t.total_decisions for t in trends)
        total_successes = sum(t.success_count for t in trends)
        health_score = total_successes / total_decisions if total_decisions > 0 else 0.0

        # Overall trend
        improving = sum(1 for t in trends if t.trend_direction == 'improving')
        degrading = sum(1 for t in trends if t.trend_direction == 'degrading')
        if improving > degrading:
            overall_trend = 'improving'
        elif degrading > improving:
            overall_trend = 'degrading'
        else:
            overall_trend = 'stable'

        # Recommendations
        recommendations: list[str] = []
        for t in trends:
            if t.trend_direction == 'degrading':
                recommendations.append(
                    f'{t.provider_id} esta degradandose (exito: {t.success_rate:.0%}). '
                    f'Considerar renovar la key o rotar a otro proveedor.'
                )
            if t.rate_limited_count > t.total_decisions * 0.3:
                recommendations.append(
                    f'{t.provider_id} tiene {t.rate_limited_count} rate limits de '
                    f'{t.total_decisions} decisiones. Considerar otro proveedor como backup.'
                )
            if t.avg_latency_ms > 10000:
                recommendations.append(
                    f'{t.provider_id} tiene latencia alta ({t.avg_latency_ms:.0f}ms). '
                    f'Verificar conexion o probar otro proveedor.'
                )

        if not any(t.success_rate > 0.5 for t in trends):
            recommendations.append(
                'Ningun proveedor tiene exito mayor al 50%. '
                'Revisar keys, cuotas y conexion a internet.'
            )

        # Best provider
        best = trends[0] if trends else None

        return {
            'status': 'analyzed',
            'health_score': round(health_score, 3),
            'overall_trend': overall_trend,
            'total_decisions': total_decisions,
            'total_successes': total_successes,
            'best_provider': best.to_dict() if best else None,
            'trends': [t.to_dict() for t in trends],
            'recommendations': recommendations,
            'last_decision': entries[-1] if entries else None,
        }

    # ------------------------------------------------------------------
    # Human-readable report for the UI
    # ------------------------------------------------------------------

    def format_chat_report(self) -> str:
        """Build a markdown report suitable for the chat UI."""
        summary = self.self_examination_summary()

        if summary['status'] == 'no_data':
            return (
                '**Audit Trail de Decisiones**\n\n'
                'No hay decisiones registradas aun. '
                'Escribe "soluciona X" para generar el primer plan y empezar a registrar.'
            )

        lines = ['**Audit Trail de Decisiones Cloud**\n']
        lines.append(f'Total de decisiones: {summary["total_decisions"]}')
        lines.append(f'Tasa de exito global: {summary["health_score"]:.0%}')

        trend_emoji = {'improving': 'mejorando', 'degrading': 'degradando', 'stable': 'estable'}
        lines.append(f'Tendencia general: **{trend_emoji.get(summary["overall_trend"], summary["overall_trend"])}**\n')

        if summary['trends']:
            lines.append('**Por proveedor:**')
            for t in summary['trends']:
                direction = trend_emoji.get(t['trend_direction'], t['trend_direction'])
                lines.append(
                    f'  - **{t["provider_id"]}**: {t["success_count"]}/{t["total_decisions"]} exitos '
                    f'({t["success_rate"]:.0%}), latencia ~{t["avg_latency_ms"]:.0f}ms, '
                    f'tendencia: {direction}'
                )
                if t['rate_limited_count'] > 0:
                    lines.append(f'    - Rate limits: {t["rate_limited_count"]}')
                if t['recent_errors']:
                    lines.append(f'    - Ultimo error: {t["recent_errors"][-1][:80]}')

        if summary['best_provider']:
            bp = summary['best_provider']
            lines.append(f'\n**Mejor proveedor:** {bp["provider_id"]} ({bp["success_rate"]:.0%} exito, {bp["avg_latency_ms"]:.0f}ms)')

        if summary['recommendations']:
            lines.append('\n**Recomendaciones:**')
            for rec in summary['recommendations'][:5]:
                lines.append(f'  - {rec}')

        last = summary.get('last_decision')
        if last:
            lines.append(f'\n_Ultima decision: {last.get("timestamp_utc", "?")} — {last.get("provider_id", "?")} — {last.get("outcome", "?")}_')

        return '\n'.join(lines)
