from __future__ import annotations

import time
from typing import Any

from iabv_v15.domain.models import (
    InferenceRequest,
    InferenceResult,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
)
from iabv_v15.services.providers.base import LLMProvider, ProviderUnavailableError

try:  # pragma: no cover - import availability depends on environment
    import httpx
except ImportError:  # pragma: no cover - handled at runtime
    httpx = None


class OpenAIProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, timeout_seconds: float = 45.0) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return self.config.name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction='Analiza el estado de la interfaz y explica el contexto visible en espanol claro.',
            response_mode='ui_analysis',
        )

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction='Esta salida es interna para routing. Infiere la tarea, restricciones y siguiente paso sin responder como chat.',
            response_mode='task_inference',
        )

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction='Responde al usuario final en espanol claro y util, sin mostrar razonamiento interno ni etiquetas de analisis.',
            response_mode='user_answer',
        )

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction='Resume la sesion observada y extrae conocimiento reutilizable en espanol claro.',
            response_mode='session_summary',
        )

    def health_check(self) -> ProviderHealth:
        if not self.config.enabled:
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.UNAVAILABLE, available=False, detail='Proveedor deshabilitado.')
        if self.config.requires_api_key and not self.config.api_key:
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.UNAVAILABLE, available=False, detail='Falta la clave API.')
        if httpx is None:
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.DEGRADED, available=False, detail='httpx no esta instalado.')
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f'{self.config.base_url}/models', headers=self._headers())
                response.raise_for_status()
            latency_ms = (time.perf_counter() - start) * 1000
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.READY, available=True, latency_ms=round(latency_ms, 2), detail='Disponible.')
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.DEGRADED, available=False, latency_ms=round(latency_ms, 2), detail=str(exc))

    def _run(self, request: InferenceRequest, *, system_instruction: str, response_mode: str) -> InferenceResult:
        if httpx is None:
            raise ProviderUnavailableError('httpx no esta instalado.')
        if self.config.requires_api_key and not self.config.api_key:
            raise ProviderUnavailableError(f'{self.name} no tiene credenciales configuradas.')

        payload: dict[str, Any] = {
            'model': self.config.model,
            'input': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'input_text', 'text': system_instruction},
                        {
                            'type': 'input_text',
                            'text': (
                                f'Objetivo: {request.user_goal}\n'
                                f'Prompt: {request.prompt}\n'
                                f'Rol: {request.task_role.value}\n'
                                f'Complejidad: {request.complexity.value}\n'
                                f'Ambiguedad: {request.ambiguity.value}\n'
                                f'Herramientas permitidas: {", ".join(tool.value for tool in request.allowed_tools) or "ninguna"}\n'
                                f'Pasos observados: {len(request.steps)}'
                            ),
                        },
                        *self.images_as_input(request.screenshots),
                    ],
                }
            ],
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f'{self.config.base_url}/responses', headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        text_output = self._extract_output_text(data)
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self.name,
            reasoning_mode=ReasoningMode.CLOUD,
            summary=text_output,
            inferred_task=request.user_goal,
            confidence=0.78 if request.deep_reasoning else 0.72,
            raw_output={'response_mode': response_mode, 'provider_payload': data},
        )

    def _headers(self) -> dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        return headers

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        output = payload.get('output', [])
        chunks: list[str] = []
        for item in output:
            for content in item.get('content', []):
                text = content.get('text')
                if text:
                    chunks.append(text)
        return '\n'.join(chunks).strip() or 'El proveedor no devolvio texto.'
