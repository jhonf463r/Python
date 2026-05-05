from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import timedelta
from typing import Any

from iabv_v15.domain.models import (
    AssistantConfigurationSnapshot,
    EvaluationRoute,
    ExperimentCandidate,
    ExperimentDomain,
    ExperimentRecommendation,
    ExperimentRun,
    IATraceEntry,
)
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.services.lab.algorithm_benchmark_registry import AlgorithmBenchmarkRegistry
from iabv_v15.services.lab.decision_scoring_engine import DecisionScoringEngine
from iabv_v15.services.lab.strategy_selector import StrategySelector


class ExperimentLab:
    def __init__(
        self,
        *,
        repository: ExperimentLabRepository,
        registry: AlgorithmBenchmarkRegistry,
        scoring_engine: DecisionScoringEngine,
        strategy_selector: StrategySelector,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.scoring_engine = scoring_engine
        self.strategy_selector = strategy_selector
        if strategy_selector is not None:
            strategy_selector._experiment_lab = self

    def run_experiment(
        self,
        *,
        domain: ExperimentDomain,
        objective: str,
        subject_key: str,
        expected: Any,
        candidates: list[ExperimentCandidate],
        metadata: dict[str, Any] | None = None,
    ) -> tuple[list[ExperimentRun], ExperimentRecommendation]:
        runs: list[ExperimentRun] = []
        historical_runs = self.repository.list_runs(domain=domain.value, subject_key=subject_key, limit=20)
        reuse_bonus = self._reuse_bonus(historical_runs)
        for candidate in candidates:
            assistant_kind = str(candidate.assistant_kind or candidate.metadata.get('assistant_kind') or candidate.label or '').strip().lower()
            assistant_configuration = self._assistant_configuration(
                assistant_kind=assistant_kind,
                route=candidate.route,
                metadata=candidate.metadata,
                explicit=candidate.assistant_configuration,
            )
            config_signature = str(candidate.config_signature or candidate.metadata.get('config_signature') or self._config_signature(assistant_configuration))
            same_config_runs = self._same_configuration_runs(
                historical_runs=historical_runs,
                assistant_kind=assistant_kind,
                config_signature=config_signature,
            )
            evaluation = self.registry.evaluate(domain=domain, objective=objective, expected=expected, candidate=candidate)
            metric = self.scoring_engine.score(
                precision=float(evaluation.get('precision') or 0.0),
                execution_ms=int(candidate.execution_ms or 0),
                operational_cost=float(candidate.operational_cost or 0.0),
                robustness=float(evaluation.get('robustness') or 0.0),
                reuse_score=float(candidate.metadata.get('reuse_score') or reuse_bonus if candidate.metadata.get('reused_pattern') else reuse_bonus * 0.5),
                user_progress=float(candidate.metadata.get('user_progress') or (metadata or {}).get('user_progress') or (metadata or {}).get('goal_progress_signal') or 0.0),
                metadata={
                    **dict(evaluation.get('metadata') or {}),
                    'candidate_label': candidate.label,
                    'route': candidate.route.value,
                    'assistant_kind': assistant_kind,
                    'config_signature': config_signature,
                    'sample_support': len(same_config_runs) + 1,
                },
            )
            metric = metric.model_copy(
                update={
                    'metadata': {
                        **dict(metric.metadata or {}),
                        'relative_vs_same_config': self._relative_vs_same_config(metric.total_score, same_config_runs),
                    }
                }
            )
            run = ExperimentRun(
                domain=domain,
                suite_name=str(evaluation.get('suite_name') or 'generic_suite'),
                objective=objective,
                subject_key=subject_key,
                comparison_scope_key=str(candidate.metadata.get('comparison_scope_key') or (metadata or {}).get('comparison_scope_key') or ''),
                route=candidate.route,
                assistant_kind=assistant_kind,
                assistant_configuration=assistant_configuration,
                config_signature=config_signature,
                candidate_id=candidate.candidate_id,
                candidate_label=candidate.label,
                success=bool(evaluation.get('success')),
                expected_summary=self._summary(expected),
                observed_summary=str(evaluation.get('observed_summary') or candidate.output_text or '')[:240],
                metrics=metric,
                evidence_refs=list(candidate.metadata.get('evidence_refs') or []),
                reused_later=bool(candidate.metadata.get('reused_later', False)),
                better_than_previous=self._better_than_previous(metric.total_score, same_config_runs, historical_runs),
                metadata={
                    **(metadata or {}),
                    **candidate.metadata,
                    'suite_name': str(evaluation.get('suite_name') or 'generic_suite'),
                    'assistant_kind': assistant_kind,
                    'config_signature': config_signature,
                    'trace_id': str(candidate.metadata.get('trace_id') or ''),
                    'session_id': str(candidate.metadata.get('session_id') or (metadata or {}).get('session_id') or ''),
                    'comparison_scope_key': str(candidate.metadata.get('comparison_scope_key') or ''),
                    'source_trace_ids': list(candidate.metadata.get('source_trace_ids') or []),
                    'proposal_summary': str(candidate.metadata.get('proposal_summary') or '')[:240],
                    'outcome_summary': str(candidate.metadata.get('outcome_summary') or evaluation.get('observed_summary') or candidate.output_text or '')[:240],
                },
            )
            self.repository.save_run(run)
            runs.append(run)
        recommendation = self.strategy_selector.recommend(
            domain=domain,
            subject_key=subject_key,
            candidate_runs=runs,
            historical_runs=historical_runs,
        )
        self.repository.save_recommendation(recommendation)
        return runs, recommendation

    def suggest_route(self, *, domain: ExperimentDomain, subject_key: str) -> ExperimentRecommendation | None:
        recommendation = self.repository.latest_recommendation(domain=domain.value, subject_key=subject_key)
        if recommendation is not None:
            return recommendation
        runs = self.repository.list_runs(domain=domain.value, subject_key=subject_key, limit=20)
        if not runs:
            return None
        recommendation = self.strategy_selector.recommend(domain=domain, subject_key=subject_key, candidate_runs=[], historical_runs=runs)
        self.repository.save_recommendation(recommendation)
        return recommendation

    def list_candidate_traces_for_scope(self, scope_key: str, *, limit: int = 20) -> list[IATraceEntry]:
        return self.repository.list_candidate_traces_for_scope(scope_key, limit=limit)

    def record_outcome(
        self,
        *,
        domain: ExperimentDomain,
        objective: str,
        subject_key: str,
        route: EvaluationRoute,
        candidate_label: str,
        success: bool,
        observed_summary: str,
        expected_summary: str = '',
        precision: float = 0.0,
        robustness: float = 0.0,
        operational_cost: float = 0.0,
        reuse_score: float = 0.0,
        user_progress: float = 0.0,
        execution_ms: int = 0,
        evidence_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        suite_name: str = 'observed_outcome',
        candidate_id: str = '',
    ) -> tuple[ExperimentRun, ExperimentRecommendation]:
        historical_runs = self.repository.list_runs(domain=domain.value, subject_key=subject_key, limit=20)
        payload_metadata = dict(metadata or {})
        assistant_kind = str(payload_metadata.get('assistant_kind') or candidate_label or '').strip().lower()
        assistant_configuration = self._assistant_configuration(
            assistant_kind=assistant_kind,
            route=route,
            metadata=payload_metadata,
        )
        config_signature = str(payload_metadata.get('config_signature') or self._config_signature(assistant_configuration))
        same_config_runs = self._same_configuration_runs(
            historical_runs=historical_runs,
            assistant_kind=assistant_kind,
            config_signature=config_signature,
        )
        metric = self.scoring_engine.score(
            precision=precision,
            execution_ms=execution_ms,
            operational_cost=operational_cost,
            robustness=robustness,
            reuse_score=reuse_score,
            user_progress=user_progress,
            metadata={
                **payload_metadata,
                'route': route.value,
                'candidate_label': candidate_label,
                'assistant_kind': assistant_kind,
                'config_signature': config_signature,
                'sample_support': len(same_config_runs) + 1,
            },
        )
        metric = metric.model_copy(
            update={
                'metadata': {
                    **dict(metric.metadata or {}),
                    'relative_vs_same_config': self._relative_vs_same_config(metric.total_score, same_config_runs),
                }
            }
        )
        run = ExperimentRun(
            domain=domain,
            suite_name=suite_name,
            objective=objective,
            subject_key=subject_key,
            comparison_scope_key=str(payload_metadata.get('comparison_scope_key') or ''),
            route=route,
            assistant_kind=assistant_kind,
            assistant_configuration=assistant_configuration,
            config_signature=config_signature,
            candidate_id=candidate_id,
            candidate_label=candidate_label,
            success=success,
            expected_summary=expected_summary[:240],
            observed_summary=str(observed_summary or '')[:240],
            metrics=metric,
            evidence_refs=list(evidence_refs or []),
            reused_later=bool(payload_metadata.get('reused_later', False)),
            better_than_previous=self._better_than_previous(metric.total_score, same_config_runs, historical_runs),
            metadata={
                **payload_metadata,
                'suite_name': suite_name,
                'candidate_label': candidate_label,
                'route': route.value,
                'assistant_kind': assistant_kind,
                'config_signature': config_signature,
                'trace_id': str(payload_metadata.get('trace_id') or ''),
                'session_id': str(payload_metadata.get('session_id') or ''),
                'comparison_scope_key': str(payload_metadata.get('comparison_scope_key') or ''),
                'source_trace_ids': list(payload_metadata.get('source_trace_ids') or []),
                'proposal_summary': str(payload_metadata.get('proposal_summary') or '')[:240],
                'outcome_summary': str(payload_metadata.get('outcome_summary') or observed_summary or '')[:240],
            },
        )
        self.repository.save_run(run)
        recommendation = self.strategy_selector.recommend(
            domain=domain,
            subject_key=subject_key,
            candidate_runs=[run],
            historical_runs=historical_runs,
        )
        self.repository.save_recommendation(recommendation)
        return run, recommendation

    def _reuse_bonus(self, historical_runs: list[ExperimentRun]) -> float:
        if not historical_runs:
            return 0.0
        successful = [item for item in historical_runs if item.success]
        return min(1.0, len(successful) / max(len(historical_runs), 1))

    def _summary(self, payload: Any) -> str:
        if isinstance(payload, dict):
            bits = []
            for key in ('text', 'expected_text', 'expression', 'value', 'objects', 'required_tokens'):
                if key in payload and payload.get(key):
                    bits.append(f"{key}={payload.get(key)}")
            return ' | '.join(bits)[:240]
        return str(payload)[:240]

    def _assistant_configuration(
        self,
        *,
        assistant_kind: str,
        route: EvaluationRoute,
        metadata: dict[str, Any] | None = None,
        explicit: AssistantConfigurationSnapshot | dict[str, Any] | None = None,
    ) -> AssistantConfigurationSnapshot:
        payload = dict(metadata or {})
        default_configuration = AssistantConfigurationSnapshot()
        if isinstance(explicit, AssistantConfigurationSnapshot) and (explicit != default_configuration or 'assistant_configuration' not in payload):
            return explicit
        if isinstance(explicit, dict) and explicit:
            return AssistantConfigurationSnapshot.model_validate(explicit)
        stored = payload.get('assistant_configuration')
        if isinstance(stored, AssistantConfigurationSnapshot):
            return stored
        if isinstance(stored, dict) and stored:
            return AssistantConfigurationSnapshot.model_validate(stored)
        unresolved_fields: list[str] = []
        if str(payload.get('attachments_support') or '').strip().upper() == 'UNRESOLVED':
            unresolved_fields.append('UNRESOLVED:attachments_mode')
        resolved_assistant = assistant_kind or str(payload.get('assistant_kind') or '').strip().lower()
        return AssistantConfigurationSnapshot(
            planning_mode=str(payload.get('planning_mode') or ('with_plan' if payload.get('enable_planning') else 'without_plan')),
            attachments_mode=str(payload.get('attachments_mode') or 'without_files'),
            reasoning_level=str(payload.get('reasoning_level') or ('extended' if payload.get('deep_reasoning') else 'normal')),
            context_mode=str(payload.get('context_mode') or ('long' if len(str(payload.get('context_pack') or '')) > 1200 else 'short')),
            tools_mode=str(
                payload.get('tools_mode')
                or ('with_tools' if route in {EvaluationRoute.CODE_AGENT, EvaluationRoute.UI, EvaluationRoute.LOCAL} or payload.get('selected_tool_id') else 'without_tools')
            ),
            browser_mode=str(
                payload.get('browser_mode')
                or (
                    'with_browser'
                    if route == EvaluationRoute.UI or any(token in str(payload.get('selected_tool_id') or '').lower() for token in ('web', 'browser'))
                    else 'without_browser'
                )
            ),
            assistant_mode=str(
                payload.get('assistant_mode')
                or ('code' if resolved_assistant == 'codex' or route == EvaluationRoute.CODE_AGENT else 'general')
            ),
            origin_mode=str(
                payload.get('origin_mode')
                or ('local' if resolved_assistant in {'ollama', 'ollama_llm'} or route == EvaluationRoute.LOCAL else 'external')
            ),
            unresolved_fields=unresolved_fields,
            metadata={k: payload[k] for k in ('attachments_support',) if k in payload},
        )

    def _config_signature(self, configuration: AssistantConfigurationSnapshot) -> str:
        return '|'.join(
            [
                configuration.planning_mode,
                configuration.attachments_mode,
                configuration.reasoning_level,
                configuration.context_mode,
                configuration.tools_mode,
                configuration.browser_mode,
                configuration.assistant_mode,
                configuration.origin_mode,
            ]
        )

    def _same_configuration_runs(
        self,
        *,
        historical_runs: list[ExperimentRun],
        assistant_kind: str,
        config_signature: str,
    ) -> list[ExperimentRun]:
        resolved_assistant = str(assistant_kind or '').strip().lower()
        resolved_signature = str(config_signature or '').strip()
        return [
            run
            for run in historical_runs
            if str(run.assistant_kind or '').strip().lower() == resolved_assistant
            and str(run.config_signature or '').strip() == resolved_signature
        ]

    def _relative_vs_same_config(self, score: float, previous_runs: list[ExperimentRun]) -> float:
        if not previous_runs:
            return 1.0
        baseline = sum(item.metrics.total_score for item in previous_runs) / max(len(previous_runs), 1)
        return round(score - baseline, 4)

    def _better_than_previous(
        self,
        score: float,
        previous_same_config: list[ExperimentRun],
        historical_runs: list[ExperimentRun],
    ) -> bool:
        comparison_pool = previous_same_config or historical_runs
        if not comparison_pool:
            return False
        return score > max(item.metrics.total_score for item in comparison_pool)

    # ------------------------------------------------------------------
    # Adaptive threshold N_c (Brecha 3.3)
    # ------------------------------------------------------------------

    _Z_SCORES: dict[float, float] = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }

    def calculate_adaptive_threshold(
        self,
        domain: str | None = None,
        *,
        confidence_level: float = 0.95,
        margin_of_error: float = 0.10,
    ) -> int:
        """Calculate the minimum number of runs needed for statistical confidence.

        Uses the sample size formula for proportion estimation:
        ``n = (Z^2 * p * (1-p)) / E^2``

        Falls back to sensible defaults:
        - If < 10 total runs exist: return 3 (bootstrap mode)
        - If 10-50 runs: return calculated N_c (typically 5-15)
        - If > 50 runs: return calculated N_c (typically 10-30)
        """
        all_runs = self.repository.list_runs(domain=domain, limit=500)
        total = len(all_runs)

        if total < 10:
            return 3

        successful = sum(1 for r in all_runs if r.success)
        p = successful / max(total, 1)
        if p in (0.0, 1.0):
            p = 0.5

        z = self._Z_SCORES.get(confidence_level)
        if z is None:
            z = self._Z_SCORES[min(self._Z_SCORES, key=lambda k: abs(k - confidence_level))]

        n = math.ceil((z ** 2 * p * (1 - p)) / (margin_of_error ** 2))
        ceiling = total // 3
        return max(3, min(n, ceiling))

    def get_current_thresholds(self) -> dict[str, int]:
        """Return current adaptive thresholds per domain.

        Returns a dict mapping ``'global'`` and each ``ExperimentDomain``
        value to its calculated N_c.
        """
        from iabv_v15.domain.models import ExperimentDomain

        result: dict[str, int] = {'global': self.calculate_adaptive_threshold()}
        for dom in ExperimentDomain:
            result[dom.value] = self.calculate_adaptive_threshold(domain=dom.value)
        return result

    # ------------------------------------------------------------------
    # Training corpus generation (Brecha 3.1)
    # ------------------------------------------------------------------

    def generate_training_corpus(
        self,
        *,
        min_runs: int | None = None,
        max_age_days: int = 30,
    ) -> list[dict[str, Any]]:
        """Generate training examples from accumulated experiment runs.

        Groups runs by ``domain + suite_name`` and extracts patterns:
        which assistant_kind wins for which type of task, which route is
        faster/more reliable, and confidence calibration.

        Returns a list of training examples.
        """
        from iabv_v15.domain.models import utc_now

        if min_runs is None:
            min_runs = self.calculate_adaptive_threshold()

        cutoff = utc_now() - timedelta(days=max_age_days)
        all_runs = self.repository.list_runs(limit=500)
        recent = [r for r in all_runs if r.created_at_utc >= cutoff]

        groups: dict[str, list[ExperimentRun]] = defaultdict(list)
        for run in recent:
            key = f'{run.domain.value}:{run.suite_name}'
            groups[key].append(run)

        examples: list[dict[str, Any]] = []
        for task_type, runs in groups.items():
            if len(runs) < min_runs:
                continue
            stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {'success': 0, 'total': 0, 'latency_sum': 0}
            )
            for run in runs:
                kind = run.assistant_kind or 'unknown'
                stats[kind]['success'] += int(run.success)
                stats[kind]['total'] += 1
                stats[kind]['latency_sum'] += run.metrics.execution_ms
                stats[kind]['route'] = run.route.value

            best_kind = ''
            best_rate = -1.0
            best_latency = float('inf')
            alternatives: list[dict[str, Any]] = []

            for kind, s in stats.items():
                rate = s['success'] / max(s['total'], 1)
                avg_lat = s['latency_sum'] / max(s['total'], 1)
                if rate > best_rate or (rate == best_rate and avg_lat < best_latency):
                    if best_kind:
                        alternatives.append({
                            'assistant': best_kind,
                            'success_rate': round(best_rate, 3),
                            'avg_latency_ms': round(best_latency, 1),
                        })
                    best_kind = kind
                    best_rate = rate
                    best_latency = avg_lat
                else:
                    alternatives.append({
                        'assistant': kind,
                        'success_rate': round(rate, 3),
                        'avg_latency_ms': round(avg_lat, 1),
                    })

            examples.append({
                'task_type': task_type,
                'recommended_route': stats[best_kind].get('route', 'unknown'),
                'recommended_assistant': best_kind,
                'confidence': round(min(best_rate, 1.0), 3),
                'sample_size': stats[best_kind]['total'],
                'avg_latency_ms': round(best_latency, 1),
                'success_rate': round(best_rate, 3),
                'alternatives': alternatives,
            })

        return examples


