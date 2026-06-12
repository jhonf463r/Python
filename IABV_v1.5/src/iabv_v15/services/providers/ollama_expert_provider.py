"""OllamaExpertProvider: integración nativa Ollama con comportamiento experto.

Usa /api/chat (endpoint nativo) en vez de /v1/chat/completions.
Parámetros ajustados por tipo de tarea. Retry con contexto reducido.
Compatible con qwen3:8b, llama3.x, deepseek-coder y otros modelos Ollama.
"""
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

try:
    import httpx
except ImportError:
    httpx = None


_MODE_PARAMS: dict[str, dict[str, Any]] = {
    'task_inference': {
        'num_predict': 512,
        'temperature': 0.1,
        'top_p': 0.9,
        'think': False,
        'repeat_penalty': 1.1,
    },
    'ui_analysis': {
        'num_predict': 512,
        'temperature': 0.2,
        'top_p': 0.9,
        'think': False,
        'repeat_penalty': 1.1,
    },
    'session_summary': {
        'num_predict': 1024,
        'temperature': 0.3,
        'top_p': 0.95,
        'think': False,
        'repeat_penalty': 1.05,
    },
    'user_answer': {
        'num_predict': 2048,
        'temperature': 0.4,
        'top_p': 0.95,
        'think': False,
        'repeat_penalty': 1.05,
    },
    'deep_reasoning': {
        'num_predict': 4096,
        'temperature': 0.6,
        'top_p': 0.95,
        'think': True,
        'repeat_penalty': 1.0,
    },
}

_SYSTEM_PROMPTS: dict[str, str] = {
    'task_inference': (
        'Eres el planificador interno de IABV v1.5. '
        'Tu salida es INTERNA para routing, nunca visible al usuario. '
        'Responde en máximo 3 oraciones: intención, rol probable, siguiente paso. '
        'Sin cadena de pensamiento, sin markdown.'
    ),
    'ui_analysis': (
        'Eres el analista visual de IABV v1.5. '
        'Describe la interfaz en español claro sin inventar elementos. '
        'Destaca solo lo útil para la tarea activa.'
    ),
    'session_summary': (
        'Eres el sintetizador de IABV v1.5. '
        'Resume la sesión en español claro y extrae pistas reutilizables. '
        'No expongas secretos ni razonamiento interno.'
    ),
    'user_answer': (
        'Eres el asistente de IABV v1.5. '
        'Responde en español claro, útil y directo. '
        'Sin etiquetas internas. Sin emojis. '
        'Si faltan datos, dilo brevemente y orienta el siguiente paso.'
    ),
}


class OllamaExpertProvider(LLMProvider):
    """Provider Ollama nativo con parámetros expertos por tipo de tarea."""

    def __init__(
        self,
        config: ProviderConfig,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        raw_url = (config.base_url or 'http://127.0.0.1:11434').rstrip('/')
        self._base_url = raw_url.removesuffix('/v1')

    @property
    def name(self) -> str:
        return self.config.name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._run(request, response_mode='ui_analysis')

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._run(request, response_mode='task_inference')

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._run(request, response_mode='user_answer')

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._run(request, response_mode='session_summary')

    def health_check(self) -> ProviderHealth:
        if not self.config.enabled:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNAVAILABLE,
                available=False,
                detail='Proveedor deshabilitado.',
            )
        if httpx is None:
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                available=False,
                detail='httpx no instalado.',
            )
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f'{self._base_url}/api/tags')
                resp.raise_for_status()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            models = [m.get('name', '') for m in resp.json().get('models', [])]
            target = self.config.model.split(':')[0]
            loaded = any(target in m for m in models)
            detail = (
                f'Modelo {self.config.model} listo.' if loaded
                else f'Ollama OK pero modelo {self.config.model} no encontrado. '
                     f'Disponibles: {", ".join(models[:4])}'
            )
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.READY if loaded else ProviderStatus.DEGRADED,
                available=True,
                latency_ms=latency_ms,
                detail=detail,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                available=False,
                latency_ms=latency_ms,
                detail=str(exc),
            )

    def _run(self, request: InferenceRequest, *, response_mode: str) -> InferenceResult:
        if httpx is None:
            raise ProviderUnavailableError('httpx no instalado.')

        params = _MODE_PARAMS.get(response_mode, _MODE_PARAMS['user_answer']).copy()
        if getattr(request, 'deep_reasoning', False):
            params = _MODE_PARAMS['deep_reasoning'].copy()

        system_text = (
            request.metadata.get('system_prompt_override')
            or _SYSTEM_PROMPTS.get(response_mode, _SYSTEM_PROMPTS['user_answer'])
        )
        user_text = self._build_user_content(request)
        model_name = request.metadata.get('override_model') or self.config.model

        messages = [
            {'role': 'system', 'content': system_text},
            {'role': 'user', 'content': user_text},
        ]
        history = request.metadata.get('conversation_context') or []
        for msg in (history[-4:] if isinstance(history, list) else []):
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                messages.append({'role': str(msg['role']), 'content': str(msg['content'])[:800]})

        payload = {
            'model': model_name,
            'messages': messages,
            'stream': False,
            'options': params,
        }

        timeout = httpx.Timeout(connect=5.0, read=self.timeout_seconds, write=10.0, pool=5.0)
        url = f'{self._base_url}/api/chat'

        try:
            summary = self._post(url, payload, timeout)
        except Exception as exc_1:
            payload_small = {
                **payload,
                'messages': [
                    {'role': 'system', 'content': system_text[:600]},
                    {'role': 'user', 'content': user_text[:1500]},
                ],
                'options': {**params, 'num_predict': min(params.get('num_predict', 2048), 512)},
            }
            try:
                summary = self._post(url, payload_small, timeout)
            except Exception as exc_2:
                raise ProviderUnavailableError(
                    f'Ollama no respondió. Intento 1: {exc_1}. Intento 2: {exc_2}'
                ) from exc_2

        return InferenceResult(
            request_id=request.request_id,
            provider_name=self.name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.72,
            executor_model=model_name,
            raw_output={'response_mode': response_mode, 'options': params},
        )

    @staticmethod
    def _post(url: str, payload: dict[str, Any], timeout: Any) -> str:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data['message']['content'].strip()
        except (KeyError, TypeError) as exc:
            raise ProviderUnavailableError(
                f'Respuesta inesperada de Ollama: {exc}. Raw: {str(data)[:200]}'
            ) from exc

    @staticmethod
    def _build_user_content(request: InferenceRequest) -> str:
        tools = ', '.join(t.value for t in request.allowed_tools) or 'ninguna'
        return (
            f'Objetivo: {request.user_goal}\n'
            f'Mensaje: {request.prompt}\n'
            f'Rol: {request.task_role.value}\n'
            f'Complejidad: {request.complexity.value}\n'
            f'Herramientas: {tools}'
        )
