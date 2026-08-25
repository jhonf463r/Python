"""Tests de SiteExplorerToolAdapter (PR-D).

Verifica que el adapter parsea correctamente las acciones del ToolTask,
llama al service con parametros canonicos y persiste el manual via el
repositorio. Usa doubles para service y repository.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from iabv_v15.domain.models import (
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolTask,
    ToolType,
)
from iabv_v15.services.tools.site_exploration_service import SiteExplorationResult, SitePageSnapshot
from iabv_v15.services.tools.tool_adapters import SiteExplorerToolAdapter


class _FakeService:
    def __init__(self, result: SiteExplorationResult | None = None) -> None:
        self._result = result or SiteExplorationResult(
            hostname='example.com',
            start_url='https://example.com/',
            pages=[SitePageSnapshot(url='https://example.com/', title='Home')],
            success=True,
        )
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def explore(self, *, start_url: str, max_pages: int | None = None, priority_keywords=None) -> SiteExplorationResult:
        self.calls.append(
            {
                'start_url': start_url,
                'max_pages': max_pages,
                'priority_keywords': list(priority_keywords or []),
            }
        )
        return self._result


class _FakeRepository:
    def __init__(self, base: Path) -> None:
        self.saved: list[dict[str, Any]] = []
        self._base = base

    def save(self, manual: dict[str, Any]) -> tuple[Path, Path]:
        self.saved.append(manual)
        json_path = self._base / f"{manual['hostname']}.json"
        md_path = self._base / f"{manual['hostname']}.md"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text('stub', encoding='utf-8')
        md_path.write_text('stub', encoding='utf-8')
        return json_path, md_path


def _card() -> ToolCard:
    return ToolCard(
        tool_id='site_explorer_v1',
        title='Site explorer v1',
        tool_type=ToolType.BROWSER,
        description='test',
        adapter_key='site_explorer',
    )


def _task(url: str | None, **params: Any) -> ToolTask:
    actions = []
    if url is not None:
        actions.append(
            ToolAction(
                action_id='a1',
                action_type=ToolActionType.OPEN_URL,
                label='open target url',
                target=url,
                parameters=params,
            )
        )
    return ToolTask(
        tool_id='site_explorer_v1',
        title='Explorar sitio',
        objective=url or 'explorar',
        actions=actions,
    )


def test_site_explorer_adapter_passes_parameters_and_persists_manual(tmp_path: Path) -> None:
    service = _FakeService()
    repo = _FakeRepository(tmp_path)
    adapter = SiteExplorerToolAdapter(service, repo)

    task = _task(
        'https://example.com/',
        max_pages=4,
        priority_keywords=['pricing', 'docs'],
    )
    result = adapter.run(_card(), task)

    assert result['success'] is True
    assert service.calls == [
        {
            'start_url': 'https://example.com/',
            'max_pages': 4,
            'priority_keywords': ['pricing', 'docs'],
        }
    ]
    assert repo.saved, 'el adapter debe persistir el manual cuando la exploracion fue exitosa'
    assert repo.saved[0]['hostname'] == 'example.com'
    assert result['metadata']['pages_visited'] == 1
    assert 'example.com' in (result['output_text'] or '')
    assert any(str(tmp_path) in art for art in result['artifacts'])


def test_site_explorer_adapter_returns_error_when_no_open_url_action(tmp_path: Path) -> None:
    service = _FakeService()
    repo = _FakeRepository(tmp_path)
    adapter = SiteExplorerToolAdapter(service, repo)

    task = _task(None)
    result = adapter.run(_card(), task)

    assert result['success'] is False
    assert 'OPEN_URL' in result['error_message']
    assert service.calls == []
    assert repo.saved == []


def test_site_explorer_adapter_does_not_persist_on_service_failure(tmp_path: Path) -> None:
    failed_result = SiteExplorationResult(
        hostname='example.com',
        start_url='https://example.com/',
        pages=[],
        success=False,
        error_message='timeout',
    )
    service = _FakeService(result=failed_result)
    repo = _FakeRepository(tmp_path)
    adapter = SiteExplorerToolAdapter(service, repo)

    result = adapter.run(_card(), _task('https://example.com/'))
    assert result['success'] is False
    assert 'timeout' in result['error_message']
    assert repo.saved == []


def test_site_explorer_adapter_reports_repository_failure_without_crashing(tmp_path: Path) -> None:
    class _RaisingRepo:
        def save(self, _manual: dict[str, Any]) -> tuple[Path, Path]:
            raise OSError('disk full')

    service = _FakeService()
    adapter = SiteExplorerToolAdapter(service, _RaisingRepo())

    result = adapter.run(_card(), _task('https://example.com/'))
    assert result['success'] is False
    assert 'disk full' in result['error_message']
    assert result['extracted_data']['hostname'] == 'example.com'
