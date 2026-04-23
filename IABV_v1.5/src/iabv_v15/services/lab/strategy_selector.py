from __future__ import annotations

from collections import defaultdict
from typing import Any

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    EvaluationRoute,
    ExperimentDomain,
    ExperimentRecommendation,
    ExperimentRun,
)


class StrategySelector:
    def __init__(self, adaptive_weight_layer: Any | None = None) -> None:
        self.adaptive_weight_layer = adaptive_weight_layer

    def recommend(
        self,
        *,
        domain: ExperimentDomain,
        subject_key: str,
        candidate_runs: list[ExperimentRun],
        historical_runs: list[ExperimentRun] | None = None,
    ) -> ExperimentRecommendation:
        route_scores: dict[EvaluationRoute, list[float]] = defaultdict(list)
        grouped_scores: dict[tuple[EvaluationRoute, str, str], list[float]] = defaultdict(list)
        support_map: dict[tuple[EvaluationRoute, str, str], list[str]] = defaultdict(list)
        reuse_map: dict[tuple[EvaluationRoute, str, str], int] = defaultdict(int)
        configuration_map: dict[tuple[EvaluationRoute, str, str], AssistantConfigurationSnapshot] = {}
        grouped_runs: dict[tuple[EvaluationRoute, str, str], list[ExperimentRun]] = defaultdict(list)
        all_runs = [*(historical_runs or []), *candidate_runs]
        for run in all_runs:
            route_scores[run.route].append(run.metrics.total_score)
            key = (
                run.route,
                str(run.assistant_kind or '').strip().lower(),
                str(run.config_signature or '').strip(),
            )
            grouped_scores[key].append(run.metrics.total_score)
            support_map[key].append(run.run_id)
            reuse_map[key] += 1 if run.reused_later else 0
            configuration_map[key] = run.assistant_configuration
            grouped_runs[key].append(run)
        if not grouped_scores:
            return ExperimentRecommendation(
                domain=domain,
                subject_key=subject_key,
                recommended_route=EvaluationRoute.FALLBACK,
                rationale='No hay evidencia previa ni resultados del laboratorio para recomendar una via.',
            )
        successful_keys = {
            key
            for key, runs in grouped_runs.items()
            if any(bool(run.success) for run in runs)
        }
        if not successful_keys:
            return ExperimentRecommendation(
                domain=domain,
                subject_key=subject_key,
                recommended_route=EvaluationRoute.FALLBACK,
                rationale='Todavia no hay una corrida exitosa para recomendar una via; conviene evitar recomendaciones automaticas hasta tener evidencia mejor.',
                metadata={
                    'ranked_routes': [],
                    'ranked_configurations': [],
                    'winning_trace_ids': [],
                    'losing_trace_ids': [
                        trace_id
                        for trace_id in (
                            str((run.metadata or {}).get('trace_id') or '')
                            for run in all_runs
                        )
                        if trace_id
                    ][:8],
                    'comparison_scope_keys': [
                        scope_key
                        for scope_key in dict.fromkeys(
                            str((run.metadata or {}).get('comparison_scope_key') or '').strip()
                            for run in all_runs
                        )
                        if scope_key
                    ][:8],
                },
            )
        route_scores = defaultdict(list)
        grouped_scores = defaultdict(list)
        support_map = defaultdict(list)
        reuse_map = defaultdict(int)
        configuration_map = {}
        grouped_runs = defaultdict(list)
        for run in all_runs:
            key = (
                run.route,
                str(run.assistant_kind or '').strip().lower(),
                str(run.config_signature or '').strip(),
            )
            if key not in successful_keys:
                continue
            route_scores[run.route].append(run.metrics.total_score)
            grouped_scores[key].append(run.metrics.total_score)
            support_map[key].append(run.run_id)
            reuse_map[key] += 1 if run.reused_later else 0
            configuration_map[key] = run.assistant_configuration
            grouped_runs[key].append(run)
        adaptive_profiles = (
            self.adaptive_weight_layer.suggest(grouped_runs=grouped_runs)
            if self.adaptive_weight_layer is not None
            else {}
        )
        ranked_configurations = sorted(
            (
                (
                    route,
                    assistant_kind,
                    config_signature,
                    sum(scores) / max(len(scores), 1),
                    len(scores),
                    reuse_map[(route, assistant_kind, config_signature)],
                    float((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('adaptive_weight') or 0.0),
                    float((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('weighted_score') or (sum(scores) / max(len(scores), 1))),
                )
                for (route, assistant_kind, config_signature), scores in grouped_scores.items()
            ),
            key=lambda item: (item[7], item[4], item[5], item[3]),
            reverse=True,
        )
        weighted_route_scores: dict[EvaluationRoute, list[float]] = defaultdict(list)
        for route, assistant_kind, config_signature, average_score, _, _, _, weighted_score in ranked_configurations:
            weighted_route_scores[route].append(weighted_score or average_score)
        ranked_routes = sorted(
            ((route, sum(scores) / max(len(scores), 1), len(scores)) for route, scores in weighted_route_scores.items()),
            key=lambda item: (item[1], item[2]),
            reverse=True,
        )
        best_route, best_assistant_kind, best_config_signature, best_score, sample_count, reuse_count, adaptive_weight, weighted_score = ranked_configurations[0]
        best_key = (best_route, best_assistant_kind, best_config_signature)
        best_profile = dict(adaptive_profiles.get(best_key) or {})
        winning_runs = grouped_runs.get(best_key, [])
        losing_runs = [run for key, runs in grouped_runs.items() if key != best_key for run in runs]
        rationale = (
            f'Recomiendo {best_route.value} para {domain.value} en {subject_key}'
            f' usando {best_assistant_kind or "asistente por defecto"}'
            f' con configuracion {best_config_signature or "base"}'
            f' por score base {best_score:.2f} y score adaptativo {weighted_score:.2f}'
            f' con {sample_count} muestra(s).'
        )
        if best_profile.get('reasons'):
            rationale += f" Ajuste adaptativo: {'; '.join(str(item) for item in best_profile.get('reasons')[:2])}."
        confidence = min(1.0, 0.42 + sample_count * 0.1 + weighted_score * 0.22 + max(adaptive_weight, 0.0) * 0.3)
        composite_recommendation = self._build_composite_recommendation(
            ranked_configurations=ranked_configurations,
            adaptive_profiles=adaptive_profiles,
            grouped_runs=grouped_runs,
        )
        return ExperimentRecommendation(
            domain=domain,
            subject_key=subject_key,
            recommended_route=best_route,
            recommended_assistant_kind=best_assistant_kind,
            recommended_assistant_configuration=configuration_map.get(best_key, AssistantConfigurationSnapshot()),
            recommended_config_signature=best_config_signature,
            score=round(weighted_score, 4),
            confidence=round(confidence, 4),
            rationale=rationale,
            supporting_run_ids=support_map[best_key][:8],
            metadata={
                'ranked_routes': [
                    {'route': route.value, 'score': round(score, 4), 'samples': count}
                    for route, score, count in ranked_routes
                ],
                'ranked_configurations': [
                    {
                        'route': route.value,
                        'assistant_kind': assistant_kind,
                        'config_signature': config_signature,
                        'score': round(score, 4),
                        'adaptive_weight': round(adaptive, 4),
                        'weighted_score': round(weighted, 4),
                        'samples': count,
                        'reuse_count': reuse,
                        'success_rate': round(float((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('success_rate') or 0.0), 4),
                        'blocked_rate': round(float((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('blocked_rate') or 0.0), 4),
                        'fallback_rate': round(float((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('fallback_rate') or 0.0), 4),
                        'reasons': list((adaptive_profiles.get((route, assistant_kind, config_signature), {}) or {}).get('reasons') or []),
                    }
                    for route, assistant_kind, config_signature, score, count, reuse, adaptive, weighted in ranked_configurations
                ],
                'winning_trace_ids': [
                    trace_id
                    for trace_id in (str((run.metadata or {}).get('trace_id') or '') for run in winning_runs)
                    if trace_id
                ][:8],
                'losing_trace_ids': [
                    trace_id
                    for trace_id in (str((run.metadata or {}).get('trace_id') or '') for run in losing_runs)
                    if trace_id
                ][:8],
                'comparison_scope_keys': [
                    scope_key
                    for scope_key in dict.fromkeys(
                        str((run.metadata or {}).get('comparison_scope_key') or '').strip()
                        for run in all_runs
                    )
                    if scope_key
                ][:8],
                'adaptive_learning_summary': {
                    'preferred_route': best_route.value,
                    'preferred_assistant_kind': best_assistant_kind,
                    'preferred_config_signature': best_config_signature,
                    'adaptive_weight': round(adaptive_weight, 4),
                    'weighted_score': round(weighted_score, 4),
                    'sample_count': int(best_profile.get('sample_count') or sample_count),
                    'success_rate': round(float(best_profile.get('success_rate') or 0.0), 4),
                    'blocked_rate': round(float(best_profile.get('blocked_rate') or 0.0), 4),
                    'fallback_rate': round(float(best_profile.get('fallback_rate') or 0.0), 4),
                    'top_environment_signatures': list(best_profile.get('top_environment_signatures') or []),
                    'top_time_buckets': list(best_profile.get('top_time_buckets') or []),
                    'reasons': list(best_profile.get('reasons') or []),
                },
                'composite_recommendation': composite_recommendation,
            },
        )

    # ------------------------------------------------------------------
    # P5: Recomendaciones compuestas multi-IA
    # ------------------------------------------------------------------

    @staticmethod
    def _build_composite_recommendation(
        *,
        ranked_configurations: list[tuple[Any, ...]],
        adaptive_profiles: dict[tuple[Any, str, str], dict[str, Any]],
        grouped_runs: dict[tuple[Any, str, str], list[ExperimentRun]],
    ) -> dict[str, Any] | None:
        """Build a composite recommendation when 2+ IAs are complementary.

        Detects when different ``assistant_kind`` values have successful runs
        in overlapping ``subject_key`` domains, and emits a coordinated
        recommendation showing the primary IA plus a secondary IA whose
        strengths complement the primary.

        Only emits when each IA has >= 3 successful runs to ensure evidence
        quality.  Returns ``None`` when there is insufficient evidence or
        only one viable IA.
        """
        if len(ranked_configurations) < 2:
            return None

        _MIN_RUNS_FOR_COMPOSITE = 3
        kind_stats: dict[str, dict[str, Any]] = {}
        for route, assistant_kind, config_sig, score, count, reuse, adaptive, weighted in ranked_configurations:
            kind = str(assistant_kind or '').strip().lower()
            if not kind:
                continue
            key = (route, assistant_kind, config_sig)
            runs = grouped_runs.get(key, [])
            successful = [r for r in runs if bool(r.success)]
            profile = adaptive_profiles.get(key, {}) or {}
            success_rate = float(profile.get('success_rate') or 0.0)
            if kind not in kind_stats:
                kind_stats[kind] = {
                    'assistant_kind': kind,
                    'best_score': round(weighted, 4),
                    'total_runs': count,
                    'successful_runs': len(successful),
                    'success_rate': round(success_rate, 4),
                    'best_route': route.value if hasattr(route, 'value') else str(route),
                    'aspects': set(),
                }
            else:
                existing = kind_stats[kind]
                if weighted > existing['best_score']:
                    existing['best_score'] = round(weighted, 4)
                    existing['best_route'] = route.value if hasattr(route, 'value') else str(route)
                existing['total_runs'] += count
                existing['successful_runs'] += len(successful)
                existing['success_rate'] = round(
                    existing['successful_runs'] / max(existing['total_runs'], 1), 4,
                )
            route_val = route.value if hasattr(route, 'value') else str(route)
            kind_stats[kind]['aspects'].add(route_val)

        viable = {
            k: v for k, v in kind_stats.items()
            if v['successful_runs'] >= _MIN_RUNS_FOR_COMPOSITE
        }
        if len(viable) < 2:
            return None

        ranked_kinds = sorted(
            viable.values(),
            key=lambda v: (v['best_score'], v['successful_runs']),
            reverse=True,
        )
        primary = ranked_kinds[0]
        secondary = ranked_kinds[1]

        primary_aspects = primary['aspects']
        secondary_aspects = secondary['aspects']
        complementary_aspects = secondary_aspects - primary_aspects
        overlapping_aspects = primary_aspects & secondary_aspects

        composite_confidence = round(
            min(1.0, 0.5 + primary['success_rate'] * 0.25 + secondary['success_rate'] * 0.25),
            4,
        )

        return {
            'primary': {
                'assistant_kind': primary['assistant_kind'],
                'aspect': primary['best_route'],
                'score': primary['best_score'],
                'success_rate': primary['success_rate'],
                'runs': primary['total_runs'],
            },
            'secondary': {
                'assistant_kind': secondary['assistant_kind'],
                'aspect': secondary['best_route'],
                'score': secondary['best_score'],
                'success_rate': secondary['success_rate'],
                'runs': secondary['total_runs'],
            },
            'composite_confidence': composite_confidence,
            'complementary_aspects': sorted(complementary_aspects),
            'overlapping_aspects': sorted(overlapping_aspects),
            'viable_ia_count': len(viable),
        }
