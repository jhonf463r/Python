from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import ToolCard, ToolType
from iabv_v15.services.tools.tool_adapters import ExternalAssistantToolAdapter


def _workspace(name: str) -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'{name}_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_external_assistant_adapter_resolves_wildcard_candidate_path(monkeypatch) -> None:
    root = _workspace('external_assistant_wildcard')
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



def test_external_assistant_adapter_uses_clipboard_capture_when_runner_returns_text() -> None:
    root = _workspace('external_assistant_clipboard_capture')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': True,
                'captured_text': 'Causa raiz probable: Bridge saturado. Cambio vertical recomendado: Ajustar drenado.',
                'error_message': '',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Diagnostico redactado')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is True
    assert result['output_text'].startswith('Causa raiz probable:')
    assert result['metadata']['response_capture_mode'] == 'clipboard_capture'
    assert result['metadata']['manual_pasteback_required'] is False
    assert result['metadata']['response_captured'] is True


def test_external_assistant_adapter_falls_back_to_manual_when_clipboard_capture_is_empty() -> None:
    root = _workspace('external_assistant_clipboard_fallback')
    exe = root / 'ChatGPT.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'ChatGPT',
                'response_captured': False,
                'captured_text': '',
                'error_message': 'clipboard_capture_empty',
            }

    card = ToolCard(
        tool_id='chatgpt_installed',
        title='ChatGPT instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'chatgpt',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['ChatGPT'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='chatgpt_installed',
        title='Consultar ChatGPT',
        objective='Explicar bloqueo',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Contexto redactado')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is True
    assert 'Copia la respuesta' in result['output_text']
    assert result['metadata']['response_capture_mode'] == 'manual_pasteback'
    assert result['metadata']['manual_pasteback_required'] is True
    assert result['metadata']['response_captured'] is False


def test_external_assistant_adapter_prefers_command_name_when_which_points_to_protected_windowsapps(monkeypatch) -> None:
    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'command_name': 'codex',
            'command_aliases': ['codex.exe'],
            'windows_default_paths': [],
        },
    )
    adapter = ExternalAssistantToolAdapter()

    monkeypatch.setattr('shutil.which', lambda name: r'C:\Program Files\WindowsApps\OpenAI.Codex_1\app\resources\codex.exe')

    assert adapter._resolve_launch_target(card) == 'codex'



def test_external_assistant_adapter_uses_session_rollout_capture_when_runner_returns_codex_session_text() -> None:
    root = _workspace('external_assistant_session_rollout_capture')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': True,
                'capture_source': 'session_rollout',
                'captured_text': 'Causa raiz probable: Bridge saturado. Cambio vertical recomendado: Ajustar drenado.',
                'thread_verified': True,
                'used_fallback_capture': False,
                'error_message': '',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'background_capture_mode': 'codex_rollout',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Pending issue: issue-123')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is True
    assert result['metadata']['response_capture_mode'] == 'session_rollout'
    assert result['metadata']['manual_pasteback_required'] is False
    assert result['metadata']['response_captured'] is True


def test_external_assistant_adapter_rejects_unverified_codex_clipboard_capture_when_rollout_mode_is_expected() -> None:
    root = _workspace('external_assistant_unverified_codex_clipboard_capture')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': True,
                'capture_source': 'clipboard_capture',
                'captured_text': 'Texto visible de una ventana de Codex, pero no del hilo verificado.',
                'thread_verified': False,
                'used_fallback_capture': False,
                'error_message': '',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'background_capture_mode': 'codex_rollout',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Pending issue: issue-123')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is False
    assert result['error_message'] == 'capture_unverified'
    assert result['metadata']['capture_unverified'] is True
    assert result['metadata']['response_captured'] is False
    assert result['metadata']['response_capture_mode'] == 'clipboard_capture'


def test_external_assistant_adapter_uses_isolated_codex_home_for_rollout_capture() -> None:
    root = _workspace('external_assistant_isolated_codex_home')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')
    captured_kwargs: dict[str, object] = {}

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            captured_kwargs.update(kwargs)
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': False,
                'captured_text': '',
                'error_message': 'codex_rollout_pending',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'background_capture_mode': 'codex_rollout',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Pending issue: issue-123')],
        metadata={'workspace_root': str(root)},
    )

    adapter.run(card, task, sandbox=False)

    expected_home = root / 'data' / 'tool_teaching' / 'external_assistants' / 'codex_home'
    assert captured_kwargs['session_state_path'] == str(expected_home / 'state_5.sqlite')
    assert captured_kwargs['session_rollouts_root'] == str(expected_home / 'sessions')
    assert captured_kwargs['launch_env']['CODEX_HOME'] == str(expected_home)


def test_external_assistant_adapter_keeps_codex_rollout_pending_without_forcing_manual_pasteback() -> None:
    root = _workspace('external_assistant_codex_pending')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': False,
                'captured_text': '',
                'capture_source': '',
                'error_message': 'codex_rollout_pending',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'background_capture_mode': 'codex_rollout',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Pending issue: issue-456')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is True
    assert 'segundo plano' in result['output_text'].lower()
    assert result['metadata']['response_capture_mode'] == 'clipboard_capture'
    assert result['metadata']['manual_pasteback_required'] is False
    assert result['metadata']['response_capture_pending'] is True
    assert result['metadata']['capture_source'] == 'codex_rollout'


def test_external_assistant_adapter_blocks_codex_when_state_tracking_is_missing() -> None:
    root = _workspace('external_assistant_codex_state_missing')
    exe = root / 'Codex.exe'
    exe.write_text('stub', encoding='utf-8')

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Codex',
                'response_captured': False,
                'captured_text': '',
                'capture_source': '',
                'error_message': 'codex_state_missing',
            }

    card = ToolCard(
        tool_id='codex_installed',
        title='Codex instalado',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'codex',
            'launch_mode': 'desktop_app',
            'response_capture_mode': 'clipboard_capture',
            'background_capture_mode': 'codex_rollout',
            'requires_manual_pasteback': False,
            'executable_path': str(exe),
            'window_title_hints': ['Codex'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='codex_installed',
        title='Consultar Codex',
        objective='Resolver bridge lag',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Pending issue: issue-789')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is False
    assert result['error_message'] == 'codex_state_missing'
    assert result['metadata']['missing_thread_tracking'] is True
    assert result['metadata']['capture_unverified'] is True
    assert result['metadata']['response_capture_pending'] is False


def test_external_assistant_adapter_treats_browser_input_missing_as_failed_capture() -> None:
    root = _workspace('external_assistant_browser_input_missing')
    url = 'https://chatgpt.com/'

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Just a moment...',
                'response_captured': False,
                'captured_text': '',
                'capture_source': 'browser_dom',
                'browser_profile_dir': str(root / 'profile'),
                'error_message': 'browser_input_missing',
            }

    card = ToolCard(
        tool_id='chatgpt_web_assisted',
        title='ChatGPT web asistido',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'chatgpt',
            'launch_mode': 'web_assisted',
            'response_capture_mode': 'dom_capture',
            'requires_manual_pasteback': False,
            'web_url': url,
            'window_title_hints': ['ChatGPT'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consultar ChatGPT',
        objective='Diagnosticar por que no despega la consulta',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Revisa la causa del atasco')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is False
    assert result['error_message'] == 'browser_input_missing'
    assert result['metadata']['launched'] is True
    assert result['metadata']['response_captured'] is False
    assert result['metadata']['response_capture_pending'] is False
    assert result['metadata']['auto_capture_reason'] == 'browser_input_missing'


def test_external_assistant_adapter_treats_browser_security_verification_as_failed_capture() -> None:
    root = _workspace('external_assistant_browser_security_verification')
    url = 'https://chatgpt.com/'

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'Just a moment...',
                'response_captured': False,
                'captured_text': '',
                'capture_source': 'browser_dom',
                'browser_profile_dir': str(root / 'profile'),
                'error_message': 'browser_security_verification',
            }

    card = ToolCard(
        tool_id='chatgpt_web_assisted',
        title='ChatGPT web asistido',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata={
            'assistant_kind': 'chatgpt',
            'launch_mode': 'web_assisted',
            'response_capture_mode': 'dom_capture',
            'requires_manual_pasteback': False,
            'web_url': url,
            'window_title_hints': ['ChatGPT'],
        },
    )
    adapter = ExternalAssistantToolAdapter(runner_factory=lambda workspace_root: _Runner(workspace_root))
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    task = ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consultar ChatGPT',
        objective='Diagnosticar por que no despega la consulta',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Revisa la causa del atasco')],
    )

    result = adapter.run(card, task, sandbox=False)

    assert result['success'] is False
    assert result['error_message'] == 'browser_security_verification'
    assert result['metadata']['auto_capture_reason'] == 'browser_security_verification'


class _FakeCredentialBroker:
    """Double minimo del CredentialBroker usado en tests de integracion."""

    def __init__(self, *, needs_map: dict[str, bool] | None = None) -> None:
        self._needs = dict(needs_map or {})
        self.requests: list[dict[str, object]] = []

    def needs(self, domain: str) -> bool:
        return bool(self._needs.get(domain, True))

    def request(self, domain: str, reason: str, username_hint: str | None = None) -> None:
        self.requests.append(
            {
                'domain': domain,
                'reason': reason,
                'username_hint': username_hint,
            }
        )


def _login_required_runner_factory():
    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            return {
                'launched': True,
                'focused_title': 'ChatGPT',
                'response_captured': False,
                'captured_text': '',
                'capture_source': 'browser_dom',
                'browser_profile_dir': '',
                'error_message': 'assistant_login_required',
            }

    return lambda workspace_root: _Runner(workspace_root)


def _chatgpt_web_card(**metadata_overrides):
    metadata = {
        'assistant_kind': 'chatgpt',
        'launch_mode': 'web_assisted',
        'response_capture_mode': 'dom_capture',
        'requires_manual_pasteback': False,
        'web_url': 'https://chatgpt.com/',
        'window_title_hints': ['ChatGPT'],
    }
    metadata.update(metadata_overrides)
    return ToolCard(
        tool_id='chatgpt_web_assisted',
        title='ChatGPT web asistido',
        tool_type=ToolType.CUSTOM,
        adapter_key='external_assistant',
        metadata=metadata,
    )


def _chatgpt_task():
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    return ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consultar ChatGPT',
        objective='Diagnosticar por que no despega la consulta',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Revisa la causa del atasco')],
    )


def test_external_assistant_adapter_requests_credentials_when_login_required() -> None:
    adapter = ExternalAssistantToolAdapter(runner_factory=_login_required_runner_factory())
    broker = _FakeCredentialBroker()
    adapter.credential_broker = broker
    card = _chatgpt_web_card()

    result = adapter.run(card, _chatgpt_task(), sandbox=False)

    # El flujo sigue devolviendo success=True con assistant_login_required=True
    # (la ruta queda esperando al usuario), pero ahora el broker recibio la solicitud.
    assert result['success'] is True
    assert result['metadata']['assistant_login_required'] is True
    assert len(broker.requests) == 1
    request = broker.requests[0]
    assert request['domain'] == 'chatgpt.com'
    assert 'ChatGPT' in str(request['reason'])


def test_external_assistant_adapter_skips_credential_request_when_broker_has_credential() -> None:
    adapter = ExternalAssistantToolAdapter(runner_factory=_login_required_runner_factory())
    # Broker ya tiene credencial para chatgpt.com; no debe reabrir el popup.
    broker = _FakeCredentialBroker(needs_map={'chatgpt.com': False})
    adapter.credential_broker = broker
    card = _chatgpt_web_card()

    adapter.run(card, _chatgpt_task(), sandbox=False)

    assert broker.requests == []


def test_external_assistant_adapter_without_broker_does_not_crash_on_login_required() -> None:
    # Escenario legacy: el adapter se construye sin broker inyectado.
    adapter = ExternalAssistantToolAdapter(runner_factory=_login_required_runner_factory())
    assert adapter.credential_broker is None

    result = adapter.run(_chatgpt_web_card(), _chatgpt_task(), sandbox=False)

    assert result['metadata']['assistant_login_required'] is True


def test_external_assistant_adapter_uses_explicit_credential_domain_when_provided() -> None:
    adapter = ExternalAssistantToolAdapter(runner_factory=_login_required_runner_factory())
    broker = _FakeCredentialBroker()
    adapter.credential_broker = broker
    card = _chatgpt_web_card(
        credential_domain='chatgpt.iabv.local',
        credential_username_hint='faber',
    )

    adapter.run(card, _chatgpt_task(), sandbox=False)

    assert len(broker.requests) == 1
    assert broker.requests[0]['domain'] == 'chatgpt.iabv.local'
    assert broker.requests[0]['username_hint'] == 'faber'


def _recording_runner_factory(recorded_calls: list[dict[str, object]]):
    """Runner factory que graba los kwargs pasados y devuelve respuesta capturada."""

    class _Runner:
        def __init__(self, workspace_root: str) -> None:
            self.workspace_root = workspace_root

        def capture_response_from_app(self, **kwargs) -> dict[str, object]:
            recorded_calls.append(dict(kwargs))
            return {
                'launched': True,
                'focused_title': 'ChatGPT',
                'response_captured': True,
                'captured_text': 'respuesta reingesta util',
                'capture_source': 'browser_dom_reingest' if kwargs.get('reingest_only') else 'browser_dom',
                'browser_profile_dir': '',
                'error_message': '',
            }

    return lambda workspace_root: _Runner(workspace_root)


def _chatgpt_task_with_metadata(metadata: dict[str, object]):
    from iabv_v15.domain.models import ToolAction, ToolActionType, ToolTask, TaskRole

    return ToolTask(
        tool_id='chatgpt_web_assisted',
        title='Consultar ChatGPT',
        objective='Diagnosticar por que no despega la consulta',
        requested_by_role=TaskRole.TOOL_USE,
        actions=[ToolAction(action_type=ToolActionType.LLM_QUERY, label='Consulta', value='Revisa la causa del atasco')],
        metadata=dict(metadata),
    )


def test_external_assistant_adapter_forwards_reingest_flag_when_task_requests_reingest() -> None:
    """Cuando el orquestador marca reingest_existing_response en la task, el adapter
    le pide al runner reingest_only=True y desactiva submit_after_paste."""
    calls: list[dict[str, object]] = []
    adapter = ExternalAssistantToolAdapter(runner_factory=_recording_runner_factory(calls))
    task = _chatgpt_task_with_metadata({'reingest_existing_response': True})

    result = adapter.run(_chatgpt_web_card(), task, sandbox=False)

    assert result['success'] is True
    assert len(calls) == 1
    assert calls[0]['reingest_only'] is True
    # Debe saltar el submit automatico cuando solo queremos releer la respuesta.
    assert calls[0]['submit_after_paste'] is False


def test_external_assistant_adapter_forwards_reingest_flag_from_goal_parameters() -> None:
    """El flag tambien se acepta anidado en goal_parameters (camino normal que
    viaja por plan_or_execute -> execute_external_consultation)."""
    calls: list[dict[str, object]] = []
    adapter = ExternalAssistantToolAdapter(runner_factory=_recording_runner_factory(calls))
    task = _chatgpt_task_with_metadata({'goal_parameters': {'reingest_existing_response': True}})

    adapter.run(_chatgpt_web_card(), task, sandbox=False)

    assert calls[0]['reingest_only'] is True
    assert calls[0]['submit_after_paste'] is False


def test_external_assistant_adapter_defaults_reingest_only_to_false() -> None:
    """Sin flag explicito el runner recibe reingest_only=False y submit normal."""
    calls: list[dict[str, object]] = []
    adapter = ExternalAssistantToolAdapter(runner_factory=_recording_runner_factory(calls))

    adapter.run(_chatgpt_web_card(), _chatgpt_task(), sandbox=False)

    assert calls[0]['reingest_only'] is False
    assert calls[0]['submit_after_paste'] is True
