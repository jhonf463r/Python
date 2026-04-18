from __future__ import annotations

from iabv_v15.infra.persistence.execution_dossier_repository import ExecutionDossierRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class RunHistoryViewModel(QObject):
    dataChanged = Signal()

    def __init__(self, repository: RunRepository, dossier_repository: ExecutionDossierRepository | None = None) -> None:
        super().__init__()
        self.repository = repository
        self.dossier_repository = dossier_repository
        self._runs: list[dict] = []
        self._selected_run: dict = {}
        self._selected_dossier: dict = {}
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
                dossiers = self.dossier_repository.find_by_run(record.run_id)
                dossier = dossiers[0].model_dump(mode='json') if dossiers else None
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

    def _load_dossier(self, run_id: str) -> dict:
        if not run_id or self.dossier_repository is None:
            return {}
        dossiers = self.dossier_repository.find_by_run(run_id)
        return dossiers[0].model_dump(mode='json') if dossiers else {}

    runs = Property(list, get_runs, notify=dataChanged)
    selectedRun = Property(dict, get_selected_run, notify=dataChanged)
    selectedDossier = Property(dict, get_selected_dossier, notify=dataChanged)
