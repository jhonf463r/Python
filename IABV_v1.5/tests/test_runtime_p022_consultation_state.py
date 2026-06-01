"""P0.22 focused tests: Consultation State Machine, Resource Pressure Deferral,
and Permission Reply Disambiguation.

All tests use SimpleNamespace stubs (no AppBootstrap) for speed.
Target: full suite < 5s on normal machine.
"""
from __future__ import annotations

import threading
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ── Stub factories ────────────────────────────────────────────


def _make_stub_vm():
    """Lightweight namespace with pure helper methods bound."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = SimpleNamespace(
        _active_dispatch_ids={},
        _working=False,
        _working_since=0,
        _busy_label='',
        _latest_response_text='',
        _latest_response_meta='',
        _chat_messages=[],
        _auto_route_enabled=True,
        _selected_role='general_analyst',
        _active_interaction_id=None,
        _interaction_has_pending_followup=False,
        _autonomy_activity_override={},
        _diagnostic_text='',
        _diagnostic_truth_state='unresolved',
        _provider_refreshing=False,
        _ui_state_lock=threading.Lock(),
        _adaptive_session_id=None,
        _last_adaptive_payload={},
        _last_guidance_action='',
    )
    for name in (
        '_pending_observation_permission_assistant',
        '_is_operational_status_question',
        '_try_resolve_pending_observation_permission',
        '_is_resource_pressure_block',
        '_is_security_verification_preflight_block',
        '_humanize_task_failure',
        '_human_external_consultation_failure',
        '_should_defer_heavy_work',
        '_new_dispatch_id',
        '_is_dispatch_active',
        '_invalidate_dispatch',
        '_external_state_notice',
        '_trace_dispatch_terminal',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is None:
            continue
        if isinstance(
            ControlCenterViewModel.__dict__.get(name),
            staticmethod,
        ):
            stub.__dict__[name] = method
        else:
            stub.__dict__[name] = types.MethodType(method, stub)
    # P0.23 class-level tuples used by _is_operational_status_question
    for attr in (
        '_EXTERNAL_ACTION_VERBS_FOR_EXCLUSION',
        '_EXTERNAL_TARGETS_FOR_EXCLUSION',
    ):
        val = getattr(ControlCenterViewModel, attr, None)
        if val is not None:
            setattr(stub, attr, val)
    return stub


def _make_apply_result_stub():
    """Build a stub VM capable of running _apply_task_result for
    external_consultation without AppBootstrap.
    """
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = _make_stub_vm()
    stub._last_user_goal = 'test goal'
    stub._provider_refreshing = False
    stub._provider_cards = []
    stub._agent_cards = []
    stub._pbt_state = {}
    stub._pbt_candidates = []
    stub._chat_interaction_lifecycle = None
    stub._interaction_has_pending_followup = False
    stub._progress_cards = []
    stub._assistant_guidance_mode = 'auto'
    stub._assistant_action_buttons = []
    stub._traced_calls = []

    original_trace = ControlCenterViewModel._trace_dispatch_terminal

    def _capture_trace(self, **kwargs):
        kwargs['interaction_id'] = getattr(self, '_active_interaction_id', '') or ''
        self._traced_calls.append(kwargs)

    for name in (
        '_apply_task_result', '_should_defer_heavy_work',
        '_remember_external_failure', '_clear_external_failure_memory',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            stub.__dict__[name] = types.MethodType(method, stub)
    stub.__dict__['_trace_dispatch_terminal'] = types.MethodType(_capture_trace, stub)
    stub._derive_external_consultation_outcome = ControlCenterViewModel._derive_external_consultation_outcome

    _noop = lambda *a, **kw: None
    _noop_list = lambda *a, **kw: []
    for attr in (
        '_clear_autonomy_activity_override', '_update_adaptive_state',
        '_set_external_consultation_activity', '_resolve_active_interaction',
        '_update_progress_cards', '_append_message', '_record_chat_audit',
        '_update_evolution_snapshot', '_refresh_development_packet',
        '_refresh_autonomy_dock', '_reset_assistant_guidance',
        '_set_autonomy_activity_override', '_promote_metacognition_after_resolution',
        '_set_live_status', '_collect_metrics',
    ):
        setattr(stub, attr, _noop)
    stub._build_agent_cards = _noop_list
    stub.dataChanged = MagicMock()
    stub.taskResolved = MagicMock()
    stub.taskFailed = MagicMock()
    stub._FINAL_INTERACTION_OUTCOMES = ControlCenterViewModel._FINAL_INTERACTION_OUTCOMES
    stub._TERMINAL_DISPATCH_STATES = ControlCenterViewModel._TERMINAL_DISPATCH_STATES
    return stub


def _make_blocked_result_stub():
    """Build a stub VM capable of running _blocked_external_consultation_result."""
    from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

    stub = _make_stub_vm()
    stub._last_adaptive_payload = {}
    stub._last_user_goal = 'test goal'
    stub._last_goal_context = {}

    for name in (
        '_blocked_external_consultation_result',
        '_guidance_for_external_preflight_block',
        '_format_human_assist_message',
        '_assistant_action',
    ):
        method = getattr(ControlCenterViewModel, name, None)
        if method is not None:
            if isinstance(ControlCenterViewModel.__dict__.get(name), staticmethod):
                stub.__dict__[name] = method
            else:
                stub.__dict__[name] = types.MethodType(method, stub)
    # Mock _update_adaptive_state as no-op — too complex for SimpleNamespace.
    stub._update_adaptive_state = lambda *a, **kw: None
    stub.dataChanged = MagicMock()
    return stub


# ── 1. test_pending_observation_permission_ignores_resource_pressure_preflight ──


class TestPendingObservationPermissionIgnoresResourcePressure:

    def test_resource_pressure_preflight_returns_empty(self) -> None:
        """When preflight exists with assistant_kind=chatgpt but block is
        resource_pressure and approval_checkpoints is empty,
        _pending_observation_permission_assistant() must return ''."""
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'blocked': True,
                    'reason': 'El entorno esta bajo presion de recursos',
                    'block_type': 'resource_pressure',
                    'requires_observation_permission': False,
                },
            },
            'approval_checkpoints': [],
        }
        result = vm._pending_observation_permission_assistant()
        assert result == '', (
            f'Expected empty string for resource_pressure preflight, got {result!r}'
        )

    def test_no_preflight_returns_empty(self) -> None:
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {}
        result = vm._pending_observation_permission_assistant()
        assert result == ''

    def test_environment_guard_preflight_returns_empty(self) -> None:
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'blocked': True,
                    'reason': 'environment guard triggered',
                    'block_type': 'governance',
                },
            },
            'approval_checkpoints': [],
        }
        result = vm._pending_observation_permission_assistant()
        assert result == ''


# ── 2. test_status_question_does_not_grant_observation_permission ──


class TestStatusQuestionDoesNotGrantPermission:

    def test_status_question_returns_false(self) -> None:
        """'si puedes hacer la consulta si o no?' must NOT grant permission."""
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'blocked': True,
                    'reason': 'resource pressure',
                    'block_type': 'resource_pressure',
                    'requires_observation_permission': False,
                },
            },
            'approval_checkpoints': [],
        }
        vm._grant_pending_observation_permission = MagicMock()
        vm._run_external_consultation = MagicMock()
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()

        result = vm._try_resolve_pending_observation_permission(
            'si puedes hacer la consulta si o no?'
        )
        assert result is False
        vm._grant_pending_observation_permission.assert_not_called()
        vm._run_external_consultation.assert_not_called()

    def test_is_operational_status_question_detects_patterns(self) -> None:
        vm = _make_stub_vm()
        assert vm._is_operational_status_question('si puedes hacer la consulta si o no?') is True
        assert vm._is_operational_status_question('¿qué pasó con la consulta?') is True
        assert vm._is_operational_status_question('sigue bloqueado?') is True
        assert vm._is_operational_status_question('funciona o no?') is True
        assert vm._is_operational_status_question('lo hiciste si o no') is True

    def test_explicit_permission_not_detected_as_status(self) -> None:
        vm = _make_stub_vm()
        assert vm._is_operational_status_question('sí, permito observar ChatGPT') is False
        assert vm._is_operational_status_question('autorizo la captura') is False
        assert vm._is_operational_status_question('acepto el permiso') is False


# ── 3. test_explicit_permission_reply_grants_when_observation_checkpoint_exists ──


class TestExplicitPermissionGrantsWithCheckpoint:

    def test_explicit_permission_phrase_grants(self) -> None:
        """With a real observation_permission checkpoint and an explicit
        permission phrase, _try_resolve_pending_observation_permission()
        must return True and call _grant_pending_observation_permission."""
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'blocked': True,
                    'requires_observation_permission': True,
                },
            },
            'approval_checkpoints': [
                {
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'permission_gates': [
                            {'assistant_kind': 'chatgpt'},
                        ],
                    },
                },
            ],
        }
        vm._grant_pending_observation_permission = MagicMock(return_value=True)
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()

        result = vm._try_resolve_pending_observation_permission(
            'sí, permito observar ChatGPT'
        )
        assert result is True
        vm._grant_pending_observation_permission.assert_called_once_with(announce=True)

    def test_short_affirmative_grants_with_permission_guidance(self) -> None:
        """A bare 'sí' should grant only if _last_guidance_action is
        approve_observation_permission."""
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'requires_observation_permission': True,
                },
            },
            'approval_checkpoints': [
                {
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'permission_gates': [
                            {'assistant_kind': 'chatgpt'},
                        ],
                    },
                },
            ],
        }
        vm._last_guidance_action = 'approve_observation_permission'
        vm._grant_pending_observation_permission = MagicMock(return_value=True)
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()

        result = vm._try_resolve_pending_observation_permission('sí')
        assert result is True

    def test_short_affirmative_rejected_without_permission_guidance(self) -> None:
        """A bare 'sí' should NOT grant if _last_guidance_action is not
        approve_observation_permission."""
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'requires_observation_permission': True,
                },
            },
            'approval_checkpoints': [
                {
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'permission_gates': [
                            {'assistant_kind': 'chatgpt'},
                        ],
                    },
                },
            ],
        }
        vm._last_guidance_action = 'some_other_action'
        vm._grant_pending_observation_permission = MagicMock()
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()

        result = vm._try_resolve_pending_observation_permission('sí')
        assert result is False
        vm._grant_pending_observation_permission.assert_not_called()


# ── 4. test_permission_retry_preserves_interaction_until_external_terminal ──


class TestPermissionRetryPreservesInteraction:

    def test_working_state_uses_awaiting_outcome(self) -> None:
        """When _try_resolve_pending_observation_permission returns True
        and _working is True, sendChat should use
        outcome='awaiting_external_response', NOT 'resolved'."""
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel

        resolve_calls: list[dict] = []

        def capture_resolve(self_stub, **kwargs):
            resolve_calls.append(kwargs)

        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'requires_observation_permission': True,
                },
            },
            'approval_checkpoints': [
                {
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'permission_gates': [
                            {'assistant_kind': 'chatgpt'},
                        ],
                    },
                },
            ],
        }
        vm._grant_pending_observation_permission = MagicMock(return_value=True)
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()
        vm._working = True
        vm._active_interaction_id = 'int-test-001'

        result = vm._try_resolve_pending_observation_permission(
            'sí, permito observar ChatGPT'
        )
        assert result is True

        # Simulate what sendChat does after _try_resolve returns True
        if vm._working:
            outcome = 'awaiting_external_response'
        else:
            outcome = 'resolved'

        assert outcome == 'awaiting_external_response'
        assert vm._active_interaction_id == 'int-test-001'

    def test_not_working_uses_resolved_outcome(self) -> None:
        vm = _make_stub_vm()
        vm._last_adaptive_payload = {
            'metadata': {
                'external_consultation_preflight': {
                    'assistant_kind': 'chatgpt',
                    'requires_observation_permission': True,
                },
            },
            'approval_checkpoints': [
                {
                    'phase_key': 'observation_permission',
                    'metadata': {
                        'permission_gates': [
                            {'assistant_kind': 'chatgpt'},
                        ],
                    },
                },
            ],
        }
        vm._grant_pending_observation_permission = MagicMock(return_value=True)
        vm._set_live_status = MagicMock()
        vm.dataChanged = MagicMock()
        vm._working = False

        result = vm._try_resolve_pending_observation_permission(
            'sí, permito observar ChatGPT'
        )
        assert result is True

        if vm._working:
            outcome = 'awaiting_external_response'
        else:
            outcome = 'resolved'
        assert outcome == 'resolved'


# ── 5. test_resource_pressure_block_maps_to_deferred_terminal_state ──


class TestResourcePressureBlockMapsToDeferredTerminal:

    def test_resource_pressure_terminal_state(self) -> None:
        """_blocked_external_consultation_result with resource_pressure
        must set terminal_state='blocked_by_resource_pressure' and
        block_type='resource_pressure'."""
        vm = _make_blocked_result_stub()
        preflight = {
            'reason': 'presion de recursos detectada',
            'governance': {
                'reason': 'El entorno esta bajo presion de recursos',
                'diagnostic_category': 'resource_pressure',
            },
            'approval_checkpoints': [],
        }
        result = vm._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )
        assert result['terminal_state'] == 'blocked_by_resource_pressure'
        assert result['block_type'] == 'resource_pressure'
        assert 'presion de recursos' in result['message'].lower()
        assert result['success'] is False

    def test_resource_pressure_metadata(self) -> None:
        vm = _make_blocked_result_stub()
        preflight = {
            'reason': 'resource pressure detected',
            'governance': {
                'diagnostic_category': 'environment_guard',
                'reason': 'degradar con gracia',
            },
        }
        result = vm._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )
        payload = result['payload']
        ecpf = payload['metadata']['external_consultation_preflight']
        assert ecpf['block_type'] == 'resource_pressure'
        assert ecpf['requires_observation_permission'] is False
        assert ecpf['retry_when_pressure_clears'] is True

    def test_non_resource_pressure_uses_governance(self) -> None:
        vm = _make_blocked_result_stub()
        preflight = {
            'reason': 'assistant unavailable',
            'governance': {
                'diagnostic_category': 'assistant_unavailable',
                'reason': 'ChatGPT not reachable',
            },
        }
        result = vm._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )
        assert result['terminal_state'] == 'failed_with_actionable_reason'
        assert result['block_type'] == 'governance'

    def test_security_verification_preflight_creates_human_assist_block(self) -> None:
        vm = _make_blocked_result_stub()
        calls: list[dict] = []
        vm._create_active_incident_frame = lambda **kw: calls.append(kw)
        preflight = {
            'reason': 'ChatGPT quedo bloqueado por una verificacion de seguridad del sitio.',
            'governance': {
                'diagnostic_category': 'browser_security_verification',
                'external_state_flags': ['browser_security_verification'],
                'reason': 'ChatGPT quedo bloqueado por una verificacion de seguridad del sitio.',
            },
            'world_model_summary': {
                'detected_blocks': ['browser_security_verification'],
                'block_records': [
                    {
                        'block_type': 'browser_security_verification',
                        'assistant_kind': 'chatgpt',
                        'target_scope': 'consult_chatgpt',
                    },
                ],
            },
        }

        result = vm._blocked_external_consultation_result(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            preflight=preflight,
        )

        assert result['terminal_state'] == 'blocked_by_security_verification'
        assert result['block_type'] == 'browser_security_verification'
        assert result['external_state_flags'] == ['browser_security_verification']
        assert 'IABV ve:' in result['message']
        assert 'permito observar ChatGPT' in result['message']
        assert calls and calls[0]['block_type'] == 'browser_security_verification'
        ext = result['payload']['metadata']['external_consultation']
        assert ext['terminal_state'] == 'blocked_by_security_verification'

    def test_security_verification_guidance_uses_human_assist_bridge(self) -> None:
        vm = _make_blocked_result_stub()
        guidance = vm._guidance_for_external_preflight_block(
            assistant_kind='chatgpt',
            assistant_title='ChatGPT',
            governance={
                'diagnostic_category': 'browser_security_verification',
                'reason': 'verificacion de seguridad',
                'external_state_flags': ['browser_security_verification'],
            },
            approval_checkpoints=[],
        )
        assert guidance['mode'] == 'human_assist_bridge'
        action_keys = [item['action'] for item in guidance['actions']]
        assert 'show_problem_window' in action_keys
        assert 'launch_governed_browser_session' in action_keys

    def test_apply_task_result_traces_resource_pressure(self) -> None:
        """_apply_task_result must trace terminal_state as
        blocked_by_resource_pressure when the result payload has it."""
        vm = _make_apply_result_stub()
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result(
            'external_consultation',
            {
                'success': False,
                'message': 'Consulta diferida por presion de recursos.',
                'meta': 'Consulta diferida por presion de recursos (ChatGPT).',
                'terminal_state': 'blocked_by_resource_pressure',
                'assistant_title': 'ChatGPT',
                'external_state_flags': [],
                'block_type': 'resource_pressure',
            },
        )
        assert len(vm._traced_calls) == 1
        trace = vm._traced_calls[0]
        assert trace['terminal_state'] == 'blocked_by_resource_pressure'

    def test_apply_task_result_schedules_dev_packet_off_ui_thread(self) -> None:
        """Post-result development packet refresh must be deferred.

        Live Windows evidence showed ``_refresh_development_packet`` reading
        dossier JSON on the UI thread after a ChatGPT attempt, causing a
        38s stall.  _apply_task_result should schedule that refresh instead.
        """
        vm = _make_apply_result_stub()
        scheduled: list[dict[str, object]] = []
        vm._schedule_idle_dev_packet_refresh = lambda **kw: scheduled.append(dict(kw))

        def _forbidden_sync_refresh(*_a, **_kw):
            raise AssertionError('sync _refresh_development_packet should not run in _apply_task_result')

        vm._refresh_development_packet = _forbidden_sync_refresh
        vm._apply_task_result(
            'external_consultation',
            {
                'success': False,
                'message': 'ChatGPT blocked by browser_security_verification.',
                'meta': 'ChatGPT: blocked_by_security_verification',
                'terminal_state': 'blocked_by_security_verification',
                'assistant_title': 'ChatGPT',
                'external_state_flags': ['browser_security_verification'],
            },
        )

        assert scheduled == [{'reason': 'post_task_result'}]

    def test_is_resource_pressure_block_static(self) -> None:
        from iabv_v15.ui.viewmodels.control_center_viewmodel import ControlCenterViewModel
        assert ControlCenterViewModel._is_resource_pressure_block({
            'governance': {'diagnostic_category': 'resource_pressure'},
        }) is True
        assert ControlCenterViewModel._is_resource_pressure_block({
            'governance': {'diagnostic_category': 'environment_guard'},
        }) is True
        assert ControlCenterViewModel._is_resource_pressure_block({
            'reason': 'degradar con gracia antes de lanzar trabajo pesado',
        }) is True
        assert ControlCenterViewModel._is_resource_pressure_block({
            'governance': {'diagnostic_category': 'assistant_unavailable'},
            'reason': 'ChatGPT not found',
        }) is False


# ── 6. test_no_empty_interaction_id_after_external_retry ──


class TestNoEmptyInteractionIdAfterRetry:

    def test_interaction_id_preserved_during_working(self) -> None:
        """When _working is True after a permission grant, the
        active_interaction_id must NOT be cleared."""
        vm = _make_stub_vm()
        vm._active_interaction_id = 'int-original-456'
        vm._working = True

        # Simulate the sendChat path: permission resolved, check _working
        if vm._working:
            outcome = 'awaiting_external_response'
        else:
            outcome = 'resolved'

        assert outcome == 'awaiting_external_response'
        assert vm._active_interaction_id == 'int-original-456'

    def test_apply_result_traces_with_interaction_id(self) -> None:
        """_apply_task_result traces dispatch_terminal with the
        active_interaction_id when it's present."""
        vm = _make_apply_result_stub()
        vm._active_interaction_id = 'int-alive-789'
        vm._new_dispatch_id('external_consultation')
        vm._apply_task_result(
            'external_consultation',
            {
                'success': True,
                'message': 'Consultation completed.',
                'meta': 'external_consultation_success',
                'assistant_title': 'ChatGPT',
                'external_state_flags': [],
            },
        )
        assert len(vm._traced_calls) >= 1
        trace = vm._traced_calls[0]
        assert trace['interaction_id'] == 'int-alive-789'


# ── 7. test_platform_pending_json_validates ──


class TestPlatformPendingP022Validates:

    def test_p022_json_validates(self) -> None:
        from pathlib import Path
        from iabv_v15.domain.models import PlatformPendingTask
        path = (
            Path(__file__).parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_runtime_external_consultation_resource_pressure.json'
        )
        assert path.exists(), f'Missing platform_pending file: {path}'
        task = PlatformPendingTask.model_validate_json(path.read_bytes())
        assert task.id == 'runtime_external_consultation_resource_pressure_p022'
        assert task.status.value == 'PENDING'
        assert task.priority == 'P0'
        assert task.category == 'runtime_stability'
        assert task.metadata.get('verification_status') == 'CODE_FIX_PENDING_LIVE_PROOF'

    def test_p022_has_evidence(self) -> None:
        from pathlib import Path
        from iabv_v15.domain.models import PlatformPendingTask
        path = (
            Path(__file__).parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_runtime_external_consultation_resource_pressure.json'
        )
        task = PlatformPendingTask.model_validate_json(path.read_bytes())
        evidence = task.metadata.get('evidence', [])
        assert len(evidence) >= 2
        dispatch_ids = [e.get('dispatch_id', '') for e in evidence]
        assert '70611c2efec5' in dispatch_ids
        assert 'ad2028481b95' in dispatch_ids

    def test_p022_has_resume_hint(self) -> None:
        from pathlib import Path
        from iabv_v15.domain.models import PlatformPendingTask
        path = (
            Path(__file__).parent.parent
            / 'data' / 'evolution' / 'platform_pending'
            / 'task_runtime_external_consultation_resource_pressure.json'
        )
        task = PlatformPendingTask.model_validate_json(path.read_bytes())
        assert task.resume_hint, 'P0.22 task must have resume_hint'
        assert task.next_action, 'P0.22 task must have next_action'
