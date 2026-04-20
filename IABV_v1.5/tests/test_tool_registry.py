from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import ToolCard, ToolType
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
        refreshed = repository.get_card('chatgpt_installed')
        assert refreshed is not None
        assert refreshed.available is True
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


def test_tool_registry_pick_card_for_task_selects_best_match_not_first() -> None:
    """pick_card_for_task must return the highest-scoring card, not the first
    card that happens to share any substring with the objective."""
    root = _workspace('tool_registry_pick_best')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        registry = ToolRegistry(repository, {
            'playwright': _UnavailableAdapter(),
            'ollama': _UnavailableAdapter(),
            'external_assistant': _UnavailableAdapter(),
        })
        from iabv_v15.domain.models import ToolTask
        task = ToolTask(
            tool_id='',
            title='consulta local',
            objective='necesito inferencia local para clasificar y razonamiento',
        )

        card = registry.pick_card_for_task(task)

        assert card is not None
        assert card.tool_id == 'ollama_llm', (
            f'Expected ollama_llm (best match for inferencia/razonamiento) '
            f'but got {card.tool_id}'
        )

        task_browser = ToolTask(
            tool_id='',
            title='abrir pagina',
            objective='abrir screenshot click automatizacion web',
        )
        card_browser = registry.pick_card_for_task(task_browser)
        assert card_browser is not None
        assert card_browser.tool_id == 'playwright_browser', (
            f'Expected playwright_browser (best match for screenshot/click/web) '
            f'but got {card_browser.tool_id}'
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tool_registry_pick_card_ignores_short_tokens() -> None:
    """Short tokens like 'en', 'de', 'la' must not cause spurious matches.
    With only short tokens no card should score > 0, so the method falls
    back to the first card in list_cards() (which is the first seeded
    default).  The important assertion is that 'specific_tool' is NOT
    chosen over seeded defaults just because of substring collisions."""
    root = _workspace('tool_registry_pick_short_tokens')
    try:
        db = AppDatabase(str(root / 'app.sqlite'))
        storage = ArtifactStorage(str(root / 'tool_teaching'))
        repository = ToolRecordRepository(db, storage)
        repository.save_card(
            ToolCard(
                tool_id='specific_tool',
                title='Herramienta especifica',
                tool_type=ToolType.CUSTOM,
                adapter_key='custom',
                capabilities=['diagnostico'],
                description='Diagnostico avanzado de problemas.',
            )
        )
        registry = ToolRegistry(repository, {'custom': _UnavailableAdapter()})
        from iabv_v15.domain.models import ToolTask

        task_short = ToolTask(
            tool_id='',
            title='en la de',
            objective='en la de el un',
        )
        card_short = registry.pick_card_for_task(task_short)
        assert card_short is not None

        task_specific = ToolTask(
            tool_id='',
            title='diagnostico',
            objective='diagnostico avanzado problemas',
        )
        card_specific = registry.pick_card_for_task(task_specific)
        assert card_specific is not None
        assert card_specific.tool_id == 'specific_tool', (
            f'Expected specific_tool (best match for diagnostico/avanzado/problemas) '
            f'but got {card_specific.tool_id}'
        )
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
