from __future__ import annotations

from collections import Counter
from typing import Iterable

from iabv_v15.domain.models import EpisodeManifest, RunRecord, RunStatus, SessionArtifact


class TeachingGapAnalyzer:
    def analyze(
        self,
        *,
        episodes: Iterable[EpisodeManifest],
        artifacts: Iterable[SessionArtifact],
        runs: Iterable[RunRecord],
        knowledge_count: int,
    ) -> dict[str, object]:
        episode_list = list(episodes)
        artifact_list = list(artifacts)
        run_list = list(runs)
        failing_runs = [run for run in run_list if run.status in {RunStatus.FAILED, RunStatus.PARTIAL}]
        task_counter = Counter((run.result.inferred_task or run.request.user_goal).strip() for run in failing_runs if (run.result.inferred_task or run.request.user_goal).strip())

        priorities: list[dict[str, object]] = []
        if not episode_list:
            priorities.append(
                {
                    'label': 'Ensenar el flujo base de acceso',
                    'reason': 'Aun no hay episodios. La prioridad mas alta es ensenar login, navegacion inicial y confirmacion.',
                    'score': 100,
                }
            )
        if episode_list and knowledge_count < len(episode_list):
            priorities.append(
                {
                    'label': 'Confirmar intenciones de sesiones recientes',
                    'reason': 'Hay mas episodios que conocimiento confirmado. Hace falta convertir demostraciones en tareas reutilizables.',
                    'score': 88,
                }
            )
        if artifact_list and not any('api' in artifact.kind or artifact.metadata.get('capture_channel') == 'api' for artifact in artifact_list):
            priorities.append(
                {
                    'label': 'Ensenar una ruta con trazas API visibles',
                    'reason': 'Las capturas actuales no estan consolidando suficiente senal API para generalizar mejor.',
                    'score': 75,
                }
            )
        for task_name, count in task_counter.most_common(3):
            priorities.append(
                {
                    'label': f'Reforzar tarea: {task_name}',
                    'reason': f'Esta tarea concentro {count} ejecuciones parciales o fallidas y conviene reensenarla con mas contexto.',
                    'score': 70 + min(count * 5, 20),
                }
            )
        if artifact_list and not any(artifact.metadata.get('capture_channel') == 'background' for artifact in artifact_list):
            priorities.append(
                {
                    'label': 'Capturar segundo plano con DOM y storage',
                    'reason': 'Falta senal estructural del navegador para inferir mejor intenciones y estados.',
                    'score': 69,
                }
            )

        ranked = sorted(priorities, key=lambda item: int(item['score']), reverse=True)
        follow_up_teachings = [str(item['label']) for item in ranked[:4]]
        summary = ranked[0]['reason'] if ranked else 'No hay huecos criticos. Puedes seguir afinando tareas de alto valor.'
        return {
            'summary': summary,
            'follow_up_teachings': follow_up_teachings,
            'priorities': ranked,
        }
