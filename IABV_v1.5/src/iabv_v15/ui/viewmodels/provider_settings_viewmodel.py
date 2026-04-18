from __future__ import annotations

import threading

from iabv_v15.domain.models import ProviderConfig
from iabv_v15.services.roles.embedding_index_service import EmbeddingIndexService
from iabv_v15.services.roles.local_role_router import LocalRoleRouter
from iabv_v15.ui.qt import QObject, Property, Signal, Slot


class ProviderSettingsViewModel(QObject):
    dataChanged = Signal()
    healthResolved = Signal(object, str)
    healthFailed = Signal(str)

    def __init__(self, configs: list[ProviderConfig], router: LocalRoleRouter, embedding_service: EmbeddingIndexService) -> None:
        super().__init__()
        self.configs = configs
        self.router = router
        self.embedding_service = embedding_service
        self._providers: list[dict] = []
        self._health_busy = False
        self._status_line = 'Consulta pendiente. Puedes revisar el stack local cuando quieras.'
        self.healthResolved.connect(self._apply_health)
        self.healthFailed.connect(self._apply_health_error)
        self.refresh()

    def _translate_status(self, status: str) -> str:
        mapping = {'ready': 'listo', 'degraded': 'degradado', 'unavailable': 'no disponible', 'optional_inactive': 'opcional no activo', 'idle': 'inactivo'}
        return mapping.get(status, status)

    def get_providers(self) -> list[dict]:
        return self._providers

    def get_policy_text(self) -> str:
        return 'Operacion local oficial: Ollama con qwen3:8b para razonamiento general, Ollama Vision con gemma3:4b para tareas visuales y LM Studio solo como complemento opcional.'

    def get_status_line(self) -> str:
        return self._status_line

    def get_health_busy(self) -> bool:
        return self._health_busy

    @Slot()
    def refresh(self) -> None:
        providers: list[dict] = []
        for config in self.configs:
            providers.append(
                {
                    **config.model_dump(),
                    'health': {
                        'provider_name': config.name,
                        'status': 'inactivo',
                        'available': False,
                        'detail': 'Chequeo pendiente.',
                    },
                }
            )
        providers.append(
            {
                'name': 'Embeddings',
                'kind': 'local',
                'base_url': self.embedding_service.base_url,
                'model': self.embedding_service.primary_model,
                'enabled': True,
                'health': {
                    'provider_name': 'Embeddings',
                    'status': 'inactivo',
                    'available': False,
                    'detail': 'Chequeo pendiente.',
                },
            }
        )
        self._providers = providers
        if not self._health_busy:
            self._status_line = 'Tarjetas reiniciadas. Usa Actualizar estado para una consulta real.'
        self.dataChanged.emit()

    @Slot()
    def refreshHealth(self) -> None:
        if self._health_busy:
            return
        self._health_busy = True
        self._status_line = 'Consultando stack local en segundo plano.'
        self.dataChanged.emit()

        def worker() -> None:
            try:
                health_map = {
                    item.provider_name: item
                    for item in self.router.health_snapshot(refresh=True, max_age_seconds=0.0)
                }
                providers: list[dict] = []
                for card in self._providers:
                    health = health_map.get(card['name'])
                    health_payload = health.model_dump() if health else card.get('health')
                    if health_payload:
                        health_payload['status'] = self._translate_status(health_payload['status'])
                    providers.append({**card, 'health': health_payload})
                self.healthResolved.emit(providers, 'Estado del stack local actualizado sin bloquear la UI.')
            except Exception as exc:  # pragma: no cover - depends on environment
                self.healthFailed.emit(f'No fue posible consultar el stack local: {exc}')

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str)
    def _apply_health(self, providers: list[dict], status_line: str) -> None:
        self._providers = providers
        self._health_busy = False
        self._status_line = status_line
        self.dataChanged.emit()

    @Slot(str)
    def _apply_health_error(self, message: str) -> None:
        self._health_busy = False
        self._status_line = message
        self.dataChanged.emit()

    providers = Property(list, get_providers, notify=dataChanged)
    policyText = Property(str, get_policy_text, constant=True)
    statusLine = Property(str, get_status_line, notify=dataChanged)
    healthBusy = Property(bool, get_health_busy, notify=dataChanged)

