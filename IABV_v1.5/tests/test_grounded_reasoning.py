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
