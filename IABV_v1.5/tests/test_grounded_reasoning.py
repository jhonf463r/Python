"""Tests for grounded metacognition reasoning — startup routing, timeline
data in responses, and enriched LLM context.

Covers:
- _is_self_examination_question routes startup questions
- _self_examination_focus returns 'startup' for startup messages
- _startup_timeline_summary reads real timeline events
- _self_examination_reply 'startup' focus includes timeline data
- SystemPromptBuilder._startup_timeline_section produces timeline block
- SystemPromptBuilder._section_self_examination includes timeline + metadata
- _self_examination_conversation_payload includes timeline + brief
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
from iabv_v15.services.llm.system_prompt_builder import SystemPromptBuilder
from iabv_v15.infra.startup_timeline import StartupTimeline, get_global_timeline


# ── Helpers ──────────────────────────────────────────────────

class _MinimalVM:
    """Bare minimum to call class/static methods on ControlCenterViewModel."""
    _is_self_examination_question = ControlCenterViewModel._is_self_examination_question
    _self_examination_focus = ControlCenterViewModel._self_examination_focus
    _startup_timeline_summary = staticmethod(ControlCenterViewModel._startup_timeline_summary)
    _finding_metrics_suffix = staticmethod(ControlCenterViewModel._finding_metrics_suffix)

    def _normalized_command_text(self, message: str) -> str:
        return ' '.join(message.lower().strip().split())


def _vm() -> _MinimalVM:
    return _MinimalVM()


def _inject_timeline_events(events: list[dict[str, Any]]) -> StartupTimeline:
    """Populate the global timeline with synthetic events."""
    tl = get_global_timeline()
    tl.reset()
    tl._events = list(events)
    return tl


@pytest.fixture(autouse=True)
def _reset_timeline():
    """Reset global timeline before and after each test."""
    tl = get_global_timeline()
    tl.reset()
    yield
    tl.reset()


# ── Test: _is_self_examination_question routing ──────────────

class TestStartupRouting:
    """Startup-related questions should be routed to self-examination."""

    @pytest.mark.parametrize('msg', [
        'como fue mi startup',
        'cómo fue mi startup',
        'como fue mi arranque',
        'cómo fue mi arranque',
        'como fue mi inicio',
        'que paso en el startup',
        'qué pasó en el arranque',
        'tiempos de arranque',
        'tiempos de inicio',
        'metricas de startup',
        'auditar autonomia',
        'auditar autonomía',
        'startup timeline',
        'como estuvo el arranque',
    ])
    def test_startup_phrases_route_to_self_exam(self, msg: str) -> None:
        vm = _vm()
        assert vm._is_self_examination_question(msg) is True

    @pytest.mark.parametrize('msg', [
        'hola como estas',
        'quiero abrir wplay',
        'consultar codex',
    ])
    def test_non_startup_does_not_route(self, msg: str) -> None:
        vm = _vm()
        assert vm._is_self_examination_question(msg) is False


# ── Test: _self_examination_focus ────────────────────────────

class TestStartupFocus:
    """Focus should return 'startup' for startup-related messages."""

    @pytest.mark.parametrize('msg,expected', [
        ('como fue mi startup', 'startup'),
        ('como fue mi arranque', 'startup'),
        ('auditar autonomia', 'startup'),
        ('tiempos de inicio', 'startup'),
        ('que esta fallando mas', 'failures'),
        ('que estoy repitiendo mal', 'repetition'),
        ('cambios recomiendas', 'adjustments'),
        ('examinate', 'general'),
    ])
    def test_focus_detection(self, msg: str, expected: str) -> None:
        vm = _vm()
        assert vm._self_examination_focus(msg) == expected


# ── Test: _startup_timeline_summary ──────────────────────────

class TestStartupTimelineSummary:
    """The summary should include real timeline data."""

    def test_empty_timeline_returns_empty(self) -> None:
        _inject_timeline_events([])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert result == ''

    def test_no_diagnostic_phases_returns_empty(self) -> None:
        _inject_timeline_events([
            {'phase': 'window_activeChanged', 't_ms_from_start': 100, 'rss_mb': 200},
        ])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert result == ''

    def test_includes_diagnostic_phases(self) -> None:
        _inject_timeline_events([
            {'phase': 'page_loader_ready', 't_ms_from_start': 7768.6, 'rss_mb': 327.9},
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 7793.5, 'rss_mb': 333.9},
            {'phase': 'dashboard_vm_refresh_done', 't_ms_from_start': 8067.7, 'rss_mb': 365.7},
        ])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert 'page_loader_ready: 7769ms' in result
        assert 'dashboard_vm_refresh_start: 7794ms' in result
        assert 'dashboard_vm_refresh_done: 8068ms' in result

    def test_includes_refresh_duration(self) -> None:
        _inject_timeline_events([
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 7793.5, 'rss_mb': 333.9},
            {'phase': 'dashboard_vm_refresh_done', 't_ms_from_start': 8067.7, 'rss_mb': 365.7},
        ])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert 'Dashboard refresh duration: 274ms' in result

    def test_includes_refresh_failed(self) -> None:
        _inject_timeline_events([
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 7793.5, 'rss_mb': 333.9},
            {'phase': 'dashboard_vm_refresh_failed', 't_ms_from_start': 8000.0, 'rss_mb': 350.0},
        ])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert 'FAILED' in result

    def test_includes_total_time_and_rss(self) -> None:
        _inject_timeline_events([
            {'phase': 'bootstrap_init_start', 't_ms_from_start': 0, 'rss_mb': 100},
            {'phase': 'page_loader_ready', 't_ms_from_start': 7768.6, 'rss_mb': 327.9},
        ])
        result = ControlCenterViewModel._startup_timeline_summary()
        assert 'Tiempo total de startup: 7769ms' in result
        assert 'RSS: 100MB -> 328MB' in result


# ── Test: SystemPromptBuilder._startup_timeline_section ──────

class TestPromptBuilderTimelineSection:
    """The builder should include timeline data for the LLM."""

    def test_empty_timeline_returns_empty(self) -> None:
        _inject_timeline_events([])
        result = SystemPromptBuilder._startup_timeline_section()
        assert result == ''

    def test_includes_phases(self) -> None:
        _inject_timeline_events([
            {'phase': 'page_loader_ready', 't_ms_from_start': 6181.2, 'rss_mb': 322.1},
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 6274.9, 'rss_mb': 340.5},
            {'phase': 'dashboard_vm_refresh_done', 't_ms_from_start': 7882.3, 'rss_mb': 562.2},
        ])
        result = SystemPromptBuilder._startup_timeline_section()
        assert 'page_loader_ready: 6181ms' in result
        assert 'dashboard_vm_refresh_start: 6275ms' in result
        assert 'dashboard_vm_refresh_done: 7882ms' in result


# ── Test: SystemPromptBuilder._section_self_examination enrichment ──

class TestSectionSelfExaminationEnriched:
    """Findings should include full metadata, not truncated."""

    def test_metadata_fields_surfaced(self) -> None:
        from iabv_v15.domain.models import SelfExaminationFinding, SelfExaminationSnapshot
        finding = SelfExaminationFinding(
            title='Bootstrap init lento',
            summary='El bootstrap tardo mas de lo esperado',
            severity='high',
            confidence=0.9,
            recommendation='Optimizar lazy loading',
            metadata={
                'observed_ms': 4500,
                'threshold_ms': 3000,
                'rss_delta_mb': 38.5,
            },
        )
        snapshot = SelfExaminationSnapshot(
            review_id='test-001',
            package_version='1.5',
            summary='Test summary',
            status='completed',
            findings=[finding],
        )
        _inject_timeline_events([])
        result = SystemPromptBuilder._section_self_examination(snapshot)
        assert 'observed_ms=4500' in result
        assert 'threshold_ms=3000' in result
        assert 'rss_delta_mb=38.5' in result
        assert '4500ms' in result  # metrics_tag
        assert 'umbral 3000ms' in result  # metrics_tag

    def test_recommendation_not_heavily_truncated(self) -> None:
        from iabv_v15.domain.models import SelfExaminationFinding, SelfExaminationSnapshot
        long_rec = 'Optimizar el servicio de embedding para no cargar todos los indices al inicio, usar lazy loading con TTL de 60 segundos para cada indice independiente'
        finding = SelfExaminationFinding(
            title='test',
            summary='test',
            severity='medium',
            confidence=0.5,
            recommendation=long_rec,
            metadata={},
        )
        snapshot = SelfExaminationSnapshot(
            review_id='test-002',
            package_version='1.5',
            summary='Test',
            status='completed',
            findings=[finding],
        )
        _inject_timeline_events([])
        result = SystemPromptBuilder._section_self_examination(snapshot)
        # Recommendation should be up to 200 chars, not 100
        assert 'lazy loading' in result

    def test_timeline_included_when_available(self) -> None:
        from iabv_v15.domain.models import SelfExaminationSnapshot
        _inject_timeline_events([
            {'phase': 'page_loader_ready', 't_ms_from_start': 5952.4, 'rss_mb': 324.4},
        ])
        snapshot = SelfExaminationSnapshot(
            review_id='test-003',
            package_version='1.5',
            summary='Test',
            status='completed',
            findings=[],
        )
        result = SystemPromptBuilder._section_self_examination(snapshot)
        assert 'page_loader_ready: 5952ms' in result


# ── Test: _self_examination_conversation_payload enrichment ──

class TestPayloadEnriched:
    """Payload should include timeline summary and assistant_brief."""

    def test_payload_includes_timeline_and_brief(self) -> None:
        _inject_timeline_events([
            {'phase': 'page_loader_ready', 't_ms_from_start': 5952.4, 'rss_mb': 324.4},
        ])

        class _PayloadVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []
            def _current_self_examination_snapshot(self) -> dict[str, Any]:
                return {
                    'assistant_brief': 'Test brief with numbers 274ms',
                    'recurring_issues': [],
                }
            def _update_adaptive_state(self, payload: Any) -> None:
                pass
            _self_examination_conversation_payload = ControlCenterViewModel._self_examination_conversation_payload

        vm = _PayloadVM()
        payload = vm._self_examination_conversation_payload(message='como fue mi startup')
        meta = payload['metadata']['decision_context']['metadata']
        assert 'page_loader_ready' in meta['startup_timeline_summary']
        assert '274ms' in meta['assistant_brief']

    def test_payload_includes_llm_grounded_flag(self) -> None:
        _inject_timeline_events([])

        class _PayloadVM2(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = [
                    {'role': 'user', 'text': 'hola'},
                    {'role': 'assistant', 'text': 'respuesta'},
                ]
            def _current_self_examination_snapshot(self) -> dict[str, Any]:
                return {'recurring_issues': []}
            def _update_adaptive_state(self, payload: Any) -> None:
                pass
            _self_examination_conversation_payload = ControlCenterViewModel._self_examination_conversation_payload

        vm = _PayloadVM2()
        payload = vm._self_examination_conversation_payload(message='como fue mi startup')
        meta = payload['metadata']['decision_context']['metadata']
        assert meta['llm_grounded_reasoning'] is True
        assert meta['conversation_flow_turns'] == 2


# ── Test: _extract_grounding_anchors ─────────────────────────

class TestExtractGroundingAnchors:
    """Anchors should capture numeric data points from context."""

    def test_extracts_ms_values(self) -> None:
        context = 'page_loader_ready: 7769ms (RSS 328MB)\ndashboard_vm_refresh_done: 8068ms'
        anchors = ControlCenterViewModel._extract_grounding_anchors(context)
        assert '7769ms' in anchors
        assert '8068ms' in anchors

    def test_extracts_mb_values(self) -> None:
        context = 'RSS: 100MB -> 328MB'
        anchors = ControlCenterViewModel._extract_grounding_anchors(context)
        assert '100MB' in anchors
        assert '328MB' in anchors

    def test_ignores_small_ms_values(self) -> None:
        context = 'some_phase: 50ms (RSS 328MB)'
        anchors = ControlCenterViewModel._extract_grounding_anchors(context)
        assert '50ms' not in anchors
        assert '328MB' in anchors

    def test_extracts_recurrence_counts(self) -> None:
        context = 'patron repetido (x5)\notro patron (x12)'
        anchors = ControlCenterViewModel._extract_grounding_anchors(context)
        assert 'x5' in anchors
        assert 'x12' in anchors

    def test_empty_context_returns_empty(self) -> None:
        assert ControlCenterViewModel._extract_grounding_anchors('') == []

    def test_max_anchors_capped(self) -> None:
        context = '\n'.join(f'phase_{i}: {1000 + i}ms' for i in range(30))
        anchors = ControlCenterViewModel._extract_grounding_anchors(context)
        assert len(anchors) <= 20


# ── Test: _validate_response_grounding ───────────────────────

class TestValidateResponseGrounding:
    """Response should be validated against available data points."""

    def test_grounded_when_response_contains_anchors(self) -> None:
        anchors = ['7769ms', '8068ms', '328MB']
        response = 'page_loader_ready tardo 7769ms, dashboard refresh termino en 8068ms con 328MB de RSS'
        is_grounded, missing = ControlCenterViewModel._validate_response_grounding(response, anchors)
        assert is_grounded is True
        assert missing == []

    def test_not_grounded_when_generic(self) -> None:
        anchors = ['7769ms', '8068ms', '328MB']
        response = 'El startup fue normal sin problemas detectados.'
        is_grounded, missing = ControlCenterViewModel._validate_response_grounding(response, anchors)
        assert is_grounded is False
        assert len(missing) == 3

    def test_partially_grounded_above_threshold(self) -> None:
        anchors = ['7769ms', '8068ms', '328MB', '100MB', '274ms']
        response = 'El refresh tardo 274ms y page_loader estuvo en 7769ms'
        is_grounded, missing = ControlCenterViewModel._validate_response_grounding(response, anchors)
        assert is_grounded is True

    def test_partially_grounded_below_threshold(self) -> None:
        anchors = ['7769ms', '8068ms', '328MB', '100MB', '274ms']
        response = 'Solo se un dato: 274ms.'
        is_grounded, missing = ControlCenterViewModel._validate_response_grounding(response, anchors)
        assert is_grounded is False

    def test_empty_anchors_always_grounded(self) -> None:
        is_grounded, missing = ControlCenterViewModel._validate_response_grounding('cualquier cosa', [])
        assert is_grounded is True
        assert missing == []


# ── Test: _build_metacognition_context ───────────────────────

class TestBuildMetacognitionContext:
    """Full panorama context should include all data sources."""

    def test_includes_timeline_data(self) -> None:
        _inject_timeline_events([
            {'phase': 'page_loader_ready', 't_ms_from_start': 7768.6, 'rss_mb': 327.9},
            {'phase': 'dashboard_vm_refresh_start', 't_ms_from_start': 7793.5, 'rss_mb': 333.9},
            {'phase': 'dashboard_vm_refresh_done', 't_ms_from_start': 8067.7, 'rss_mb': 365.7},
        ])

        class _ContextVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []
            def _current_self_examination_snapshot(self) -> dict[str, Any]:
                return {
                    'top_findings': [
                        {
                            'title': 'Dashboard refresh lento',
                            'summary': 'El refresh tardo mas de lo esperado',
                            'recommendation': 'Usar lazy loading',
                            'metadata': {'observed_ms': 274, 'threshold_ms': 5000},
                        }
                    ],
                    'recurring_issues': [{'title': 'HTTP noise', 'count': 145}],
                    'recommended_adjustments': [{'recommended_change': 'Suprimir logs HTTP'}],
                }
            def _current_environment_self_model(self):
                raise RuntimeError('not available in test')
            def _current_world_model(self):
                raise RuntimeError('not available in test')
            _build_metacognition_context = ControlCenterViewModel._build_metacognition_context

        vm = _ContextVM()
        if not hasattr(vm, 'experiment_lab_repository'):
            vm.experiment_lab_repository = None
        ctx = vm._build_metacognition_context('como fue mi startup', 'startup')

        assert 'page_loader_ready' in ctx
        assert '7769ms' in ctx or '7768' in ctx
        assert 'Dashboard refresh lento' in ctx
        assert '274ms' in ctx
        assert 'HTTP noise' in ctx
        assert 'x145' in ctx
        assert 'Suprimir logs HTTP' in ctx

    def test_includes_oses_metadata(self) -> None:
        _inject_timeline_events([])

        class _ContextVM2(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []
            def _current_self_examination_snapshot(self) -> dict[str, Any]:
                return {
                    'top_findings': [{
                        'title': 'Test finding',
                        'summary': 'Summary',
                        'recommendation': '',
                        'metadata': {
                            'observed_ms': 4500,
                            'threshold_ms': 3000,
                            'rss_delta_mb': 120.5,
                        },
                    }],
                }
            def _current_environment_self_model(self):
                raise RuntimeError('skip')
            def _current_world_model(self):
                raise RuntimeError('skip')
            _build_metacognition_context = ControlCenterViewModel._build_metacognition_context

        vm = _ContextVM2()
        vm.experiment_lab_repository = None
        ctx = vm._build_metacognition_context('examinate', 'general')
        assert 'observed_ms=4500' in ctx
        assert 'threshold_ms=3000' in ctx
        assert 'rss_delta_mb=120.5' in ctx

    def test_includes_chat_flow(self) -> None:
        _inject_timeline_events([])

        class _ContextVM3(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = [
                    {'role': 'user', 'text': 'como fue mi startup', 'evidenceTag': ''},
                    {'role': 'assistant', 'text': 'Fue normal', 'evidenceTag': 'unresolved'},
                ]
            def _current_self_examination_snapshot(self) -> dict[str, Any]:
                return {}
            def _current_environment_self_model(self):
                raise RuntimeError('skip')
            def _current_world_model(self):
                raise RuntimeError('skip')
            _build_metacognition_context = ControlCenterViewModel._build_metacognition_context

        vm = _ContextVM3()
        vm.experiment_lab_repository = None
        ctx = vm._build_metacognition_context('profundiza', 'general')
        assert 'Flujo de la conversacion reciente' in ctx
        assert 'como fue mi startup' in ctx
        assert 'Fue normal' in ctx


# ── Test: _invoke_llm_for_self_examination ───────────────────

class TestInvokeLLMForSelfExamination:
    """LLM invocation should handle provider unavailability gracefully."""

    def test_returns_none_when_no_provider(self) -> None:
        class _NoProviderVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []

            class role_router:
                general_provider = None

            _invoke_llm_for_self_examination = ControlCenterViewModel._invoke_llm_for_self_examination
            _conversation_context = ControlCenterViewModel._conversation_context

        vm = _NoProviderVM()
        result = vm._invoke_llm_for_self_examination('test', 'context', 'general')
        assert result is None

    def test_returns_none_when_health_check_fails(self) -> None:
        class _FailingProvider:
            def health_check(self):
                raise ConnectionError('Ollama not running')

        class _FailVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []

            class role_router:
                general_provider = _FailingProvider()

            _invoke_llm_for_self_examination = ControlCenterViewModel._invoke_llm_for_self_examination
            _conversation_context = ControlCenterViewModel._conversation_context

        vm = _FailVM()
        result = vm._invoke_llm_for_self_examination('test', 'context', 'startup')
        assert result is None

    def test_returns_none_when_provider_unavailable(self) -> None:
        class _UnavailableHealth:
            available = False

        class _UnavailableProvider:
            def health_check(self):
                return _UnavailableHealth()

        class _UnavailableVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = []

            class role_router:
                general_provider = _UnavailableProvider()

            _invoke_llm_for_self_examination = ControlCenterViewModel._invoke_llm_for_self_examination
            _conversation_context = ControlCenterViewModel._conversation_context

        vm = _UnavailableVM()
        result = vm._invoke_llm_for_self_examination('test', 'context', 'failures')
        assert result is None


# ── Test: _conversation_context enrichment ───────────────────

class TestConversationContextEnriched:
    """Conversation context should include evidence_tag for each message."""

    def test_includes_evidence_tag_from_messages(self) -> None:
        class _ChatVM(_MinimalVM):
            def __init__(self):
                super().__init__()
                self._chat_messages: list[dict[str, Any]] = [
                    {'role': 'user', 'text': 'pregunta'},
                    {'role': 'assistant', 'text': 'respuesta', 'evidenceTag': 'observed'},
                    {'role': 'user', 'text': 'otra pregunta'},
                    {'role': 'assistant', 'text': 'sin datos', 'evidenceTag': 'unresolved'},
                ]
            _conversation_context = ControlCenterViewModel._conversation_context

        vm = _ChatVM()
        ctx = vm._conversation_context()
        assert len(ctx) == 4
        assert 'evidence_tag' not in ctx[0]
        assert ctx[1]['evidence_tag'] == 'observed'
        assert 'evidence_tag' not in ctx[2]
        assert ctx[3]['evidence_tag'] == 'unresolved'


# ── Test: SystemPromptBuilder meta-cognition enrichment ──────

class TestMetaCognitionPromptEnriched:
    """System prompt should include conversational awareness and auto-validation rules."""

    def test_includes_conversational_awareness(self) -> None:
        prompt = SystemPromptBuilder._section_meta_cognition()
        assert 'flujo conversacional' in prompt
        assert 'turnos anteriores' in prompt

    def test_includes_auto_validation(self) -> None:
        prompt = SystemPromptBuilder._section_meta_cognition()
        assert 'Auto-validacion' in prompt
        assert 'dato numerico concreto' in prompt
