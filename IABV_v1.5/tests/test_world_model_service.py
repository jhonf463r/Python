from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

from iabv_v15.domain.models import (
    BackgroundProcessSnapshot,
    EnvironmentSelfModel,
    IssueSeverity,
    NetworkStatusSnapshot,
    ToolCard,
    ToolLiveStatus,
    ToolType,
    WindowObservation,
)
from iabv_v15.services.evolution.world_model_service import WorldModelService


REPO_ROOT = Path(__file__).resolve().parents[1]


def _workspace(name: str) -> Path:
    base = REPO_ROOT / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_world_model_service_builds_operational_snapshot_with_detected_blocks() -> None:
    workspace = _workspace('world_model_operational')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            environment_id='env-demo',
            scan_status='ready',
            risk_signals=[],
        )
        service._list_windows = lambda: [{'title': 'Codex - IABV', 'pid': 101}]  # type: ignore[method-assign]
        service._focused_window = lambda: WindowObservation(  # type: ignore[method-assign]
            title='Codex - IABV',
            app_name='Codex',
            pid=101,
            focused=True,
            visible=True,
            state='focused',
        )
        service._network_status = lambda *, full: (  # type: ignore[method-assign]
            NetworkStatusSnapshot(
                connected=True,
                status='conectado',
                quality='buena',
                latency_ms=42.0,
                detail='La red responde bien.',
            ),
            [],
        )
        service._tool_live_status = lambda **_: (  # type: ignore[method-assign]
            [
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    available=True,
                    status='abierto',
                    detail='Codex esta abierto, pero el hilo activo no coincide con IABV.',
                    window_open=True,
                    focused=True,
                    thread_status='otro_hilo_activo',
                    messages_status='disponibles',
                    session_status='abierta',
                    capture_status='no_disponible',
                    detected_blocks=['wrong_thread'],
                    confidence=0.86,
                )
            ],
            [],
        )
        service._background_processes = lambda *, full: [  # type: ignore[method-assign]
            BackgroundProcessSnapshot(
                process_name='OneDrive',
                pid=999,
                memory_mb=1024.0,
                state='memory_heavy',
                detail='Consume bastante memoria.',
                interferes_with_capture=True,
            )
        ]

        snapshot = service.scan_now(reason='manual', full=False)

        assert snapshot.focused_window is not None
        assert snapshot.focused_window.title == 'Codex - IABV'
        assert 'wrong_thread' in snapshot.detected_blocks
        assert 'process_interference:onedrive' in snapshot.detected_blocks
        assert any('Codex esta abierto' in item for item in snapshot.inferred_state['deductions'])
        assert snapshot.confidence > 0.4
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_service_marks_network_block_when_probe_fails() -> None:
    workspace = _workspace('world_model_network')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            environment_id='env-demo',
            scan_status='ready',
            risk_signals=[],
        )
        service._list_windows = lambda: []  # type: ignore[method-assign]
        service._focused_window = lambda: None  # type: ignore[method-assign]
        service._tool_live_status = lambda **_: ([], [])  # type: ignore[method-assign]
        service._background_processes = lambda *, full: []  # type: ignore[method-assign]
        service._network_connectivity_probe = lambda: (None, 'timeout while probing')  # type: ignore[method-assign]

        snapshot = service.scan_now(reason='manual', full=False)

        assert snapshot.network_status.status == 'desconectado'
        assert 'network_blocked' in snapshot.detected_blocks
        assert any('conectividad' in item.lower() or 'red' in item.lower() for item in snapshot.inferred_state['deductions'])
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_service_emits_permission_gate_and_route_block_for_codex_probe() -> None:
    workspace = _workspace('world_model_permission_gate')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            environment_id='env-demo',
            scan_status='ready',
            risk_signals=[],
        )
        service._list_windows = lambda: [{'title': 'Codex - IABV', 'pid': 404}]  # type: ignore[method-assign]
        service._focused_window = lambda: WindowObservation(  # type: ignore[method-assign]
            title='Codex - IABV',
            app_name='Codex',
            pid=404,
            focused=True,
            visible=True,
            state='focused',
        )
        service._network_status = lambda *, full: (  # type: ignore[method-assign]
            NetworkStatusSnapshot(
                connected=True,
                status='conectado',
                quality='buena',
                latency_ms=36.0,
                detail='La red responde bien.',
            ),
            [],
        )
        service._tool_live_status = lambda **_: (  # type: ignore[method-assign]
            [
                ToolLiveStatus(
                    tool_id='codex_installed',
                    title='Codex instalado',
                    assistant_kind='codex',
                    available=True,
                    status='abierto',
                    detail='Para verificar si Codex esta listo de verdad necesito observar el contenido visible de esa ventana.',
                    window_open=True,
                    focused=True,
                    thread_status='correcto_probable',
                    messages_status='desconocidos',
                    session_status='abierta',
                    probe_status='permiso_requerido',
                    permission_state='requerido',
                    observed_via=['windows_api', 'codex_state_sqlite'],
                    detected_blocks=['permission_required'],
                    confidence=0.78,
                    metadata={'permission_scope': 'observe_window_content:codex'},
                )
            ],
            [],
        )
        service._background_processes = lambda *, full: []  # type: ignore[method-assign]

        snapshot = service.scan_now(reason='manual', full=True)

        assert snapshot.permission_gates
        assert snapshot.permission_gates[0].assistant_kind == 'codex'
        assert snapshot.permission_gates[0].scope == 'observe_window_content:codex'
        assert snapshot.permission_gates[0].status == 'requerido'
        assert any(item.block_type == 'permission_required' and item.target_scope == 'consult_codex' for item in snapshot.block_records)
        assert 'permission_required:observe_window_content:codex' in snapshot.detected_blocks
        assert 'permission_registry' in snapshot.observation_sources
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_service_blocks_heavy_local_route_when_cpu_pressure_is_detected() -> None:
    workspace = _workspace('world_model_cpu_pressure')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._environment_self_model = lambda: EnvironmentSelfModel(  # type: ignore[method-assign]
            environment_id='env-demo',
            scan_status='ready',
            risk_signals=[],
        )
        service._list_windows = lambda: []  # type: ignore[method-assign]
        service._focused_window = lambda: None  # type: ignore[method-assign]
        service._network_status = lambda *, full: (  # type: ignore[method-assign]
            NetworkStatusSnapshot(
                connected=True,
                status='conectado',
                quality='buena',
                latency_ms=27.0,
                detail='La red responde bien.',
            ),
            [],
        )
        service._tool_live_status = lambda **_: (  # type: ignore[method-assign]
            [
                ToolLiveStatus(
                    tool_id='ollama_llm',
                    title='Ollama local',
                    assistant_kind='ollama',
                    available=True,
                    status='disponible',
                    detail='Proveedor local listo.',
                    messages_status='disponibles',
                    session_status='activa',
                    probe_status='verificado_pasivo',
                    confidence=0.84,
                )
            ],
            [],
        )
        service._background_processes = lambda *, full: [  # type: ignore[method-assign]
            BackgroundProcessSnapshot(
                process_name='python-heavy',
                pid=5150,
                memory_mb=1536.0,
                cpu_percent=88.0,
                cpu_load_percent=88.0,
                gpu_percent=None,
                state='cpu_heavy',
                detail='Consume CPU de forma sostenida.',
            )
        ]

        snapshot = service.scan_now(reason='manual', full=True)

        assert 'process_cpu_heavy:python-heavy' in snapshot.detected_blocks
        assert 'UNRESOLVED:gpu_process_usage' in snapshot.unresolved_fields
        assert any(item.block_type == 'cpu_heavy' and item.target_scope == 'heavy_local_model' for item in snapshot.block_records)
        assert any(item.get('target_scope') == 'heavy_local_model' for item in snapshot.inferred_state.get('blocked_routes', []))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_background_processes_preserves_browser_processes_not_in_top_cpu() -> None:
    workspace = _workspace('world_model_browser_process_inventory')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )

        def fake_powershell_json(command: str):
            if 'Get-Process -Name' in command:
                return {
                    'Name': 'msedge',
                    'IDProcess': 10636,
                    'PercentProcessorTime': 0.0,
                    'WorkingSetPrivate': 300 * 1024 * 1024,
                }
            return {
                'Name': 'python-heavy',
                'IDProcess': 5150,
                'PercentProcessorTime': 92.0,
                'WorkingSetPrivate': 512 * 1024 * 1024,
            }

        service._powershell_json = fake_powershell_json  # type: ignore[method-assign]

        processes = service._background_processes(full=True)
        names = {item.process_name for item in processes}
        edge = next(item for item in processes if item.process_name == 'msedge')

        assert 'python-heavy' in names
        assert 'msedge' in names
        assert edge.metadata.get('browser_process_candidate') is True
        assert 'ventana visible' in edge.metadata.get('observation_note', '')
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_browser_processes_fallback_to_tasklist_when_powershell_times_out() -> None:
    workspace = _workspace('world_model_browser_tasklist_fallback')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        service._powershell_json = lambda _command: None  # type: ignore[method-assign]
        tasklist_output = (
            '"Image Name","PID","Session Name","Session#","Mem Usage"\n'
            '"msedge.exe","10636","Console","1","38,556 K"\n'
        )
        completed = SimpleNamespace(returncode=0, stdout=tasklist_output)

        with patch('iabv_v15.services.evolution.world_model_service.os.name', 'nt'), \
                patch('iabv_v15.services.evolution.world_model_service.subprocess.run', MagicMock(return_value=completed)):
            processes = service._background_processes(full=True)

        edge = next(item for item in processes if item.process_name == 'msedge')
        assert edge.pid == 10636
        assert edge.metadata.get('browser_process_candidate') is True
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_service_prefers_live_codex_thread_over_stale_wrong_thread_history() -> None:
    workspace = _workspace('world_model_codex_live_thread')
    try:
        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            auto_start=False,
            bootstrap_scan=False,
        )
        card = ToolCard(
            tool_id='codex_installed',
            title='Codex instalado',
            tool_type=ToolType.CUSTOM,
            adapter_key='external_assistant',
            available=True,
            metadata={
                'assistant_kind': 'codex',
                'launch_mode': 'desktop_app',
                'response_capture_mode': 'clipboard_capture',
            },
        )
        service._cards_to_probe = lambda: [card]  # type: ignore[method-assign]
        service._tool_signal = lambda _: SimpleNamespace(  # type: ignore[method-assign]
            metadata={'observed_pid': 16668, 'window_count': 1, 'process_count': 0},
            visual_snapshot={'window_visible': True, 'process_running': True},
            latest_title='Codex',
            unresolved_fields=[],
        )
        service._recent_tool_history = lambda _tool_id: {  # type: ignore[method-assign]
            'external_state_flags': ['wrong_thread'],
            'error_message': 'wrong_thread',
            'browser_security_verification': False,
            'state': 'failed',
            'detail': 'La evidencia reciente apunta a un hilo distinto del esperado.',
            'latest_success': False,
            'awaiting_response': False,
        }
        service._codex_thread_status = lambda _card: (  # type: ignore[method-assign]
            'correcto_probable',
            'Codex parece estar enfocado en el hilo correcto del workspace actual.',
            [],
        )
        service._probe_state_for_tool = lambda **_: (  # type: ignore[method-assign]
            'verificado_pasivo',
            'no_requerido',
            '',
            [],
            True,
        )

        statuses, unresolved = service._tool_live_status(
            raw_windows=[{'title': 'Codex', 'pid': 16668}],
            focused=WindowObservation(
                title='Codex',
                app_name='Codex',
                pid=16668,
                focused=True,
                visible=True,
                state='focused',
            ),
            network_status=NetworkStatusSnapshot(
                connected=True,
                status='conectado',
                quality='buena',
                latency_ms=24.0,
                detail='La red responde bien.',
            ),
            environment=EnvironmentSelfModel(
                environment_id='env-demo',
                scan_status='ready',
                risk_signals=[],
            ),
            full=True,
        )

        assert unresolved == []
        assert len(statuses) == 1
        codex = statuses[0]
        assert codex.status == 'abierto'
        assert codex.thread_status == 'correcto_probable'
        assert 'wrong_thread' not in codex.detected_blocks
        assert 'wrong_thread' not in codex.external_state_flags
        assert 'hilo correcto' in codex.detail.lower()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_world_model_service_cards_to_probe_includes_shell_and_site_explorer() -> None:
    """_cards_to_probe debe incluir shell_command y site_explorer_v1 además de assistants.

    Antes sólo se probaban tools con `assistant_kind` o en un allowlist chico
    (`playwright_browser`, `desktop_human_runner`). Esto producía mismatches en
    `self_audit.environment_match` porque `EnvironmentSelfModel.available_tools`
    sí los declaraba pero `WorldModelSnapshot.tool_live_status` no.
    """
    workspace = _workspace('world_model_cards_probe')
    try:
        cards = [
            ToolCard(
                tool_id='ollama_llm',
                title='Ollama LLM',
                tool_type=ToolType.LLM_LOCAL,
                adapter_key='ollama',
                available=True,
                metadata={'assistant_kind': 'ollama'},
            ),
            ToolCard(
                tool_id='shell_command',
                title='Shell command',
                tool_type=ToolType.SHELL,
                adapter_key='shell',
                available=True,
                metadata={'launch_mode': 'cli'},
            ),
            ToolCard(
                tool_id='site_explorer_v1',
                title='Site explorer',
                tool_type=ToolType.CUSTOM,
                adapter_key='site_explorer',
                available=True,
                metadata={'launch_mode': 'library'},
            ),
            ToolCard(
                tool_id='playwright_browser',
                title='Playwright',
                tool_type=ToolType.CUSTOM,
                adapter_key='playwright',
                available=True,
                metadata={'launch_mode': 'library'},
            ),
        ]

        class _FakeRegistry:
            def list_cards(self) -> list[ToolCard]:
                return list(cards)

            def refresh_card(self, card: ToolCard) -> ToolCard:
                return card

        service = WorldModelService(
            workspace_root=str(workspace),
            evolution_dir=str(workspace / 'evolution'),
            tool_registry=_FakeRegistry(),
            auto_start=False,
            bootstrap_scan=False,
        )

        selected = service._cards_to_probe()
        selected_ids = {card.tool_id for card in selected}

        assert 'ollama_llm' in selected_ids
        assert 'playwright_browser' in selected_ids
        assert 'shell_command' in selected_ids, (
            'shell_command debe aparecer en tool_live_status para alinear con '
            'EnvironmentSelfModel.available_tools'
        )
        assert 'site_explorer_v1' in selected_ids, (
            'site_explorer_v1 debe aparecer en tool_live_status para alinear '
            'con EnvironmentSelfModel.available_tools'
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
