from __future__ import annotations

from dataclasses import dataclass

from iabv_v15.domain.models import ToolCard, ToolType
from iabv_v15.services.capture.universal_perception_service import UniversalPerceptionService


@dataclass
class _FakeRegistry:
    card: ToolCard

    def get_card(self, tool_id: str) -> ToolCard | None:
        return self.card if tool_id == self.card.tool_id else None

    def list_cards(self) -> list[ToolCard]:
        return [self.card]

    def refresh_card(self, card: ToolCard) -> ToolCard:
        return card


def test_universal_perception_service_builds_browser_signal() -> None:
    service = UniversalPerceptionService()

    signal = service.build_signal(
        replay_summary={
            'visual_summary': {'green_count': 3, 'orange_count': 1, 'red_count': 0},
            'learning_readiness': {'status': 'ready'},
            'cross_check_summary': {'status': 'aligned'},
            'metadata': {
                'latest_url': 'https://example.com/chat',
                'latest_title': 'Chat especial',
                'dom_available': True,
                'visible_targets': ['chat input', 'send button'],
                'visual_evidence_refs': ['episode:1'],
            },
        },
        session_health={'status': 'active'},
        lane_summary={'total': 1},
        runtime_signals=[{'signal_kind': 'bridge_lag'}],
        site_id='example',
    )

    assert signal.source_app == 'example'
    assert signal.visual_snapshot['status'] == 'available'
    assert signal.dom_summary['status'] == 'available'
    assert signal.available_actions
    assert signal.confidence > 0.5


def test_web_page_signal_detects_chatgpt_login_and_input_without_response() -> None:
    service = UniversalPerceptionService()

    signal = service.build_web_page_signal(
        assistant_kind='chatgpt',
        requested_target='chatgpt',
        dom_observation={
            'source': 'cdp',
            'url': 'https://chatgpt.com/',
            'title': 'ChatGPT',
            'body_text': (
                'Obtén respuestas adaptadas a ti. Inicia sesión para obtener '
                'respuestas basadas en chats guardados. Iniciar sesión. '
                '¿En qué estás trabajando?'
            ),
            'interactive_elements': [
                {'tag': 'button', 'text': 'Iniciar sesión', 'visible': True},
                {'tag': 'textarea', 'placeholder': 'Pregunta lo que quieras', 'visible': True},
                {'tag': 'button', 'text': 'Voz', 'visible': True},
            ],
            'metadata': {'cdp_url': 'http://127.0.0.1:9223'},
        },
    )

    concepts = signal.metadata['visual_concepts']
    assert 'target_bound' in concepts
    assert 'login_screen_candidate' in concepts
    assert 'unauthenticated_session' in concepts
    assert 'chat_input_ready' in concepts
    assert 'submit_control_missing' in concepts
    assert 'response_captured' not in concepts
    assert 'UNRESOLVED:login_or_session_required' in signal.unresolved_fields
    assert 'UNRESOLVED:submit_control_not_observed' in signal.unresolved_fields
    assert 'UNRESOLVED:response_not_captured' in signal.unresolved_fields
    assert signal.dom_summary['semantic_sources'] == ['dom', 'cdp']
    assert any(action['action'] == 'discover_submit_control' for action in signal.available_actions)


def test_web_page_signal_accepts_live_cdp_alias_fields() -> None:
    service = UniversalPerceptionService()

    signal = service.build_web_page_signal(
        assistant_kind='chatgpt',
        requested_target='chatgpt',
        dom_observation={
            'sources': ['dom', 'cdp'],
            'html_flags': {'title': 'ChatGPT', 'url': 'https://chatgpt.com/'},
            'visible_text': (
                'Obtén respuestas adaptadas a ti. Inicia sesión para obtener respuestas '
                'basadas en chats guardados. Iniciar sesión. ¿Qué toca hoy?'
            ),
            'controls': [
                {'tag': 'BUTTON', 'text': 'Iniciar sesión', 'visible': True},
                {'tag': 'BUTTON', 'aria': 'Selector de modelo', 'text': 'ChatGPT', 'visible': True},
                {'tag': 'TEXTAREA', 'placeholder': 'Pregunta lo que quieras', 'visible': True},
                {'tag': 'BUTTON', 'text': 'Voz', 'visible': True},
            ],
        },
    )

    concepts = signal.metadata['visual_concepts']
    assert signal.dom_available is True
    assert signal.dom_summary['semantic_sources'] == ['dom', 'cdp']
    assert 'target_bound' in concepts
    assert 'login_screen_candidate' in concepts
    assert 'unauthenticated_session' in concepts
    assert 'chat_input_ready' in concepts
    assert 'submit_control_missing' in concepts
    assert 'low_information_capture' not in concepts
    assert 'UNRESOLVED:login_or_session_required' in signal.unresolved_fields


def test_web_page_signal_detects_security_verification_as_concept() -> None:
    service = UniversalPerceptionService()

    signal = service.build_web_page_signal(
        assistant_kind='chatgpt',
        requested_target='chatgpt',
        dom_observation={
            'url': 'https://chatgpt.com/',
            'title': 'Just a moment...',
            'body_text': 'Performing security verification. Verify you are not a bot. Ray ID: abc.',
            'interactive_elements': [],
        },
    )

    assert 'security_verification_candidate' in signal.metadata['visual_concepts']
    assert 'security_verification' in signal.detected_blocks
    assert 'UNRESOLVED:security_verification_required' in signal.unresolved_fields
    assert any(action['action'] == 'request_human_security_verification' for action in signal.available_actions)


def test_build_capture_signal_accepts_web_dom_observation() -> None:
    service = UniversalPerceptionService()

    signal = service.build_capture_signal(
        replay_summary={
            'metadata': {
                'assistant_kind': 'chatgpt',
                'web_dom_observation': {
                    'url': 'https://chatgpt.com/',
                    'title': 'ChatGPT',
                    'body_text': 'S',
                    'interactive_elements': [],
                    'metadata': {'response_captured': True, 'captured_text': 'S'},
                },
            },
        }
    )

    assert signal.source == 'web_page_observation'
    assert 'response_captured' in signal.metadata['visual_concepts']
    assert signal.cross_check_status == 'grounded'


def test_universal_perception_service_scans_codex_local_without_dom() -> None:
    registry = _FakeRegistry(
        ToolCard(
            tool_id='codex_installed',
            title='Codex instalado',
            tool_type=ToolType.CUSTOM,
            description='Codex local',
            adapter_key='external_assistant',
            available=True,
            capabilities=['launch_app', 'llm_query', 'consult_external', 'code_assistance'],
            metadata={
                'assistant_kind': 'codex',
                'launch_mode': 'desktop_app',
                'command_name': 'codex',
                'command_aliases': ['codex.exe'],
                'window_title_hints': ['Codex'],
            },
        )
    )
    service = UniversalPerceptionService(tool_registry=registry)
    service._list_windows = lambda: [{'title': 'Codex - Proyecto', 'pid': 4120}]  # type: ignore[method-assign]
    service._list_process_rows = lambda: [{'image_name': 'codex.exe', 'pid': 4120, 'window_title': 'Codex - Proyecto'}]  # type: ignore[method-assign]

    signal = service.scan_codex_local()

    assert signal.source_app == 'codex'
    assert signal.latest_title == 'Codex - Proyecto'
    assert signal.dom_summary['status'] == 'no_disponible'
    assert signal.visual_snapshot['window_visible'] is True
    assert any(action['action'] == 'llm_query' for action in signal.available_actions)
    assert signal.confidence > 0.6


def test_universal_perception_service_reuses_desktop_snapshot_across_tool_probes() -> None:
    registry = _FakeRegistry(
        ToolCard(
            tool_id='codex_installed',
            title='Codex instalado',
            tool_type=ToolType.CUSTOM,
            description='Codex local',
            adapter_key='external_assistant',
            available=True,
            capabilities=['launch_app', 'llm_query'],
            metadata={
                'assistant_kind': 'codex',
                'launch_mode': 'desktop_app',
                'command_name': 'codex',
                'window_title_hints': ['Codex'],
            },
        )
    )
    service = UniversalPerceptionService(tool_registry=registry)
    counters = {'windows': 0, 'processes': 0}

    def _windows() -> list[dict[str, object]]:
        counters['windows'] += 1
        return [{'title': 'Codex - Proyecto', 'pid': 4120}]

    def _processes() -> list[dict[str, object]]:
        counters['processes'] += 1
        return [{'image_name': 'codex.exe', 'pid': 4120, 'window_title': 'Codex - Proyecto'}]

    service._list_windows = _windows  # type: ignore[method-assign]
    service._list_process_rows = _processes  # type: ignore[method-assign]

    first = service.scan_codex_local()
    second = service.scan_codex_local()

    assert first.latest_title == 'Codex - Proyecto'
    assert second.latest_title == 'Codex - Proyecto'
    assert counters == {'windows': 1, 'processes': 1}
