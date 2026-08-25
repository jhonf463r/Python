from __future__ import annotations

import logging
from typing import Any

from iabv_v15.infra.persistence.adaptive_session_repository import AdaptiveSessionRepository
from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.ui.qt import QObject, Property, QTimer, Signal, Slot

logger = logging.getLogger(__name__)


class RunHistoryViewModel(QObject):
    dataChanged = Signal()

    def __init__(
        self,
        repository: RunRepository,
        dossier_repository: ExecutionDossierRepository | None = None,
        session_repository: AdaptiveSessionRepository | None = None,
        *,
        defer_initial_refresh: bool = False,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.dossier_repository = dossier_repository
        self.session_repository = session_repository
        self._runs: list[dict] = []
        self._selected_run: dict = {}
        self._selected_dossier: dict = {}
        if defer_initial_refresh:
            QTimer.singleShot(0, self.refresh)
        else:
            self.refresh()

    def get_runs(self) -> list[dict]:
        return self._runs

    def get_selected_run(self) -> dict:
        return self._selected_run

    def get_selected_dossier(self) -> dict:
        return self._selected_dossier

    @Slot()
    def refresh(self) -> None:
        runs = []
        for record in self.repository.list_recent():
            payload = record.model_dump(mode='json')
            dossier = None
            if self.dossier_repository is not None:
                try:
                    dossiers = self.dossier_repository.find_by_run(record.run_id)
                    dossier = dossiers[0].model_dump(mode='json') if dossiers else None
                except Exception as exc:
                    logger.warning('run_history: dossier load failed for run %s: %s', record.run_id, exc)
            role_value = ((payload.get('result') or {}).get('detected_role') or (payload.get('route') or {}).get('task_role') or 'training')
            payload['role_label'] = role_value.replace('_', ' ')
            payload['duration_label'] = f"{int(payload.get('duration_ms') or 0)} ms" if payload.get('duration_ms') is not None else 'sin medicion'
            payload['planner_label'] = 'si' if (payload.get('result') or {}).get('planner_used') else 'no'
            payload['model_label'] = ((payload.get('result') or {}).get('executor_model') or (payload.get('route') or {}).get('model_name') or 'n/d')
            payload['incident_available'] = dossier is not None
            payload['dossier_id'] = (dossier or {}).get('dossier_id', '')
            payload['dossier_severity'] = (dossier or {}).get('severity', '')
            payload['dossier_summary'] = (dossier or {}).get('summary', '')
            payload['error_summary'] = payload.get('error_summary') or (payload.get('result') or {}).get('error_summary', '')
            tp = self._load_task_packet(record.run_id)
            payload['truth_state'] = tp.get('state', '')
            payload['selected_worker_label'] = self._worker_label(tp.get('selected_worker'))
            gate = tp.get('worker_gate_summary', {})
            payload['gate_ran'] = bool(gate.get('ran', False))
            payload['gate_usable'] = bool(gate.get('usable', False))
            payload['gate_available_count'] = int(gate.get('available_count', 0))
            payload['approval_required'] = bool(tp.get('governance_flags', {}).get('approval_required', False))
            unresolved = tp.get('unresolved', [])
            payload['unresolved_count'] = len(unresolved)
            payload['unresolved_summary'] = ', '.join(unresolved[:3]) if unresolved else ''
            tss = tp.get('tool_selection_summary') or {}
            payload['tool_selected'] = str(tss.get('selected_tool', ''))
            payload['tool_selection_reason'] = str(tss.get('reason', ''))
            payload['tool_fallback_used'] = bool(tss.get('fallback_used', False))
            payload['tool_quota_confirmed'] = bool(tss.get('quota_confirmed', False))
            runs.append(payload)
        self._runs = runs
        if self._runs:
            selected_id = self._selected_run.get('run_id') if self._selected_run else ''
            selected = next((item for item in self._runs if item.get('run_id') == selected_id), self._runs[0])
            self._selected_run = selected
            self._selected_dossier = self._load_dossier(selected.get('run_id', ''))
        else:
            self._selected_run = {}
            self._selected_dossier = {}
        self.dataChanged.emit()

    @Slot(str)
    def selectRun(self, run_id: str) -> None:
        selected = next((item for item in self._runs if item.get('run_id') == run_id), None)
        if selected is None:
            return
        self._selected_run = selected
        self._selected_dossier = self._load_dossier(run_id)
        self.dataChanged.emit()

    def _load_task_packet(self, run_id: str) -> dict[str, Any]:
        """Extract task_packet from the AdaptiveSession linked to this run."""
        if not run_id or self.session_repository is None:
            return {}
        try:
            sessions = self.session_repository.find_by_run(run_id)
            if sessions:
                tp = dict(sessions[0].metadata.get('task_packet') or {})
                eb = dict(tp.get('evidence_basis') or {})
                tp['state'] = str(eb.get('state', ''))
                return tp
        except Exception as exc:
            logger.warning('run_history: session load failed for run %s: %s', run_id, exc)
        return {}

    @staticmethod
    def _worker_label(worker: dict | None) -> str:
        if not worker:
            return ''
        email = str(worker.get('email') or '')
        tool = str(worker.get('tool') or '')
        if email and tool:
            return f'{tool} ({email})'
        return tool or email or ''

    def _load_dossier(self, run_id: str) -> dict:
        if not run_id or self.dossier_repository is None:
            return {}
        try:
            dossiers = self.dossier_repository.find_by_run(run_id)
            return dossiers[0].model_dump(mode='json') if dossiers else {}
        except Exception as exc:
            logger.warning('run_history: dossier load failed for run %s: %s', run_id, exc)
            return {}

    runs = Property(list, get_runs, notify=dataChanged)
    selectedRun = Property(dict, get_selected_run, notify=dataChanged)
    selectedDossier = Property(dict, get_selected_dossier, notify=dataChanged)
