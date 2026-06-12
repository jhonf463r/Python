"""OllamaExpertProvider: integración nativa Ollama con comportamiento experto.

Usa /api/chat (endpoint nativo) en vez de /v1/chat/completions.
Parámetros ajustados por tipo de tarea. Retry con contexto reducido y timeout escalonado.
Compatible con qwen3:8b, llama3.x, deepseek-coder y otros modelos Ollama.

METACOGNICIÓN AUTOMÁTICA:
- Timeout escalonado: 30s primer intento, 15s retry (evita congelamiento)
- Detección temprana de disponibilidad antes de inferencias largas
- Manejo específico de excepciones httpx (timeout vs error real)
- Health check consistente con timeouts de inferencia
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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
        timeout_seconds: float = 30.0,  # REDUCIDO: 90s era excesivo, causaba congelamiento
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._quick_timeout = min(timeout_seconds / 2, 15.0)  # Timeout para retry
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
        """Health check con timeout consistente y detección temprana."""
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
            # Timeout consistente: 5s para health check (rápido pero suficiente)
            timeout = httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0)
            with httpx.Client(timeout=timeout) as client:
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
        except httpx.TimeoutException as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning('Ollama health check timeout: %s', exc)
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                available=False,
                latency_ms=latency_ms,
                detail=f'Timeout: {exc}',
            )
        except httpx.ConnectError as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning('Ollama no responde (conexión rechazada): %s', exc)
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.UNAVAILABLE,
                available=False,
                latency_ms=latency_ms,
                detail=f'Ollama no está corriendo: {exc}',
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning('Ollama health check error: %s', exc)
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                available=False,
                latency_ms=latency_ms,
                detail=str(exc),
            )

    def _run(self, request: InferenceRequest, *, response_mode: str) -> InferenceResult:
        """Ejecuta inferencia con timeout escalonado y manejo específico de errores."""
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

        # Timeout escalonado: primer intento con timeout completo, retry con timeout reducido
        timeout_full = httpx.Timeout(connect=5.0, read=self.timeout_seconds, write=10.0, pool=5.0)
        timeout_quick = httpx.Timeout(connect=3.0, read=self._quick_timeout, write=5.0, pool=3.0)
        url = f'{self._base_url}/api/chat'

        try:
            summary = self._post(url, payload, timeout_full)
        except httpx.TimeoutException as exc_1:
            logger.warning('Ollama timeout primer intento (%s), retry con timeout reducido...', exc_1)
            payload_small = {
                **payload,
                'messages': [
                    {'role': 'system', 'content': system_text[:600]},
                    {'role': 'user', 'content': user_text[:1500]},
                ],
                'options': {**params, 'num_predict': min(params.get('num_predict', 2048), 512)},
            }
            try:
                summary = self._post(url, payload_small, timeout_quick)
            except httpx.TimeoutException as exc_2:
                logger.error('Ollama timeout en retry también: %s', exc_2)
                raise ProviderUnavailableError(
                    f'Ollama no respondió en tiempo útil. '
                    f'Timeout primer intento: {exc_1}. Retry: {exc_2}'
                ) from exc_2
            except Exception as exc_2:
                logger.error('Ollama error en retry: %s', exc_2)
                raise ProviderUnavailableError(
                    f'Ollama falló en retry después de timeout. '
                    f'Primer timeout: {exc_1}. Error retry: {exc_2}'
                ) from exc_2
        except httpx.ConnectError as exc_1:
            logger.error('Ollama no accesible (conexión rechazada): %s', exc_1)
            raise ProviderUnavailableError(
                f'Ollama no está corriendo o no es accesible: {exc_1}'
            ) from exc_1
        except Exception as exc_1:
            logger.warning('Ollama error primer intento: %s, retry con contexto reducido...', exc_1)
            payload_small = {
                **payload,
                'messages': [
                    {'role': 'system', 'content': system_text[:600]},
                    {'role': 'user', 'content': user_text[:1500]},
                ],
                'options': {**params, 'num_predict': min(params.get('num_predict', 2048), 512)},
            }
            try:
                summary = self._post(url, payload_small, timeout_quick)
            except Exception as exc_2:
                logger.error('Ollama error en retry también: %s', exc_2)
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
        """Ejecuta POST con manejo específico de errores HTTP."""
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error('Ollama HTTP error %s: %s', exc.response.status_code, exc)
            raise ProviderUnavailableError(
                f'Ollama respondió con error HTTP {exc.response.status_code}: {exc}'
            ) from exc
        except httpx.TimeoutException as exc:
            logger.warning('Ollama timeout en POST: %s', exc)
            raise  # Re-lanzar para manejo específico en _run
        except httpx.ConnectError as exc:
            logger.error('Ollama conexión rechazada en POST: %s', exc)
            raise  # Re-lanzar para manejo específico en _run
        except Exception as exc:
            logger.error('Ollama error inesperado en POST: %s', exc)
            raise ProviderUnavailableError(
                f'Error inesperado comunicando con Ollama: {exc}'
            ) from exc

        try:
            return data['message']['content'].strip()
        except (KeyError, TypeError) as exc:
            logger.error('Ollama respuesta mal formada: %s. Raw: %s', exc, str(data)[:200])
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
