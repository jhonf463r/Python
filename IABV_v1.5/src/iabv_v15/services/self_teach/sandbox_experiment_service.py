from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import (
    EvaluationRoute,
    ExperimentRecommendation,
    NetworkStatusSnapshot,
    SandboxExperiment,
    SandboxExperimentVerdict,
    WorldModelSnapshot,
)
from iabv_v15.services.lab.experiment_lab import ExperimentLab


class SandboxExperimentService:
    def __init__(self, *, experiment_lab: ExperimentLab) -> None:
        self.experiment_lab = experiment_lab

    def validate_recommendation(
        self,
        recommendation: ExperimentRecommendation,
        *,
        world_model: WorldModelSnapshot,
        environment_model: Any | None = None,
        reason: str = 'manual',
    ) -> SandboxExperiment:
        metadata = dict(recommendation.metadata or {})
        ranked = [dict(item) for item in (metadata.get('ranked_configurations') or []) if isinstance(item, dict)]
        baseline_blockers = self._recommendation_blockers(
            recommendation=recommendation,
            world_model=world_model,
            environment_model=environment_model,
        )
        baseline_score = self._matching_ranked_score(
            ranked=ranked,
            route=recommendation.recommended_route.value,
            assistant_kind=recommendation.recommended_assistant_kind,
            config_signature=recommendation.recommended_config_signature,
        )
        alternative = self._best_alternative(
            ranked=ranked,
            recommendation=recommendation,
            world_model=world_model,
        )
        candidate_route = self._route_from_value(alternative.get('route')) if alternative else recommendation.recommended_route
        candidate_assistant_kind = str(
            (alternative.get('assistant_kind') if alternative else recommendation.recommended_assistant_kind) or ''
        ).strip().lower()
        candidate_config_signature = str(
            (alternative.get('config_signature') if alternative else recommendation.recommended_config_signature) or ''
        ).strip()
        candidate_score = float(
            (alternative.get('weighted_score') if alternative else baseline_score) or 0.0
        )
        evidence_strength = min(
            0.98,
            float(recommendation.confidence or 0.0) * 0.45
            + (0.35 if baseline_blockers else 0.1)
            + (0.18 if alternative else 0.0),
        )
        if baseline_blockers and alternative is not None:
            verdict = SandboxExperimentVerdict.VALID
            promote = True
            status = 'promoted'
            summary = (
                f'La ruta actual quedo bloqueada por {", ".join(baseline_blockers[:2])}. '
                f'La alternativa {candidate_assistant_kind or candidate_route.value} queda mejor alineada con el estado operativo.'
            )
        elif baseline_blockers and alternative is None:
            verdict = SandboxExperimentVerdict.UNRESOLVED
            promote = False
            status = 'observed'
            summary = 'La ruta actual quedo bloqueada, pero no encontre una alternativa con evidencia suficiente para promover.'
        elif alternative is not None and candidate_score > baseline_score + 0.08:
            verdict = SandboxExperimentVerdict.DOUBTFUL
            promote = False
            status = 'observed'
            summary = (
                f'Hay una alternativa mejor posicionada ({candidate_assistant_kind or candidate_route.value}), '
                'pero la mejora todavia no es lo bastante fuerte como para cambiar la preferencia principal.'
            )
        else:
            verdict = SandboxExperimentVerdict.VALID
            promote = False
            status = 'stable'
            summary = 'La recomendacion actual sigue siendo coherente con el historial y el estado operativo.'
        experiment = SandboxExperiment(
            subject_key=recommendation.subject_key,
            sandbox_subject_key=self._sandbox_subject_key(recommendation.subject_key),
            domain=recommendation.domain,
            hypothesis=f'Validar si {recommendation.recommended_assistant_kind or recommendation.recommended_route.value} sigue siendo la mejor via para {recommendation.subject_key}.',
            baseline_route=recommendation.recommended_route,
            baseline_assistant_kind=str(recommendation.recommended_assistant_kind or '').strip().lower(),
            baseline_config_signature=str(recommendation.recommended_config_signature or '').strip(),
            candidate_route=candidate_route,
            candidate_assistant_kind=candidate_assistant_kind,
            candidate_config_signature=candidate_config_signature,
            status=status,
            verdict=verdict,
            promote_to_primary=promote,
            evidence_strength=round(evidence_strength, 4),
            supporting_run_ids=list(recommendation.supporting_run_ids or [])[:8],
            observed_blockers=baseline_blockers,
            summary=summary,
            metadata={
                'validation_reason': reason,
                'baseline_weighted_score': round(baseline_score, 4),
                'candidate_weighted_score': round(candidate_score, 4),
                'comparison_scope_keys': list(metadata.get('comparison_scope_keys') or []),
                'ranked_configurations': ranked[:4],
                'network_status': str((world_model.network_status.status if isinstance(world_model.network_status, NetworkStatusSnapshot) else '') or ''),
            },
        )
        self._record_sandbox_run(experiment=experiment)
        if experiment.promote_to_primary:
            self._record_promotion(experiment=experiment, recommendation=recommendation)
        return experiment

    def _record_sandbox_run(self, *, experiment: SandboxExperiment) -> None:
        success = experiment.verdict in {SandboxExperimentVerdict.VALID, SandboxExperimentVerdict.DOUBTFUL}
        precision = experiment.evidence_strength if success else max(0.18, experiment.evidence_strength * 0.5)
        robustness = max(0.2, 1.0 - (len(experiment.observed_blockers) * 0.15))
        self.experiment_lab.record_outcome(
            domain=experiment.domain,
            objective=experiment.hypothesis,
            subject_key=experiment.sandbox_subject_key,
            route=experiment.candidate_route,
            candidate_label=experiment.candidate_assistant_kind or experiment.candidate_route.value,
            candidate_id=experiment.experiment_id,
            success=success,
            observed_summary=experiment.summary,
            expected_summary='Validar preferencia historica sin contaminar la ruta principal.',
            precision=precision,
            robustness=robustness,
            reuse_score=min(1.0, len(experiment.supporting_run_ids) / 5.0),
            user_progress=0.42 if experiment.promote_to_primary else 0.18,
            execution_ms=0,
            evidence_refs=list(experiment.supporting_run_ids or [])[:8],
            metadata={
                'assistant_kind': experiment.candidate_assistant_kind,
                'config_signature': experiment.candidate_config_signature,
                'comparison_scope_key': experiment.subject_key,
                'source_trace_ids': list(experiment.supporting_run_ids or [])[:8],
                'proposal_summary': experiment.hypothesis,
                'outcome_summary': experiment.summary,
                'learning_source': 'sandbox_experiment',
                'isolated_experiment': True,
                'sandbox_experiment_id': experiment.experiment_id,
                'validation_verdict': experiment.verdict.value,
                'validation_reason': str(experiment.metadata.get('validation_reason') or ''),
                'observed_blockers': list(experiment.observed_blockers or []),
                'blocked': bool(experiment.observed_blockers),
                'external_state_flags': list(experiment.observed_blockers or []),
                'source_subject_key': experiment.subject_key,
            },
            suite_name='sandbox_experiment',
        )

    def _record_promotion(self, *, experiment: SandboxExperiment, recommendation: ExperimentRecommendation) -> None:
        self.experiment_lab.record_outcome(
            domain=recommendation.domain,
            objective=experiment.hypothesis,
            subject_key=recommendation.subject_key,
            route=experiment.candidate_route,
            candidate_label=experiment.candidate_assistant_kind or experiment.candidate_route.value,
            candidate_id=experiment.experiment_id,
            success=True,
            observed_summary=experiment.summary,
            expected_summary='Promover solo aprendizaje validado en sandbox.',
            precision=min(0.98, 0.72 + experiment.evidence_strength * 0.2),
            robustness=max(0.55, experiment.evidence_strength),
            reuse_score=min(1.0, len(experiment.supporting_run_ids) / 4.0),
            user_progress=0.58,
            execution_ms=0,
            evidence_refs=list(experiment.supporting_run_ids or [])[:8],
            metadata={
                'assistant_kind': experiment.candidate_assistant_kind,
                'config_signature': experiment.candidate_config_signature,
                'comparison_scope_key': recommendation.subject_key,
                'source_trace_ids': list(experiment.supporting_run_ids or [])[:8],
                'proposal_summary': experiment.hypothesis,
                'outcome_summary': experiment.summary,
                'learning_source': 'sandbox_promotion',
                'sandbox_experiment_id': experiment.experiment_id,
                'validation_verdict': experiment.verdict.value,
                'promotion_reason': experiment.summary,
                'source_subject_key': experiment.sandbox_subject_key,
                'blocked': False,
                'external_state_flags': [],
            },
            suite_name='sandbox_promotion',
        )

    def _best_alternative(
        self,
        *,
        ranked: list[dict[str, Any]],
        recommendation: ExperimentRecommendation,
        world_model: WorldModelSnapshot,
    ) -> dict[str, Any] | None:
        baseline_assistant = str(recommendation.recommended_assistant_kind or '').strip().lower()
        baseline_signature = str(recommendation.recommended_config_signature or '').strip()
        for item in ranked:
            route = str(item.get('route') or '').strip()
            assistant_kind = str(item.get('assistant_kind') or '').strip().lower()
            config_signature = str(item.get('config_signature') or '').strip()
            if route == recommendation.recommended_route.value and assistant_kind == baseline_assistant and config_signature == baseline_signature:
                continue
            if self._assistant_blocked(assistant_kind=assistant_kind, world_model=world_model):
                continue
            return item
        return None

    def _matching_ranked_score(
        self,
        *,
        ranked: list[dict[str, Any]],
        route: str,
        assistant_kind: str,
        config_signature: str,
    ) -> float:
        normalized_assistant = str(assistant_kind or '').strip().lower()
        normalized_signature = str(config_signature or '').strip()
        for item in ranked:
            if (
                str(item.get('route') or '').strip() == str(route or '').strip()
                and str(item.get('assistant_kind') or '').strip().lower() == normalized_assistant
                and str(item.get('config_signature') or '').strip() == normalized_signature
            ):
                return float(item.get('weighted_score') or item.get('score') or 0.0)
        if not ranked:
            return 0.0
        first = dict(ranked[0] or {})
        return float(first.get('weighted_score') or first.get('score') or 0.0)

    def _recommendation_blockers(
        self,
        *,
        recommendation: ExperimentRecommendation,
        world_model: WorldModelSnapshot,
        environment_model: Any | None,
    ) -> list[str]:
        blockers: list[str] = []
        assistant_kind = str(recommendation.recommended_assistant_kind or '').strip().lower()
        route_value = recommendation.recommended_route.value
        for block in (world_model.block_records or []):
            target = str(block.target_scope or '').strip().lower()
            block_assistant = str(block.assistant_kind or '').strip().lower()
            if block_assistant and assistant_kind and block_assistant != assistant_kind:
                continue
            if target and target not in {'consult_external', f'consult_{assistant_kind}', route_value, 'heavy_local_model'}:
                continue
            probe = str(block.block_type or block.reason or '').strip().lower()
            if probe and probe not in blockers:
                blockers.append(probe)
        network_status = str(world_model.network_status.status or '').strip().lower()
        if assistant_kind in {'chatgpt', 'claude'} and network_status == 'desconectado':
            blockers.append('network_disconnected')
        if environment_model is not None and recommendation.recommended_route == EvaluationRoute.LOCAL:
            for risk in getattr(environment_model, 'risk_signals', []) or []:
                kind = str(getattr(risk, 'kind', '') or '').strip().lower()
                severity = str(getattr(getattr(risk, 'severity', ''), 'value', getattr(risk, 'severity', '')) or '').strip().lower()
                if severity in {'high', 'critical'} and kind in {'cpu_pressure', 'ram_pressure', 'ram_critical', 'throttling_detected'}:
                    if kind not in blockers:
                        blockers.append(kind)
        return blockers

    def _assistant_blocked(self, *, assistant_kind: str, world_model: WorldModelSnapshot) -> bool:
        normalized = str(assistant_kind or '').strip().lower()
        if not normalized:
            return False
        for block in (world_model.block_records or []):
            target = str(block.target_scope or '').strip().lower()
            block_assistant = str(block.assistant_kind or '').strip().lower()
            if block_assistant == normalized or target == f'consult_{normalized}':
                return True
        return False

    def _sandbox_subject_key(self, subject_key: str) -> str:
        probe = str(subject_key or '').strip() or 'general'
        return f'sandbox:{probe}'

    def _route_from_value(self, value: Any) -> EvaluationRoute:
        probe = str(value or '').strip()
        for route in EvaluationRoute:
            if route.value == probe:
                return route
        return EvaluationRoute.FALLBACK
