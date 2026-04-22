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
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.ui.qt import QObject, Property, Signal, Slot


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
        self._status_text = 'Centro Vivo listo. Pulsa Actualizar para cargar el estado operativo.'
        self._working = False
        self._last_refresh_utc = ''
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

    def get_status_text(self) -> str:
        return self._status_text

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
    statusText = Property(str, get_status_text, notify=dataChanged)
    working = Property(bool, get_working, notify=dataChanged)
    lastRefreshUtc = Property(str, get_last_refresh_utc, notify=dataChanged)

    # ------------------------------------------------------------------
    # Refresh (synchronous, called from ctor and QML slot)
    # ------------------------------------------------------------------
    @Slot()
    def refresh(self) -> None:
        self._orchestrator_queue = self._build_orchestrator_queue()
        self._ia_distribution = self._build_ia_distribution()
        self._heuristic_decisions = self._build_heuristic_decisions()
        self._experiment_metrics = self._build_experiment_metrics()
        self._learning_gaps = self._build_learning_gaps()
        self._self_examination_findings = self._build_self_examination_findings()
        self._world_model_summary = self._build_world_model_summary()
        self._last_refresh_utc = datetime.now(timezone.utc).isoformat(timespec='seconds')
        self._status_text = self._build_status_text()
        self.dataChanged.emit()

    # ------------------------------------------------------------------
    # Internal builders — each reads from one service/repository
    # ------------------------------------------------------------------
    def _build_orchestrator_queue(self) -> list[dict[str, Any]]:
        repo = self.adaptive_session_repository
        if repo is None:
            return []
        try:
            sessions = repo.list_recent(limit=20)
        except Exception:
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
        return items

    def _build_ia_distribution(self) -> list[dict[str, Any]]:
        repo = self.tool_record_repository
        if repo is None:
            return []
        try:
            cards = repo.list_cards()
        except Exception:
            return []
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
        return items

    def _build_heuristic_decisions(self) -> list[dict[str, Any]]:
        lab_repo = self.experiment_lab_repository
        if lab_repo is None:
            return []
        try:
            recommendations = lab_repo.list_recommendations(limit=10)
        except Exception:
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
        return items

    def _build_experiment_metrics(self) -> list[dict[str, Any]]:
        lab_repo = self.experiment_lab_repository
        if lab_repo is None:
            return []
        try:
            runs = lab_repo.list_runs(limit=20)
        except Exception:
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
        return items

    def _build_learning_gaps(self) -> list[dict[str, Any]]:
        backlog_dir = self._data_root / 'chat_research_backlog'
        if not backlog_dir.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        try:
            files = sorted(backlog_dir.glob('*.jsonl'), reverse=True)
            for fp in files[:5]:
                for line in fp.read_text(encoding='utf-8').strip().splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        entries.append({
                            'kind': entry.get('kind', ''),
                            'label': entry.get('label', ''),
                            'snippet': entry.get('snippet', ''),
                            'research_hint': entry.get('research_hint', ''),
                            'timestamp': entry.get('timestamp', ''),
                            'session_id': entry.get('session_id', ''),
                        })
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            pass
        entries.sort(key=lambda e: e.get('timestamp', ''), reverse=True)
        return entries[:30]

    def _build_self_examination_findings(self) -> list[dict[str, Any]]:
        service = self.self_examination_service
        if service is None:
            return []
        try:
            review = service.current_review(refresh=False)
        except Exception:
            return []
        if review is None:
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
        return items

    def _build_world_model_summary(self) -> dict[str, Any]:
        service = self.world_model_service
        if service is None:
            return {}
        try:
            snapshot = service.current_model()
        except Exception:
            return {}
        if snapshot is None:
            return {}
        dumped = snapshot.model_dump(mode='json') if hasattr(snapshot, 'model_dump') else {}
        windows = dumped.get('active_windows', dumped.get('windows', []))
        tools = dumped.get('tool_live_status', [])
        network = dumped.get('network_status', dumped.get('network', {}))
        focus = dumped.get('focused_window', dumped.get('focus_window', ''))
        return {
            'window_count': len(windows),
            'focus_window': focus,
            'tool_count': len(tools),
            'tools_ready': sum(1 for t in tools if (t.get('status') or t.get('live_status', '')) == 'ready'),
            'tools_degraded': sum(1 for t in tools if (t.get('status') or t.get('live_status', '')) == 'degraded'),
            'network_connected': bool(network.get('connected', False)),
            'active_blockages': dumped.get('active_blockages', []),
        }

    def _build_status_text(self) -> str:
        queue_count = len(self._orchestrator_queue)
        active = sum(1 for s in self._orchestrator_queue if s.get('status') in ('executing', 'ready_to_execute'))
        tools_ready = self._world_model_summary.get('tools_ready', 0)
        tool_count = self._world_model_summary.get('tool_count', 0)
        findings_count = len(self._self_examination_findings)
        gaps_count = len(self._learning_gaps)
        parts: list[str] = []
        parts.append(f'{queue_count} sesiones en cola ({active} activas)')
        parts.append(f'{tools_ready}/{tool_count} herramientas listas')
        if findings_count:
            parts.append(f'{findings_count} hallazgos de autoexaminacion')
        if gaps_count:
            parts.append(f'{gaps_count} areas de investigacion pendientes')
        return ' | '.join(parts)
