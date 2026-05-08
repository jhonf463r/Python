from __future__ import annotations

import atexit
import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping

logger = logging.getLogger(__name__)

from iabv_v15.domain.models import InferenceRequest, IncidentQuery, RunStatus, TaskRole
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.hidden_incident_repository import HiddenIncidentRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.scenario_run_repository import ScenarioRunRepository
from iabv_v15.services.evolution.evolution_review_service import EvolutionReviewService
from iabv_v15.services.evolution.incident_packet_service import IncidentPacketService
from iabv_v15.services.evolution.self_check_orchestrator import SelfCheckOrchestrator
from iabv_v15.ui.qt import QObject, Property, QGuiApplication, QTimer, Signal, Slot


class EvolutionCenterViewModel(QObject):
    dataChanged = Signal()
    taskResolved = Signal(str, object)
    taskFailed = Signal(str, str)
    refreshReady = Signal(int, object)  # (generation, snapshot_dict)

    # Granular property-change signals to avoid mass QML re-evaluation.
    overviewChanged = Signal()       # statusText, healthSnapshot, working
    incidentsChanged = Signal()      # recentIncidents, incidentFilter, selectedIncident
    dossiersChanged = Signal()       # recentDossiers, selectedDossier, evidencePreview, latestPacket
    backlogChanged = Signal()        # improvementBacklog, recentPendingIssues
    toolsChanged = Signal()          # knownToolCards, latestToolStatus, toolEvolutionPanel
    worldModelChanged = Signal()     # worldModel, environmentSelfModel, evidenceBasis
    metacognitionChanged = Signal()  # portableContext/Brief, selfExamination/Brief, autonomousValidation, controlMaster
    screenshotsChanged = Signal()    # recentUiScreenshots
    proactiveChanged = Signal()      # proactiveDashboard, proactiveDashboardBrief
    publishPrChanged = Signal()      # publishPrStatus, publishPrResult
    iaComparisonsChanged = Signal()  # iaComparisons
    clipboardChanged = Signal()      # clipboardNotice
    refreshStatusChanged = Signal()   # refreshStatus, lastRefreshSummary, lastRefreshResult

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
        control_master_service: Any | None = None,
        control_master_digest_builder: Any | None = None,
        github_remote_service: Any | None = None,
        defer_initial_refresh: bool = False,
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
        self.control_master_service = control_master_service
        self.control_master_digest_builder = control_master_digest_builder
        # F2.2: el VM no decide rutas ni abre PRs por su cuenta; solo dispara
        # el servicio ya existente (``GitHubRemoteService``) y expone el
        # resultado como Property para que la UI lo muestre. Queda ``None``
        # cuando el servicio no fue wireado (ej. tests headless).
        self.github_remote_service = github_remote_service
        self._control_master_digest: dict[str, Any] = {}
        self._control_master_brief = 'Todavia no he consultado el control maestro desde esta vista.'
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
        self._evidence_basis: dict[str, Any] = {}
        self._tool_evolution_panel: dict[str, Any] = {}
        self._self_examination: dict[str, Any] = {}
        self._self_examination_brief = 'Todavia no he generado una autoexaminacion operativa desde esta vista.'
        self._proactive_dashboard: dict[str, Any] = {}
        self._proactive_dashboard_brief = 'Todavia no he consultado que necesita IABV del humano ahora.'
        # Hook opcional: bootstrap setea este atributo despues del ctor.
        # El VM no lo invoca si sigue siendo None.
        self.proactive_dashboard_service: Any | None = None
        self.human_approval_broker: Any | None = None
        self.approval_memory: Any | None = None
        # F1.1: captura de snapshots UI persistida. Setea bootstrap; el VM
        # solo lee la foto (list_recent) y no persiste nada por su cuenta.
        self.ui_screenshot_service: Any | None = None
        self._recent_ui_screenshots: list[dict[str, Any]] = []
        self._latest_tool_status = 'Todavia no he probado ninguna herramienta desde esta vista.'
        self._publish_pr_status = 'Todavia no he publicado ningun PR desde esta vista.'
        self._publish_pr_result: dict[str, Any] = {}
        self._selected_dossier: dict[str, Any] = {}
        self._selected_incident: dict[str, Any] = {}
        self._pinned_dossier_selection = False
        self._pinned_incident_selection = False
        self._evidence_preview = 'Selecciona un incidente o dossier para ver evidencia relacionada.'
        self._latest_packet = 'Todavia no hay un paquete de incidente seleccionado.'
        self._clipboard_notice = 'Nada copiado aun.'
        self._refresh_status = 'idle'
        self._last_refresh_summary = ''
        self._last_refresh_result = 'none'
        self._section_fingerprints: dict[str, str] = {}
        self._bg_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ecvm-bg')
        atexit.register(self._shutdown_bg_pool)
        self._refresh_generation: int = 0
        self._refresh_in_flight: bool = False
        self.refreshReady.connect(self._apply_refresh_snapshot)
        self.taskResolved.connect(self._apply_result)
        self.taskFailed.connect(self._apply_failure)
        if defer_initial_refresh:
            QTimer.singleShot(0, self.refreshAsync)
        else:
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

    def get_evidence_basis(self) -> dict[str, Any]:
        return self._evidence_basis

    def get_control_master_digest(self) -> dict[str, Any]:
        return self._control_master_digest

    def get_control_master_brief(self) -> str:
        return self._control_master_brief

    def get_tool_evolution_panel(self) -> dict[str, Any]:
        return self._tool_evolution_panel

    def get_self_examination(self) -> dict[str, Any]:
        return self._self_examination

    def get_self_examination_brief(self) -> str:
        return self._self_examination_brief

    def get_proactive_dashboard(self) -> dict[str, Any]:
        return self._proactive_dashboard

    def get_proactive_dashboard_brief(self) -> str:
        return self._proactive_dashboard_brief

    def get_recent_ui_screenshots(self) -> list[dict[str, Any]]:
        return self._recent_ui_screenshots

    def get_latest_tool_status(self) -> str:
        return self._latest_tool_status

    def get_publish_pr_status(self) -> str:
        return self._publish_pr_status

    def get_publish_pr_result(self) -> dict[str, Any]:
        return self._publish_pr_result

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

    def get_refresh_status(self) -> str:
        return self._refresh_status

    def get_last_refresh_summary(self) -> str:
        return self._last_refresh_summary

    def get_last_refresh_result(self) -> str:
        return self._last_refresh_result

    def _shutdown_bg_pool(self) -> None:
        try:
            self._bg_pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    _ITEM_FIELDS = (
        'dossier_id', 'incident_id', 'issue_id', 'tool_id', 'entry_id',
        'status', 'outcome', 'severity', 'title', 'summary',
        'updated_at', 'created_at', 'timestamp',
    )
    _DICT_FIELDS = (
        'summary', 'status', 'assistant_brief', 'updated_at_utc',
        'last_updated', 'generated_at', 'generated_at_epoch',
        'pending_attention_count', 'learned_policies_count', 'truthState',
    )

    @staticmethod
    def _compact_value(value: Any, depth: int = 0, max_depth: int = 2) -> Any:
        """Recursively compact a value for deterministic fingerprinting.

        - scalars (str/int/float/bool/None): kept, strings truncated to 64 chars
        - lists: {"__len": n, "items": first 8 items compacted}
        - dicts: sorted top-level keys, values compacted recursively up to *max_depth*
        """
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:64]
        if isinstance(value, list):
            if depth >= max_depth:
                return {'__len': len(value)}
            items = [EvolutionCenterViewModel._compact_value(v, depth + 1, max_depth) for v in value[:8]]
            return {'__len': len(value), 'items': items}
        if isinstance(value, dict):
            if depth >= max_depth:
                return {'__keys': sorted(value.keys())[:16]}
            compact: dict[str, Any] = {}
            for k in sorted(value.keys())[:24]:
                compact[k] = EvolutionCenterViewModel._compact_value(value[k], depth + 1, max_depth)
            return compact
        return str(value)[:64]

    @staticmethod
    def _section_fingerprint(value: Any) -> str:
        """Robust lightweight fingerprint for change detection.

        For lists: per-item compact dict of id/status/title/updated_at fields
        (first 20 items).
        For dicts: generic recursive compaction of all top-level keys with
        depth limit 2, sorted deterministically.
        Result: md5 of json.dumps(sort_keys=True) truncated to 16 hex chars.
        """
        if isinstance(value, list):
            items = []
            for item in value[:20]:
                if isinstance(item, dict):
                    compact = {k: str(item[k])[:48] for k in EvolutionCenterViewModel._ITEM_FIELDS if k in item and item[k] is not None}
                    items.append(compact)
            raw = json.dumps({'n': len(value), 'items': items}, sort_keys=True, default=str)
        elif isinstance(value, dict):
            compact_dict = EvolutionCenterViewModel._compact_value(value, depth=0, max_depth=2)
            raw = json.dumps(compact_dict, sort_keys=True, default=str)
        elif isinstance(value, str):
            raw = value[:128]
        else:
            raw = str(value)[:128]
        return hashlib.md5(raw.encode('utf-8', errors='replace')).hexdigest()[:16]

    def _trace_refresh(self, kind: str, **data: Any) -> None:
        """Emit a lightweight trace event to RuntimeAuditTracer if available."""
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            get_runtime_tracer().trace(kind, **data)
        except Exception:
            pass

    def _collect_refresh_data(self) -> dict[str, Any]:
        """Collect all data for refresh. Safe to call from a background thread."""
        snapshot = None
        try:
            snapshot = self.evolution_review_service.build_project_health()
        except Exception as exc:
            logger.warning('evolution_center: build_project_health failed: %s', exc)
        try:
            dossiers = [item.model_dump(mode='json') for item in self.dossier_repository.list_recent(limit=24)]
        except Exception as exc:
            logger.warning('evolution_center: dossier list_recent failed: %s', exc)
            dossiers = []
        try:
            incidents = [item.model_dump(mode='json') for item in self.hidden_incident_repository.list_recent(limit=30)]
        except Exception as exc:
            logger.warning('evolution_center: incident list_recent failed: %s', exc)
            incidents = []
        filtered_incidents = self._filter_incidents(incidents, self._incident_filter)
        try:
            backlog = [item.model_dump(mode='json') for item in self.evolution_review_service.build_improvement_backlog(limit=8)]
        except Exception as exc:
            logger.warning('evolution_center: build_improvement_backlog failed: %s', exc)
            backlog = []
        try:
            pending = [item.model_dump(mode='json') for item in self.pending_issue_repository.list_recent(limit=10)] if self.pending_issue_repository is not None else []
        except Exception as exc:
            logger.warning('evolution_center: pending list_recent failed: %s', exc)
            pending = []
        try:
            tool_cards = [item.model_dump(mode='json') for item in self.tool_record_repository.list_cards()] if self.tool_record_repository is not None else []
        except Exception as exc:
            logger.warning('evolution_center: tool list_cards failed: %s', exc)
            tool_cards = []
        ia_comparisons = self._build_ia_comparisons()
        try:
            environment_self_model = (
                self.environment_self_awareness_service.current_model().model_dump(mode='json')
                if self.environment_self_awareness_service is not None
                else {}
            )
        except Exception as exc:
            logger.warning('evolution_center: environment_self_model failed: %s', exc)
            environment_self_model = {}
        try:
            world_model = (
                self.world_model_service.current_model().model_dump(mode='json')
                if self.world_model_service is not None
                else {}
            )
        except Exception as exc:
            logger.warning('evolution_center: world_model failed: %s', exc)
            world_model = {}
        try:
            autonomous_validation = (
                self.autonomous_validation_cycle.current_snapshot().model_dump(mode='json')
                if self.autonomous_validation_cycle is not None
                else {}
            )
        except Exception as exc:
            logger.warning('evolution_center: autonomous_validation failed: %s', exc)
            autonomous_validation = {}
        try:
            portable_context = (
                self.portable_context_service.current_package(refresh=False).model_dump(mode='json')
                if self.portable_context_service is not None and hasattr(self.portable_context_service, 'current_package')
                else {}
            )
        except Exception as exc:
            logger.warning('evolution_center: portable_context failed: %s', exc)
            portable_context = {}
        try:
            self_examination = (
                self.self_examination_service.current_review(refresh=False).model_dump(mode='json')
                if self.self_examination_service is not None and hasattr(self.self_examination_service, 'current_review')
                else {}
            )
        except Exception as exc:
            logger.warning('evolution_center: self_examination failed: %s', exc)
            self_examination = {}
        control_master_digest: dict[str, Any] = {}
        if self.control_master_service is not None and self.control_master_digest_builder is not None:
            try:
                state = self.control_master_service.current_state(refresh=False)
                try:
                    work_queue = self.control_master_service.current_work_queue(limit=10)
                except Exception:
                    work_queue = []
                control_master_digest = self.control_master_digest_builder.build(state, work_queue=work_queue).model_dump(mode='json')
            except Exception:
                control_master_digest = {}
        return {
            'snapshot': snapshot.model_dump(mode='json') if snapshot is not None else None,
            'dossiers': dossiers,
            'filtered_incidents': filtered_incidents,
            'backlog': backlog,
            'pending': pending,
            'tool_cards': tool_cards,
            'ia_comparisons': ia_comparisons,
            'environment_self_model': environment_self_model,
            'world_model': world_model,
            'autonomous_validation': autonomous_validation,
            'portable_context': portable_context,
            'self_examination': self_examination,
            'control_master_digest': control_master_digest,
        }

    def _apply_collected_data(self, data: dict[str, Any]) -> None:
        """Apply collected refresh data to UI properties. Must run on UI thread."""
        snapshot_dict = data.get('snapshot')
        dossiers = data.get('dossiers', [])
        filtered_incidents = data.get('filtered_incidents', [])
        backlog = data.get('backlog', [])
        pending = data.get('pending', [])
        tool_cards = data.get('tool_cards', [])
        ia_comparisons = data.get('ia_comparisons', [])
        environment_self_model = data.get('environment_self_model', {})
        world_model = data.get('world_model', {})
        autonomous_validation = data.get('autonomous_validation', {})
        portable_context = data.get('portable_context', {})
        self_examination = data.get('self_examination', {})
        control_master_digest = data.get('control_master_digest', {})
        self._health_snapshot = snapshot_dict if snapshot_dict is not None else self._health_snapshot
        self._recent_dossiers = dossiers
        self._recent_incidents = filtered_incidents
        self._improvement_backlog = backlog
        self._recent_pending_issues = pending
        self._known_tool_cards = tool_cards
        self._ia_comparisons = ia_comparisons
        environment_self_model['truthState'] = self._classify_panel_truth(
            has_live_source=self.environment_self_awareness_service is not None,
            payload=environment_self_model,
        )
        self._environment_self_model = environment_self_model
        world_model['truthState'] = self._classify_panel_truth(
            has_live_source=self.world_model_service is not None,
            payload=world_model,
        )
        self._world_model = world_model
        autonomous_validation['truthState'] = self._classify_panel_truth(
            has_live_source=self.autonomous_validation_cycle is not None,
            payload=autonomous_validation,
        )
        self._autonomous_validation = autonomous_validation
        portable_context['truthState'] = self._classify_panel_truth(
            has_live_source=False,
            payload=portable_context,
        )
        self._portable_context = portable_context
        self._portable_context_brief = str(portable_context.get('assistant_brief') or '').strip() or self._portable_context_brief
        eb_raw = dict((portable_context.get('metadata') or {}).get('evidence_basis') or {})
        eb_state = str(eb_raw.get('state') or 'unresolved')
        eb_raw['truthState'] = eb_state
        self._evidence_basis = eb_raw
        self._tool_evolution_panel = self._build_tool_evolution_panel(portable_context=portable_context, autonomous_validation=autonomous_validation)
        self_examination['truthState'] = self._classify_panel_truth(
            has_live_source=False,
            payload=self_examination,
        )
        self._self_examination = self_examination
        self._self_examination_brief = str(self_examination.get('assistant_brief') or '').strip() or self._self_examination_brief
        proactive_dashboard = self._build_proactive_dashboard()
        self._proactive_dashboard = proactive_dashboard
        dashboard_brief = self._format_proactive_dashboard_brief(proactive_dashboard)
        if dashboard_brief:
            self._proactive_dashboard_brief = dashboard_brief
        self._recent_ui_screenshots = self._build_recent_ui_screenshots()
        control_master_digest['truthState'] = self._classify_panel_truth(
            has_live_source=self.control_master_service is not None,
            payload=control_master_digest,
        )
        self._control_master_digest = control_master_digest
        control_master_brief = self._format_control_master_brief(control_master_digest)
        if control_master_brief:
            self._control_master_brief = control_master_brief
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
        status_summary = str(data.get('_status_summary') or '')
        self._status_text = status_summary if status_summary else self._status_text
        validation_summary = str((autonomous_validation or {}).get('summary') or '').strip()
        if validation_summary:
            self._status_text = f'{self._status_text} | Validacion autonoma: {validation_summary}'
        changed_sections = data.get('_changed_sections')
        emitted = self._emit_granular_signals(changed_sections)
        data['_emitted_signals'] = emitted

    _SECTION_SIGNAL_MAP: dict[str, str] = {
        'dossiers': 'dossiersChanged',
        'filtered_incidents': 'incidentsChanged',
        'backlog': 'backlogChanged',
        'pending': 'backlogChanged',
        'tool_cards': 'toolsChanged',
        'ia_comparisons': 'iaComparisonsChanged',
        'environment_self_model': 'worldModelChanged',
        'world_model': 'worldModelChanged',
        'portable_context': 'metacognitionChanged',
        'self_examination': 'metacognitionChanged',
        'control_master_digest': 'metacognitionChanged',
    }

    def _emit_granular_signals(self, changed_sections: list[str] | None = None) -> list[str]:
        """Emit per-section signals so QML only re-evaluates affected bindings.

        When *changed_sections* is given, only signals mapped to those sections
        are emitted.  When ``None`` (legacy/sync path), all signals fire.
        Returns the list of signal names actually emitted.
        """
        if changed_sections is None:
            all_signals = [
                'overviewChanged', 'incidentsChanged', 'dossiersChanged',
                'backlogChanged', 'toolsChanged', 'worldModelChanged',
                'metacognitionChanged', 'screenshotsChanged', 'proactiveChanged',
                'iaComparisonsChanged',
            ]
            for name in all_signals:
                getattr(self, name).emit()
            return list(all_signals)

        signal_names: set[str] = set()
        for section in changed_sections:
            sig = self._SECTION_SIGNAL_MAP.get(section)
            if sig:
                signal_names.add(sig)
        signal_names.add('overviewChanged')
        emitted: list[str] = sorted(signal_names)
        for name in emitted:
            getattr(self, name).emit()
        return emitted

    @Slot()
    def refresh(self) -> None:
        """Synchronous refresh — runs all queries on calling thread.

        Used by tests and programmatic callers that need immediate results.
        For UI/QML callers use :meth:`refreshAsync` instead.
        """
        data = self._collect_refresh_data()
        snapshot_dict = data.get('snapshot')
        if snapshot_dict is not None:
            data['_status_summary'] = snapshot_dict.get('summary', '')
        self._apply_collected_data(data)
        # Backward compat: no QML Property uses notify=dataChanged anymore,
        # so this does NOT cause mass binding re-evaluation. Kept for
        # Python-side consumers / tests that connect to dataChanged.
        self.dataChanged.emit()

    @Slot()
    def refreshFromUser(self) -> None:
        """Slot for QML Actualizar button — traces as user_click."""
        self._do_refresh_async('user_click')

    @Slot()
    def refreshAsync(self) -> None:
        """Non-blocking refresh — heavy I/O on ``_bg_pool``, results via signal."""
        self._do_refresh_async('programmatic')

    def _do_refresh_async(self, source: str = 'programmatic') -> None:
        refresh_id = f'r{int(time.time() * 1000) % 1_000_000:06d}'
        self._trace_refresh('evolution_refresh_requested', refresh_id=refresh_id, source=source, generation=self._refresh_generation)

        if self._refresh_in_flight:
            self._trace_refresh('evolution_refresh_skipped', refresh_id=refresh_id, reason='in_flight')
            return
        self._refresh_in_flight = True
        self._refresh_generation += 1
        gen = self._refresh_generation

        self._refresh_status = 'refreshing'
        self._last_refresh_summary = 'Actualizando Centro Evolutivo...'
        self._last_refresh_result = 'started'
        self.refreshStatusChanged.emit()
        self.overviewChanged.emit()

        t0 = time.perf_counter()
        self._trace_refresh('evolution_refresh_started', refresh_id=refresh_id, source=source, generation=gen, status_emitted_signals=['refreshStatusChanged', 'overviewChanged'])

        def _bg() -> dict[str, Any] | None:
            if self._refresh_generation != gen:
                return None
            data = self._collect_refresh_data()
            data['_refresh_meta'] = {
                'refresh_id': refresh_id,
                'source': source,
                'generation': gen,
                't0': t0,
            }
            section_keys = [
                'dossiers', 'filtered_incidents', 'backlog', 'pending',
                'tool_cards', 'ia_comparisons', 'environment_self_model',
                'world_model', 'portable_context', 'self_examination',
                'control_master_digest',
            ]
            counts = {k: len(data.get(k, [])) if isinstance(data.get(k), list) else (1 if data.get(k) else 0) for k in section_keys}
            self._trace_refresh('evolution_refresh_collected', refresh_id=refresh_id, section_counts=counts)
            return data

        def _done(fut: Any) -> None:
            if self._refresh_generation != gen:
                self._refresh_in_flight = False
                self._trace_refresh('evolution_refresh_stale', refresh_id=refresh_id, reason='generation_superseded')
                if self._refresh_status == 'refreshing':
                    self._refresh_status = 'idle'
                    self._last_refresh_summary = 'Refresh cancelado: se solicit\u00f3 uno nuevo.'
                    self._last_refresh_result = 'cancelled'
                    self.refreshStatusChanged.emit()
                return
            try:
                result = fut.result()
            except Exception as exc:
                self._refresh_in_flight = False
                self._trace_refresh('evolution_refresh_failed', refresh_id=refresh_id, error=str(exc))
                self._refresh_status = 'failed'
                self._last_refresh_result = 'failed'
                self._last_refresh_summary = f'No pude actualizar: {str(exc)[:80]}'
                self.refreshStatusChanged.emit()
                self.overviewChanged.emit()
                logger.debug('evolution_center bg refresh failed', exc_info=True)
                return
            if result is None:
                self._refresh_in_flight = False
                self._trace_refresh('evolution_refresh_stale', refresh_id=refresh_id, reason='result_none')
                if self._refresh_status == 'refreshing':
                    self._refresh_status = 'idle'
                    self._last_refresh_summary = 'Refresh cancelado: generaci\u00f3n obsoleta.'
                    self._last_refresh_result = 'cancelled'
                    self.refreshStatusChanged.emit()
                return
            self.refreshReady.emit(gen, result)

        future = self._bg_pool.submit(_bg)
        future.add_done_callback(_done)

    @Slot(int, object)
    def _apply_refresh_snapshot(self, gen: int, data: object) -> None:
        """Apply background-collected data on the UI thread."""
        if self._refresh_generation != gen or not isinstance(data, dict):
            self._refresh_in_flight = False
            if self._refresh_status == 'refreshing':
                self._refresh_status = 'idle'
                self._last_refresh_result = 'cancelled'
                self._last_refresh_summary = 'Refresh descartado: generaci\u00f3n obsoleta.'
                self.refreshStatusChanged.emit()
            return
        meta = data.pop('_refresh_meta', {})
        refresh_id = meta.get('refresh_id', '?')
        source = meta.get('source', '?')
        t0 = meta.get('t0', time.perf_counter())

        snapshot_dict = data.get('snapshot')
        if snapshot_dict is not None:
            data['_status_summary'] = snapshot_dict.get('summary', '')

        section_map = {
            'dossiers': data.get('dossiers', []),
            'filtered_incidents': data.get('filtered_incidents', []),
            'backlog': data.get('backlog', []),
            'pending': data.get('pending', []),
            'tool_cards': data.get('tool_cards', []),
            'ia_comparisons': data.get('ia_comparisons', []),
            'environment_self_model': data.get('environment_self_model', {}),
            'world_model': data.get('world_model', {}),
            'portable_context': data.get('portable_context', {}),
            'self_examination': data.get('self_examination', {}),
            'control_master_digest': data.get('control_master_digest', {}),
        }
        new_fps = {k: self._section_fingerprint(v) for k, v in section_map.items()}
        old_fps = self._section_fingerprints
        changed = [k for k in new_fps if new_fps[k] != old_fps.get(k, '')]
        unchanged = [k for k in new_fps if new_fps[k] == old_fps.get(k, '')]
        self._section_fingerprints = new_fps

        try:
            data['_changed_sections'] = changed
            self._apply_collected_data(data)
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            result = 'changed' if changed else 'unchanged'
            self._refresh_in_flight = False
            self._refresh_status = 'idle'
            self._last_refresh_result = result
            if changed:
                self._last_refresh_summary = f'Actualizado: cambiaron {len(changed)} secciones ({", ".join(changed[:4])}).'
            else:
                self._last_refresh_summary = 'Actualizado: no hubo cambios nuevos en las fuentes vivas.'
            self.refreshStatusChanged.emit()
            all_emitted = list(data.get('_emitted_signals', []))
            if 'refreshStatusChanged' not in all_emitted:
                all_emitted.append('refreshStatusChanged')
            self._trace_refresh(
                'evolution_refresh_applied',
                refresh_id=refresh_id, source=source, generation=gen,
                duration_ms=duration_ms, result=result,
                changed_sections=changed, unchanged_sections=unchanged,
                emitted_signals=sorted(all_emitted),
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            self._refresh_in_flight = False
            self._trace_refresh('evolution_refresh_failed', refresh_id=refresh_id, error=str(exc), duration_ms=duration_ms)
            self._refresh_status = 'failed'
            self._last_refresh_result = 'failed'
            self._last_refresh_summary = f'No pude actualizar: {str(exc)[:80]}'
            self.refreshStatusChanged.emit()
            logger.debug('evolution_center UI apply failed', exc_info=True)

    def _build_proactive_dashboard(self) -> dict[str, Any]:
        """Consulta `ProactiveDashboardService` si esta wired; caso contrario
        devuelve `{}`. Serializa entries a dicts para consumo desde QML.

        Respeta AGENTS.md: el VM no decide rutas, solo expone la foto que
        produce el servicio. Si el servicio no esta wired no inventa datos.
        """
        service = getattr(self, 'proactive_dashboard_service', None)
        if service is None:
            return {}
        try:
            snapshot = service.snapshot()
        except Exception:
            return {}
        entries: list[dict[str, Any]] = []
        for entry in getattr(snapshot, 'entries', ()) or ():
            entries.append(
                {
                    'entry_id': getattr(entry, 'entry_id', ''),
                    'kind': getattr(entry, 'kind', ''),
                    'title': getattr(entry, 'title', ''),
                    'detail': getattr(entry, 'detail', ''),
                    'severity': getattr(entry, 'severity', 'info'),
                    'scope': dict(getattr(entry, 'scope', {}) or {}),
                    'actionable': bool(getattr(entry, 'actionable', False)),
                    'created_at_epoch': float(getattr(entry, 'created_at_epoch', 0.0) or 0.0),
                }
            )
        return {
            'generated_at_epoch': float(getattr(snapshot, 'generated_at_epoch', 0.0) or 0.0),
            'pending_attention_count': int(getattr(snapshot, 'pending_attention_count', 0) or 0),
            'learned_policies_count': int(getattr(snapshot, 'learned_policies_count', 0) or 0),
            'entries': entries,
        }

    @staticmethod
    def _classify_panel_truth(*, has_live_source: bool, payload: dict[str, Any]) -> str:
        """Classify a panel's evidence basis.

        - ``observed``: live service produced non-empty data
        - ``inferred``: no live service, but persisted data exists
        - ``unresolved``: no data at all (empty payload or service missing)
        """
        has_data = bool(payload) and any(
            v for k, v in payload.items() if k != 'truthState'
        )
        if has_live_source and has_data:
            return 'observed'
        if has_data:
            return 'inferred'
        return 'unresolved'

    @staticmethod
    def _format_proactive_dashboard_brief(dashboard: dict[str, Any]) -> str:
        if not dashboard:
            return ''
        pending = int(dashboard.get('pending_attention_count') or 0)
        policies = int(dashboard.get('learned_policies_count') or 0)
        entries = list(dashboard.get('entries') or [])
        if pending == 0 and policies == 0:
            return 'IABV no requiere nada del humano ahora mismo.'
        parts: list[str] = []
        if pending:
            parts.append(f'{pending} pendiente(s) de atencion')
            top = next(
                (
                    e
                    for e in entries
                    if str(e.get('kind') or '') == 'approval_request'
                ),
                None,
            )
            if top and top.get('title'):
                parts.append(f'proximo: {top["title"]}')
        if policies:
            parts.append(f'{policies} politica(s) aprendida(s)')
        return ' | '.join(parts)

    def _build_recent_ui_screenshots(self) -> list[dict[str, Any]]:
        """Consulta `UIScreenshotService.list_recent` si esta wired.

        Devuelve lista serializable a QML. Tolera ausencia del servicio y
        cualquier excepcion (devuelve []). El VM no captura ni elimina;
        solo expone la foto del servicio (contrato AGENTS.md).
        """
        service = getattr(self, 'ui_screenshot_service', None)
        if service is None:
            return []
        try:
            records = service.list_recent(limit=10)
        except Exception:
            return []
        payload: list[dict[str, Any]] = []
        for record in records or ():
            try:
                as_dict = record.as_dict() if hasattr(record, 'as_dict') else dict(record)
            except Exception:
                continue
            if isinstance(as_dict, dict):
                payload.append(as_dict)
        return payload

    @staticmethod
    def _format_control_master_brief(digest: dict[str, Any]) -> str:
        if not digest:
            return ''
        parts: list[str] = []
        vision = str(digest.get('current_vision') or '').strip()
        if vision:
            parts.append(f'Vision: {vision}')
        rules = digest.get('rules_brief') or []
        if rules:
            parts.append(f'Reglas ({len(rules)}): {rules[0]}')
        active = digest.get('active_objectives_brief') or []
        if active:
            parts.append(f'Objetivos activos: {", ".join(active[:3])}')
        unresolved = digest.get('unresolved') or []
        if unresolved:
            parts.append(f'UNRESOLVED: {unresolved[0]}')
        return ' | '.join(parts)

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
        self.overviewChanged.emit()
        self.dossiersChanged.emit()
        self.incidentsChanged.emit()

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
        self.overviewChanged.emit()
        self.incidentsChanged.emit()
        self.dossiersChanged.emit()

    @Slot()
    def viewIncidentEvidence(self) -> None:
        self._evidence_preview = self._build_evidence_preview()
        self.dossiersChanged.emit()

    @Slot()
    def runDeepSelfCheck(self) -> None:
        if self._working:
            return
        self._working = True
        self._status_text = 'Ejecutando autodiagnostico profundo sobre stack local, embeddings, SQL y replay.'
        self.overviewChanged.emit()

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
            self.toolsChanged.emit()
            return
        card = self.tool_record_repository.get_card(tool_id)
        if card is None:
            self._latest_tool_status = 'No encontre la ToolCard seleccionada.'
            self.toolsChanged.emit()
            return
        self._latest_tool_status = self._run_tool_sandbox(card)
        self.refresh()

    @Slot()
    def auditBaseTools(self) -> None:
        if self.tool_record_repository is None or self.tool_teach_service is None:
            self._latest_tool_status = 'La capa Tool Teaching no esta disponible en esta sesion.'
            self.toolsChanged.emit()
            return
        if self._working:
            return
        self._working = True
        self._status_text = 'Ejecutando auditoria base de herramientas en segundo plano...'
        self.overviewChanged.emit()
        self.toolsChanged.emit()

        tool_repo = self.tool_record_repository

        def worker() -> None:
            try:
                ordered = ['ollama_llm', 'playwright_browser', 'desktop_human_runner', 'codex_installed', 'chatgpt_installed', 'chatgpt_web_assisted']
                sections: list[str] = []
                audited = 0
                for tool_id in ordered:
                    card = tool_repo.get_card(tool_id)
                    if card is None:
                        continue
                    audited += 1
                    try:
                        sections.append(self._run_tool_sandbox(card))
                    except Exception as exc:
                        sections.append(f'Herramienta {tool_id}: error — {exc}')
                if audited == 0:
                    self.taskFailed.emit('audit_base_tools', 'No encontre herramientas base para auditar en esta sesion.')
                    return
                header = f'Auditoria base completada. Herramientas auditadas: {audited}.'
                self.taskResolved.emit('audit_base_tools', {'status': header, 'sections': sections})
            except Exception as exc:
                self.taskFailed.emit('audit_base_tools', str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, str, str, str, int, bool)
    def publishBranchAsPR(
        self,
        branch: str,
        title: str,
        body: str,
        base: str,
        diff_lines: int,
        draft: bool,
    ) -> None:
        """F2.2: dispara ``GitHubRemoteService.publish_branch_as_pr`` en un thread.

        El VM no valida politica ni decide la ruta: la policy la aplica el
        propio servicio (``AutonomyGovernancePolicy.allow_github_pr_open``).
        Aca solo sanitizamos argumentos basicos y delegamos. El resultado
        llega via ``taskResolved('publish_pr', ...)`` y se refleja en
        ``publishPrStatus`` / ``publishPrResult`` como Property.
        """

        if self._working:
            return
        if self.github_remote_service is None:
            self._publish_pr_status = (
                'El servicio GitHubRemoteService no esta disponible en esta sesion.'
            )
            self.publishPrChanged.emit()
            return
        branch = (branch or '').strip()
        title = (title or '').strip()
        base = (base or 'main').strip() or 'main'
        if not branch:
            self._publish_pr_status = 'Falta el nombre de la rama para publicar el PR.'
            self.publishPrChanged.emit()
            return
        if not title:
            self._publish_pr_status = 'Falta el titulo del PR.'
            self.publishPrChanged.emit()
            return
        normalized_diff: int | None = int(diff_lines) if diff_lines and diff_lines > 0 else None
        self._working = True
        self._status_text = f'Publicando rama "{branch}" como PR contra "{base}"...'
        self._publish_pr_status = f'Publicando rama "{branch}" como PR contra "{base}"...'
        self._publish_pr_result = {}
        self.overviewChanged.emit()
        self.publishPrChanged.emit()

        service = self.github_remote_service

        def worker() -> None:
            try:
                result = service.publish_branch_as_pr(
                    branch=branch,
                    title=title,
                    body=body or '',
                    base=base,
                    diff_lines=normalized_diff,
                    draft=bool(draft),
                )
                payload = self._serialize_publish_result(result)
                self.taskResolved.emit('publish_pr', payload)
            except Exception as exc:  # pragma: no cover - defensivo
                self.taskFailed.emit('publish_pr', str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _serialize_publish_result(result: Any) -> dict[str, Any]:
        """Convierte un ``PublishResult`` (dataclass) o dict en dict JSON-friendly."""

        if isinstance(result, dict):
            return dict(result)
        payload: dict[str, Any] = {}
        for field in (
            'success',
            'branch',
            'base',
            'pr_number',
            'pr_url',
            'http_status',
            'pushed',
            'blocked_by_policy',
            'required_approval',
            'approval_granted',
            'error',
            'evidence_path',
        ):
            if hasattr(result, field):
                payload[field] = getattr(result, field)
        extra = getattr(result, 'extra', None)
        if isinstance(extra, Mapping):
            payload['extra'] = dict(extra)
        return payload

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
        self.clipboardChanged.emit()

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
        if task_name == 'publish_pr':
            data = dict(payload) if isinstance(payload, Mapping) else {}
            self._publish_pr_result = data
            self._publish_pr_status = self._format_publish_pr_status(data)
            self._status_text = self._publish_pr_status
            self._working = False
            self.overviewChanged.emit()
            self.publishPrChanged.emit()
            return
        if task_name == 'audit_base_tools':
            data = dict(payload) if isinstance(payload, Mapping) else {}
            sections = list(data.get('sections') or [])
            header = str(data.get('status') or f'Auditoria base completada.')
            self._latest_tool_status = header + '\n\n' + '\n\n'.join(sections) if sections else header
            self._status_text = 'Auditoria base de herramientas completada.'
            self._working = False
            self.refresh()
            return
        self._working = False
        self.overviewChanged.emit()

    @Slot(str, str)
    def _apply_failure(self, task_name: str, message: str) -> None:
        self._working = False
        self._status_text = f'No pude completar {task_name}: {message}'
        if task_name == 'publish_pr':
            self._publish_pr_status = f'No pude publicar el PR: {message}'
            self._publish_pr_result = {'success': False, 'error': message}
            self.publishPrChanged.emit()
        elif task_name == 'audit_base_tools':
            self._latest_tool_status = f'Error en auditoria base de herramientas: {message}'
            self.toolsChanged.emit()
        self.overviewChanged.emit()

    @staticmethod
    def _format_publish_pr_status(data: Mapping[str, Any]) -> str:
        branch = data.get('branch') or '<sin-rama>'
        if data.get('success'):
            pr_number = data.get('pr_number')
            pr_url = data.get('pr_url') or ''
            if pr_number:
                return f'PR #{pr_number} abierto para "{branch}". {pr_url}'.strip()
            return f'PR abierto para "{branch}". {pr_url}'.strip()
        if data.get('blocked_by_policy'):
            reason = data.get('error') or 'policy rechazo la apertura del PR'
            return f'Policy bloqueo la apertura del PR: {reason}'
        if data.get('required_approval') and not data.get('approval_granted'):
            return f'Se requiere aprobacion humana para publicar "{branch}" como PR.'
        error = data.get('error') or 'error desconocido'
        return f'No pude publicar "{branch}" como PR: {error}'

    working = Property(bool, get_working, notify=overviewChanged)
    statusText = Property(str, get_status_text, notify=overviewChanged)
    healthSnapshot = Property(dict, get_health_snapshot, notify=overviewChanged)
    recentDossiers = Property(list, get_recent_dossiers, notify=dossiersChanged)
    recentIncidents = Property(list, get_recent_incidents, notify=incidentsChanged)
    incidentFilter = Property(str, get_incident_filter, notify=incidentsChanged)
    improvementBacklog = Property(list, get_improvement_backlog, notify=backlogChanged)
    recentPendingIssues = Property(list, get_recent_pending_issues, notify=backlogChanged)
    knownToolCards = Property(list, get_known_tool_cards, notify=toolsChanged)
    iaComparisons = Property(list, get_ia_comparisons, notify=iaComparisonsChanged)
    environmentSelfModel = Property(dict, get_environment_self_model, notify=worldModelChanged)
    worldModel = Property(dict, get_world_model, notify=worldModelChanged)
    autonomousValidation = Property(dict, get_autonomous_validation, notify=metacognitionChanged)
    portableContext = Property(dict, get_portable_context, notify=metacognitionChanged)
    portableContextBrief = Property(str, get_portable_context_brief, notify=metacognitionChanged)
    evidenceBasis = Property(dict, get_evidence_basis, notify=worldModelChanged)
    controlMasterDigest = Property(dict, get_control_master_digest, notify=metacognitionChanged)
    controlMasterBrief = Property(str, get_control_master_brief, notify=metacognitionChanged)
    toolEvolutionPanel = Property(dict, get_tool_evolution_panel, notify=toolsChanged)
    selfExamination = Property(dict, get_self_examination, notify=metacognitionChanged)
    selfExaminationBrief = Property(str, get_self_examination_brief, notify=metacognitionChanged)
    proactiveDashboard = Property(dict, get_proactive_dashboard, notify=proactiveChanged)
    proactiveDashboardBrief = Property(str, get_proactive_dashboard_brief, notify=proactiveChanged)
    recentUiScreenshots = Property(list, get_recent_ui_screenshots, notify=screenshotsChanged)
    latestToolStatus = Property(str, get_latest_tool_status, notify=toolsChanged)
    publishPrStatus = Property(str, get_publish_pr_status, notify=publishPrChanged)
    publishPrResult = Property('QVariant', get_publish_pr_result, notify=publishPrChanged)
    selectedDossier = Property(dict, get_selected_dossier, notify=dossiersChanged)
    selectedIncident = Property(dict, get_selected_incident, notify=incidentsChanged)
    evidencePreview = Property(str, get_evidence_preview, notify=dossiersChanged)
    latestPacket = Property(str, get_latest_packet, notify=dossiersChanged)
    clipboardNotice = Property(str, get_clipboard_notice, notify=clipboardChanged)
    refreshStatus = Property(str, get_refresh_status, notify=refreshStatusChanged)
    lastRefreshSummary = Property(str, get_last_refresh_summary, notify=refreshStatusChanged)
    lastRefreshResult = Property(str, get_last_refresh_result, notify=refreshStatusChanged)

