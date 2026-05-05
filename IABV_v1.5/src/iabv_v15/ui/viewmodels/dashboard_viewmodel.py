from __future__ import annotations

import atexit
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from iabv_v15.infra.persistence.episode_repository import EpisodeRepository
from iabv_v15.infra.persistence.knowledge_repository import KnowledgeRepository
from iabv_v15.infra.persistence.run_repository import RunRepository
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.ui.qt import QObject, Property, QTimer, Signal, Slot

logger = logging.getLogger(__name__)


class DashboardViewModel(QObject):
    dataChanged = Signal()
    healthResolved = Signal(object, str)
    healthFailed = Signal(str)
    refreshResolved = Signal(object)
    refreshFailed = Signal(str)

    def __init__(
        self,
        episode_repository: EpisodeRepository,
        knowledge_repository: KnowledgeRepository,
        run_repository: RunRepository,
        role_router: LocalRoleRouter,
        embedding_service: EmbeddingIndexService,
        defer_initial_refresh: bool = False,
    ) -> None:
        super().__init__()
        self.episode_repository = episode_repository
        self.knowledge_repository = knowledge_repository
        self.run_repository = run_repository
        self.role_router = role_router
        self.embedding_service = embedding_service
        self._summary_cards: list[dict] = []
        self._provider_cards: list[dict] = self._placeholder_health_cards()
        self._health_busy = False
        self._health_status = 'Chequeo pendiente. Usa el boton para consultar el stack local.'
        self._bg_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='dvm-bg')
        atexit.register(self._shutdown_bg_pool)
        self.healthResolved.connect(self._apply_health)
        self.healthFailed.connect(self._apply_health_error)
        self.refreshResolved.connect(self._apply_refresh)
        self.refreshFailed.connect(self._apply_refresh_error)
        if defer_initial_refresh:
            QTimer.singleShot(250, self._deferred_initial_refresh)
        else:
            self._refresh_data_sync()

    def _shutdown_bg_pool(self) -> None:
        self._bg_pool.shutdown(wait=False)

    def _deferred_initial_refresh(self) -> None:
        self._bg_pool.submit(self._refresh_data_bg)

    def _mark_timeline(self, phase: str, **extra) -> None:
        try:
            from iabv_v15.infra.startup_timeline import get_global_timeline
            get_global_timeline().mark(phase, **extra)
        except Exception:
            pass

    def _refresh_data_bg(self) -> None:
        self._mark_timeline('dashboard_vm_refresh_start')
        try:
            cards = self._collect_summary_cards()
            self._mark_timeline('dashboard_vm_refresh_done')
            self.refreshResolved.emit(cards)
        except Exception as exc:
            self._mark_timeline('dashboard_vm_refresh_failed', error=str(exc))
            self.refreshFailed.emit(str(exc))

    # Dashboard summary only displays counts; keep limits low to
    # avoid blocking the background thread under SQLite contention.
    _SUMMARY_QUERY_LIMIT = 10

    def _collect_summary_cards(self) -> list[dict]:
        limit = self._SUMMARY_QUERY_LIMIT
        self._mark_timeline('dashboard_vm_refresh_query_episodes_start')
        episodes = self.episode_repository.list_recent(limit=limit)
        self._mark_timeline('dashboard_vm_refresh_query_episodes_done')
        knowledge = self.knowledge_repository.list_recent(limit=limit)
        self._mark_timeline('dashboard_vm_refresh_query_knowledge_done')
        runs = self.run_repository.list_recent(limit=limit)
        self._mark_timeline('dashboard_vm_refresh_query_runs_done')
        index_state = self.embedding_service.describe_index()
        self._mark_timeline('dashboard_vm_refresh_query_index_done')
        return [
            {'title': 'Episodios', 'value': str(len(episodes)), 'hint': 'Sesiones capturadas y listas para revisar'},
            {'title': 'Conocimiento', 'value': str(len(knowledge)), 'hint': 'Memoria confirmada para reutilizacion'},
            {'title': 'Ejecuciones', 'value': str(len(runs)), 'hint': 'Respuestas por rol ya registradas'},
            {'title': 'Indexado', 'value': str(index_state.get('knowledge_count', 0)), 'hint': 'Elementos de conocimiento reflejados por el indice local'},
        ]

    def _refresh_data_sync(self) -> None:
        self._summary_cards = self._collect_summary_cards()
        self.dataChanged.emit()

    @Slot(object)
    def _apply_refresh(self, cards: list[dict]) -> None:
        self._summary_cards = cards
        self.dataChanged.emit()

    @Slot(str)
    def _apply_refresh_error(self, message: str) -> None:
        logger.warning('DashboardViewModel refresh failed: %s', message)

    def _translate_status(self, status: str) -> str:
        mapping = {'ready': 'listo', 'degraded': 'degradado', 'unavailable': 'no disponible', 'optional_inactive': 'opcional no activo', 'idle': 'inactivo'}
        return mapping.get(status, status)

    def _placeholder_health_cards(self) -> list[dict]:
        return [
            {'provider_name': 'Ollama', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.'},
            {'provider_name': 'LM Studio', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.'},
            {'provider_name': 'Embeddings', 'status': 'inactivo', 'available': False, 'detail': 'Chequeo pendiente.'},
        ]

    def get_summary_cards(self) -> list[dict]:
        return self._summary_cards

    def get_provider_cards(self) -> list[dict]:
        return self._provider_cards

    def get_route_policy(self) -> str:
        return 'Stack local por roles: qwen3:8b para razonamiento general, gemma3:4b por vision desde Ollama y qwen3-embedding para recuperacion semantica. LM Studio queda como complemento opcional.'

    def get_health_busy(self) -> bool:
        return self._health_busy

    def get_health_status(self) -> str:
        return self._health_status

    @Slot()
    def refresh(self) -> None:
        self._bg_pool.submit(self._refresh_data_bg)

    @Slot()
    def refreshHealth(self) -> None:
        if self._health_busy:
            return
        self._health_busy = True
        self._health_status = 'Consultando Ollama, Ollama Vision, LM Studio opcional y el indice local sin bloquear la interfaz.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                translated = []
                for health in self.role_router.health_snapshot(refresh=True, max_age_seconds=0.0):
                    payload = health.model_dump()
                    payload['status'] = self._translate_status(payload['status'])
                    translated.append(payload)
                self.healthResolved.emit(translated, 'Stack local actualizado sin bloquear la ventana.')
            except Exception as exc:  # pragma: no cover - depends on environment
                self.healthFailed.emit(f'No fue posible consultar el stack local: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str)
    def _apply_health(self, provider_cards: list[dict], status_text: str) -> None:
        self._provider_cards = provider_cards
        self._health_busy = False
        self._health_status = status_text
        self.dataChanged.emit()

    @Slot(str)
    def _apply_health_error(self, message: str) -> None:
        self._provider_cards = self._placeholder_health_cards()
        self._health_busy = False
        self._health_status = message
        self.dataChanged.emit()

    summaryCards = Property(list, get_summary_cards, notify=dataChanged)
    providerCards = Property(list, get_provider_cards, notify=dataChanged)
    routePolicy = Property(str, get_route_policy, constant=True)
    healthBusy = Property(bool, get_health_busy, notify=dataChanged)
    healthStatus = Property(str, get_health_status, notify=dataChanged)
