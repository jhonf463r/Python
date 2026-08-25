from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import TaskRole, ToolCard, ToolTask, ToolType
from iabv_v15.infra.persistence.database import AppDatabase
from iabv_v15.infra.persistence.storage import ArtifactStorage
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter
from iabv_v15.services.tools.tool_registry import ToolRegistry


class _UnavailableAdapter:
    tool_type = ToolType.CUSTOM

    def is_available(self, card: ToolCard) -> bool:
        return False

    def run(self, card: ToolCard, task, *, sandbox: bool = False) -> dict:
        return {'success': False}


class _AvailableAdapter:
    def __init__(self) -> None:
        self.calls = 0

    tool_type = ToolType.CUSTOM

    def is_available(self, card: ToolCard) -> bool:
        self.calls += 1
        return True

    def run(self, card: ToolCard, task, *, sandbox: bool = False) -> dict:
        return {'success': True}


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_external_assistant_adapter_resolves_wildcard_candidate_path(monkeypatch) -> None:
    root = _workspace('external_assistant_wildcard')
    try:
        openai_root = root / 'OpenAI'
        version_dir = openai_root / 'app-1.0.0'
        version_dir.mkdir(parents=True, exist_ok=True)
        exe = version_dir / 'ChatGPT.exe'
        exe.write_text('stub', encoding='utf-8')

        monkeypatch.setenv('LOCALAPPDATA', str(root))
        card = ToolCard(
            tool_id='chatgpt_installed',
            title='ChatGPT instalado',
            tool_type=ToolType.CUSTOM,
            adapter_key='external_assistant',
            metadata={
                'command_name': 'chatgpt',
                'command_aliases': ['ChatGPT', 'OpenAI'],
                'windows_default_paths': [r'{localappdata}\OpenAI\*\ChatGPT.exe'],
            },
        )

        adapter = ExternalAssistantToolAdapter()

        assert adapter.is_available(card) is True
        assert adapter._resolve_launch_target(card) == str(exe)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_registry_refreshes_default_metadata_but_preserves_manual_executable_path() -> None:
    root = _workspace('tool_registry_metadata_refresh')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        manual_path = str(root / 'manual-chatgpt.exe')
        repository.save_card(
            ToolCard(
                tool_id='chatgpt_installed',
                title='ChatGPT viejo',
                tool_type=ToolType.CUSTOM,
                adapter_key='external_assistant',
                available=False,
                metadata={
                    'assistant_kind': 'chatgpt',
                    'launch_mode': 'desktop_app',
                    'command_name': 'chatgpt',
                    'windows_default_paths': [r'{localappdata}\Programs\ChatGPT\ChatGPT.exe'],
                    'executable_path': manual_path,
                    'updated_at_utc': '2026-01-01T00:00:00+00:00',
                },
            )
        )

        registry = ToolRegistry(repository, {'external_assistant': _UnavailableAdapter()})
        card = repository.get_card('chatgpt_installed')
        assert card is not None
        assert card.metadata['executable_path'] == manual_path
        assert r'{localappdata}\OpenAI\ChatGPT.exe' in card.metadata['windows_default_paths']
        assert 'command_aliases' in card.metadata

        registry = ToolRegistry(repository, {'external_assistant': _AvailableAdapter()})
        # seed_defaults no longer probes availability (deferred to
        # _log_tool_availability); verify via explicit refresh.
        card_pre = repository.get_card('chatgpt_installed')
        assert card_pre is not None
        refreshed = registry.refresh_card(card_pre)
        assert refreshed.available is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_registry_prefers_synaptic_assistant_kind_hint() -> None:
    root = _workspace('tool_registry_synaptic_hint')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        registry = ToolRegistry(repository, {'external_assistant': _AvailableAdapter()})

        task = ToolTask(
            tool_id='',
            title='Revisar arquitectura',
            objective='analiza este cambio con la IA mas fuerte',
            requested_by_role=TaskRole.TOOL_USE,
        )

        card = registry.pick_card_for_task(task, preferred_assistant_kind='claude')

        assert card is not None
        assert card.metadata['assistant_kind'] == 'claude'
    finally:
        shutil.rmtree(root, ignore_errors=True)




def test_external_assistant_adapter_treats_windowsapps_alias_as_launchable_when_exists_raises(monkeypatch) -> None:
    adapter = ExternalAssistantToolAdapter()
    from iabv_v15.services.tools import tool_adapters as module

    def _raise(self) -> bool:
        raise OSError(1920, 'alias access denied')

    monkeypatch.setattr(module.Path, 'exists', _raise)
    assert adapter._path_exists(r'C:\Users\faber\AppData\Local\Microsoft\WindowsApps\ChatGPT.exe') is True
    assert adapter._path_exists(r'C:\tmp\missing.exe') is False


def test_tool_registry_refreshes_codex_defaults_with_windowsapps_candidates() -> None:
    root = _workspace('tool_registry_codex_refresh')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        repository.save_card(
            ToolCard(
                tool_id='codex_installed',
                title='Codex viejo',
                tool_type=ToolType.CUSTOM,
                adapter_key='external_assistant',
                available=False,
                metadata={
                    'assistant_kind': 'codex',
                    'launch_mode': 'desktop_app',
                    'command_name': 'codex',
                    'updated_at_utc': '2026-01-01T00:00:00+00:00',
                },
            )
        )

        registry = ToolRegistry(repository, {'external_assistant': _UnavailableAdapter()})
        card = repository.get_card('codex_installed')
        assert card is not None
        assert 'command_aliases' in card.metadata
        assert any('OpenAI.Codex_' in item for item in card.metadata['windows_default_paths'])
        assert card.metadata['response_capture_mode'] == 'clipboard_capture'
        assert card.metadata['requires_manual_pasteback'] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_tool_registry_seeds_claude_cards_with_expected_metadata() -> None:
    root = _workspace('tool_registry_claude_seed')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)

        ToolRegistry(repository, {'external_assistant': _UnavailableAdapter()})

        claude = repository.get_card('claude_installed')
        claude_web = repository.get_card('claude_web_assisted')
        assert claude is not None
        assert claude_web is not None
        assert claude.metadata['assistant_kind'] == 'claude'
        assert claude.metadata['launch_mode'] == 'desktop_app'
        assert claude.metadata['response_capture_mode'] == 'clipboard_capture'
        assert claude.metadata['requires_manual_pasteback'] is False
        assert 'command_aliases' in claude.metadata
        assert any('Claude.exe' in item for item in claude.metadata['windows_default_paths'])
        assert claude_web.metadata['assistant_kind'] == 'claude'
        assert claude_web.metadata['launch_mode'] == 'web_assisted'
        assert claude_web.metadata['web_url'] == 'https://claude.ai/'
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_registry_resets_stale_dry_run_flag_for_external_desktop_assistants() -> None:
    root = _workspace('tool_registry_dry_run_reset')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        repository.save_card(
            ToolCard(
                tool_id='codex_installed',
                title='Codex stale',
                tool_type=ToolType.CUSTOM,
                adapter_key='external_assistant',
                available=True,
                metadata={
                    'assistant_kind': 'codex',
                    'launch_mode': 'desktop_app',
                    'command_name': 'codex',
                    'dry_run_launch': True,
                    'updated_at_utc': '2026-01-01T00:00:00+00:00',
                },
            )
        )

        ToolRegistry(repository, {'external_assistant': _AvailableAdapter()})
        card = repository.get_card('codex_installed')
        assert card is not None
        assert card.metadata['dry_run_launch'] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_registry_skips_rechecking_fresh_card() -> None:
    root = _workspace('tool_registry_fresh_cache')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        adapter = _AvailableAdapter()
        registry = ToolRegistry(repository, {'custom': adapter})
        card = ToolCard(
            tool_id='custom_tool',
            title='Custom tool',
            tool_type=ToolType.CUSTOM,
            adapter_key='custom',
            available=False,
            metadata={},
        )

        first = registry.refresh_card(card)
        second = registry.refresh_card(first)
        forced = registry.refresh_card(second, force=True)

        assert first.available is True
        assert second.available is True
        assert forced.available is True
        assert adapter.calls == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_windsurf_toolcard_seeded_with_correct_metadata() -> None:
    """Verifica que el ToolCard de Windsurf se registra con metadata conservadora."""
    root = _workspace('windsurf_metadata_check')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        registry = ToolRegistry(repository, {'external_assistant': _AvailableAdapter()})

        card = registry.get_card('windsurf_installed')
        assert card is not None
        assert card.tool_id == 'windsurf_installed'
        assert card.title == 'Windsurf instalado'
        assert card.adapter_key == 'external_assistant'
        assert card.available is True
        assert card.requires_human_approval is True
        assert 'launch_app' in card.capabilities
        assert 'code_assistance' in card.capabilities

        # Verificar metadata conservadora
        assert card.metadata.get('assistant_kind') == 'windsurf'
        assert card.metadata.get('launch_mode') == 'desktop_app'
        assert card.metadata.get('command_name') == 'windsurf'
        assert 'windsurf.exe' in card.metadata.get('command_aliases', [])

        # Verificar rutas oficiales confirmadas por Codex
        windows_paths = card.metadata.get('windows_default_paths', [])
        assert any(r'\Windsurf\Windsurf.exe' in p for p in windows_paths)

        # Verificar paths de config oficiales
        config_paths = card.metadata.get('config_paths', [])
        assert any(r'\.codeium\windsurf' in p for p in config_paths)

        # Verificar comportamiento real: lanzable con pasteback manual, auto-capture UNRESOLVED
        assert card.metadata.get('status') == 'AVAILABLE_MANUAL_ASSISTED'
        assert card.metadata.get('status_reason') == 'auto_capture_unconfirmed'
        assert card.metadata.get('requires_manual_pasteback') is True
        # response_capture_mode NO debe estar presente (UNRESOLVED)
        assert 'response_capture_mode' not in card.metadata or not card.metadata.get('response_capture_mode')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_windsurf_adapter_detects_by_official_path_programfiles(monkeypatch) -> None:
    r"""Verifica detección de Windsurf por ruta oficial C:\Program Files\Windsurf."""
    root = _workspace('windsurf_programfiles_detection')
    try:
        windsurf_dir = root / 'Program Files' / 'Windsurf'
        windsurf_dir.mkdir(parents=True, exist_ok=True)
        exe = windsurf_dir / 'Windsurf.exe'
        exe.write_text('stub', encoding='utf-8')

        monkeypatch.setenv('ProgramFiles', str(root / 'Program Files'))

        card = ToolCard(
            tool_id='windsurf_installed',
            title='Windsurf instalado',
            tool_type=ToolType.CODE_EDITOR,
            adapter_key='external_assistant',
            metadata={
                'command_name': 'windsurf',
                'command_aliases': ['windsurf.exe'],
                'windows_default_paths': [
                    r'{programfiles}\Windsurf\Windsurf.exe',
                    r'{localappdata}\Programs\Windsurf\Windsurf.exe',
                ],
            },
        )

        adapter = ExternalAssistantToolAdapter()
        assert adapter.is_available(card) is True
        resolved = adapter._resolve_launch_target(card)
        assert 'Windsurf' in resolved or 'windsurf' in resolved.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_windsurf_adapter_detects_by_official_path_localappdata(monkeypatch) -> None:
    r"""Verifica detección de Windsurf por ruta oficial %LocalAppData%\Programs\Windsurf."""
    root = _workspace('windsurf_localappdata_detection')
    try:
        windsurf_dir = root / 'Programs' / 'Windsurf'
        windsurf_dir.mkdir(parents=True, exist_ok=True)
        exe = windsurf_dir / 'Windsurf.exe'
        exe.write_text('stub', encoding='utf-8')

        monkeypatch.setenv('LOCALAPPDATA', str(root))

        card = ToolCard(
            tool_id='windsurf_installed',
            title='Windsurf instalado',
            tool_type=ToolType.CODE_EDITOR,
            adapter_key='external_assistant',
            metadata={
                'command_name': 'windsurf',
                'windows_default_paths': [
                    r'{programfiles}\Windsurf\Windsurf.exe',
                    r'{localappdata}\Programs\Windsurf\Windsurf.exe',
                ],
            },
        )

        adapter = ExternalAssistantToolAdapter()
        assert adapter.is_available(card) is True
        resolved = adapter._resolve_launch_target(card)
        assert 'Windsurf' in resolved or 'windsurf' in resolved.lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_windsurf_adapter_detects_by_command_name_in_path(monkeypatch) -> None:
    """Verifica detección de Windsurf por comando 'windsurf' en PATH."""
    import os
    import stat
    root = _workspace('windsurf_path_detection')
    try:
        windsurf_dir = root / 'bin'
        windsurf_dir.mkdir(parents=True, exist_ok=True)
        exe_name = 'windsurf.exe' if os.name == 'nt' else 'windsurf'
        exe = windsurf_dir / exe_name
        exe.write_text('stub', encoding='utf-8')
        if os.name != 'nt':
            exe.chmod(exe.stat().st_mode | stat.S_IEXEC)

        original_path = os.environ.get('PATH', '')
        monkeypatch.setenv('PATH', str(windsurf_dir) + os.pathsep + original_path)

        card = ToolCard(
            tool_id='windsurf_installed',
            title='Windsurf instalado',
            tool_type=ToolType.CODE_EDITOR,
            adapter_key='external_assistant',
            metadata={
                'command_name': 'windsurf',
                'command_aliases': ['windsurf.exe'],
                'windows_default_paths': [],
            },
        )

        adapter = ExternalAssistantToolAdapter()
        assert adapter.is_available(card) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_windsurf_backward_compatibility_no_break_existing_tools() -> None:
    """Verifica que agregar Windsurf no rompe el registro de herramientas existentes."""
    root = _workspace('windsurf_backward_compat')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        registry = ToolRegistry(repository, {'external_assistant': _UnavailableAdapter()})

        # Verificar que herramientas existentes siguen presentes
        assert registry.get_card('codex_installed') is not None
        assert registry.get_card('chatgpt_installed') is not None
        assert registry.get_card('claude_installed') is not None
        assert registry.get_card('ollama_llm') is not None
        assert registry.get_card('shell_command') is not None

        # Verificar que Windsurf está presente
        windsurf_card = registry.get_card('windsurf_installed')
        assert windsurf_card is not None
        assert windsurf_card.metadata.get('assistant_kind') == 'windsurf'
    finally:
        shutil.rmtree(root, ignore_errors=True)
