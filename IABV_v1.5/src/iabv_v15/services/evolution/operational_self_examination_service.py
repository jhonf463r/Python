from __future__ import annotations

import json
import math
import os
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    AdaptiveSessionStatus,
    AutonomousValidationSnapshot,
    ExperimentRecommendation,
    ExperimentRun,
    IssueSeverity,
    RunRecord,
    RunStatus,
    SelfExaminationFinding,
    SelfExaminationSnapshot,
    WorldModelSnapshot,
    utc_now,
)
from iabv_v15.infra.persistence.storage import ArtifactStorage

# Startup health thresholds (in milliseconds).  Crossing any of these emits a
# ``startup_degradation`` finding from :meth:`_startup_health_findings`.  They
# are intentionally module-level constants so any operator can grep + tune
# without hunting through method bodies.  The values come from the live audit
# handoff ("splash 45-75s en algunas corridas") and the deferred-tool-probe
# baseline introduced in PR #257.
STARTUP_INIT_MS_DEGRADED = 4000.0
STARTUP_RUN_TO_WINDOW_MS_DEGRADED = 8000.0
STARTUP_DEFERRED_MS_DEGRADED = 5000.0
# populate_ui: the interval where all ViewModels are constructed on the main
# thread.  Windsurf live tests show 30s+ blocks here, causing "Not Responding".
STARTUP_POPULATE_UI_MS_DEGRADED = 5000.0
STARTUP_POPULATE_UI_INCOMPLETE_MIN_MS = 120000.0
# RSS growth during populate_ui (in MB).  273→495 MB observed in live tests.
STARTUP_RSS_GROWTH_MB_DEGRADED = 150.0

# Boot profile thresholds — aggregated across historical boots.
# p95 boot duration above this emits a finding.
BOOT_P95_MS_DEGRADED = 30000.0
# Average wiring duration above this emits a finding.
BOOT_WIRING_AVG_MS_DEGRADED = 20000.0
# Boot regression: if the last boot is >40% slower than the rolling average,
# emit a regression finding.
BOOT_REGRESSION_RATIO = 1.4


class OperationalSelfExaminationService:
    def __init__(
        self,
        *,
        workspace_root: str,
        storage: ArtifactStorage,
        run_repository: Any | None = None,
        adaptive_session_repository: Any | None = None,
        experiment_lab_repository: Any | None = None,
        scenario_run_repository: Any | None = None,
        evolution_review_service: Any | None = None,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        adaptive_weight_layer: Any | None = None,
        token_rotation_ledger: Any | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self._created_at = time.time()
        self.storage = storage
        self.run_repository = run_repository
        self.adaptive_session_repository = adaptive_session_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.scenario_run_repository = scenario_run_repository
        self.evolution_review_service = evolution_review_service
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.adaptive_weight_layer = adaptive_weight_layer
        # Capa 2.2 — dep opcional. Si se pasa un ``TokenRotationLedger``,
        # ``_token_rotation_findings`` produce hallazgos proactivos sobre
        # PATs de GitHub / Devin API a punto de expirar. Es lo unico que
        # permite cerrar el loop "detectar el patron de expiracion antes
        # de que el user lo note" sin inventar observacion nueva.
        self.token_rotation_ledger: Any | None = token_rotation_ledger
        # PCS v1 — hook opcional. Si un provider con ``snapshot()`` está
        # presente, `_persist_review` incluye las violaciones de
        # encarnamiento en ``metadata['embodiment_violations']`` sin
        # cambiar el contrato del SelfExaminationSnapshot.
        self.embodiment_violation_provider: Any | None = None
        self.decision_audit_trail: Any | None = None
        self.code_audit_trail: Any | None = None
        self.boot_profile_store: Any | None = None
        self.chat_message_repository: Any | None = None
        self._current_review: SelfExaminationSnapshot | None = None
        # Read-only cache for GitHub API rate-limit data.  Populated
        # externally (e.g. auto-correction scan); _account_resource_health_findings
        # never probes — it only reads if fresh, otherwise skips the finding.
        self._gh_api_cache: dict[str, Any] | None = None
        self._gh_api_cached_at: float = 0.0
        self._GH_API_TTL: float = 60.0
        self._freeze_incident_reporter: Any | None = None

    def current_review(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: int = 300,
    ) -> SelfExaminationSnapshot:
        cached = self._current_review
        if cached is None:
            cached = self._load_latest_review()
            self._current_review = cached
        if not refresh and cached is not None and self._is_fresh(cached, max_age_seconds=max_age_seconds):
            return cached
        review = self.build_review()
        self._current_review = review
        return review

    def review_summary(self, review: SelfExaminationSnapshot | None = None) -> dict[str, Any]:
        resolved = review or self.current_review()
        metadata = dict(resolved.metadata or {})
        return {
            'review_id': resolved.review_id,
            'package_version': resolved.package_version,
            'summary': resolved.summary,
            'status': resolved.status,
            'assistant_brief': resolved.assistant_brief,
            'top_findings': [item.model_dump(mode='json') for item in resolved.findings[:4]],
            'recurring_issues': list(resolved.recurring_issues[:5]),
            'recommended_adjustments': list(resolved.recommended_adjustments[:5]),
            'validated_improvements': list(resolved.validated_improvements[:4]),
            'unresolved_risks': list(resolved.unresolved_risks[:6]),
            'recommendation_feedback': list(metadata.get('recommendation_feedback') or [])[:6],
            'feedback_summary': dict(metadata.get('feedback_summary') or {}),
            # H4 — surfacing explícito de los probe requests pendientes al
            # summary para que la UI, el orquestador y los MCP consumers los
            # vean sin tener que descender al ``metadata`` crudo.
            'pending_auto_probes': list(metadata.get('pending_auto_probes') or [])[:6],
            'updated_at_utc': resolved.updated_at_utc.isoformat(),
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
        }

    def _is_low_load(self, world: WorldModelSnapshot) -> bool:
        """Determine if the system is under low load (idle or near-idle).

        Low load is detected when:
        - No CRITICAL or HIGH risk signals from ``EnvironmentSelfModel``
          (fetched via ``world_model_service.environment_self_awareness_service``)
        - The world model has <= 3 active ``block_records``

        When load is low, ``build_review`` activates deferred deep
        cognition: additional analysis passes that are too expensive
        to run under normal or high load.

        Note: ``risk_signals`` lives on ``EnvironmentSelfModel``, NOT on
        ``WorldModelSnapshot``.  ``WorldModelSnapshot`` has ``block_records``
        (list[OperationalBlockRecord]) and ``detected_blocks`` (list[str]).
        """
        # Check risk signals from EnvironmentSelfModel (if accessible).
        try:
            wm_service = self.world_model_service
            if wm_service is not None:
                env_service = getattr(wm_service, 'environment_self_awareness_service', None)
                if env_service is not None and hasattr(env_service, 'current_model'):
                    env_model = env_service.current_model()
                    if env_model is not None:
                        for signal in (env_model.risk_signals or []):
                            severity = str(getattr(signal, 'severity', '') or '').upper()
                            if severity in {'CRITICAL', 'HIGH'}:
                                return False
        except Exception:
            pass

        # Check operational blocks from WorldModelSnapshot.block_records.
        active_blocks = [
            b for b in (world.block_records or [])
            if str(getattr(b, 'status', '') or '') == 'active'
        ]
        if len(active_blocks) > 3:
            return False
        return True

    def _deferred_deep_cognition_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recent_runs: list[RunRecord],
        findings_so_far: list[SelfExaminationFinding],
    ) -> list[SelfExaminationFinding]:
        """Deep cognition pass — only runs when the system is under low load.

        This is the "when I have free time, think deeply" mechanism. It
        performs analysis that would be too expensive under normal load:

        1. Cross-correlation between failure patterns across different IAs
        2. Long-window trend detection (are things getting better or worse?)
        3. Strategy effectiveness decay (is a once-good strategy degrading?)

        These findings are tagged with ``source='deferred_deep_cognition'``
        so downstream consumers know they came from a deep analysis pass.
        """
        findings: list[SelfExaminationFinding] = []

        # 1. Cross-correlation: if two different IAs fail on the same intent
        # pattern, the problem is likely in the intent/context, not the IA.
        if len(experiment_runs) >= 6:
            intent_failures: dict[str, set[str]] = {}
            for run in experiment_runs:
                if bool(run.success):
                    continue
                intent_key = str(getattr(run, 'intent_key', '') or run.domain or '').strip()
                kind = str(run.assistant_kind or '').strip().lower()
                if intent_key and kind:
                    intent_failures.setdefault(intent_key, set()).add(kind)
            for intent_key, failing_kinds in intent_failures.items():
                if len(failing_kinds) >= 2:
                    findings.append(SelfExaminationFinding(
                        category='cross_correlation_failure',
                        severity=IssueSeverity.HIGH,
                        title=f'Multiples IAs fallan en "{intent_key}"',
                        summary=(
                            f'{len(failing_kinds)} IAs distintas ({", ".join(sorted(failing_kinds))}) '
                            f'fallan en el mismo patron de intent. El problema probablemente '
                            f'esta en el contexto o la clasificacion, no en las IAs.'
                        ),
                        source_refs=['deferred_deep_cognition'],
                    ))

        # 2. Trend detection: compare success rate of last N runs vs previous N.
        if len(recent_runs) >= 10:
            mid = len(recent_runs) // 2
            older_runs = recent_runs[mid:]
            newer_runs = recent_runs[:mid]
            older_success = sum(1 for r in older_runs if r.status == RunStatus.SUCCESS) / max(len(older_runs), 1)
            newer_success = sum(1 for r in newer_runs if r.status == RunStatus.SUCCESS) / max(len(newer_runs), 1)
            delta = newer_success - older_success
            if delta <= -0.15:
                findings.append(SelfExaminationFinding(
                    category='trend_degradation',
                    severity=IssueSeverity.HIGH,
                    title='Tendencia de degradacion detectada',
                    summary=(
                        f'La tasa de exito cayo de {older_success:.0%} '
                        f'a {newer_success:.0%} (delta={delta:+.0%}). '
                        f'Revisar cambios recientes en configuracion o entorno.'
                    ),
                    source_refs=['deferred_deep_cognition'],
                ))
            elif delta >= 0.15:
                findings.append(SelfExaminationFinding(
                    category='trend_improvement',
                    severity=IssueSeverity.LOW,
                    title='Tendencia de mejora detectada',
                    summary=(
                        f'La tasa de exito subio de {older_success:.0%} '
                        f'a {newer_success:.0%} (delta={delta:+.0%}). '
                        f'Los ajustes recientes estan funcionando.'
                    ),
                    source_refs=['deferred_deep_cognition'],
                ))

        # 3. Strategy effectiveness decay: a strategy that was good but is
        # now producing mixed results.
        if len(experiment_runs) >= 8:
            kind_runs: dict[str, list[ExperimentRun]] = {}
            for run in experiment_runs:
                kind = str(run.assistant_kind or '').strip().lower()
                if kind:
                    kind_runs.setdefault(kind, []).append(run)
            for kind, runs in kind_runs.items():
                if len(runs) < 4:
                    continue
                mid = len(runs) // 2
                older = runs[mid:]
                newer = runs[:mid]
                older_rate = sum(1 for r in older if bool(r.success)) / max(len(older), 1)
                newer_rate = sum(1 for r in newer if bool(r.success)) / max(len(newer), 1)
                if older_rate >= 0.6 and newer_rate <= 0.35:
                    findings.append(SelfExaminationFinding(
                        category='strategy_decay',
                        severity=IssueSeverity.MEDIUM,
                        title=f'Estrategia "{kind}" en decadencia',
                        summary=(
                            f'{kind} tenia {older_rate:.0%} exito y ahora tiene '
                            f'{newer_rate:.0%}. Considerar reclasificar o '
                            f'investigar cambios en el proveedor.'
                        ),
                        source_refs=['deferred_deep_cognition'],
                    ))

        return findings[:3]

    # ------------------------------------------------------------------
    # Background decision review (CognitiveMonitor) — extends OSES with
    # continuous observation of every decision via DecisionAuditTrail.
    # Evaluates in each review whether the chosen route was optimal by
    # comparing the decision's outcome against the historical best for
    # that intent/provider combination.
    # ------------------------------------------------------------------

    def _background_decision_review_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Background meta-observer: review recent decisions for sub-optimal choices.

        Reads the last N decisions from ``DecisionAuditTrail`` and checks:
        1. Whether a decision used a provider that historically underperforms
           for that phase (provider mismatch).
        2. Whether decisions with low confidence (<0.4) led to failures
           (confidence calibration).
        3. Whether the same error repeats across recent decisions (error
           pattern stagnation).
        """
        findings: list[SelfExaminationFinding] = []
        trail = self.decision_audit_trail
        if trail is None:
            return findings

        try:
            recent = trail.load_recent(limit=50)
        except Exception:
            return findings

        if len(recent) < 5:
            return findings

        # 1. Provider mismatch: provider used but historically worse.
        provider_outcomes: dict[str, list[bool]] = {}
        for entry in recent:
            pid = str(entry.get('provider_id') or '').strip()
            outcome = str(entry.get('outcome') or '')
            if pid:
                provider_outcomes.setdefault(pid, []).append(outcome == 'success')

        for pid, outcomes in provider_outcomes.items():
            if len(outcomes) < 3:
                continue
            rate = sum(outcomes) / len(outcomes)
            if rate < 0.35:
                findings.append(SelfExaminationFinding(
                    category='background_provider_underperformance',
                    severity=IssueSeverity.MEDIUM,
                    title=f'Proveedor "{pid}" con tasa de exito baja ({rate:.0%})',
                    summary=(
                        f'{pid} tuvo exito en solo {sum(outcomes)}/{len(outcomes)} '
                        f'decisiones recientes. Considerar reclasificar o degradar '
                        f'su prioridad en StrategySelector.'
                    ),
                    source_refs=['background_decision_review', 'DecisionAuditTrail'],
                ))

        # 2. Confidence calibration: low-confidence decisions that failed.
        low_conf_failures = [
            e for e in recent
            if float(e.get('confidence') or 1.0) < 0.4
            and str(e.get('outcome') or '') in ('failed', 'timeout', 'rate_limited')
        ]
        if len(low_conf_failures) >= 3:
            findings.append(SelfExaminationFinding(
                category='background_confidence_miscalibration',
                severity=IssueSeverity.HIGH,
                title=f'{len(low_conf_failures)} decisiones de baja confianza fallaron',
                summary=(
                    f'El sistema tomo {len(low_conf_failures)} decisiones con '
                    f'confianza <0.4 que terminaron en fallo. El umbral minimo '
                    f'de confianza deberia elevarse o la ruta deberia bloquearse.'
                ),
                source_refs=['background_decision_review', 'DecisionAuditTrail'],
            ))

        # 3. Error stagnation: same error_detail repeating.
        error_counts: Counter[str] = Counter()
        for entry in recent[-20:]:
            err = str(entry.get('error_detail') or '').strip()[:80]
            if err:
                error_counts[err] += 1
        for err_msg, count in error_counts.most_common(2):
            if count >= 3:
                findings.append(SelfExaminationFinding(
                    category='background_error_stagnation',
                    severity=IssueSeverity.HIGH,
                    title=f'Error repetido {count} veces sin correccion',
                    summary=(
                        f'El error "{err_msg}" se repite {count} veces en las '
                        f'ultimas 20 decisiones. El sistema no esta corrigiendo '
                        f'este patron — requiere intervencion o ruta alternativa.'
                    ),
                    source_refs=['background_decision_review', 'DecisionAuditTrail'],
                ))

        return findings[:3]

    # ------------------------------------------------------------------
    # TemporalAwareness — conciencia del tiempo y detección de anomalías
    # temporales. Extiende OSES para detectar tareas que tardan mucho más
    # de lo esperado, comparando latencias contra promedios históricos.
    # ------------------------------------------------------------------

    def _temporal_awareness_findings(
        self,
        *,
        recent_runs: list[RunRecord],
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect temporal anomalies in task execution.

        Analyses:
        1. Tasks that took significantly longer than the historical median
           for their intent/kind (z-score > 2.0).
        2. Increasing latency trend across the last N runs (regression).
        3. Stalled operations: runs that started but never completed within
           a reasonable window.
        """
        findings: list[SelfExaminationFinding] = []

        # 1. Latency anomaly detection via z-score on experiment runs.
        kind_latencies: dict[str, list[float]] = {}
        for run in experiment_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            latency = float(
                getattr(run, 'latency_ms', 0)
                or getattr(getattr(run, 'metrics', None), 'execution_ms', 0)
                or 0
            )
            if kind and latency > 0:
                kind_latencies.setdefault(kind, []).append(latency)

        for kind, latencies in kind_latencies.items():
            if len(latencies) < 5:
                continue
            last_latency = latencies[0]  # most recent
            # Exclude the observation under test from the reference
            # distribution to avoid self-masking the z-score.
            ref = latencies[1:]
            if len(ref) < 4:
                continue
            mean_lat = sum(ref) / len(ref)
            if mean_lat <= 0:
                continue
            variance = sum((x - mean_lat) ** 2 for x in ref) / len(ref)
            std_dev = math.sqrt(variance) if variance > 0 else 0
            if std_dev <= 0:
                continue
            z_score = (last_latency - mean_lat) / std_dev
            if z_score > 2.0:
                findings.append(SelfExaminationFinding(
                    category='temporal_latency_anomaly',
                    severity=IssueSeverity.MEDIUM if z_score < 3.0 else IssueSeverity.HIGH,
                    title=f'Anomalia temporal en "{kind}" (z={z_score:.1f})',
                    summary=(
                        f'La ultima ejecucion de {kind} tardo {last_latency:.0f}ms '
                        f'vs media historica de {mean_lat:.0f}ms (z-score={z_score:.1f}). '
                        f'Posible degradacion del proveedor o sobrecarga.'
                    ),
                    source_refs=['temporal_awareness'],
                ))

        # 2. Latency trend: are runs getting progressively slower?
        if len(experiment_runs) >= 10:
            all_latencies = [
                float(
                    getattr(r, 'latency_ms', 0)
                    or getattr(getattr(r, 'metrics', None), 'execution_ms', 0)
                    or 0
                )
                for r in experiment_runs[:20]
                if float(
                    getattr(r, 'latency_ms', 0)
                    or getattr(getattr(r, 'metrics', None), 'execution_ms', 0)
                    or 0
                ) > 0
            ]
            if len(all_latencies) >= 10:
                mid = len(all_latencies) // 2
                newer_avg = sum(all_latencies[:mid]) / mid
                older_avg = sum(all_latencies[mid:]) / (len(all_latencies) - mid)
                if older_avg > 0 and newer_avg > older_avg * 1.5:
                    findings.append(SelfExaminationFinding(
                        category='temporal_latency_regression',
                        severity=IssueSeverity.MEDIUM,
                        title='Regresion de latencia detectada',
                        summary=(
                            f'La latencia promedio reciente ({newer_avg:.0f}ms) es '
                            f'{newer_avg / older_avg:.1f}x mayor que la historica '
                            f'({older_avg:.0f}ms). El sistema se esta volviendo mas lento.'
                        ),
                        source_refs=['temporal_awareness'],
                    ))

        # 3. Stalled operations: runs with status != success/failed that
        # have been running for too long (> 5 min based on created_at).
        now = utc_now()
        stalled_count = 0
        for run in recent_runs[:20]:
            status = run.status
            if status in (RunStatus.SUCCESS, RunStatus.FAILED):
                continue
            created = getattr(run, 'created_at', None) or getattr(run, 'created_at_utc', None)
            if created is None:
                continue
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except (ValueError, TypeError):
                    continue
            if not hasattr(created, 'tzinfo') or created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            elapsed = (now - created).total_seconds()
            if elapsed > 300:  # > 5 minutes
                stalled_count += 1

        if stalled_count >= 2:
            findings.append(SelfExaminationFinding(
                category='temporal_stalled_operations',
                severity=IssueSeverity.HIGH,
                title=f'{stalled_count} operaciones estancadas (>5 min)',
                summary=(
                    f'{stalled_count} runs llevan mas de 5 minutos sin completar. '
                    f'Posible bloqueo o recurso no disponible. Considerar timeout '
                    f'automatico o abort de sesiones zombi.'
                ),
                source_refs=['temporal_awareness'],
            ))

        return findings[:3]

    # ------------------------------------------------------------------
    # DeepAnalysisQueue — análisis estadístico profundo diferido.
    # Cuando el sistema está idle, ejecuta análisis más costosos:
    # correlaciones, distribuciones, z-scores globales, moving averages.
    # Complementa _deferred_deep_cognition_findings con estadística real.
    # ------------------------------------------------------------------

    def _deep_analysis_queue_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recent_runs: list[RunRecord],
    ) -> list[SelfExaminationFinding]:
        """Statistical deep analysis — only runs under low load.

        Performs:
        1. Moving average of success rate with exponential smoothing
           to detect subtle drift before it becomes a visible trend.
        2. Provider correlation: which providers succeed/fail together
           (indicating shared infrastructure issues vs provider-specific).
        3. Anomaly detection via IQR on latencies to surface outliers
           that z-score might miss.
        """
        findings: list[SelfExaminationFinding] = []

        # 1. Exponential moving average (EMA) drift detection.
        if len(recent_runs) >= 15:
            alpha = 0.3  # smoothing factor
            successes = [
                1.0 if r.status == RunStatus.SUCCESS else 0.0
                for r in reversed(recent_runs[:30])
            ]
            ema = successes[0]
            for val in successes[1:]:
                ema = alpha * val + (1 - alpha) * ema
            overall_rate = sum(successes) / len(successes)
            if ema < overall_rate - 0.15 and ema < 0.5:
                findings.append(SelfExaminationFinding(
                    category='deep_analysis_ema_drift',
                    severity=IssueSeverity.MEDIUM,
                    title=f'EMA de exito en declive ({ema:.0%} vs {overall_rate:.0%} global)',
                    summary=(
                        f'El promedio movil exponencial de exito (alpha={alpha}) '
                        f'esta en {ema:.0%}, por debajo de la media global '
                        f'({overall_rate:.0%}). Esto indica degradacion reciente '
                        f'que aun no se refleja en metricas brutas.'
                    ),
                    source_refs=['deep_analysis_queue'],
                ))

        # 2. Provider success correlation: if two providers fail in the
        # same time window, they may share an infrastructure issue.
        trail = self.decision_audit_trail
        if trail is not None:
            try:
                entries = trail.load_recent(limit=40)
                if len(entries) >= 10:
                    window_failures: dict[str, list[str]] = {}
                    for entry in entries:
                        ts = str(entry.get('timestamp_utc') or '')[:13]  # hour-level bucket
                        outcome = str(entry.get('outcome') or '')
                        pid = str(entry.get('provider_id') or '')
                        if outcome in ('failed', 'timeout') and pid and ts:
                            window_failures.setdefault(ts, []).append(pid)
                    correlated_windows = [
                        (ts, pids) for ts, pids in window_failures.items()
                        if len(set(pids)) >= 2
                    ]
                    if len(correlated_windows) >= 2:
                        all_providers = set()
                        for _, pids in correlated_windows:
                            all_providers.update(pids)
                        findings.append(SelfExaminationFinding(
                            category='deep_analysis_correlated_failures',
                            severity=IssueSeverity.HIGH,
                            title=f'Fallos correlacionados entre {len(all_providers)} proveedores',
                            summary=(
                                f'{len(correlated_windows)} ventanas temporales muestran '
                                f'fallos simultaneos en {", ".join(sorted(all_providers))}. '
                                f'Posible causa comun: red, DNS, o saturacion del sistema.'
                            ),
                            source_refs=['deep_analysis_queue', 'DecisionAuditTrail'],
                        ))
            except Exception:
                pass

        # 3. IQR outlier detection on latencies.
        all_latencies = sorted(
            float(
                getattr(r, 'latency_ms', 0)
                or getattr(getattr(r, 'metrics', None), 'execution_ms', 0)
                or 0
            )
            for r in experiment_runs
            if float(
                getattr(r, 'latency_ms', 0)
                or getattr(getattr(r, 'metrics', None), 'execution_ms', 0)
                or 0
            ) > 0
        )
        if len(all_latencies) >= 10:
            q1_idx = len(all_latencies) // 4
            q3_idx = 3 * len(all_latencies) // 4
            q1 = all_latencies[q1_idx]
            q3 = all_latencies[q3_idx]
            iqr = q3 - q1
            upper_fence = q3 + 1.5 * iqr
            outliers = [lat for lat in all_latencies if lat > upper_fence]
            if len(outliers) >= 3:
                findings.append(SelfExaminationFinding(
                    category='deep_analysis_latency_outliers',
                    severity=IssueSeverity.MEDIUM,
                    title=f'{len(outliers)} outliers de latencia (>{upper_fence:.0f}ms)',
                    summary=(
                        f'{len(outliers)} ejecuciones exceden el fence superior '
                        f'IQR de {upper_fence:.0f}ms (Q1={q1:.0f}, Q3={q3:.0f}, '
                        f'IQR={iqr:.0f}). Estas ejecuciones anomalas podrian '
                        f'estar enmascarando problemas intermitentes.'
                    ),
                    source_refs=['deep_analysis_queue'],
                ))

        return findings[:3]

    def build_review(self) -> SelfExaminationSnapshot:
        now = utc_now()
        previous_review = self._load_latest_review()
        recent_runs = self._recent_runs()
        adaptive_sessions = self._recent_adaptive_sessions()
        experiment_runs = self._recent_experiment_runs()
        recommendations = self._recent_recommendations()
        scenario_runs = self._recent_scenario_runs()
        project_health = self._project_health_snapshot()
        backlog = self._improvement_backlog()
        world = self._world_model()
        validation = self._validation_snapshot()

        findings: list[SelfExaminationFinding] = []
        findings.extend(self._recurring_failure_findings(recent_runs=recent_runs))
        findings.extend(self._pack_stall_findings(adaptive_sessions=adaptive_sessions))
        findings.extend(
            self._route_inertia_findings(
                experiment_runs=experiment_runs,
                recommendations=recommendations,
            )
        )
        findings.extend(
            self._repeated_block_findings(
                experiment_runs=experiment_runs,
                world=world,
            )
        )
        findings.extend(self._weak_correction_findings(scenario_runs=scenario_runs))
        findings.extend(self._token_rotation_findings())
        findings.extend(self._cloud_reasoning_findings())
        startup_findings = self._startup_health_findings()
        findings.extend(startup_findings)
        findings.extend(self._startup_birth_audit_findings())
        self._auto_capture_startup_freeze(startup_findings)
        findings.extend(self._ui_heartbeat_stall_findings())
        findings.extend(self._interaction_episode_findings())
        # P0.22: dispatch lifecycle anomaly detection — resource_pressure
        # repeated blocks, permission-grant-then-block, orphan interaction_id.
        findings.extend(self._dispatch_lifecycle_anomaly_findings())
        findings.extend(self._boot_profile_findings())
        findings.extend(self._chat_research_backlog_findings())
        # Cognitive meta-patterns: fijación, incubación, atractores, ensambles
        findings.extend(
            self._cognitive_fixation_findings(
                experiment_runs=experiment_runs,
                recommendations=recommendations,
            )
        )
        findings.extend(self._cognitive_incubation_findings(experiment_runs=experiment_runs))
        findings.extend(self._neural_attractor_findings(experiment_runs=experiment_runs))
        findings.extend(self._neural_ensemble_findings(experiment_runs=experiment_runs))
        # Loop-closure introspection: the system checks its own mechanisms
        findings.extend(self._loop_closure_findings(
            findings_so_far=findings,
            experiment_runs=experiment_runs,
        ))
        # Metacognitive error detection: the system audits its own introspection
        findings.extend(self._metacognitive_accuracy_findings(
            previous_review=previous_review,
            current_findings=findings,
            experiment_runs=experiment_runs,
        ))
        findings.extend(self._introspection_blind_spot_findings(
            experiment_runs=experiment_runs,
            findings_so_far=findings,
        ))
        findings.extend(self._metacognitive_calibration_findings(
            previous_review=previous_review,
            experiment_runs=experiment_runs,
        ))
        # Grounding gap: detect when OSES has concrete data but its brief
        # doesn't include the actual numbers — the system is being generic
        # when it should be specific.
        findings.extend(self._response_grounding_gap_findings(
            previous_review=previous_review,
            current_findings=findings,
        ))
        # Runtime log self-inspection: read own log tail and detect anomalies
        findings.extend(self._runtime_log_findings())
        # Fix 42-43: Functional gap analysis and underutilized resource detection
        findings.extend(self._functional_gap_findings())
        # Account/quota/worker health: detect exhausted quotas, API issues,
        # missing critical secrets — feeds cross-session learning.
        findings.extend(self._account_resource_health_findings())
        # Brecha 2.3: web session health — detect expired/missing browser sessions
        findings.extend(self._web_session_findings())
        # UI self-awareness: detect own window issues (zombie, missing, duplicate)
        findings.extend(self._ui_self_examination_findings(world=world))
        # Chat observability: detect chat persistence anomalies, reasoning
        # path imbalance and evidence tag gaps from ChatMessageRepository.
        findings.extend(self._chat_observability_findings())

        # RuntimePerformance: always runs — detects memory pressure, excessive
        # threads, slow network probes and other bottlenecks that cause the UI
        # to feel slow or frozen.
        findings.extend(self._runtime_performance_findings())

        # Background decision review (CognitiveMonitor): always runs — reads
        # DecisionAuditTrail and flags sub-optimal provider choices, confidence
        # miscalibration, and error stagnation.
        findings.extend(self._background_decision_review_findings(
            experiment_runs=experiment_runs,
        ))

        # TemporalAwareness: always runs — detects latency anomalies (z-score),
        # latency regressions, and stalled operations.
        findings.extend(self._temporal_awareness_findings(
            recent_runs=recent_runs,
            experiment_runs=experiment_runs,
        ))

        # C: Cognición profunda diferida — cuando la carga es baja, ejecutar
        # análisis más profundos que serían costosos bajo presión normal.
        # Cross-correlación de fallos, detección de tendencias, y decay de
        # estrategias. Solo se activa cuando _is_low_load() retorna True.
        if self._is_low_load(world):
            findings.extend(self._deferred_deep_cognition_findings(
                experiment_runs=experiment_runs,
                recent_runs=recent_runs,
                findings_so_far=findings,
            ))
            # DeepAnalysisQueue: statistical analysis (EMA drift, correlated
            # failures, IQR outliers) — only under low load.
            findings.extend(self._deep_analysis_queue_findings(
                experiment_runs=experiment_runs,
                recent_runs=recent_runs,
            ))
        # MetacognitionEvolution: aggregate findings from DecisionSimplifier,
        # PlatformLearning, and provider health monitoring.
        metacog = getattr(self, 'metacognition_evolution', None)
        if metacog is not None:
            try:
                from iabv_v15.domain.models import SelfExaminationFinding, IssueSeverity
                for raw in metacog.all_findings():
                    sev_str = str(raw.get('severity', 'MEDIUM')).upper()
                    try:
                        sev = IssueSeverity(sev_str)
                    except (ValueError, KeyError):
                        sev = IssueSeverity.MEDIUM
                    findings.append(SelfExaminationFinding(
                        category=raw.get('category', 'metacognition_evolution'),
                        title=raw.get('title', ''),
                        summary=raw.get('summary', ''),
                        severity=sev,
                        confidence=raw.get('confidence', 0.5),
                        recommendation=raw.get('recommendation', ''),
                        metadata=raw.get('metadata', {}),
                    ))
            except Exception as exc:
                logger.warning('oses: metacognition_evolution findings error: %s', exc)

        # CodeAuditTrail cross-referencing: detect recurring bug patterns
        # across external audits and flag modules needing cross-verification.
        findings.extend(self._code_audit_cross_reference_findings())

        # Task-packet pattern findings: detect recurring governance,
        # worker-gate and evidence-basis anomalies across recent runs.
        findings.extend(self._task_packet_pattern_findings(
            experiment_runs=experiment_runs,
        ))

        # Adaptive threshold N_c shift detection (Brecha 3.3)
        findings.extend(self._adaptive_threshold_shift_findings(
            previous_review=previous_review,
        ))

        # Windows platform integration: detect missing native capabilities
        # and emit structured findings that map to pending tasks.
        findings.extend(self._windows_integration_findings())

        # UniversalAutonomyIndex: calculate composite autonomy metrics from
        # data already accumulated in ExperimentLab, TaskOutcomeRecorder,
        # DecisionAuditTrail and WorldModel.  Produces a single finding
        # with AutonomyScore, ResilienceScore, CalibrationError, BlindSpotRatio.
        findings.extend(self._universal_autonomy_index_findings(
            recent_runs=recent_runs,
            adaptive_sessions=adaptive_sessions,
            experiment_runs=experiment_runs,
            world=world,
            findings_so_far=findings,
        ))

        # SQLite lock contention: read persisted incident from bootstrap
        findings.extend(self._sqlite_lock_contention_findings())

        # P0.5: Shared Reality Learning — detect repeated visual mismatch
        # patterns from shared_reality_handoff events in runtime_audit.jsonl.
        findings.extend(self._shared_reality_handoff_findings())

        # P0.7: Visual Remediation Learning — detect patterns from
        # visual_remediation_attempted events in runtime_audit.jsonl.
        findings.extend(self._visual_remediation_findings())

        # P0.27: External failure continuity learning. If the user repeatedly
        # has to explain/help after a security-verification block, surface it
        # as an algorithmic continuity gap instead of a one-off UI issue.
        findings.extend(self._external_failure_context_findings())
        findings.extend(self._external_failure_followup_misrouted_findings())

        findings = self._dedupe_findings(findings)

        recurring_issues = self._recurring_issues(findings=findings, project_health=project_health)
        recommended_adjustments = self._recommended_adjustments(findings=findings, backlog=backlog)
        validated_improvements = self._validated_improvements(
            recommendations=recommendations,
            validation=validation,
            experiment_runs=experiment_runs,
        )
        recommendation_feedback = self._recommendation_feedback(
            previous_review=previous_review,
            current_findings=findings,
            validated_improvements=validated_improvements,
            experiment_runs=experiment_runs,
            validation=validation,
        )
        feedback_summary = self._feedback_summary(recommendation_feedback)
        recommended_adjustments = self._apply_feedback_to_adjustments(
            recommended_adjustments=recommended_adjustments,
            recommendation_feedback=recommendation_feedback,
        )
        unresolved_risks = self._unresolved_risks(
            findings=findings,
            world=world,
            validation=validation,
            experiment_runs=experiment_runs,
            adaptive_sessions=adaptive_sessions,
        )
        status = self._status(findings=findings, unresolved_risks=unresolved_risks)
        summary = self._summary(
            status=status,
            findings=findings,
            validated_improvements=validated_improvements,
            recurring_issues=recurring_issues,
            feedback_summary=feedback_summary,
        )
        solution_proposals = self._solution_proposals(
            findings=findings,
            recommendations=recommendations,
            experiment_runs=experiment_runs,
            validated_improvements=validated_improvements,
        )
        review = SelfExaminationSnapshot(
            created_at_utc=now,
            updated_at_utc=now,
            summary=summary,
            status=status,
            findings=findings[:8],
            recurring_issues=recurring_issues[:6],
            recommended_adjustments=recommended_adjustments[:6],
            validated_improvements=validated_improvements[:4],
            unresolved_risks=unresolved_risks[:8],
            metadata={
                'recommendation_feedback': recommendation_feedback[:6],
                'feedback_summary': feedback_summary,
                'solution_proposals': solution_proposals[:4],
            },
        )
        # Metacognitive feedback loop: convert overconfidence/underconfidence
        # detections into adaptive weight adjustments so future scoring is
        # biased to self-correct.  Also tracks calibration improvement.
        mc_feedback = self._apply_metacognitive_feedback(
            findings, experiment_runs=experiment_runs,
        )
        if mc_feedback:
            review = review.model_copy(update={
                'findings': [*review.findings, *mc_feedback][:10],
                'metadata': {
                    **dict(review.metadata or {}),
                    'metacognitive_feedback': [
                        f.model_dump(mode='json') for f in mc_feedback
                    ],
                },
            })

        # Store current adaptive threshold N_c for next-review shift detection.
        try:
            nc_val = self._compute_current_adaptive_nc()
            if nc_val is not None:
                review = review.model_copy(update={
                    'metadata': {**dict(review.metadata or {}), 'adaptive_threshold_nc': nc_val},
                })
        except Exception:
            pass

        # Persist metacognitive ledger from the FULL findings list (before
        # truncation to 8) so MEDIUM-severity entries are not lost.
        self._persist_metacognitive_ledger_from_findings(
            findings, review_id=review.review_id,
        )
        persisted = self._persist_review(review)

        # Self-audit auto-correction loop: feed HIGH-severity findings
        # into the auto-correction engine for safe, automatic fixes.
        self._auto_correct_from_findings(findings)

        # Close the auto-improvement loop: materialize qualifying
        # task_packet findings as persistent pending issues so the
        # next evolution review picks them up as actionable backlog.
        self._materialize_task_packet_issues(findings)

        # Autonomy bridge: delegate to AutonomyCycleService if wired.
        # Falls back to inline bridge for backward compatibility.
        acs = getattr(self, '_autonomy_cycle_service', None)
        if acs is not None:
            try:
                acs.bridge_findings(findings)
            except Exception:
                logger.debug('oses: autonomy_cycle bridge failed, falling back')
                self._bridge_findings_to_pending_queue(findings)
        else:
            self._bridge_findings_to_pending_queue(findings)

        return persisted

    def _auto_correct_from_findings(
        self, findings: list[SelfExaminationFinding],
    ) -> None:
        """Attempt safe auto-corrections for HIGH-severity findings.

        Maps finding categories to auto-correction actions and delegates
        to ``auto_correction_engine`` if the action is marked safe.
        This closes the loop between detection and correction without
        creating a new orchestrator — OSES detects, AutoCorrection fixes.
        """
        _CATEGORY_TO_ACTION: dict[str, str] = {
            'background_provider_underperformance': 'degrade_provider_priority',
            'background_error_stagnation': 'block_failing_route',
            'temporal_latency_anomaly': 'flag_slow_provider',
            'cross_correlation_failure': 'reclassify_intent',
            'trend_degradation': 'trigger_diagnostic_scan',
        }
        actionable = [
            f for f in findings
            if f.severity in (IssueSeverity.HIGH,)
            and f.category in _CATEGORY_TO_ACTION
        ]
        if not actionable:
            return

        import logging
        logger = logging.getLogger(__name__)

        for finding in actionable[:3]:
            action_name = _CATEGORY_TO_ACTION[finding.category]
            try:
                from iabv_v15.services.auto_correction_engine import (
                    execute_corrections,
                )
                deductions = [{
                    'conclusion': finding.category,
                    'action': action_name,
                    'severity': finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                    'safe': True,
                    'description': finding.summary,
                    'source': 'oses_self_audit',
                    'finding_title': finding.title,
                }]
                result = execute_corrections(
                    deductions=deductions,
                    context={'source': 'oses_auto_correction', 'review_findings': True},
                )
                logger.info(
                    'oses_auto_correct: %s → %s (applied=%d)',
                    finding.category, action_name,
                    result.get('applied_count', 0),
                )
            except Exception as exc:
                logger.debug('oses_auto_correct: failed for %s: %s', finding.category, exc)

    def _apply_metacognitive_feedback(
        self,
        findings: list[SelfExaminationFinding],
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Convert metacognitive detection into adaptive weight adjustments.

        When OSES detects overconfidence, underconfidence, or miscalibration,
        this method feeds the signal into ``AdaptiveWeightLayer`` so future
        scoring is biased accordingly.  This converts the system from
        "detect and report" to "detect and self-correct".

        Also tracks whether calibration is improving across reviews
        (``loop_closure_improving``).
        """
        if self.adaptive_weight_layer is None:
            return []
        if not hasattr(self.adaptive_weight_layer, 'apply_metacognitive_adjustment'):
            return []

        results: list[SelfExaminationFinding] = []
        mc_categories = {
            'task_packet_metacognitive_overconfidence',
            'task_packet_metacognitive_underconfidence',
            'task_packet_metacognitive_miscalibration',
        }
        mc_findings = [f for f in findings if f.category in mc_categories]
        if not mc_findings:
            return results

        dominant_route = ''
        dominant_ak = ''
        if experiment_runs:
            from collections import Counter
            routes = Counter(
                getattr(r.route, 'value', str(r.route or ''))
                for r in experiment_runs if r.route
            )
            aks = Counter(
                str(r.assistant_kind or '').strip().lower()
                for r in experiment_runs if r.assistant_kind
            )
            dominant_route = routes.most_common(1)[0][0] if routes else ''
            dominant_ak = aks.most_common(1)[0][0] if aks else ''

        if not dominant_route:
            return results

        adjustments_applied: list[dict[str, Any]] = []
        for finding in mc_findings:
            if finding.category == 'task_packet_metacognitive_overconfidence':
                adj = -0.08
                reason = f'overconfidence detected: {finding.metadata.get("false_positive_count", 0)} false positives'
            elif finding.category == 'task_packet_metacognitive_underconfidence':
                adj = 0.06
                reason = f'underconfidence detected: {finding.metadata.get("false_negative_count", 0)} false negatives'
            else:
                avg_ce = finding.metadata.get('avg_calibration_error', 0.5)
                adj = -0.04 if avg_ce > 0.5 else -0.02
                reason = f'miscalibration detected: avg_error={avg_ce:.2f}'

            try:
                applied = self.adaptive_weight_layer.apply_metacognitive_adjustment(
                    route=dominant_route,
                    assistant_kind=dominant_ak,
                    adjustment=adj,
                    reason=reason,
                )
                adjustments_applied.append({
                    'finding': finding.category,
                    'route': dominant_route,
                    'assistant_kind': dominant_ak,
                    **applied,
                })
            except Exception:
                pass

        if adjustments_applied:
            results.append(SelfExaminationFinding(
                category='metacognitive_feedback_applied',
                severity=IssueSeverity.LOW,
                title=f'Ajuste adaptativo metacognitivo aplicado ({len(adjustments_applied)} ajustes)',
                summary=(
                    f'OSES detecto patrones metacognitivos y ajusto pesos '
                    f'adaptativos para {dominant_route}/{dominant_ak}. '
                    f'Ajustes: {", ".join(a["reason"] for a in adjustments_applied)}.'
                ),
                confidence=0.7,
                recommendation=(
                    'Monitorear si el calibration_error promedio mejora en '
                    'las proximas ejecuciones. Si no mejora, revisar la '
                    'formula de confianza en StrategySelector.'
                ),
                source_refs=['AdaptiveWeightLayer._metacognitive_adjustments'],
                metadata={
                    'pattern': 'metacognitive_feedback_loop',
                    'adjustments': adjustments_applied,
                    'dominant_route': dominant_route,
                    'dominant_assistant_kind': dominant_ak,
                },
            ))

        # --- Calibration improvement tracking ---
        previous_review = self._load_latest_review()
        if previous_review is not None:
            prev_meta = dict(previous_review.metadata or {})
            prev_cal = None
            for f in (previous_review.findings or []):
                if f.category == 'task_packet_metacognitive_miscalibration':
                    prev_cal = (f.metadata or {}).get('avg_calibration_error')
                    break
            if prev_cal is None:
                prev_cal = (prev_meta.get('last_avg_calibration_error'))

            current_cal = None
            for f in mc_findings:
                if f.category == 'task_packet_metacognitive_miscalibration':
                    current_cal = (f.metadata or {}).get('avg_calibration_error')
                    break

            if (
                isinstance(prev_cal, (int, float))
                and isinstance(current_cal, (int, float))
                and current_cal < prev_cal
            ):
                improvement = prev_cal - current_cal
                results.append(SelfExaminationFinding(
                    category='metacognitive_loop_closure_improving',
                    severity=IssueSeverity.LOW,
                    title=f'Calibracion metacognitiva mejorando ({improvement:.3f} reduccion)',
                    summary=(
                        f'El error de calibracion promedio bajo de {prev_cal:.3f} '
                        f'a {current_cal:.3f} (mejora de {improvement:.3f}). '
                        f'El feedback loop metacognitivo esta funcionando.'
                    ),
                    confidence=min(0.6 + improvement, 0.9),
                    recommendation=(
                        'Mantener el feedback loop activo. Si la mejora se '
                        'estabiliza, considerar reducir la magnitud de los '
                        'ajustes adaptativos.'
                    ),
                    source_refs=['AdaptiveWeightLayer._metacognitive_adjustments'],
                    metadata={
                        'pattern': 'loop_closure_improving',
                        'previous_avg_calibration_error': round(prev_cal, 4),
                        'current_avg_calibration_error': round(current_cal, 4),
                        'improvement': round(improvement, 4),
                        'loop_closure_improving': True,
                    },
                ))

        return results

    def _persist_review(self, review: SelfExaminationSnapshot) -> SelfExaminationSnapshot:
        embodiment_violations = self._collect_embodiment_violations()
        metadata_update: dict[str, Any] = {
            **dict(review.metadata or {}),
            'workspace_root': self.workspace_root,
            'source_refs': [
                'RunRepository',
                'AdaptiveSessionRepository',
                'ExperimentLab',
                'EvolutionReviewService',
                'WorldModelSnapshot',
                'AutonomousValidationSnapshot',
            ],
        }
        if embodiment_violations is not None:
            metadata_update['embodiment_violations'] = embodiment_violations
        # H4 — cierre del loop de autoexaminacion real (capa P4). Cuando el
        # self-exam detecta un hallazgo HIGH con alta confianza, la responsa-
        # bilidad del servicio no es solo "quejarse" en recommended_adjustments:
        # tambien debe dejar explicita la prueba reproducible concreta (scope,
        # evidence_refs, suggested_tests) lista para que el orquestador o la
        # UI la disparen. Antes esto se perdia en texto generico como
        # "Construir prueba reproducible del fallo" con last_feedback_status
        # == 'no_evidence', y ningun componente recogia ese testigo. No se
        # inventa un cerebro nuevo: solo se estructura la senal de probe para
        # que el AutonomousValidationCycle / ToolTeachService existentes la
        # consuman.
        metadata_update['pending_auto_probes'] = self._pending_auto_probes(
            findings=list(review.findings)
        )
        review = review.model_copy(
            update={
                'assistant_brief': self._render_assistant_brief(review),
                'package_path': str(self.storage.resolve('self_examination/latest.json')),
                'markdown_path': str(self.storage.resolve('self_examination/latest.md')),
                'metadata': metadata_update,
            }
        )
        archive_json_rel = f'self_examination/history/{review.review_id}.json'
        archive_md_rel = f'self_examination/history/{review.review_id}.md'
        latest_json_rel = 'self_examination/latest.json'
        latest_md_rel = 'self_examination/latest.md'
        payload = review.model_dump(mode='json')
        self.storage.save_json_atomic(archive_json_rel, payload)
        self.storage.save_bytes(archive_md_rel, review.assistant_brief.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, payload)
        self.storage.save_bytes(latest_md_rel, review.assistant_brief.encode('utf-8'))
        review.metadata.update(
            {
                'archive_json_path': str(self.storage.resolve(archive_json_rel)),
                'archive_markdown_path': str(self.storage.resolve(archive_md_rel)),
            }
        )
        self.storage.save_json_atomic(latest_json_rel, review.model_dump(mode='json'))
        return review

    def _collect_embodiment_violations(self) -> list[dict[str, Any]] | None:
        """Serializa el snapshot del provider de encarnamiento (si hay).

        Fail-observable: si el provider no está, devuelve ``None`` y el
        caller omite la clave de metadata. Si el provider falla en
        runtime, se come la excepción y se devuelve ``None`` — PCS v1
        declara ``handshake_required=False`` y no debe romper la
        autoexaminación.
        """

        provider = getattr(self, 'embodiment_violation_provider', None)
        if provider is None or not hasattr(provider, 'snapshot'):
            return None
        try:
            records = list(provider.snapshot() or [])
        except Exception:
            return None
        serialized: list[dict[str, Any]] = []
        for record in records:
            if hasattr(record, 'model_dump'):
                try:
                    serialized.append(record.model_dump(mode='json'))
                    continue
                except Exception:
                    pass
            if isinstance(record, dict):
                serialized.append(record)
        return serialized

    def _load_latest_review(self) -> SelfExaminationSnapshot | None:
        try:
            if not self.storage.exists('self_examination/latest.json'):
                return None
            payload = self.storage.load_json('self_examination/latest.json')
            return SelfExaminationSnapshot.model_validate(payload)
        except Exception:
            return None

    def _is_fresh(self, review: SelfExaminationSnapshot, *, max_age_seconds: int) -> bool:
        try:
            age_seconds = (utc_now() - review.updated_at_utc).total_seconds()
        except Exception:
            return False
        return age_seconds <= max_age_seconds

    def _recent_runs(self) -> list[RunRecord]:
        repository = self.run_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=60))
        except Exception:
            return []

    def _recent_adaptive_sessions(self) -> list[Any]:
        repository = self.adaptive_session_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=40))
        except Exception:
            return []

    def _recent_experiment_runs(self) -> list[ExperimentRun]:
        repository = self.experiment_lab_repository
        if repository is None or not hasattr(repository, 'list_runs'):
            return []
        try:
            return list(repository.list_runs(limit=60))
        except Exception:
            return []

    def _recent_recommendations(self) -> list[ExperimentRecommendation]:
        repository = self.experiment_lab_repository
        if repository is None or not hasattr(repository, 'list_recommendations'):
            return []
        try:
            return list(repository.list_recommendations(limit=12))
        except Exception:
            return []

    def _recent_scenario_runs(self) -> list[Any]:
        repository = self.scenario_run_repository
        if repository is None or not hasattr(repository, 'list_recent'):
            return []
        try:
            return list(repository.list_recent(limit=30))
        except Exception:
            return []

    def _project_health_snapshot(self) -> dict[str, Any]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_project_health'):
            return {}
        try:
            return service.build_project_health().model_dump(mode='json')
        except Exception:
            return {}

    def _improvement_backlog(self) -> list[dict[str, Any]]:
        service = self.evolution_review_service
        if service is None or not hasattr(service, 'build_improvement_backlog'):
            return []
        try:
            return [item.model_dump(mode='json') for item in service.build_improvement_backlog(limit=8)]
        except Exception:
            return []

    def _world_model(self) -> WorldModelSnapshot:
        service = self.world_model_service
        if service is None or not hasattr(service, 'current_model'):
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])
        try:
            return service.current_model()
        except Exception:
            return WorldModelSnapshot(unresolved_fields=['UNRESOLVED:world_model'])

    def _validation_snapshot(self) -> AutonomousValidationSnapshot:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return AutonomousValidationSnapshot(
                status='idle',
                unresolved_fields=['UNRESOLVED:validation_cycle'],
            )
        try:
            return service.current_snapshot()
        except Exception:
            return AutonomousValidationSnapshot(
                status='degraded',
                unresolved_fields=['UNRESOLVED:validation_cycle'],
            )

    # Ventana de recurrencia real para "fallo repetido". Runs anteriores a
    # este margen se consideran historia fria y no cuentan, evitando que un
    # fallo viejo unico quede atrapado en `list_recent(limit=60)` como si
    # fuera recurrencia.
    _RECURRING_FAILURE_WINDOW = timedelta(hours=48)

    # Umbral para promover un hallazgo a auto-probe. Por debajo de 0.85 la
    # evidencia del self-exam no es lo suficientemente fuerte como para
    # pedirle al orquestador que gaste ciclos de validacion; por encima, el
    # silencio de no generar probe concreto es peor (capa P4 se queda muda).
    _AUTO_PROBE_CONFIDENCE_FLOOR = 0.85

    def _pending_auto_probes(
        self,
        *,
        findings: list[SelfExaminationFinding],
    ) -> list[dict[str, Any]]:
        """Derivar probe requests concretos para findings HIGH + alta confianza.

        El servicio no ejecuta la prueba: sólo deja la tarjeta lista para que
        el orquestador (``AdaptiveTaskOrchestrator``), la UI
        (``EvolutionCenterViewModel``) o el ciclo de validación autónoma la
        consuman. Respeta los contratos de las capas cerradas P1–P4: no crea
        otro cerebro, ni duplica ``PerceptionSnapshot``, ni toma decisiones de
        ruta por su cuenta.
        """
        probes: list[dict[str, Any]] = []
        now = utc_now()
        for finding in findings:
            if getattr(finding.severity, 'value', str(finding.severity)) != IssueSeverity.HIGH.value:
                continue
            confidence = float(finding.confidence or 0.0)
            if confidence < self._AUTO_PROBE_CONFIDENCE_FLOOR:
                continue
            suggested_tests = self._auto_probe_suggested_tests(finding=finding)
            if not suggested_tests:
                continue
            metadata = dict(finding.metadata or {})
            scope = str(
                metadata.get('scope')
                or metadata.get('pack_id')
                or metadata.get('block')
                or metadata.get('token_name')
                or ''
            ).strip()
            probes.append(
                {
                    'finding_id': finding.finding_id,
                    'category': finding.category,
                    'scope': scope,
                    'title': finding.title,
                    'severity': getattr(finding.severity, 'value', str(finding.severity)),
                    'confidence': confidence,
                    'evidence_refs': list(finding.evidence_refs[:4]),
                    'source_refs': list(finding.source_refs[:4]),
                    'suggested_tests': suggested_tests,
                    'trigger_reason': (
                        f'Finding HIGH \'{finding.category}\' con confianza '
                        f'{confidence:.2f} >= {self._AUTO_PROBE_CONFIDENCE_FLOOR:.2f}; '
                        f'autotests=0 no cierra el loop P4.'
                    ),
                    'requested_at_utc': now.isoformat(),
                    'status': 'requested',
                }
            )
        return probes[:6]

    def _auto_probe_suggested_tests(
        self,
        *,
        finding: SelfExaminationFinding,
    ) -> list[str]:
        """Sugerencia de prueba concreta por categoría de finding.

        Las sugerencias son comandos/descripciones estables que el orquestador
        puede mapear a un runner real. No se lanza nada desde aquí.
        """
        metadata = dict(finding.metadata or {})
        category = str(finding.category or '').strip().lower()
        if category == 'recurring_failure':
            scope = str(metadata.get('scope') or '').strip()
            tests = ['pytest -q -p no:cacheprovider tests/']
            run_ids = [ref for ref in finding.evidence_refs[:3] if str(ref).strip()]
            if run_ids:
                tests.append(f"reproduce_run_ids={','.join(run_ids)}")
            if scope:
                tests.append(f'scope={scope}')
            return tests
        if category == 'repeated_stall':
            pack_id = str(metadata.get('pack_id') or '').strip()
            tests = ['revisar defaults y readiness del pack en sandbox']
            if pack_id:
                tests.append(f'pack_id={pack_id}')
            return tests
        if category == 'route_inertia':
            return ['re-lanzar contendiente vs ganador en ExperimentLab']
        if category == 'repeated_block':
            block = str(metadata.get('block') or '').strip()
            return [f'replay con block={block}'] if block else []
        if category == 'weak_correction':
            return ['recapturar escena con anotacion reforzada']
        if category == 'token_rotation':
            token_name = str(metadata.get('token_name') or '').strip()
            tests: list[str] = ['powershell -ExecutionPolicy Bypass -File scripts\\rotate_tokens.ps1']
            if token_name:
                tests.append(f'token_name={token_name}')
            return tests
        return []

    def _recurring_failure_findings(self, *, recent_runs: list[RunRecord]) -> list[SelfExaminationFinding]:
        now = utc_now()
        window_start = now - self._RECURRING_FAILURE_WINDOW
        grouped: dict[str, dict[str, RunRecord]] = defaultdict(dict)
        for run in recent_runs:
            # Solo FAILED cuenta como fallo real; PARTIAL es "resuelto parcial",
            # no es un fallo a repetir. Antes se agrupaban ambos y eso generaba
            # falsos positivos tipo "Fallo repetido en general:training".
            if run.status != RunStatus.FAILED:
                continue
            if run.created_at_utc and run.created_at_utc < window_start:
                continue
            # Dedup defensivo por run_id: garantiza que un mismo run repetido
            # en la lista (retry logging, etc.) no se cuente dos veces.
            grouped[self._task_scope(run)].setdefault(run.run_id, run)
        findings: list[SelfExaminationFinding] = []
        for scope, runs_by_id in grouped.items():
            runs = list(runs_by_id.values())
            if len(runs) < 2:
                continue
            severity = IssueSeverity.HIGH if len(runs) >= 3 else IssueSeverity.MEDIUM
            findings.append(
                SelfExaminationFinding(
                    category='recurring_failure',
                    title=f'Fallo repetido en {scope}',
                    summary=(
                        f'La clase de tarea {scope} acumula {len(runs)} corridas fallidas '
                        f'en las ultimas {int(self._RECURRING_FAILURE_WINDOW.total_seconds() // 3600)} horas.'
                    ),
                    severity=severity,
                    confidence=min(0.92, 0.45 + len(runs) * 0.12),
                    recommendation=f'Revisar la ruta, el pack y la evidencia previa antes de repetir {scope}.',
                    evidence_refs=[run.run_id for run in runs[:4]],
                    source_refs=['RunRepository'],
                    linked_run_ids=[run.run_id for run in runs[:10]],
                    metadata={
                        'scope': scope,
                        'failed_count': len(runs),
                        'window_hours': int(self._RECURRING_FAILURE_WINDOW.total_seconds() // 3600),
                    },
                )
            )
        return findings

    def _pack_stall_findings(self, *, adaptive_sessions: list[Any]) -> list[SelfExaminationFinding]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        stalled_statuses = {
            AdaptiveSessionStatus.NEED_INFO.value,
            AdaptiveSessionStatus.WAITING_APPROVAL.value,
            AdaptiveSessionStatus.FAILED.value,
        }
        for session in adaptive_sessions:
            status = str(getattr(getattr(session, 'status', None), 'value', getattr(session, 'status', '')) or '')
            if status not in stalled_statuses:
                continue
            pack_id = str(getattr(session, 'chosen_pack_id', '') or 'pack_desconocido')
            grouped[pack_id].append(session)
        findings: list[SelfExaminationFinding] = []
        for pack_id, sessions in grouped.items():
            if len(sessions) < 2:
                continue
            findings.append(
                SelfExaminationFinding(
                    category='repeated_stall',
                    title=f'Pack atascado: {pack_id}',
                    summary=f'El pack {pack_id} reaparece {len(sessions)} veces en need_info, waiting_approval o failed.',
                    severity=IssueSeverity.MEDIUM,
                    confidence=min(0.9, 0.42 + len(sessions) * 0.14),
                    recommendation=f'Revisar defaults, readiness y preguntas obligatorias del pack {pack_id}.',
                    evidence_refs=[str(getattr(session, 'session_id', '') or '') for session in sessions[:4]],
                    source_refs=['AdaptiveSessionRepository'],
                    metadata={
                        'pack_id': pack_id,
                        'statuses': [
                            str(getattr(getattr(session, 'status', None), 'value', getattr(session, 'status', '')) or '')
                            for session in sessions[:4]
                        ],
                    },
                )
            )
        return findings

    def _route_inertia_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recommendations: list[ExperimentRecommendation],
    ) -> list[SelfExaminationFinding]:
        if not experiment_runs:
            return []
        grouped_runs: dict[tuple[object, str, str], list[ExperimentRun]] = defaultdict(list)
        for run in experiment_runs:
            key = (
                run.route,
                str(run.assistant_kind or '').strip().lower(),
                str(run.config_signature or '').strip(),
            )
            grouped_runs[key].append(run)
        profiles = (
            self.adaptive_weight_layer.suggest(grouped_runs=grouped_runs)
            if self.adaptive_weight_layer is not None
            else {}
        )
        recommended_keys = {
            (
                recommendation.recommended_route,
                str(recommendation.recommended_assistant_kind or '').strip().lower(),
                str(recommendation.recommended_config_signature or '').strip(),
            )
            for recommendation in recommendations
        }
        findings: list[SelfExaminationFinding] = []
        for key, profile in profiles.items():
            sample_count = int(profile.get('sample_count') or 0)
            if sample_count < 3:
                continue
            blocked_rate = float(profile.get('blocked_rate') or 0.0)
            fallback_rate = float(profile.get('fallback_rate') or 0.0)
            success_rate = float(profile.get('success_rate') or 0.0)
            trend_score = float(profile.get('trend_score') or 0.0)
            if blocked_rate < 0.34 and fallback_rate < 0.34 and success_rate >= 0.55 and trend_score > -0.12:
                continue
            route, assistant_kind, config_signature = key
            route_value = str(getattr(route, 'value', route) or '')
            recommendation = (
                'Exigir validacion adicional antes de reutilizar esta ruta.'
                if blocked_rate >= 0.34 or fallback_rate >= 0.34
                else 'Debilitar esta preferencia hasta que la tendencia vuelva a mejorar.'
            )
            if key in recommended_keys:
                recommendation += ' Hoy sigue apareciendo como preferencia y conviene revisar si se mantiene por inercia.'
            findings.append(
                SelfExaminationFinding(
                    category='inertial_route',
                    title=f'Ruta debil o inercial: {assistant_kind or "asistente_base"} por {route_value}',
                    summary=(
                        f'Se reutilizo {sample_count} veces con exito {success_rate:.0%}, '
                        f'bloqueos {blocked_rate:.0%}, fallback {fallback_rate:.0%} y tendencia {trend_score:+.2f}.'
                    ),
                    severity=IssueSeverity.HIGH if blocked_rate >= 0.5 or success_rate < 0.45 else IssueSeverity.MEDIUM,
                    confidence=min(0.94, 0.46 + sample_count * 0.08),
                    recommendation=recommendation,
                    evidence_refs=[run.run_id for run in grouped_runs[key][:4]],
                    source_refs=['ExperimentLab', 'AdaptiveWeightLayer'],
                    linked_run_ids=[run.run_id for run in grouped_runs[key][:10]],
                    metadata={
                        'route': route_value,
                        'assistant_kind': assistant_kind,
                        'config_signature': config_signature,
                        'profile': dict(profile),
                        'currently_recommended': key in recommended_keys,
                    },
                )
            )
        return findings

    def _repeated_block_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        world: WorldModelSnapshot,
    ) -> list[SelfExaminationFinding]:
        block_counts: Counter[str] = Counter()
        evidence: dict[str, list[str]] = defaultdict(list)
        for run in experiment_runs:
            metadata = dict(run.metadata or {})
            flags = [str(item).strip() for item in (metadata.get('external_state_flags') or []) if str(item).strip()]
            for flag in flags:
                block_counts[flag] += 1
                evidence[flag].append(run.run_id)
        current_blocks = {str(item).strip() for item in (world.detected_blocks or []) if str(item).strip()}
        findings: list[SelfExaminationFinding] = []
        for flag, count in block_counts.most_common():
            if count < 2:
                continue
            active_now = flag in current_blocks
            recommendation = f'No reintentar rutas afectadas por {flag} hasta verificar la condicion operativa.'
            if active_now:
                recommendation += ' El world model la sigue reportando en este momento.'
            findings.append(
                SelfExaminationFinding(
                    category='repeated_block',
                    title=f'Bloqueo recurrente: {flag}',
                    summary=f'El bloqueo {flag} reaparecio {count} veces en corridas comparables.',
                    severity=IssueSeverity.HIGH if active_now or count >= 3 else IssueSeverity.MEDIUM,
                    confidence=min(0.95, 0.48 + count * 0.1),
                    recommendation=recommendation,
                    evidence_refs=evidence[flag][:5],
                    source_refs=['ExperimentLab', 'WorldModelSnapshot'],
                    linked_run_ids=evidence[flag][:10],
                    metadata={
                        'block': flag,
                        'count': count,
                        'active_now': active_now,
                    },
                )
            )
        return findings

    def _weak_correction_findings(self, *, scenario_runs: list[Any]) -> list[SelfExaminationFinding]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for scenario_run in scenario_runs:
            scenario_id = str(getattr(getattr(scenario_run, 'scenario', None), 'scenario_id', '') or '')
            if not scenario_id:
                continue
            grouped[scenario_id].append(scenario_run)
        findings: list[SelfExaminationFinding] = []
        for scenario_id, runs in grouped.items():
            weak_runs = []
            for scenario_run in runs:
                adjustments = list(getattr(scenario_run, 'runtime_adjustments', []) or [])
                pending_issue_id = str(getattr(scenario_run, 'pending_issue_id', '') or '')
                diagnosis = getattr(scenario_run, 'diagnosis', None)
                category = str(getattr(getattr(diagnosis, 'category', None), 'value', getattr(diagnosis, 'category', '')) or '')
                if adjustments and (pending_issue_id or category == 'need_codex_fix'):
                    weak_runs.append(scenario_run)
                    continue
                guided_cycle = dict(getattr(scenario_run, 'metadata', {}).get('guided_improvement_cycle') or {})
                if int(guided_cycle.get('applied_count') or 0) > 0 and pending_issue_id:
                    weak_runs.append(scenario_run)
            if not weak_runs:
                continue
            findings.append(
                SelfExaminationFinding(
                    category='weak_correction',
                    title=f'Correccion debil en {scenario_id}',
                    summary=(
                        f'Los ajustes o correcciones guiadas del escenario {scenario_id} no cerraron el problema '
                        f'y terminaron en pending issue o need_codex_fix.'
                    ),
                    severity=IssueSeverity.HIGH if len(weak_runs) >= 2 else IssueSeverity.MEDIUM,
                    confidence=min(0.9, 0.5 + len(weak_runs) * 0.12),
                    recommendation=f'Dejar de iterar solo con tuning runtime en {scenario_id} y escalar a cambio verificable.',
                    evidence_refs=[str(getattr(run, 'scenario_run_id', '') or '') for run in weak_runs[:4]],
                    source_refs=['ScenarioRunRepository', 'GuidedImprovementCycle'],
                    metadata={
                        'scenario_id': scenario_id,
                        'occurrences': len(weak_runs),
                    },
                )
            )
        return findings

    def _token_rotation_findings(self) -> list[SelfExaminationFinding]:
        """Hallazgos proactivos sobre rotacion de tokens (capa 2.2).

        Lee el ``TokenRotationLedger`` inyectado por ``bootstrap``. Si no
        hay ledger o todavia no hay eventos registrados, devuelve lista
        vacia (NO inventa observacion). Reglas:

        - ``expired_live`` en la ultima observacion -> HIGH, recomienda
          ``scripts/rotate_tokens.ps1`` ya.
        - ``proactive_due`` (projected_expiry <= lead_time y al menos una
          rotacion previa) -> HIGH: cerrar el loop antes del 401.
        - ``stale`` (sin probe OK reciente) pero sin 401 observado ->
          MEDIUM: quizas el sistema dejo de mirar, quizas el token ya
          no se usa; pide un probe explicito.
        """
        ledger = getattr(self, 'token_rotation_ledger', None)
        if ledger is None or not hasattr(ledger, 'predictions'):
            return []
        try:
            predictions = list(ledger.predictions() or [])
        except Exception:
            return []
        findings: list[SelfExaminationFinding] = []
        for pred in predictions:
            if not isinstance(pred, dict):
                continue
            token_name = str(pred.get('token_name') or '').strip()
            if not token_name:
                continue
            expired = bool(pred.get('expired_live'))
            proactive = bool(pred.get('proactive_due'))
            stale = bool(pred.get('stale'))
            if not (expired or proactive or stale):
                continue

            if expired:
                severity = IssueSeverity.HIGH
                confidence = 0.93
                title = f'Token {token_name} expirado: rotar ya'
                summary = (
                    f'La ultima observacion del token {token_name} fue un probe fallido '
                    f'(probe_failed). El sistema dejo de autenticar contra su endpoint '
                    f'y cualquier ruta externa dependiente esta rota hasta rotar.'
                )
            elif proactive:
                severity = IssueSeverity.HIGH
                confidence = 0.87
                days = pred.get('days_until_projected_expiry')
                days_txt = f'{days:.1f}d' if isinstance(days, (int, float)) else 'pronto'
                title = f'Rotacion proactiva de {token_name} ({days_txt})'
                summary = (
                    f'Por el promedio observado ({pred.get("avg_interval_days") or 0:.1f} dias '
                    f'entre rotaciones pasadas, {pred.get("rotations_observed")} muestras) '
                    f'el token {token_name} expirara en {days_txt}. Rotar antes evita 401.'
                )
            else:  # stale
                severity = IssueSeverity.MEDIUM
                confidence = 0.6
                title = f'Observabilidad stale en {token_name}'
                summary = (
                    f'No hay un probe OK reciente del token {token_name}. No implica '
                    f'caducidad real, pero el sistema perdio la senal. Falta probe '
                    f'contra el endpoint autenticado para reestablecer observabilidad.'
                )

            findings.append(
                SelfExaminationFinding(
                    category='token_rotation',
                    title=title,
                    summary=summary,
                    severity=severity,
                    confidence=confidence,
                    recommendation=(
                        'Ejecutar scripts/rotate_tokens.ps1 (device-flow de GitHub + '
                        'prompt seguro de Devin API key). Es idempotente y solo actualiza '
                        '~/.iabv_secrets.ps1 cuando el probe post-rotacion da 200 OK.'
                    ),
                    evidence_refs=[
                        ref for ref in (
                            pred.get('last_probe_ok_at'),
                            pred.get('last_probe_failed_at'),
                            pred.get('last_rotation_at'),
                        ) if ref
                    ],
                    source_refs=['TokenRotationLedger'],
                    metadata={
                        'token_name': token_name,
                        'expired_live': expired,
                        'proactive_due': proactive,
                        'stale': stale,
                        'avg_interval_days': pred.get('avg_interval_days'),
                        'days_until_projected_expiry': pred.get('days_until_projected_expiry'),
                        'projected_expiry_at': pred.get('projected_expiry_at'),
                        'rotations_observed': pred.get('rotations_observed'),
                    },
                )
            )
        return findings

    def _auto_capture_startup_freeze(
        self,
        startup_findings: list[SelfExaminationFinding],
    ) -> None:
        """Fire FreezeIncidentReporter when startup findings are HIGH+.

        Called from ``build_review()`` after ``_startup_health_findings()``
        returns.  Only fires if ``_freeze_incident_reporter`` has been
        wired from bootstrap and at least one finding has severity >= HIGH.
        Dedup is handled by FreezeIncidentReporter._should_auto_capture().
        """
        reporter = self._freeze_incident_reporter
        if reporter is None:
            return
        high_findings = [
            f for f in startup_findings
            if getattr(f, 'severity', None) in (
                IssueSeverity.HIGH, IssueSeverity.CRITICAL,
            )
        ]
        if not high_findings:
            return
        # A memory spike is an anomaly, not a freeze by itself.  Keep it as an
        # OSES finding, but do not promote it to FreezeIncidentReporter unless
        # another high-severity finding also proves blocking, false readiness,
        # or a timed startup degradation.  This keeps "observed resource
        # growth" separate from "user-visible frozen UI".
        high_findings = [
            f for f in high_findings
            if getattr(f, 'category', '') != 'startup_memory_spike'
        ]
        high_findings = [
            f for f in high_findings
            if not (
                getattr(f, 'category', '') == 'startup_false_ready'
                and self._latest_timeline_contradicts_false_ready()
            )
        ]
        if not high_findings:
            return
        if self._should_defer_startup_false_ready_capture(high_findings):
            return
        try:
            findings_meta = [
                {
                    'category': f.category,
                    'title': f.title,
                    'severity': str(f.severity),
                    'metadata': dict(f.metadata or {}),
                }
                for f in high_findings
            ]
            path = reporter.capture_startup_freeze(
                findings_metadata=findings_meta,
            )
            if path is not None:
                from iabv_v15.services.evolution.runtime_audit_tracer import (
                    get_runtime_tracer,
                )
                tracer = get_runtime_tracer()
                dominant = high_findings[0]
                meta = dict(dominant.metadata or {})
                tracer.trace_freeze_incident(
                    'startup_freeze',
                    severity=str(dominant.severity),
                    duration_ms=float(
                        meta.get('observed_ms')
                        or meta.get('sync_blocking_ms')
                        or 0,
                    ),
                    dominant_phase=str(meta.get('phase', '')),
                    rss_mb=0.0,
                    report_path=str(path),
                )
        except Exception:
            logger.debug('_auto_capture_startup_freeze failed', exc_info=True)

    def _latest_timeline_contradicts_false_ready(self) -> bool:
        """Return True when the latest startup timeline proves readiness.

        This is a final evidence check before promoting a false-ready finding
        into a freeze incident. If the live timeline says
        ``shell_loader_ready`` or ``page_loader_ready`` happened before
        ``splash_set_ready``, the finding is stale or based on incomplete
        metadata and must not become a freeze report.
        """
        log_path = Path(self.workspace_root or Path.cwd()) / 'data' / 'logs' / 'startup_timeline.jsonl'
        if not log_path.exists():
            return False
        events: list[dict[str, Any]] = []
        try:
            with log_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return False
        if not events:
            return False
        last_run: list[dict[str, Any]] = [events[-1]]
        for evt in reversed(events[:-1]):
            try:
                if float(evt.get('t_ms_from_start') or 0.0) <= float(last_run[0].get('t_ms_from_start') or 0.0):
                    last_run.insert(0, evt)
                else:
                    break
            except (TypeError, ValueError):
                break
        phase_to_ms: dict[str, float] = {}
        for evt in last_run:
            phase = str(evt.get('phase') or '')
            if not phase:
                continue
            try:
                phase_to_ms[phase] = float(evt.get('t_ms_from_start') or 0.0)
            except (TypeError, ValueError):
                continue
        splash_ms = phase_to_ms.get('splash_set_ready')
        if splash_ms is None:
            return False
        for proof in ('page_loader_ready', 'shell_loader_ready'):
            proof_ms = phase_to_ms.get(proof)
            if proof_ms is not None and proof_ms <= splash_ms:
                return True
        return False

    def _should_defer_startup_false_ready_capture(
        self,
        high_findings: list[SelfExaminationFinding],
    ) -> bool:
        """Avoid auto-capturing missing-readiness findings before evidence settles.

        A startup finding based on lack of readiness proof is provisional while
        the current boot is still writing ``startup_timeline.jsonl``. Live P0.17
        showed FreezeIncidentReporter firing with ``startup_timeline=[]`` even
        though the real log later contained shell/page readiness. Ordering
        violations can be captured immediately; missing-proof findings must wait
        for the observation window.
        """
        missing_proof_categories = {
            'splash_set_ready_without_readiness_proof',
            'splash_set_ready_without_shell_loader_ready',
            'shell_loader_ready_fallback_used',
        }
        has_provisional_false_ready = False
        for finding in high_findings:
            if getattr(finding, 'category', '') != 'startup_false_ready':
                continue
            metadata = dict(getattr(finding, 'metadata', {}) or {})
            reasons = {str(item) for item in (metadata.get('reasons') or [])}
            if reasons & missing_proof_categories:
                has_provisional_false_ready = True
                break
        if not has_provisional_false_ready:
            return False
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            elapsed_ms = float(get_runtime_tracer().current_elapsed_ms())
        except Exception:
            elapsed_ms = 0.0
        return elapsed_ms < 120_000.0

    def _ui_heartbeat_stall_findings(self) -> list[SelfExaminationFinding]:
        """Emit findings from UIHeartbeatWatchdog stall history."""
        watchdog = getattr(self, '_ui_heartbeat_watchdog', None)
        if watchdog is None:
            return []
        try:
            summary = watchdog.summary()
        except Exception:
            return []
        stall_count = summary.get('stall_count', 0)
        if stall_count == 0:
            return []
        recent = summary.get('recent_stalls', [])
        worst_ms = max(
            (s.get('duration_ms', 0) for s in recent), default=0,
        )
        severity = IssueSeverity.HIGH if worst_ms > 5000 else IssueSeverity.MEDIUM
        phases = [s.get('dominant_phase', '') for s in recent if s.get('dominant_phase')]
        dominant = phases[0] if phases else 'unknown'
        return [
            SelfExaminationFinding(
                title=f'UI event loop stalls: {stall_count} detected (worst {worst_ms:.0f}ms)',
                summary=(
                    f'{stall_count} heartbeat stalls detected. '
                    f'Worst: {worst_ms:.0f}ms. Dominant phase: {dominant}.'
                ),
                severity=severity,
                category='ui_heartbeat_stall',
                confidence=0.95,
                recommendation=(
                    f'Investigate blocking on main thread during phase "{dominant}". '
                    'Consider moving heavy work to background threads or adding '
                    'yield-to-event-loop calls.'
                ),
                metadata={
                    'stall_count': stall_count,
                    'worst_ms': worst_ms,
                    'dominant_phase': dominant,
                    'recent_stalls': recent[-3:],
                    'tick_count': summary.get('tick_count', 0),
                },
            )
        ]

    def _interaction_episode_findings(self) -> list[SelfExaminationFinding]:
        """Emit findings for recent interaction episodes from runtime_audit.jsonl.

        Reads the durable audit trail so that episodes are visible even if
        the in-memory ``ChatInteractionLifecycle`` object was lost (process
        death, OOM, etc.).

        Deduplicates by ``interaction_id``: only the most recent event per
        id is kept so that a ``prepared`` followed by ``resolved`` for the
        same id counts once (as resolved), not twice.
        """
        import json as _json
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        seen_ids: set[str] = set()
        episodes: list[dict[str, Any]] = []
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    event = _json.loads(line)
                except Exception:
                    continue
                if event.get('kind') not in ('interaction_resolved', 'interaction_outcome'):
                    continue
                data = dict(event.get('data') or {})
                iid = data.get('interaction_id', '')
                if iid and iid in seen_ids:
                    continue
                if iid:
                    seen_ids.add(iid)
                episodes.append(data)
                if len(episodes) >= 5:
                    break
        except Exception:
            return []
        if not episodes:
            return []
        episodes.reverse()
        findings: list[SelfExaminationFinding] = []
        stall_episodes = [
            e for e in episodes if len(e.get('stalls_during') or []) > 0
        ]
        failed_episodes = [
            e for e in episodes if e.get('outcome') == 'failed'
        ]
        if stall_episodes:
            ep_details: list[str] = []
            for ep in stall_episodes:
                sc = len(ep.get('stalls_during') or [])
                ep_details.append(
                    f'[{ep.get("interaction_id", "?")}] '
                    f'"{str(ep.get("message_preview", ""))[:40]}" '
                    f'provider={ep.get("provider", "?")} '
                    f'duration={ep.get("total_duration_ms", 0)}ms '
                    f'stalls={sc} '
                    f'early_technical={ep.get("had_early_technical_response", False)} '
                    f'window_inactive={ep.get("window_went_inactive", False)}'
                )
            findings.append(SelfExaminationFinding(
                title=f'Interaction episodes with UI stalls: {len(stall_episodes)} of {len(episodes)} recent',
                summary=(
                    f'{len(stall_episodes)} of the last {len(episodes)} interaction episodes '
                    f'had UI stalls. Episodes: ' + '; '.join(ep_details)
                ),
                severity=IssueSeverity.MEDIUM,
                category='interaction_episode_stalls',
                confidence=0.9,
                recommendation='Investigate UI thread blocking during chat interactions.',
                metadata={
                    'stall_episode_count': len(stall_episodes),
                    'total_episodes': len(episodes),
                    'stall_episodes': stall_episodes,
                    'source': 'runtime_audit',
                },
            ))
        if failed_episodes:
            ep_details_f: list[str] = []
            for ep in failed_episodes:
                ep_details_f.append(
                    f'[{ep.get("interaction_id", "?")}] '
                    f'"{str(ep.get("message_preview", ""))[:40]}" '
                    f'provider={ep.get("provider", "?")} '
                    f'duration={ep.get("total_duration_ms", 0)}ms '
                    f'stalls={len(ep.get("stalls_during") or [])} '
                    f'early_technical={ep.get("had_early_technical_response", False)} '
                    f'window_inactive={ep.get("window_went_inactive", False)}'
                )
            findings.append(SelfExaminationFinding(
                title=f'Failed interaction episodes: {len(failed_episodes)} of {len(episodes)} recent',
                summary=(
                    f'{len(failed_episodes)} of the last {len(episodes)} interaction episodes '
                    f'ended with outcome=failed. Episodes: ' + '; '.join(ep_details_f)
                ),
                severity=IssueSeverity.MEDIUM,
                category='interaction_episode_failures',
                confidence=0.9,
                recommendation='Review failed interactions for patterns.',
                metadata={
                    'failed_count': len(failed_episodes),
                    'total_episodes': len(episodes),
                    'failed_episodes': failed_episodes,
                    'source': 'runtime_audit',
                },
            ))
        # Blocked episodes: terminal but not successful (is_final=true, resolved=false)
        blocked_episodes = [
            e for e in episodes if e.get('outcome') == 'blocked'
        ]
        if blocked_episodes:
            ep_details_b: list[str] = []
            for ep in blocked_episodes:
                ep_details_b.append(
                    f'[{ep.get("interaction_id", "?")}] '
                    f'"{str(ep.get("message_preview", ""))[:40]}" '
                    f'outcome=blocked '
                    f'provider={ep.get("provider", "?")}'
                )
            findings.append(SelfExaminationFinding(
                title=f'Blocked interaction episodes: {len(blocked_episodes)} of {len(episodes)} recent',
                summary=(
                    f'{len(blocked_episodes)} of the last {len(episodes)} interaction episodes '
                    f'were blocked (terminal, not resolved). Episodes: '
                    + '; '.join(ep_details_b)
                ),
                severity=IssueSeverity.MEDIUM,
                category='interaction_episode_blocked',
                confidence=0.9,
                recommendation='Review blocked interactions for access, quota or preflight issues.',
                metadata={
                    'blocked_count': len(blocked_episodes),
                    'total_episodes': len(episodes),
                    'blocked_episodes': blocked_episodes,
                    'source': 'runtime_audit',
                },
            ))
        # Non-final outcomes: prepared/reused_context/awaiting_external_response
        # NOTE: blocked is NOT pending — it is terminal (is_final=true).
        non_final_outcomes = {'prepared', 'awaiting_external_response', 'reused_context'}
        pending_episodes = [
            e for e in episodes
            if e.get('outcome') in non_final_outcomes
            or (not e.get('is_final', True) and e.get('outcome') not in ('resolved', 'failed', 'blocked'))
        ]
        if pending_episodes:
            ep_details_p: list[str] = []
            for ep in pending_episodes:
                ep_details_p.append(
                    f'[{ep.get("interaction_id", "?")}] '
                    f'"{str(ep.get("message_preview", ""))[:40]}" '
                    f'outcome={ep.get("outcome", "?")} '
                    f'provider={ep.get("provider", "?")}'
                )
            findings.append(SelfExaminationFinding(
                title=f'Non-resolved interaction episodes: {len(pending_episodes)} pending',
                summary=(
                    f'{len(pending_episodes)} interaction episode(s) have non-final outcomes '
                    f'(prepared/reused_context/awaiting_external_response). '
                    f'These should NOT be presented as resolved. Episodes: '
                    + '; '.join(ep_details_p)
                ),
                severity=IssueSeverity.LOW,
                category='interaction_episode_pending',
                confidence=0.9,
                recommendation=(
                    'External consultations with outcome=prepared/reused_context/awaiting_external_response '
                    'are NOT resolved. Track until actual external response is captured.'
                ),
                metadata={
                    'pending_count': len(pending_episodes),
                    'total_episodes': len(episodes),
                    'pending_episodes': pending_episodes,
                    'source': 'runtime_audit',
                },
            ))
        return findings

    def _dispatch_lifecycle_anomaly_findings(self) -> list[SelfExaminationFinding]:
        """P0.22: detect consultation dispatch lifecycle anomalies.

        Reads runtime_audit.jsonl and detects three patterns:
        1. Repeated external_consultation blocked by resource_pressure.
        2. observation_permission grant immediately followed by
           external_consultation blocked for a non-permission reason.
        3. dispatch_terminal with empty interaction_id after
           dispatch_started had an interaction_id.
        """
        import json as _json
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        try:
            lines = audit_path.read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError:
            return []

        resource_pressure_blocks: list[dict[str, Any]] = []
        permission_grants: list[dict[str, Any]] = []
        started_events: dict[str, dict[str, Any]] = {}
        orphan_interaction_pairs: list[dict[str, Any]] = []
        grant_then_block_pairs: list[dict[str, Any]] = []

        for line in lines[-500:]:
            if not line.strip():
                continue
            try:
                event = _json.loads(line)
            except Exception:
                continue
            kind = event.get('kind', '')
            data = dict(event.get('data') or {})

            if kind == 'dispatch_terminal':
                task = data.get('task_name', '')
                reason = str(data.get('reason') or '').lower()
                dispatch_id = data.get('dispatch_id', '')
                terminal_iid = data.get('interaction_id', '')
                terminal_state = data.get('terminal_state', '')
                if task == 'external_consultation' and (
                    'resource_pressure' in reason
                    or 'presion de recursos' in reason
                    or terminal_state == 'blocked_by_resource_pressure'
                ):
                    resource_pressure_blocks.append(data)
                started = started_events.pop(dispatch_id, None)
                if started and started.get('interaction_id') and not terminal_iid:
                    orphan_interaction_pairs.append({
                        'dispatch_id': dispatch_id,
                        'started_interaction_id': started.get('interaction_id', ''),
                        'terminal_interaction_id': terminal_iid,
                    })
            elif kind == 'dispatch_started':
                did = data.get('dispatch_id', '')
                if did:
                    started_events[did] = data
            elif kind == 'permission':
                action = data.get('action', '')
                if action == 'granted' and 'observation' in str(data.get('permission_id', '')).lower():
                    permission_grants.append(data)

        for grant in permission_grants:
            grant_ts = grant.get('timestamp', '')
            for block in resource_pressure_blocks:
                block_ts = block.get('timestamp', '')
                if grant_ts and block_ts and block_ts > grant_ts:
                    grant_then_block_pairs.append({
                        'grant': grant,
                        'subsequent_block': block,
                    })
                    break

        findings: list[SelfExaminationFinding] = []

        if len(resource_pressure_blocks) >= 2:
            findings.append(SelfExaminationFinding(
                category='dispatch_lifecycle_anomaly',
                title=f'Repeated external_consultation blocked by resource_pressure ({len(resource_pressure_blocks)}x)',
                summary=(
                    f'external_consultation was blocked by resource_pressure '
                    f'{len(resource_pressure_blocks)} times in recent audit events. '
                    f'This indicates persistent environment degradation.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.92,
                recommendation=(
                    'Represent resource_pressure blocks as deferred (not failed). '
                    'Do not re-dispatch external consultation while pressure persists. '
                    'Disambiguate user permission replies from status questions.'
                ),
                evidence_refs=[
                    str(b.get('dispatch_id', ''))[:12] for b in resource_pressure_blocks[:5]
                ],
                source_refs=['runtime_audit'],
                metadata={
                    'pattern': 'repeated_resource_pressure_block',
                    'count': len(resource_pressure_blocks),
                },
            ))

        if grant_then_block_pairs:
            findings.append(SelfExaminationFinding(
                category='dispatch_lifecycle_anomaly',
                title='Permission grant followed by non-permission block',
                summary=(
                    f'observation_permission was granted but the subsequent '
                    f'external_consultation was blocked for resource_pressure '
                    f'({len(grant_then_block_pairs)} occurrence(s)). '
                    f'The permission grant was likely a misclassified status question.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.88,
                recommendation=(
                    'Disambiguate permission replies from operational status questions. '
                    'Only grant observation_permission when an actual '
                    'observation_permission checkpoint exists and the user sends '
                    'an explicit permission phrase.'
                ),
                evidence_refs=[
                    str(p.get('subsequent_block', {}).get('dispatch_id', ''))[:12]
                    for p in grant_then_block_pairs[:3]
                ],
                source_refs=['runtime_audit'],
                metadata={
                    'pattern': 'grant_then_non_permission_block',
                    'count': len(grant_then_block_pairs),
                },
            ))

        if orphan_interaction_pairs:
            findings.append(SelfExaminationFinding(
                category='dispatch_lifecycle_anomaly',
                title=f'dispatch_terminal with empty interaction_id ({len(orphan_interaction_pairs)}x)',
                summary=(
                    f'{len(orphan_interaction_pairs)} dispatch(es) had interaction_id '
                    f'in dispatch_started but empty interaction_id in dispatch_terminal. '
                    f'The local interaction was closed before the external worker finished.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.90,
                recommendation=(
                    'Preserve interaction correlation: do not close active_interaction '
                    'when an external worker is still alive. Use outcome '
                    'awaiting_external_response instead of resolved.'
                ),
                evidence_refs=[
                    p.get('dispatch_id', '')[:12] for p in orphan_interaction_pairs[:5]
                ],
                source_refs=['runtime_audit'],
                metadata={
                    'pattern': 'orphan_interaction_id',
                    'count': len(orphan_interaction_pairs),
                    'pairs': orphan_interaction_pairs[:5],
                },
            ))

        return findings

    def _startup_health_findings(self) -> list[SelfExaminationFinding]:
        """Read ``data/logs/startup_timeline.jsonl`` and emit degradation findings.

        Cable A del marco de simbiosis: el JSONL deja de ser log suelto.  Esta
        funcion lo lee, identifica la ultima corrida contigua y emite un
        ``SelfExaminationFinding`` por cada umbral cruzado.  Sin servicio nuevo,
        sin memoria paralela.

        Thresholds at module top: ``STARTUP_INIT_MS_DEGRADED``,
        ``STARTUP_RUN_TO_WINDOW_MS_DEGRADED``, ``STARTUP_DEFERRED_MS_DEGRADED``.

        If the JSONL is missing or has no parseable events, no finding is
        emitted (the PortableContext snapshot will already carry the
        ``UNRESOLVED:startup_timeline_*`` flag).
        """
        log_path = Path(self.workspace_root) / 'data' / 'logs' / 'startup_timeline.jsonl'
        if not log_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            with log_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        if not events:
            return []
        last_run: list[dict[str, Any]] = [events[-1]]
        for evt in reversed(events[:-1]):
            try:
                if float(evt.get('t_ms_from_start') or 0.0) <= float(last_run[0].get('t_ms_from_start') or 0.0):
                    last_run.insert(0, evt)
                else:
                    break
            except (TypeError, ValueError):
                break
        phase_to_ms: dict[str, float] = {}
        for evt in last_run:
            phase = str(evt.get('phase') or '')
            if not phase:
                continue
            try:
                phase_to_ms[phase] = float(evt.get('t_ms_from_start') or 0.0)
            except (TypeError, ValueError):
                continue

        def _delta(a: str, b: str) -> float | None:
            if a in phase_to_ms and b in phase_to_ms:
                return phase_to_ms[b] - phase_to_ms[a]
            return None

        init_ms = _delta('bootstrap_init_start', 'bootstrap_init_done')
        run_to_window_ms = _delta('run_start', 'main_window_shown')
        if run_to_window_ms is None:
            run_to_window_ms = _delta('bootstrap_init_done', 'main_window_shown')
        deferred_ms = _delta('deferred_post_window_setup_start', 'deferred_post_window_setup_done')

        findings: list[SelfExaminationFinding] = []
        if init_ms is not None and init_ms > STARTUP_INIT_MS_DEGRADED:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title=f'Bootstrap init lento: {init_ms:.0f}ms',
                summary=(
                    f'El paso bootstrap_init_start->bootstrap_init_done duro '
                    f'{init_ms:.0f}ms (umbral {STARTUP_INIT_MS_DEGRADED:.0f}ms). '
                    f'Esto retiene el GUI thread antes de que aparezca el splash.'
                ),
                severity=IssueSeverity.HIGH if init_ms > STARTUP_INIT_MS_DEGRADED * 2 else IssueSeverity.MEDIUM,
                confidence=0.9,
                recommendation=(
                    'Diferir scans de cuentas, instalacion de mcp_client y probes '
                    'de proveedores de bootstrap.__init__ a un QTimer post-show. '
                    'Patron ya aplicado a _log_tool_availability en PR #257.'
                ),
                source_refs=['data/logs/startup_timeline.jsonl', 'iabv_v15.infra.startup_timeline'],
                metadata={
                    'phase': 'bootstrap_init',
                    'observed_ms': round(init_ms, 1),
                    'threshold_ms': STARTUP_INIT_MS_DEGRADED,
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))
        if run_to_window_ms is not None and run_to_window_ms > STARTUP_RUN_TO_WINDOW_MS_DEGRADED:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title=f'Run -> ventana visible lento: {run_to_window_ms:.0f}ms',
                summary=(
                    f'El tramo desde run_start hasta main_window_shown duro '
                    f'{run_to_window_ms:.0f}ms (umbral '
                    f'{STARTUP_RUN_TO_WINDOW_MS_DEGRADED:.0f}ms). El usuario ve '
                    f'splash congelado durante ese tiempo.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.9,
                recommendation=(
                    'Verificar que engine.load(Main.qml), construccion de '
                    'ViewModels y poblacion inicial no corran en GUI thread '
                    'sincronicamente. Mover trabajos pesados al QTimer.singleShot '
                    'post-show o a workers QThread.'
                ),
                source_refs=['data/logs/startup_timeline.jsonl', 'iabv_v15.infra.startup_timeline'],
                metadata={
                    'phase': 'run_to_main_window',
                    'observed_ms': round(run_to_window_ms, 1),
                    'threshold_ms': STARTUP_RUN_TO_WINDOW_MS_DEGRADED,
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))
        if deferred_ms is not None and deferred_ms > STARTUP_DEFERRED_MS_DEGRADED:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title=f'Setup post-ventana lento: {deferred_ms:.0f}ms',
                summary=(
                    f'deferred_post_window_setup duro {deferred_ms:.0f}ms '
                    f'(umbral {STARTUP_DEFERRED_MS_DEGRADED:.0f}ms). Aunque la '
                    f'ventana ya es visible, el sistema sigue cargado y la '
                    f'primera interaccion puede sentirse lenta.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Revisar _log_tool_availability, scans de providers e '
                    'instalaciones automaticas que arrancan post-show. Mover a '
                    'QTimer encadenados o gating por demanda real.'
                ),
                source_refs=['data/logs/startup_timeline.jsonl', 'iabv_v15.infra.startup_timeline'],
                metadata={
                    'phase': 'deferred_post_window',
                    'observed_ms': round(deferred_ms, 1),
                    'threshold_ms': STARTUP_DEFERRED_MS_DEGRADED,
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))

        # ``startup_false_ready`` — detect when the splash declared readiness
        # dishonestly.  With phased construction, ``populate_ui_done``
        # arrives long after ``splash_set_ready`` (Phase 3 VMs are deferred)
        # so ``splash < populate_done`` is EXPECTED and NOT a bug.
        #
        # Readiness proof is hierarchical:
        # 1. ``page_loader_ready`` proves the real internal page exists and is
        #    stronger than the shell signal.
        # 2. ``shell_loader_ready`` proves the shell loader exists.
        # 3. fallback is a degraded proof only when no honest signal exists.
        #
        # Live P0.17 evidence showed page_loader_ready -> splash_set_ready but
        # no shell_loader_ready mark. Treating that as false-ready teaches the
        # organism the wrong failure, so the proof hierarchy must win.
        splash_ms = phase_to_ms.get('splash_set_ready')
        populate_done_ms = phase_to_ms.get('populate_ui_done')
        page_ready_ms = phase_to_ms.get('page_loader_ready')
        shell_ready_ms = phase_to_ms.get('shell_loader_ready')
        shell_ready_fallback_ms = phase_to_ms.get('shell_loader_ready_fallback')
        readiness_proof_ms = page_ready_ms if page_ready_ms is not None else shell_ready_ms
        readiness_proof_phase = (
            'page_loader_ready'
            if page_ready_ms is not None
            else 'shell_loader_ready'
            if shell_ready_ms is not None
            else ''
        )
        false_ready_reasons: list[str] = []
        if splash_ms is not None and readiness_proof_ms is not None and splash_ms < readiness_proof_ms:
            false_ready_reasons.append(f'splash_set_ready_before_{readiness_proof_phase}')
        if (
            splash_ms is not None
            and readiness_proof_ms is None
            and shell_ready_fallback_ms is None
        ):
            false_ready_reasons.append('splash_set_ready_without_readiness_proof')
        if shell_ready_fallback_ms is not None and readiness_proof_ms is None:
            false_ready_reasons.append('shell_loader_ready_fallback_used')
        if false_ready_reasons:
            findings.append(SelfExaminationFinding(
                category='startup_false_ready',
                title='Splash declaro ready antes de que el shell estuviera vivo',
                summary=(
                    'splash.set_ready() se emitio sin que el shell QML real '
                    '(mainShellLoader) estuviera disponible. La ventana visible '
                    'fue una ApplicationWindow vacia con ViewModels en None. '
                    f'Razones: {", ".join(false_ready_reasons)}.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.95,
                recommendation=(
                    'Diferir splash.set_ready() hasta que MainWindowBridge '
                    'reciba shellLoaderReady desde QML (Loader.onStatusChanged '
                    '== Loader.Ready en mainShellLoader). Mantener fallback '
                    'determinista (IABV_SHELL_READY_FALLBACK_MS, default 5s) '
                    'para no congelar el splash si la senal QML nunca llega.'
                ),
                source_refs=[
                    'data/logs/startup_timeline.jsonl',
                    'iabv_v15.bootstrap._handle_shell_loader_ready',
                    'iabv_v15.ui.controllers.main_window_bridge',
                    'src/iabv_v15/ui/qml/Main.qml',
                ],
                metadata={
                    'phase': 'startup_false_ready',
                    'reasons': false_ready_reasons,
                    'splash_set_ready_ms': splash_ms,
                    'populate_ui_done_ms': populate_done_ms,
                    'page_loader_ready_ms': page_ready_ms,
                    'shell_loader_ready_ms': shell_ready_ms,
                    'shell_loader_ready_fallback_ms': shell_ready_fallback_ms,
                    'readiness_proof_phase': readiness_proof_phase,
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))

        # ``qml_event_loop_starvation`` — detect when the fallback timer
        # took much longer than expected (wall_clock >> timer_ms), indicating
        # the Qt main thread was blocked by QML incubation and couldn't
        # process the QTimer until it unblocked.
        for evt in last_run:
            if str(evt.get('phase') or '') == 'shell_loader_ready_fallback':
                wall_clock_ms = evt.get('wall_clock_ms', 0)
                expected_ms = evt.get('expected_ms', 5000)
                starved = evt.get('event_loop_starved', False)
                if starved and wall_clock_ms > 0:
                    starvation_seconds = (wall_clock_ms - expected_ms) / 1000.0
                    findings.append(SelfExaminationFinding(
                        category='qml_event_loop_starvation',
                        title=(
                            f'Qt main thread bloqueado {starvation_seconds:.0f}s '
                            f'por QML incubation'
                        ),
                        summary=(
                            f'El fallback de shell_loader_ready se programo a '
                            f'{expected_ms}ms pero tardo {wall_clock_ms:.0f}ms '
                            f'en ejecutarse (wall clock). El Qt main thread '
                            f'estuvo bloqueado {starvation_seconds:.0f}s por la '
                            f'incubacion del mainShellLoader QML. Durante ese '
                            f'tiempo el proceso aparece como Not Responding.'
                        ),
                        severity=IssueSeverity.CRITICAL,
                        confidence=0.95,
                        recommendation=(
                            'El freeze no es Python/GIL — es QML incubation '
                            'bloqueando el Qt event loop. Opciones: (1) reducir '
                            'el component tree del mainShellLoader, (2) usar '
                            'QQmlIncubationController para limitar objetos por '
                            'frame, (3) fragmentar la carga QML en sub-Loaders '
                            'con asynchronous=true escalonados.'
                        ),
                        source_refs=[
                            'data/logs/startup_timeline.jsonl',
                            'iabv_v15.bootstrap._force_splash_ready_fallback',
                            'src/iabv_v15/ui/qml/Main.qml',
                        ],
                        metadata={
                            'phase': 'qml_event_loop_starvation',
                            'wall_clock_ms': round(wall_clock_ms, 1),
                            'expected_ms': expected_ms,
                            'starvation_seconds': round(starvation_seconds, 1),
                            'phases_seen': list(phase_to_ms.keys()),
                        },
                    ))
                break

        # ``startup_populate_ui_freeze`` — the interval where all ViewModels
        # are constructed on the main thread.  Windsurf live testing on
        # 2026-05-01 shows 30s+ blocks here (273MB→495MB RSS), causing
        # Windows "Not Responding".  OSES previously measured run_start →
        # main_window_shown (7.7s, under threshold) and missed the real
        # freeze that happens AFTER the window is already visible.
        #
        # Phased architecture awareness (PR #307+): when
        # ``populate_ui_critical_done`` exists the boot uses a phased
        # pipeline where populate_ui_done fires AFTER an async
        # page_loader_ready wait — the total span is NOT main-thread
        # blocking time.  Measure synchronous phases individually.
        populate_start_ms = phase_to_ms.get('populate_ui_start')
        populate_done_ms_val = phase_to_ms.get('populate_ui_done')
        critical_done_ms = phase_to_ms.get('populate_ui_critical_done')
        deferred_1_start_ms = phase_to_ms.get('populate_ui_deferred_1_start')
        deferred_1_done_ms = phase_to_ms.get('populate_ui_deferred_1_done')

        if populate_start_ms is not None and populate_done_ms_val is not None:
            is_phased = critical_done_ms is not None
            if is_phased:
                # Phased boot: measure only the synchronous phases.
                phase_1_ms = (critical_done_ms - populate_start_ms) if critical_done_ms is not None else 0.0
                phase_d1_ms = (
                    (deferred_1_done_ms - deferred_1_start_ms)
                    if deferred_1_start_ms is not None and deferred_1_done_ms is not None
                    else 0.0
                )
                sync_blocking_ms = phase_1_ms + phase_d1_ms
                total_span_ms = populate_done_ms_val - populate_start_ms
                if sync_blocking_ms > STARTUP_POPULATE_UI_MS_DEGRADED:
                    findings.append(SelfExaminationFinding(
                        category='startup_populate_ui_freeze',
                        title=f'populate_ui fases sincronas bloquean: {sync_blocking_ms:.0f}ms',
                        summary=(
                            f'Las fases sincronas de populate_ui suman '
                            f'{sync_blocking_ms:.0f}ms (phase1={phase_1_ms:.0f}ms, '
                            f'deferred1={phase_d1_ms:.0f}ms). Umbral: '
                            f'{STARTUP_POPULATE_UI_MS_DEGRADED:.0f}ms.'
                        ),
                        severity=IssueSeverity.CRITICAL if sync_blocking_ms > 15000 else IssueSeverity.HIGH,
                        confidence=0.95,
                        recommendation=(
                            'Reducir la duracion de las fases sincronas '
                            'moviendo trabajo pesado a deferred init o '
                            'background threads.'
                        ),
                        source_refs=[
                            'data/logs/startup_timeline.jsonl',
                            'iabv_v15.bootstrap._build_ui_objects',
                        ],
                        metadata={
                            'phase': 'populate_ui_phased',
                            'sync_blocking_ms': round(sync_blocking_ms, 1),
                            'phase_1_ms': round(phase_1_ms, 1),
                            'deferred_1_ms': round(phase_d1_ms, 1),
                            'total_span_ms': round(total_span_ms, 1),
                            'threshold_ms': STARTUP_POPULATE_UI_MS_DEGRADED,
                            'phases_seen': list(phase_to_ms.keys()),
                        },
                    ))
            else:
                # Legacy synchronous boot: measure the full span.
                populate_duration = populate_done_ms_val - populate_start_ms
                if populate_duration > STARTUP_POPULATE_UI_MS_DEGRADED:
                    findings.append(SelfExaminationFinding(
                        category='startup_populate_ui_freeze',
                        title=f'populate_ui bloqueo main thread: {populate_duration:.0f}ms',
                        summary=(
                            f'La construccion de ViewModels (populate_ui_start → '
                            f'populate_ui_done) duro {populate_duration:.0f}ms '
                            f'(umbral {STARTUP_POPULATE_UI_MS_DEGRADED:.0f}ms). '
                            f'Durante este intervalo el hilo principal esta bloqueado '
                            f'y Windows reporta el proceso como "Not Responding".'
                        ),
                        severity=IssueSeverity.CRITICAL if populate_duration > 15000 else IssueSeverity.HIGH,
                        confidence=0.95,
                        recommendation=(
                            'Migrar a phased populate_ui para construir VMs '
                            'en fases con event loop yields entre cada una.'
                        ),
                        source_refs=[
                            'data/logs/startup_timeline.jsonl',
                            'iabv_v15.bootstrap._build_ui_objects',
                        ],
                        metadata={
                            'phase': 'populate_ui',
                            'observed_ms': round(populate_duration, 1),
                            'threshold_ms': STARTUP_POPULATE_UI_MS_DEGRADED,
                            'populate_ui_start_ms': round(populate_start_ms, 1),
                            'populate_ui_done_ms': round(populate_done_ms_val, 1),
                            'phases_seen': list(phase_to_ms.keys()),
                        },
                    ))
        elif populate_start_ms is not None and populate_done_ms_val is None:
            latest_phase_ms = max(phase_to_ms.values(), default=populate_start_ms)
            pending_ms = max(0.0, latest_phase_ms - populate_start_ms)
            if pending_ms >= STARTUP_POPULATE_UI_INCOMPLETE_MIN_MS:
                findings.append(SelfExaminationFinding(
                    category='startup_populate_ui_incomplete',
                    title='populate_ui no termino tras espera prolongada',
                    summary=(
                        f'populate_ui_start llego a {populate_start_ms:.0f}ms '
                        f'y no existe populate_ui_done tras {pending_ms:.0f}ms '
                        f'de eventos posteriores. Esto sugiere bloqueo real o '
                        f'perdida del marcador final.'
                    ),
                    severity=IssueSeverity.CRITICAL,
                    confidence=0.9,
                    recommendation=(
                        'Cruzar con UIHeartbeatWatchdog antes de asumir freeze '
                        'permanente. Si no hubo stall real, corregir el marcador '
                        'populate_ui_done en bootstrap.'
                    ),
                    source_refs=[
                        'data/logs/startup_timeline.jsonl',
                        'iabv_v15.bootstrap._build_ui_objects',
                        'iabv_v15.bootstrap._populate_ui',
                    ],
                    metadata={
                        'phase': 'populate_ui_incomplete',
                        'populate_ui_start_ms': round(populate_start_ms, 1),
                        'observed_ms': round(pending_ms, 1),
                        'threshold_ms': STARTUP_POPULATE_UI_INCOMPLETE_MIN_MS,
                        'phases_seen': list(phase_to_ms.keys()),
                    },
                ))

        # RSS growth detection during startup.  Extract RSS values from
        # events that carry them.
        rss_values: list[tuple[str, float]] = []
        for evt in last_run:
            rss_mb = evt.get('rss_mb')
            phase = str(evt.get('phase') or '')
            if rss_mb is not None and phase:
                try:
                    rss_values.append((phase, float(rss_mb)))
                except (TypeError, ValueError):
                    pass
        if len(rss_values) >= 2:
            min_rss = min(v for _, v in rss_values)
            max_rss = max(v for _, v in rss_values)
            rss_growth = max_rss - min_rss
            if rss_growth > STARTUP_RSS_GROWTH_MB_DEGRADED:
                max_phase = next(p for p, v in rss_values if v == max_rss)
                min_phase = next(p for p, v in rss_values if v == min_rss)
                findings.append(SelfExaminationFinding(
                    category='startup_memory_spike',
                    title=f'RSS crecio {rss_growth:.0f}MB durante startup',
                    summary=(
                        f'RSS paso de {min_rss:.0f}MB ({min_phase}) a '
                        f'{max_rss:.0f}MB ({max_phase}), un crecimiento de '
                        f'{rss_growth:.0f}MB (umbral {STARTUP_RSS_GROWTH_MB_DEGRADED:.0f}MB). '
                        f'Esto puede causar presion de memoria y GC stalls.'
                    ),
                    severity=IssueSeverity.HIGH if rss_growth > 300 else IssueSeverity.MEDIUM,
                    confidence=0.9,
                    recommendation=(
                        'Revisar que ViewModels con defer_initial_refresh=True '
                        'no hagan queries pesados en el constructor. Verificar '
                        'que _log_tool_availability() no cree objetos grandes.'
                    ),
                    source_refs=[
                        'data/logs/startup_timeline.jsonl',
                    ],
                    metadata={
                        'phase': 'startup_rss_growth',
                        'min_rss_mb': round(min_rss, 1),
                        'max_rss_mb': round(max_rss, 1),
                        'growth_mb': round(rss_growth, 1),
                        'threshold_mb': STARTUP_RSS_GROWTH_MB_DEGRADED,
                        'min_phase': min_phase,
                        'max_phase': max_phase,
                    },
                ))

        # Process-start readiness metrics for metacognitive tracking.
        # Extract t_ms_from_process when available.
        phase_to_process_ms: dict[str, float] = {}
        for evt in last_run:
            phase = str(evt.get('phase') or '')
            if phase and 't_ms_from_process' in evt:
                try:
                    phase_to_process_ms[phase] = float(evt['t_ms_from_process'])
                except (TypeError, ValueError):
                    pass

        readiness_metadata: dict[str, Any] = {
            'phases_seen': list(phase_to_ms.keys()),
            'fallback_used': shell_ready_fallback_ms is not None,
        }
        for key, phases in [
            ('process_to_shell_loader_ready_ms', ['shell_loader_ready', 'shell_loader_ready_fallback']),
            ('process_to_page_loader_ready_ms', ['page_loader_ready']),
            ('process_to_splash_window_closing_ms', ['splash_window_closing']),
        ]:
            val: float | None = None
            for phase in phases:
                if phase in phase_to_process_ms:
                    val = round(phase_to_process_ms[phase], 1)
                    break
                if phase in phase_to_ms:
                    val = round(phase_to_ms[phase], 1)
                    break
            readiness_metadata[key] = val

        # If shell_loader_ready took >12s from process start, flag it.
        slr_ms = readiness_metadata.get('process_to_shell_loader_ready_ms')
        if slr_ms is not None and slr_ms > 12000.0:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title=f'Shell readiness lenta: {slr_ms:.0f}ms desde process start',
                summary=(
                    f'process_to_shell_loader_ready_ms = {slr_ms:.0f}ms. '
                    f'El shell QML tardo mas de 12s en estar listo. '
                    f'Verificar si deferred_post_window_setup bloquea '
                    f'el event loop (debe correr en background thread).'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Mover _run_deferred_post_window_setup a un thread '
                    'background para no bloquear el QML incubator.'
                ),
                source_refs=['data/logs/startup_timeline.jsonl'],
                metadata=readiness_metadata,
            ))

        # ``dashboard_vm_refresh_slow`` — detect when the initial dashboard
        # data load took too long.  Since PR fix-dashboard-refresh-freeze
        # this runs on a background thread and does NOT block the GUI, but
        # a slow refresh still means the user sees empty summary cards for
        # a long time.
        dash_refresh_ms = _delta('dashboard_vm_refresh_start', 'dashboard_vm_refresh_done')
        if dash_refresh_ms is not None and dash_refresh_ms > 5000.0:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title=f'Dashboard refresh lento: {dash_refresh_ms:.0f}ms',
                summary=(
                    f'dashboard_vm_refresh tardo {dash_refresh_ms:.0f}ms '
                    f'(umbral 5000ms). Aunque corre en background thread '
                    f'y no bloquea la UI, el usuario ve tarjetas vacias '
                    f'durante ese tiempo.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Optimizar queries lentas en KnowledgeRepository y '
                    'RunRepository (medidos en >17s cada uno). Considerar '
                    'caching o queries con LIMIT reducido.'
                ),
                source_refs=[
                    'data/logs/startup_timeline.jsonl',
                    'iabv_v15.ui.viewmodels.dashboard_viewmodel',
                ],
                metadata={
                    'phase': 'dashboard_vm_refresh',
                    'observed_ms': round(dash_refresh_ms, 1),
                    'threshold_ms': 5000.0,
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))
        dash_failed = 'dashboard_vm_refresh_failed' in phase_to_ms
        if dash_failed:
            findings.append(SelfExaminationFinding(
                category='startup_degradation',
                title='Dashboard refresh fallo durante startup',
                summary=(
                    'dashboard_vm_refresh_failed se registro en el timeline. '
                    'Las tarjetas de resumen quedaron vacias.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.95,
                recommendation=(
                    'Revisar logs de DashboardViewModel para el error '
                    'especifico. Verificar que la DB SQLite no este '
                    'corrompida o bloqueada.'
                ),
                source_refs=[
                    'data/logs/startup_timeline.jsonl',
                    'iabv_v15.ui.viewmodels.dashboard_viewmodel',
                ],
                metadata={
                    'phase': 'dashboard_vm_refresh_failed',
                    'phases_seen': list(phase_to_ms.keys()),
                },
            ))

        return findings

    # ------------------------------------------------------------------
    # SQLite lock contention findings — persisted by bootstrap
    # ------------------------------------------------------------------

    def _startup_birth_audit_findings(self) -> list[SelfExaminationFinding]:
        """Detect startup attempts that never reached RuntimeAuditTracer."""
        try:
            from iabv_v15.infra.startup_audit import startup_audit_snapshot
            snapshot = startup_audit_snapshot(self.workspace_root)
        except Exception:
            return []
        unresolved = set(snapshot.get('unresolved_fields') or [])
        findings: list[SelfExaminationFinding] = []
        if 'UNRESOLVED:startup_attempt_without_runtime_fingerprint' in unresolved:
            findings.append(SelfExaminationFinding(
                category='startup_birth_blind_spot',
                title='Startup intento arrancar pero no llego a runtime_fingerprint',
                summary=(
                    'El launcher/PowerShell registro un startup_attempt, pero '
                    'RuntimeAuditTracer no registro runtime_build_fingerprint '
                    'para ese intento. El sistema no puede probar que Python '
                    'haya tomado control del arranque.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.9,
                recommendation=(
                    'Revisar startup_audit.jsonl, iabv_start.lock y procesos '
                    'start_iabv.ps1/run_mcp_bridge.ps1 activos antes de asumir '
                    'que la UI cargo el codigo actual.'
                ),
                source_refs=['data/logs/startup_audit.jsonl', 'data/logs/runtime_audit.jsonl'],
                unresolved_fields=['UNRESOLVED:startup_attempt_without_runtime_fingerprint'],
                metadata={
                    'attempt_id': snapshot.get('attempt_id', ''),
                    'last_event': snapshot.get('last_event', ''),
                    'events_seen': list(snapshot.get('events_seen') or []),
                },
            ))
        if 'UNRESOLVED:suspected_hung_start' in unresolved:
            findings.append(SelfExaminationFinding(
                category='startup_birth_blind_spot',
                title='Lock de arranque apunta a proceso vivo pero sospechoso',
                summary=(
                    'El lock de startup no era claramente removible: el PID '
                    'seguia vivo despues del periodo de arranque. Esto puede '
                    'bloquear doble click/reintentos mientras la UI no esta viva.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Mantener el lock solo durante la fase de nacimiento y '
                    'registrar procesos antiguos sin matarlos automaticamente.'
                ),
                source_refs=['data/logs/startup_audit.jsonl'],
                unresolved_fields=['UNRESOLVED:suspected_hung_start'],
                metadata={'attempt_id': snapshot.get('attempt_id', '')},
            ))
        stale_lock_count = int(snapshot.get('stale_lock_count') or 0)
        if stale_lock_count >= 2:
            findings.append(SelfExaminationFinding(
                category='startup_birth_blind_spot',
                title='Locks de arranque stale repetidos',
                summary=(
                    f'Se removieron {stale_lock_count} locks stale en el '
                    'historial reciente de startup_audit.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation='Auditar por que start_iabv.ps1 no libero el lock al terminar la fase de arranque.',
                source_refs=['data/logs/startup_audit.jsonl'],
                metadata={'stale_lock_count': stale_lock_count},
            ))
        hidden_process_count = int(snapshot.get('hidden_process_count') or 0)
        if hidden_process_count >= 2:
            findings.append(SelfExaminationFinding(
                category='startup_birth_blind_spot',
                title='Procesos de arranque ocultos repetidos',
                summary=(
                    f'startup_audit detecto {hidden_process_count} procesos '
                    'start_iabv/run_mcp_bridge antiguos. No se mataron '
                    'automaticamente porque la propiedad del proceso es ambigua.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.8,
                recommendation='Mostrar esta evidencia al usuario y reiniciar solo procesos con ownership inequivoco.',
                source_refs=['data/logs/startup_audit.jsonl'],
                unresolved_fields=['UNRESOLVED:startup_process_ownership_ambiguous'],
                metadata={'hidden_process_count': hidden_process_count},
            ))
        return findings

    def _sqlite_lock_contention_findings(self) -> list[SelfExaminationFinding]:
        """Read ``startup_sqlite_incident.json`` if persisted by bootstrap.

        When ``_record_startup_sqlite_incident`` fires during startup,
        it writes a structured incident file.  This method reads it and
        promotes it to a proper OSES finding so it appears in the review
        and in PortableContext.
        """
        findings: list[SelfExaminationFinding] = []
        try:
            incident_path = Path(self.evolution_dir) / 'self_examination' / 'startup_sqlite_incident.json'
            if not incident_path.exists():
                return findings
            import json
            incident = json.loads(incident_path.read_text(encoding='utf-8'))
            findings.append(SelfExaminationFinding(
                category=incident.get('category', 'sqlite_lock_contention'),
                title=incident.get('title', 'database is locked durante startup'),
                summary=incident.get('summary', ''),
                severity=IssueSeverity.HIGH,
                confidence=incident.get('confidence', 0.95),
                recommendation=incident.get('recommendation', ''),
                source_refs=incident.get('source_refs', []),
                metadata={
                    'incident_timestamp': incident.get('timestamp', ''),
                    'error': incident.get('error', ''),
                    'source': 'startup_sqlite_incident.json',
                },
            ))
        except Exception:
            pass
        return findings

    # ------------------------------------------------------------------
    # Boot profile findings — read-only analysis of BootProfileStore
    # ------------------------------------------------------------------

    def _boot_profile_findings(self) -> list[SelfExaminationFinding]:
        """Read boot profile history and emit degradation / regression findings.

        Reads ``BootProfileStore.boot_profile_summary()`` for the current
        environment.  Emits findings for:
        - p95 boot duration above ``BOOT_P95_MS_DEGRADED``
        - average wiring duration above ``BOOT_WIRING_AVG_MS_DEGRADED``
        - boot regression: last boot >40% slower than rolling average

        Pure observability — no decisions, no mutations.
        """
        store = self.boot_profile_store
        if store is None:
            return []

        environment_id = self._boot_profile_environment_id()
        if not environment_id:
            return []

        try:
            summary = store.boot_profile_summary(environment_id)
        except Exception:
            return []

        if summary.get('boot_count', 0) < 2:
            return []

        findings: list[SelfExaminationFinding] = []
        dur = summary.get('boot_duration', {})
        wiring = summary.get('wiring_duration', {})
        boot_count = summary.get('boot_count', 0)

        source_refs = [
            'data/evolution/boot_profiles/',
            'iabv_v15.services.evolution.boot_profile_store',
        ]

        p95_ms = dur.get('p95_ms', 0)
        if p95_ms > BOOT_P95_MS_DEGRADED:
            findings.append(SelfExaminationFinding(
                category='boot_profile_degradation',
                title=f'Boot p95 alto: {p95_ms:.0f}ms',
                summary=(
                    f'El percentil 95 del boot es {p95_ms:.0f}ms '
                    f'(umbral {BOOT_P95_MS_DEGRADED:.0f}ms) sobre '
                    f'{boot_count} boots en {environment_id}.'
                ),
                severity=IssueSeverity.HIGH if p95_ms > BOOT_P95_MS_DEGRADED * 2 else IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Revisar slowest_phases del boot profile para '
                    'identificar fases que se pueden diferir o paralelizar.'
                ),
                source_refs=source_refs,
                metadata={
                    'finding_type': 'boot_p95_high',
                    'environment_id': environment_id,
                    'p95_ms': p95_ms,
                    'threshold_ms': BOOT_P95_MS_DEGRADED,
                    'boot_count': boot_count,
                    'avg_ms': dur.get('avg_ms', 0),
                },
            ))

        wiring_avg = wiring.get('avg_ms', 0)
        if wiring_avg > BOOT_WIRING_AVG_MS_DEGRADED:
            findings.append(SelfExaminationFinding(
                category='boot_profile_degradation',
                title=f'Wiring duration alto: avg {wiring_avg:.0f}ms',
                summary=(
                    f'El wiring promedio es {wiring_avg:.0f}ms '
                    f'(umbral {BOOT_WIRING_AVG_MS_DEGRADED:.0f}ms) sobre '
                    f'{boot_count} boots. El backend tarda mucho antes '
                    f'de que la UI sea visible.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Diferir scans de cuentas, probes de proveedores y '
                    'registro de herramientas a despues de la UI visible.'
                ),
                source_refs=source_refs,
                metadata={
                    'finding_type': 'wiring_duration_high',
                    'environment_id': environment_id,
                    'wiring_avg_ms': wiring_avg,
                    'wiring_max_ms': wiring.get('max_ms', 0),
                    'threshold_ms': BOOT_WIRING_AVG_MS_DEGRADED,
                    'boot_count': boot_count,
                },
            ))

        avg_ms = dur.get('avg_ms', 0)
        if avg_ms > 0:
            try:
                history = store.load_history(environment_id, limit=5)
                if len(history) >= 2:
                    last_boot_ms = history[-1].get('boot_duration_ms', 0)
                    if last_boot_ms > 0 and last_boot_ms > avg_ms * BOOT_REGRESSION_RATIO:
                        ratio = last_boot_ms / avg_ms
                        findings.append(SelfExaminationFinding(
                            category='boot_profile_regression',
                            title=f'Regresion de boot: {last_boot_ms:.0f}ms vs avg {avg_ms:.0f}ms',
                            summary=(
                                f'El ultimo boot ({last_boot_ms:.0f}ms) es '
                                f'{ratio:.1f}x el promedio historico ({avg_ms:.0f}ms). '
                                f'Posible regresion de rendimiento.'
                            ),
                            severity=IssueSeverity.HIGH if ratio > 2.0 else IssueSeverity.MEDIUM,
                            confidence=0.75,
                            recommendation=(
                                'Comparar el ultimo boot con corridas anteriores. '
                                'Revisar si se agregaron fases nuevas o si alguna '
                                'fase existente se hizo mas lenta.'
                            ),
                            source_refs=source_refs,
                            metadata={
                                'finding_type': 'boot_regression',
                                'environment_id': environment_id,
                                'last_boot_ms': last_boot_ms,
                                'avg_ms': avg_ms,
                                'ratio': round(ratio, 2),
                                'threshold_ratio': BOOT_REGRESSION_RATIO,
                                'boot_count': boot_count,
                            },
                        ))
            except Exception:
                pass

        return findings

    def _boot_profile_environment_id(self) -> str:
        """Resolve environment_id for boot profile queries.

        Uses world_model_service -> environment_self_awareness_service
        -> current_model().environment_id, same chain OSES already uses.
        """
        wm_service = self.world_model_service
        if wm_service is None:
            return ''
        env_service = getattr(wm_service, 'environment_self_awareness_service', None)
        if env_service is None or not hasattr(env_service, 'current_model'):
            return ''
        try:
            model = env_service.current_model()
            return getattr(model, 'environment_id', '') or ''
        except Exception:
            return ''

    def _cloud_reasoning_findings(self) -> list[SelfExaminationFinding]:
        """Analyze cloud reasoning decision trail for metacognitive findings.

        Reads the ``DecisionAuditTrail`` and produces findings about:
        - Provider degradation (success rate dropping)
        - Rate limiting patterns (provider over-used)
        - Fallback dependency (always falling back to lower-tier providers)
        - No functional provider (all keys failing)
        - Configuration improvement opportunities
        """
        audit = getattr(self, 'decision_audit_trail', None)
        if audit is None:
            return []
        try:
            summary = audit.self_examination_summary()
        except Exception:
            return []
        if summary.get('status') == 'no_data':
            return []

        findings: list[SelfExaminationFinding] = []
        trends = summary.get('trends', [])
        health_score = summary.get('health_score', 0.0)
        overall_trend = summary.get('overall_trend', 'stable')

        # Finding: overall health degrading
        if overall_trend == 'degrading' and health_score < 0.7:
            findings.append(SelfExaminationFinding(
                category='cloud_reasoning_degradation',
                title='Cloud reasoning degradandose: exito global bajo',
                summary=(
                    f'El health score de cloud reasoning cayo a {health_score:.0%}. '
                    f'La tendencia general es "degrading". Esto indica que las '
                    f'configuraciones actuales de proveedores estan rindiendo peor '
                    f'que antes. Revisar keys, cuotas y considerar rotar proveedores.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.85,
                recommendation=(
                    'Ejecutar "revisar api keys" para diagnosticar estado de cada '
                    'proveedor. Si hay keys expiradas, usar "generar keys" para '
                    'renovar. Considerar agregar proveedores backup (OpenRouter, '
                    'Together AI).'
                ),
                source_refs=['DecisionAuditTrail'],
                metadata={'health_score': health_score, 'overall_trend': overall_trend},
            ))

        for trend in trends:
            if not isinstance(trend, dict):
                continue
            provider_id = trend.get('provider_id', '')
            success_rate = trend.get('success_rate', 0.0)
            rate_limited_count = trend.get('rate_limited_count', 0)
            total_decisions = trend.get('total_decisions', 0)
            trend_dir = trend.get('trend_direction', 'stable')

            # Finding: specific provider degrading
            if trend_dir == 'degrading' and total_decisions >= 6:
                findings.append(SelfExaminationFinding(
                    category='cloud_provider_degradation',
                    title=f'Proveedor {provider_id} degradandose',
                    summary=(
                        f'{provider_id} tiene exito de {success_rate:.0%} con tendencia '
                        f'"degrading" sobre {total_decisions} decisiones recientes. '
                        f'La segunda mitad de las decisiones tiene peor resultado que la primera.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.78,
                    recommendation=(
                        f'Verificar el estado de la API key de {provider_id}. Si '
                        f'la cuota esta agotada, esperar reinicio diario o rotar '
                        f'a otro proveedor. Si la key es invalida, renovarla.'
                    ),
                    source_refs=['DecisionAuditTrail'],
                    metadata={'provider_id': provider_id, **trend},
                ))

            # Finding: heavy rate limiting
            if total_decisions > 0 and rate_limited_count > total_decisions * 0.3:
                findings.append(SelfExaminationFinding(
                    category='cloud_rate_limiting',
                    title=f'{provider_id} con rate limiting frecuente',
                    summary=(
                        f'{provider_id}: {rate_limited_count} de {total_decisions} decisiones '
                        f'fueron rate-limited. El proveedor esta siendo sobre-utilizado '
                        f'o la cuota del tier gratuito es insuficiente.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.82,
                    recommendation=(
                        f'Reducir la frecuencia de consultas a {provider_id} o agregar '
                        f'un proveedor adicional como backup para distribuir la carga. '
                        f'Considerar OpenRouter o Together AI como alternativas gratuitas.'
                    ),
                    source_refs=['DecisionAuditTrail'],
                    metadata={'provider_id': provider_id, **trend},
                ))

            # Finding: provider improving (positive reinforcement)
            if trend_dir == 'improving' and total_decisions >= 6 and success_rate > 0.8:
                findings.append(SelfExaminationFinding(
                    category='cloud_provider_improving',
                    title=f'{provider_id} mejorando: mantener configuracion',
                    summary=(
                        f'{provider_id} tiene exito de {success_rate:.0%} con tendencia '
                        f'"improving". La configuracion actual esta funcionando bien. '
                        f'Mantener como proveedor principal.'
                    ),
                    severity=IssueSeverity.LOW,
                    confidence=0.80,
                    recommendation=(
                        f'Mantener {provider_id} como proveedor principal de cloud '
                        f'reasoning. Registrar este resultado como referencia baseline '
                        f'para futuras comparaciones.'
                    ),
                    source_refs=['DecisionAuditTrail'],
                    metadata={'provider_id': provider_id, **trend},
                ))

        # Finding: no functional provider
        if trends and not any(
            isinstance(t, dict) and t.get('success_rate', 0) > 0.5
            for t in trends
        ):
            findings.append(SelfExaminationFinding(
                category='cloud_no_functional_provider',
                title='Ningun proveedor cloud con exito aceptable',
                summary=(
                    'Ninguno de los proveedores configurados tiene tasa de exito '
                    'mayor al 50%. Cloud reasoning no esta funcionando de forma '
                    'confiable. Se necesita diagnostico y posible renovacion de keys.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.90,
                recommendation=(
                    'Ejecutar "revisar api keys" para diagnostico completo. '
                    'Verificar conexion a internet. Renovar keys si es necesario. '
                    'Considerar agregar multiples proveedores para redundancia.'
                ),
                source_refs=['DecisionAuditTrail'],
                metadata={'trends': trends},
            ))

        return findings

    def _chat_research_backlog_findings(self) -> list[SelfExaminationFinding]:
        """Consume ``data/chat_research_backlog/<session>.jsonl`` y produce
        hallazgos de ``research_gap`` por cada ``kind`` unico con entradas
        ``status='open'``.

        ``ChatCapabilityIngestionService`` (capa chat) persiste capacidades
        declaradas por el usuario (GPU, modelos locales, cuentas, runtimes)
        como tareas de investigacion pendientes. Sin este hook, el dato se
        escribia pero nadie lo consumia. OSES es el lugar natural para
        surfacearlo: las capacidades declaradas son gaps de investigacion
        reales hasta que se midan contra el StrategySelector / ExperimentLab.

        Agrupamos por ``kind`` para evitar ruido: si el usuario menciono
        "gpu" 10 veces en distintas sesiones, es un solo ``research_gap``,
        no diez. Solo se ignoran entradas con ``status`` distinto de
        ``'open'`` (ej: ya investigadas, archivadas). Si el directorio no
        existe o no hay entradas abiertas, devuelve lista vacia sin
        inventar observacion.
        """

        backlog_dir = Path(self.workspace_root) / 'data' / 'chat_research_backlog'
        if not backlog_dir.exists() or not backlog_dir.is_dir():
            return []

        try:
            files = sorted(backlog_dir.glob('*.jsonl'))
        except OSError:
            return []
        if not files:
            return []

        # Agrupacion por ``kind``: nos quedamos con la entrada mas reciente
        # por kind para tener la evidencia mas actual sin duplicar findings.
        per_kind: dict[str, dict[str, Any]] = {}
        per_kind_count: Counter[str] = Counter()
        per_kind_sessions: dict[str, set[str]] = defaultdict(set)
        for path in files:
            try:
                with path.open('r', encoding='utf-8') as handle:
                    for line in handle:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            record = json.loads(stripped)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(record, dict):
                            continue
                        if str(record.get('status') or 'open') != 'open':
                            continue
                        kind = str(record.get('kind') or '').strip()
                        if not kind:
                            continue
                        per_kind_count[kind] += 1
                        session_id = str(record.get('session_id') or '').strip()
                        if session_id:
                            per_kind_sessions[kind].add(session_id)
                        existing = per_kind.get(kind)
                        if existing is None:
                            per_kind[kind] = record
                            continue
                        # Conservar la entrada con ``detected_at_utc`` mas
                        # reciente (comparacion lexicografica de ISO-8601 UTC
                        # es equivalente a temporal).
                        if str(record.get('detected_at_utc') or '') > str(existing.get('detected_at_utc') or ''):
                            per_kind[kind] = record
            except OSError:
                continue

        if not per_kind:
            return []

        findings: list[SelfExaminationFinding] = []
        for kind, entry in per_kind.items():
            label = str(entry.get('label') or kind).strip()
            hint = str(entry.get('research_hint') or '').strip()
            matched_text = str(entry.get('matched_text') or '').strip()
            occurrences = per_kind_count[kind]
            sessions = sorted(per_kind_sessions[kind])
            detected_at = str(entry.get('detected_at_utc') or '').strip()

            summary_parts = [
                f'El usuario declaro "{label}"'
                + (f' (detectado como "{matched_text}")' if matched_text else '')
                + ' en el chat, pero el sistema aun no valido su impacto.',
            ]
            if hint:
                summary_parts.append(f'Investigacion pendiente: {hint}')
            if occurrences > 1:
                summary_parts.append(
                    f'La mencion aparece {occurrences} veces en el backlog '
                    f'({len(sessions)} sesiones).'
                )
            summary = ' '.join(summary_parts)

            evidence_refs: list[str] = []
            if detected_at:
                evidence_refs.append(f'detected_at_utc={detected_at}')
            if sessions:
                evidence_refs.append('sessions=' + ','.join(sessions[:4]))

            findings.append(
                SelfExaminationFinding(
                    category='research_gap',
                    title=f'Capacidad declarada sin validar: {label}',
                    summary=summary,
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.6,
                    recommendation=hint or (
                        'Validar la capacidad declarada contra ExperimentLab / '
                        'StrategySelector y registrar resultado real.'
                    ),
                    evidence_refs=evidence_refs,
                    source_refs=['ChatCapabilityIngestionService', 'chat_research_backlog'],
                    metadata={
                        'kind': kind,
                        'label': label,
                        'matched_text': matched_text,
                        'occurrences': occurrences,
                        'sessions': sessions,
                        'latest_detected_at_utc': detected_at,
                    },
                )
            )
        return findings

    # ------------------------------------------------------------------
    # Runtime log self-inspection
    # ------------------------------------------------------------------
    _LOG_TAIL_LINES = 500
    _LOG_ANOMALY_PATTERNS: tuple[tuple[str, str, str, str], ...] = (
        # (substring_to_match, category, title, recommendation)
        (
            'multi_source_disagreement',
            'runtime_noise',
            'multi_source_disagreement repetido en logs',
            'El cache de 300s puede no ser suficiente o el MCP polling '
            'recrea instancias que pierden el cache. Considerar aumentar '
            'TTL o mover cache a nivel de clase persistente.',
        ),
        (
            'No pude completar la consulta externa',
            'external_consultation_failure',
            'Consulta externa fallida detectada en logs',
            'Revisar si la herramienta externa estaba realmente disponible '
            'antes de intentar la consulta. Preferir via local cuando el '
            'tema es interno (secretos, configuracion, metacognicion).',
        ),
        (
            'tool_missing',
            'tool_availability',
            'Herramienta faltante reportada en logs',
            'Verificar si la herramienta faltante es necesaria para el '
            'flujo actual o si existe un fallback disponible.',
        ),
        (
            'ghost_session_watchdog',
            'ghost_session',
            'Watchdog de sesion fantasma se activo',
            'Una consulta externa excedio el timeout y fue cancelada. '
            'Investigar por que la herramienta no respondio.',
        ),
        (
            'HTTP Request:',
            'http_noise',
            'Ruido excesivo de logs HTTP (httpx)',
            'Demasiadas lineas de httpx poluciona el log y dificulta '
            'encontrar hallazgos importantes. Auto-suprimir httpx a '
            'WARNING cuando exceda el umbral.',
        ),
        (
            'cloudflare_challenge',
            'cloudflare_blocked',
            'Sesion bloqueada por Cloudflare challenge',
            'La sesion aislada no puede pasar la verificacion de Cloudflare. '
            'El programa deberia usar CDP contra el Chrome del usuario '
            '(use_browser_session=False) donde ya hay sesion activa.',
        ),
        (
            'wrong_thread',
            'wrong_thread',
            'Captura en hilo incorrecto del asistente',
            'La sesion se abrio pero capturo respuesta de un hilo diferente '
            'al esperado. Verificar que el thread_key apunte al hilo '
            'correcto o crear un hilo nuevo dedicado.',
        ),
        (
            'verificacion del sitio',
            'session_verification_failed',
            'Sesion no paso verificacion del sitio',
            'La sesion aislada quedo bloqueada en la pagina de verificacion '
            'sin poder acceder al chat. Esto indica que se necesita reusar '
            'la sesion del navegador del usuario, no una sesion aislada.',
        ),
        (
            'adapter_missing',
            'adapter_missing',
            'Falta adaptador operativo para fase de ejecucion',
            'Hay estrategia y contexto listos pero no existe un adaptador '
            'que ejecute la fase. Verificar ToolRegistry y considerar usar '
            'un executor local disponible.',
        ),
    )

    def _runtime_log_findings(self) -> list[SelfExaminationFinding]:
        """Read the tail of the runtime log file and detect anomaly patterns.

        This is the core of the "program sees itself" capability: instead
        of requiring the user to copy-paste logs into the chat, the
        autoexamination service reads its own log output and produces
        findings from patterns like repeated errors, ghost sessions,
        tool disagreements, and failed external consultations.
        """
        # Primary path: data/logs/iabv_v15.log (matches configure_logging)
        log_path = Path(self.workspace_root) / 'data' / 'logs' / 'iabv_v15.log'
        if not log_path.exists():
            # Legacy fallback: some old setups used src/data/
            log_path = Path(self.workspace_root) / 'src' / 'data' / 'iabv_v15.log'
        if not log_path.exists():
            log_path = Path(self.workspace_root) / 'iabv_v15.log'
        if not log_path.exists():
            return []

        try:
            with log_path.open('r', encoding='utf-8', errors='replace') as fh:
                # Read only last N lines to avoid loading huge files
                lines = fh.readlines()[-self._LOG_TAIL_LINES:]
        except OSError:
            return []

        if not lines:
            return []

        findings: list[SelfExaminationFinding] = []
        for pattern_str, category, title, recommendation in self._LOG_ANOMALY_PATTERNS:
            matching_lines = [
                line.strip() for line in lines
                if pattern_str in line
            ]
            if not matching_lines:
                continue
            count = len(matching_lines)
            severity = IssueSeverity.HIGH if count > 10 else (
                IssueSeverity.MEDIUM if count > 3 else IssueSeverity.LOW
            )
            sample = matching_lines[-3:]  # last 3 occurrences as evidence
            findings.append(
                SelfExaminationFinding(
                    category=category,
                    title=title,
                    summary=(
                        f'Detectadas {count} ocurrencias de "{pattern_str}" '
                        f'en las ultimas {self._LOG_TAIL_LINES} lineas del log. '
                        f'Ejemplo reciente: {sample[-1][:200]}'
                    ),
                    severity=severity,
                    confidence=0.9,
                    recommendation=recommendation,
                    evidence_refs=[f'log_occurrences={count}'] + [
                        line[:120] for line in sample
                    ],
                    source_refs=['runtime_log', str(log_path)],
                    metadata={
                        'pattern': pattern_str,
                        'occurrences': count,
                        'log_path': str(log_path),
                    },
                )
            )

        # Enrich with browser account awareness: the program should know
        # what accounts the user has in their browsers to make better
        # decisions about using isolated vs shared sessions.
        try:
            from iabv_v15.services.account_resource_scanner import scan_browser_accounts
            browser_info = scan_browser_accounts()
            acct_count = browser_info.get('count', 0)
            if acct_count > 0:
                accounts = browser_info.get('accounts', [])
                account_summary = ', '.join(
                    f"{a.get('email', '?')} ({a.get('browser', '?')})"
                    for a in accounts[:5]
                )
                # Only report if there are cloudflare/session issues
                has_session_issues = any(
                    f.category in ('cloudflare_blocked', 'session_verification_failed', 'wrong_thread')
                    for f in findings
                )
                if has_session_issues:
                    findings.append(
                        SelfExaminationFinding(
                            category='browser_accounts_available',
                            title=f'{acct_count} cuenta(s) de navegador detectadas',
                            summary=(
                                f'El usuario tiene {acct_count} cuenta(s) activa(s) en sus '
                                f'navegadores: {account_summary}. Estas sesiones pueden '
                                f'usarse via CDP para evitar bloqueos de Cloudflare.'
                            ),
                            severity=IssueSeverity.LOW,
                            confidence=0.95,
                            recommendation=(
                                'Usar connect_over_cdp al Chrome del usuario en vez de '
                                'sesiones aisladas para herramientas web (ChatGPT, Claude, Codex).'
                            ),
                            evidence_refs=[
                                f'{a.get("browser", "?")}: {a.get("email", "?")}'
                                for a in accounts[:5]
                            ],
                            source_refs=['account_resource_scanner'],
                            metadata={'browser_accounts': browser_info},
                        )
                    )
        except Exception:
            pass  # scanner not available or failed — not critical

        # Auto-correction loop: when the program detects anomalies in its
        # own logs, attempt corrective actions automatically.
        if findings:
            try:
                from iabv_v15.services.auto_correction_engine import (
                    apply_runtime_log_corrections,
                )
                corrections = apply_runtime_log_corrections(
                    [
                        {
                            'category': f.category,
                            'occurrences': (f.metadata or {}).get('occurrences', 0),
                        }
                        for f in findings
                    ],
                    workspace=str(self.workspace_root),
                )
                applied = corrections.get('corrections_count', 0)
                if applied > 0:
                    findings.append(
                        SelfExaminationFinding(
                            category='self_correction',
                            title=f'Auto-correcciones aplicadas desde log: {applied}',
                            summary=(
                                f'El programa detecto {len(findings)} anomalias en su '
                                f'propio log y aplico {applied} correcciones automaticas.'
                            ),
                            severity=IssueSeverity.LOW,
                            confidence=1.0,
                            recommendation='Verificar que las correcciones fueron efectivas en el proximo ciclo.',
                            evidence_refs=[
                                f'{c.get("action", "?")}: {c.get("detail", "?")}'
                                for c in corrections.get('corrections_applied', [])
                            ],
                            source_refs=['auto_correction_engine'],
                            metadata={'corrections': corrections},
                        )
                    )
            except Exception as exc:
                logger.debug('runtime log auto-correction failed: %s', exc)

        # Deductive reasoning: instead of only matching patterns to hardcoded
        # handlers, ask Ollama to reason about ALL findings and deduce what
        # corrections to make using available tools and resources.
        # This gives the program general-purpose "intuition" — the ability
        # to solve NEW problems without a human programming each case.
        if findings:
            try:
                from iabv_v15.services.auto_correction_engine import (
                    apply_deductive_corrections,
                )
                finding_dicts = [
                    {
                        'category': f.category,
                        'occurrences': (f.metadata or {}).get('occurrences', 0),
                        'title': f.title,
                        'summary': f.summary,
                    }
                    for f in findings
                    if f.category != 'self_correction'
                ]
                if finding_dicts:
                    deductive = apply_deductive_corrections(
                        finding_dicts,
                        workspace=str(self.workspace_root),
                    )
                    ded_applied = deductive.get('corrections_count', 0)
                    reasoning = deductive.get('deductive_reasoning', '')
                    if ded_applied > 0 or reasoning:
                        findings.append(
                            SelfExaminationFinding(
                                category='deductive_self_correction',
                                title=f'Razonamiento deductivo: {ded_applied} correcciones',
                                summary=(
                                    f'El programa uso Ollama para razonar sobre '
                                    f'{len(finding_dicts)} hallazgo(s) y dedujo '
                                    f'{ded_applied} correccion(es). '
                                    f'Razonamiento: {reasoning[:300]}'
                                ),
                                severity=IssueSeverity.LOW,
                                confidence=0.85,
                                recommendation=(
                                    'El programa ahora puede razonar sobre problemas '
                                    'nuevos sin necesitar programacion especifica.'
                                ),
                                evidence_refs=[
                                    f'{c.get("action", "?")}: {c.get("detail", "?")}'
                                    for c in deductive.get('corrections_applied', [])
                                ],
                                source_refs=['deductive_reasoning_engine', 'ollama'],
                                metadata={
                                    'deductive_corrections': deductive,
                                    'ollama_available': deductive.get('ollama_available', False),
                                },
                            )
                        )
            except Exception as exc:
                logger.debug('deductive reasoning failed: %s', exc)

        # Intelligent tool verification: when there are disagreements about
        # tool availability, the program deep-probes each tool and asks
        # Ollama to deduce the best configuration.  This is the program
        # auditing its OWN tool access autonomously.
        disagreement_tools = [
            f for f in findings
            if f.category in ('multi_source_disagreement', 'runtime_noise')
            and 'disagreement' in (f.summary or '').lower()
        ]
        if disagreement_tools:
            try:
                from iabv_v15.services.auto_correction_engine import (
                    verify_tool_access_deductive,
                )
                # Extract tool_ids from disagreement findings
                verified_tools: list[str] = []
                for f in disagreement_tools:
                    refs = f.evidence_refs or []
                    for ref in refs:
                        ref_str = str(ref)
                        if '_installed' in ref_str:
                            tid = ref_str.split(' ')[0].split(':')[0].strip()
                            if tid and tid not in verified_tools:
                                verified_tools.append(tid)
                    # Also try extracting from metadata
                    meta = f.metadata or {}
                    for key in ('tool_id', 'tool_ids'):
                        val = meta.get(key, '')
                        if isinstance(val, str) and val and val not in verified_tools:
                            verified_tools.append(val)
                        elif isinstance(val, list):
                            for v in val:
                                if v and v not in verified_tools:
                                    verified_tools.append(str(v))

                # If we couldn't extract specific tool_ids, check common ones
                if not verified_tools:
                    verified_tools = ['codex_installed', 'chatgpt_installed', 'claude_installed', 'ollama_llm']

                for tid in verified_tools[:5]:
                    verification = verify_tool_access_deductive(
                        tid, workspace=str(self.workspace_root),
                    )
                    if verification.get('reasoning'):
                        findings.append(
                            SelfExaminationFinding(
                                category='tool_access_verification',
                                title=f'Verificacion inteligente: {tid}',
                                summary=(
                                    f"truly_available={verification.get('truly_available', '?')}, "
                                    f"best_mode={verification.get('best_mode', '?')}. "
                                    f"{verification.get('reasoning', '')[:300]}"
                                ),
                                severity=IssueSeverity.LOW,
                                confidence=0.85,
                                recommendation=(
                                    f"Configuracion optima deducida: "
                                    f"{verification.get('configuration', {})}"
                                ),
                                evidence_refs=[
                                    f"filesystem={verification.get('probe', {}).get('filesystem', {}).get('any_exists', '?')}",
                                    f"process={verification.get('probe', {}).get('process', {}).get('is_running', '?')}",
                                    f"session={verification.get('probe', {}).get('session', {}).get('state_exists', '?')}",
                                ],
                                source_refs=['verify_tool_access_deductive', 'ollama'],
                                metadata={'verification': verification},
                            )
                        )
            except Exception as exc:
                logger.debug('tool access verification failed: %s', exc)

        return findings

    def _dedupe_findings(self, findings: list[SelfExaminationFinding]) -> list[SelfExaminationFinding]:
        ranked = sorted(
            findings,
            key=lambda item: (
                self._severity_rank(item.severity),
                float(item.confidence or 0.0),
                len(item.evidence_refs or []),
            ),
            reverse=True,
        )
        unique: list[SelfExaminationFinding] = []
        seen: set[tuple[str, str]] = set()
        for finding in ranked:
            key = (finding.category, finding.title)
            if key in seen:
                continue
            unique.append(finding)
            seen.add(key)
        return unique

    def _recurring_issues(
        self,
        *,
        findings: list[SelfExaminationFinding],
        project_health: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items = [
            {
                'title': finding.title,
                'category': finding.category,
                'summary': finding.summary,
                'severity': getattr(finding.severity, 'value', str(finding.severity)),
                'confidence': finding.confidence,
                'evidence_refs': list(finding.evidence_refs[:4]),
                'source_refs': list(finding.source_refs[:4]),
            }
            for finding in findings[:5]
        ]
        repeated = list(project_health.get('repeated_issues') or [])
        for issue in repeated[:3]:
            issue_hint = str(issue.get('issue_hint') or '').strip()
            if not issue_hint:
                continue
            count = int(issue.get('count') or 0)
            severity = IssueSeverity.HIGH if count >= 5 else IssueSeverity.MEDIUM if count >= 2 else IssueSeverity.LOW
            confidence = min(0.80, 0.30 + count * 0.07)
            items.append(
                {
                    'title': issue_hint,
                    'category': 'project_health_repeat',
                    'summary': (
                        f'El issue {issue_hint} reaparece {count} veces en la '
                        f'capa evolutiva. Requiere accion correctiva si persiste '
                        f'en corridas recientes.'
                    ),
                    'severity': severity.value,
                    'confidence': round(confidence, 2),
                    'evidence_refs': [],
                    'source_refs': ['EvolutionReviewService'],
                }
            )
        return items[:6]

    def _recommended_adjustments(
        self,
        *,
        findings: list[SelfExaminationFinding],
        backlog: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items = [
            {
                'title': finding.title,
                'recommended_change': finding.recommendation,
                'category': finding.category,
                    'severity': getattr(finding.severity, 'value', str(finding.severity)),
                    'confidence': finding.confidence,
                    'evidence_refs': list(finding.evidence_refs[:4]),
                    'source_refs': list(finding.source_refs[:4]),
                    'metadata': dict(finding.metadata or {}),
                    'feedback_key': self._adjustment_feedback_key(
                        category=finding.category,
                        title=finding.title,
                        metadata=dict(finding.metadata or {}),
                    ),
                }
            for finding in findings
            if finding.recommendation
        ]
        for proposal in backlog[:4]:
            recommended_change = str(proposal.get('recommended_change') or '').strip()
            if not recommended_change:
                continue
            if any(str(item.get('recommended_change') or '').strip().lower() == recommended_change.lower() for item in items):
                continue
            items.append(
                {
                    'title': str(proposal.get('title') or 'Mejora sugerida'),
                    'recommended_change': recommended_change,
                    'category': 'backlog',
                    'severity': IssueSeverity.MEDIUM.value,
                    'confidence': min(0.95, float(proposal.get('priority_score') or 0) / 100.0),
                    'evidence_refs': [],
                    'source_refs': ['EvolutionReviewService'],
                    'metadata': dict(proposal.get('metadata') or {}),
                    'feedback_key': self._adjustment_feedback_key(
                        category='backlog',
                        title=str(proposal.get('title') or 'Mejora sugerida'),
                        metadata=dict(proposal.get('metadata') or {}),
                    ),
                }
            )
        return self._dedupe_adjustments(items)[:6]

    def _adjustment_group_key(self, item: dict[str, Any]) -> tuple[str, str, str]:
        """Clave de agrupacion para colapsar ajustes recomendados duplicados.

        Usa ``(fuente_principal, categoria, titulo)``: distintos "recommended_change"
        con el mismo titulo/categoria/fuente se consideran variantes del mismo
        patron y se colapsan con ``duplicate_count``.
        """
        sources = list(item.get('source_refs') or [])
        primary_source = str(sources[0]) if sources else ''
        category = str(item.get('category') or '').strip().lower()
        title = str(item.get('title') or '').strip().lower()
        return primary_source, category, title

    def _dedupe_adjustments(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: dict[tuple[str, str, str], dict[str, Any]] = {}
        order: list[tuple[str, str, str]] = []
        for item in items:
            key = self._adjustment_group_key(item)
            if key in seen:
                existing = seen[key]
                metadata = dict(existing.get('metadata') or {})
                metadata['duplicate_count'] = int(metadata.get('duplicate_count') or 1) + 1
                variants = list(metadata.get('duplicate_variants') or [])
                variant = str(item.get('recommended_change') or '').strip()
                if variant and variant not in variants and len(variants) < 4:
                    variants.append(variant)
                if variants:
                    metadata['duplicate_variants'] = variants
                existing['metadata'] = metadata
                existing_refs = list(existing.get('evidence_refs') or [])
                for ref in item.get('evidence_refs') or []:
                    if ref not in existing_refs and len(existing_refs) < 4:
                        existing_refs.append(ref)
                existing['evidence_refs'] = existing_refs
                if float(item.get('confidence') or 0.0) > float(existing.get('confidence') or 0.0):
                    existing['confidence'] = item.get('confidence')
                    recommended_change = str(item.get('recommended_change') or '').strip()
                    if recommended_change:
                        existing['recommended_change'] = recommended_change
            else:
                clone = dict(item)
                metadata = dict(item.get('metadata') or {})
                metadata['duplicate_count'] = 1
                variant = str(item.get('recommended_change') or '').strip()
                if variant:
                    metadata['duplicate_variants'] = [variant]
                clone['metadata'] = metadata
                clone['evidence_refs'] = list(item.get('evidence_refs') or [])
                seen[key] = clone
                order.append(key)
        return [seen[key] for key in order]

    def _recommendation_feedback(
        self,
        *,
        previous_review: SelfExaminationSnapshot | None,
        current_findings: list[SelfExaminationFinding],
        validated_improvements: list[dict[str, Any]],
        experiment_runs: list[ExperimentRun],
        validation: AutonomousValidationSnapshot,
    ) -> list[dict[str, Any]]:
        if previous_review is None:
            return []
        previous_adjustments = list(previous_review.recommended_adjustments or [])
        if not previous_adjustments:
            return []
        reviewed_after = previous_review.updated_at_utc
        post_review_runs = [
            run
            for run in experiment_runs
            if getattr(run, 'created_at_utc', None) is not None and run.created_at_utc > reviewed_after
        ]
        current_findings_by_key = {
            self._adjustment_feedback_key(
                category=finding.category,
                title=finding.title,
                metadata=dict(finding.metadata or {}),
            ): finding
            for finding in current_findings
        }
        items: list[dict[str, Any]] = []
        for adjustment in previous_adjustments[:8]:
            category = str(adjustment.get('category') or '').strip()
            title = str(adjustment.get('title') or 'Ajuste previo').strip()
            metadata = dict(adjustment.get('metadata') or {})
            feedback_key = str(adjustment.get('feedback_key') or self._adjustment_feedback_key(category=category, title=title, metadata=metadata))
            matching_runs = self._matching_runs_for_adjustment(
                adjustment=adjustment,
                experiment_runs=post_review_runs,
            )
            profile = self._feedback_profile(matching_runs)
            current_finding = current_findings_by_key.get(feedback_key)
            has_validated_evidence = self._adjustment_has_validated_evidence(
                adjustment=adjustment,
                validated_improvements=validated_improvements,
                validation=validation,
            )
            sample_count = int(profile.get('sample_count') or 0)
            success_rate = float(profile.get('success_rate') or 0.0)
            blocked_rate = float(profile.get('blocked_rate') or 0.0)
            fallback_rate = float(profile.get('fallback_rate') or 0.0)
            trend_score = float(profile.get('trend_score') or 0.0)
            positive_metrics = sample_count >= 2 and success_rate >= 0.66 and blocked_rate < 0.25 and fallback_rate < 0.25 and trend_score > -0.08
            negative_metrics = sample_count >= 2 and (success_rate < 0.5 or blocked_rate >= 0.34 or fallback_rate >= 0.34 or current_finding is not None)
            if has_validated_evidence and positive_metrics and current_finding is None:
                status = 'validated_improvement'
                summary = 'La recomendacion previa ya tiene evidencia positiva y validacion suficiente para darla por consolidada.'
                next_step = 'No hace falta proponer el mismo ajuste otra vez salvo que reaparezca degradacion.'
            elif positive_metrics and current_finding is None:
                status = 'valid_adjustment'
                summary = 'La recomendacion previa mejoro el comportamiento en corridas posteriores, aunque todavia sin una validacion fuerte completa.'
                next_step = 'Mantener la preferencia actual y seguir observando antes de consolidarla.'
            elif negative_metrics:
                status = 'false_improvement'
                summary = 'La recomendacion previa no produjo beneficio real en la evidencia posterior o el patron sigue activo.'
                next_step = 'No repetir exactamente este ajuste sin evidencia nueva; exigir alternativa o validacion adicional.'
            else:
                status = 'no_evidence'
                summary = 'Todavia no hay suficiente evidencia posterior para juzgar si esta recomendacion sirvio o no.'
                next_step = 'Mantenerla en observacion hasta tener mas corridas comparables.'
            confidence = 0.52
            if sample_count >= 3:
                confidence += 0.18
            if has_validated_evidence:
                confidence += 0.14
            if current_finding is not None:
                confidence += 0.08
            evidence_refs = list(adjustment.get('evidence_refs') or [])[:2]
            evidence_refs.extend(run.run_id for run in matching_runs[:3])
            evidence_refs = list(dict.fromkeys(item for item in evidence_refs if str(item).strip()))
            items.append(
                {
                    'title': title,
                    'category': category or 'unknown',
                    'feedback_key': feedback_key,
                    'status': status,
                    'summary': summary,
                    'next_step': next_step,
                    'confidence': min(0.96, confidence),
                    'sample_count': sample_count,
                    'evidence_refs': evidence_refs[:5],
                    'source_refs': list(dict.fromkeys([*(adjustment.get('source_refs') or []), 'OperationalSelfExaminationService', 'ExperimentLab', 'AutonomousValidationSnapshot'])),
                    'profile': profile,
                    'current_issue_still_active': current_finding is not None,
                    'repeat_recommendation': status not in {'validated_improvement', 'false_improvement'},
                    'updated_at_utc': utc_now().isoformat(),
                }
            )
        return items[:6]

    def _apply_feedback_to_adjustments(
        self,
        *,
        recommended_adjustments: list[dict[str, Any]],
        recommendation_feedback: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        feedback_by_key = {
            str(item.get('feedback_key') or ''): item
            for item in recommendation_feedback
            if str(item.get('feedback_key') or '').strip()
        }
        updated: list[dict[str, Any]] = []
        for item in recommended_adjustments:
            payload = dict(item)
            feedback_key = str(payload.get('feedback_key') or self._adjustment_feedback_key(
                category=str(payload.get('category') or ''),
                title=str(payload.get('title') or ''),
                metadata=dict(payload.get('metadata') or {}),
            ))
            feedback = feedback_by_key.get(feedback_key)
            if feedback is not None:
                payload['last_feedback_status'] = str(feedback.get('status') or '')
                payload['repeat_policy'] = 'require_new_evidence' if str(feedback.get('status') or '') == 'false_improvement' else (
                    'resolved_or_validated' if str(feedback.get('status') or '') in {'validated_improvement', 'valid_adjustment'} else 'pending_evidence'
                )
                payload['feedback_note'] = str(feedback.get('next_step') or '').strip()
            updated.append(payload)
        return updated

    def _feedback_summary(self, recommendation_feedback: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(str(item.get('status') or 'unknown') for item in recommendation_feedback)
        return {
            'total_reviewed': len(recommendation_feedback),
            'validated_improvement': int(counts.get('validated_improvement', 0)),
            'valid_adjustment': int(counts.get('valid_adjustment', 0)),
            'false_improvement': int(counts.get('false_improvement', 0)),
            'no_evidence': int(counts.get('no_evidence', 0)),
        }

    def _validated_improvements(
        self,
        *,
        recommendations: list[ExperimentRecommendation],
        validation: AutonomousValidationSnapshot,
        experiment_runs: list[ExperimentRun],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_feedback_keys: set[str] = set()
        for recommendation in recommendations[:4]:
            if float(recommendation.confidence or 0.0) < 0.75 and float(recommendation.score or 0.0) < 0.75:
                continue
            adaptive = dict((recommendation.metadata or {}).get('adaptive_learning_summary') or {})
            feedback_key = self._adjustment_feedback_key(
                category='inertial_route',
                title=f'{recommendation.recommended_assistant_kind or "ruta"} por {recommendation.recommended_route.value}',
                metadata={
                    'assistant_kind': recommendation.recommended_assistant_kind,
                    'route': recommendation.recommended_route.value,
                    'config_signature': recommendation.recommended_config_signature,
                    'subject_key': recommendation.subject_key,
                },
            )
            if feedback_key in seen_feedback_keys:
                continue
            seen_feedback_keys.add(feedback_key)
            items.append(
                {
                    'title': f'{recommendation.recommended_assistant_kind or "ruta"} por {recommendation.recommended_route.value}',
                    'summary': str(recommendation.rationale or '').strip(),
                    'subject_key': recommendation.subject_key,
                    'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                    'recommended_route': recommendation.recommended_route.value,
                    'confidence': float(recommendation.confidence or 0.0),
                    'score': float(recommendation.score or 0.0),
                    'reasons': list(adaptive.get('reasons') or []),
                    'source_refs': ['ExperimentLab', 'StrategySelector'],
                    'evidence_refs': list(recommendation.supporting_run_ids[:4]),
                    'feedback_key': feedback_key,
                }
            )
        current_experiment = validation.current_experiment
        if int(validation.promoted_count or 0) > 0:
            items.append(
                {
                    'title': 'Promocion validada en sandbox',
                    'summary': str(validation.summary or '').strip() or 'Una alternativa ya fue promovida tras validacion controlada.',
                    'subject_key': str(getattr(current_experiment, 'subject_key', '') or ''),
                    'recommended_assistant_kind': str(getattr(current_experiment, 'candidate_assistant_kind', '') or ''),
                    'recommended_route': str(getattr(getattr(current_experiment, 'candidate_route', None), 'value', getattr(current_experiment, 'candidate_route', '')) or ''),
                    'confidence': 0.82,
                    'score': min(1.0, 0.68 + int(validation.promoted_count or 0) * 0.06),
                    'reasons': [str(validation.summary or '').strip()] if str(validation.summary or '').strip() else [],
                    'source_refs': ['AutonomousValidationSnapshot'],
                    'evidence_refs': [str(validation.last_experiment_id or '')] if str(validation.last_experiment_id or '').strip() else [],
                    'feedback_key': self._adjustment_feedback_key(
                        category='validation',
                        title='Promocion validada en sandbox',
                        metadata={
                            'assistant_kind': str(getattr(current_experiment, 'candidate_assistant_kind', '') or ''),
                            'route': str(getattr(getattr(current_experiment, 'candidate_route', None), 'value', getattr(current_experiment, 'candidate_route', '')) or ''),
                            'config_signature': str(getattr(current_experiment, 'candidate_config_signature', '') or ''),
                            'subject_key': str(getattr(current_experiment, 'subject_key', '') or ''),
                        },
                    ),
                }
            )
        if not items and experiment_runs:
            best_run = max(experiment_runs, key=lambda item: float(item.metrics.total_score or 0.0))
            items.append(
                {
                    'title': f'{best_run.assistant_kind or "ruta"} por {best_run.route.value}',
                    'summary': 'Hay una mejora fuerte en experimentos recientes, pero todavia no un recommendation consolidado.',
                    'subject_key': best_run.subject_key,
                    'recommended_assistant_kind': best_run.assistant_kind,
                    'recommended_route': best_run.route.value,
                    'confidence': 0.58,
                    'score': float(best_run.metrics.total_score or 0.0),
                    'reasons': [],
                    'source_refs': ['ExperimentLab'],
                    'evidence_refs': [best_run.run_id],
                    'feedback_key': self._adjustment_feedback_key(
                        category='inertial_route',
                        title=f'{best_run.assistant_kind or "ruta"} por {best_run.route.value}',
                        metadata={
                            'assistant_kind': best_run.assistant_kind,
                            'route': best_run.route.value,
                            'config_signature': best_run.config_signature,
                            'subject_key': best_run.subject_key,
                        },
                    ),
                }
            )
        return items[:4]

    # ------------------------------------------------------------------
    # Cognitive meta-patterns
    # ------------------------------------------------------------------

    def _cognitive_fixation_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        recommendations: list[ExperimentRecommendation],
    ) -> list[SelfExaminationFinding]:
        """Detect cognitive fixation: the system choosing the same IA/route
        repeatedly despite availability of better alternatives.

        Cognitive fixation occurs when the orchestrator "locks on" to a
        familiar route even when evidence shows declining performance.
        This goes beyond route_inertia (which is about the decision log)
        by examining the actual experiment outcomes for persistent bias.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 5:
            return findings
        kind_counts: dict[str, int] = defaultdict(int)
        kind_recent_failures: dict[str, int] = defaultdict(int)
        recent_runs = experiment_runs[-10:]
        for run in recent_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            if not kind:
                continue
            kind_counts[kind] += 1
            if not bool(run.success):
                kind_recent_failures[kind] += 1
        dominant_kind = max(kind_counts, key=kind_counts.get, default='')  # type: ignore[arg-type]
        if not dominant_kind:
            return findings
        dominant_ratio = kind_counts[dominant_kind] / len(recent_runs)
        dominant_failure_rate = kind_recent_failures.get(dominant_kind, 0) / max(kind_counts[dominant_kind], 1)
        better_alternatives = [
            rec for rec in recommendations
            if str(rec.recommended_assistant_kind or '').strip().lower() != dominant_kind
            and float(rec.confidence or 0.0) > 0.6
        ]
        if dominant_ratio >= 0.7 and dominant_failure_rate >= 0.4 and better_alternatives:
            findings.append(SelfExaminationFinding(
                title=f'Fijación cognitiva en {dominant_kind}',
                description=(
                    f'El sistema sigue eligiendo {dominant_kind} en {dominant_ratio:.0%} de los últimos runs '
                    f'a pesar de una tasa de fallo de {dominant_failure_rate:.0%}. '
                    f'Hay {len(better_alternatives)} alternativa(s) recomendada(s) con mayor confianza.'
                ),
                severity=IssueSeverity.HIGH,
                category='cognitive_fixation',
                metadata={
                    'dominant_kind': dominant_kind,
                    'dominant_ratio': round(dominant_ratio, 4),
                    'failure_rate': round(dominant_failure_rate, 4),
                    'alternative_count': len(better_alternatives),
                    'best_alternative': str(better_alternatives[0].recommended_assistant_kind or ''),
                },
            ))
        return findings

    def _cognitive_incubation_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect when cognitive incubation could help: problems that failed
        multiple times recently but might benefit from a "cooling period."

        Incubation is the cognitive phenomenon where stepping away from a
        problem allows subconscious processing to find a solution.  Here
        we detect subject_keys with 3+ consecutive failures and suggest
        deferring them to let the system gather new evidence or context.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 3:
            return findings
        subject_recent_failures: dict[str, int] = defaultdict(int)
        subject_total: dict[str, int] = defaultdict(int)
        for run in experiment_runs[-15:]:
            sk = str(run.subject_key or '').strip()
            if not sk:
                continue
            subject_total[sk] += 1
            if not bool(run.success):
                subject_recent_failures[sk] += 1
            else:
                subject_recent_failures[sk] = 0
        for sk, consecutive_fails in subject_recent_failures.items():
            if consecutive_fails >= 3 and subject_total.get(sk, 0) >= 3:
                findings.append(SelfExaminationFinding(
                    title=f'Incubación cognitiva sugerida para {sk}',
                    description=(
                        f'El problema {sk} acumula {consecutive_fails} fallos consecutivos recientes. '
                        f'Postergar este subject_key por 1-2 ciclos para acumular contexto o '
                        f'permitir que el AdaptiveWeightLayer recalcule con datos frescos.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    category='cognitive_incubation',
                    metadata={
                        'subject_key': sk,
                        'consecutive_failures': consecutive_fails,
                        'total_runs': subject_total.get(sk, 0),
                    },
                ))
        return findings[:2]

    def _neural_attractor_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect neural attractors: stable configurations the system
        converges toward naturally.

        An attractor is a (route, assistant_kind, config) combination
        that consistently produces good results.  Identifying attractors
        helps the system consciously reinforce what works instead of
        drifting.  If no attractor exists, that itself is a finding.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 4:
            return findings
        config_success: dict[str, list[float]] = defaultdict(list)
        config_total: dict[str, int] = defaultdict(int)
        for run in experiment_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            route = str(run.route.value if run.route else '')
            if not kind:
                continue
            key = f'{kind}:{route}'
            config_total[key] += 1
            if bool(run.success):
                config_success[key].append(float(run.metrics.total_score or 0.0))
        attractors: list[tuple[str, float, int]] = []
        for key, scores in config_success.items():
            total = config_total.get(key, len(scores))
            if total < 3:
                continue
            success_rate = len(scores) / max(total, 1)
            avg_score = sum(scores) / max(len(scores), 1)
            if success_rate >= 0.75 and avg_score >= 0.5:
                attractors.append((key, avg_score, total))
        if attractors:
            attractors.sort(key=lambda t: (t[1], t[2]), reverse=True)
            best = attractors[0]
            findings.append(SelfExaminationFinding(
                title=f'Atractor neuronal identificado: {best[0]}',
                description=(
                    f'La configuración {best[0]} converge a resultados positivos consistentemente '
                    f'(score {best[1]:.2f}, {best[2]} runs). Este atractor debe ser reforzado '
                    f'como ruta preferente para tareas compatibles.'
                ),
                severity=IssueSeverity.LOW,
                category='neural_attractor',
                metadata={
                    'attractor_key': best[0],
                    'avg_score': round(best[1], 4),
                    'total_runs': best[2],
                    'all_attractors': [{'key': a[0], 'score': round(a[1], 4), 'runs': a[2]} for a in attractors[:3]],
                },
            ))
        elif len(experiment_runs) >= 8:
            findings.append(SelfExaminationFinding(
                title='Sin atractor neuronal estable',
                description=(
                    'No se detecta ninguna configuración (IA+ruta) que converja consistentemente '
                    'a resultados positivos. El sistema opera sin preferencia estable, lo que '
                    'puede indicar exploración excesiva o datos insuficientes.'
                ),
                severity=IssueSeverity.MEDIUM,
                category='neural_attractor',
                metadata={'experiment_count': len(experiment_runs)},
            ))
        return findings[:1]

    def _neural_ensemble_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect neural ensembles: groups of IAs that work well together.

        A neural ensemble is the activation of multiple "neurons" (services/IAs)
        working in concert.  Here we identify pairs of assistant_kinds that,
        when used on the same subject_key, produce consistently better
        outcomes than either alone.
        """
        findings: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 6:
            return findings
        subject_kind_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for run in experiment_runs:
            sk = str(run.subject_key or '').strip()
            kind = str(run.assistant_kind or '').strip().lower()
            if not sk or not kind:
                continue
            score = float(run.metrics.total_score or 0.0) if bool(run.success) else 0.0
            subject_kind_scores[sk][kind].append(score)
        ensembles: list[tuple[str, str, str, float]] = []
        for sk, kinds_map in subject_kind_scores.items():
            active_kinds = [k for k, scores in kinds_map.items() if len(scores) >= 2]
            if len(active_kinds) < 2:
                continue
            for i, k1 in enumerate(active_kinds):
                for k2 in active_kinds[i + 1:]:
                    avg1 = sum(kinds_map[k1]) / max(len(kinds_map[k1]), 1)
                    avg2 = sum(kinds_map[k2]) / max(len(kinds_map[k2]), 1)
                    combined = (avg1 + avg2) / 2
                    if combined > 0.4:
                        ensembles.append((sk, k1, k2, round(combined, 4)))
        if ensembles:
            ensembles.sort(key=lambda t: t[3], reverse=True)
            best = ensembles[0]
            findings.append(SelfExaminationFinding(
                title=f'Ensamble neuronal detectado: {best[1]} + {best[2]}',
                description=(
                    f'Para el problema {best[0]}, la combinación {best[1]} + {best[2]} '
                    f'produce un score combinado de {best[3]:.2f}. Este ensamble debe '
                    f'ser considerado para planes coordinados futuros en tareas similares.'
                ),
                severity=IssueSeverity.LOW,
                category='neural_ensemble',
                metadata={
                    'subject_key': best[0],
                    'ensemble_pair': [best[1], best[2]],
                    'combined_score': best[3],
                    'all_ensembles': [{'subject': e[0], 'pair': [e[1], e[2]], 'score': e[3]} for e in ensembles[:3]],
                },
            ))
        return findings[:1]

    # ------------------------------------------------------------------
    # Loop-closure introspection: the system audits its own mechanisms
    # ------------------------------------------------------------------

    def _loop_closure_findings(
        self,
        *,
        findings_so_far: list[SelfExaminationFinding],
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Introspect whether G1, G2, G3, G4 and cognitive mechanisms are active.

        This is the system's self-awareness of its own architecture: it
        checks that the introspective loop is actually closed by verifying
        each mechanism is wired and producing output.  If a gap is detected,
        a finding with severity HIGH is emitted so the user (or the system
        itself) can act.
        """
        results: list[SelfExaminationFinding] = []
        checks: list[dict[str, Any]] = []

        # --- G1: auto-execution wire ---
        validation_cycle = self.autonomous_validation_cycle
        g1_wired = False
        g1_has_executed = False
        if validation_cycle is not None:
            orchestrator = getattr(validation_cycle, 'adaptive_task_orchestrator', None)
            g1_wired = orchestrator is not None
            executed_keys = getattr(validation_cycle, '_auto_executed_keys', None)
            if isinstance(executed_keys, set):
                g1_has_executed = len(executed_keys) > 0
        checks.append({
            'mechanism': 'G1_auto_execution',
            'wired': g1_wired,
            'active': g1_has_executed,
            'detail': 'orchestrator wired' if g1_wired else 'orchestrator NOT connected to validation_cycle',
        })

        # --- G2: validation feedback persistence ---
        feedback_path = Path(self.workspace_root) / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
        g2_file_exists = feedback_path.is_file()
        g2_entry_count = 0
        if g2_file_exists:
            try:
                g2_entry_count = sum(1 for line in feedback_path.read_text(encoding='utf-8').splitlines() if line.strip())
            except Exception:
                pass
        checks.append({
            'mechanism': 'G2_feedback_persistence',
            'wired': True,
            'active': g2_file_exists and g2_entry_count > 0,
            'detail': f'{g2_entry_count} entries' if g2_file_exists else 'history.jsonl not yet created (fires after first validation)',
        })

        # --- G3: AdaptiveWeightLayer connected ---
        g3_wired = self.adaptive_weight_layer is not None
        g3_has_suggest = g3_wired and callable(getattr(self.adaptive_weight_layer, 'suggest', None))
        checks.append({
            'mechanism': 'G3_weight_layer',
            'wired': g3_wired,
            'active': g3_has_suggest,
            'detail': 'suggest() available' if g3_has_suggest else ('layer connected but no suggest()' if g3_wired else 'AdaptiveWeightLayer NOT connected'),
        })

        # --- G4: Metacognitive feedback loop ---
        g4_wired = (
            self.adaptive_weight_layer is not None
            and hasattr(self.adaptive_weight_layer, 'apply_metacognitive_adjustment')
        )
        g4_active = False
        if g4_wired:
            adjustments = getattr(self.adaptive_weight_layer, '_metacognitive_adjustments', {})
            g4_active = len(adjustments) > 0
        checks.append({
            'mechanism': 'G4_metacognitive_feedback',
            'wired': g4_wired,
            'active': g4_active,
            'detail': (
                f'{len(getattr(self.adaptive_weight_layer, "_metacognitive_adjustments", {}))} adjustments active'
                if g4_active
                else ('wired but no adjustments yet' if g4_wired else 'metacognitive feedback NOT connected')
            ),
        })

        # --- Cognitive mechanisms: check if findings were generated ---
        cognitive_categories = {'cognitive_fixation', 'cognitive_incubation', 'neural_attractor', 'neural_ensemble'}
        found_categories = {f.category for f in findings_so_far if f.category in cognitive_categories}
        checks.append({
            'mechanism': 'cognitive_findings',
            'wired': True,
            'active': len(found_categories) > 0,
            'detail': f'active categories: {sorted(found_categories)}' if found_categories else f'none active (need >= 5 experiment runs, have {len(experiment_runs)})',
        })

        # --- Summary ---
        wired_count = sum(1 for c in checks if c['wired'])
        active_count = sum(1 for c in checks if c['active'])
        total = len(checks)
        all_wired = wired_count == total
        all_active = active_count == total

        if all_wired and all_active:
            results.append(SelfExaminationFinding(
                title='Loop introspectivo cerrado: todos los mecanismos activos',
                description=(
                    f'G1 (auto-ejecución), G2 (feedback persistence), G3 (weight layer) y '
                    f'mecanismos cognitivos están wired y produciendo output. '
                    f'El sistema se auto-observa y actúa sin intervención manual.'
                ),
                severity=IssueSeverity.LOW,
                category='loop_closure',
                metadata={
                    'checks': checks,
                    'wired': wired_count,
                    'active': active_count,
                    'total': total,
                    'closed': True,
                },
            ))
        else:
            gaps = [c for c in checks if not c['wired'] or not c['active']]
            gap_names = [c['mechanism'] for c in gaps]
            results.append(SelfExaminationFinding(
                title=f'Loop introspectivo abierto: {len(gaps)} mecanismo(s) inactivo(s)',
                description=(
                    f'Mecanismos con gaps: {", ".join(gap_names)}. '
                    f'{wired_count}/{total} wired, {active_count}/{total} activos. '
                    + '; '.join(f"{c['mechanism']}: {c['detail']}" for c in gaps)
                ),
                severity=IssueSeverity.HIGH if not all_wired else IssueSeverity.MEDIUM,
                category='loop_closure',
                metadata={
                    'checks': checks,
                    'wired': wired_count,
                    'active': active_count,
                    'total': total,
                    'closed': False,
                    'gap_mechanisms': gap_names,
                },
            ))

        return results[:1]

    # ------------------------------------------------------------------
    # Metacognitive error detection: the system audits its own
    # introspection quality and learns from its metacognitive mistakes
    # ------------------------------------------------------------------

    def _metacognitive_accuracy_findings(
        self,
        *,
        previous_review: SelfExaminationSnapshot | None,
        current_findings: list[SelfExaminationFinding],
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Detect metacognitive errors: false positives and false negatives.

        A *false positive* is a previous finding that predicted a problem
        but subsequent evidence shows no degradation occurred — the system
        "cried wolf."  A *false negative* is a new failure pattern that
        appeared without any prior finding warning about it — a blind spot
        in the introspective loop.

        Tracking these errors lets the system learn which of its own
        diagnostic categories are reliable and which need recalibration.
        """
        results: list[SelfExaminationFinding] = []
        if previous_review is None or not experiment_runs:
            return results

        reviewed_after = previous_review.updated_at_utc
        post_runs = [
            run for run in experiment_runs
            if getattr(run, 'created_at_utc', None) is not None
            and run.created_at_utc > reviewed_after
        ]
        if len(post_runs) < 3:
            return results

        # --- False positives: previous HIGH findings without subsequent failures ---
        false_positives: list[str] = []
        for prev_finding in (previous_review.findings or []):
            if prev_finding.severity != IssueSeverity.HIGH:
                continue
            meta = dict(prev_finding.metadata or {})
            dominant_kind = str(meta.get('dominant_kind') or meta.get('assistant_kind') or '').strip().lower()
            subject_key = str(meta.get('subject_key') or '').strip()

            related_runs: list[ExperimentRun] = []
            for run in post_runs:
                run_kind = str(run.assistant_kind or '').strip().lower()
                run_subject = str(run.subject_key or '').strip()
                if dominant_kind and run_kind == dominant_kind:
                    related_runs.append(run)
                elif subject_key and run_subject == subject_key:
                    related_runs.append(run)

            if len(related_runs) >= 3:
                post_success_rate = sum(1 for r in related_runs if r.success) / len(related_runs)
                if post_success_rate >= 0.75:
                    false_positives.append(
                        f'{prev_finding.category}:{prev_finding.title} '
                        f'(success_rate posterior {post_success_rate:.0%})'
                    )

        if false_positives:
            results.append(SelfExaminationFinding(
                title=f'Falsos positivos metacognitivos: {len(false_positives)} hallazgo(s) sin confirmar',
                summary=(
                    f'La introspección previa emitió {len(false_positives)} hallazgo(s) HIGH que la '
                    f'evidencia posterior no confirmó. El sistema sobreestimó riesgos que no se '
                    f'materializaron: {"; ".join(false_positives[:3])}.'
                ),
                severity=IssueSeverity.MEDIUM,
                category='metacognitive_false_positive',
                confidence=min(0.85, 0.5 + len(false_positives) * 0.1),
                recommendation=(
                    'Recalibrar los umbrales de severidad para estas categorías. '
                    'Exigir más evidencia antes de emitir hallazgos HIGH en ellas.'
                ),
                metadata={
                    'false_positives': false_positives[:6],
                    'post_run_count': len(post_runs),
                },
            ))

        # --- False negatives: failures without prior warning ---
        current_finding_scopes: set[str] = set()
        for finding in (previous_review.findings or []):
            meta = dict(finding.metadata or {})
            scope_key = str(meta.get('dominant_kind') or meta.get('subject_key') or finding.category or '').strip().lower()
            if scope_key:
                current_finding_scopes.add(scope_key)

        failure_kinds: Counter[str] = Counter()
        for run in post_runs:
            if not run.success:
                kind = str(run.assistant_kind or '').strip().lower()
                if kind:
                    failure_kinds[kind] += 1

        false_negatives: list[str] = []
        for kind, fail_count in failure_kinds.items():
            if fail_count >= 3 and kind not in current_finding_scopes:
                kind_total = sum(1 for r in post_runs if str(r.assistant_kind or '').strip().lower() == kind)
                fail_rate = fail_count / max(kind_total, 1)
                if fail_rate >= 0.5:
                    false_negatives.append(f'{kind} ({fail_count} fallos, {fail_rate:.0%} tasa)')

        if false_negatives:
            results.append(SelfExaminationFinding(
                title=f'Puntos ciegos metacognitivos: {len(false_negatives)} fallo(s) no anticipado(s)',
                summary=(
                    f'Aparecieron {len(false_negatives)} patrón(es) de fallo que la introspección '
                    f'previa no detectó ni anticipó: {"; ".join(false_negatives[:3])}. '
                    f'Esto indica áreas donde la autoexaminación no está mirando.'
                ),
                severity=IssueSeverity.HIGH,
                category='metacognitive_false_negative',
                confidence=min(0.90, 0.55 + len(false_negatives) * 0.12),
                recommendation=(
                    'Ampliar la cobertura introspectiva para incluir estas rutas/IAs. '
                    'Considerar agregar monitores específicos para los patrones no detectados.'
                ),
                metadata={
                    'false_negatives': false_negatives[:6],
                    'post_run_count': len(post_runs),
                },
            ))

        return results[:2]

    def _introspection_blind_spot_findings(
        self,
        *,
        experiment_runs: list[ExperimentRun],
        findings_so_far: list[SelfExaminationFinding],
    ) -> list[SelfExaminationFinding]:
        """Detect areas the system's introspection never examines.

        A blind spot is a route/assistant_kind combination that has
        experiment runs (operational evidence) but has NEVER been
        flagged by any introspective finding.  This means the system
        is operating in those areas but not reflecting on them.
        """
        results: list[SelfExaminationFinding] = []
        if len(experiment_runs) < 5:
            return results

        kind_run_counts: Counter[str] = Counter()
        kind_failure_counts: Counter[str] = Counter()
        for run in experiment_runs:
            kind = str(run.assistant_kind or '').strip().lower()
            if not kind:
                continue
            kind_run_counts[kind] += 1
            if not run.success:
                kind_failure_counts[kind] += 1

        examined_kinds: set[str] = set()
        for finding in findings_so_far:
            meta = dict(finding.metadata or {})
            for key in ('dominant_kind', 'assistant_kind', 'attractor_key'):
                val = str(meta.get(key) or '').strip().lower()
                if val:
                    examined_kinds.add(val.split(':')[0])
            if finding.category in {'cognitive_fixation', 'cognitive_incubation',
                                     'neural_attractor', 'neural_ensemble'}:
                for key_val in meta.values():
                    if isinstance(key_val, str):
                        examined_kinds.add(key_val.strip().lower().split(':')[0])

        blind_spots: list[str] = []
        for kind, count in kind_run_counts.most_common():
            if count >= 3 and kind not in examined_kinds:
                fail_rate = kind_failure_counts.get(kind, 0) / max(count, 1)
                blind_spots.append(f'{kind} ({count} runs, {fail_rate:.0%} fallos)')

        if blind_spots:
            results.append(SelfExaminationFinding(
                title=f'Puntos ciegos introspectivos: {len(blind_spots)} IA(s) sin examinar',
                summary=(
                    f'El sistema tiene actividad operativa en {len(blind_spots)} IA(s) que '
                    f'nunca aparecen en hallazgos introspectivos: {"; ".join(blind_spots[:4])}. '
                    f'La autoexaminación no cubre estas áreas, lo que puede ocultar patrones '
                    f'de degradación silenciosa.'
                ),
                severity=IssueSeverity.MEDIUM,
                category='introspection_blind_spot',
                confidence=min(0.80, 0.45 + len(blind_spots) * 0.1),
                recommendation=(
                    'Incluir estas IAs en los ciclos de análisis cognitivo (fijación, '
                    'incubación, atractores). Monitorear su tasa de fallo activamente.'
                ),
                metadata={
                    'blind_spots': blind_spots[:8],
                    'examined_kinds': sorted(examined_kinds),
                    'total_kinds': len(kind_run_counts),
                },
            ))
        return results[:1]

    def _metacognitive_calibration_findings(
        self,
        *,
        previous_review: SelfExaminationSnapshot | None,
        experiment_runs: list[ExperimentRun],
    ) -> list[SelfExaminationFinding]:
        """Measure how well the system's confidence predicts reality.

        Compares the confidence scores emitted in previous findings against
        the actual outcomes that followed.  Systematic overconfidence
        (high confidence but poor outcomes) or underconfidence (low
        confidence but good outcomes) are metacognitive calibration errors
        that the system should learn to correct.
        """
        results: list[SelfExaminationFinding] = []
        if previous_review is None or not experiment_runs:
            return results

        reviewed_after = previous_review.updated_at_utc
        post_runs = [
            run for run in experiment_runs
            if getattr(run, 'created_at_utc', None) is not None
            and run.created_at_utc > reviewed_after
        ]
        if len(post_runs) < 3:
            return results

        post_success_rate = sum(1 for r in post_runs if r.success) / max(len(post_runs), 1)

        # Historical calibration: load ledger to detect persistent patterns.
        # Runs independently of calibrated_findings — only needs the ledger.
        ledger = self._load_metacognitive_ledger()
        if ledger:
            total_fp = sum(len(entry.get('false_positives') or []) for entry in ledger)
            total_fn = sum(len(entry.get('false_negatives') or []) for entry in ledger)
            if total_fp + total_fn >= 4:
                dominant_error = 'falsos positivos' if total_fp > total_fn else 'falsos negativos'
                results.append(SelfExaminationFinding(
                    title=f'Patrón metacognitivo persistente: tendencia a {dominant_error}',
                    summary=(
                        f'El ledger metacognitivo acumula {total_fp} falso(s) positivo(s) y '
                        f'{total_fn} falso(s) negativo(s) en {len(ledger)} ciclo(s). '
                        f'La tendencia dominante es hacia {dominant_error}, lo que indica '
                        f'un sesgo sistemático en la autoexaminación.'
                    ),
                    severity=IssueSeverity.HIGH,
                    category='metacognitive_persistent_bias',
                    confidence=min(0.92, 0.5 + (total_fp + total_fn) * 0.04),
                    recommendation=(
                        f'Recalibrar umbrales de detección para compensar el sesgo hacia {dominant_error}. '
                        f'Si el sesgo es hacia falsos positivos, elevar los mínimos de evidencia. '
                        f'Si es hacia falsos negativos, ampliar la cobertura de monitoreo.'
                    ),
                    metadata={
                        'total_false_positives': total_fp,
                        'total_false_negatives': total_fn,
                        'ledger_entries': len(ledger),
                        'dominant_error': dominant_error,
                    },
                ))

        # Overconfidence / underconfidence checks require calibrated findings
        calibrated_findings = [
            f for f in (previous_review.findings or [])
            if f.confidence > 0.0
        ]
        if not calibrated_findings:
            return results[:2]

        avg_confidence = sum(f.confidence for f in calibrated_findings) / len(calibrated_findings)
        high_severity_count = sum(1 for f in calibrated_findings if f.severity in {IssueSeverity.HIGH, IssueSeverity.CRITICAL})
        high_severity_ratio = high_severity_count / max(len(calibrated_findings), 1)

        # Overconfidence: system predicts problems with high confidence
        # but outcomes are actually good
        if avg_confidence >= 0.65 and high_severity_ratio >= 0.5 and post_success_rate >= 0.75:
            calibration_gap = avg_confidence - (1.0 - post_success_rate)
            results.append(SelfExaminationFinding(
                title='Sobreconfianza metacognitiva detectada',
                summary=(
                    f'La introspección previa emitió hallazgos con confianza promedio '
                    f'{avg_confidence:.2f} y {high_severity_ratio:.0%} de severidad alta, '
                    f'pero la tasa de éxito posterior fue {post_success_rate:.0%}. '
                    f'El sistema sobreestima sus propios problemas (brecha de calibración: '
                    f'{calibration_gap:.2f}).'
                ),
                severity=IssueSeverity.MEDIUM,
                category='metacognitive_overconfidence',
                confidence=min(0.85, 0.5 + calibration_gap * 0.3),
                recommendation=(
                    'Reducir la sensibilidad de los umbrales de severidad HIGH. '
                    'Exigir mayor evidencia antes de elevar hallazgos. '
                    'El sistema debe confiar más en su propia capacidad operativa.'
                ),
                metadata={
                    'avg_finding_confidence': round(avg_confidence, 4),
                    'high_severity_ratio': round(high_severity_ratio, 4),
                    'post_success_rate': round(post_success_rate, 4),
                    'calibration_gap': round(calibration_gap, 4),
                    'finding_count': len(calibrated_findings),
                    'post_run_count': len(post_runs),
                },
            ))

        # Underconfidence: system predicts everything is fine with low
        # confidence and low severity but outcomes are bad
        if avg_confidence < 0.45 and high_severity_ratio < 0.2 and post_success_rate < 0.5:
            calibration_gap = (1.0 - post_success_rate) - avg_confidence
            results.append(SelfExaminationFinding(
                title='Subconfianza metacognitiva detectada',
                summary=(
                    f'La introspección previa fue tibia (confianza promedio {avg_confidence:.2f}, '
                    f'solo {high_severity_ratio:.0%} severidad alta) pero la tasa de éxito '
                    f'posterior fue baja ({post_success_rate:.0%}). El sistema subestima '
                    f'sus propios problemas (brecha de calibración: {calibration_gap:.2f}).'
                ),
                severity=IssueSeverity.HIGH,
                category='metacognitive_underconfidence',
                confidence=min(0.90, 0.55 + calibration_gap * 0.3),
                recommendation=(
                    'Aumentar la sensibilidad de detección para fallos repetidos. '
                    'El sistema debe ser más agresivo al señalar riesgos operativos. '
                    'Revisar si los hallazgos actuales cubren los patrones reales de fallo.'
                ),
                metadata={
                    'avg_finding_confidence': round(avg_confidence, 4),
                    'high_severity_ratio': round(high_severity_ratio, 4),
                    'post_success_rate': round(post_success_rate, 4),
                    'calibration_gap': round(calibration_gap, 4),
                    'finding_count': len(calibrated_findings),
                    'post_run_count': len(post_runs),
                },
            ))

        return results[:2]

    def _response_grounding_gap_findings(
        self,
        *,
        previous_review: SelfExaminationSnapshot | None,
        current_findings: list[SelfExaminationFinding],
    ) -> list[SelfExaminationFinding]:
        """Detect when OSES has concrete data but its output doesn't use it.

        This is meta-metacognition: the system checks whether its OWN
        analysis is grounded in the data it actually has.  If concrete
        metrics (observed_ms, threshold_ms, phases_seen, etc.) exist in
        finding metadata but the assistant_brief from the previous review
        doesn't reference them, the system is being generic when it should
        be specific.

        Also checks if the startup timeline has observable phases that
        no finding references at all — data exists but OSES itself
        didn't analyze it.
        """
        results: list[SelfExaminationFinding] = []

        # --- Check 1: concrete metrics exist in findings but brief is vague ---
        if previous_review is not None and previous_review.assistant_brief:
            brief = previous_review.assistant_brief.lower()
            concrete_findings = []
            ungrounded_findings = []
            for finding in (previous_review.findings or []):
                meta = dict(finding.metadata or {})
                observed_ms = meta.get('observed_ms')
                threshold_ms = meta.get('threshold_ms')
                if observed_ms is not None:
                    concrete_findings.append(finding)
                    ms_str = str(int(observed_ms))
                    if ms_str not in brief:
                        ungrounded_findings.append(
                            f'{finding.category}: {finding.title} '
                            f'(observed_ms={observed_ms} no aparece en brief)'
                        )

            if ungrounded_findings and len(concrete_findings) >= 1:
                results.append(SelfExaminationFinding(
                    title=f'Gap de grounding: {len(ungrounded_findings)} hallazgo(s) con datos concretos no citados',
                    summary=(
                        f'OSES tiene {len(concrete_findings)} hallazgo(s) con metricas '
                        f'concretas (observed_ms, threshold_ms) pero el assistant_brief '
                        f'no incluye esos numeros. El sistema tiene datos especificos '
                        f'pero los omite en su output, causando respuestas genericas.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    category='metacognition_grounding_gap',
                    confidence=min(0.90, 0.55 + len(ungrounded_findings) * 0.1),
                    recommendation=(
                        'Incluir metricas observadas (ms, %, conteos) en el '
                        'assistant_brief y en las respuestas de autoexaminacion. '
                        'Cuando un finding tiene metadata.observed_ms, citarlo '
                        'explicitamente en vez de solo mencionar el titulo.'
                    ),
                    metadata={
                        'ungrounded_findings': ungrounded_findings[:6],
                        'total_concrete_findings': len(concrete_findings),
                        'brief_length': len(brief),
                    },
                ))

        # --- Check 2: timeline phases exist but no finding references them ---
        log_path = Path(self.workspace_root) / 'data' / 'logs' / 'startup_timeline.jsonl'
        if log_path.exists():
            try:
                timeline_phases: set[str] = set()
                with log_path.open('r', encoding='utf-8') as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            evt = json.loads(line)
                            phase = str(evt.get('phase') or '')
                            if phase:
                                timeline_phases.add(phase)
                        except json.JSONDecodeError:
                            continue

                finding_phases: set[str] = set()
                for finding in current_findings:
                    meta = dict(finding.metadata or {})
                    phases = meta.get('phases_seen')
                    if isinstance(phases, list):
                        finding_phases.update(str(p) for p in phases)
                    phase_val = str(meta.get('phase') or '')
                    if phase_val:
                        finding_phases.add(phase_val)

                unanalyzed = timeline_phases - finding_phases
                # Filter to phases that likely carry diagnostic value
                diagnostic_prefixes = (
                    'dashboard_vm_', 'bootstrap_', 'populate_ui_',
                    'shell_loader_', 'page_loader_', 'deferred_',
                    'main_window_', 'splash_', 'run_start',
                )
                meaningful_unanalyzed = [
                    p for p in sorted(unanalyzed)
                    if any(p.startswith(prefix) for prefix in diagnostic_prefixes)
                ]

                if len(meaningful_unanalyzed) >= 3:
                    results.append(SelfExaminationFinding(
                        title=f'Fases del timeline sin analizar: {len(meaningful_unanalyzed)}',
                        summary=(
                            f'El startup timeline tiene {len(timeline_phases)} fases '
                            f'observadas pero {len(meaningful_unanalyzed)} fases '
                            f'diagnosticas no son referenciadas por ningun finding: '
                            f'{", ".join(meaningful_unanalyzed[:5])}. '
                            f'OSES no esta aprovechando toda la informacion disponible.'
                        ),
                        severity=IssueSeverity.LOW,
                        category='metacognition_grounding_gap',
                        confidence=0.70,
                        recommendation=(
                            'Ampliar _startup_health_findings() para analizar '
                            'las fases diagnosticas faltantes del timeline.'
                        ),
                        metadata={
                            'total_timeline_phases': len(timeline_phases),
                            'analyzed_phases': len(finding_phases),
                            'meaningful_unanalyzed': meaningful_unanalyzed[:10],
                        },
                    ))
            except OSError:
                pass

        return results[:2]

    def _persist_metacognitive_ledger_from_findings(
        self,
        findings: list[SelfExaminationFinding],
        *,
        review_id: str = '',
    ) -> None:
        """Extract metacognitive errors from findings and persist to ledger.

        Called from ``_persist_review`` (after all findings are finalized)
        so that ``_metacognitive_calibration_findings`` only reads
        *previous* cycles during the same ``build_review()`` call.
        """
        false_positives: list[str] = []
        false_negatives: list[str] = []
        for finding in findings:
            meta = dict(finding.metadata or {})
            if finding.category == 'metacognitive_false_positive':
                false_positives = list(meta.get('false_positives') or [])
            elif finding.category == 'metacognitive_false_negative':
                false_negatives = list(meta.get('false_negatives') or [])
        if false_positives or false_negatives:
            self._persist_metacognitive_ledger(
                false_positives=false_positives,
                false_negatives=false_negatives,
                review_id=review_id,
            )

    def _persist_metacognitive_ledger(
        self,
        *,
        false_positives: list[str],
        false_negatives: list[str],
        review_id: str,
    ) -> None:
        """Append a metacognitive error entry to the learning ledger.

        The ledger persists across reviews so the system can detect
        *persistent* metacognitive biases (e.g. always producing false
        positives in a certain category).
        """
        ledger_rel = 'self_examination/metacognitive_ledger.jsonl'
        entry = json.dumps({
            'review_id': review_id,
            'timestamp': utc_now().isoformat(),
            'false_positives': false_positives[:8],
            'false_negatives': false_negatives[:8],
        }, ensure_ascii=False)
        try:
            existing = ''
            if self.storage.exists(ledger_rel):
                existing = self.storage.load_bytes(ledger_rel).decode('utf-8')
            lines = [line for line in existing.splitlines() if line.strip()]
            lines = lines[-19:]
            lines.append(entry)
            self.storage.save_bytes(ledger_rel, ('\n'.join(lines) + '\n').encode('utf-8'))
        except Exception:
            pass

    def _load_metacognitive_ledger(self) -> list[dict[str, Any]]:
        """Load the metacognitive error ledger for persistent bias detection."""
        ledger_rel = 'self_examination/metacognitive_ledger.jsonl'
        entries: list[dict[str, Any]] = []
        try:
            if not self.storage.exists(ledger_rel):
                return entries
            raw = self.storage.load_bytes(ledger_rel).decode('utf-8')
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    continue
        except Exception:
            pass
        return entries

    # ------------------------------------------------------------------
    # G2: Leer feedback de validación para filtrar propuestas ya intentadas
    # ------------------------------------------------------------------

    def _load_tried_proposal_keys(self) -> set[str]:
        """G2: Load proposal keys that have already been validated.

        Reads the JSONL file written by ``AutonomousValidationCycleService._persist_validation_feedback``
        and returns a set of synthetic keys for proposals that were
        ``discarded`` or ``unresolved`` — so ``_solution_proposals`` avoids
        re-proposing the same strategy.  Proposals that were ``promoted``
        are NOT filtered (they succeeded and may be proposed again for
        different contexts).
        """
        tried: set[str] = set()
        try:
            feedback_path = Path(self.workspace_root) / 'data' / 'evolution' / 'validation_feedback' / 'history.jsonl'
            if not feedback_path.is_file():
                return tried
            for line in feedback_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                decision = str(entry.get('decision') or '')
                if decision not in {'discarded', 'unresolved'}:
                    continue
                kind = str(entry.get('proposal_kind') or entry.get('proposal_key') or '').strip()
                candidate = str(entry.get('candidate_assistant_kind') or '').strip().lower()
                current = str(entry.get('current_assistant_kind') or '').strip().lower()
                if kind and candidate and current:
                    tried.add(f'route_substitution:{current}:{candidate}')
                if kind and candidate and current:
                    tried.add(f'collaborative_execution:{candidate}:{current}')
                    tried.add(f'collaborative_execution:{current}:{candidate}')
                    tried.add(f'validated_collaboration:{candidate}:{current}')
                    tried.add(f'validated_collaboration:{current}:{candidate}')
        except Exception:
            pass
        return tried

    # ------------------------------------------------------------------
    # P3: Propuestas proactivas de solución
    # ------------------------------------------------------------------

    def _solution_proposals(
        self,
        *,
        findings: list[SelfExaminationFinding],
        recommendations: list[ExperimentRecommendation],
        experiment_runs: list[ExperimentRun],
        validated_improvements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate actionable solution proposals from findings and evidence.

        When self-examination detects recurring patterns (failures, blocks,
        inertia), this method converts them into concrete proposals that
        specify which IAs should handle which aspects and with what
        estimated confidence.  Proposals are purely descriptive — the
        orchestrator or UI decides whether to act on them.

        G2: reads validation feedback to filter out proposals already tried.
        G3: uses ``AdaptiveWeightLayer.suggest()`` for weighted profiles
        when available, instead of computing crude averages.
        """
        proposals: list[dict[str, Any]] = []

        # G2: load validation feedback to skip already-tried proposals
        tried_keys = self._load_tried_proposal_keys()

        # G3: use AdaptiveWeightLayer for weighted profiles when available
        kind_success: dict[str, list[float]] = defaultdict(list)
        kind_failures: dict[str, int] = defaultdict(int)
        kind_weighted_scores: dict[str, float] = {}

        if self.adaptive_weight_layer is not None and experiment_runs:
            grouped: dict[tuple[object, str, str], list[ExperimentRun]] = defaultdict(list)
            for run in experiment_runs:
                kind = str(run.assistant_kind or '').strip().lower()
                if not kind:
                    continue
                key = (run.route, kind, str(run.config_signature or ''))
                grouped[key].append(run)
                if bool(run.success):
                    kind_success[kind].append(float(run.metrics.total_score or 0.0))
                else:
                    kind_failures[kind] += 1
            profiles = self.adaptive_weight_layer.suggest(grouped_runs=grouped)
            for key, profile in profiles.items():
                kind = str(key[1]).strip().lower()
                if kind and kind not in kind_weighted_scores:
                    kind_weighted_scores[kind] = float(profile.get('weighted_score') or 0.0)
        else:
            for run in experiment_runs:
                kind = str(run.assistant_kind or '').strip().lower()
                if not kind:
                    continue
                if bool(run.success):
                    kind_success[kind].append(float(run.metrics.total_score or 0.0))
                else:
                    kind_failures[kind] += 1

        def _kind_score(kind: str) -> float:
            """G3: prefer weighted score from AdaptiveWeightLayer."""
            if kind in kind_weighted_scores:
                return kind_weighted_scores[kind]
            scores = kind_success.get(kind, [])
            return sum(scores) / max(len(scores), 1) if scores else 0.0

        recurring_failure_kinds: set[str] = set()
        for finding in findings:
            if finding.severity in {IssueSeverity.HIGH, IssueSeverity.MEDIUM}:
                metadata = dict(finding.metadata or {})
                kind = str(metadata.get('assistant_kind') or '').strip().lower()
                if kind and kind_failures.get(kind, 0) >= 2:
                    recurring_failure_kinds.add(kind)

        for failing_kind in recurring_failure_kinds:
            fail_count = kind_failures.get(failing_kind, 0)
            alternatives = sorted(
                (
                    (k, _kind_score(k), len(scores))
                    for k, scores in kind_success.items()
                    if k != failing_kind and len(scores) >= 2
                ),
                key=lambda t: (t[1], t[2]),
                reverse=True,
            )
            if not alternatives:
                continue
            best_alt, best_score, best_count = alternatives[0]
            proposal_key = f'route_substitution:{failing_kind}:{best_alt}'
            # G2: skip proposals already tried and discarded
            if proposal_key in tried_keys:
                continue
            proposals.append({
                'type': 'route_substitution',
                'proposal_key': proposal_key,
                'title': f'Sustituir {failing_kind} por {best_alt} en tareas con fallos recurrentes',
                'description': (
                    f'{failing_kind} tiene {fail_count} fallos recientes. '
                    f'{best_alt} tiene score {"ponderado" if best_alt in kind_weighted_scores else "promedio"} {best_score:.2f} con {best_count} éxitos.'
                ),
                'action_plan': [
                    {'step': 1, 'ia': best_alt, 'action': 'Asumir tareas que fallaban con ' + failing_kind},
                    {'step': 2, 'ia': failing_kind, 'action': 'Reducir prioridad hasta evidencia de mejora'},
                ],
                'estimated_confidence': round(min(1.0, 0.5 + best_score * 0.3), 4),
                'evidence_refs': [f'failures:{failing_kind}:{fail_count}', f'success:{best_alt}:{best_count}'],
            })

        if len(kind_success) >= 2:
            sorted_kinds = sorted(
                ((k, _kind_score(k), len(v)) for k, v in kind_success.items() if len(v) >= 2),
                key=lambda t: (t[1], t[2]),
                reverse=True,
            )
            if len(sorted_kinds) >= 2:
                primary_kind, primary_score, primary_runs = sorted_kinds[0]
                secondary_kind, secondary_score, secondary_runs = sorted_kinds[1]
                collab_key = f'collaborative_execution:{primary_kind}:{secondary_kind}'
                if primary_score > 0.3 and secondary_score > 0.3 and collab_key not in tried_keys:
                    proposals.append({
                        'type': 'collaborative_execution',
                        'proposal_key': collab_key,
                        'title': f'Plan coordinado: {primary_kind} + {secondary_kind}',
                        'description': (
                            f'{primary_kind} (score {"ponderado" if primary_kind in kind_weighted_scores else "promedio"} {primary_score:.2f}, {primary_runs} éxitos) '
                            f'y {secondary_kind} (score {"ponderado" if secondary_kind in kind_weighted_scores else "promedio"} {secondary_score:.2f}, {secondary_runs} éxitos) '
                            f'pueden trabajar en conjunto: uno investiga, el otro implementa.'
                        ),
                        'action_plan': [
                            {'step': 1, 'ia': primary_kind, 'action': 'Investigar y proponer solución'},
                            {'step': 2, 'ia': secondary_kind, 'action': 'Validar y complementar propuesta'},
                            {'step': 3, 'ia': 'orchestrator', 'action': 'Consolidar y ejecutar plan final'},
                        ],
                        'estimated_confidence': round(
                            min(1.0, 0.4 + primary_score * 0.2 + secondary_score * 0.2 + min(primary_runs, secondary_runs) * 0.02),
                            4,
                        ),
                        'evidence_refs': [f'success:{primary_kind}:{primary_runs}', f'success:{secondary_kind}:{secondary_runs}'],
                    })

        for improvement in validated_improvements[:2]:
            rec_kind = str(improvement.get('recommended_assistant_kind') or '').strip().lower()
            rec_confidence = float(improvement.get('confidence') or 0.0)
            if rec_kind and rec_confidence >= 0.75:
                complementary = [
                    k for k, scores in kind_success.items()
                    if k != rec_kind and len(scores) >= 2 and _kind_score(k) > 0.4
                ]
                if complementary:
                    vc_key = f'validated_collaboration:{rec_kind}:{complementary[0]}'
                    if vc_key not in tried_keys:
                        proposals.append({
                            'type': 'validated_collaboration',
                            'proposal_key': vc_key,
                            'title': f'Extender éxito validado de {rec_kind} con {complementary[0]}',
                            'description': (
                                f'{rec_kind} fue validado con confianza {rec_confidence:.2f}. '
                                f'Combinar con {complementary[0]} para cubrir aspectos complementarios.'
                            ),
                            'action_plan': [
                                {'step': 1, 'ia': rec_kind, 'action': str(improvement.get('summary') or 'Aplicar mejora validada')},
                                {'step': 2, 'ia': complementary[0], 'action': 'Complementar con fortalezas propias'},
                            ],
                            'estimated_confidence': round(min(1.0, rec_confidence * 0.8 + 0.15), 4),
                            'evidence_refs': list(improvement.get('evidence_refs') or [])[:4],
                        })

        return proposals[:4]

    def _unresolved_risks(
        self,
        *,
        findings: list[SelfExaminationFinding],
        world: WorldModelSnapshot,
        validation: AutonomousValidationSnapshot,
        experiment_runs: list[ExperimentRun],
        adaptive_sessions: list[Any],
    ) -> list[str]:
        unresolved = list(dict.fromkeys([*list(world.unresolved_fields or []), *list(validation.unresolved_fields or [])]))
        unresolved.extend(
            finding.unresolved_fields[0]
            for finding in findings
            if finding.unresolved_fields
        )
        if not experiment_runs:
            unresolved.append('UNRESOLVED:experiment_history')
        if not adaptive_sessions:
            unresolved.append('UNRESOLVED:adaptive_sessions')
        return list(dict.fromkeys(item for item in unresolved if str(item).strip()))[:8]

    def _status(
        self,
        *,
        findings: list[SelfExaminationFinding],
        unresolved_risks: list[str],
    ) -> str:
        if any(finding.severity == IssueSeverity.HIGH for finding in findings):
            return 'needs_attention'
        if findings:
            return 'watch'
        if unresolved_risks:
            return 'partial'
        return 'stable'

    def _summary(
        self,
        *,
        status: str,
        findings: list[SelfExaminationFinding],
        validated_improvements: list[dict[str, Any]],
        recurring_issues: list[dict[str, Any]],
        feedback_summary: dict[str, Any],
    ) -> str:
        if findings:
            top = findings[0]
            response = (
                f'Autoexaminacion {status}: {len(findings)} hallazgos activos. '
                f'Lo mas fuerte ahora es {top.title.lower()}. '
                f'Mejoras validadas: {len(validated_improvements)} | issues recurrentes: {len(recurring_issues)}.'
            )
            if int(feedback_summary.get('false_improvement') or 0) > 0:
                response += f" La retroalimentacion marca {int(feedback_summary.get('false_improvement') or 0)} ajuste(s) previos que no conviene repetir igual."
            return response
        if validated_improvements:
            response = (
                f'Autoexaminacion {status}: no veo degradaciones fuertes. '
                f'Si hay {len(validated_improvements)} mejoras ya respaldadas por evidencia reciente.'
            )
            if int(feedback_summary.get('valid_adjustment') or 0) > 0 or int(feedback_summary.get('validated_improvement') or 0) > 0:
                response += (
                    f" La retroalimentacion confirma {int(feedback_summary.get('validated_improvement') or 0)} mejora(s) validadas"
                    f" y {int(feedback_summary.get('valid_adjustment') or 0)} ajuste(s) utiles."
                )
            return response
        if int(feedback_summary.get('total_reviewed') or 0) > 0:
            return (
                f'Autoexaminacion {status}: revise {int(feedback_summary.get("total_reviewed") or 0)} ajuste(s) previos. '
                f'Validados: {int(feedback_summary.get("validated_improvement") or 0)} | '
                f'utiles: {int(feedback_summary.get("valid_adjustment") or 0)} | '
                f'falsas mejoras: {int(feedback_summary.get("false_improvement") or 0)} | '
                f'sin evidencia: {int(feedback_summary.get("no_evidence") or 0)}.'
            )
        return 'Autoexaminacion partial: todavia no tengo suficiente evidencia acumulada para emitir una revision fuerte.'

    @staticmethod
    def _extract_metrics_tag(finding: SelfExaminationFinding) -> str:
        """Build a compact metrics suffix from finding metadata.

        When a finding has concrete numeric data (observed_ms, threshold_ms,
        observed_count, etc.) this returns a tag like
        ``  [observed: 274ms, umbral: 5000ms]`` so the assistant_brief and
        UI responses include the actual numbers instead of just the title.
        """
        meta = dict(finding.metadata or {})
        parts: list[str] = []
        observed_ms = meta.get('observed_ms')
        if observed_ms is not None:
            parts.append(f'observado: {observed_ms}ms')
        threshold_ms = meta.get('threshold_ms')
        if threshold_ms is not None:
            parts.append(f'umbral: {threshold_ms}ms')
        starvation_s = meta.get('starvation_seconds')
        if starvation_s is not None:
            parts.append(f'bloqueo: {starvation_s}s')
        wall_clock_ms = meta.get('wall_clock_ms')
        if wall_clock_ms is not None and observed_ms is None:
            parts.append(f'wall_clock: {wall_clock_ms}ms')
        total_fp = meta.get('total_false_positives')
        total_fn = meta.get('total_false_negatives')
        if total_fp is not None and total_fn is not None:
            parts.append(f'FP: {total_fp}, FN: {total_fn}')
        if not parts:
            return ''
        return f'  [{", ".join(parts)}]'

    def _render_assistant_brief(self, review: SelfExaminationSnapshot) -> str:
        lines = [
            '# IABV v1.5 - Operational Self Examination',
            '',
            f'Generado: {review.updated_at_utc.isoformat()}',
            f'Resumen: {review.summary}',
            '',
            'Usa esta revision para entender que esta fallando, que se repite y que ajustes conviene hacer antes de tocar la arquitectura.',
            '',
            '## Hallazgos',
        ]
        if review.findings:
            for finding in review.findings[:6]:
                metrics_tag = self._extract_metrics_tag(finding)
                lines.append(
                    f"- {finding.title}: {finding.summary}{metrics_tag} | recomendacion: {finding.recommendation or 'sin ajuste concreto'} | confianza {finding.confidence:.2f}"
                )
        else:
            lines.append('- Sin hallazgos fuertes confirmados.')
        lines.extend(['', '## Ajustes recomendados'])
        if review.recommended_adjustments:
            for item in review.recommended_adjustments[:6]:
                lines.append(
                    f"- {str(item.get('title') or 'Ajuste')}: {str(item.get('recommended_change') or 'sin cambio sugerido')} | fuente {', '.join(item.get('source_refs') or []) or 'n/d'}"
                )
        else:
            lines.append('- Sin ajustes respaldados por evidencia suficiente.')
        lines.extend(['', '## Mejoras validadas'])
        if review.validated_improvements:
            for item in review.validated_improvements[:4]:
                lines.append(
                    f"- {str(item.get('title') or 'Mejora')}: {str(item.get('summary') or 'sin resumen')} | confianza {float(item.get('confidence') or 0.0):.2f}"
                )
        else:
            lines.append('- Sin mejoras validadas fuertes todavia.')
        feedback = list(dict(review.metadata or {}).get('recommendation_feedback') or [])
        lines.extend(['', '## Retroalimentacion de ajustes'])
        if feedback:
            for item in feedback[:4]:
                lines.append(
                    f"- {str(item.get('title') or 'Ajuste previo')}: {str(item.get('status') or 'sin estado')} | {str(item.get('summary') or 'sin resumen')} | siguiente paso: {str(item.get('next_step') or 'seguir observando')}"
                )
        else:
            lines.append('- Todavia no hay suficiente evidencia posterior para juzgar ajustes anteriores.')
        if review.unresolved_risks:
            lines.extend(['', f"UNRESOLVED: {', '.join(review.unresolved_risks)}"])
        return '\n'.join(lines).strip()

    def _adjustment_feedback_key(self, *, category: str, title: str, metadata: dict[str, Any]) -> str:
        category_value = str(category or 'unknown').strip().lower()
        if category_value == 'inertial_route':
            assistant = str(metadata.get('assistant_kind') or '').strip().lower()
            route = str(metadata.get('route') or '').strip().lower()
            config = str(metadata.get('config_signature') or '').strip().lower()
            return f'{category_value}:{assistant}:{route}:{config}'
        if category_value == 'repeated_block':
            block = str(metadata.get('block') or title).strip().lower()
            return f'{category_value}:{block}'
        if category_value == 'recurring_failure':
            scope = str(metadata.get('scope') or title).strip().lower()
            return f'{category_value}:{scope}'
        if category_value == 'repeated_stall':
            pack_id = str(metadata.get('pack_id') or title).strip().lower()
            return f'{category_value}:{pack_id}'
        if category_value == 'weak_correction':
            scenario_id = str(metadata.get('scenario_id') or title).strip().lower()
            return f'{category_value}:{scenario_id}'
        if category_value == 'token_rotation':
            # ``title`` incluye dias proyectados (``(3.0d)``) que cambian en
            # cada review. ``token_name`` es estable y esta en metadata de
            # expired/proactive/stale por igual.
            token_name = str(metadata.get('token_name') or title).strip().lower()
            return f'{category_value}:{token_name}'
        return f'{category_value}:{str(title or "").strip().lower()}'

    def _matching_runs_for_adjustment(
        self,
        *,
        adjustment: dict[str, Any],
        experiment_runs: list[ExperimentRun],
    ) -> list[ExperimentRun]:
        category = str(adjustment.get('category') or '').strip().lower()
        metadata = dict(adjustment.get('metadata') or {})
        if category == 'inertial_route':
            route = str(metadata.get('route') or '').strip().lower()
            assistant = str(metadata.get('assistant_kind') or '').strip().lower()
            config = str(metadata.get('config_signature') or '').strip()
            return [
                run
                for run in experiment_runs
                if str(run.assistant_kind or '').strip().lower() == assistant
                and str(getattr(run.route, 'value', run.route) or '').strip().lower() == route
                and str(run.config_signature or '').strip() == config
            ]
        if category == 'repeated_block':
            block = str(metadata.get('block') or '').strip().lower()
            if not block:
                return []
            return [
                run
                for run in experiment_runs
                if any(block == str(item).strip().lower() for item in (dict(run.metadata or {}).get('external_state_flags') or []))
            ]
        if category == 'recurring_failure':
            scope = str(metadata.get('scope') or '').strip().lower()
            if not scope:
                return []
            return [run for run in experiment_runs if self._experiment_task_scope(run).lower() == scope]
        return []

    def _feedback_profile(self, runs: list[ExperimentRun]) -> dict[str, Any]:
        if not runs:
            return {
                'sample_count': 0,
                'success_rate': 0.0,
                'blocked_rate': 0.0,
                'fallback_rate': 0.0,
                'trend_score': 0.0,
            }
        if self.adaptive_weight_layer is not None and hasattr(self.adaptive_weight_layer, '_profile'):
            return dict(self.adaptive_weight_layer._profile(runs))
        sample_count = len(runs)
        success_rate = sum(1 for run in runs if run.success) / max(sample_count, 1)
        blocked_rate = sum(1 for run in runs if bool(dict(run.metadata or {}).get('blocked'))) / max(sample_count, 1)
        fallback_rate = sum(1 for run in runs if bool(dict(run.metadata or {}).get('fallback_used') or dict(run.metadata or {}).get('used_fallback'))) / max(sample_count, 1)
        return {
            'sample_count': sample_count,
            'success_rate': round(success_rate, 4),
            'blocked_rate': round(blocked_rate, 4),
            'fallback_rate': round(fallback_rate, 4),
            'trend_score': 0.0,
        }

    def _adjustment_has_validated_evidence(
        self,
        *,
        adjustment: dict[str, Any],
        validated_improvements: list[dict[str, Any]],
        validation: AutonomousValidationSnapshot,
    ) -> bool:
        category = str(adjustment.get('category') or '').strip().lower()
        metadata = dict(adjustment.get('metadata') or {})
        if category == 'inertial_route':
            target_key = self._adjustment_feedback_key(
                category='inertial_route',
                title=str(adjustment.get('title') or ''),
                metadata=metadata,
            )
            for item in validated_improvements:
                item_key = str(item.get('feedback_key') or '')
                if item_key and item_key == target_key:
                    return True
        assistant = str(metadata.get('assistant_kind') or '').strip().lower()
        route = str(metadata.get('route') or '').strip().lower()
        subject_key = str(metadata.get('subject_key') or '').strip().lower()
        text = ' '.join(
            str(part).strip().lower()
            for part in (
                validation.summary,
                *[item.get('title') for item in validated_improvements],
                *[item.get('summary') for item in validated_improvements],
            )
            if str(part or '').strip()
        )
        token_match = False
        if assistant and assistant in text:
            token_match = True
        if route and route in text:
            token_match = True
        if subject_key and subject_key in text:
            token_match = True
        return token_match and (
            int(validation.promoted_count or 0) > 0
            or any(float(item.get('confidence') or 0.0) >= 0.8 for item in validated_improvements)
        )

    def _experiment_task_scope(self, run: ExperimentRun) -> str:
        metadata = dict(run.metadata or {})
        subject_key = str(run.subject_key or '').strip()
        route = str(getattr(run.route, 'value', run.route) or '').strip()
        assistant = str(run.assistant_kind or '').strip().lower()
        if subject_key:
            return subject_key
        if assistant:
            return f'{assistant}:{route}'
        return route or 'general'

    def _task_scope(self, run: RunRecord) -> str:
        request = run.request
        route = run.route
        site = str(getattr(request, 'site_hint', '') or '').strip() or 'general'
        role = str(getattr(getattr(route, 'task_role', None), 'value', getattr(route, 'task_role', '')) or '').strip()
        if not role:
            role = str(getattr(getattr(run.result, 'detected_role', None), 'value', getattr(run.result, 'detected_role', '')) or '').strip()
        if not role:
            role = str(getattr(getattr(request, 'task_role', None), 'value', getattr(request, 'task_role', '')) or 'general')
        return f'{site}:{role}'

    def _severity_rank(self, severity: IssueSeverity | str) -> int:
        value = str(getattr(severity, 'value', severity) or '').strip().lower()
        order = {
            IssueSeverity.LOW.value: 1,
            IssueSeverity.MEDIUM.value: 2,
            IssueSeverity.HIGH.value: 3,
            IssueSeverity.CRITICAL.value: 4,
        }
        return order.get(value, 0)

    # ──────────────────────────────────────────────────────────
    # Chat Observability: detect anomalies in persisted chat messages
    # ──────────────────────────────────────────────────────────

    def _chat_observability_findings(self) -> list[SelfExaminationFinding]:
        """Detect chat persistence anomalies from ChatMessageRepository.

        Produces findings when:
        - No messages have been persisted (persistence may be disconnected)
        - A reasoning_path dominates >80% of messages (possible route fixation)
        - Too many messages lack evidence_tag (evidence gap)
        - Retention policy has not been applied recently for large histories
        """
        from iabv_v15.domain.models import SelfExaminationFinding, IssueSeverity
        repo = self.chat_message_repository
        if repo is None:
            return []
        try:
            total = repo.count()
        except Exception:
            return []
        if total == 0:
            return []
        findings: list[SelfExaminationFinding] = []
        try:
            recent = repo.list_recent(limit=200)
        except Exception:
            return []
        if not recent:
            return findings
        path_counts: dict[str, int] = {}
        no_evidence = 0
        for msg in recent:
            path = msg.get('reasoning_path', '') or ''
            if path:
                path_counts[path] = path_counts.get(path, 0) + 1
            tag = msg.get('evidence_tag', '') or ''
            if not tag:
                no_evidence += 1
        sample_size = len(recent)
        for path, count in path_counts.items():
            ratio = count / sample_size
            if ratio > 0.80 and sample_size >= 10:
                findings.append(SelfExaminationFinding(
                    category='chat_observability',
                    title=f'Fijacion de ruta chat: {path} ({ratio:.0%})',
                    summary=(
                        f'La ruta "{path}" domina {count}/{sample_size} mensajes recientes. '
                        f'Puede indicar que el sistema no explora otras rutas.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.7,
                    recommendation=(
                        'Revisar si el usuario solo hace un tipo de pregunta o si el '
                        'routing esta sesgado hacia esta ruta.'
                    ),
                    metadata={'path': path, 'ratio': ratio, 'count': count},
                ))
        evidence_gap_ratio = no_evidence / sample_size if sample_size else 0.0
        if evidence_gap_ratio > 0.5 and sample_size >= 10:
            findings.append(SelfExaminationFinding(
                category='chat_observability',
                title=f'Brecha de evidencia en chat: {no_evidence}/{sample_size} sin tag',
                summary=(
                    f'{no_evidence} de {sample_size} mensajes recientes no tienen evidence_tag. '
                    f'Esto dificulta distinguir respuestas observadas de inferidas.'
                ),
                severity=IssueSeverity.LOW,
                confidence=0.6,
                recommendation='Verificar que _append_message pasa evidence_tag en todas las rutas.',
                metadata={'no_evidence': no_evidence, 'ratio': evidence_gap_ratio},
            ))
        if total > 1200:
            sessions = repo.list_sessions()
            old_sessions = [s for s in sessions if s.get('count', 0) > 0]
            if len(old_sessions) > 20:
                findings.append(SelfExaminationFinding(
                    category='chat_observability',
                    title=f'Historial de chat grande: {total} mensajes en {len(old_sessions)} sesiones',
                    summary=(
                        f'El historial de chat tiene {total} mensajes. '
                        f'Considerar aplicar retention policy para compactar sesiones antiguas.'
                    ),
                    severity=IssueSeverity.LOW,
                    confidence=0.8,
                    recommendation='Ejecutar ChatMessageRepository.apply_retention() periodicamente.',
                    metadata={'total': total, 'sessions': len(old_sessions)},
                ))
        return findings

    # UI Self-Awareness: detect own window anomalies
    # ──────────────────────────────────────────────────────────

    _IABV_TITLE_MARKERS = ('iabv', 'iabv v1.5', 'centro de control', 'centro vivo')
    _ZOMBIE_MARKERS = ('no responde', 'not responding')

    def _ui_self_examination_findings(
        self, *, world: WorldModelSnapshot,
    ) -> list[SelfExaminationFinding]:
        """Detect anomalies in IABV's own UI windows.

        Uses the WorldModel's active_windows to check:
        - Zombie IABV windows ("No responde")
        - Missing IABV window entirely
        - Duplicate IABV instances
        """
        findings: list[SelfExaminationFinding] = []
        if not world.active_windows:
            return findings

        iabv_windows: list[Any] = []
        zombie_windows: list[Any] = []

        for w in world.active_windows:
            title_lower = (w.title or '').lower()
            is_iabv = any(m in title_lower for m in self._IABV_TITLE_MARKERS)
            if not is_iabv:
                continue
            is_zombie = any(z in title_lower for z in self._ZOMBIE_MARKERS)
            if is_zombie:
                zombie_windows.append(w)
            else:
                iabv_windows.append(w)

        if zombie_windows:
            zombie_titles = [w.title for w in zombie_windows]
            findings.append(SelfExaminationFinding(
                category='ui_self_awareness',
                title='zombie_iabv_window',
                summary=(
                    f'{len(zombie_windows)} ventana(s) IABV en estado '
                    f'"No responde": {zombie_titles}. El event loop de la UI '
                    f'esta bloqueado o el proceso esta colgado.'
                ),
                severity=IssueSeverity.HIGH,
                confidence=0.95,
                recommendation=(
                    'Terminar el proceso zombie y reiniciar la UI. '
                    'Investigar que operacion bloqueo el hilo principal.'
                ),
                evidence_refs=[f'window:{t}' for t in zombie_titles],
                source_refs=['WorldModelSnapshot.active_windows'],
            ))

        if not iabv_windows and not zombie_windows and len(world.active_windows) > 0:
            # El MCP server arranca ANTES de la UI. Durante los primeros
            # ~60s de vida del servicio, es normal que la ventana IABV no
            # exista todavia. Tambien, si start_iabv.ps1 no uso -StartUI,
            # la UI no se lanzo y esta ausencia es esperada.
            uptime_s = time.time() - self._created_at
            is_early_startup = uptime_s < 60.0
            severity = IssueSeverity.MEDIUM if is_early_startup else IssueSeverity.HIGH
            confidence = 0.50 if is_early_startup else 0.80
            timing_note = (
                ' Nota: este hallazgo puede ser un falso positivo de '
                'timing — el MCP arranca antes de la UI y el primer '
                'scan de ventanas no la detecta. Deberia resolverse '
                'en el siguiente sync_pulse.'
            ) if is_early_startup else ''
            findings.append(SelfExaminationFinding(
                category='ui_self_awareness',
                title='iabv_window_missing',
                summary=(
                    'No se detecta ninguna ventana IABV entre las '
                    f'{len(world.active_windows)} ventanas activas. '
                    'La UI puede no haberse iniciado, el titulo no '
                    'coincide con los marcadores conocidos, o el scan '
                    'corrio antes de que la ventana fuera visible.'
                    + timing_note
                ),
                severity=severity,
                confidence=confidence,
                recommendation=(
                    'Verificar que el proceso UI (python -m iabv_v15 app) '
                    'esta corriendo y que la ventana es visible para Win32 '
                    '(MainWindowHandle != 0). Si el MCP acaba de arrancar, '
                    'esperar al siguiente sync_pulse para re-evaluar.'
                ),
                evidence_refs=[
                    f'total_windows:{len(world.active_windows)}',
                    f'early_startup:{is_early_startup}',
                ],
                source_refs=['WorldModelSnapshot.active_windows'],
            ))

        if len(iabv_windows) > 1:
            titles = [w.title for w in iabv_windows]
            findings.append(SelfExaminationFinding(
                category='ui_self_awareness',
                title='duplicate_iabv_windows',
                summary=(
                    f'{len(iabv_windows)} instancias IABV activas: {titles}. '
                    f'Solo deberia haber una instancia corriendo.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Cerrar las instancias duplicadas. Verificar que '
                    'start_iabv.ps1 no lance multiples procesos.'
                ),
                evidence_refs=[f'window:{t}' for t in titles],
                source_refs=['WorldModelSnapshot.active_windows'],
            ))

        return findings

    # ──────────────────────────────────────────────────────────
    # CodeAuditTrail cross-referencing
    # ──────────────────────────────────────────────────────────

    def _code_audit_cross_reference_findings(self) -> list[SelfExaminationFinding]:
        """Cross-reference external audit findings with internal observations.

        Detects:
        - Recurring bug patterns across audit rounds (same pattern_tag)
        - Findings that need cross-verification on this environment
        - Modules audited externally that OSES also flagged
        """
        trail = getattr(self, 'code_audit_trail', None)
        if trail is None:
            return []
        findings: list[SelfExaminationFinding] = []
        try:
            patterns = trail.analyze_bug_patterns()
            for pattern in patterns[:3]:
                if pattern.get('occurrences', 0) >= 2 and not pattern.get('all_fixed'):
                    findings.append(SelfExaminationFinding(
                        category='code_audit_recurring_pattern',
                        title=f"Patron recurrente en auditorias: {pattern.get('pattern_tag', '')}",
                        summary=(
                            f"Detectado {pattern.get('occurrences', 0)} veces en "
                            f"{len(pattern.get('affected_modules', []))} modulos. "
                            f"{pattern.get('description', '')[:200]}"
                        ),
                        severity=IssueSeverity.HIGH,
                        confidence=0.85,
                        recommendation=(
                            'Buscar este patron en modulos no auditados aun. '
                            'Considerar agregar validacion automatica en tests.'
                        ),
                        source_refs=['CodeAuditTrail', 'analyze_bug_patterns'],
                    ))

            cross_verifications = trail.pending_cross_verifications()
            windows_pending = [
                f for f in cross_verifications
                if f.get('needs_windows_verification')
            ]
            if windows_pending:
                titles = [f.get('title', '') for f in windows_pending[:3]]
                findings.append(SelfExaminationFinding(
                    category='code_audit_cross_verification',
                    title=f'{len(windows_pending)} hallazgo(s) necesitan verificacion en Windows',
                    summary=(
                        'Auditorias externas (Linux) encontraron hallazgos que '
                        'requieren verificacion en el entorno real Windows: '
                        + '; '.join(t for t in titles if t)
                    ),
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.75,
                    recommendation=(
                        'Ejecutar tests focalizados en Windows para verificar '
                        'estos hallazgos en el entorno de produccion real.'
                    ),
                    source_refs=['CodeAuditTrail', 'pending_cross_verifications'],
                ))
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning('oses: code_audit_cross_reference error: %s', exc)
        return findings

    # ──────────────────────────────────────────────────────────
    # RuntimePerformance: memory, threads, bottleneck detection
    # ──────────────────────────────────────────────────────────

    def _runtime_performance_findings(self) -> list[SelfExaminationFinding]:
        """Detect runtime performance bottlenecks: memory, threads, network.

        This is IABV observing its own resource consumption and flagging
        conditions that cause the UI to feel slow or frozen. Unlike external
        monitoring, this is self-awareness: the system notices its own
        degradation and recommends corrective action.

        Checks:
        - Process RSS memory > threshold → recommend lazy loading
        - Excessive active threads → recommend consolidation
        - Polling threads competing for GIL → recommend longer intervals
        - Network probe failures cached → report connectivity status
        - Child subprocess count → flag orphan processes
        """
        import threading as _threading

        findings: list[SelfExaminationFinding] = []

        # --- Memory pressure ---
        rss_mb = self._read_process_rss_mb()
        if rss_mb is not None and rss_mb > 500:
            severity = IssueSeverity.HIGH if rss_mb > 800 else IssueSeverity.MEDIUM
            findings.append(SelfExaminationFinding(
                category='runtime_performance',
                title='high_memory_usage',
                summary=(
                    f'El proceso IABV consume {rss_mb:.0f}MB de RAM. '
                    f'Esto puede causar lentitud en la UI y en respuestas MCP. '
                    f'Considerar lazy loading de servicios no criticos.'
                ),
                severity=severity,
                confidence=0.95,
                recommendation=(
                    'Implementar lazy loading: instanciar EmbeddingIndexService, '
                    'SiteExplorationService, BrowserSessionController y servicios '
                    'similares solo cuando se usen por primera vez, no en __init__. '
                    'Usar @property con cache en AppBootstrap.'
                ),
                evidence_refs=[f'rss_mb:{rss_mb:.0f}'],
                source_refs=['runtime_performance_monitor'],
            ))

        # --- Thread count ---
        threads = _threading.enumerate()
        thread_count = len(threads)
        polling_keywords = (
            'scan', 'poll', 'monitor', 'timer', 'refresh',
            'world_model', 'health', 'bridge', 'bg-install',
        )
        polling_threads = [
            t for t in threads
            if any(kw in t.name.lower() for kw in polling_keywords)
        ]

        if thread_count > 20:
            findings.append(SelfExaminationFinding(
                category='runtime_performance',
                title='excessive_threads',
                summary=(
                    f'{thread_count} hilos activos en el proceso. '
                    f'Python GIL causa contention entre hilos — cada hilo '
                    f'adicional degrada latencia de respuesta.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation=(
                    'Consolidar hilos de polling: WorldModelService, '
                    'EnvironmentSelfAwareness y HealthRouter podrian compartir '
                    'un unico hilo con diferentes intervalos. Usar asyncio '
                    'en vez de threads donde sea posible.'
                ),
                evidence_refs=[
                    f'total_threads:{thread_count}',
                    f'polling_threads:{len(polling_threads)}',
                ],
                source_refs=['runtime_performance_monitor'],
            ))

        if len(polling_threads) > 4:
            names = [t.name for t in polling_threads[:8]]
            findings.append(SelfExaminationFinding(
                category='runtime_performance',
                title='excessive_polling_threads',
                summary=(
                    f'{len(polling_threads)} hilos de polling activos: {names}. '
                    f'Cada uno ejecuta scans periodicos que compiten por CPU y GIL.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.90,
                recommendation=(
                    'Reducir frecuencia de scan: WorldModelService._DEFAULT_SCAN_INTERVAL '
                    'de 18s a 45s para uso normal. Usar scan_interval_seconds=120 '
                    'cuando la presion de recursos es alta.'
                ),
                evidence_refs=[f'polling:{n}' for n in names],
                source_refs=['runtime_performance_monitor'],
            ))

        # --- Network probe health ---
        wms = self.world_model_service
        if wms is not None:
            cache = getattr(wms, '_network_cache', (None, '', 0.0))
            cached_latency, cached_error, _ = cache
            if cached_latency is None and cached_error:
                findings.append(SelfExaminationFinding(
                    category='runtime_performance',
                    title='network_probe_failing',
                    summary=(
                        f'El probe de conectividad falla: {cached_error[:100]}. '
                        f'Esto bloquea al WorldModel scan por hasta 7s cada ciclo '
                        f'y causa que IABV reporte "sin internet" incorrectamente.'
                    ),
                    severity=IssueSeverity.HIGH,
                    confidence=0.90,
                    recommendation=(
                        'Verificar firewall: port 53 TCP puede estar bloqueado. '
                        'El probe ya tiene fallback a port 443 y HTTP HEAD. '
                        'Si todos fallan, verificar proxy/VPN. Considerar aumentar '
                        'NETWORK_CACHE_TTL a 120s para reducir impacto.'
                    ),
                    evidence_refs=[f'error:{cached_error[:80]}'],
                    source_refs=['WorldModelService._network_connectivity_probe'],
                ))

        # --- Model/provider degradation (from AdaptiveModelSelector) ---
        ams = getattr(self, 'adaptive_model_selector', None)
        if ams is not None:
            try:
                degradations = ams.detect_degradation()
                for d in degradations:
                    dtype = d.get('type', '')
                    pid = d.get('provider_id', '')
                    if dtype == 'very_slow':
                        findings.append(SelfExaminationFinding(
                            category='runtime_performance',
                            title='model_too_slow',
                            summary=(
                                f'El proveedor {pid} promedia '
                                f'{d.get("avg_latency_ms", 0):.0f}ms de latencia. '
                                f'Esto degrada la experiencia del usuario.'
                            ),
                            severity=IssueSeverity.MEDIUM,
                            confidence=0.85,
                            recommendation=d.get('recommendation', ''),
                            evidence_refs=[f'avg_latency_ms:{d.get("avg_latency_ms", 0):.0f}'],
                            source_refs=['AdaptiveModelSelector'],
                        ))
                    elif dtype == 'high_failure_rate':
                        findings.append(SelfExaminationFinding(
                            category='runtime_performance',
                            title='provider_failing',
                            summary=(
                                f'El proveedor {pid} tiene solo '
                                f'{d.get("success_rate", 0):.0%} de exito. '
                                f'Rotando automaticamente al siguiente proveedor.'
                            ),
                            severity=IssueSeverity.HIGH,
                            confidence=0.90,
                            recommendation=d.get('recommendation', ''),
                            evidence_refs=[
                                f'success_rate:{d.get("success_rate", 0):.2f}',
                            ] + [f'error:{e[:60]}' for e in d.get('recent_errors', [])[:2]],
                            source_refs=['AdaptiveModelSelector'],
                        ))
                    elif dtype == 'quota_exhausted':
                        findings.append(SelfExaminationFinding(
                            category='runtime_performance',
                            title='provider_quota_exhausted',
                            summary=(
                                f'El proveedor {pid} agoto su cuota '
                                f'({d.get("count", 0)} errores 429). '
                                f'IABV roto automaticamente al siguiente '
                                f'proveedor disponible.'
                            ),
                            severity=IssueSeverity.HIGH,
                            confidence=0.95,
                            recommendation=d.get('recommendation', ''),
                            evidence_refs=[f'quota_errors:{d.get("count", 0)}'],
                            source_refs=['AdaptiveModelSelector'],
                        ))
            except Exception:
                pass

        return findings

    def _read_process_rss_mb(self) -> float | None:
        """Read current process RSS in MB. Cross-platform."""
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            pass
        try:
            with open('/proc/self/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) / 1024
        except Exception:
            pass
        # Windows fallback via PowerShell (WorldModelService already has this).
        try:
            import os
            import subprocess
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 f'(Get-Process -Id {os.getpid()}).WorkingSet64'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip()) / (1024 * 1024)
        except Exception:
            pass
        return None

    # ──────────────────────────────────────────────────────────
    # Fix 42-43: Functional gap analysis + underutilized resources
    # ──────────────────────────────────────────────────────────

    def _functional_gap_findings(self) -> list[SelfExaminationFinding]:
        """Detect functional gaps and underutilized resources.

        Unlike other findings that look at errors/failures, this method
        proactively analyzes what the system COULD be doing better:
        - Sessions in browsers without associated accounts (worker pool gap)
        - API keys available but not used by the intent classifier
        - Cloud models available but only local model being used
        - Training examples accumulating but not being applied
        """
        import os
        findings: list[SelfExaminationFinding] = []

        # Gap 1: Sessions without accounts (Opera/Brave/Firefox)
        try:
            from iabv_v15.services.account_resource_scanner import (
                scan_browser_accounts,
                scan_browser_sessions,
                verify_account_sessions,
            )
            accounts = scan_browser_accounts()
            sessions = scan_browser_sessions()
            verified = verify_account_sessions()

            session_browsers = {s.get('browser', '') for s in sessions.get('sessions', [])}
            account_browsers = {a.get('browser', '') for a in accounts.get('accounts', [])}
            orphan_browsers = session_browsers - account_browsers

            if orphan_browsers and sessions.get('session_count', 0) > 0:
                findings.append(SelfExaminationFinding(
                    category='functional_gap',
                    title='Sesiones activas en navegadores sin cuentas asociadas',
                    summary=(
                        f'Se detectaron sesiones activas en {", ".join(orphan_browsers)} '
                        f'pero no hay cuentas de Google asociadas en esos navegadores. '
                        f'El pool de asistentes usa workers anonimos para estas sesiones.'
                    ),
                    severity=IssueSeverity.LOW,
                    confidence=0.9,
                    recommendation=(
                        'Considerar asociar cuentas a los navegadores con sesiones '
                        'para mejor tracking de cuotas por cuenta.'
                    ),
                    evidence_refs=[
                        f'session_browsers={list(session_browsers)}',
                        f'account_browsers={list(account_browsers)}',
                    ],
                    metadata={
                        'gap_type': 'orphan_browser_sessions',
                        'orphan_browsers': list(orphan_browsers),
                    },
                ))

            # Gap 2: Workers with sessions but no quota tracking
            pool_accounts = verified.get('accounts', [])
            accounts_with_sessions = [
                a for a in pool_accounts if a.get('tool_count', 0) > 0
            ]
            if accounts_with_sessions:
                from iabv_v15.services.account_resource_scanner import get_all_quota_status
                quotas = get_all_quota_status()
                tracked_count = len(quotas.get('statuses', []))
                if tracked_count == 0 and len(accounts_with_sessions) > 0:
                    findings.append(SelfExaminationFinding(
                        category='functional_gap',
                        title='Asistentes con sesion activa sin rastreo de cuotas',
                        summary=(
                            f'{len(accounts_with_sessions)} asistentes tienen sesion activa '
                            f'pero ninguno tiene cuotas rastreadas. El rastreo se activa '
                            f'automaticamente al enviar mensajes.'
                        ),
                        severity=IssueSeverity.LOW,
                        confidence=0.85,
                        recommendation=(
                            'Iniciar uso de las herramientas (ChatGPT, Claude, Codex) '
                            'para que el rastreo de cuotas comience automaticamente.'
                        ),
                        metadata={
                            'gap_type': 'untracked_quotas',
                            'accounts_with_sessions': len(accounts_with_sessions),
                        },
                    ))
        except Exception:
            pass

        # Gap 3: Cloud API keys available but not used by intent classifier
        try:
            has_openai = bool(os.environ.get('OPENAI_API_KEY'))
            has_anthropic = bool(os.environ.get('ANTHROPIC_API_KEY'))
            from iabv_v15.services.account_resource_scanner import _load_training_examples
            training_count = len(_load_training_examples())

            if (has_openai or has_anthropic) and training_count == 0:
                cloud_name = 'OpenAI' if has_openai else 'Anthropic'
                findings.append(SelfExaminationFinding(
                    category='underutilized_resource',
                    title=f'API key de {cloud_name} disponible sin ejemplos de entrenamiento',
                    summary=(
                        f'Hay una API key de {cloud_name} configurada pero el '
                        f'clasificador dual aun no ha generado ejemplos de entrenamiento. '
                        f'El modelo local se beneficiaria de clasificaciones del modelo '
                        f'de la nube para mejorar su precision.'
                    ),
                    severity=IssueSeverity.LOW,
                    confidence=0.8,
                    recommendation=(
                        'El clasificador dual se activara automaticamente la proxima vez '
                        'que una pregunta ambigua pase por el chat. Los ejemplos de '
                        'entrenamiento se acumularan en data/evolution/intent_training.jsonl.'
                    ),
                    metadata={
                        'gap_type': 'unused_cloud_api',
                        'cloud_provider': cloud_name,
                        'training_examples': training_count,
                    },
                ))

            if training_count > 0:
                findings.append(SelfExaminationFinding(
                    category='learning_progress',
                    title=f'Clasificador dual: {training_count} ejemplos de entrenamiento acumulados',
                    summary=(
                        f'El modelo local ha aprendido de {training_count} clasificaciones '
                        f'del modelo de la nube. Estos ejemplos se inyectan como few-shot '
                        f'al prompt del modelo local para mejorar su precision.'
                    ),
                    severity=IssueSeverity.LOW,
                    confidence=0.95,
                    recommendation='Continuar usando el chat normalmente para acumular mas ejemplos.',
                    metadata={
                        'gap_type': 'training_progress',
                        'training_examples': training_count,
                    },
                ))
        except Exception:
            pass

        # Gap 4: Ollama available but not being leveraged for all classifiers
        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                resp = client.get('http://127.0.0.1:11434/api/tags')
                if resp.status_code == 200:
                    models = resp.json().get('models', [])
                    model_names = [m.get('name', '') for m in models]
                    if len(models) > 1:
                        findings.append(SelfExaminationFinding(
                            category='underutilized_resource',
                            title=f'{len(models)} modelos Ollama disponibles',
                            summary=(
                                f'Modelos instalados: {", ".join(model_names[:5])}. '
                                f'El clasificador usa solo el modelo por defecto. '
                                f'Modelos mas grandes podrian dar mejor precision local.'
                            ),
                            severity=IssueSeverity.LOW,
                            confidence=0.7,
                            recommendation=(
                                'Considerar ejecutar benchmarks con diferentes modelos '
                                'para determinar cual clasifica mejor los metadatos de IABV.'
                            ),
                            metadata={
                                'gap_type': 'multiple_local_models',
                                'models': model_names[:10],
                            },
                        ))
        except Exception:
            pass

        return findings

    def _account_resource_health_findings(self) -> list[SelfExaminationFinding]:
        """Detect account/quota/worker health issues for cross-session learning.

        Complements ``_functional_gap_findings`` (which detects orphan sessions
        and untracked quotas) by looking at ACTIONABLE health problems:
        - Accounts with >= 50% quotas exhausted (HIGH if 100%)
        - GitHub API rate limit running low (< 50 requests) — **read-only
          from prior cache**, this method never calls ``scan_github_api()``
        - Missing critical secrets (GITHUB_TOKEN_IABV, DEVIN_API_KEY_IABV)

        ``get_all_quota_status`` and ``scan_configured_secrets`` are cheap
        (local JSON / env vars).  The GitHub API finding consumes
        ``_gh_api_cache`` populated externally (e.g. by the auto-correction
        scan or a dedicated refresh task).  If no fresh cache exists the
        finding is simply not emitted — no live HTTP probe from here.
        """
        findings: list[SelfExaminationFinding] = []

        try:
            from iabv_v15.services.account_resource_scanner import (
                get_all_quota_status,
                scan_configured_secrets,
            )
        except Exception:
            return findings

        # Finding 1: Exhausted quotas blocking execution
        try:
            quotas = get_all_quota_status()
            exhausted_count = quotas.get('exhausted_count', 0)
            available_count = quotas.get('available_count', 0)
            total = exhausted_count + available_count

            if total > 0 and exhausted_count > 0:
                ratio = exhausted_count / total
                if ratio >= 0.5:
                    exhausted_keys = quotas.get('exhausted_keys', [])
                    severity = IssueSeverity.HIGH if ratio >= 1.0 else IssueSeverity.MEDIUM
                    findings.append(SelfExaminationFinding(
                        category='resource_exhaustion',
                        title=f'{exhausted_count}/{total} cuentas con cuota agotada',
                        summary=(
                            f'{exhausted_count} de {total} cuentas rastreadas tienen '
                            f'la cuota de mensajes agotada. '
                            + ('No quedan workers disponibles para consultas externas. '
                               if ratio >= 1.0
                               else f'Solo {available_count} cuenta(s) disponible(s). ')
                            + 'El sistema deberia priorizar rutas locales (Ollama) '
                            'hasta que las cuotas se reactiven.'
                        ),
                        severity=severity,
                        confidence=0.9,
                        recommendation=(
                            'Esperar reactivacion de cuotas o rotar a cuentas '
                            'frescas. Mientras tanto, usar Ollama como ruta principal.'
                        ),
                        evidence_refs=[f'exhausted_keys:{",".join(exhausted_keys[:5])}'],
                        metadata={
                            'gap_type': 'quota_exhaustion',
                            'exhausted_count': exhausted_count,
                            'available_count': available_count,
                            'exhaustion_ratio': round(ratio, 2),
                        },
                    ))
        except Exception:
            pass

        # Finding 2: API health — consume prior cache only, never probe here.
        # _gh_api_cache is populated externally; if absent or stale we skip.
        now = time.monotonic()
        gh = self._gh_api_cache
        cache_fresh = (
            gh is not None
            and (now - self._gh_api_cached_at) <= self._GH_API_TTL
        )

        if cache_fresh and gh.get('available') and gh.get('remaining', 5000) < 50:
            findings.append(SelfExaminationFinding(
                category='resource_degradation',
                title=f'GitHub API: solo {gh["remaining"]} requests restantes',
                summary=(
                    f'GitHub API tiene solo {gh["remaining"]}/{gh.get("rate_limit", "?")} '
                    f'requests restantes. Se reinicia en {gh.get("reset_at", "?")}. '
                    f'Operaciones que dependan de GitHub podrian fallar.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.95,
                recommendation='Reducir consultas a GitHub API hasta reinicio de rate limit.',
                metadata={
                    'gap_type': 'api_rate_limit',
                    'remaining': gh.get('remaining', 0),
                    'limit': gh.get('rate_limit', 0),
                    'reset_at': gh.get('reset_at', ''),
                },
            ))

        # Finding 3: Critical secrets missing
        try:
            secrets = scan_configured_secrets()
            missing = secrets.get('missing', [])
            critical_missing = [
                s for s in missing
                if s in ('GITHUB_TOKEN_IABV', 'DEVIN_API_KEY_IABV')
            ]
            if critical_missing:
                findings.append(SelfExaminationFinding(
                    category='configuration_gap',
                    title=f'Secretos criticos faltantes: {", ".join(critical_missing)}',
                    summary=(
                        f'{len(critical_missing)} secreto(s) critico(s) no configurado(s): '
                        f'{", ".join(critical_missing)}. Esto bloquea funcionalidad '
                        f'esencial (GitHub, Devin API).'
                    ),
                    severity=IssueSeverity.HIGH,
                    confidence=0.95,
                    recommendation=(
                        'Configurar los secretos faltantes via la UI de IABV '
                        '(auto_provision_missing_secrets). IABV abrira el browser '
                        'a la pagina correcta y guardara el token automaticamente.'
                    ),
                    metadata={
                        'gap_type': 'missing_critical_secrets',
                        'missing_secrets': critical_missing,
                    },
                ))
        except Exception:
            pass

        return findings

    # ------------------------------------------------------------------
    # Brecha 2.3 — Web session health findings
    # ------------------------------------------------------------------

    def _web_session_findings(self) -> list[SelfExaminationFinding]:
        """Detect expired or missing web sessions for governed re-auth.

        Checks each known web provider (ChatGPT, Claude, Gemini) and emits
        a finding when the session is expired and needs human re-login.
        """
        findings: list[SelfExaminationFinding] = []

        try:
            from iabv_v15.services.auto_correction_engine import (
                check_web_session_health,
                _WEB_SESSION_COOKIE_DOMAINS,
            )
        except Exception:
            return findings

        for provider in _WEB_SESSION_COOKIE_DOMAINS:
            try:
                health = check_web_session_health(provider)
            except Exception:
                continue

            status = health.get('status', 'unknown')
            if status == 'expired':
                label_map = {
                    'chatgpt_web': 'ChatGPT Web',
                    'claude_web': 'Claude Web',
                    'gemini_web': 'Gemini Web',
                }
                label = label_map.get(provider, provider)
                url_map = {
                    'chatgpt_web': 'https://chat.openai.com/auth/login',
                    'claude_web': 'https://claude.ai/login',
                    'gemini_web': 'https://gemini.google.com/',
                }
                findings.append(SelfExaminationFinding(
                    category='web_session_expired',
                    title=f'{label} necesita re-login',
                    summary=(
                        f'La sesion web de {label} esta expirada o no existe. '
                        f'Razon: {health.get("reason", "desconocida")}. '
                        f'El proveedor web no sera seleccionado hasta que el '
                        f'usuario re-autentique manualmente.'
                    ),
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.85,
                    recommendation=(
                        f'Abrir {url_map.get(provider, "")} en el navegador, '
                        f'hacer login manualmente (captcha/2FA si aplica), '
                        f'y IABV detectara la nueva sesion automaticamente.'
                    ),
                    source_refs=['check_web_session_health', 'AccountResourceScanner'],
                    metadata={
                        'provider': provider,
                        'session_status': status,
                        'needs_human': health.get('needs_human', True),
                        'expires_hint': health.get('expires_hint'),
                        'reason': health.get('reason', ''),
                    },
                ))

        return findings

    # ==================================================================
    # Audit Platform — Algorithmic Analysis & Optimization
    # Extends OSES with statistical, structural, and validation tooling.
    # ==================================================================

    # ---- MathEngine: statistical analysis on system data ----

    @staticmethod
    def math_engine_moving_average(values: list[float], window: int = 5) -> list[float]:
        """Compute simple moving average over a window."""
        if not values or window < 1:
            return []
        result: list[float] = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            segment = values[start:i + 1]
            result.append(sum(segment) / len(segment))
        return result

    @staticmethod
    def math_engine_exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
        """Compute exponential smoothing (EMA)."""
        if not values:
            return []
        result = [values[0]]
        for val in values[1:]:
            result.append(alpha * val + (1 - alpha) * result[-1])
        return result

    @staticmethod
    def math_engine_z_scores(values: list[float]) -> list[float]:
        """Compute z-scores for anomaly detection."""
        if len(values) < 2:
            return [0.0] * len(values)
        import math
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0
        if std_dev == 0:
            return [0.0] * len(values)
        return [(x - mean) / std_dev for x in values]

    @staticmethod
    def math_engine_iqr_outliers(values: list[float], factor: float = 1.5) -> list[int]:
        """Return indices of IQR outliers."""
        if len(values) < 4:
            return []
        sorted_v = sorted(values)
        n = len(sorted_v)
        q1 = sorted_v[n // 4]
        q3 = sorted_v[(3 * n) // 4]
        iqr = q3 - q1
        lower = q1 - factor * iqr
        upper = q3 + factor * iqr
        return [i for i, v in enumerate(values) if v < lower or v > upper]

    @staticmethod
    def math_engine_correlation(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient between two series."""
        import math
        n = min(len(x), len(y))
        if n < 3:
            return 0.0
        x, y = x[:n], y[:n]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        if std_x == 0 or std_y == 0:
            return 0.0
        return cov / (std_x * std_y)

    @staticmethod
    def math_engine_confidence(success_count: int, total: int) -> float:
        """Wilson score lower bound for confidence estimation."""
        if total == 0:
            return 0.0
        import math
        z = 1.96  # 95% confidence
        p = success_count / total
        denominator = 1 + z * z / total
        centre = p + z * z / (2 * total)
        adjustment = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
        return max(0.0, (centre - adjustment) / denominator)

    def math_engine_report(self, recent_runs: list[RunRecord] | None = None) -> dict[str, Any]:
        """Generate a statistical report from system data."""
        runs = recent_runs or self._recent_runs()
        latencies = [float(getattr(r, 'elapsed_ms', 0) or 0) for r in runs if getattr(r, 'elapsed_ms', None)]
        successes = [1.0 if r.status == RunStatus.SUCCESS else 0.0 for r in runs]
        report: dict[str, Any] = {
            'sample_size': len(runs),
            'success_rate': sum(successes) / len(successes) if successes else 0.0,
        }
        if latencies:
            report['latency_ema'] = self.math_engine_exponential_smoothing(latencies)[-1] if latencies else 0.0
            report['latency_z_scores'] = self.math_engine_z_scores(latencies)
            report['latency_iqr_outliers'] = self.math_engine_iqr_outliers(latencies)
            report['latency_sma'] = self.math_engine_moving_average(latencies)[-1] if latencies else 0.0
        if successes:
            report['success_confidence'] = self.math_engine_confidence(
                int(sum(successes)), len(successes),
            )
        return report

    # ---- AlgorithmAnalyzer: structural code analysis ----

    @staticmethod
    def algorithm_analyzer_cyclomatic_complexity(source_code: str) -> int:
        """Estimate cyclomatic complexity of Python source code."""
        import re
        decision_keywords = re.findall(
            r'\b(if|elif|for|while|except|and|or)\b', source_code,
        )
        return 1 + len(decision_keywords)

    @staticmethod
    def algorithm_analyzer_dead_code(source_code: str) -> list[dict[str, Any]]:
        """Detect potentially dead code patterns."""
        import re
        issues: list[dict[str, Any]] = []
        lines = source_code.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('# TODO') or stripped.startswith('# FIXME'):
                issues.append({'line': i, 'type': 'todo_comment', 'text': stripped[:80]})
            if re.match(r'^\s*(return|raise)\b', line):
                if i < len(lines):
                    next_stripped = lines[i].strip() if i < len(lines) else ''
                    if next_stripped and not next_stripped.startswith(('#', 'def ', 'class ', 'except', 'elif', 'else', ')', ']', '}')):
                        issues.append({'line': i + 1, 'type': 'unreachable_after_return', 'text': next_stripped[:80]})
        return issues

    @staticmethod
    def algorithm_analyzer_dependency_map(module_source: str) -> list[str]:
        """Extract import dependencies from Python source."""
        import re
        deps: list[str] = []
        for match in re.finditer(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', module_source, re.MULTILINE):
            dep = match.group(1) or match.group(2)
            if dep:
                deps.append(dep)
        return sorted(set(deps))

    @staticmethod
    def algorithm_analyzer_antipatterns(source_code: str) -> list[dict[str, Any]]:
        """Detect common anti-patterns in Python source."""
        import re
        issues: list[dict[str, Any]] = []
        lines = source_code.splitlines()
        for i, line in enumerate(lines, 1):
            if re.search(r'\bexcept\s*:', line) and 'pragma' not in line:
                issues.append({'line': i, 'type': 'bare_except', 'text': line.strip()[:80]})
            if re.search(r'\bgetattr\s*\(.*,\s*["\']', line) and 'pragma' not in line:
                issues.append({'line': i, 'type': 'dynamic_getattr', 'text': line.strip()[:80]})
            if len(line) > 200:
                issues.append({'line': i, 'type': 'long_line', 'length': len(line)})
        return issues

    def algorithm_analysis_report(self, source_code: str) -> dict[str, Any]:
        """Full structural analysis of given source code."""
        return {
            'cyclomatic_complexity': self.algorithm_analyzer_cyclomatic_complexity(source_code),
            'dead_code': self.algorithm_analyzer_dead_code(source_code),
            'dependencies': self.algorithm_analyzer_dependency_map(source_code),
            'antipatterns': self.algorithm_analyzer_antipatterns(source_code),
        }

    # ---- AlgorithmTestBench: systematic test case generation ----

    @staticmethod
    def test_bench_edge_cases(func: Any, test_inputs: list[Any]) -> list[dict[str, Any]]:
        """Run a function against test inputs and record outcomes."""
        results: list[dict[str, Any]] = []
        for inp in test_inputs:
            try:
                output = func(inp)
                results.append({'input': repr(inp), 'output': repr(output), 'status': 'ok', 'error': None})
            except Exception as exc:
                results.append({'input': repr(inp), 'output': None, 'status': 'error', 'error': str(exc)})
        return results

    @staticmethod
    def test_bench_null_inputs(func: Any) -> list[dict[str, Any]]:
        """Test function with None, empty string, empty list, 0, etc."""
        null_inputs: list[Any] = [None, '', [], {}, 0, 0.0, False, set()]
        results: list[dict[str, Any]] = []
        for inp in null_inputs:
            try:
                output = func(inp)
                results.append({'input': repr(inp), 'output': repr(output), 'status': 'ok', 'error': None})
            except Exception as exc:
                results.append({'input': repr(inp), 'output': None, 'status': 'error', 'error': str(exc)})
        return results

    @staticmethod
    def test_bench_overflow(func: Any) -> list[dict[str, Any]]:
        """Test function with extreme numeric values."""
        overflow_inputs = [10**18, -10**18, float('inf'), float('-inf'), float('nan'), 2**63 - 1]
        results: list[dict[str, Any]] = []
        for inp in overflow_inputs:
            try:
                output = func(inp)
                results.append({'input': repr(inp), 'output': repr(output), 'status': 'ok', 'error': None})
            except Exception as exc:
                results.append({'input': repr(inp), 'output': None, 'status': 'error', 'error': str(exc)})
        return results

    @staticmethod
    def test_bench_performance(func: Any, input_val: Any, iterations: int = 100) -> dict[str, Any]:
        """Benchmark function execution time."""
        import time as _t
        times: list[float] = []
        for _ in range(iterations):
            t0 = _t.perf_counter()
            try:
                func(input_val)
            except Exception:
                pass
            times.append(_t.perf_counter() - t0)
        import math
        mean_t = sum(times) / len(times)
        std_t = math.sqrt(sum((t - mean_t) ** 2 for t in times) / len(times)) if len(times) > 1 else 0.0
        return {
            'iterations': iterations,
            'mean_ms': round(mean_t * 1000, 3),
            'std_ms': round(std_t * 1000, 3),
            'min_ms': round(min(times) * 1000, 3),
            'max_ms': round(max(times) * 1000, 3),
        }

    def test_bench_report(self, func: Any, test_inputs: list[Any] | None = None) -> dict[str, Any]:
        """Full test bench report for a function."""
        inputs = test_inputs or []
        return {
            'edge_cases': self.test_bench_edge_cases(func, inputs),
            'null_inputs': self.test_bench_null_inputs(func),
            'overflow': self.test_bench_overflow(func),
            'performance': self.test_bench_performance(func, inputs[0] if inputs else None),
        }

    # ---- AlgorithmValidator: contract and rule validation ----

    @staticmethod
    def validator_check_contracts(
        source_code: str,
        *,
        required_preconditions: list[str] | None = None,
        required_postconditions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Verify that source code contains expected pre/postconditions."""
        import re
        found_pre = [p for p in (required_preconditions or []) if re.search(re.escape(p), source_code)]
        found_post = [p for p in (required_postconditions or []) if re.search(re.escape(p), source_code)]
        missing_pre = [p for p in (required_preconditions or []) if p not in found_pre]
        missing_post = [p for p in (required_postconditions or []) if p not in found_post]
        return {
            'preconditions_found': found_pre,
            'preconditions_missing': missing_pre,
            'postconditions_found': found_post,
            'postconditions_missing': missing_post,
            'valid': not missing_pre and not missing_post,
        }

    @staticmethod
    def validator_check_exceptions(source_code: str) -> list[dict[str, Any]]:
        """Check that exceptions are properly handled (not bare except)."""
        import re
        issues: list[dict[str, Any]] = []
        for i, line in enumerate(source_code.splitlines(), 1):
            if re.search(r'\bexcept\s*:', line) and 'pragma' not in line:
                issues.append({'line': i, 'issue': 'bare_except', 'text': line.strip()[:80]})
            if re.search(r'\bpass\s*$', line):
                context_start = max(0, i - 3)
                context = source_code.splitlines()[context_start:i]
                if any('except' in cl for cl in context):
                    issues.append({'line': i, 'issue': 'silent_exception', 'text': line.strip()[:80]})
        return issues

    @staticmethod
    def validator_check_agents_rules(source_code: str) -> list[dict[str, Any]]:
        """Check for AGENTS.md violations in source code."""
        violations: list[dict[str, Any]] = []
        lines = source_code.splitlines()
        for i, line in enumerate(lines, 1):
            lower = line.lower()
            if 'class' in lower and 'orchestrator' in lower and 'adaptive' not in lower:
                violations.append({'line': i, 'rule': 'no_new_orchestrator', 'text': line.strip()[:80]})
            if 'perceptionsnapshot' in lower and 'class' in lower:
                violations.append({'line': i, 'rule': 'no_duplicate_perception', 'text': line.strip()[:80]})
        return violations

    @staticmethod
    def validator_check_types(source_code: str) -> list[dict[str, Any]]:
        """Check for lazy typing patterns (Any, getattr)."""
        import re
        issues: list[dict[str, Any]] = []
        for i, line in enumerate(source_code.splitlines(), 1):
            if re.search(r'\bAny\b', line) and 'import' not in line and '#' not in line.split('Any')[0]:
                pass  # Any in type hints is acceptable in this codebase
            if re.search(r'\bsetattr\s*\(', line) and 'pragma' not in line:
                issues.append({'line': i, 'issue': 'setattr_usage', 'text': line.strip()[:80]})
        return issues

    def validation_report(self, source_code: str) -> dict[str, Any]:
        """Full validation report for source code."""
        return {
            'contracts': self.validator_check_contracts(source_code),
            'exceptions': self.validator_check_exceptions(source_code),
            'agents_rules': self.validator_check_agents_rules(source_code),
            'types': self.validator_check_types(source_code),
        }

    # ---- AlgorithmOptimizer: parameter tuning and A/B testing ----

    @staticmethod
    def optimizer_grid_search(
        func: Any,
        param_grid: dict[str, list[Any]],
        eval_func: Any,
        base_input: Any = None,
    ) -> list[dict[str, Any]]:
        """Simple grid search over parameter combinations."""
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        results: list[dict[str, Any]] = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            try:
                output = func(base_input, **params) if base_input is not None else func(**params)
                score = eval_func(output) if eval_func else 0.0
                results.append({'params': params, 'score': score, 'status': 'ok', 'error': None})
            except Exception as exc:
                results.append({'params': params, 'score': 0.0, 'status': 'error', 'error': str(exc)})
        results.sort(key=lambda r: r['score'], reverse=True)
        return results

    @staticmethod
    def optimizer_ab_test(
        func_a: Any,
        func_b: Any,
        test_inputs: list[Any],
        eval_func: Any,
    ) -> dict[str, Any]:
        """Compare two implementations on the same inputs."""
        scores_a: list[float] = []
        scores_b: list[float] = []
        for inp in test_inputs:
            try:
                out_a = func_a(inp)
                scores_a.append(float(eval_func(out_a)))
            except Exception:
                scores_a.append(0.0)
            try:
                out_b = func_b(inp)
                scores_b.append(float(eval_func(out_b)))
            except Exception:
                scores_b.append(0.0)
        mean_a = sum(scores_a) / len(scores_a) if scores_a else 0.0
        mean_b = sum(scores_b) / len(scores_b) if scores_b else 0.0
        return {
            'variant_a_mean': round(mean_a, 4),
            'variant_b_mean': round(mean_b, 4),
            'winner': 'a' if mean_a >= mean_b else 'b',
            'margin': round(abs(mean_a - mean_b), 4),
            'sample_size': len(test_inputs),
        }

    def optimization_proposal(
        self,
        func: Any,
        param_grid: dict[str, list[Any]],
        eval_func: Any,
        base_input: Any = None,
    ) -> dict[str, Any]:
        """Generate an optimization proposal with best parameters."""
        results = self.optimizer_grid_search(func, param_grid, eval_func, base_input)
        best = results[0] if results else None
        return {
            'best_params': best['params'] if best else {},
            'best_score': best['score'] if best else 0.0,
            'total_combinations': len(results),
            'top_3': results[:3],
        }

    # ---- ExperimentSimulator: scenario simulation ----

    @staticmethod
    def simulator_fault_injection(
        func: Any,
        fault_scenarios: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Simulate fault scenarios and record system behavior."""
        results: list[dict[str, Any]] = []
        for scenario in fault_scenarios:
            name = str(scenario.get('name') or 'unnamed')
            fault_input = scenario.get('input')
            try:
                output = func(fault_input)
                results.append({
                    'scenario': name,
                    'status': 'completed',
                    'output': repr(output)[:200],
                    'graceful': True,
                })
            except Exception as exc:
                results.append({
                    'scenario': name,
                    'status': 'error',
                    'error': str(exc),
                    'graceful': 'handled' in str(type(exc).__name__).lower(),
                })
        return results

    @staticmethod
    def simulator_stress_test(
        func: Any,
        concurrent_count: int = 10,
        input_factory: Any = None,
    ) -> dict[str, Any]:
        """Simulate concurrent execution stress."""
        import time as _t
        results: list[dict[str, Any]] = []
        t0 = _t.perf_counter()
        for i in range(concurrent_count):
            inp = input_factory(i) if input_factory else i
            start = _t.perf_counter()
            try:
                func(inp)
                results.append({'index': i, 'status': 'ok', 'elapsed_ms': round((_t.perf_counter() - start) * 1000, 2)})
            except Exception as exc:
                results.append({'index': i, 'status': 'error', 'error': str(exc), 'elapsed_ms': round((_t.perf_counter() - start) * 1000, 2)})
        total_ms = round((_t.perf_counter() - t0) * 1000, 2)
        ok_count = sum(1 for r in results if r['status'] == 'ok')
        return {
            'total_runs': concurrent_count,
            'success_count': ok_count,
            'failure_count': concurrent_count - ok_count,
            'total_ms': total_ms,
            'avg_ms': round(total_ms / concurrent_count, 2) if concurrent_count else 0,
            'results': results,
        }

    @staticmethod
    def simulator_monte_carlo(
        func: Any,
        param_sampler: Any,
        iterations: int = 100,
    ) -> dict[str, Any]:
        """Monte Carlo simulation: run func with random parameters."""
        import random
        random.seed(42)
        outputs: list[Any] = []
        errors: list[str] = []
        for _ in range(iterations):
            params = param_sampler()
            try:
                result = func(**params) if isinstance(params, dict) else func(params)
                outputs.append(result)
            except Exception as exc:
                errors.append(str(exc))
        numeric_outputs = [float(o) for o in outputs if isinstance(o, (int, float))]
        return {
            'iterations': iterations,
            'success_count': len(outputs),
            'error_count': len(errors),
            'numeric_mean': sum(numeric_outputs) / len(numeric_outputs) if numeric_outputs else None,
            'numeric_min': min(numeric_outputs) if numeric_outputs else None,
            'numeric_max': max(numeric_outputs) if numeric_outputs else None,
        }

    @staticmethod
    def simulator_what_if(
        current_config: dict[str, Any],
        changes: dict[str, Any],
        impact_estimator: Any,
    ) -> dict[str, Any]:
        """Estimate impact of config changes without applying them."""
        proposed = {**current_config, **changes}
        try:
            current_score = impact_estimator(current_config)
            proposed_score = impact_estimator(proposed)
            return {
                'current_score': current_score,
                'proposed_score': proposed_score,
                'delta': proposed_score - current_score,
                'improvement': proposed_score > current_score,
                'changes': changes,
            }
        except Exception as exc:
            return {
                'error': str(exc),
                'changes': changes,
                'improvement': False,
            }

    def simulation_report(
        self,
        func: Any,
        fault_scenarios: list[dict[str, Any]] | None = None,
        stress_count: int = 10,
    ) -> dict[str, Any]:
        """Full simulation report combining fault injection and stress testing."""
        return {
            'fault_injection': self.simulator_fault_injection(func, fault_scenarios or []),
            'stress_test': self.simulator_stress_test(func, stress_count),
        }

    # ------------------------------------------------------------------
    # Task-packet pattern findings (detection)
    # ------------------------------------------------------------------

    _TP_MIN_RUNS = 5
    _TP_HIGH_UNRESOLVED_RATIO = 0.4
    _TP_HIGH_APPROVAL_RATIO = 0.5
    _TP_HIGH_NO_WORKER_RATIO = 0.3

    def _task_packet_pattern_findings(
        self,
        *,
        experiment_runs: list[Any],
    ) -> list[SelfExaminationFinding]:
        total = 0
        evidence_states: Counter[str] = Counter()
        approval_count = 0
        no_worker_count = 0
        gate_unusable_count = 0
        wt_budget_exhausted = 0
        wt_handoff_unresolved = 0
        wt_total = 0

        for run in experiment_runs:
            meta = getattr(run, 'metadata', None) or {}
            eb = meta.get('evidence_basis')
            if eb is None:
                continue
            total += 1
            state = eb.get('state', 'unknown') if isinstance(eb, dict) else 'unknown'
            evidence_states[state] += 1

            gf = meta.get('governance_flags') or {}
            if gf.get('approval_required'):
                approval_count += 1

            should_consult = bool(gf.get('should_consult'))

            sw = meta.get('selected_worker') or {}
            has_worker = bool(
                sw.get('tool') or sw.get('email')
                or sw.get('browser') or sw.get('profile')
                or sw.get('name') or sw.get('assistant_kind')
            )
            if should_consult and not has_worker:
                no_worker_count += 1

            rwc = meta.get('ranked_worker_count')
            if should_consult and rwc is not None and int(rwc) == 0:
                gate_unusable_count += 1

            wt = meta.get('worker_telemetry')
            if isinstance(wt, dict) and wt.get('worker_kind'):
                wt_total += 1
                bs = str(wt.get('budget_state') or '').lower()
                if bs in {'exhausted', 'quota_exceeded', 'timeout'}:
                    wt_budget_exhausted += 1
                if wt.get('handoff_required') and wt.get('continuation_state') != 'resumed':
                    wt_handoff_unresolved += 1

        if total < self._TP_MIN_RUNS:
            return []

        results: list[SelfExaminationFinding] = []
        unresolved_count = evidence_states.get('unresolved', 0)
        unresolved_ratio = unresolved_count / total

        if unresolved_ratio >= self._TP_HIGH_UNRESOLVED_RATIO:
            results.append(SelfExaminationFinding(
                category='task_packet_high_unresolved',
                severity=IssueSeverity.MEDIUM,
                title=f'Alto ratio de evidence unresolved ({unresolved_ratio:.0%})',
                summary=(
                    f'{unresolved_count}/{total} runs recientes tienen '
                    f'evidence_basis.state == unresolved.'
                ),
                confidence=min(0.6 + unresolved_ratio * 0.3, 0.95),
                recommendation=(
                    'Verificar world model, environment_id y learning '
                    'persistido para reducir unresolved.'
                ),
                source_refs=['ExperimentRun.metadata.evidence_basis'],
                metadata={
                    'pattern': 'high_unresolved',
                    'unresolved_count': unresolved_count,
                    'total': total,
                    'ratio': round(unresolved_ratio, 3),
                },
            ))

        approval_ratio = approval_count / total
        if approval_ratio >= self._TP_HIGH_APPROVAL_RATIO:
            results.append(SelfExaminationFinding(
                category='task_packet_recurring_approval',
                severity=IssueSeverity.MEDIUM,
                title=f'Approval requerido recurrente ({approval_ratio:.0%})',
                summary=(
                    f'{approval_count}/{total} runs recientes requieren '
                    f'aprobacion. Puede bloquear progreso autonomo.'
                ),
                confidence=min(0.6 + approval_ratio * 0.3, 0.95),
                recommendation=(
                    'Revisar governance policies y considerar ajustar '
                    'umbrales para rutas locales ya validadas.'
                ),
                source_refs=['ExperimentRun.metadata.governance_flags'],
                metadata={
                    'pattern': 'recurring_approval',
                    'approval_count': approval_count,
                    'total': total,
                    'ratio': round(approval_ratio, 3),
                },
            ))

        no_worker_ratio = no_worker_count / total
        if no_worker_ratio >= self._TP_HIGH_NO_WORKER_RATIO:
            results.append(SelfExaminationFinding(
                category='task_packet_no_worker',
                severity=IssueSeverity.MEDIUM,
                title=f'Sin worker seleccionado recurrente ({no_worker_ratio:.0%})',
                summary=(
                    f'{no_worker_count}/{total} runs recientes no tienen '
                    f'selected_worker. Verificar disponibilidad.'
                ),
                confidence=min(0.6 + no_worker_ratio * 0.3, 0.95),
                recommendation=(
                    'Verificar workers configurados y disponibles. '
                    'Si todas las rutas son locales, puede ser esperado.'
                ),
                source_refs=['ExperimentRun.metadata.selected_worker'],
                metadata={
                    'pattern': 'no_worker',
                    'no_worker_count': no_worker_count,
                    'total': total,
                    'ratio': round(no_worker_ratio, 3),
                },
            ))

        if gate_unusable_count >= 2:
            results.append(SelfExaminationFinding(
                category='task_packet_gate_unusable',
                severity=IssueSeverity.MEDIUM,
                title=f'Worker gate sin candidatos ({gate_unusable_count} veces)',
                summary=(
                    f'{gate_unusable_count}/{total} runs recientes tienen '
                    f'ranked_worker_count == 0.'
                ),
                confidence=0.7,
                recommendation=(
                    'Revisar worker_health_gate y estado de cuentas '
                    'externas.'
                ),
                source_refs=['ExperimentRun.metadata.ranked_worker_count'],
                metadata={
                    'pattern': 'gate_unusable',
                    'gate_unusable_count': gate_unusable_count,
                    'total': total,
                },
            ))

        if wt_total > 0 and wt_budget_exhausted >= 2:
            ratio = wt_budget_exhausted / wt_total
            results.append(SelfExaminationFinding(
                category='task_packet_worker_budget_exhausted',
                severity=IssueSeverity.MEDIUM,
                title=f'Workers con presupuesto agotado ({wt_budget_exhausted}/{wt_total})',
                summary=(
                    f'{wt_budget_exhausted} de {wt_total} ejecuciones con '
                    f'telemetria reportan budget exhausted/timeout. '
                    f'Puede requerir redistribucion de carga entre workers.'
                ),
                confidence=min(0.6 + ratio * 0.3, 0.95),
                recommendation=(
                    'Verificar cuotas de workers externos (Codex, Devin, '
                    'Windsurf). Considerar handoff a worker con cuota '
                    'disponible o reanudar en nueva sesion.'
                ),
                source_refs=['ExperimentRun.metadata.worker_telemetry.budget_state'],
                metadata={
                    'pattern': 'worker_budget_exhausted',
                    'budget_exhausted_count': wt_budget_exhausted,
                    'wt_total': wt_total,
                    'ratio': round(ratio, 3),
                },
            ))

        if wt_total > 0 and wt_handoff_unresolved >= 2:
            ratio = wt_handoff_unresolved / wt_total
            results.append(SelfExaminationFinding(
                category='task_packet_worker_handoff_unresolved',
                severity=IssueSeverity.MEDIUM,
                title=f'Handoffs sin resolver ({wt_handoff_unresolved}/{wt_total})',
                summary=(
                    f'{wt_handoff_unresolved} de {wt_total} ejecuciones '
                    f'requieren handoff pero no han sido retomadas.'
                ),
                confidence=min(0.6 + ratio * 0.3, 0.95),
                recommendation=(
                    'Revisar tareas con handoff_required=true y '
                    'continuation_state != resumed. Asignar a otro '
                    'worker o reanudar manualmente.'
                ),
                source_refs=['ExperimentRun.metadata.worker_telemetry.handoff_required'],
                metadata={
                    'pattern': 'worker_handoff_unresolved',
                    'handoff_unresolved_count': wt_handoff_unresolved,
                    'wt_total': wt_total,
                    'ratio': round(ratio, 3),
                },
            ))

        # --- High correction recurrence ---
        if wt_total >= 3:
            correction_vals = [
                int(wt2.get('correction_rounds') or 0)
                for run in experiment_runs
                if isinstance((wt2 := (run.metadata or {}).get('worker_telemetry')), dict)
            ]
            if correction_vals:
                avg_corrections = sum(correction_vals) / len(correction_vals)
                if avg_corrections >= 2.0:
                    results.append(SelfExaminationFinding(
                        category='task_packet_worker_high_corrections',
                        severity=IssueSeverity.MEDIUM,
                        title=f'Alta recurrencia de correcciones ({avg_corrections:.1f} avg)',
                        summary=(
                            f'Los workers externos requieren un promedio de '
                            f'{avg_corrections:.1f} rondas de correccion por '
                            f'ejecucion. Puede indicar prompts poco claros '
                            f'o workers inadecuados para la tarea.'
                        ),
                        confidence=min(0.6 + avg_corrections * 0.1, 0.9),
                        recommendation=(
                            'Revisar la calidad de los prompts enviados. '
                            'Considerar cambiar de worker si el patron persiste.'
                        ),
                        source_refs=['ExperimentRun.metadata.worker_telemetry.correction_rounds'],
                        metadata={
                            'pattern': 'high_correction_recurrence',
                            'avg_corrections': round(avg_corrections, 2),
                            'sample_size': len(correction_vals),
                        },
                    ))

        # --- Compression / reuse quality ---
        if wt_total >= 3:
            cr_vals = [
                float(wt3.get('compression_ratio'))
                for run in experiment_runs
                if isinstance((wt3 := (run.metadata or {}).get('worker_telemetry')), dict)
                and isinstance(wt3.get('compression_ratio'), (int, float))
            ]
            if len(cr_vals) >= 3:
                avg_cr = sum(cr_vals) / len(cr_vals)
                if avg_cr < 0.3:
                    results.append(SelfExaminationFinding(
                        category='task_packet_worker_good_compression',
                        severity=IssueSeverity.LOW,
                        title=f'Buena compresion de output ({avg_cr:.2f})',
                        summary=(
                            f'Las respuestas de workers tienen ratio de compresion '
                            f'promedio {avg_cr:.2f} (bajo = mas estructurado). '
                            f'Esto sugiere outputs bien organizados y reutilizables.'
                        ),
                        confidence=0.6,
                        recommendation=(
                            'Mantener la estrategia actual de prompting. '
                            'Considerar promover workers con buena compresion.'
                        ),
                        source_refs=['ExperimentRun.metadata.worker_telemetry.compression_ratio'],
                        metadata={
                            'pattern': 'good_compression',
                            'avg_compression_ratio': round(avg_cr, 4),
                            'sample_size': len(cr_vals),
                        },
                    ))

        # --- Nonlinearity detection (performance jump) ---
        recent_scores = [
            float(run.total_score)
            for run in experiment_runs
            if hasattr(run, 'total_score')
            and isinstance(run.total_score, (int, float))
        ]
        if len(recent_scores) >= 10:
            try:
                from iabv_v15.services.lab.scientific_proxy_engine import nonlinearity_indicator
                nli = nonlinearity_indicator(recent_scores, window=5)
                if nli >= 1.5:
                    results.append(SelfExaminationFinding(
                        category='task_packet_performance_jump',
                        severity=IssueSeverity.LOW,
                        title=f'Salto no lineal de rendimiento detectado ({nli:.2f}x)',
                        summary=(
                            f'El rendimiento promedio de las ultimas 5 ejecuciones '
                            f'es {nli:.2f}x mayor que las 5 anteriores. '
                            f'Esto puede indicar una mejora significativa en la '
                            f'estrategia o configuracion actual.'
                        ),
                        confidence=min(0.5 + (nli - 1.0) * 0.2, 0.85),
                        recommendation=(
                            'Investigar que cambio produjo la mejora. '
                            'Si es reproducible, promover la configuracion actual.'
                        ),
                        source_refs=['ExperimentRun.total_score'],
                        metadata={
                            'pattern': 'nonlinear_performance_jump',
                            'nonlinearity_indicator': round(nli, 4),
                            'recent_scores_count': len(recent_scores),
                        },
                    ))
            except Exception:
                pass

        # --- Metacognitive calibration findings ---
        if wt_total >= 3:
            mc_cal_errors: list[float] = []
            mc_fp = 0
            mc_fn = 0
            for run in experiment_runs:
                mc = (run.metadata or {}).get('metacognitive_evaluation')
                if not isinstance(mc, dict):
                    continue
                ce = mc.get('calibration_error')
                if isinstance(ce, (int, float)):
                    mc_cal_errors.append(float(ce))
                if mc.get('false_positive'):
                    mc_fp += 1
                if mc.get('false_negative'):
                    mc_fn += 1

            if len(mc_cal_errors) >= 3:
                avg_ce = sum(mc_cal_errors) / len(mc_cal_errors)
                if avg_ce > 0.4:
                    results.append(SelfExaminationFinding(
                        category='task_packet_metacognitive_miscalibration',
                        severity=IssueSeverity.MEDIUM,
                        title=f'Mala calibracion metacognitiva ({avg_ce:.2f} avg)',
                        summary=(
                            f'El error de calibracion promedio es {avg_ce:.2f} '
                            f'sobre {len(mc_cal_errors)} evaluaciones. '
                            f'Falsos positivos: {mc_fp}, falsos negativos: {mc_fn}. '
                            f'El sistema no predice bien sus propios resultados.'
                        ),
                        confidence=min(0.6 + avg_ce * 0.3, 0.9),
                        recommendation=(
                            'Revisar la calidad de las recomendaciones de '
                            'StrategySelector. Considerar ajustar pesos '
                            'adaptativos o agregar mas evidencia antes de '
                            'recomendar.'
                        ),
                        source_refs=['ExperimentRun.metadata.metacognitive_evaluation.calibration_error'],
                        metadata={
                            'pattern': 'metacognitive_miscalibration',
                            'avg_calibration_error': round(avg_ce, 4),
                            'false_positive_count': mc_fp,
                            'false_negative_count': mc_fn,
                            'evaluations_count': len(mc_cal_errors),
                        },
                    ))

                if mc_fp >= 2 and mc_fp > mc_fn:
                    results.append(SelfExaminationFinding(
                        category='task_packet_metacognitive_overconfidence',
                        severity=IssueSeverity.MEDIUM,
                        title=f'Sobreconfianza recurrente ({mc_fp} falsos positivos)',
                        summary=(
                            f'El sistema predijo exito {mc_fp} veces cuando realmente '
                            f'fallo. Esto indica sobreconfianza sistematica en las '
                            f'recomendaciones de ruta/worker.'
                        ),
                        confidence=min(0.6 + mc_fp * 0.1, 0.9),
                        recommendation=(
                            'Bajar el umbral de confianza en StrategySelector '
                            'o requerir mas evidencia antes de predecir exito.'
                        ),
                        source_refs=['ExperimentRun.metadata.metacognitive_evaluation.false_positive'],
                        metadata={
                            'pattern': 'overconfidence',
                            'false_positive_count': mc_fp,
                            'false_negative_count': mc_fn,
                        },
                    ))

                if mc_fn >= 2 and mc_fn > mc_fp:
                    results.append(SelfExaminationFinding(
                        category='task_packet_metacognitive_underconfidence',
                        severity=IssueSeverity.LOW,
                        title=f'Infraconfianza recurrente ({mc_fn} falsos negativos)',
                        summary=(
                            f'El sistema predijo fallo {mc_fn} veces cuando realmente '
                            f'tuvo exito. Esto indica infraconfianza sistematica.'
                        ),
                        confidence=min(0.5 + mc_fn * 0.1, 0.85),
                        recommendation=(
                            'El sistema subestima sus capacidades. Considerar '
                            'ajustar pesos adaptativos al alza o expandir '
                            'la evidencia de rutas exitosas.'
                        ),
                        source_refs=['ExperimentRun.metadata.metacognitive_evaluation.false_negative'],
                        metadata={
                            'pattern': 'underconfidence',
                            'false_positive_count': mc_fp,
                            'false_negative_count': mc_fn,
                        },
                    ))

        return results

    def _compute_current_adaptive_nc(self) -> int | None:
        repo = self.experiment_lab_repository
        if repo is None:
            return None
        try:
            from iabv_v15.services.lab.experiment_lab import ExperimentLab
            from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
            from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
            from iabv_v15.services.lab.strategy_selector import StrategySelector
            lab = ExperimentLab(
                repository=repo,
                registry=AlgorithmBenchmarkRegistry(),
                scoring_engine=DecisionScoringEngine(),
                strategy_selector=StrategySelector(),
            )
            return lab.calculate_adaptive_threshold()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Adaptive threshold N_c shift detection (Brecha 3.3)
    # ------------------------------------------------------------------

    def _adaptive_threshold_shift_findings(
        self,
        *,
        previous_review: Any | None = None,
    ) -> list[SelfExaminationFinding]:
        """Detect significant shifts in the adaptive N_c threshold."""
        repo = self.experiment_lab_repository
        if repo is None:
            return []
        try:
            from iabv_v15.services.lab.experiment_lab import ExperimentLab
            from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
            from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
            from iabv_v15.services.lab.strategy_selector import StrategySelector
            lab = ExperimentLab(
                repository=repo,
                registry=AlgorithmBenchmarkRegistry(),
                scoring_engine=DecisionScoringEngine(),
                strategy_selector=StrategySelector(),
            )
            current_nc = lab.calculate_adaptive_threshold()
        except Exception:
            return []

        previous_nc = 3
        if previous_review is not None:
            meta = getattr(previous_review, 'metadata', None) or {}
            previous_nc = int(meta.get('adaptive_threshold_nc', 3))

        results: list[SelfExaminationFinding] = []
        if previous_nc > 0 and abs(current_nc - previous_nc) / max(previous_nc, 1) > 0.20:
            results.append(SelfExaminationFinding(
                category='adaptive_threshold_shift',
                severity=IssueSeverity.LOW,
                title=f'N_c shifted from {previous_nc} to {current_nc}',
                summary=(
                    f'The adaptive statistical threshold changed from '
                    f'{previous_nc} to {current_nc} based on accumulated '
                    f'evidence volume.'
                ),
                confidence=0.85,
                recommendation=(
                    'Review domain-specific thresholds via '
                    'ExperimentLab.get_current_thresholds() to ensure '
                    'each domain has appropriate sensitivity.'
                ),
                metadata={
                    'previous_nc': previous_nc,
                    'current_nc': current_nc,
                    'shift_ratio': round(
                        abs(current_nc - previous_nc) / max(previous_nc, 1), 3,
                    ),
                },
            ))
        return results

    # ------------------------------------------------------------------
    # Windows platform integration findings (Fix 18c)
    # ------------------------------------------------------------------

    def _windows_integration_findings(self) -> list[SelfExaminationFinding]:
        """Detect missing Windows-native capabilities and emit structured findings.

        Reads the ``platform.*`` entries from the EnvironmentSelfModel
        capability_graph.  For each capability that is ``missing`` or has
        ``missing_dependency`` status, emits a finding with structured
        metadata matching the PlatformPendingTask schema so the pending
        queue can be seeded from these findings.
        """
        findings: list[SelfExaminationFinding] = []
        if os.name != 'nt':
            return findings

        env_model = self._environment_model()
        if env_model is None:
            return findings

        cap_graph = env_model.capability_graph or []
        platform_caps = [c for c in cap_graph if c.capability_id.startswith('platform.')]

        missing_caps = [
            c for c in platform_caps
            if not c.available and c.status not in ('not_applicable',)
        ]

        if not missing_caps:
            return findings

        missing_ids = [c.capability_id for c in missing_caps]
        missing_titles = [c.title for c in missing_caps]

        findings.append(SelfExaminationFinding(
            category='windows_integration_gaps',
            title=f'{len(missing_caps)} capacidades Windows nativas faltantes',
            summary=(
                f'El sistema detecta {len(missing_caps)} capacidades de la '
                f'plataforma Windows que no estan disponibles o tienen '
                f'dependencias faltantes: {", ".join(missing_titles[:5])}.'
            ),
            severity=IssueSeverity.MEDIUM,
            confidence=0.9,
            recommendation=(
                'Revisar la cola de pendientes de plataforma en '
                'data/evolution/platform_pending/. Cada capacidad '
                'faltante tiene next_action y dependency_missing '
                'documentados para continuacion por agente o usuario.'
            ),
            source_refs=[
                'iabv_v15.services.evolution.environment_self_awareness_service._windows_platform_capabilities',
                'data/evolution/platform_pending/',
            ],
            metadata={
                'phase': 'windows_integration',
                'missing_capability_ids': missing_ids,
                'missing_count': len(missing_caps),
                'total_platform_caps': len(platform_caps),
                'coverage_ratio': round(
                    (len(platform_caps) - len(missing_caps)) / max(len(platform_caps), 1),
                    2,
                ),
            },
        ))

        for cap in missing_caps:
            dep_info = cap.metadata.get('missing', '') if cap.metadata else ''
            findings.append(SelfExaminationFinding(
                category='windows_capability_missing',
                title=f'Falta: {cap.title}',
                summary=cap.summary or f'{cap.capability_id} no disponible',
                severity=IssueSeverity.LOW,
                confidence=0.85,
                recommendation=f'Dependencia: {dep_info}' if dep_info else 'Verificar disponibilidad en el entorno',
                source_refs=[cap.capability_id],
                metadata={
                    'capability_id': cap.capability_id,
                    'status': cap.status,
                    'pending_task_status': 'PENDING',
                },
            ))

        return findings

    # ------------------------------------------------------------------
    # UniversalAutonomyIndex (Fase 7)
    # ------------------------------------------------------------------

    def _universal_autonomy_index_findings(
        self,
        *,
        recent_runs: list[RunRecord],
        adaptive_sessions: list[Any],
        experiment_runs: list[ExperimentRun],
        world: WorldModelSnapshot,
        findings_so_far: list[SelfExaminationFinding],
    ) -> list[SelfExaminationFinding]:
        """Calculate composite autonomy metrics and emit a summary finding.

        Computes four scores from data already present in ExperimentLab,
        TaskOutcomeRecorder, DecisionAuditTrail and WorldModel:

        * **AutonomyScore** — weighted blend of capability coverage, handoff
          rate, unresolved ratio, permission request rate, resume success rate.
        * **ResilienceScore** — fallback chain coverage, worker diversity,
          checkpoint coverage.
        * **CalibrationError** — mean |estimated_confidence − actual_success|.
        * **BlindSpotRatio** — unverified findings / total findings.

        If there is insufficient data (< 3 runs) the method returns an
        UNRESOLVED finding instead of guessing.
        """
        findings: list[SelfExaminationFinding] = []

        total_runs = len(recent_runs)
        total_experiments = len(experiment_runs)
        total_sessions = len(adaptive_sessions)

        if total_runs < 3 and total_experiments < 3 and total_sessions < 3:
            findings.append(SelfExaminationFinding(
                category='autonomy_index_insufficient_data',
                title='UniversalAutonomyIndex: datos insuficientes',
                summary=(
                    f'Solo hay {total_runs} runs, {total_experiments} experimentos '
                    f'y {total_sessions} sesiones adaptivas. Se necesitan al menos '
                    f'3 en algun eje para calcular metricas confiables.'
                ),
                severity=IssueSeverity.LOW,
                confidence=0.95,
                recommendation=(
                    'Ejecutar mas tareas para acumular datos de rendimiento. '
                    'Las metricas se calcularan automaticamente cuando haya '
                    'suficiente evidencia.'
                ),
                source_refs=['OperationalSelfExaminationService._universal_autonomy_index_findings'],
                status='unresolved',
                unresolved_fields=['autonomy_score', 'resilience_score',
                                   'calibration_error', 'blind_spot_ratio'],
                metadata={'total_runs': total_runs,
                          'total_experiments': total_experiments,
                          'total_sessions': total_sessions},
            ))
            return findings

        # -- AutonomyScore components --

        # 1. capability_coverage: successful runs / total runs
        successful_runs = sum(
            1 for r in recent_runs if r.status == RunStatus.SUCCESS
        )
        capability_coverage = (
            successful_runs / total_runs if total_runs > 0 else 0.0
        )

        # 2. handoff_required_rate: sessions that needed human intervention
        handoff_count = 0
        for sess in adaptive_sessions:
            status = getattr(sess, 'status', None)
            if status is None and isinstance(sess, dict):
                status = sess.get('status', '')
            status_str = str(status.value if hasattr(status, 'value') else status)
            if status_str in ('waiting_approval', 'need_info', 'aborted'):
                handoff_count += 1
        handoff_required_rate = (
            handoff_count / total_sessions if total_sessions > 0 else 0.0
        )

        # 3. unresolved_ratio: from WorldModel + current findings
        total_fields = max(len(world.tool_live_status) + len(world.permission_gates), 1)
        unresolved_count = len(world.unresolved_fields)
        unresolved_ratio = unresolved_count / total_fields

        # 4. permission_request_rate: permission gates as fraction of actions
        total_gates = len(world.permission_gates)
        total_actions = max(total_runs + total_sessions, 1)
        permission_request_rate = min(total_gates / total_actions, 1.0)

        # 5. resume_success_rate: sessions resumed vs interrupted
        interrupted_count = 0
        resumed_count = 0
        for sess in adaptive_sessions:
            md = getattr(sess, 'metadata', {})
            if isinstance(sess, dict):
                md = sess.get('metadata', {})
            if md.get('resumed_from') or md.get('resume_hint_id'):
                resumed_count += 1
            status = getattr(sess, 'status', None)
            if status is None and isinstance(sess, dict):
                status = sess.get('status', '')
            status_str = str(status.value if hasattr(status, 'value') else status)
            if status_str in ('aborted', 'failed'):
                interrupted_count += 1
        resume_success_rate = (
            resumed_count / max(interrupted_count, 1)
            if interrupted_count > 0 else 1.0
        )
        resume_success_rate = min(resume_success_rate, 1.0)

        autonomy_score = (
            0.30 * capability_coverage
            + 0.25 * (1 - handoff_required_rate)
            + 0.20 * (1 - unresolved_ratio)
            + 0.15 * (1 - permission_request_rate)
            + 0.10 * resume_success_rate
        )

        # -- ResilienceScore components --

        # fallback_chain_coverage: providers with fallbacks
        fallback_count = 0
        tool_count = max(len(world.tool_live_status), 1)
        for tool in world.tool_live_status:
            if getattr(tool, 'metadata', None):
                meta = tool.metadata if isinstance(tool.metadata, dict) else {}
                if meta.get('fallback_available') or meta.get('fallback_provider'):
                    fallback_count += 1
        fallback_chain_coverage = fallback_count / tool_count

        # worker_diversity: unique assistant_kind values used in experiments
        unique_assistants: set[str] = set()
        for exp in experiment_runs:
            if exp.assistant_kind:
                unique_assistants.add(exp.assistant_kind)
        worker_diversity = min(len(unique_assistants) / max(tool_count, 3), 1.0)

        # checkpoint_coverage: sessions with resume hints / total sessions
        sessions_with_checkpoint = 0
        for sess in adaptive_sessions:
            md = getattr(sess, 'metadata', {})
            if isinstance(sess, dict):
                md = sess.get('metadata', {})
            if md.get('resume_hint_id') or md.get('checkpoint_saved'):
                sessions_with_checkpoint += 1
        checkpoint_coverage = (
            sessions_with_checkpoint / total_sessions
            if total_sessions > 0 else 0.0
        )

        resilience_score = (
            0.35 * fallback_chain_coverage
            + 0.35 * worker_diversity
            + 0.30 * checkpoint_coverage
        )

        # -- CalibrationError --
        # mean |estimated_confidence - actual_success| per experiment
        calibration_diffs: list[float] = []
        for exp in experiment_runs:
            # ExperimentMetric uses ``precision`` as the estimated score;
            # metadata may carry an explicit ``confidence`` override.
            confidence = 0.0
            if exp.metadata:
                confidence = float(exp.metadata.get('confidence', 0.0))
            if confidence <= 0 and exp.metrics:
                confidence = exp.metrics.precision
            actual = 1.0 if exp.success else 0.0
            if confidence > 0:
                calibration_diffs.append(abs(confidence - actual))
        calibration_error = (
            sum(calibration_diffs) / len(calibration_diffs)
            if calibration_diffs else 0.0
        )

        # -- BlindSpotRatio --
        total_findings = max(len(findings_so_far), 1)
        unverified_findings = sum(
            1 for f in findings_so_far
            if f.status in ('observed', 'unresolved')
               and f.confidence < 0.7
        )
        blind_spot_ratio = unverified_findings / total_findings

        # -- Determine overall severity --
        if autonomy_score >= 0.80 and resilience_score >= 0.75:
            severity = IssueSeverity.LOW
            verdict = 'SALUDABLE'
        elif autonomy_score >= 0.60:
            severity = IssueSeverity.MEDIUM
            verdict = 'PARCIAL'
        else:
            severity = IssueSeverity.HIGH
            verdict = 'INSUFICIENTE'

        metrics = {
            'autonomy_score': round(autonomy_score, 3),
            'resilience_score': round(resilience_score, 3),
            'calibration_error': round(calibration_error, 3),
            'blind_spot_ratio': round(blind_spot_ratio, 3),
            'verdict': verdict,
            'components': {
                'capability_coverage': round(capability_coverage, 3),
                'handoff_required_rate': round(handoff_required_rate, 3),
                'unresolved_ratio': round(unresolved_ratio, 3),
                'permission_request_rate': round(permission_request_rate, 3),
                'resume_success_rate': round(resume_success_rate, 3),
                'fallback_chain_coverage': round(fallback_chain_coverage, 3),
                'worker_diversity': round(worker_diversity, 3),
                'checkpoint_coverage': round(checkpoint_coverage, 3),
            },
            'sample_sizes': {
                'runs': total_runs,
                'experiments': total_experiments,
                'sessions': total_sessions,
                'calibration_samples': len(calibration_diffs),
            },
        }

        # Build recommendation based on weakest component
        weakest_component = ''
        weakest_value = 1.0
        for comp_name, comp_val in metrics['components'].items():
            effective = comp_val
            if comp_name in ('handoff_required_rate', 'unresolved_ratio',
                             'permission_request_rate'):
                effective = 1 - comp_val
            if effective < weakest_value:
                weakest_value = effective
                weakest_component = comp_name

        recommendation_map = {
            'capability_coverage': (
                'Mejorar tasa de exito de tareas. Revisar rutas que fallan '
                'frecuentemente en ExperimentLab y rotar a proveedores mas confiables.'
            ),
            'handoff_required_rate': (
                'Reducir intervenciones humanas. Verificar que AutonomyGovernancePolicy '
                'no bloquee rutas innecesariamente y que los permisos esten configurados.'
            ),
            'unresolved_ratio': (
                'Resolver campos UNRESOLVED en WorldModel. Ejecutar escaneo de '
                'cuentas y verificar estado de herramientas externas.'
            ),
            'permission_request_rate': (
                'Reducir permisos pendientes. Configurar permission_gates para '
                'herramientas de uso frecuente.'
            ),
            'resume_success_rate': (
                'Mejorar reanudacion de tareas interrumpidas. Verificar que '
                'AutonomyCycleService.save_resume_hint() se llame correctamente.'
            ),
            'fallback_chain_coverage': (
                'Agregar proveedores de respaldo. Configurar fallback_provider '
                'para herramientas criticas en el WorldModel.'
            ),
            'worker_diversity': (
                'Diversificar asistentes utilizados. Probar rutas alternativas '
                'en ExperimentLab para reducir dependencia de un solo proveedor.'
            ),
            'checkpoint_coverage': (
                'Mejorar checkpointing de sesiones. Verificar que las tareas '
                'largas guarden resume hints antes de completar.'
            ),
        }

        recommendation = recommendation_map.get(weakest_component, (
            'Revisar todas las metricas del indice de autonomia para '
            'identificar areas de mejora prioritarias.'
        ))

        findings.append(SelfExaminationFinding(
            category='universal_autonomy_index',
            title=f'UniversalAutonomyIndex: {verdict} (autonomia={autonomy_score:.0%})',
            summary=(
                f'AutonomyScore={autonomy_score:.0%} (objetivo >80%), '
                f'ResilienceScore={resilience_score:.0%} (objetivo >75%), '
                f'CalibrationError={calibration_error:.2f} (objetivo <0.10), '
                f'BlindSpotRatio={blind_spot_ratio:.0%} (objetivo <30%). '
                f'Componente mas debil: {weakest_component} ({weakest_value:.0%}).'
            ),
            severity=severity,
            confidence=0.88,
            recommendation=recommendation,
            source_refs=[
                'ExperimentLab', 'TaskOutcomeRecorder',
                'DecisionAuditTrail', 'WorldModelSnapshot',
                'PlatformPendingQueue',
            ],
            metadata=metrics,
        ))

        # Additional finding if calibration error is too high
        if calibration_error > 0.10 and len(calibration_diffs) >= 5:
            findings.append(SelfExaminationFinding(
                category='autonomy_calibration_drift',
                title=f'Calibracion desviada: error={calibration_error:.2f}',
                summary=(
                    f'La confianza estimada difiere del resultado real por '
                    f'{calibration_error:.2f} en promedio sobre '
                    f'{len(calibration_diffs)} experimentos. El sistema '
                    f'sobreestima o subestima sus capacidades.'
                ),
                severity=IssueSeverity.MEDIUM,
                confidence=0.82,
                recommendation=(
                    'Revisar el AdaptiveWeightLayer para ajustar los pesos '
                    'de confianza. Los experimentos recientes muestran que '
                    'las predicciones no coinciden con los resultados reales.'
                ),
                source_refs=['ExperimentLab', 'AdaptiveWeightLayer'],
                metadata={
                    'calibration_error': round(calibration_error, 3),
                    'sample_count': len(calibration_diffs),
                },
            ))

        return findings

    # ------------------------------------------------------------------
    # Autonomy bridge: OSES findings → PlatformPendingQueue
    # ------------------------------------------------------------------

    # Categories that should generate structured pending tasks when they
    # appear as HIGH or CRITICAL findings.  Each maps to a human-readable
    # action template.
    _FINDING_TO_PENDING_CATEGORIES: dict[str, str] = {
        'startup_populate_ui_freeze': (
            'Optimizar fases de populate_ui para reducir bloqueo del main thread.'
        ),
        'startup_degradation': (
            'Investigar regresion de startup y aplicar fix.'
        ),
        'startup_memory_spike': (
            'Reducir consumo de memoria durante el arranque.'
        ),
        'recurring_failure': (
            'Analizar patron de fallos recurrentes y aplicar correccion.'
        ),
        'cloud_reasoning_degradation': (
            'Evaluar health de proveedores cloud y ajustar fallback.'
        ),
        'windows_integration_gaps': (
            'Implementar capacidades Windows faltantes de la cola de pendientes.'
        ),
        'temporal_regression': (
            'Investigar regresion de latencia detectada por anomalia temporal.'
        ),
    }

    def _bridge_findings_to_pending_queue(
        self,
        findings: list[SelfExaminationFinding],
    ) -> None:
        """Convert HIGH/CRITICAL findings into PlatformPendingTask entries.

        Only creates tasks for categories listed in
        ``_FINDING_TO_PENDING_CATEGORIES``.  Idempotent: existing tasks
        with the same id are updated, not duplicated.
        """
        try:
            from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
            from iabv_v15.domain.models import PlatformPendingTask, PendingTaskStatus
        except Exception:
            return

        queue = self._get_pending_queue()
        if queue is None:
            return

        for finding in findings:
            if finding.category not in self._FINDING_TO_PENDING_CATEGORIES:
                continue
            if finding.severity not in (IssueSeverity.HIGH, IssueSeverity.CRITICAL):
                continue
            task_id = f'oses_{finding.category}'
            next_action = self._FINDING_TO_PENDING_CATEGORIES[finding.category]
            try:
                existing = queue.get(task_id)
                if existing is not None and existing.status == PendingTaskStatus.COMPLETED:
                    continue
                priority = 'critical' if finding.severity == IssueSeverity.CRITICAL else 'high'
                task = PlatformPendingTask(
                    id=task_id,
                    title=finding.title,
                    description=finding.summary or '',
                    reason=f'OSES finding: {finding.category}',
                    priority=priority,
                    next_action=next_action,
                    status=PendingTaskStatus.PENDING,
                    category='oses_finding',
                    resume_hint=finding.recommendation or '',
                    metadata={
                        'source': 'oses_bridge',
                        'severity': finding.severity.value,
                        'confidence': finding.confidence,
                    },
                )
                queue.upsert(task)
            except Exception:
                logger.debug('oses: failed to bridge finding %s to queue', finding.category)

    def _get_pending_queue(self) -> Any | None:
        """Resolve PlatformPendingQueue from data dir (lazy, cached)."""
        cached = getattr(self, '_pending_queue_cache', None)
        if cached is not None:
            return cached
        try:
            from iabv_v15.services.evolution.platform_pending_queue import PlatformPendingQueue
            data_dir = Path(self.workspace_root) / 'data' / 'evolution'
            if not data_dir.exists():
                return None
            queue = PlatformPendingQueue(evolution_dir=str(data_dir))
            self._pending_queue_cache = queue
            return queue
        except Exception:
            return None

    def _environment_model(self) -> Any | None:
        """Read EnvironmentSelfModel from world_model_service or direct."""
        wms = self.world_model_service
        if wms is not None:
            try:
                snap = wms.current_model()
                env = getattr(snap, 'environment', None)
                if env is not None:
                    return env
            except Exception:
                pass
            try:
                esas = getattr(wms, 'environment_self_awareness_service', None)
                if esas is not None:
                    return esas.current_model()
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Task-packet → pending issues (materialization)
    # ------------------------------------------------------------------

    def _materialize_task_packet_issues(
        self,
        findings: list[SelfExaminationFinding],
    ) -> None:
        svc = self.evolution_review_service
        if svc is None:
            return
        tp_findings = [
            f for f in findings
            if f.category.startswith('task_packet_')
        ]
        if not tp_findings:
            return
        try:
            svc.materialize_task_packet_issues(tp_findings)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug(
                'oses: materialize_task_packet_issues failed: %s', exc,
            )

    # ── P0.5: Shared Reality Learning ──────────────────────────────
    def _external_failure_context_findings(self) -> list[SelfExaminationFinding]:
        """Detect repeated follow-up loops after external security blocks."""
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            recent_lines: deque[str] = deque(maxlen=5000)
            with audit_path.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    recent_lines.append(line)
            for line in reversed(recent_lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                kind = str(event.get('kind') or '')
                if kind not in {
                    'external_failure_followup_answered',
                    'security_verification_user_handoff_window',
                    'dispatch_terminal',
                }:
                    continue
                events.append({'kind': kind, **dict(event.get('data') or {})})
                if len(events) >= 80:
                    break
            events.reverse()
        except Exception:
            return []
        if not events:
            return []

        security_followups = [
            e for e in events
            if e.get('kind') == 'external_failure_followup_answered'
            and any(
                marker in ' '.join(
                    str(e.get(key) or '')
                    for key in ('previous_meta', 'user_message', 'outcome')
                ).lower()
                for marker in (
                    'blocked_by_security_verification',
                    'browser_security_verification',
                    'verificacion',
                    'verificación',
                    'captcha',
                )
            )
        ]
        handoff_windows = [
            e for e in events
            if e.get('kind') == 'security_verification_user_handoff_window'
        ]
        profile_mismatch_handoffs = [
            e for e in handoff_windows
            if bool(e.get('profile_mismatch_detected'))
            or str(e.get('mode') or '').strip().lower() in {'visible_user_browser', 'default_user_browser'}
        ]
        local_timeouts = [
            e for e in events
            if e.get('kind') == 'dispatch_terminal'
            and str(e.get('task_name') or '') == 'chat'
            and 'watchdog' in str(e.get('reason') or '').lower()
        ]
        findings: list[SelfExaminationFinding] = []
        if len(security_followups) >= 2 or (security_followups and local_timeouts):
            last = security_followups[-1] if security_followups else local_timeouts[-1]
            findings.append(SelfExaminationFinding(
                category='external_failure_context_continuity_gap',
                severity=IssueSeverity.HIGH,
                title='Continuidad causal de fallo externo requiere ajuste',
                summary=(
                    f'Se detectaron {len(security_followups)} follow-ups sobre bloqueos '
                    f'de seguridad externa y {len(local_timeouts)} timeout(s) locales recientes. '
                    'Esto indica que el sistema debe preservar el contexto causal del fallo '
                    'antes de elegir un nuevo camino de razonamiento.'
                ),
                confidence=0.9,
                recommendation=(
                    'Mantener el guard de follow-up externo antes del chat local pesado, '
                    'abrir una ventana visible cuando el usuario ofrece ayuda, y retestar '
                    'solo despues de una confirmacion explicita como "ya lo hice".'
                ),
                evidence_refs=[
                    f'security_followups={len(security_followups)}',
                    f'local_watchdog_timeouts={len(local_timeouts)}',
                    f'handoff_windows={len(handoff_windows)}',
                ],
                source_refs=['runtime_audit', 'external_failure_followup_answered'],
                metadata={
                    'pattern': 'external_failure_context_continuity_gap',
                    'frequency': len(security_followups),
                    'handoff_window_attempts': len(handoff_windows),
                    'last_user_message': str(last.get('user_message') or '')[:240],
                    'recommended_action': 'causal_failure_context_before_route_selection',
                    'priority': 'high',
                },
            ))
        if len(handoff_windows) >= 2 and not any(e.get('opened') for e in handoff_windows):
            findings.append(SelfExaminationFinding(
                category='security_verification_window_open_failed_repeated',
                severity=IssueSeverity.MEDIUM,
                title='Ventana visible de verificacion no pudo abrirse repetidamente',
                summary=(
                    f'IABV intento abrir una ventana visible de verificacion {len(handoff_windows)} veces, '
                    'pero ningun intento reporto opened=true.'
                ),
                confidence=0.85,
                recommendation=(
                    'Revisar deteccion de Chrome/Edge y fallback de navegador por defecto para que '
                    'el usuario pueda completar verificaciones de seguridad en la sesion correcta.'
                ),
                evidence_refs=[f'handoff_window_attempts={len(handoff_windows)}'],
                source_refs=['runtime_audit', 'security_verification_user_handoff_window'],
                metadata={
                    'pattern': 'security_verification_window_open_failed_repeated',
                    'frequency': len(handoff_windows),
                    'recommended_action': 'repair_visible_security_handoff_launcher',
                    'priority': 'medium',
                },
            ))
        if profile_mismatch_handoffs:
            findings.append(SelfExaminationFinding(
                category='external_assistant_profile_mismatch',
                severity=IssueSeverity.HIGH,
                title='Sesion autenticada del usuario no coincide con el perfil usado por IABV',
                summary=(
                    'El usuario indico que ChatGPT funcionaba o estaba autenticado en su navegador, '
                    'mientras IABV venia intentando una sesion aislada bloqueada por verificacion. '
                    'Esto es un desajuste de realidad compartida por perfil, no una falta de razonamiento local.'
                ),
                confidence=0.91,
                recommendation=(
                    'Cuando aparezca este patron, no repetir el perfil aislado. Usar handoff/manual en el '
                    'navegador del usuario o una ruta CDP gobernada con permiso explicito de observacion.'
                ),
                evidence_refs=[
                    f'profile_mismatch_handoffs={len(profile_mismatch_handoffs)}',
                    f'handoff_windows={len(handoff_windows)}',
                ],
                source_refs=['runtime_audit', 'security_verification_user_handoff_window'],
                metadata={
                    'pattern': 'external_assistant_profile_mismatch',
                    'frequency': len(profile_mismatch_handoffs),
                    'recommended_action': 'prefer_user_browser_manual_or_governed_cdp',
                    'priority': 'high',
                },
            ))
        return findings

    def _external_failure_followup_misrouted_findings(self) -> list[SelfExaminationFinding]:
        """Detect blocked external consultation followed by local chat.

        OSES only observes and reports. It does not dispatch, retry, or alter
        routing. The finding exists so this exact live failure becomes part of
        the metacognitive loop instead of remaining a one-off UI anecdote.
        """
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        try:
            recent_lines: deque[str] = deque(maxlen=1000)
            with audit_path.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    recent_lines.append(line)
        except OSError:
            return []

        blocked_states = {
            'blocked_by_resource_pressure',
            'blocked_by_security_verification',
            'blocked_by_permission',
            'failed_with_actionable_reason',
            'timeout',
            'needs_human_handoff',
        }
        misroute_pairs: list[dict[str, str]] = []
        last_external_block: dict[str, str] | None = None
        for line in recent_lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            kind = str(event.get('kind') or '')
            data = dict(event.get('data') or {})
            if kind == 'dispatch_terminal':
                task = str(data.get('task_name') or '')
                terminal = str(data.get('terminal_state') or '')
                if task == 'external_consultation' and terminal in blocked_states:
                    last_external_block = {
                        'dispatch_id': str(data.get('dispatch_id') or ''),
                        'terminal_state': terminal,
                        'interaction_id': str(data.get('interaction_id') or ''),
                    }
                continue
            if kind != 'dispatch_started':
                continue
            task = str(data.get('task_name') or '')
            if task == 'chat' and last_external_block is not None:
                misroute_pairs.append({
                    'external_dispatch_id': last_external_block.get('dispatch_id', ''),
                    'external_terminal_state': last_external_block.get('terminal_state', ''),
                    'external_interaction_id': last_external_block.get('interaction_id', ''),
                    'local_dispatch_id': str(data.get('dispatch_id') or ''),
                    'local_interaction_id': str(data.get('interaction_id') or ''),
                    'user_goal_excerpt': str(data.get('user_goal_excerpt') or '')[:160],
                })
                last_external_block = None
            elif task != 'chat':
                last_external_block = None

        if len(misroute_pairs) < 2:
            return []
        return [SelfExaminationFinding(
            category='external_failure_followup_misrouted_to_local',
            title=f'External consultation blocked then local chat dispatched ({len(misroute_pairs)}x)',
            summary=(
                f'{len(misroute_pairs)} time(s) an external_consultation was blocked or failed and '
                'the next message fell to local chat inference instead of the external-failure follow-up path. '
                'This wastes CPU, can freeze the UI, and loses the causal context of the blocked tool.'
            ),
            severity=IssueSeverity.HIGH,
            confidence=0.90,
            recommendation=(
                'Keep _try_handle_external_failure_followup before local dispatch and include deictic '
                'follow-ups such as "solucionar eso" and typo variants.'
            ),
            evidence_refs=[p.get('external_dispatch_id', '')[:12] for p in misroute_pairs[:5]],
            source_refs=['runtime_audit'],
            metadata={
                'pattern': 'external_failure_followup_misrouted_to_local',
                'count': len(misroute_pairs),
                'pairs': misroute_pairs[:5],
            },
        )]

    def _shared_reality_handoff_findings(self) -> list[SelfExaminationFinding]:
        """Detect repeated visual-mismatch patterns from ``shared_reality_handoff``
        events in ``runtime_audit.jsonl``.

        Patterns detected:
        - ``repeated_visual_mismatch``: ≥2 events where capture was useless
        - ``user_browser_differs_from_iabv_session``: ≥2 events where browser
          label indicates isolated/controlled session
        - ``black_capture_repeated``: ≥2 events with blank_probability ≥ 0.8
        - ``user_needed_to_explain_same_gap``: ≥2 events with a user_claim
          (user had to tell IABV "it works for me")

        A single isolated event does NOT produce a finding — only repetition
        indicates a pattern worth surfacing.
        """
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            recent_lines: deque[str] = deque(maxlen=5000)
            with audit_path.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    recent_lines.append(line)
            # Read in reverse to collect the 50 most RECENT handoff events,
            # then restore chronological order for last_case accuracy.
            for line in reversed(recent_lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get('kind') != 'shared_reality_handoff':
                    continue
                events.append(dict(event.get('data') or event))
                if len(events) >= 50:
                    break
            events.reverse()  # restore chronological order
        except Exception:
            return []
        if len(events) < 2:
            return []
        findings: list[SelfExaminationFinding] = []

        # Pattern 1: repeated_visual_mismatch
        useless_captures = [
            e for e in events
            if not e.get('capture_useful', True)
        ]
        if len(useless_captures) >= 2:
            last = useless_captures[-1]
            findings.append(SelfExaminationFinding(
                category='repeated_visual_mismatch',
                severity=IssueSeverity.HIGH,
                title=f'Captura visual inútil repetida: {len(useless_captures)} eventos',
                summary=(
                    f'{len(useless_captures)} consultas externas capturaron evidencia '
                    f'inútil (capture_useful=false). Último caso: '
                    f'{last.get("assistant_kind", "?")} con ventana '
                    f'"{last.get("target_window_title", "?")}".'
                ),
                confidence=0.9,
                recommendation=(
                    'Mejorar selección/restauración automática de ventana objetivo '
                    'antes de captura. Considerar selector de ventana visible o '
                    'restauración automática de ventanas minimizadas.'
                ),
                evidence_refs=[
                    f'shared_reality_handoff_count={len(useless_captures)}',
                ],
                source_refs=['runtime_audit', 'shared_reality_handoff'],
                metadata={
                    'pattern': 'repeated_visual_mismatch',
                    'frequency': len(useless_captures),
                    'last_case': {
                        'assistant_kind': last.get('assistant_kind'),
                        'target_window_title': last.get('target_window_title'),
                        'capture_useful': last.get('capture_useful'),
                    },
                    'recommended_action': 'auto_restore_or_select_window',
                    'priority': 'high',
                },
            ))

        # Pattern 2: user_browser_differs_from_iabv_session
        _BROWSER_KW = ('aislada', 'controlada', 'chrome for testing')
        def _has_isolated_signal(e: dict[str, Any]) -> bool:
            for field in ('mismatch_reason', 'browser_label',
                          'browser_profile', 'selected_browser_or_profile'):
                val = str(e.get(field, '')).lower()
                if any(kw in val for kw in _BROWSER_KW):
                    return True
            return False
        diff_session = [e for e in events if _has_isolated_signal(e)]
        if len(diff_session) >= 2:
            last = diff_session[-1]
            findings.append(SelfExaminationFinding(
                category='user_browser_differs_from_iabv_session',
                severity=IssueSeverity.MEDIUM,
                title=f'Diferencia navegador usuario/IABV repetida: {len(diff_session)} eventos',
                summary=(
                    f'En {len(diff_session)} consultas, IABV usó una sesión aislada/controlada '
                    f'diferente al navegador del usuario. Esto genera confusión recurrente.'
                ),
                confidence=0.85,
                recommendation=(
                    'Implementar selector de sesión/navegador que permita al usuario '
                    'indicar qué navegador usar, o detectar automáticamente el navegador '
                    'visible del usuario.'
                ),
                evidence_refs=[
                    f'browser_diff_count={len(diff_session)}',
                ],
                source_refs=['runtime_audit', 'shared_reality_handoff'],
                metadata={
                    'pattern': 'user_browser_differs_from_iabv_session',
                    'frequency': len(diff_session),
                    'last_case': {
                        'assistant_kind': last.get('assistant_kind'),
                        'mismatch_reason': last.get('mismatch_reason'),
                    },
                    'recommended_action': 'browser_session_selector',
                    'priority': 'medium',
                },
            ))

        # Pattern 3: black_capture_repeated
        black_captures = [
            e for e in events
            if float(e.get('blank_probability', 0) or 0) >= 0.8
            or (isinstance(e.get('capture_quality'), dict)
                and float(e['capture_quality'].get('blank_probability', 0) or 0) >= 0.8)
        ]
        if len(black_captures) >= 2:
            last = black_captures[-1]
            bp = (
                last.get('blank_probability')
                or (last.get('capture_quality') or {}).get('blank_probability', '?')
            )
            findings.append(SelfExaminationFinding(
                category='black_capture_repeated',
                severity=IssueSeverity.HIGH,
                title=f'Captura negra repetida: {len(black_captures)} eventos',
                summary=(
                    f'{len(black_captures)} capturas con blank_probability ≥ 0.8. '
                    f'Último: blank_probability={bp}. Las capturas negras indican '
                    f'ventanas offscreen/minimizadas no detectadas a tiempo.'
                ),
                confidence=0.9,
                recommendation=(
                    'Validar estado de ventana (rect, minimizada) ANTES de capturar. '
                    'Si rect indica offscreen, restaurar o pedir selección antes de '
                    'intentar captura.'
                ),
                evidence_refs=[
                    f'black_capture_count={len(black_captures)}',
                ],
                source_refs=['runtime_audit', 'shared_reality_handoff'],
                metadata={
                    'pattern': 'black_capture_repeated',
                    'frequency': len(black_captures),
                    'last_blank_probability': bp,
                    'recommended_action': 'pre_capture_window_validation',
                    'priority': 'high',
                },
            ))

        # Pattern 4: user_needed_to_explain_same_gap
        user_explained = [
            e for e in events
            if e.get('user_claim') and str(e['user_claim']) not in ('', 'unknown')
        ]
        if len(user_explained) >= 2:
            last = user_explained[-1]
            findings.append(SelfExaminationFinding(
                category='user_needed_to_explain_same_gap',
                severity=IssueSeverity.HIGH,
                title=f'Usuario explicó el mismo gap {len(user_explained)} veces',
                summary=(
                    f'El usuario tuvo que explicar la diferencia entre su vista y la de IABV '
                    f'{len(user_explained)} veces. Último claim: '
                    f'"{str(last.get("user_claim", ""))[:80]}". '
                    f'IABV debería anticipar esta explicación automáticamente.'
                ),
                confidence=0.9,
                recommendation=(
                    'Mejorar la explicación proactiva antes de que el usuario pregunte. '
                    'Incluir "Tu vista vs Vista de IABV" en el primer mensaje de fallo, '
                    'no solo como respuesta al claim del usuario.'
                ),
                evidence_refs=[
                    f'user_explain_count={len(user_explained)}',
                ],
                source_refs=['runtime_audit', 'shared_reality_handoff'],
                metadata={
                    'pattern': 'user_needed_to_explain_same_gap',
                    'frequency': len(user_explained),
                    'last_case': {
                        'user_claim': last.get('user_claim'),
                        'assistant_kind': last.get('assistant_kind'),
                    },
                    'recommended_action': 'proactive_causal_explanation',
                    'priority': 'high',
                },
            ))

        return findings

    def _visual_remediation_findings(self) -> list[SelfExaminationFinding]:
        """Detect repeated patterns from ``visual_remediation_attempted``
        events in ``runtime_audit.jsonl``.

        Patterns detected (each requires ≥2 events):
        - ``repeated_restore_without_recapture``: action was taken but
          capture_useful_after is None (no recapture API).
        - ``repeated_win32_restore_unavailable``: Win32 API not available.
        - ``repeated_user_selection_needed``: user had to select window.
        - ``repeated_restore_attempted``: restore was attempted — measure
          whether subsequent consultations improved.
        """
        workspace = getattr(self, 'workspace_root', None)
        if not workspace:
            return []
        audit_path = Path(str(workspace)) / 'data' / 'logs' / 'runtime_audit.jsonl'
        if not audit_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            recent_lines: deque[str] = deque(maxlen=5000)
            with audit_path.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    recent_lines.append(line)
            for line in reversed(recent_lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get('kind') != 'visual_remediation_attempted':
                    continue
                events.append(dict(event.get('data') or event))
                if len(events) >= 50:
                    break
            events.reverse()
        except Exception:
            return []
        if len(events) < 2:
            return []
        findings: list[SelfExaminationFinding] = []

        # Pattern 1: repeated_restore_without_recapture
        no_recapture = [
            e for e in events
            if e.get('action_taken', 'none') != 'none'
            and e.get('capture_useful_after') is None
        ]
        if len(no_recapture) >= 2:
            last = no_recapture[-1]
            findings.append(SelfExaminationFinding(
                category='repeated_restore_without_recapture',
                severity=IssueSeverity.HIGH,
                title=f'Restauración sin recaptura: {len(no_recapture)} eventos',
                summary=(
                    f'{len(no_recapture)} remediaciones ejecutaron restore pero '
                    f'capture_useful_after=None (sin recaptura). '
                    f'Último: {last.get("assistant_kind", "?")}.'
                ),
                confidence=0.9,
                recommendation=(
                    'Implementar recaptura real después de restaurar ventana, '
                    'o reintento automático controlado de la consulta externa.'
                ),
                evidence_refs=[
                    f'restore_without_recapture_count={len(no_recapture)}',
                ],
                source_refs=['runtime_audit', 'visual_remediation_attempted'],
                metadata={
                    'pattern': 'repeated_restore_without_recapture',
                    'frequency': len(no_recapture),
                    'last_case': {
                        'assistant_kind': last.get('assistant_kind'),
                        'action_taken': last.get('action_taken'),
                    },
                    'recommended_action': 'implement_recapture_after_restore',
                    'priority': 'high',
                },
            ))

        # Pattern 2: repeated_win32_restore_unavailable
        win32_unavailable = [
            e for e in events
            if (
                str(e.get('remediation_detail_code', '')).lower()
                == 'win32_api_not_available'
                or (
                    'win32' in str(e.get('detail', '')).lower()
                    and 'not available' in str(e.get('detail', '')).lower()
                )
            )
        ]
        if len(win32_unavailable) >= 2:
            findings.append(SelfExaminationFinding(
                category='repeated_win32_restore_unavailable',
                severity=IssueSeverity.MEDIUM,
                title=f'Win32 restore no disponible: {len(win32_unavailable)} eventos',
                summary=(
                    f'{len(win32_unavailable)} intentos de restauración fallaron '
                    f'porque Win32 API no estaba disponible. Esto indica ejecución '
                    f'fuera de Windows desktop.'
                ),
                confidence=0.85,
                recommendation=(
                    'Marcar limitación de entorno. La restauración automática '
                    'solo funciona en Windows desktop. Considerar mecanismo '
                    'alternativo para otros entornos.'
                ),
                evidence_refs=[
                    f'win32_unavailable_count={len(win32_unavailable)}',
                ],
                source_refs=['runtime_audit', 'visual_remediation_attempted'],
                metadata={
                    'pattern': 'repeated_win32_restore_unavailable',
                    'frequency': len(win32_unavailable),
                    'recommended_action': 'environment_limitation_marker',
                    'priority': 'medium',
                },
            ))

        # Pattern 3: repeated_user_selection_needed
        user_selection = [
            e for e in events
            if e.get('proposed_action') == 'request_user_selection'
        ]
        if len(user_selection) >= 2:
            last = user_selection[-1]
            findings.append(SelfExaminationFinding(
                category='repeated_user_selection_needed',
                severity=IssueSeverity.MEDIUM,
                title=f'Selección de ventana requerida: {len(user_selection)} eventos',
                summary=(
                    f'{len(user_selection)} veces IABV no pudo identificar la ventana '
                    f'objetivo y requirió selección del usuario.'
                ),
                confidence=0.85,
                recommendation=(
                    'Implementar selector visual de ventana/perfil. Permitir '
                    'al usuario pre-configurar qué ventana usar para cada herramienta.'
                ),
                evidence_refs=[
                    f'user_selection_count={len(user_selection)}',
                ],
                source_refs=['runtime_audit', 'visual_remediation_attempted'],
                metadata={
                    'pattern': 'repeated_user_selection_needed',
                    'frequency': len(user_selection),
                    'last_case': {
                        'assistant_kind': last.get('assistant_kind'),
                        'target_window_title': last.get('target_window_title'),
                    },
                    'recommended_action': 'visual_window_selector',
                    'priority': 'medium',
                },
            ))

        # Pattern 4: repeated_restore_attempted
        restore_attempted = [
            e for e in events
            if e.get('action_taken') in (
                'restore_window_by_hwnd', 'restore_and_recapture',
            )
        ]
        if len(restore_attempted) >= 2:
            last = restore_attempted[-1]
            findings.append(SelfExaminationFinding(
                category='repeated_restore_attempted',
                severity=IssueSeverity.LOW,
                title=f'Restauración intentada: {len(restore_attempted)} eventos',
                summary=(
                    f'{len(restore_attempted)} intentos de restaurar ventana vía Win32. '
                    f'Medir si la siguiente consulta mejora después del restore.'
                ),
                confidence=0.7,
                recommendation=(
                    'Correlacionar resultado de restauración con éxito de la '
                    'siguiente consulta externa. Si no mejora, ajustar estrategia.'
                ),
                evidence_refs=[
                    f'restore_attempted_count={len(restore_attempted)}',
                ],
                source_refs=['runtime_audit', 'visual_remediation_attempted'],
                metadata={
                    'pattern': 'repeated_restore_attempted',
                    'frequency': len(restore_attempted),
                    'last_case': {
                        'assistant_kind': last.get('assistant_kind'),
                        'action_taken': last.get('action_taken'),
                        'result_status': last.get('result_status'),
                    },
                    'recommended_action': 'measure_post_restore_improvement',
                    'priority': 'low',
                },
            ))

        return findings


# ---------------------------------------------------------------------------
# Lightweight accessor for functional-gap findings without full service init.
# Used by ``_account_resource_reply`` so the chat response can include gaps.
# ---------------------------------------------------------------------------

def get_functional_gap_summary() -> list[dict[str, str]]:
    """Return functional-gap findings as simple dicts (title + detail).

    Runs only the cheap checks (browser account scan, env vars, Ollama
    tags) without requiring the full OperationalSelfExaminationService
    dependency graph.
    """
    import logging
    import os

    _log = logging.getLogger(__name__)
    gaps: list[dict[str, str]] = []

    # Gap 1 & 2: orphan browser sessions / untracked quotas
    try:
        from iabv_v15.services.account_resource_scanner import (
            scan_browser_accounts,
            scan_browser_sessions,
            verify_account_sessions,
            get_all_quota_status,
        )
        accounts = scan_browser_accounts()
        sessions = scan_browser_sessions()

        session_browsers = {s.get('browser', '') for s in sessions.get('sessions', [])}
        account_browsers = {a.get('browser', '') for a in accounts.get('accounts', [])}
        orphan_browsers = session_browsers - account_browsers
        if orphan_browsers and sessions.get('session_count', 0) > 0:
            gaps.append({
                'title': 'Sesiones sin cuenta asociada',
                'detail': (
                    f'Navegadores con sesiones pero sin cuenta: '
                    f'{", ".join(sorted(orphan_browsers))}.'
                ),
            })

        verified = verify_account_sessions()
        pool_accounts = verified.get('accounts', [])
        active = [a for a in pool_accounts if a.get('tool_count', 0) > 0]
        if active:
            quotas = get_all_quota_status()
            if len(quotas.get('statuses', [])) == 0:
                gaps.append({
                    'title': 'Workers sin rastreo de cuotas',
                    'detail': (
                        f'{len(active)} asistentes tienen sesion activa '
                        f'pero ninguno tiene cuotas rastreadas aun.'
                    ),
                })
    except Exception as exc:
        _log.debug('functional gap scan (browsers) skipped: %s', exc)

    # Gap 3: cloud API keys unused
    try:
        has_openai = bool(os.environ.get('OPENAI_API_KEY'))
        has_anthropic = bool(os.environ.get('ANTHROPIC_API_KEY'))
        if has_openai or has_anthropic:
            from iabv_v15.services.account_resource_scanner import _load_training_examples
            training_count = len(_load_training_examples())
            if training_count == 0:
                cloud_name = 'OpenAI' if has_openai else 'Anthropic'
                gaps.append({
                    'title': f'API {cloud_name} sin uso por clasificador',
                    'detail': (
                        f'Hay una API key de {cloud_name} pero el clasificador '
                        f'dual aun no tiene ejemplos de entrenamiento.'
                    ),
                })
            elif training_count > 0:
                gaps.append({
                    'title': f'Clasificador dual: {training_count} ejemplos acumulados',
                    'detail': (
                        f'El modelo local aprendio de {training_count} '
                        f'clasificaciones de la nube.'
                    ),
                })
    except Exception as exc:
        _log.debug('functional gap scan (cloud) skipped: %s', exc)

    # Gap 4: multiple Ollama models
    try:
        import httpx
        with httpx.Client(timeout=3.0) as client:
            resp = client.get('http://127.0.0.1:11434/api/tags')
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                if len(models) > 1:
                    names = [m.get('name', '?') for m in models[:5]]
                    gaps.append({
                        'title': f'{len(models)} modelos Ollama disponibles',
                        'detail': (
                            f'Modelos: {", ".join(names)}. Se usa solo el default.'
                        ),
                    })
    except Exception:
        pass

    return gaps
