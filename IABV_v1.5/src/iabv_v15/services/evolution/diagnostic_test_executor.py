"""Non-blocking, bounded execution for read-only diagnostic proposals."""
from __future__ import annotations

import inspect
import threading
from concurrent.futures import Future
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import urlopen

from iabv_v15.infra.background_worker_universal import get_background_worker


DiagnosticRunner = Callable[..., dict[str, Any]]
DiagnosticResultHandler = Callable[[dict[str, Any]], None]


class DiagnosticTestExecutor:
    """Starts one local diagnostic at a time and publishes one terminal result."""

    _ALLOWED_TYPES = {'provider_availability'}
    _LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
    _active: dict[str, dict[str, Any]] = {}
    _active_lock = threading.RLock()

    def __init__(self, runner: DiagnosticRunner | None = None) -> None:
        self._runner = runner or self._default_runner

    def start(
        self,
        selected_test: dict[str, Any],
        *,
        session_id: str,
        frame_id: str,
        interaction_id: str = '',
        run_id: str = '',
        on_result: DiagnosticResultHandler | None = None,
    ) -> dict[str, Any]:
        """Schedule a diagnostic and return without waiting for its runner."""
        started = datetime.now(timezone.utc)
        result = self._base_result(selected_test, frame_id, interaction_id, run_id, started)
        reason = self._rejection_reason(selected_test, session_id=session_id, frame_id=frame_id)
        if reason:
            result.update(status='skipped', error=reason)
            finished = self._finish(result, perf_counter())
            self._publish(on_result, finished)
            return {'state': 'skipped', 'deduplication_key': '', 'worker_still_running': False}

        key = self._deduplication_key(session_id, frame_id, result['test_id'])
        with self._active_lock:
            if key in self._active:
                return {
                    'state': 'duplicate_suppressed',
                    'deduplication_key': key,
                    'worker_still_running': True,
                    'duplicate_suppressed': True,
                }

            cancel_event = threading.Event()
            state = {
                'key': key,
                'result': result,
                'started_clock': perf_counter(),
                'cancel_event': cancel_event,
                'on_result': on_result,
                'timed_out': False,
                'published': False,
                'timer': None,
                'future': None,
            }
            self._active[key] = state

            timeout_seconds = float(selected_test.get('timeout_seconds') or 2.0)
            observed_condition = selected_test.get('observed_condition', 'provider_available')  # P0.20g
            future = get_background_worker().submit_json_operation(
                self._invoke_runner,
                str(selected_test['target']),
                timeout_seconds,
                cancel_event,
                observed_condition,  # P0.20g: Pass observed_condition to runner
            )
            state['future'] = future
            timer = threading.Timer(timeout_seconds, self._timeout, args=(key,))
            timer.daemon = True
            state['timer'] = timer
            timer.start()
            future.add_done_callback(lambda done, diagnostic_key=key: self._complete(diagnostic_key, done))

        return {'state': 'running', 'deduplication_key': key, 'worker_still_running': True}

    def _timeout(self, key: str) -> None:
        callback: DiagnosticResultHandler | None = None
        result: dict[str, Any] | None = None
        with self._active_lock:
            state = self._active.get(key)
            if state is None or state['published']:
                return
            future = state['future']
            if isinstance(future, Future) and future.done():
                return
            state['timed_out'] = True
            state['cancel_event'].set()
            if isinstance(future, Future):
                future.cancel()
            result = dict(state['result'])
            result.update(
                status='timeout',
                error='diagnostic_timeout',
                timed_out=True,
                worker_still_running=True,
                cooperative_cancel_requested=True,
            )
            result = self._finish(result, state['started_clock'])
            state['published'] = True
            callback = state['on_result']
        self._publish(callback, result)

    def _complete(self, key: str, future: Future[Any]) -> None:
        callback: DiagnosticResultHandler | None = None
        result: dict[str, Any] | None = None
        with self._active_lock:
            state = self._active.get(key)
            if state is None:
                return
            timer = state.get('timer')
            if isinstance(timer, threading.Timer):
                timer.cancel()
            if not state['published']:
                try:
                    observation = future.result()
                except Exception as exc:  # defensive: worker normally returns None on error
                    observation = {'status': 'failed', 'error': str(exc)[:240]}
                result = dict(state['result'])
                if isinstance(observation, dict):
                    result.update(
                        status=str(observation.get('status') or 'unavailable'),
                        evidence=list(observation.get('evidence') or [])[:4],
                        error=str(observation.get('error') or '')[:240],
                    )
                    # P0.20d: Preserve actual_result if present in observation
                    if observation.get('actual_result'):
                        result['actual_result'] = observation['actual_result']
                else:
                    result.update(status='failed', error='diagnostic_runner_failed')
                result = self._finish(result, state['started_clock'])
                state['published'] = True
                callback = state['on_result']
            self._active.pop(key, None)
        if result is not None:
            self._publish(callback, result)

    def _invoke_runner(
        self,
        target: str,
        timeout_seconds: float,
        cancel_event: threading.Event,
        observed_condition: str,  # P0.20h: No default - must be provided
    ) -> dict[str, Any]:
        if cancel_event.is_set():
            return {'status': 'timeout', 'error': 'diagnostic_cancelled'}
        try:
            signature = inspect.signature(self._runner)
            parameters = list(signature.parameters.values())
            accepts_cancel = (
                'cancel_event' in signature.parameters
                or any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters)
                or len([parameter for parameter in parameters if parameter.kind in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                }]) >= 3
            )
            accepts_observed_condition = 'observed_condition' in signature.parameters  # P0.20g
        except (TypeError, ValueError):
            accepts_cancel = False
            accepts_observed_condition = False  # P0.20g

        if accepts_cancel and accepts_observed_condition:
            return self._runner(target, timeout_seconds, cancel_event, observed_condition)
        elif accepts_cancel:
            return self._runner(target, timeout_seconds, cancel_event)
        elif accepts_observed_condition:
            return self._runner(target, timeout_seconds, observed_condition)
        return self._runner(target, timeout_seconds)

    @classmethod
    def _rejection_reason(cls, selected_test: dict[str, Any], *, session_id: str, frame_id: str) -> str:
        if not session_id or not frame_id or not selected_test.get('test_id'):
            return 'trace_identity_required'
        if selected_test.get('status') != 'proposed':
            return 'proposal_not_pending'
        if not selected_test.get('diagnostic') or not selected_test.get('read_only'):
            return 'diagnostic_read_only_required'
        if selected_test.get('requires_approval') is not False:
            return 'approval_free_required'
        if str(selected_test.get('test_type') or '') not in cls._ALLOWED_TYPES:
            return 'test_type_not_allowed'
        # P0.20h: Reject tests without mandatory observed_condition
        if not selected_test.get('observed_condition'):
            return 'observed_condition_required'
        parsed = urlparse(str(selected_test.get('target') or ''))
        if parsed.scheme not in {'http', 'https'} or parsed.hostname not in cls._LOCAL_HOSTS:
            return 'local_target_required'
        return ''

    @staticmethod
    def _deduplication_key(session_id: str, frame_id: str, test_id: str) -> str:
        return f'{session_id}:{frame_id}:{test_id}'

    @staticmethod
    def _default_runner(
        target: str,
        timeout_seconds: float,
        cancel_event: threading.Event,
        observed_condition: str,  # P0.20h: No default - must be provided
    ) -> dict[str, Any]:
        if cancel_event.is_set():
            return {'status': 'timeout', 'error': 'diagnostic_cancelled'}
        try:
            with urlopen(target, timeout=timeout_seconds) as response:
                if cancel_event.is_set():
                    return {'status': 'timeout', 'error': 'diagnostic_cancelled'}
                # P0.20c: Produce structured actual_result comparable with expected_result
                # P0.20f: Separate actual_result from raw_evidence to satisfy strict verification contract
                # P0.20g: Use observed_condition from selected_test instead of hardcoded semantic
                # actual_result contains only condition + observed for verification
                # raw_evidence is preserved at result level for traceability
                is_available = 200 <= response.status < 400
                raw_evidence = f'http_status:{response.status}'
                return {
                    'status': 'success',
                    'evidence': [raw_evidence],
                    'raw_evidence': raw_evidence,  # P0.20f: Preserve raw evidence at result level
                    'actual_result': {
                        'condition': observed_condition,  # P0.20g: Use explicit observed_condition
                        'observed': is_available,
                    }
                }
        except TimeoutError:
            return {'status': 'timeout', 'error': 'diagnostic_timeout'}
        except Exception as exc:
            return {'status': 'unavailable', 'error': str(exc)}

    @staticmethod
    def _base_result(selected_test: dict[str, Any], frame_id: str, interaction_id: str, run_id: str, started: datetime) -> dict[str, Any]:
        return {
            'test_id': str(selected_test.get('test_id') or ''),
            'frame_id': frame_id,
            'interaction_id': interaction_id,
            'run_id': run_id,
            'status': 'unavailable',
            'duration_ms': 0,
            'evidence': [],
            'error': '',
            'started_at': started.isoformat(),
            'finished_at': '',
        }

    @staticmethod
    def _finish(result: dict[str, Any], start_clock: float) -> dict[str, Any]:
        result['duration_ms'] = int((perf_counter() - start_clock) * 1000)
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        return result

    @staticmethod
    def _publish(callback: DiagnosticResultHandler | None, result: dict[str, Any] | None) -> None:
        if callback is None or result is None:
            return
        try:
            callback(result)
        except Exception:
            # Persistence failure cannot cause a second diagnostic execution.
            return
