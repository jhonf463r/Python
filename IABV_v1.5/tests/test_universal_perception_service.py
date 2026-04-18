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
