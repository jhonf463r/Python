from __future__ import annotations

import threading
from typing import Callable, Optional

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    InferenceRequest,
    InferenceResult,
    ProviderHealth,
    ProviderKind,
    ReasoningMode,
    RouteDecision,
)
from iabv_v15.services.providers.base import LLMProvider


HealthHandler = Callable[[list[ProviderHealth]], None]


class ProviderRouter:
    def __init__(self, local_provider: LLMProvider, fallback_local_provider: LLMProvider, cloud_provider: LLMProvider):
        self.local_provider = local_provider
        self.fallback_local_provider = fallback_local_provider
        self.cloud_provider = cloud_provider
        self._health_handler: Optional[HealthHandler] = None
        self._health_lock = threading.RLock()

    def decide(self, request: InferenceRequest) -> RouteDecision:
        if request.offline_only:
            return RouteDecision(
                primary_provider=self.local_provider.name,
                primary_kind=ProviderKind.LOCAL,
                fallback_provider=self.fallback_local_provider.name,
                reason='Offline-only request forces local execution.',
            )

        if self._contains_sensitive_browser_teach_data(request):
            return RouteDecision(
                primary_provider=self.local_provider.name,
                primary_kind=ProviderKind.LOCAL,
                fallback_provider=self.fallback_local_provider.name,
                reason='Sensitive browser-teach observations stay local until a cloud-safe summary exists.',
            )

        if len(request.screenshots) <= 1 and request.complexity == ComplexityLevel.SIMPLE and request.ambiguity == AmbiguityLevel.LOW:
            return RouteDecision(
                primary_provider=self.local_provider.name,
                primary_kind=ProviderKind.LOCAL,
                fallback_provider=self.fallback_local_provider.name,
                reason='Single-capture low-ambiguity task fits local routing.',
            )

        return RouteDecision(
            primary_provider=self.cloud_provider.name,
            primary_kind=ProviderKind.CLOUD,
            fallback_provider=self.local_provider.name,
            reason='Multi-capture or deep reasoning task benefits from cloud analysis.',
        )

    def infer_task(self, request: InferenceRequest) -> tuple[RouteDecision, InferenceResult]:
        return self._execute_with_route(request, 'infer_task')

    def analyze_ui(self, request: InferenceRequest) -> tuple[RouteDecision, InferenceResult]:
        return self._execute_with_route(request, 'analyze_ui')

    def summarize_session(self, request: InferenceRequest) -> tuple[RouteDecision, InferenceResult]:
        return self._execute_with_route(request, 'summarize_session')

    def health_snapshot(self) -> list[ProviderHealth]:
        return [
            self.local_provider.health_check(),
            self.fallback_local_provider.health_check(),
            self.cloud_provider.health_check(),
        ]

    def register_health_handler(self, handler: HealthHandler | None) -> None:
        """Registra el callback que emite providerHealthChanged en la UI.

        El handler recibe la lista de ProviderHealth tal como la devuelve
        health_snapshot(). Pasar None desengancha el handler activo. Siguiendo
        el patron de CredentialBroker.register_prompt_handler, esto no cambia
        la ruta ni dispara autonomia; solo media entre el estado observable
        y la capa UI.
        """
        with self._health_lock:
            self._health_handler = handler

    def publish_health(self) -> list[ProviderHealth]:
        """Toma un snapshot fresco y lo publica al handler si hay uno.

        Devuelve el snapshot para que el llamador pueda usarlo directamente
        (bootstrap, refresh manual, etc). Si el handler levanta una excepcion
        se propaga al llamador; no silenciamos errores aqui para que la UI
        pueda reportar el fallo en evidencia evolutiva.
        """
        snapshot = self.health_snapshot()
        with self._health_lock:
            handler = self._health_handler
        if handler is not None:
            handler(list(snapshot))
        return snapshot

    def _execute_with_route(self, request: InferenceRequest, method_name: str) -> tuple[RouteDecision, InferenceResult]:
        route = self.decide(request)
        local_method = getattr(self.local_provider, method_name)
        fallback_local_method = getattr(self.fallback_local_provider, method_name)
        cloud_method = getattr(self.cloud_provider, method_name)

        if route.primary_kind == ProviderKind.LOCAL:
            try:
                return route, local_method(request)
            except Exception as local_exc:
                try:
                    degraded = fallback_local_method(request)
                    degraded.reasoning_mode = ReasoningMode.DEGRADED
                    degraded.confidence_reduced = True
                    degraded.used_fallback = True
                    degraded.provider_name = self.fallback_local_provider.name
                    return route, degraded
                except Exception as fallback_exc:
                    if not request.offline_only and not self._contains_sensitive_browser_teach_data(request):
                        try:
                            cloud_result = cloud_method(request)
                            cloud_result.used_fallback = True
                            cloud_result.provider_name = self.cloud_provider.name
                            return route, cloud_result
                        except Exception as cloud_exc:
                            raise RuntimeError(
                                'Ningun proveedor pudo responder. '
                                f'{self.local_provider.name}: {local_exc}. '
                                f'{self.fallback_local_provider.name}: {fallback_exc}. '
                                f'{self.cloud_provider.name}: {cloud_exc}.'
                            ) from cloud_exc
                    raise RuntimeError(
                        'No hay proveedor local disponible. '
                        f'{self.local_provider.name}: {local_exc}. '
                        f'{self.fallback_local_provider.name}: {fallback_exc}.'
                    ) from fallback_exc

        try:
            return route, cloud_method(request)
        except Exception as cloud_exc:
            try:
                degraded = local_method(request)
                degraded.reasoning_mode = ReasoningMode.DEGRADED
                degraded.confidence_reduced = True
                degraded.used_fallback = True
                degraded.provider_name = self.local_provider.name
                return route, degraded
            except Exception as local_exc:
                try:
                    degraded = fallback_local_method(request)
                    degraded.reasoning_mode = ReasoningMode.DEGRADED
                    degraded.confidence_reduced = True
                    degraded.used_fallback = True
                    degraded.provider_name = self.fallback_local_provider.name
                    return route, degraded
                except Exception as fallback_exc:
                    raise RuntimeError(
                        'Ningun proveedor pudo responder. '
                        f'{self.cloud_provider.name}: {cloud_exc}. '
                        f'{self.local_provider.name}: {local_exc}. '
                        f'{self.fallback_local_provider.name}: {fallback_exc}.'
                    ) from fallback_exc

    def _contains_sensitive_browser_teach_data(self, request: InferenceRequest) -> bool:
        capture_channels = request.metadata.get('capture_channels') or []
        browser_teach_mode = bool(request.metadata.get('browser_teach_mode'))
        contains_sensitive_data = bool(request.metadata.get('contains_sensitive_data'))
        redacted_for_cloud = bool(request.metadata.get('redacted_for_cloud'))
        if contains_sensitive_data:
            return True
        if browser_teach_mode and capture_channels and not redacted_for_cloud:
            return True
        return False
