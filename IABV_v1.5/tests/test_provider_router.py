from __future__ import annotations

from iabv_v15.domain.models import (
    AmbiguityLevel,
    ComplexityLevel,
    InferenceRequest,
    InferenceResult,
    ProviderHealth,
    ProviderStatus,
    ReasoningMode,
)
from iabv_v15.services.providers.base import LLMProvider
from iabv_v15.services.providers.provider_router import ProviderRouter


class FakeProvider(LLMProvider):
    def __init__(self, name: str, mode: ReasoningMode, fail: bool = False):
        self._name = name
        self.mode = mode
        self.fail = fail

    @property
    def name(self) -> str:
        return self._name

    def analyze_ui(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def infer_task(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def answer_user(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def summarize_session(self, request: InferenceRequest) -> InferenceResult:
        return self._result(request)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_name=self._name, status=ProviderStatus.READY, available=True, detail='ok')

    def _result(self, request: InferenceRequest) -> InferenceResult:
        if self.fail:
            raise RuntimeError(f'{self._name} unavailable')
        return InferenceResult(
            request_id=request.request_id,
            provider_name=self._name,
            reasoning_mode=self.mode,
            summary=f'{self._name} handled the request',
            inferred_task=request.user_goal,
            confidence=0.8,
        )



def _router() -> ProviderRouter:
    return ProviderRouter(
        local_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL),
        fallback_local_provider=FakeProvider('Ollama', ReasoningMode.LOCAL),
        cloud_provider=FakeProvider('OpenAI', ReasoningMode.CLOUD),
    )



def test_simple_request_prefers_local() -> None:
    router = _router()
    request = InferenceRequest(user_goal='Open settings', screenshots=['one.png'])
    route, result = router.infer_task(request)
    assert route.primary_provider == 'LM Studio'
    assert result.provider_name == 'LM Studio'
    assert result.used_fallback is False



def test_raw_browser_teach_bundle_stays_local() -> None:
    router = _router()
    request = InferenceRequest(
        user_goal='Learn this login flow',
        screenshots=['1.png', '2.png'],
        complexity=ComplexityLevel.DEEP,
        ambiguity=AmbiguityLevel.HIGH,
        metadata={
            'browser_teach_mode': True,
            'capture_channels': ['visible', 'background', 'api'],
            'contains_sensitive_data': True,
        },
    )
    route, result = router.infer_task(request)
    assert route.primary_provider == 'LM Studio'
    assert 'Sensitive browser-teach' in route.reason
    assert result.provider_name == 'LM Studio'



def test_complex_request_falls_back_from_cloud_to_local() -> None:
    router = ProviderRouter(
        local_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL),
        fallback_local_provider=FakeProvider('Ollama', ReasoningMode.LOCAL),
        cloud_provider=FakeProvider('OpenAI', ReasoningMode.CLOUD, fail=True),
    )
    request = InferenceRequest(
        user_goal='Understand checkout flow',
        screenshots=['1.png', '2.png'],
        complexity=ComplexityLevel.DEEP,
        ambiguity=AmbiguityLevel.HIGH,
        deep_reasoning=True,
        metadata={'redacted_for_cloud': True},
    )
    route, result = router.infer_task(request)
    assert route.primary_provider == 'OpenAI'
    assert result.provider_name == 'LM Studio'
    assert result.used_fallback is True
    assert result.confidence_reduced is True
    assert result.reasoning_mode == ReasoningMode.DEGRADED



def test_local_failure_uses_fallback_local() -> None:
    router = ProviderRouter(
        local_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL, fail=True),
        fallback_local_provider=FakeProvider('Ollama', ReasoningMode.LOCAL),
        cloud_provider=FakeProvider('OpenAI', ReasoningMode.CLOUD),
    )
    request = InferenceRequest(user_goal='Single-step local task', screenshots=['one.png'])
    route, result = router.infer_task(request)
    assert route.primary_provider == 'LM Studio'
    assert result.provider_name == 'Ollama'
    assert result.used_fallback is True



def test_hybrid_can_escape_to_cloud_when_both_local_providers_are_down() -> None:
    router = ProviderRouter(
        local_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL, fail=True),
        fallback_local_provider=FakeProvider('Ollama', ReasoningMode.LOCAL, fail=True),
        cloud_provider=FakeProvider('OpenAI', ReasoningMode.CLOUD),
    )
    request = InferenceRequest(
        user_goal='Plan the next safe action',
        prompt='Plan the next safe action',
        metadata={'redacted_for_cloud': True},
    )
    route, result = router.infer_task(request)
    assert route.primary_provider == 'LM Studio'
    assert result.provider_name == 'OpenAI'
    assert result.used_fallback is True
    assert result.reasoning_mode == ReasoningMode.CLOUD



def test_hybrid_reports_cloud_and_local_errors_when_everything_fails() -> None:
    router = ProviderRouter(
        local_provider=FakeProvider('LM Studio', ReasoningMode.LOCAL, fail=True),
        fallback_local_provider=FakeProvider('Ollama', ReasoningMode.LOCAL, fail=True),
        cloud_provider=FakeProvider('OpenAI', ReasoningMode.CLOUD, fail=True),
    )
    request = InferenceRequest(
        user_goal='Diagnose providers',
        screenshots=['1.png', '2.png'],
        complexity=ComplexityLevel.DEEP,
        ambiguity=AmbiguityLevel.HIGH,
        deep_reasoning=True,
        metadata={'redacted_for_cloud': True},
    )

    try:
        router.infer_task(request)
    except RuntimeError as exc:
        message = str(exc)
        assert 'OpenAI' in message
        assert 'LM Studio' in message
        assert 'Ollama' in message
    else:
        raise AssertionError('Expected combined provider failure')



def test_publish_health_without_handler_returns_snapshot() -> None:
    router = _router()
    snapshot = router.publish_health()
    assert [h.provider_name for h in snapshot] == ['LM Studio', 'Ollama', 'OpenAI']
    assert all(h.available for h in snapshot)



def test_publish_health_invokes_registered_handler_with_snapshot() -> None:
    router = _router()
    received: list[list[ProviderHealth]] = []

    def handler(payload: list[ProviderHealth]) -> None:
        received.append(payload)

    router.register_health_handler(handler)
    returned = router.publish_health()

    assert len(received) == 1
    assert received[0] == returned
    assert [h.provider_name for h in received[0]] == ['LM Studio', 'Ollama', 'OpenAI']
    assert all(h.status == ProviderStatus.READY for h in received[0])



def test_register_health_handler_none_unregisters_previous_handler() -> None:
    router = _router()
    received: list[list[ProviderHealth]] = []

    router.register_health_handler(received.append)
    router.publish_health()
    assert len(received) == 1

    router.register_health_handler(None)
    router.publish_health()
    assert len(received) == 1  # no new invocations after unregister



def test_publish_health_gives_handler_an_independent_list_copy() -> None:
    router = _router()
    received: list[list[ProviderHealth]] = []
    router.register_health_handler(received.append)

    returned = router.publish_health()
    received[0].clear()

    # Mutating the handler's list must not affect the list returned to the caller.
    assert len(returned) == 3



def test_health_snapshot_does_not_invoke_handler() -> None:
    """health_snapshot sigue siendo pull-only; publish_health es el push."""
    router = _router()
    received: list[list[ProviderHealth]] = []
    router.register_health_handler(received.append)

    router.health_snapshot()

    assert received == []
