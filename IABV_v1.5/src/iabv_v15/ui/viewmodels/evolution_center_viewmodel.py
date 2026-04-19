from __future__ import annotations

import threading
from typing import Any

from iabv_v15.domain.models import InferenceRequest, IncidentQuery, RunStatus, TaskRole
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.services.evolution.evolution_review_service import EvolutionReviewService
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.evolution.self_check_orchestrator import SelfCheckOrchestrator
from iabv_v15.ui.qt import QObject, Property, QGuiApplication, Signal, Slot


class EvolutionCenterViewModel(QObject):
    dataChanged = Signal()
    taskResolved = Signal(str, object)
    taskFailed = Signal(str, str)

    # Señales evolutivas para diálogos UI (Task B)
    credentialPromptRequested = Signal(dict)  # {domain, reason, username_hint}
    clarificationRequested = Signal(dict)     # {id, question, options, context}
    missingDependencyRequested = Signal(dict) # {package_name, manager, reason}
    backgroundActivityChanged = Signal(dict)  # {text, progress, status, details}
    providerHealthChanged = Signal(list)       # [ProviderHealth]

    def __init__(
        self,
        *,
        dossier_repository: ExecutionDossierRepository,
        hidden_incident_repository: HiddenIncidentRepository,
        evolution_review_service: EvolutionReviewService,
        incident_packet_service: IncidentPacketService,
        self_check_orchestrator: SelfCheckOrchestrator,
        pending_issue_repository: PendingIssueRepository | None = None,
        scenario_run_repository: ScenarioRunRepository | None = None,
        experiment_lab_repository: ExperimentLabRepository | None = None,
        tool_record_repository: Any | None = None,
        tool_teach_service: Any | None = None,
        environment_self_awareness_service: Any | None = None,
        world_model_service: Any | None = None,
        autonomous_validation_cycle: Any | None = None,
        portable_context_service: Any | None = None,
        self_examination_service: Any | None = None,
    ) -> None:
        super().__init__()
        self.dossier_repository = dossier_repository
        self.hidden_incident_repository = hidden_incident_repository
        self.evolution_review_service = evolution_review_service
        self.incident_packet_service = incident_packet_service
        self.self_check_orchestrator = self_check_orchestrator
        self.pending_issue_repository = pending_issue_repository
        self.scenario_run_repository = scenario_run_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.tool_record_repository = tool_record_repository
        self.tool_teach_service = tool_teach_service
        self.environment_self_awareness_service = environment_self_awareness_service
        self.world_model_service = world_model_service
        self.autonomous_validation_cycle = autonomous_validation_cycle
        self.portable_context_service = portable_context_service
        self.self_examination_service = self_examination_service
        self._working = False
        self._status_text = 'La capa evolutiva esta lista para resumir fallos, parciales e incidentes invisibles.'
        self._health_snapshot: dict[str, Any] = {}
        self._recent_dossiers: list[dict[str, Any]] = []
        self._recent_incidents: list[dict[str, Any]] = []
        self._incident_filter = 'all'
        self._improvement_backlog: list[dict[str, Any]] = []
        self._recent_pending_issues: list[dict[str, Any]] = []
        self._known_tool_cards: list[dict[str, Any]] = []
        self._ia_comparisons: list[dict[str, Any]] = []
        self._environment_self_model: dict[str, Any] = {}
        self._world_model: dict[str, Any] = {}
        self._autonomous_validation: dict[str, Any] = {}
        self._portable_context: dict[str, Any] = {}
        self._portable_context_brief = 'Todavia no he exportado un contexto portable desde esta vista.'
        self._tool_evolution_panel: dict[str, Any] = {}
        self._self_examination: dict[str, Any] = {}
        self._self_examination_brief = 'Todavia no he generado una autoexaminacion operativa desde esta vista.'
        self._latest_tool_status = 'Todavia no he probado ninguna herramienta desde esta vista.'
        self._selected_dossier: dict[str, Any] = {}
        self._selected_incident: dict[str, Any] = {}
        self._pinned_dossier_selection = False
        self._pinned_incident_selection = False
        self._evidence_preview = 'Selecciona un incidente o dossier para ver evidencia relacionada.'
        self._latest_packet = 'Todavia no hay un paquete de incidente seleccionado.'
        self._clipboard_notice = 'Nada copiado aun.'
        self.taskResolved.connect(self._apply_result)
        self.taskFailed.connect(self._apply_failure)
        self.refresh()

    def get_working(self) -> bool:
        return self._working

    def get_status_text(self) -> str:
        return self._status_text

    def get_health_snapshot(self) -> dict[str, Any]:
        return self._health_snapshot

    def get_recent_dossiers(self) -> list[dict[str, Any]]:
        return self._recent_dossiers

    def get_recent_incidents(self) -> list[dict[str, Any]]:
        return self._recent_incidents

    def get_incident_filter(self) -> str:
        return self._incident_filter

    def get_improvement_backlog(self) -> list[dict[str, Any]]:
        return self._improvement_backlog

    def get_recent_pending_issues(self) -> list[dict[str, Any]]:
        return self._recent_pending_issues

    def get_known_tool_cards(self) -> list[dict[str, Any]]:
        return self._known_tool_cards

    def get_ia_comparisons(self) -> list[dict[str, Any]]:
        return self._ia_comparisons

    def get_environment_self_model(self) -> dict[str, Any]:
        return self._environment_self_model

    def get_world_model(self) -> dict[str, Any]:
        return self._world_model

    def get_autonomous_validation(self) -> dict[str, Any]:
        return self._autonomous_validation

    def get_portable_context(self) -> dict[str, Any]:
        return self._portable_context

    def get_portable_context_brief(self) -> str:
        return self._portable_context_brief

    def get_tool_evolution_panel(self) -> dict[str, Any]:
        return self._tool_evolution_panel

    def get_self_examination(self) -> dict[str, Any]:
        return self._self_examination

    def get_self_examination_brief(self) -> str:
        return self._self_examination_brief

    def get_latest_tool_status(self) -> str:
        return self._latest_tool_status

    def get_selected_dossier(self) -> dict[str, Any]:
        return self._selected_dossier

    def get_selected_incident(self) -> dict[str, Any]:
        return self._selected_incident

    def get_evidence_preview(self) -> str:
        return self._evidence_preview

    def get_latest_packet(self) -> str:
        return self._latest_packet

    def get_clipboard_notice(self) -> str:
        return self._clipboard_notice

    @Slot()
    def refresh(self) -> None:
        snapshot = self.evolution_review_service.build_project_health()
        dossiers = [item.model_dump(mode='json') for item in self.dossier_repository.list_recent(limit=24)]
        incidents = [item.model_dump(mode='json') for item in self.hidden_incident_repository.list_recent(limit=30)]
        filtered_incidents = self._filter_incidents(incidents, self._incident_filter)
        backlog = [item.model_dump(mode='json') for item in self.evolution_review_service.build_improvement_backlog(limit=8)]
        pending = [item.model_dump(mode='json') for item in self.pending_issue_repository.list_recent(limit=10)] if self.pending_issue_repository is not None else []
        tool_cards = [item.model_dump(mode='json') for item in self.tool_record_repository.list_cards()] if self.tool_record_repository is not None else []
        ia_comparisons = self._build_ia_comparisons()
        environment_self_model = (
            self.environment_self_awareness_service.current_model().model_dump(mode='json')
            if self.environment_self_awareness_service is not None
            else {}
        )
        world_model = (
            self.world_model_service.current_model().model_dump(mode='json')
            if self.world_model_service is not None
            else {}
        )
        autonomous_validation = (
            self.autonomous_validation_cycle.current_snapshot().model_dump(mode='json')
            if self.autonomous_validation_cycle is not None
            else {}
        )
        portable_context = (
            self.portable_context_service.current_package(refresh=False).model_dump(mode='json')
            if self.portable_context_service is not None and hasattr(self.portable_context_service, 'current_package')
            else {}
        )
        self_examination = (
            self.self_examination_service.current_review(refresh=False).model_dump(mode='json')
            if self.self_examination_service is not None and hasattr(self.self_examination_service, 'current_review')
            else {}
        )
        self._health_snapshot = snapshot.model_dump(mode='json')
        self._recent_dossiers = dossiers
        self._recent_incidents = filtered_incidents
        self._improvement_backlog = backlog
        self._recent_pending_issues = pending
        self._known_tool_cards = tool_cards
        self._ia_comparisons = ia_comparisons
        self._environment_self_model = environment_self_model
        self._world_model = world_model
        self._autonomous_validation = autonomous_validation
        self._portable_context = portable_context
        self._portable_context_brief = str(portable_context.get('assistant_brief') or '').strip() or self._portable_context_brief
        self._tool_evolution_panel = self._build_tool_evolution_panel(portable_context=portable_context, autonomous_validation=autonomous_validation)
        self._self_examination = self_examination
        self._self_examination_brief = str(self_examination.get('assistant_brief') or '').strip() or self._self_examination_brief
        if dossiers:
            if self._pinned_dossier_selection:
                current_id = self._selected_dossier.get('dossier_id') if self._selected_dossier else ''
                self._selected_dossier = next((item for item in dossiers if item.get('dossier_id') == current_id), dossiers[0])
            else:
                self._selected_dossier = dossiers[0]
        else:
            self._selected_dossier = {}
            self._pinned_dossier_selection = False
        if filtered_incidents:
            if self._pinned_incident_selection:
                current_incident_id = self._selected_incident.get('incident_id') if self._selected_incident else ''
                self._selected_incident = next((item for item in filtered_incidents if item.get('incident_id') == current_incident_id), filtered_incidents[0])
            else:
                self._selected_incident = filtered_incidents[0]
        else:
            self._selected_incident = {}
            self._pinned_incident_selection = False
        self._latest_packet = self._build_current_packet()
        self._evidence_preview = self._build_evidence_preview()
        self._status_text = snapshot.summary
        validation_summary = str((autonomous_validation or {}).get('summary') or '').strip()
        if validation_summary:
            self._status_text = f'{self._status_text} | Validacion autonoma: {validation_summary}'
        self.dataChanged.emit()

    def _build_tool_evolution_panel(self, *, portable_context: dict[str, Any], autonomous_validation: dict[str, Any]) -> dict[str, Any]:
        metadata = dict((portable_context or {}).get('metadata') or {})
        tool_evolution_summary = dict(metadata.get('tool_evolution_summary') or {})
        decision_summary = dict(metadata.get('tool_evolution_decision_summary') or {})
        tool_discovery_summary = dict(metadata.get('tool_discovery_summary') or {})
        winning_by_problem = dict(tool_evolution_summary.get('winning_by_problem') or decision_summary.get('winning_by_problem') or {})
        in_validation = list(tool_evolution_summary.get('in_validation') or decision_summary.get('in_validation') or [])
        discoveries_recent = list(tool_discovery_summary.get('active_signals') or [])[:4]
        if not discoveries_recent:
            discoveries_recent = list(tool_discovery_summary.get('promoted_signals') or [])[:4]
        if not discoveries_recent:
            discoveries_recent = list(tool_discovery_summary.get('in_validation_signals') or [])[:4]
        latest_decisions = list(tool_evolution_summary.get('recent_decisions') or decision_summary.get('recent_decisions') or [])[:4]
        if not latest_decisions:
            latest_decisions = list(metadata.get('tool_evolution_validated_proposals') or [])[:4]
        discarded = list(tool_evolution_summary.get('discarded_proposals') or [])[:4]
        unresolved_fields = [
            str(item).strip()
            for item in list(tool_evolution_summary.get('unresolved_fields') or [])
            + list(decision_summary.get('unresolved_fields') or [])
            + list(tool_discovery_summary.get('unresolved_fields') or [])
            if str(item).strip()
        ]
        summary_parts: list[str] = []
        if winning_by_problem:
            summary_parts.append(f'ganadores {len(winning_by_problem)}')
        if in_validation:
            summary_parts.append(f'en validacion {len(in_validation)}')
        if discoveries_recent:
            summary_parts.append(f'discoveries {len(discoveries_recent)}')
        if latest_decisions:
            summary_parts.append(f'ultimas decisiones {len(latest_decisions)}')
        summary = ' | '.join(summary_parts) if summary_parts else str((autonomous_validation or {}).get('summary') or 'Sin estado evolutivo fuerte confirmado.')
        if not summary_parts and not unresolved_fields:
            unresolved_fields = ['UNRESOLVED:tool_evolution_panel']
        return {
            'summary': summary,
            'winning_by_problem': winning_by_problem,
            'in_validation': in_validation,
            'discoveries_recent': discoveries_recent,
            'latest_decisions': latest_decisions,
            'discarded': discarded,
            'unresolved_fields': unresolved_fields,
        }

    @Slot(str)
    def selectDossier(self, dossier_id: str) -> None:
        selected = next((item for item in self._recent_dossiers if item.get('dossier_id') == dossier_id), None)
        if selected is None:
            return
        self._selected_dossier = selected
        self._pinned_dossier_selection = True
        self._selected_incident = {}
        self._pinned_incident_selection = False
        self._latest_packet = self._build_current_packet()
        self._evidence_preview = self._build_evidence_preview()
        self._status_text = f'Dossier seleccionado: {selected.get("title", "sin titulo")}'
        self.dataChanged.emit()

    @Slot(str)
    def setIncidentFilter(self, filter_key: str) -> None:
        self._incident_filter = filter_key or 'all'
        self._pinned_incident_selection = False
        self.refresh()

    @Slot(str)
    def selectIncident(self, incident_id: str) -> None:
        selected = next((item for item in self._recent_incidents if item.get('incident_id') == incident_id), None)
        if selected is None:
            return
        self._selected_incident = selected
        self._pinned_incident_selection = True
        self._selected_dossier = {}
        self._pinned_dossier_selection = False
        self._latest_packet = self._build_current_packet()
        self._evidence_preview = self._build_evidence_preview()
        self._status_text = f'Incidente seleccionado: {selected.get("incident_kind", "sin tipo")}'
        self.dataChanged.emit()

    @Slot()
    def viewIncidentEvidence(self) -> None:
        self._evidence_preview = self._build_evidence_preview()
        self.dataChanged.emit()

    @Slot()
    def runDeepSelfCheck(self) -> None:
        if self._working:
            return
        self._working = True
        self._status_text = 'Ejecutando autodiagnostico profundo sobre stack local, embeddings, SQL y replay.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                snapshot = self.self_check_orchestrator.run_deep_suite()
                self.taskResolved.emit('deep_suite', snapshot.model_dump(mode='json'))
            except Exception as exc:
                self.taskFailed.emit('deep_suite', str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def copyIncidentPacket(self) -> None:
        packet = self._build_current_packet()
        self._latest_packet = packet
        self._copy_text(packet, 'Paquete del incidente copiado al portapapeles.')

    @Slot()
    def copyLatestFailurePacket(self) -> None:
        packet = self.incident_packet_service.build_codex_packet_for_issue(IncidentQuery(status=RunStatus.FAILED, recent_hours=72, limit=1))
        self._latest_packet = packet
        self._copy_text(packet, 'Paquete del ultimo fallo copiado al portapapeles.')

    @Slot(str)
    def sandboxToolCard(self, tool_id: str) -> None:
        if self.tool_record_repository is None or self.tool_teach_service is None:
            self._latest_tool_status = 'La capa Tool Teaching no esta disponible en esta sesion.'
            self.dataChanged.emit()
            return
        card = self.tool_record_repository.get_card(tool_id)
        if card is None:
            self._latest_tool_status = 'No encontre la ToolCard seleccionada.'
            self.dataChanged.emit()
            return
        self._latest_tool_status = self._run_tool_sandbox(card)
        self.refresh()

    @Slot()
    def auditBaseTools(self) -> None:
        if self.tool_record_repository is None or self.tool_teach_service is None:
            self._latest_tool_status = 'La capa Tool Teaching no esta disponible en esta sesion.'
            self.dataChanged.emit()
            return
        ordered = ['ollama_llm', 'playwright_browser', 'desktop_human_runner', 'codex_installed', 'chatgpt_installed', 'chatgpt_web_assisted']
        sections: list[str] = []
        audited = 0
        for tool_id in ordered:
            card = self.tool_record_repository.get_card(tool_id)
            if card is None:
                continue
            audited += 1
            sections.append(self._run_tool_sandbox(card))
        if audited == 0:
            self._latest_tool_status = 'No encontre herramientas base para auditar en esta sesion.'
            self.dataChanged.emit()
            return
        header = f'Auditoria base completada. Herramientas auditadas: {audited}.'
        self._latest_tool_status = header + '\n\n' + '\n\n'.join(sections)
        self._status_text = 'Auditoria base de herramientas completada.'
        self.refresh()

    @Slot()
    def copyLatestToolStatus(self) -> None:
        text = self._latest_tool_status or 'Todavia no he probado ninguna herramienta desde esta vista.'
        self._copy_text(text, 'Estado de herramienta copiado al portapapeles.')

    @Slot()
    def copyPortableContext(self) -> None:
        text = self._portable_context_brief or str(self._portable_context.get('summary') or '').strip()
        if not text:
            text = 'Todavia no hay un contexto portable disponible en esta sesion.'
        self._copy_text(text, 'Contexto portable copiado al portapapeles.')

    @Slot()
    def copySelfExamination(self) -> None:
        text = self._self_examination_brief or str(self._self_examination.get('summary') or '').strip()
        if not text:
            text = 'Todavia no hay una autoexaminacion operativa disponible en esta sesion.'
        self._copy_text(text, 'Autoexaminacion operativa copiada al portapapeles.')

    def _build_current_packet(self) -> str:
        if self._selected_incident:
            return self.incident_packet_service.build_codex_packet_for_issue(IncidentQuery(incident_id=self._selected_incident.get('incident_id'), limit=5))
        if self._selected_dossier:
            run_id = self._selected_dossier.get('run_id') or None
            episode_id = self._selected_dossier.get('episode_id') or None
            if run_id:
                return self.incident_packet_service.build_codex_packet_for_issue(IncidentQuery(run_id=run_id, limit=5))
            if episode_id:
                return self.incident_packet_service.build_codex_packet_for_issue(IncidentQuery(episode_id=episode_id, limit=5))
            issue_hint = self._selected_dossier.get('issue_hint_text') or ''
            return self.incident_packet_service.build_codex_packet_for_issue(IncidentQuery(issue_hint=issue_hint, limit=5))
        return 'Todavia no hay incidentes ni dossiers seleccionados.'

    def _build_evidence_preview(self) -> str:
        if self._selected_incident:
            return (
                f"Incidente: {self._selected_incident.get('incident_kind', 'n/d')}\n"
                f"Resumen: {self._selected_incident.get('summary', '')}\n"
                f"URL afectada: {self._selected_incident.get('affected_url', '') or 'n/d'}\n"
                f"Severidad: {self._selected_incident.get('severity', 'n/d')}\n"
                f"Estado: {self._selected_incident.get('status', 'n/d')}"
            )
        if self._selected_dossier:
            return (
                f"Dossier: {self._selected_dossier.get('title', 'n/d')}\n"
                f"Estado: {self._selected_dossier.get('status', 'n/d')}\n"
                f"Resumen: {self._selected_dossier.get('summary', '')}"
            )
        return 'Selecciona un incidente o dossier para ver evidencia relacionada.'

    def _build_ia_comparisons(self) -> list[dict[str, Any]]:
        if self.experiment_lab_repository is None:
            return []
        items: list[dict[str, Any]] = []
        for recommendation in self.experiment_lab_repository.list_recommendations(limit=8):
            metadata = dict(recommendation.metadata or {})
            items.append(
                {
                    'recommendation_id': recommendation.recommendation_id,
                    'domain': recommendation.domain.value,
                    'subject_key': recommendation.subject_key,
                    'recommended_route': recommendation.recommended_route.value,
                    'recommended_assistant_kind': recommendation.recommended_assistant_kind,
                    'recommended_config_signature': recommendation.recommended_config_signature,
                    'score': recommendation.score,
                    'confidence': recommendation.confidence,
                    'winning_trace_ids': list(metadata.get('winning_trace_ids') or []),
                    'losing_trace_ids': list(metadata.get('losing_trace_ids') or []),
                    'comparison_scope_keys': list(metadata.get('comparison_scope_keys') or []),
                    'supporting_run_ids': list(recommendation.supporting_run_ids or []),
                    'adaptive_learning_summary': dict(metadata.get('adaptive_learning_summary') or {}),
                }
            )
        return items

    def _filter_incidents(self, incidents: list[dict[str, Any]], filter_key: str) -> list[dict[str, Any]]:
        if filter_key in {'', 'all'}:
            return incidents
        mapping = {
            'captura': {'capture_starvation', 'bridge_lag'},
            'navegacion': {'navigation_stall', 'tab_attach_gap', 'session_restore_weak'},
            'finalizacion': {'finalize_slow'},
            'replay': {'replay_incomplete'},
        }
        allowed = mapping.get(filter_key, set())
        return [item for item in incidents if item.get('incident_kind') in allowed]

    def _run_tool_sandbox(self, card: Any) -> str:
        request = InferenceRequest(
            user_goal=f'Validar en sandbox la herramienta {card.title}',
            task_role=TaskRole.TOOL_SANDBOX,
            goal_parameters={'tool_id': card.tool_id, 'execution_scope': 'read_only'},
        )
        task = self.tool_teach_service.build_task_from_request(request)
        result = self.tool_teach_service.execute_task(task, approved=False)
        return self._format_tool_status(card.model_dump(mode='json'), result.model_dump(mode='json'))

    def _copy_text(self, text: str, success_message: str) -> None:
        clipboard = None
        try:
            clipboard = QGuiApplication.clipboard()
        except Exception:
            app = QGuiApplication.instance()
            if app is not None and hasattr(app, 'clipboard'):
                try:
                    clipboard = app.clipboard()
                except Exception:
                    clipboard = None
        if clipboard is None:
            self._clipboard_notice = 'No pude acceder al portapapeles en esta sesion.'
        else:
            clipboard.setText(text)
            self._clipboard_notice = success_message
        self.dataChanged.emit()

    def _format_tool_status(self, card: dict[str, Any], result: dict[str, Any]) -> str:
        execution = dict(result.get('execution_state') or {})
        metadata = dict(execution.get('metadata') or {})
        lines = [
            f'Herramienta: {card.get("title", "n/d")} ({card.get("tool_id", "n/d")})',
            f'Estado: {execution.get("state", "n/d")}',
        ]
        detail = str(execution.get('detail') or '').strip()
        if detail:
            lines.append(f'Detalle: {detail}')
        output_text = str(result.get('output_text') or '').strip()
        if output_text:
            lines.append(f'Salida: {output_text}')
        error_message = str(result.get('error_message') or '').strip()
        if error_message:
            lines.append(f'Error: {error_message}')
        approval_decision = str(execution.get('approval_decision') or '').strip()
        if approval_decision:
            lines.append(f'Aprobacion: {approval_decision}')
        assistant_kind = str(metadata.get('assistant_kind') or '').strip()
        if assistant_kind:
            lines.append(f'Asistente: {assistant_kind}')
        launch_mode = str(metadata.get('launch_mode') or '').strip()
        if launch_mode:
            lines.append(f'Via: {launch_mode}')
        launch_target = str(metadata.get('launch_target') or '').strip()
        if launch_target:
            lines.append(f'Destino: {launch_target}')
        response_capture_mode = str(metadata.get('response_capture_mode') or '').strip().lower()
        if response_capture_mode == 'clipboard_capture':
            lines.append('Respuesta: captura automatica por clipboard con fallback manual si no aparece texto util')
        elif metadata.get('manual_pasteback_required'):
            lines.append('Respuesta: pegado manual confirmado por el usuario')
        live_audit = dict(result.get('metadata', {}).get('live_audit') or {})
        if live_audit:
            decision = dict(live_audit.get('decision') or {})
            findings = [str(item.get('kind') or item.get('title') or '') for item in (live_audit.get('findings') or []) if isinstance(item, dict)]
            lines.append(f'Auditoria viva: {decision.get("action", "continue_local")}')
            if findings:
                lines.append(f'Hallazgos: {", ".join(findings[:3])}')
            lines.append(f'Confianza auditoria: {float(live_audit.get("confidence") or 0.0):.2f}')
        return '\n'.join(lines)

    @Slot(str, object)
    def _apply_result(self, task_name: str, payload: Any) -> None:
        if task_name == 'deep_suite':
            self._health_snapshot = dict(payload)
            self._improvement_backlog = list((payload or {}).get('backlog', []))
            self._status_text = (payload or {}).get('summary', 'Autodiagnostico profundo completado.')
            self._working = False
            self.refresh()
            return
        self._working = False
        self.dataChanged.emit()

    @Slot(str, str)
    def _apply_failure(self, task_name: str, message: str) -> None:
        self._working = False
        self._status_text = f'No pude completar {task_name}: {message}'
        self.dataChanged.emit()

    working = Property(bool, get_working, notify=dataChanged)
    statusText = Property(str, get_status_text, notify=dataChanged)
    healthSnapshot = Property(dict, get_health_snapshot, notify=dataChanged)
    recentDossiers = Property(list, get_recent_dossiers, notify=dataChanged)
    recentIncidents = Property(list, get_recent_incidents, notify=dataChanged)
    incidentFilter = Property(str, get_incident_filter, notify=dataChanged)
    improvementBacklog = Property(list, get_improvement_backlog, notify=dataChanged)
    recentPendingIssues = Property(list, get_recent_pending_issues, notify=dataChanged)
    knownToolCards = Property(list, get_known_tool_cards, notify=dataChanged)
    iaComparisons = Property(list, get_ia_comparisons, notify=dataChanged)
    environmentSelfModel = Property(dict, get_environment_self_model, notify=dataChanged)
    worldModel = Property(dict, get_world_model, notify=dataChanged)
    autonomousValidation = Property(dict, get_autonomous_validation, notify=dataChanged)
    portableContext = Property(dict, get_portable_context, notify=dataChanged)
    portableContextBrief = Property(str, get_portable_context_brief, notify=dataChanged)
    toolEvolutionPanel = Property(dict, get_tool_evolution_panel, notify=dataChanged)
    selfExamination = Property(dict, get_self_examination, notify=dataChanged)
    selfExaminationBrief = Property(str, get_self_examination_brief, notify=dataChanged)
    latestToolStatus = Property(str, get_latest_tool_status, notify=dataChanged)
    selectedDossier = Property(dict, get_selected_dossier, notify=dataChanged)
    selectedIncident = Property(dict, get_selected_incident, notify=dataChanged)
    evidencePreview = Property(str, get_evidence_preview, notify=dataChanged)
    latestPacket = Property(str, get_latest_packet, notify=dataChanged)
    clipboardNotice = Property(str, get_clipboard_notice, notify=dataChanged)

