from __future__ import annotations

from collections import Counter
from typing import Any

from iabv_v15.domain.models import EvolutionSnapshot, ImprovementProposal, RunRecord, RunStatus, SelfCheckResult
from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService
from iabv_v15.services.training.pbt_control_service import PBTControlService


class SelfCheckOrchestrator:
    def __init__(
        self,
        *,
        role_router: LocalRoleRouter,
        embedding_service: EmbeddingIndexService,
        sql_service: SqlQueryAdvisorService,
        episode_repository: EpisodeRepository,
        pbt_service: PBTControlService | None = None,
    ) -> None:
        self.role_router = role_router
        self.embedding_service = embedding_service
        self.sql_service = sql_service
        self.episode_repository = episode_repository
        self.pbt_service = pbt_service

    def run_light_checks_for_run(self, run_record: RunRecord, evidence_refs: list[Any]) -> list[SelfCheckResult]:
        checks: list[SelfCheckResult] = []
        health = self.role_router.health_snapshot()
        core_ready = any(item.available for item in health if item.provider_name in {'Ollama', 'Ollama Vision'})
        checks.append(
            SelfCheckResult(
                check_name='stack_local',
                status=RunStatus.SUCCESS if core_ready else RunStatus.FAILED,
                detail='Stack local disponible.' if core_ready else 'No hay proveedor local listo para la ejecucion.',
            )
        )
        consistency_ok = bool(run_record.result.summary.strip()) and run_record.result.request_id == run_record.request.request_id
        checks.append(
            SelfCheckResult(
                check_name='request_route_result_consistency',
                status=RunStatus.SUCCESS if consistency_ok else RunStatus.PARTIAL,
                detail='La respuesta coincide con la solicitud y trae resumen.' if consistency_ok else 'La respuesta llego con evidencia incompleta o resumen vacio.',
            )
        )
        evidence_ok = bool(evidence_refs)
        checks.append(
            SelfCheckResult(
                check_name='evidence_ready',
                status=RunStatus.SUCCESS if evidence_ok else RunStatus.PARTIAL,
                detail='La corrida dejo evidencia verificable.' if evidence_ok else 'La corrida no dejo evidencia suficiente para auditoria.',
            )
        )
        fallback_status = RunStatus.PARTIAL if (run_record.result.used_fallback or run_record.status == RunStatus.PARTIAL) else RunStatus.SUCCESS
        checks.append(
            SelfCheckResult(
                check_name='fallback_and_confidence',
                status=fallback_status,
                detail=(
                    'Se uso fallback o la confianza quedo reducida; conviene revisar el stack y el prompt.'
                    if fallback_status != RunStatus.SUCCESS
                    else 'No hubo fallback relevante en la ejecucion.'
                ),
            )
        )
        return checks

    def run_light_checks_for_teaching(self, metrics: dict[str, Any], evidence_refs: list[Any]) -> list[SelfCheckResult]:
        visible_steps = int(metrics.get('visible_step_count', 0) or 0)
        screenshots = int(metrics.get('screenshot_count', 0) or 0)
        replay_ok = bool(metrics.get('has_recoverable_replay'))
        checks = [
            SelfCheckResult(
                check_name='visible_capture',
                status=RunStatus.SUCCESS if visible_steps > 0 or screenshots > 0 else RunStatus.PARTIAL,
                detail=(
                    f'Captura visible disponible con {visible_steps} pasos y {screenshots} capturas.'
                    if visible_steps > 0 or screenshots > 0
                    else 'La ensenanza quedo sin pasos visibles ni capturas; revisar bridge o politica de screenshots.'
                ),
            ),
            SelfCheckResult(
                check_name='replay_recoverable',
                status=RunStatus.SUCCESS if replay_ok else RunStatus.FAILED,
                detail='El replay puede reconstruirse.' if replay_ok else 'No hay replay recuperable para esta ensenanza.',
            ),
            SelfCheckResult(
                check_name='evidence_ready',
                status=RunStatus.SUCCESS if evidence_refs else RunStatus.PARTIAL,
                detail='La ensenanza dejo artefactos y referencias auditables.' if evidence_refs else 'No hubo evidencia suficiente para el dossier.',
            ),
        ]
        return checks

    def run_deep_suite(self) -> EvolutionSnapshot:
        health = self.role_router.health_snapshot()
        schema = self.sql_service.schema_overview()
        index_state = self.embedding_service.describe_index()
        episodes = self.episode_repository.list_recent(limit=40)
        pbt_state = self.pbt_service.load_state() if self.pbt_service is not None else {}
        status_cards = [
            {
                'title': 'Stack local',
                'value': sum(1 for item in health if item.available),
                'detail': ', '.join(f"{item.provider_name}:{item.status.value}" for item in health),
            },
            {
                'title': 'Embeddings',
                'value': int(index_state.get('knowledge_count', 0) or 0),
                'detail': f"modo {index_state.get('index_mode', 'desconocido')} | ultima consulta: {index_state.get('last_query', '')}",
            },
            {
                'title': 'SQL readonly',
                'value': len(schema),
                'detail': 'Tablas visibles: ' + ', '.join(sorted(schema.keys())),
            },
            {
                'title': 'Replay y ensenanzas',
                'value': len(episodes),
                'detail': 'Episodios recientes disponibles para auditoria local.',
            },
            {
                'title': 'PBT',
                'value': int(pbt_state.get('generation', 0) or 0),
                'detail': pbt_state.get('summary', 'Sin ejecuciones PBT aun.'),
            },
        ]
        repeated = Counter()
        if not health or not any(item.available for item in health if item.provider_name == 'Ollama'):
            repeated['stack_local'] += 1
        backlog: list[ImprovementProposal] = []
        if repeated['stack_local']:
            backlog.append(
                ImprovementProposal(
                    title='Verificar backend local principal',
                    rationale='El stack local no paso el autodiagnostico profundo.',
                    recommended_change='Confirmar que Ollama siga respondiendo y que qwen3:8b este listo antes de depurar capas superiores.',
                    suggested_tests=['refreshProviderHealth', 'consulta simple en Centro de Control'],
                    tradeoffs=['Sin backend local listo, los siguientes checks pierden valor diagnostico.'],
                    priority_score=90,
                )
            )
        return EvolutionSnapshot(
            summary='Autodiagnostico profundo completado sobre stack local, embeddings, SQL readonly y replay reciente.',
            status_cards=status_cards,
            recent_failures=[],
            repeated_issues=[{'issue_hint': key, 'count': value} for key, value in repeated.items() if value],
            backlog=backlog,
        )
