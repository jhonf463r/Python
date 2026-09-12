from __future__ import annotations

from collections import defaultdict
from typing import Any

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ExperimentRun,
    ToolDiscoverySignal,
    ToolEvolutionProposal,
    ToolEvolutionStatus,
    ToolPerformanceSnapshot,
    utc_now,
)
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.services.adaptive.adaptive_weight_layer import AdaptiveWeightLayer


class ToolEvolutionMonitor:
    def __init__(
        self,
        *,
        storage: ArtifactStorage,
        experiment_lab_repository: ExperimentLabRepository,
        adaptive_weight_layer: AdaptiveWeightLayer,
        autonomous_validation_cycle: Any | None = None,
        tool_discovery_service: Any | None = None,
    ) -> None:
        self.storage = storage
        self.experiment_lab_repository = experiment_lab_repository
        self.adaptive_weight_layer = adaptive_weight_layer
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.tool_discovery_service = tool_discovery_service
        self._current_status: ToolEvolutionStatus | None = None
        # Coalescing guard to prevent excessive history file generation
        self._status_build_in_flight: bool = False
        self._last_status_build_time: float = 0.0
        self._STATUS_BUILD_COOLDOWN_S: float = 10.0  # Minimum 10 seconds between builds
        # Lock to prevent race condition in coalescing check
        import threading as _threading
        self._status_build_lock = _threading.Lock()

    def current_status(
        self,
        *,
        refresh: bool = False,
        max_age_seconds: int = 300,
        subject_key: str | None = None,
    ) -> ToolEvolutionStatus:
        import time as _time
        now = _time.time()

        cached = self._current_status
        if cached is None:
            cached = self._load_latest_status()
            self._current_status = cached
        if (
            cached is not None
            and not refresh
            and self._is_fresh(cached, max_age_seconds=max_age_seconds)
            and (not subject_key or subject_key in list((cached.metadata or {}).get('subject_keys') or []))
        ):
            return cached

        # Coalescing guard: two separate concepts
        # 1. IN_FLIGHT EXCLUSION: while a build is in progress, no second build can start
        # 2. COOLDOWN: after a build completes, wait before allowing another build
        # Use lock to prevent race condition between check and set
        with self._status_build_lock:
            # IN_FLIGHT EXCLUSION: if a build is already in progress, always block
            if self._status_build_in_flight:
                # Build in progress, return cached even if stale
                return cached if cached is not None else self._load_latest_status()

            # COOLDOWN: only apply if no build is in flight
            if (now - self._last_status_build_time) < self._STATUS_BUILD_COOLDOWN_S:
                # Too soon since last build completed, return cached
                return cached if cached is not None else self._load_latest_status()

            # Safe to start new build
            self._status_build_in_flight = True
            # Note: _last_status_build_time will be updated on successful completion

        try:
            status = self.build_status(subject_key=subject_key)
            self._current_status = status
            # Update timestamp only on successful completion
            with self._status_build_lock:
                self._last_status_build_time = utc_now()
            return status
        finally:
            # Always reset in-flight flag, even on failure
            with self._status_build_lock:
                self._status_build_in_flight = False

    def build_status(self, *, subject_key: str | None = None, recommendation_limit: int = 8, run_limit: int = 18) -> ToolEvolutionStatus:
        now = utc_now()
        entries = self._subject_entries(subject_key=subject_key, recommendation_limit=recommendation_limit)
        discovery_status = self._current_discovery_status(subject_key=subject_key)
        performance: list[ToolPerformanceSnapshot] = []
        proposals: list[ToolEvolutionProposal] = []
        degraded_subjects: list[str] = []
        subject_summaries: list[str] = []
        seen_proposal_keys: set[str] = set()
        for entry in entries:
            recommendation = entry.get('recommendation')
            resolved_subject_key = str(entry.get('subject_key') or '').strip() or 'general'
            resolved_domain = self._domain_from_value(entry.get('domain'))
            runs = self.experiment_lab_repository.list_runs(
                domain=resolved_domain.value,
                subject_key=resolved_subject_key,
                limit=max(run_limit, 8),
            )
            if not runs:
                continue
            grouped_runs = self._grouped_runs(runs)
            if not grouped_runs:
                continue
            profiles = self.adaptive_weight_layer.suggest(grouped_runs=grouped_runs)
            ranked = self._rank_profiles(grouped_runs=grouped_runs, profiles=profiles)
            subject_performance = self._performance_snapshots(
                domain=resolved_domain,
                subject_key=resolved_subject_key,
                grouped_runs=grouped_runs,
                profiles=profiles,
                ranked=ranked,
            )
            performance.extend(subject_performance[:3])
            if any(item.degraded for item in subject_performance):
                degraded_subjects.append(resolved_subject_key)
            proposal = self._proposal_for_subject(
                recommendation=recommendation if isinstance(recommendation, ExperimentRecommendation) else None,
                domain=resolved_domain,
                subject_key=resolved_subject_key,
                grouped_runs=grouped_runs,
                profiles=profiles,
                ranked=ranked,
            )
            if proposal is not None:
                probe_key = str(proposal.proposal_key or '').strip()
                if probe_key and probe_key not in seen_proposal_keys:
                    proposals.append(proposal)
                    seen_proposal_keys.add(probe_key)
            for discovery_signal in self._discovery_signals_for_subject(
                discovery_status=discovery_status,
                domain=resolved_domain,
                subject_key=resolved_subject_key,
            ):
                discovery_proposal = self._proposal_from_discovery_signal(
                    signal=discovery_signal,
                    recommendation=recommendation if isinstance(recommendation, ExperimentRecommendation) else None,
                )
                if discovery_proposal is None:
                    continue
                probe_key = str(discovery_proposal.proposal_key or '').strip()
                if probe_key and probe_key not in seen_proposal_keys:
                    proposals.append(discovery_proposal)
                    seen_proposal_keys.add(probe_key)
            subject_summaries.append(self._subject_summary(subject_key=resolved_subject_key, ranked=ranked, proposal=proposal))
        active_proposals, decided_proposals, decision_summary, recent_decisions = self._reconcile_proposals(proposals)
        decided_payloads = self._decided_proposal_payloads(
            decided_proposals=decided_proposals,
            decision_entries=recent_decisions,
        )
        unresolved_fields: list[str] = []
        if not entries:
            unresolved_fields.append('UNRESOLVED:tool_evolution_subjects')
        if not performance:
            unresolved_fields.append('UNRESOLVED:tool_evolution_performance')
        validation = self._validation_summary()
        summary = self._summary(
            subject_summaries=subject_summaries,
            proposal_count=len(active_proposals),
            decided_count=len(decided_payloads),
            degraded_count=len(degraded_subjects),
            validation=validation,
        )
        status = ToolEvolutionStatus(
            created_at_utc=now,
            updated_at_utc=now,
            summary=summary,
            performance=performance[:12],
            proposals=active_proposals[:6],
            degraded_subjects=list(dict.fromkeys(degraded_subjects))[:8],
            unresolved_fields=unresolved_fields,
            metadata={
                'subject_keys': [str(entry.get('subject_key') or '').strip() for entry in entries if str(entry.get('subject_key') or '').strip()],
                'proposal_count': len(active_proposals),
                'active_proposal_count': len(active_proposals),
                'decided_proposal_count': len(decided_payloads),
                'degraded_count': len(list(dict.fromkeys(degraded_subjects))),
                'validation_status': str(validation.get('status') or ''),
                'validation_summary': str(validation.get('summary') or ''),
                'active_proposals': [item.model_dump(mode='json') for item in active_proposals[:6]],
                'decided_proposals': list(decided_payloads or [])[:6],
                'decision_log_summary': dict(decision_summary or {}),
                'recent_decisions': list(recent_decisions or [])[:6],
                'discovery_summary': (
                    dict(discovery_status.metadata or {}) if discovery_status is not None else {}
                ),
            },
        )
        markdown = self._render_markdown(status)
        archive_json_rel = f'tool_evolution/history/{status.status_id}.json'
        archive_md_rel = f'tool_evolution/history/{status.status_id}.md'
        latest_json_rel = 'tool_evolution/latest.json'
        latest_md_rel = 'tool_evolution/latest.md'
        self.storage.save_json_atomic(archive_json_rel, status.model_dump(mode='json'))
        self.storage.save_bytes(archive_md_rel, markdown.encode('utf-8'))
        self.storage.save_json_atomic(latest_json_rel, status.model_dump(mode='json'))
        self.storage.save_bytes(latest_md_rel, markdown.encode('utf-8'))
        status = status.model_copy(
            update={
                'package_path': str(self.storage.resolve(latest_json_rel)),
                'markdown_path': str(self.storage.resolve(latest_md_rel)),
                'metadata': {
                    **dict(status.metadata or {}),
                    'archive_json_path': str(self.storage.resolve(archive_json_rel)),
                    'archive_markdown_path': str(self.storage.resolve(archive_md_rel)),
                },
            }
        )
        self.storage.save_json_atomic(latest_json_rel, status.model_dump(mode='json'))
        return status

    def status_summary(self, status: ToolEvolutionStatus | None = None) -> dict[str, Any]:
        resolved = status or self.current_status()
        metadata = dict(resolved.metadata or {})
        decision_summary = dict(metadata.get('decision_log_summary') or {})
        active_proposals = list(metadata.get('active_proposals') or [])
        decided_proposals = list(metadata.get('decided_proposals') or [])
        return {
            'summary': resolved.summary,
            'status_id': resolved.status_id,
            'updated_at_utc': resolved.updated_at_utc.isoformat(),
            'degraded_subjects': list(resolved.degraded_subjects or [])[:6],
            'top_performers': [
                {
                    'subject_key': item.subject_key,
                    'assistant_kind': item.assistant_kind,
                    'route': item.route.value,
                    'weighted_score': round(float(item.weighted_score or 0.0), 4),
                    'degraded': bool(item.degraded),
                }
                for item in list(resolved.performance or [])[:4]
            ],
            'proposals': list(active_proposals or [])[:4],
            'active_proposals': list(active_proposals or [])[:4],
            'decided_proposals': list(decided_proposals or [])[:4],
            'active_proposal_count': int(metadata.get('active_proposal_count') or len(active_proposals)),
            'decided_proposal_count': int(metadata.get('decided_proposal_count') or len(decided_proposals)),
            'winning_by_problem': dict(decision_summary.get('winning_by_problem') or {}),
            'in_validation': list(decision_summary.get('in_validation') or [])[:8],
            'discarded_proposals': [
                item for item in list(decided_proposals or [])[:6] if str(item.get('status') or '') == 'discarded'
            ],
            'recent_decisions': list(metadata.get('recent_decisions') or [])[:6],
            'unresolved_fields': list(resolved.unresolved_fields or []),
            'package_path': resolved.package_path,
            'markdown_path': resolved.markdown_path,
        }

    def _load_latest_status(self) -> ToolEvolutionStatus | None:
        try:
            if not self.storage.exists('tool_evolution/latest.json'):
                return None
            payload = self.storage.load_json('tool_evolution/latest.json')
            return ToolEvolutionStatus.model_validate(payload)
        except Exception:
            return None

    def _is_fresh(self, status: ToolEvolutionStatus, *, max_age_seconds: int) -> bool:
        try:
            age_seconds = (utc_now() - status.updated_at_utc).total_seconds()
        except Exception:
            return False
        return age_seconds <= max_age_seconds

    def _subject_entries(self, *, subject_key: str | None, recommendation_limit: int) -> list[dict[str, Any]]:
        if subject_key:
            recommendation = self.experiment_lab_repository.latest_recommendation(subject_key=subject_key)
            if recommendation is not None:
                return [{'subject_key': subject_key, 'domain': recommendation.domain, 'recommendation': recommendation}]
            runs = self.experiment_lab_repository.list_runs(subject_key=subject_key, limit=1)
            if runs:
                return [{'subject_key': subject_key, 'domain': runs[0].domain, 'recommendation': None}]
            return []
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for recommendation in self.experiment_lab_repository.list_recommendations(limit=recommendation_limit):
            probe = str(recommendation.subject_key or '').strip()
            if not probe or probe in seen or probe.startswith('sandbox:'):
                continue
            seen.add(probe)
            entries.append({'subject_key': probe, 'domain': recommendation.domain, 'recommendation': recommendation})
        if entries:
            return entries
        for run in self.experiment_lab_repository.list_runs(limit=max(recommendation_limit * 3, 18)):
            probe = str(run.subject_key or '').strip()
            if not probe or probe in seen or probe.startswith('sandbox:'):
                continue
            seen.add(probe)
            entries.append({'subject_key': probe, 'domain': run.domain, 'recommendation': None})
            if len(entries) >= recommendation_limit:
                break
        return entries

    def _grouped_runs(self, runs: list[ExperimentRun]) -> dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]]:
        grouped: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]] = defaultdict(list)
        for run in runs:
            key = (
                run.route,
                str(run.assistant_kind or '').strip().lower(),
                str(run.config_signature or '').strip(),
            )
            grouped[key].append(run)
        return grouped

    def _rank_profiles(
        self,
        *,
        grouped_runs: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]],
        profiles: dict[tuple[EvaluationRoute, str, str], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for key, runs in grouped_runs.items():
            route, assistant_kind, config_signature = key
            profile = dict(profiles.get(key) or {})
            ranked.append(
                {
                    'key': key,
                    'route': route,
                    'assistant_kind': assistant_kind,
                    'config_signature': config_signature,
                    'weighted_score': float(profile.get('weighted_score') or 0.0),
                    'average_score': float(profile.get('average_score') or 0.0),
                    'sample_count': int(profile.get('sample_count') or len(runs)),
                    'profile': profile,
                    'runs': list(runs),
                }
            )
        return sorted(
            ranked,
            key=lambda item: (
                float(item.get('weighted_score') or 0.0),
                int(item.get('sample_count') or 0),
                float(item.get('average_score') or 0.0),
            ),
            reverse=True,
        )

    def _performance_snapshots(
        self,
        *,
        domain: ExperimentDomain,
        subject_key: str,
        grouped_runs: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]],
        profiles: dict[tuple[EvaluationRoute, str, str], dict[str, Any]],
        ranked: list[dict[str, Any]],
    ) -> list[ToolPerformanceSnapshot]:
        items: list[ToolPerformanceSnapshot] = []
        comparison_scope_keys = self._comparison_scope_keys(grouped_runs=grouped_runs)
        for row in ranked:
            route, assistant_kind, config_signature = row['key']
            profile = dict(profiles.get(row['key']) or {})
            runs = list(row.get('runs') or [])
            degraded, degradation_reasons = self._degradation(profile)
            items.append(
                ToolPerformanceSnapshot(
                    domain=domain,
                    subject_key=subject_key,
                    route=route,
                    assistant_kind=assistant_kind,
                    config_signature=config_signature,
                    sample_count=int(profile.get('sample_count') or len(runs)),
                    success_count=sum(1 for run in runs if bool(run.success)),
                    failure_count=sum(1 for run in runs if not bool(run.success)),
                    blocked_count=sum(1 for run in runs if self._is_blocked(run)),
                    fallback_count=sum(1 for run in runs if self._used_fallback(run)),
                    success_rate=float(profile.get('success_rate') or 0.0),
                    blocked_rate=float(profile.get('blocked_rate') or 0.0),
                    fallback_rate=float(profile.get('fallback_rate') or 0.0),
                    average_score=float(profile.get('average_score') or 0.0),
                    average_latency_ms=int(profile.get('average_latency_ms') or 0),
                    adaptive_weight=float(profile.get('adaptive_weight') or 0.0),
                    weighted_score=float(profile.get('weighted_score') or 0.0),
                    trend_score=float(profile.get('trend_score') or 0.0),
                    degraded=degraded,
                    degradation_reasons=degradation_reasons,
                    evidence_refs=[run.run_id for run in runs[:6]],
                    comparison_scope_keys=comparison_scope_keys,
                    metadata={
                        'reasons': list(profile.get('reasons') or []),
                        'top_environment_signatures': list(profile.get('top_environment_signatures') or []),
                        'top_time_buckets': list(profile.get('top_time_buckets') or []),
                    },
                )
            )
        return items

    def _proposal_for_subject(
        self,
        *,
        recommendation: ExperimentRecommendation | None,
        domain: ExperimentDomain,
        subject_key: str,
        grouped_runs: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]],
        profiles: dict[tuple[EvaluationRoute, str, str], dict[str, Any]],
        ranked: list[dict[str, Any]],
    ) -> ToolEvolutionProposal | None:
        if not ranked:
            return None
        baseline_row = self._baseline_row(recommendation=recommendation, ranked=ranked)
        if baseline_row is None:
            return None
        alternative = next((item for item in ranked if item['key'] != baseline_row['key']), None)
        baseline_degraded, baseline_reasons = self._degradation(dict(baseline_row.get('profile') or {}))
        baseline_route: EvaluationRoute = baseline_row['route']
        baseline_assistant = str(baseline_row.get('assistant_kind') or '')
        baseline_signature = str(baseline_row.get('config_signature') or '')
        comparison_scope_keys = self._comparison_scope_keys(grouped_runs=grouped_runs)
        evidence_refs = [run.run_id for run in list(baseline_row.get('runs') or [])[:4]]
        baseline_profile = dict(baseline_row.get('profile') or {})
        if alternative is None and baseline_degraded:
            return ToolEvolutionProposal(
                proposal_key=self._proposal_key(
                    subject_key=subject_key,
                    proposal_kind='collect_more_evidence',
                    baseline_route=baseline_route,
                    baseline_assistant=baseline_assistant,
                    baseline_signature=baseline_signature,
                    candidate_route=baseline_route,
                    candidate_assistant=baseline_assistant,
                    candidate_signature=baseline_signature,
                ),
                domain=domain,
                subject_key=subject_key,
                status='pending',
                proposal_kind='collect_more_evidence',
                title=f'Recolectar mas evidencia para {subject_key}',
                summary='La ruta actual muestra degradacion, pero todavia no existe una alternativa con evidencia suficiente para competir.',
                rationale='Conviene recolectar nuevas corridas comparables antes de seguir reforzando la preferencia actual.',
                current_route=baseline_route,
                current_assistant_kind=baseline_assistant,
                current_config_signature=baseline_signature,
                candidate_route=baseline_route,
                candidate_assistant_kind=baseline_assistant,
                candidate_config_signature=baseline_signature,
                confidence=0.58,
                evidence_refs=evidence_refs,
                comparison_scope_keys=comparison_scope_keys,
                metadata={
                    'next_action': 'collect_more_runs',
                    'degradation_reasons': baseline_reasons,
                    'baseline_profile': baseline_profile,
                },
            )
        if alternative is None:
            return None
        alternative_route: EvaluationRoute = alternative['route']
        alternative_assistant = str(alternative.get('assistant_kind') or '')
        alternative_signature = str(alternative.get('config_signature') or '')
        alternative_profile = dict(alternative.get('profile') or {})
        margin = float(alternative.get('weighted_score') or 0.0) - float(baseline_row.get('weighted_score') or 0.0)
        alternative_local = self._is_local_route(alternative_route)
        baseline_local = self._is_local_route(baseline_route)
        proposal_kind = ''
        title = ''
        summary = ''
        rationale = ''
        status = 'proposed'
        confidence = 0.0
        if baseline_degraded and margin >= 0.05:
            proposal_kind = 'validate_replacement'
            title = f'Validar reemplazo de {baseline_assistant or baseline_route.value} en {subject_key}'
            summary = (
                f'{baseline_assistant or baseline_route.value} viene degradandose y {alternative_assistant or alternative_route.value} '
                'ya muestra mejor puntaje ponderado.'
            )
            rationale = 'La recomendacion actual dejo de ser la mejor opcion con evidencia suficiente para un sandbox de reemplazo.'
            confidence = min(0.96, 0.62 + margin + (0.08 if alternative_local and not baseline_local else 0.0))
        elif not baseline_local and alternative_local and margin >= -0.03:
            proposal_kind = 'validate_local_first'
            title = f'Validar ruta local primero para {subject_key}'
            summary = (
                f'La alternativa local {alternative_assistant or alternative_route.value} esta lo bastante cerca del baseline '
                'como para justificar un experimento local-first.'
            )
            rationale = 'Si la alternativa local mantiene resultado comparable, conviene reducir dependencia externa.'
            confidence = min(0.92, 0.55 + max(margin, 0.0) + 0.08)
        elif baseline_degraded and margin > 0:
            proposal_kind = 'compare_again'
            title = f'Recomparar herramienta para {subject_key}'
            summary = (
                f'La ruta actual muestra degradacion y {alternative_assistant or alternative_route.value} '
                'aparece mejor posicionada, aunque la ventaja todavia es moderada.'
            )
            rationale = 'Conviene repetir la comparacion en sandbox antes de promover un cambio estable.'
            confidence = min(0.86, 0.5 + margin + 0.06)
        if not proposal_kind:
            return None
        evidence_refs.extend([run.run_id for run in list(alternative.get('runs') or [])[:4]])
        return ToolEvolutionProposal(
            proposal_key=self._proposal_key(
                subject_key=subject_key,
                proposal_kind=proposal_kind,
                baseline_route=baseline_route,
                baseline_assistant=baseline_assistant,
                baseline_signature=baseline_signature,
                candidate_route=alternative_route,
                candidate_assistant=alternative_assistant,
                candidate_signature=alternative_signature,
            ),
            domain=domain,
            subject_key=subject_key,
            status='pending',
            proposal_kind=proposal_kind,
            title=title,
            summary=summary,
            rationale=rationale,
            current_route=baseline_route,
            current_assistant_kind=baseline_assistant,
            current_config_signature=baseline_signature,
            candidate_route=alternative_route,
            candidate_assistant_kind=alternative_assistant,
            candidate_config_signature=alternative_signature,
            confidence=round(confidence, 4),
            evidence_refs=list(dict.fromkeys(evidence_refs))[:8],
            comparison_scope_keys=comparison_scope_keys,
            metadata={
                'next_action': 'validate_in_sandbox',
                'score_margin': round(margin, 4),
                'baseline_degraded': baseline_degraded,
                'degradation_reasons': baseline_reasons,
                'baseline_profile': baseline_profile,
                'candidate_profile': alternative_profile,
                'alternative_weighted_score': round(float(alternative.get('weighted_score') or 0.0), 4),
                'baseline_weighted_score': round(float(baseline_row.get('weighted_score') or 0.0), 4),
                'local_first_candidate': alternative_local and not baseline_local,
                'ranked_configurations': [
                    {
                        'route': baseline_route.value,
                        'assistant_kind': baseline_assistant,
                        'config_signature': baseline_signature,
                        'weighted_score': round(float(baseline_row.get('weighted_score') or 0.0), 4),
                        'score': round(float(baseline_row.get('average_score') or 0.0), 4),
                        'samples': int(baseline_profile.get('sample_count') or 0),
                    },
                    {
                        'route': alternative_route.value,
                        'assistant_kind': alternative_assistant,
                        'config_signature': alternative_signature,
                        'weighted_score': round(float(alternative.get('weighted_score') or 0.0), 4),
                        'score': round(float(alternative.get('average_score') or 0.0), 4),
                        'samples': int(alternative_profile.get('sample_count') or 0),
                    },
                ],
            },
        )

    def _baseline_row(self, *, recommendation: ExperimentRecommendation | None, ranked: list[dict[str, Any]]) -> dict[str, Any] | None:
        if recommendation is None:
            return ranked[0] if ranked else None
        expected_key = (
            recommendation.recommended_route,
            str(recommendation.recommended_assistant_kind or '').strip().lower(),
            str(recommendation.recommended_config_signature or '').strip(),
        )
        for row in ranked:
            if row['key'] == expected_key:
                return row
        return ranked[0] if ranked else None

    def _degradation(self, profile: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        success_rate = float(profile.get('success_rate') or 0.0)
        blocked_rate = float(profile.get('blocked_rate') or 0.0)
        fallback_rate = float(profile.get('fallback_rate') or 0.0)
        trend_score = float(profile.get('trend_score') or 0.0)
        average_latency_ms = int(profile.get('average_latency_ms') or 0)
        sample_count = int(profile.get('sample_count') or 0)
        if blocked_rate >= 0.34:
            reasons.append(f'bloqueos frecuentes {blocked_rate:.0%}')
        if fallback_rate >= 0.34:
            reasons.append(f'fallback recurrente {fallback_rate:.0%}')
        if trend_score <= -0.12:
            reasons.append('deterioro reciente')
        if sample_count >= 3 and success_rate < 0.5:
            reasons.append(f'exito insuficiente {success_rate:.0%}')
        if average_latency_ms >= 1800:
            reasons.append(f'latencia alta {average_latency_ms} ms')
        return bool(reasons), reasons

    def _comparison_scope_keys(self, *, grouped_runs: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]]) -> list[str]:
        items: list[str] = []
        for runs in grouped_runs.values():
            for run in runs:
                probe = str((run.metadata or {}).get('comparison_scope_key') or '').strip()
                if probe and probe not in items:
                    items.append(probe)
        return items[:6]

    def _validation_summary(self) -> dict[str, Any]:
        service = self.autonomous_validation_cycle
        if service is None or not hasattr(service, 'current_snapshot'):
            return {}
        try:
            snapshot = service.current_snapshot()
            return {
                'status': str(getattr(snapshot, 'status', '') or ''),
                'summary': str(getattr(snapshot, 'summary', '') or ''),
                'subject_key': str(getattr(getattr(snapshot, 'current_experiment', None), 'subject_key', '') or ''),
            }
        except Exception:
            return {}

    def _summary(
        self,
        *,
        subject_summaries: list[str],
        proposal_count: int,
        decided_count: int,
        degraded_count: int,
        validation: dict[str, Any],
    ) -> str:
        if not subject_summaries:
            return 'Todavia no hay suficiente evidencia comparativa para un monitor de evolucion de herramientas.'
        summary = (
            f'Superviso {len(subject_summaries)} contexto(s) con {proposal_count} propuesta(s) activa(s), '
            f'{decided_count} ya decidida(s) y {degraded_count} contexto(s) degradado(s).'
        )
        summary += f' Mejor panorama actual: {subject_summaries[0]}'
        validation_status = str(validation.get('status') or '').strip()
        validation_summary = str(validation.get('summary') or '').strip()
        if validation_status:
            summary += f' Validacion autonoma: {validation_status}.'
        if validation_summary:
            summary += f' {validation_summary}'
        return summary.strip()

    def _subject_summary(self, *, subject_key: str, ranked: list[dict[str, Any]], proposal: ToolEvolutionProposal | None) -> str:
        top = ranked[0] if ranked else {}
        label = str(top.get('assistant_kind') or (top.get('route').value if top.get('route') else 'ruta no resuelta'))
        detail = f'{subject_key} favorece {label} con score {float(top.get("weighted_score") or 0.0):.2f}'
        if proposal is not None:
            detail += f' y propuesta {proposal.proposal_kind}'
        return detail

    def _reconcile_proposals(
        self,
        proposals: list[ToolEvolutionProposal],
    ) -> tuple[list[ToolEvolutionProposal], list[ToolEvolutionProposal], dict[str, Any], list[dict[str, Any]]]:
        summary, entries = self._decision_log_summary()
        latest_by_key: dict[str, dict[str, Any]] = {}
        for entry in entries:
            proposal_key = str(entry.get('proposal_key') or '').strip()
            if proposal_key:
                latest_by_key[proposal_key] = entry
        active: list[ToolEvolutionProposal] = []
        decided: list[ToolEvolutionProposal] = []
        for proposal in proposals:
            probe_key = str(proposal.proposal_key or '').strip()
            latest = latest_by_key.get(probe_key)
            if latest is None:
                active.append(proposal)
                continue
            metadata = {
                **dict(proposal.metadata or {}),
                'decision_state': {
                    'decision': str(latest.get('decision') or ''),
                    'winner': str(latest.get('winner') or ''),
                    'reason': str(latest.get('reason') or ''),
                    'recorded_at_utc': str(latest.get('recorded_at_utc') or ''),
                    'result_id': str(latest.get('result_id') or ''),
                },
            }
            resolved = proposal.model_copy(update={'status': str(latest.get('decision') or 'pending'), 'metadata': metadata})
            if resolved.status == 'pending':
                active.append(resolved)
            else:
                decided.append(resolved)
        return active, decided, summary, entries[-6:]

    def _decision_log_summary(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        service = self.autonomous_validation_cycle
        if (
            service is None
            or not hasattr(service, 'current_decision_log')
            or not hasattr(service, 'decision_log_summary')
        ):
            return {}, []
        try:
            log = service.current_decision_log(refresh=True)
            summary = dict(service.decision_log_summary(log) or {})
            entries = [item.model_dump(mode='json') for item in list(getattr(log, 'entries', []) or [])]
            return summary, entries
        except Exception:
            return {}, []

    def _current_discovery_status(self, *, subject_key: str | None) -> Any | None:
        service = self.tool_discovery_service
        if service is None or not hasattr(service, 'current_status'):
            return None
        try:
            return service.current_status(refresh=True, subject_key=subject_key)
        except Exception:
            return None

    def _discovery_signals_for_subject(
        self,
        *,
        discovery_status: Any | None,
        domain: ExperimentDomain,
        subject_key: str,
    ) -> list[ToolDiscoverySignal]:
        if discovery_status is None:
            return []
        candidates: list[ToolDiscoverySignal] = []
        for item in list(getattr(discovery_status, 'signals', []) or []):
            if item.domain != domain or str(item.scope or '').strip() != subject_key:
                continue
            if str(item.status or '').strip() != 'detected':
                continue
            candidates.append(item)
        candidates.sort(
            key=lambda item: (
                float(item.confidence or 0.0),
                float(item.impact_score or 0.0),
                float(item.compatibility_score or 0.0),
                float(item.cost_score or 0.0),
            ),
            reverse=True,
        )
        return candidates[:2]

    def _proposal_from_discovery_signal(
        self,
        *,
        signal: ToolDiscoverySignal,
        recommendation: ExperimentRecommendation | None,
    ) -> ToolEvolutionProposal | None:
        if recommendation is None:
            return None
        metadata = dict(signal.metadata or {})
        discovery_source = str(signal.source or '').strip() or 'tool_registry'
        baseline_score = float(metadata.get('baseline_weighted_score') or recommendation.score or 0.0)
        estimated_candidate_score = float(metadata.get('estimated_candidate_score') or baseline_score)
        score_margin = round(estimated_candidate_score - baseline_score, 4)
        current_assistant = str(recommendation.recommended_assistant_kind or '').strip().lower()
        current_signature = str(recommendation.recommended_config_signature or '').strip()
        return ToolEvolutionProposal(
            proposal_key=str(signal.proposal_key or '').strip(),
            domain=signal.domain,
            subject_key=signal.scope,
            status='pending',
            proposal_kind='validate_discovery',
            title=signal.title,
            summary=signal.summary,
            rationale=f"Descubierto via {discovery_source} con evidencia {', '.join(signal.source_refs[:2])}.",
            current_route=recommendation.recommended_route,
            current_assistant_kind=current_assistant,
            current_config_signature=current_signature,
            candidate_route=signal.route,
            candidate_assistant_kind=str(signal.assistant_kind or '').strip().lower(),
            candidate_config_signature=str(signal.config_signature or '').strip(),
            confidence=round(float(signal.confidence or 0.0), 4),
            evidence_refs=list(signal.evidence_refs or [])[:8],
            comparison_scope_keys=[signal.scope],
            metadata={
                'next_action': 'validate_in_sandbox',
                'discovery_signal_id': signal.signal_id,
                'discovery_source': discovery_source,
                'discovery_source_refs': list(signal.source_refs or []),
                'compatibility_score': float(signal.compatibility_score or 0.0),
                'impact_score': float(signal.impact_score or 0.0),
                'cost_score': float(signal.cost_score or 0.0),
                'baseline_weighted_score': round(baseline_score, 4),
                'alternative_weighted_score': round(estimated_candidate_score, 4),
                'score_margin': score_margin,
                'baseline_profile': {
                    'weighted_score': round(baseline_score, 4),
                    'sample_count': len(list(dict.fromkeys(signal.evidence_refs or []))),
                },
                'candidate_profile': {
                    'weighted_score': round(estimated_candidate_score, 4),
                    'compatibility_score': float(signal.compatibility_score or 0.0),
                    'impact_score': float(signal.impact_score or 0.0),
                    'cost_score': float(signal.cost_score or 0.0),
                },
                'ranked_configurations': [
                    {
                        'route': recommendation.recommended_route.value,
                        'assistant_kind': current_assistant,
                        'config_signature': current_signature,
                        'weighted_score': round(baseline_score, 4),
                        'score': round(baseline_score, 4),
                        'samples': len(list(dict.fromkeys(signal.evidence_refs or []))),
                    },
                    {
                        'route': signal.route.value,
                        'assistant_kind': str(signal.assistant_kind or '').strip().lower(),
                        'config_signature': str(signal.config_signature or '').strip(),
                        'weighted_score': round(estimated_candidate_score, 4),
                        'score': round(estimated_candidate_score, 4),
                        'samples': 0,
                    },
                ],
                **metadata,
            },
        )

    def _decided_proposal_payloads(
        self,
        *,
        decided_proposals: list[ToolEvolutionProposal],
        decision_entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = [item.model_dump(mode='json') for item in list(decided_proposals or [])]
        seen = {str(item.get('proposal_key') or '').strip() for item in items if str(item.get('proposal_key') or '').strip()}
        for entry in reversed(list(decision_entries or [])):
            proposal_key = str(entry.get('proposal_key') or '').strip()
            if not proposal_key or proposal_key in seen:
                continue
            items.append(
                {
                    'proposal_id': str(entry.get('proposal_id') or ''),
                    'proposal_key': proposal_key,
                    'domain': str(entry.get('domain') or ''),
                    'subject_key': str(entry.get('subject_key') or ''),
                    'status': str(entry.get('decision') or 'unresolved'),
                    'proposal_kind': str(entry.get('proposal_kind') or ''),
                    'title': str(entry.get('proposal_kind') or 'decision'),
                    'summary': str(entry.get('reason') or ''),
                    'current_route': str(entry.get('current_route') or ''),
                    'current_assistant_kind': str(entry.get('current_assistant_kind') or ''),
                    'current_config_signature': str(entry.get('current_config_signature') or ''),
                    'candidate_route': str(entry.get('candidate_route') or ''),
                    'candidate_assistant_kind': str(entry.get('candidate_assistant_kind') or ''),
                    'candidate_config_signature': str(entry.get('candidate_config_signature') or ''),
                    'confidence': float(entry.get('confidence') or 0.0),
                    'evidence_refs': list(entry.get('evidence_refs') or []),
                    'comparison_scope_keys': list(entry.get('comparison_scope_keys') or []),
                    'metadata': {
                        'decision_state': {
                            'decision': str(entry.get('decision') or ''),
                            'winner': str(entry.get('winner') or ''),
                            'reason': str(entry.get('reason') or ''),
                            'recorded_at_utc': str(entry.get('recorded_at_utc') or ''),
                            'result_id': str(entry.get('result_id') or ''),
                        }
                    },
                }
            )
            seen.add(proposal_key)
        return items[:6]

    def _render_markdown(self, status: ToolEvolutionStatus) -> str:
        lines = [
            '# IABV v1.5 - Tool Evolution Monitor',
            '',
            f'Generado: {status.updated_at_utc.isoformat()}',
            f'Resumen: {status.summary}',
            '',
            '## Rendimiento por herramienta',
        ]
        for item in status.performance[:8]:
            lines.append(
                f"- {item.subject_key}: {item.assistant_kind or item.route.value} | route={item.route.value} | "
                f"score={item.weighted_score:.2f} | exito={item.success_rate:.0%} | bloqueos={item.blocked_rate:.0%}"
            )
        lines.append('')
        lines.append('## Propuestas')
        if not status.proposals:
            lines.append('- Sin propuestas nuevas con evidencia suficiente.')
        for item in status.proposals[:6]:
            lines.append(
                f"- {item.title}: {item.summary} | accion={str(item.metadata.get('next_action') or 'n/d')} | confianza={item.confidence:.2f}"
            )
        if status.unresolved_fields:
            lines.append('')
            lines.append(f"UNRESOLVED: {', '.join(status.unresolved_fields)}")
        return '\n'.join(lines).strip()

    def _proposal_key(
        self,
        *,
        subject_key: str,
        proposal_kind: str,
        baseline_route: EvaluationRoute,
        baseline_assistant: str,
        baseline_signature: str,
        candidate_route: EvaluationRoute,
        candidate_assistant: str,
        candidate_signature: str,
    ) -> str:
        return '|'.join(
            [
                str(subject_key or '').strip(),
                str(proposal_kind or '').strip(),
                baseline_route.value,
                str(baseline_assistant or '').strip().lower(),
                str(baseline_signature or '').strip(),
                candidate_route.value,
                str(candidate_assistant or '').strip().lower(),
                str(candidate_signature or '').strip(),
            ]
        )

    def _domain_from_value(self, value: Any) -> ExperimentDomain:
        if isinstance(value, ExperimentDomain):
            return value
        probe = str(value or '').strip()
        for domain in ExperimentDomain:
            if domain.value == probe:
                return domain
        return ExperimentDomain.LANGUAGE

    def _is_blocked(self, run: ExperimentRun) -> bool:
        metadata = dict(run.metadata or {})
        flags = [str(item).strip().lower() for item in (metadata.get('external_state_flags') or []) if str(item).strip()]
        if bool(metadata.get('blocked')) or bool(metadata.get('governance_blocked')):
            return True
        blockers = {'wrong_thread', 'permission_required', 'account_limited', 'browser_security_verification', 'session_expired'}
        return any(any(token in flag for token in blockers) for flag in flags)

    def _used_fallback(self, run: ExperimentRun) -> bool:
        metadata = dict(run.metadata or {})
        return bool(metadata.get('used_fallback') or metadata.get('fallback_used'))

    def _is_local_route(self, route: EvaluationRoute) -> bool:
        return route in {
            EvaluationRoute.LOCAL,
            EvaluationRoute.CODE_AGENT,
            EvaluationRoute.MATH_EVALUATION,
            EvaluationRoute.OCR_VISION,
        }
