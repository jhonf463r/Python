from __future__ import annotations

import time

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


class OpenAICompatLocalProvider(LLMProvider):
    """Provider para runtimes locales compatibles con la API estilo OpenAI."""

    def __init__(self, config: ProviderConfig, timeout_seconds: float = 45.0) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return self.config.name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction=(
                'Eres el analista visual local de IABV v1.5. Describe la interfaz en espanol claro, '
                'sin inventar elementos y destacando solo lo util para la tarea.'
            ),
            user_instruction='Analiza esta interfaz y describe el contexto actual.',
            response_mode='ui_analysis',
        )

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction=(
                'Eres el planificador interno de IABV v1.5. Tu salida es interna para routing. '
                'No respondas como chat al usuario. Resume de forma breve la intencion, el rol probable, '
                'las restricciones y el siguiente paso recomendado sin exponer cadena de pensamiento extensa.'
            ),
            user_instruction='Infiere la tarea del usuario con razonamiento breve y estructurado para uso interno.',
            response_mode='task_inference',
        )

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction=(
                'Eres el asistente local de IABV v1.5. Responde al usuario final en espanol claro, util y directo. '
                'No muestres razonamiento interno, no uses etiquetas como "Tarea inferida", "Razonamiento" o "Objetivo directo", '
                'no uses emojis ni adornos innecesarios, y no expliques el routing salvo que aporte valor practico. '
                'Si faltan datos, dilo de forma breve y orienta el siguiente paso.'
            ),
            user_instruction='Responde al usuario final de forma natural y accionable usando el contexto del rol y las herramientas disponibles.',
            response_mode='user_answer',
        )

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._run(
            request,
            system_instruction=(
                'Eres el sintetizador local de IABV v1.5. Resume la sesion en espanol claro y extrae pistas reutilizables '
                'para automatizacion sin exponer secretos ni razonamiento interno innecesario.'
            ),
            user_instruction='Resume la sesion y extrae pistas utiles para automatizacion.',
            response_mode='session_summary',
        )

    def health_check(self) -> ProviderHealth:
        if not self.config.enabled:
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.UNAVAILABLE, available=False, detail='Proveedor deshabilitado.')
        if httpx is None:
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.DEGRADED, available=False, detail='httpx no esta instalado.')
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(f'{self.config.base_url}/models')
                response.raise_for_status()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ProviderHealth(provider_name=self.name, status=ProviderStatus.READY, available=True, latency_ms=latency_ms, detail='Disponible.')
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if self.config.optional and self._looks_inactive(exc):
                return ProviderHealth(
                    provider_name=self.name,
                    status=ProviderStatus.OPTIONAL_INACTIVE,
                    available=False,
                    latency_ms=latency_ms,
                    detail=f'Componente opcional no activo en {self.config.base_url}.',
                )
            return ProviderHealth(
                provider_name=self.name,
                status=ProviderStatus.DEGRADED,
                available=False,
                latency_ms=latency_ms,
                detail=str(exc),
            )

    def _run(
        self,
        request: InferenceRequest,
        *,
        system_instruction: str,
        user_instruction: str,
        response_mode: str,
    ) -> InferenceResult:
        if httpx is None:
            raise ProviderUnavailableError('httpx no esta instalado.')
        effective_system = self._resolve_system_instruction(request, system_instruction)
        messages: list[dict[str, str]] = [
            {'role': 'system', 'content': effective_system},
            {'role': 'user', 'content': self._build_user_payload(request, user_instruction)},
        ]
        messages.extend(self._conversation_context_messages(request))
        payload = {
            'model': self.config.model,
            'messages': messages,
            'stream': False,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f'{self.config.base_url}/chat/completions', json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            summary = data['choices'][0]['message']['content'].strip()
        except Exception as exc:
            raise ProviderUnavailableError(f'{self.name} devolvio una respuesta inesperada: {exc}') from exc
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self.name,
            reasoning_mode=ReasoningMode.LOCAL,
            summary=summary,
            inferred_task=request.user_goal,
            confidence=0.66 if request.complexity.value == 'simple' else 0.6,
            executor_model=self.config.model,
            raw_output={'response_mode': response_mode, 'provider_payload': data},
        )

    def _build_user_payload(self, request: InferenceRequest, instruction: str) -> str:
        role_label = request.task_role.value.replace('_', ' ')
        tools = ', '.join(tool.value for tool in request.allowed_tools) or 'sin herramientas explicitas'
        knowledge_scope = ', '.join(request.knowledge_scope) or 'sin alcance adicional'
        return (
            f'{instruction}\n\n'
            f'Rol activo: {role_label}\n'
            f'Objetivo: {request.user_goal}\n'
            f'Prompt/contexto: {request.prompt}\n'
            f'Complejidad: {request.complexity.value}\n'
            f'Ambiguedad: {request.ambiguity.value}\n'
            f'Herramientas permitidas: {tools}\n'
            f'Alcance de conocimiento: {knowledge_scope}\n'
            f'Consulta SQL solo lectura: {"si" if request.read_only_sql else "no"}\n'
            f'Capturas: {len(request.screenshots)}\n'
            f'Pasos observados: {len(request.steps)}\n'
            f'Razonamiento visual requerido: {"si" if request.requires_visual_reasoning else "no"}'
        )

    @staticmethod
    def _resolve_system_instruction(request: InferenceRequest, fallback: str) -> str:
        override = request.metadata.get('system_prompt_override')
        if isinstance(override, str) and override.strip():
            return override
        return fallback

    @staticmethod
    def _conversation_context_messages(request: InferenceRequest) -> list[dict[str, str]]:
        extra: list[dict[str, str]] = []
        for item in request.conversation_context:
            if not isinstance(item, dict):
                continue
            role = str(item.get('role') or '').strip()
            content = str(item.get('content') or '').strip()
            if not role or not content:
                continue
            if role not in {'system', 'user', 'assistant', 'tool'}:
                continue
            extra.append({'role': role, 'content': content})
        return extra

    def _looks_inactive(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                '10061',
                'connection refused',
                'actively refused',
                'failed to establish a new connection',
                'connecterror',
            )
        )
