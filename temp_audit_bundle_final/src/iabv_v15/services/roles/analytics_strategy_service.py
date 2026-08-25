from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from iabv_v15.domain.models import RunStatus
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository


class AnalyticsStrategyService:
    def __init__(
        self,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        artifact_repository: SessionArtifactRepository,
    ) -> None:
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.artifact_repository = artifact_repository

    def collect_metrics(self) -> dict[str, Any]:
        episodes = self.episode_repository.list_recent(limit=500)
        knowledge = self.knowledge_repository.list_recent(limit=500)
        runs = self.run_repository.list_recent(limit=500)
        artifacts = self.artifact_repository.list_recent(limit=1000)
        statuses = Counter(run.status.value for run in runs)
        confidences = [run.result.confidence for run in runs]
        top_tasks = Counter((run.result.inferred_task or run.request.user_goal).strip() for run in runs if (run.result.inferred_task or run.request.user_goal).strip())
        return {
            'episodes': len(episodes),
            'knowledge_items': len(knowledge),
            'runs': len(runs),
            'artifacts': len(artifacts),
            'success_runs': statuses.get(RunStatus.SUCCESS.value, 0),
            'partial_runs': statuses.get(RunStatus.PARTIAL.value, 0),
            'failed_runs': statuses.get(RunStatus.FAILED.value, 0),
            'average_confidence': round(mean(confidences), 2) if confidences else 0.0,
            'top_tasks': top_tasks.most_common(5),
            'artifact_channels': Counter(artifact.metadata.get('capture_channel', 'unknown') for artifact in artifacts).most_common(),
        }

    def build_report(self) -> dict[str, Any]:
        metrics = self.collect_metrics()
        focus = 'reforzar calidad de conocimiento' if metrics['knowledge_items'] < max(metrics['episodes'], 1) else 'mejorar conversion a ejecucion'
        summary = (
            f"Episodios {metrics['episodes']}, conocimiento {metrics['knowledge_items']}, corridas {metrics['runs']} "
            f"y confianza media {metrics['average_confidence']}. La prioridad sugerida es {focus}."
        )
        if metrics['failed_runs'] or metrics['partial_runs']:
            summary += f" Hay {metrics['failed_runs']} fallos y {metrics['partial_runs']} parciales que conviene reensenar."
        actions = [
            'Consolidar tareas con mas episodios que conocimiento confirmado.' if metrics['knowledge_items'] < metrics['episodes'] else 'Mantener el ratio entre episodios y conocimiento.',
            'Reensenar tareas con ejecuciones parciales.' if metrics['partial_runs'] else 'Aumentar el volumen de ejecuciones reales para medir calidad.',
            'Usar analytics locales para comparar progreso antes de cambiar prompts o umbrales.',
        ]
        return {
            'summary': summary,
            'metrics': metrics,
            'recommended_actions': actions,
            'sources': ['tabla:episodes', 'tabla:knowledge_items', 'tabla:run_records', 'tabla:session_artifacts'],
        }
