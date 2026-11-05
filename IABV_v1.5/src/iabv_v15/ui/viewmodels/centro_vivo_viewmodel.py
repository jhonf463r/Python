"""Centro Vivo — panel operativo unificado.

Agrega en una sola vista:
- cola del orquestador (sesiones adaptativas pendientes/ejecutando)
- reparto entre IAs (que asistente se llamo, con que cuenta, que respondio)
- decisiones de ruta (heuristica, score del StrategySelector)
- metricas vivas (ExperimentLab: rutas comparadas, ganador, ventaja %)
- gaps de aprendizaje (TeachingGaps / research backlog)
- findings de autoexaminacion (patrones repetidos, degradaciones)
- world model (ventanas/foco/red/herramientas)

El ViewModel NO decide rutas ni modifica estado: solo lee y expone
Properties para que la QML page lo renderice.
"""
from __future__ import annotations

import json
import os
import stat
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.ui.qt import QObject, Property, QTimer, Signal, Slot


class CentroVivoViewModel(QObject):
    dataChanged = Signal()

    def __init__(
        self,
        *,
        adaptive_session_repository: Any | None = None,
        experiment_lab_repository: Any | None = None,
        tool_record_repository: Any | None = None,
        world_model_service: Any | None = None,
        self_examination_service: Any | None = None,
        portable_context_service: Any | None = None,
        evolution_review_service: Any | None = None,
        data_root: str | Path = '',
        defer_initial_refresh: bool = False,
    ) -> None:
        super().__init__()
        self.adaptive_session_repository = adaptive_session_repository
        self.experiment_lab_repository = experiment_lab_repository
        self.tool_record_repository = tool_record_repository
        self.world_model_service = world_model_service
        self.self_examination_service = self_examination_service
        self.portable_context_service = portable_context_service
        self.evolution_review_service = evolution_review_service
        self._data_root = Path(data_root) if data_root else Path('.')

        self._orchestrator_queue: list[dict[str, Any]] = []
        self._ia_distribution: list[dict[str, Any]] = []
        self._heuristic_decisions: list[dict[str, Any]] = []
        self._experiment_metrics: list[dict[str, Any]] = []
        self._learning_gaps: list[dict[str, Any]] = []
        self._self_examination_findings: list[dict[str, Any]] = []
        self._world_model_summary: dict[str, Any] = {}
        self._account_inventory: list[dict[str, Any]] = []
        self._account_inventory_summary: dict[str, Any] = {}
        self._status_text = 'Centro Vivo listo. Pulsa Actualizar para cargar el estado operativo.'
        self._working = False
        self._last_refresh_utc = ''
        self._source_statuses: dict[str, str] = {}
        self._source_errors: dict[str, str] = {}
        self._source_reports: dict[str, dict[str, Any]] = {}
        if defer_initial_refresh:
            QTimer.singleShot(0, self.refresh)
        else:
            self.refresh()

    # ------------------------------------------------------------------
    # Property getters
    # ------------------------------------------------------------------
    def get_orchestrator_queue(self) -> list[dict[str, Any]]:
        return self._orchestrator_queue

    def get_ia_distribution(self) -> list[dict[str, Any]]:
        return self._ia_distribution

    def get_heuristic_decisions(self) -> list[dict[str, Any]]:
        return self._heuristic_decisions

    def get_experiment_metrics(self) -> list[dict[str, Any]]:
        return self._experiment_metrics

    def get_learning_gaps(self) -> list[dict[str, Any]]:
        return self._learning_gaps

    def get_self_examination_findings(self) -> list[dict[str, Any]]:
        return self._self_examination_findings

    def get_world_model_summary(self) -> dict[str, Any]:
        return self._world_model_summary

    def get_account_inventory(self) -> list[dict[str, Any]]:
        return self._account_inventory

    def get_account_inventory_summary(self) -> dict[str, Any]:
        return self._account_inventory_summary

    def get_status_text(self) -> str:
        return self._status_text

    def get_source_statuses(self) -> dict[str, str]:
        return dict(self._source_statuses)

    def get_source_reports(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in self._source_reports.items()}

    def _record_source_status(self, source: str, status: str, error: str = '') -> None:
        self._source_statuses[source] = status
        if error:
            self._source_errors[source] = error[:160]
        else:
            self._source_errors.pop(source, None)

    def _record_source_report(self, source: str, report: Any) -> None:
        if report is None:
            self._source_reports.pop(source, None)
            return
        serializer = getattr(report, 'to_dict', None)
        if callable(serializer):
            self._source_reports[source] = serializer()
        else:
            self._source_reports[source] = {
                'status': getattr(getattr(report, 'status', None), 'value', str(getattr(report, 'status', 'UNKNOWN'))),
                'records_seen': getattr(report, 'records_seen', None),
                'records_loaded': getattr(report, 'records_loaded', None),
                'missing_ids': list(getattr(report, 'missing_ids', []) or []),
                'failed_ids': list(getattr(report, 'failed_ids', []) or []),
                'collection_error_type': getattr(report, 'collection_error_type', ''),
            }

    def get_working(self) -> bool:
        return self._working

    def get_last_refresh_utc(self) -> str:
        return self._last_refresh_utc

    # ------------------------------------------------------------------
    # Qt Properties
    # ------------------------------------------------------------------
    orchestratorQueue = Property(list, get_orchestrator_queue, notify=dataChanged)
    iaDistribution = Property(list, get_ia_distribution, notify=dataChanged)
    heuristicDecisions = Property(list, get_heuristic_decisions, notify=dataChanged)
    experimentMetrics = Property(list, get_experiment_metrics, notify=dataChanged)
    learningGaps = Property(list, get_learning_gaps, notify=dataChanged)
    selfExaminationFindings = Property(list, get_self_examination_findings, notify=dataChanged)
    worldModelSummary = Property(dict, get_world_model_summary, notify=dataChanged)
    accountInventory = Property(list, get_account_inventory, notify=dataChanged)
    accountInventorySummary = Property(dict, get_account_inventory_summary, notify=dataChanged)
    statusText = Property(str, get_status_text, notify=dataChanged)
    sourceStatuses = Property(dict, get_source_statuses, notify=dataChanged)
    working = Property(bool, get_working, notify=dataChanged)
    lastRefreshUtc = Property(str, get_last_refresh_utc, notify=dataChanged)

    # ------------------------------------------------------------------
    # Refresh (synchronous, called from ctor and QML slot)
    # ------------------------------------------------------------------
    @Slot()
    def refresh(self) -> None:
        self._source_statuses = {}
        self._source_errors = {}
        self._orchestrator_queue = self._build_orchestrator_queue()
        self._ia_distribution = self._build_ia_distribution()
        self._heuristic_decisions = self._build_heuristic_decisions()
        self._experiment_metrics = self._build_experiment_metrics()
        self._learning_gaps = self._build_learning_gaps()
        self._self_examination_findings = self._build_self_examination_findings()
        self._world_model_summary = self._build_world_model_summary()
        inv = self._build_account_inventory()
        self._account_inventory = inv.get('entries', [])
        self._account_inventory_summary = inv.get('summary', {})
        self._last_refresh_utc = datetime.now(timezone.utc).isoformat(timespec='seconds')
        self._status_text = self._build_status_text()
        self.dataChanged.emit()

    # ------------------------------------------------------------------
    # Internal builders — each reads from one service/repository
    # ------------------------------------------------------------------
    def _build_orchestrator_queue(self) -> list[dict[str, Any]]:
        repo = self.adaptive_session_repository
        if repo is None:
            self._record_source_status('adaptive_session_repository', 'NOT_CONFIGURED')
            return []
        try:
            sessions = repo.list_recent(limit=20)
        except Exception as exc:
            self._record_source_status('adaptive_session_repository', 'READ_FAILED', type(exc).__name__)
            return []
        items: list[dict[str, Any]] = []
        for session in sessions:
            dumped = session.model_dump(mode='json') if hasattr(session, 'model_dump') else {}
            items.append({
                'session_id': dumped.get('session_id', ''),
                'user_goal': dumped.get('user_goal', ''),
                'status': dumped.get('status', ''),
                'chosen_pack': dumped.get('chosen_pack_title', '') or dumped.get('chosen_pack_id', ''),
                'created_at': dumped.get('created_at_utc', ''),
                'updated_at': dumped.get('updated_at_utc', ''),
            })
        self._record_source_status('adaptive_session_repository', 'READ_OK')
        return items

    def _build_ia_distribution(self) -> list[dict[str, Any]]:
        repo = self.tool_record_repository
        if repo is None:
            self._record_source_status('tool_record_repository', 'NOT_CONFIGURED')
            return []
        try:
            cards = repo.list_cards()
        except Exception as exc:
            report = getattr(exc, 'report', None) or getattr(repo, 'last_read_report', None)
            self._record_source_report('tool_record_repository', report)
            report_status = getattr(getattr(report, 'status', None), 'value', '')
            status = 'READ_PARTIAL' if report_status == 'READ_PARTIAL' else 'READ_FAILED'
            self._record_source_status('tool_record_repository', status, type(exc).__name__)
            return []
        self._record_source_report('tool_record_repository', getattr(repo, 'last_read_report', None))
        items: list[dict[str, Any]] = []
        for card in cards:
            dumped = card.model_dump(mode='json') if hasattr(card, 'model_dump') else {}
            tool_id = dumped.get('tool_id', '')
            status = dumped.get('live_status', dumped.get('status', ''))
            category = dumped.get('category', '')
            last_used = dumped.get('last_used_utc', '')
            items.append({
                'tool_id': tool_id,
                'status': status,
                'category': category,
                'last_used': last_used,
            })
        self._record_source_status('tool_record_repository', 'READ_OK')
        return items

    def _build_heuristic_decisions(self) -> list[dict[str, Any]]:
        lab_repo = self.experiment_lab_repository
        if lab_repo is None:
            self._record_source_status('experiment_recommendations', 'NOT_CONFIGURED')
            return []
        try:
            recommendations = lab_repo.list_recommendations(limit=10)
        except Exception as exc:
            self._record_source_status('experiment_recommendations', 'READ_FAILED', type(exc).__name__)
            return []
        items: list[dict[str, Any]] = []
        for rec in recommendations:
            dumped = rec.model_dump(mode='json') if hasattr(rec, 'model_dump') else {}
            items.append({
                'recommendation_id': dumped.get('recommendation_id', ''),
                'domain': dumped.get('domain', ''),
                'subject_key': dumped.get('subject_key', ''),
                'winner_label': dumped.get('winner_label', ''),
                'advantage_pct': dumped.get('advantage_pct', 0.0),
                'confidence': dumped.get('confidence', 0.0),
                'summary': dumped.get('summary', ''),
            })
        self._record_source_status('experiment_recommendations', 'READ_OK')
        return items

    def _build_experiment_metrics(self) -> list[dict[str, Any]]:
        lab_repo = self.experiment_lab_repository
        if lab_repo is None:
            self._record_source_status('experiment_runs', 'NOT_CONFIGURED')
            return []
        try:
            runs = lab_repo.list_runs(limit=20)
        except Exception as exc:
            self._record_source_status('experiment_runs', 'READ_FAILED', type(exc).__name__)
            return []
        items: list[dict[str, Any]] = []
        for run in runs:
            dumped = run.model_dump(mode='json') if hasattr(run, 'model_dump') else {}
            items.append({
                'run_id': dumped.get('run_id', ''),
                'domain': dumped.get('domain', ''),
                'subject_key': dumped.get('subject_key', ''),
                'candidate_label': dumped.get('candidate_label', dumped.get('label', '')),
                'score': dumped.get('score', 0.0),
                'duration_ms': dumped.get('duration_ms', 0),
                'assistant_kind': dumped.get('assistant_kind', ''),
            })
        self._record_source_status('experiment_runs', 'READ_OK')
        return items

    def _build_learning_gaps(self) -> list[dict[str, Any]]:
        backlog_dir = self._data_root / 'chat_research_backlog'
        try:
            directory_stat = backlog_dir.stat()
        except FileNotFoundError:
            self._record_source_status('learning_gaps', 'CONFIRMED_NOT_FOUND')
            return []
        except OSError as exc:
            self._record_source_status('learning_gaps', 'READ_FAILED', type(exc).__name__)
            return []
        if not stat.S_ISDIR(directory_stat.st_mode):
            self._record_source_status('learning_gaps', 'READ_FAILED', 'backlog_path_is_not_directory')
            return []
        entries: list[dict[str, Any]] = []
        partial = False
        try:
            files = sorted(
                (Path(entry.path) for entry in os.scandir(backlog_dir)
                 if entry.is_file() and entry.name.endswith('.jsonl')),
                reverse=True,
            )
            for fp in files[:5]:
                try:
                    raw_lines = fp.read_text(encoding='utf-8').splitlines()
                except Exception:
                    partial = True
                    continue
                for line in raw_lines:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if not isinstance(entry, dict):
                            raise TypeError('backlog_line_not_object')
                        entries.append({
                            'kind': entry.get('kind', ''),
                            'label': entry.get('label', ''),
                            'snippet': entry.get('snippet', ''),
                            'research_hint': entry.get('research_hint', ''),
                            'timestamp': entry.get('timestamp', ''),
                            'session_id': entry.get('session_id', ''),
                        })
                    except (json.JSONDecodeError, KeyError, TypeError):
                        partial = True
        except Exception as exc:
            self._record_source_status(
                'learning_gaps', 'READ_PARTIAL' if entries else 'READ_FAILED', type(exc).__name__
            )
            return entries[:30]
        entries.sort(key=lambda e: e.get('timestamp', ''), reverse=True)
        self._record_source_status(
            'learning_gaps', 'READ_PARTIAL' if partial else 'READ_OK',
            'one_or_more_backlog_entries_unreadable' if partial else '',
        )
        return entries[:30]

    def _build_self_examination_findings(self) -> list[dict[str, Any]]:
        service = self.self_examination_service
        if service is None:
            self._record_source_status('self_examination_service', 'NOT_CONFIGURED')
            return []
        try:
            review = service.current_review(refresh=False)
        except Exception as exc:
            self._record_source_status('self_examination_service', 'READ_FAILED', type(exc).__name__)
            return []
        if review is None:
            self._record_source_status('self_examination_service', 'CONFIRMED_NOT_FOUND')
            return []
        dumped = review.model_dump(mode='json') if hasattr(review, 'model_dump') else {}
        findings_raw = dumped.get('findings', [])
        items: list[dict[str, Any]] = []
        for f in findings_raw:
            items.append({
                'finding_id': f.get('finding_id', ''),
                'category': f.get('category', ''),
                'title': f.get('title', ''),
                'severity': f.get('severity', ''),
                'confidence': f.get('confidence', 0.0),
                'recommendation': f.get('recommendation', ''),
                'status': f.get('status', ''),
            })
        self._record_source_status('self_examination_service', 'READ_OK')
        return items

    def _build_world_model_summary(self) -> dict[str, Any]:
        service = self.world_model_service
        if service is None:
            self._record_source_status('world_model_service', 'NOT_CONFIGURED')
            return {}
        try:
            snapshot = service.current_model()
        except Exception as exc:
            self._record_source_status('world_model_service', 'READ_FAILED', type(exc).__name__)
            return {}
        if snapshot is None:
            self._record_source_status('world_model_service', 'CONFIRMED_NOT_FOUND')
            return {}
        dumped = snapshot.model_dump(mode='json') if hasattr(snapshot, 'model_dump') else {}
        windows = dumped.get('active_windows', dumped.get('windows', []))
        tools = dumped.get('tool_live_status', [])
        network = dumped.get('network_status', dumped.get('network', {}))
        focus = dumped.get('focused_window', dumped.get('focus_window', ''))
        summary = {
            'window_count': len(windows),
            'focus_window': focus,
            'tool_count': len(tools),
            'tools_ready': sum(1 for t in tools if (t.get('status') or t.get('live_status', '')) in ('listo', 'abierto', 'disponible', 'ready')),
            'tools_degraded': sum(1 for t in tools if (t.get('status') or t.get('live_status', '')) in ('lento', 'limitado', 'degraded')),
            'network_connected': bool(network.get('connected', False) or str(network.get('status', '')).strip() in ('conectado', 'lento')),
            'active_blockages': dumped.get('active_blockages', []),
        }
        self._record_source_status('world_model_service', 'READ_OK')
        return summary

    def _build_account_inventory(self) -> dict[str, Any]:
        """Build account inventory from the formal snapshot.

        Swallows failures gracefully — the UI never crashes because the
        scanner is unavailable.
        """
        try:
            from iabv_v15.services.account_resource_scanner import (
                build_inventory_snapshot,
            )
            snapshot = build_inventory_snapshot()
        except Exception as exc:
            self._record_source_status('account_inventory', 'READ_FAILED', type(exc).__name__)
            return {'entries': [], 'summary': {}}

        entries: list[dict[str, Any]] = []
        for entry in snapshot.entries:
            resets_at = ''
            if entry.quota_resets_at:
                resets_at = entry.quota_resets_at.isoformat()
            entries.append({
                'email': entry.email,
                'browser': entry.browser,
                'profile': entry.profile,
                'tool': entry.tool,
                'has_session': entry.has_session,
                'quota_remaining': entry.quota_remaining,
                'quota_limit': entry.quota_limit,
                'quota_resets_at': resets_at,
                'exhausted': entry.exhausted,
                'score': round(entry.score, 4),
                'status': entry.status.value,
                'block_signals': entry.block_signals,
            })

        # Build continuity queue (top entries)
        queue: list[dict[str, Any]] = []
        for entry in snapshot.continuity_queue[:5]:
            queue.append({
                'email': entry.email,
                'tool': entry.tool,
                'score': round(entry.score, 4),
                'quota_remaining': entry.quota_remaining,
            })

        summary = {
            'active_count': snapshot.active_count,
            'exhausted_count': snapshot.exhausted_count,
            'unresolved_count': snapshot.unresolved_count,
            'total_remaining_messages': snapshot.total_remaining_messages,
            'tools_available': snapshot.tools_available,
            'continuity_queue': queue,
            'next_recommended': queue[0] if queue else None,
            'unresolved_items': snapshot.unresolved_items,
            'requires_human_approval': True,
        }

        self._record_source_status('account_inventory', 'READ_OK')
        return {'entries': entries, 'summary': summary}

    @Slot(str, str)
    def approveAccountSwitch(self, tool: str, email: str) -> None:
        """Slot called from QML when user approves switching to a specific account.

        This is the human-in-the-loop approval point.  Writes to the
        ``AccountApprovalLedger`` so the worker health gate uses this
        account as priority override for *tool* on the next dispatch.
        Other tools are NOT affected.
        """
        from iabv_v15.domain.models import AccountApproval
        from iabv_v15.services.account_approval_ledger import AccountApprovalLedger

        import logging
        logger = logging.getLogger(__name__)

        approval = AccountApproval(
            tool=tool,
            email=email,
            origin='centro_vivo_ui',
            reason='user_manual_approval',
        )

        try:
            ledger = AccountApprovalLedger(data_root=str(self._data_root))
            ledger.approve(approval)
        except Exception:
            logger.warning('approveAccountSwitch: ledger write failed for %s/%s', tool, email)

        logger.info(
            'account_switch_approved: tool=%s email=%s (user decision via ledger)',
            tool, email,
        )
        self.refresh()

    def _build_status_text(self) -> str:
        queue_count = len(self._orchestrator_queue)
        active = sum(1 for s in self._orchestrator_queue if s.get('status') in ('executing', 'ready_to_execute'))
        tools_ready = self._world_model_summary.get('tools_ready', 0)
        tool_count = self._world_model_summary.get('tool_count', 0)
        findings_count = len(self._self_examination_findings)
        gaps_count = len(self._learning_gaps)
        inv_active = self._account_inventory_summary.get('active_count', 0)
        inv_exhausted = self._account_inventory_summary.get('exhausted_count', 0)
        parts: list[str] = []
        parts.append(f'{queue_count} sesiones en cola ({active} activas)')
        parts.append(f'{tools_ready}/{tool_count} herramientas listas')
        if inv_active or inv_exhausted:
            parts.append(f'{inv_active} cuentas activas, {inv_exhausted} agotadas')
        if findings_count:
            parts.append(f'{findings_count} hallazgos de autoexaminacion')
        if gaps_count:
            parts.append(f'{gaps_count} areas de investigacion pendientes')
        non_confirmed = [
            f'{source}={status}'
            for source, status in sorted(self._source_statuses.items())
            if status != 'READ_OK'
        ]
        if non_confirmed:
            parts.append('Fuentes no verificadas: ' + ', '.join(non_confirmed))
        return ' | '.join(parts)
