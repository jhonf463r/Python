from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import IncidentQuery
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.infra.persistence.session_artifact_repository import SessionArtifactRepository
from iabv_v15.services.development.development_assist_service import DevelopmentAssistService
from iabv_v15.services.evolution.evolution_review_service import EvolutionReviewService
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.roles.analytics_strategy_service import AnalyticsStrategyService
from iabv_v15.services.roles.teaching_gap_analyzer import TeachingGapAnalyzer
from iabv_v15.services.training.pbt_control_service import PBTControlService


class EngineeringReviewService:
    def __init__(
        self,
        *,
        workspace_root: str,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        artifact_repository: SessionArtifactRepository,
        analytics_service: AnalyticsStrategyService,
        teaching_gap_analyzer: TeachingGapAnalyzer,
        pbt_service: PBTControlService,
        development_assist_service: DevelopmentAssistService,
        execution_dossier_repository: ExecutionDossierRepository | None = None,
        evolution_review_service: EvolutionReviewService | None = None,
        incident_packet_service: IncidentPacketService | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.artifact_repository = artifact_repository
        self.analytics_service = analytics_service
        self.teaching_gap_analyzer = teaching_gap_analyzer
        self.pbt_service = pbt_service
        self.development_assist_service = development_assist_service
        self.execution_dossier_repository = execution_dossier_repository
        self.evolution_review_service = evolution_review_service
        self.incident_packet_service = incident_packet_service
        self._context_cache: dict[str, Any] | None = None
        self._context_cache_ts: float = 0.0
        self._context_cache_ttl: float = 60.0

    def build_project_context(self, *, force: bool = False) -> dict[str, Any]:
        """Build project context with TTL cache.

        Reads ~1120 items from disk (episodes, knowledge, runs, artifacts,
        dossiers) and calls several analysis services.  Caching with a 60s
        TTL avoids redundant I/O when called multiple times in quick
        succession (e.g. ``_refresh_development_packet`` on every chat msg).
        """
        now = time.monotonic()
        if (
            not force
            and self._context_cache is not None
            and (now - self._context_cache_ts) < self._context_cache_ttl
        ):
            return self._context_cache
        episodes = self.episode_repository.list_recent(limit=200)
        knowledge = self.knowledge_repository.list_recent(limit=200)
        runs = self.run_repository.list_recent(limit=200)
        artifacts = self.artifact_repository.list_recent(limit=400)
        analytics = self.analytics_service.build_report()
        gaps = self.teaching_gap_analyzer.analyze(
            episodes=episodes,
            artifacts=artifacts,
            runs=runs,
            knowledge_count=len(knowledge),
        )
        pbt_state = self.pbt_service.load_state()
        dossiers = self.execution_dossier_repository.list_recent(limit=120) if self.execution_dossier_repository is not None else []
        project_health = self.evolution_review_service.build_project_health() if self.evolution_review_service is not None else None
        backlog = self.evolution_review_service.build_improvement_backlog(limit=8) if self.evolution_review_service is not None else []
        ctx = {
            'episodes': len(episodes),
            'knowledge_items': len(knowledge),
            'runs': len(runs),
            'artifacts': len(artifacts),
            'dossiers': len(dossiers),
            'analytics': analytics,
            'teaching_gaps': gaps,
            'pbt_state': pbt_state,
            'project_health': project_health.model_dump(mode='json') if project_health is not None else {},
            'improvement_backlog': [item.model_dump(mode='json') for item in backlog],
        }
        self._context_cache = ctx
        self._context_cache_ts = now
        return ctx

    def build_codex_packet(self, *, user_goal: str, selected_role_title: str) -> str:
        context = self.build_project_context()
        packet = self.development_assist_service.build_codex_packet(
            user_goal=user_goal,
            selected_role_title=selected_role_title,
            project_context=context,
        )
        health = context.get('project_health') or {}
        backlog = context.get('improvement_backlog') or []
        if not health and not backlog:
            return packet
        extra_lines = ['\nCentro evolutivo:']
        if health:
            extra_lines.append(f"- resumen: {health.get('summary', 'Sin resumen evolutivo.')}")
        if backlog:
            extra_lines.append('- backlog sugerido: ' + ', '.join(item.get('title', '') for item in backlog[:3] if item.get('title')))
        return packet + '\n'.join(extra_lines) + '\n'

    def build_incident_packet(self, query: IncidentQuery) -> str:
        if self.incident_packet_service is None:
            return 'Paquete para Codex - Incidente IABV v1.5\n\nLa capa evolutiva todavia no esta inicializada en este contexto.'
        return self.incident_packet_service.build_codex_packet_for_issue(query)
