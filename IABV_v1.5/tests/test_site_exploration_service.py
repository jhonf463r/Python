"""Tests de SiteExplorationService y SiteManualRepository (PR-D).

Usan `FakeBrowserController` y `FakePage` para no depender de playwright
real. Verifican:

- Crawl same-domain con budget respetado y orden BFS.
- Links externos descartados.
- Normalizacion de URLs (fragments, schemas distintos).
- Manual persistido en JSON + markdown reload.
- Summary opcional se invoca y puede capturar errores sin romper.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from iabv_v15.infra.persistence.site_manual_repository import SiteManualRepository
from iabv_v15.services.tools.site_exploration_service import SiteExplorationService


class FakePage:
    def __init__(self, pages: dict[str, dict[str, Any]]) -> None:
        self._pages = pages
        self.visited: list[str] = []
        self._current: dict[str, Any] = {}
        self.closed = False

    def goto(self, url: str, **_: Any) -> None:
        self.visited.append(url)
        self._current = self._pages.get(url, {'title': '', 'headings': [], 'links': [], 'forms': []})

    def title(self) -> str:  # Playwright-style
        return str(self._current.get('title') or '')

    def evaluate(self, script: str) -> Any:
        if 'querySelectorAll(\'h1, h2, h3\')' in script:
            return list(self._current.get('headings') or [])
        if 'querySelectorAll(\'a[href]\')' in script:
            return list(self._current.get('links') or [])
        if 'querySelectorAll(\'form\')' in script:
            return list(self._current.get('forms') or [])
        return []


class FakeController:
    def __init__(self, fake_page: FakePage) -> None:
        self.page: FakePage | None = None
        self._prepared = fake_page
        self.closed = False

    def start(self) -> None:
        self.page = self._prepared

    def new_page(self) -> FakePage:
        self.page = self._prepared
        return self._prepared

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def dummy_site() -> dict[str, dict[str, Any]]:
    return {
        'https://example.com/': {
            'title': 'Home',
            'headings': ['Welcome', 'Features'],
            'links': [
                '/about',
                '/pricing',
                'https://other.example.net/spam',
                'mailto:hi@example.com',
                'javascript:void(0)',
                '#top',
            ],
            'forms': [{'action': '/search', 'method': 'get', 'inputs': [{'name': 'q', 'type': 'text'}]}],
        },
        'https://example.com/about': {
            'title': 'About us',
            'headings': ['Mission'],
            'links': ['/pricing', '/contact', 'https://external.example.org/x'],
            'forms': [],
        },
        'https://example.com/pricing': {
            'title': 'Pricing',
            'headings': ['Plans'],
            'links': ['/pricing', '/about'],
            'forms': [],
        },
        'https://example.com/contact': {
            'title': 'Contact',
            'headings': [],
            'links': [],
            'forms': [{'action': '/contact/submit', 'method': 'post', 'inputs': [{'name': 'email', 'type': 'email'}]}],
        },
    }


def _service(dummy_site: dict[str, dict[str, Any]], *, summary_fn=None) -> tuple[SiteExplorationService, FakeController]:
    page = FakePage(dummy_site)
    controller = FakeController(page)
    service = SiteExplorationService(
        controller_factory=lambda: controller,
        summary_fn=summary_fn,
    )
    return service, controller


def test_explore_bfs_same_domain_respects_budget_and_drops_external_links(dummy_site: dict[str, dict[str, Any]]) -> None:
    service, controller = _service(dummy_site)

    result = service.explore(start_url='https://example.com/', max_pages=3)

    assert result.success is True
    assert result.hostname == 'example.com'
    assert [p.url for p in result.pages] == [
        'https://example.com/',
        'https://example.com/about',
        'https://example.com/pricing',
    ]
    assert controller.closed is True
    # ningun link externo se incluyo en los internos
    for page in result.pages:
        for link in page.internal_links:
            assert 'example.com' in link
            assert 'other.example.net' not in link
            assert 'external.example.org' not in link
    # los fragments/mailto/javascript se descartaron
    home = result.pages[0]
    assert all('mailto:' not in link and 'javascript:' not in link for link in home.internal_links)
    # formularios detectados en home
    assert home.forms and home.forms[0]['action'] == '/search'


def test_explore_returns_failure_when_start_url_has_no_hostname() -> None:
    service, _ = _service({})
    result = service.explore(start_url='not-a-url')
    assert result.success is False
    assert 'hostname' in result.error_message.lower()
    assert result.pages == []


def test_explore_runs_summary_fn_when_success_and_captures_its_errors(dummy_site: dict[str, dict[str, Any]]) -> None:
    called = {}

    def summary_ok(pages, start_url, hostname):
        called['ok_args'] = (len(pages), start_url, hostname)
        return 'Resumen humano del crawl.'

    service, _ = _service(dummy_site, summary_fn=summary_ok)
    result = service.explore(start_url='https://example.com/', max_pages=2)
    assert result.summary == 'Resumen humano del crawl.'
    assert called['ok_args'][1] == 'https://example.com/'
    assert called['ok_args'][2] == 'example.com'

    def summary_explodes(*_args):
        raise RuntimeError('boom')

    service_bad, _ = _service(dummy_site, summary_fn=summary_explodes)
    result_bad = service_bad.explore(start_url='https://example.com/', max_pages=1)
    assert result_bad.success is True
    assert result_bad.summary.startswith('(summary_fn fallo: RuntimeError')


def test_site_manual_repository_round_trips_payload_to_json_and_markdown(tmp_path: Path) -> None:
    repo = SiteManualRepository(tmp_path / 'site_manuals')
    manual = {
        'hostname': 'example.com',
        'start_url': 'https://example.com/',
        'pages': [
            {
                'url': 'https://example.com/',
                'title': 'Home',
                'headings': ['Welcome'],
                'internal_links': ['https://example.com/about'],
                'forms': [{'action': '/search'}],
                'error': '',
            }
        ],
        'summary': 'Un sitio de prueba.',
    }
    json_path, md_path = repo.save(manual)
    assert json_path.exists() and md_path.exists()

    loaded = repo.load('example.com')
    assert loaded is not None
    assert loaded['hostname'] == 'example.com'
    assert loaded['pages'][0]['title'] == 'Home'
    assert 'updated_at_utc' in loaded

    md = md_path.read_text(encoding='utf-8')
    assert '# Manual del sitio `example.com`' in md
    assert 'Un sitio de prueba.' in md
    assert 'Welcome' in md

    # el slug del hostname evita caracteres exoticos
    exotic = {'hostname': 'WEIRD!hostname?.com', 'pages': [], 'start_url': ''}
    json_exo, md_exo = repo.save(exotic)
    assert '_' in json_exo.stem
    assert md_exo.exists()
    raw = json.loads(json_exo.read_text(encoding='utf-8'))
    assert raw['hostname'] == 'weird!hostname?.com'


def test_site_manual_repository_rejects_empty_hostname(tmp_path: Path) -> None:
    repo = SiteManualRepository(tmp_path / 'site_manuals')
    with pytest.raises(ValueError):
        repo.save({'hostname': '', 'pages': []})


def test_site_manual_repository_load_missing_returns_none(tmp_path: Path) -> None:
    repo = SiteManualRepository(tmp_path / 'site_manuals')
    assert repo.load('does-not-exist.com') is None
