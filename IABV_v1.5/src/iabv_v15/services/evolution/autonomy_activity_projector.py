from __future__ import annotations

from typing import Any

from iabv_v15.domain.models import canonical_external_state_flags
from iabv_v15.infra.persistence.experiment_lab_repository import ExperimentLabRepository
from iabv_v15.infra.persistence.pending_issue_repository import PendingIssueRepository
from iabv_v15.infra.persistence.tool_record_repository import ToolRecordRepository


class AutonomyActivityProjector:
    ASSISTANT_TOOL_IDS = {
        'codex_installed',
        'chatgpt_installed',
        'chatgpt_web_assisted',
        'claude_installed',
        'claude_web_assisted',
        'ollama_llm',
    }
    ASSISTANT_ORDER = ('codex', 'chatgpt', 'claude', 'ollama')

    def __init__(
        self,
        *,
        tool_record_repository: ToolRecordRepository,
        pending_issue_repository: PendingIssueRepository | None = None,
        experiment_lab_repository: ExperimentLabRepository | None = None,
    ) -> None:
        self.tool_record_repository = tool_record_repository
        self.pending_issue_repository = pending_issue_repository
        self.experiment_lab_repository = experiment_lab_repository

    def project(
        self,
        *,
        goal_context: dict[str, Any] | None = None,
        live_audit: dict[str, Any] | None = None,
        replay_visual_summary: dict[str, Any] | None = None,
        autonomy_activity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        goal = dict(goal_context or {})
        audit = dict(live_audit or {})
        replay = dict(replay_visual_summary or {})
        activity = dict(autonomy_activity or {})
        tasks = [task for task in self.tool_record_repository.list_tasks(limit=36) if self._is_assistant_task(task)]
        latest_results = {task.task_id: self._latest_result(task.task_id) for task in tasks}
        tasks.sort(key=lambda item: self._sort_key(item, latest_results.get(item.task_id)), reverse=True)
        assistant_session_cards = self._assistant_session_cards(tasks, latest_results)
        live_work_items = [self._work_item(task, latest_results.get(task.task_id)) for task in tasks[:6]]
        timeline = self._timeline(tasks, latest_results)
        pending_issue = self._latest_pending_issue()
        experiment = self._latest_experiment(goal)
        return {
            'live_process_summary': self._live_process_summary(
                goal_context=goal,
                live_audit=audit,
                replay_visual_summary=replay,
                autonomy_activity=activity,
                live_work_items=live_work_items,
                pending_issue=pending_issue,
                experiment=experiment,
            ),
            'live_work_items': live_work_items,
            'assistant_session_cards': assistant_session_cards,
            'autonomy_timeline': timeline,
        }

    def _is_assistant_task(self, task: Any) -> bool:
        metadata = dict(getattr(task, 'metadata', {}) or {})
        return metadata.get('consultation_scope') == 'external_assistant' or str(getattr(task, 'tool_id', '') or '') in self.ASSISTANT_TOOL_IDS

    def _latest_result(self, task_id: str) -> Any | None:
        results = self.tool_record_repository.list_results(task_id=task_id, limit=1)
        return results[0] if results else None

    def _assistant_session_cards(self, tasks: list[Any], latest_results: dict[str, Any | None]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for assistant_kind in self.ASSISTANT_ORDER:
            task = next((item for item in tasks if self._assistant_kind(item) == assistant_kind), None)
            if task is None:
                continue
            result = latest_results.get(task.task_id)
            task_metadata = dict(getattr(task, 'metadata', {}) or {})
            execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
            phase = self._phase_snapshot(task, result)
            external_flags = self._external_state_flags(task, result)
            cards.append({
                'assistant_kind': assistant_kind,
                'requested_assistant_kind': self._requested_assistant_kind(task, result),
                'actual_assistant_kind': self._assistant_kind(task),
                'title': self._assistant_title(assistant_kind),
                'status': self._status_label(result),
                'stage': phase['stage'],
                'current_step': phase['current_step'],
                'progress': phase['progress'],
                'progress_pct': phase['progress_pct'],
                'lane': str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or self._lane_for(task, result)),
                'thread_key': str(execution_metadata.get('thread_key') or task_metadata.get('thread_key') or ''),
                'thread_title': str(execution_metadata.get('thread_title') or task_metadata.get('thread_title') or ''),
                'session_label': str(execution_metadata.get('session_label') or task_metadata.get('session_label') or ''),
                'session_scope': str(execution_metadata.get('session_scope') or task_metadata.get('session_scope') or ''),
                'session_profile_dir': str(execution_metadata.get('session_profile_dir') or execution_metadata.get('browser_profile_dir') or task_metadata.get('session_profile_dir') or ''),
                'awaiting_reason': str(execution_metadata.get('awaiting_reason') or task_metadata.get('awaiting_reason') or ''),
                'last_capture_attempt_utc': str(execution_metadata.get('last_capture_attempt_utc') or task_metadata.get('last_capture_attempt_utc') or ''),
                'reused_thread': bool(execution_metadata.get('reused_thread', task_metadata.get('reused_thread', False))),
                'task_id': task.task_id,
                'result_id': getattr(result, 'result_id', ''),
                'detail': str(getattr(result, 'output_text', '') or getattr(getattr(result, 'execution_state', None), 'detail', '') or getattr(task, 'title', '')).strip(),
                'pending_summary': phase['pending_summary'],
                'blocker': phase['blocker'],
                'external_state_flags': external_flags,
                'coherence_flags': self._coherence_flags(task, result),
            })
        return cards

    def _work_item(self, task: Any, result: Any | None) -> dict[str, Any]:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        phase = self._phase_snapshot(task, result)
        external_flags = self._external_state_flags(task, result)
        flags = external_flags or self._coherence_flags(task, result)
        return {
            'task_id': task.task_id,
            'result_id': getattr(result, 'result_id', ''),
            'assistant_kind': self._assistant_kind(task),
            'assistant_title': self._assistant_title(self._assistant_kind(task)),
            'title': str(getattr(task, 'title', '') or getattr(task, 'objective', '') or 'Consulta externa'),
            'stage': phase['stage'],
            'status': self._status_label(result),
            'progress': phase['progress'],
            'progress_pct': phase['progress_pct'],
            'remaining_pct': phase['remaining_pct'],
            'current_step': phase['current_step'],
            'pending_steps': phase['pending_steps'],
            'pending_summary': phase['pending_summary'],
            'lane': str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or self._lane_for(task, result)),
            'detail': str(getattr(result, 'output_text', '') or getattr(getattr(result, 'execution_state', None), 'detail', '') or getattr(task, 'objective', '')).strip(),
            'thread_key': str(execution_metadata.get('thread_key') or task_metadata.get('thread_key') or ''),
            'thread_title': str(execution_metadata.get('thread_title') or task_metadata.get('thread_title') or ''),
            'awaiting_reason': str(execution_metadata.get('awaiting_reason') or task_metadata.get('awaiting_reason') or ''),
            'help': self._help_for(task, result, flags),
            'blocker': phase['blocker'],
            'waiting': self._status_label(result) == 'awaiting_response',
            'external_state_flags': external_flags,
            'coherence_flags': flags,
        }

    def _timeline(self, tasks: list[Any], latest_results: dict[str, Any | None]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for entry in self.tool_record_repository.list_log(limit=24):
            tool_id = str(entry.get('tool_id') or '')
            task_id = str(entry.get('task_id') or '')
            if tool_id not in self.ASSISTANT_TOOL_IDS and task_id not in latest_results:
                continue
            payload = dict(entry.get('payload') or {})
            assistant_kind = str(payload.get('assistant_kind') or payload.get('requested_assistant_kind') or tool_id.split('_')[0] or 'assistant')
            items.append({
                'title': str(entry.get('action_type') or 'evento').replace('_', ' '),
                'detail': str(payload.get('detail') or payload.get('reason') or payload.get('summary') or entry.get('state') or ''),
                'status': str(entry.get('state') or ''),
                'assistant_title': self._assistant_title(assistant_kind),
                'created_at_utc': str(entry.get('created_at_utc') or ''),
            })
            if len(items) >= 8:
                return items
        for task in tasks[:4]:
            result = latest_results.get(task.task_id)
            phase = self._phase_snapshot(task, result)
            items.append({
                'title': phase['current_step'],
                'detail': str(phase['detail'] or getattr(result, 'output_text', '') or getattr(getattr(result, 'execution_state', None), 'detail', '') or getattr(task, 'objective', '')).strip(),
                'status': self._status_label(result),
                'progress_pct': phase['progress_pct'],
                'assistant_title': self._assistant_title(self._assistant_kind(task)),
                'created_at_utc': str((dict(getattr(task, 'metadata', {}) or {}).get('updated_at_utc') or dict(getattr(task, 'metadata', {}) or {}).get('created_at_utc') or '')),
            })
        return items[:8]

    def _live_process_summary(
        self,
        *,
        goal_context: dict[str, Any],
        live_audit: dict[str, Any],
        replay_visual_summary: dict[str, Any],
        autonomy_activity: dict[str, Any],
        live_work_items: list[dict[str, Any]],
        pending_issue: Any | None,
        experiment: dict[str, Any],
    ) -> dict[str, Any]:
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        top_item = live_work_items[0] if live_work_items else {}
        activity_status = str(autonomy_activity.get('status') or '').strip()
        activity_stage = str(autonomy_activity.get('stage') or '').strip()
        activity_detail = str(autonomy_activity.get('detail') or '').strip()
        status = activity_status if activity_status and activity_status != 'idle' else str(top_item.get('status') or 'idle')
        stage = activity_stage if activity_stage and activity_stage not in {'idle', 'sin actividad'} else str(top_item.get('stage') or 'sin actividad')
        summary = activity_detail if activity_detail and status not in {'idle', 'sin actividad'} else str(top_item.get('detail') or 'Sin actividad autonoma reciente.').strip()
        progress_value = float(autonomy_activity.get('progress') or top_item.get('progress') or goal_context.get('progress') or 0.0)
        normalized = max(0.0, min(1.0, progress_value))
        progress_pct = int(round(normalized * 100.0))
        return {
            'status': status,
            'stage': stage,
            'progress': round(normalized, 4),
            'progress_pct': progress_pct,
            'remaining_pct': int(max(0, 100 - progress_pct)),
            'summary': summary,
            'goal_title': str(objective.get('title') or goal_context.get('active_title') or ''),
            'project_title': str(project.get('title') or ''),
            'task_title': str(task.get('title') or ''),
            'assistant_title': str(top_item.get('assistant_title') or autonomy_activity.get('tool') or ''),
            'lane': str(top_item.get('lane') or ''),
            'thread_key': str(top_item.get('thread_key') or ''),
            'thread_title': str(top_item.get('thread_title') or ''),
            'task_id': str(top_item.get('task_id') or ''),
            'result_id': str(top_item.get('result_id') or ''),
            'current_step': str(top_item.get('current_step') or autonomy_activity.get('stage') or 'sin actividad'),
            'pending_steps': list(top_item.get('pending_steps') or []),
            'pending_summary': str(top_item.get('pending_summary') or ''),
            'blocker': str(top_item.get('blocker') or goal_context.get('blocker') or getattr(pending_issue, 'summary', '') or ''),
            'human_help': str(autonomy_activity.get('human_help') or top_item.get('help') or live_audit.get('decision', {}).get('human_help') or '').strip(),
            'latest_experiment': str(experiment.get('summary') or 'Sin experimentos externos recientes.'),
            'audit_status': str(live_audit.get('status') or replay_visual_summary.get('metadata', {}).get('audit_status') or ''),
            'replay_alignment': float(replay_visual_summary.get('metadata', {}).get('visual_alignment_score') or 0.0),
            'confidence': float(goal_context.get('confidence') or 0.0),
        }

    def _latest_pending_issue(self) -> Any | None:
        if self.pending_issue_repository is None:
            return None
        issues = self.pending_issue_repository.list_recent(limit=1)
        return issues[0] if issues else None

    def _latest_experiment(self, goal_context: dict[str, Any]) -> dict[str, Any]:
        if self.experiment_lab_repository is None:
            return {}
        for subject_key in self._subject_candidates(goal_context):
            recommendations = self.experiment_lab_repository.list_recommendations(subject_key=subject_key, limit=1)
            if recommendations:
                item = recommendations[0]
                return {'summary': f'{subject_key}: recomendada {item.recommended_route.value} con score {item.score:.2f}', 'subject_key': subject_key}
            runs = self.experiment_lab_repository.list_runs(subject_key=subject_key, limit=1)
            if runs:
                item = runs[0]
                return {'summary': f'{subject_key}: ultima via {item.route.value} con score {item.metrics.total_score:.2f}', 'subject_key': subject_key}
        runs = self.experiment_lab_repository.list_runs(limit=1)
        if not runs:
            return {}
        item = runs[0]
        return {'summary': f'{item.subject_key}: ultima via {item.route.value} con score {item.metrics.total_score:.2f}', 'subject_key': item.subject_key}

    def _subject_candidates(self, goal_context: dict[str, Any]) -> list[str]:
        objective = dict(goal_context.get('objective') or {})
        project = dict(goal_context.get('project') or {})
        task = dict(goal_context.get('task') or {})
        metadata = dict(goal_context.get('metadata') or {})
        candidates: list[str] = []
        for value in (task.get('title'), project.get('title'), objective.get('title'), metadata.get('site_id')):
            normalized = self._slug(str(value or ''))
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        return candidates

    def _assistant_kind(self, task: Any) -> str:
        metadata = dict(getattr(task, 'metadata', {}) or {})
        actual = str(metadata.get('actual_assistant_kind') or '').strip().lower()
        if actual:
            return actual
        assistant = str(metadata.get('assistant_kind') or '').strip().lower()
        if assistant:
            return assistant
        return self._assistant_family_for_tool_id(str(getattr(task, 'tool_id', '') or '')) or 'assistant'

    def _assistant_title(self, assistant_kind: str) -> str:
        return {'codex': 'Codex', 'chatgpt': 'ChatGPT', 'claude': 'Claude', 'ollama': 'Ollama'}.get(str(assistant_kind or '').strip().lower(), 'Asistente')

    def _lane_for(self, task: Any, result: Any | None) -> str:
        metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        capture_mode = str(execution_metadata.get('response_capture_mode') or metadata.get('response_capture_mode') or '').strip().lower()
        background_mode = str(execution_metadata.get('background_capture_mode') or metadata.get('background_capture_mode') or '').strip().lower()
        if capture_mode in {'tool_result', 'direct_text', 'dom_capture', 'browser_dom'} or background_mode in {'browser_dom', 'codex_rollout'}:
            return 'background'
        if capture_mode == 'clipboard_capture':
            return 'app'
        return 'manual'

    def _status_label(self, result: Any | None) -> str:
        if result is None:
            return 'idle'
        state = str(getattr(getattr(result, 'execution_state', None), 'state', '') or '').strip()
        if state == 'awaiting_response':
            return 'awaiting_response'
        if state in {'failed', 'blocked', 'adapter_missing'} or not bool(getattr(result, 'success', False)):
            return 'blocked'
        if str(getattr(getattr(result, 'validation_status', None), 'value', '') or '') == 'unvalidated':
            return 'warning'
        return 'active'

    def _stage_label(self, task: Any, result: Any | None) -> str:
        return self._phase_snapshot(task, result)['stage']

    def _progress_for(self, task: Any, result: Any | None) -> float:
        return self._phase_snapshot(task, result)['progress']

    def _help_for(self, task: Any, result: Any | None, flags: list[str]) -> str:
        metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        if flags:
            return ' | '.join(flags)
        focused_title = str(execution_metadata.get('focused_title') or '').strip()
        if execution_metadata.get('auto_capture_reason') == 'browser_input_missing' and focused_title:
            return f'La sesion aislada quedo en "{focused_title}" y aun no aparecio el input del chat especial.'
        if execution_metadata.get('assistant_login_required'):
            return 'La sesion aislada necesita login una sola vez.'
        if execution_metadata.get('response_capture_pending'):
            return str(execution_metadata.get('awaiting_reason') or metadata.get('awaiting_reason') or 'Deja a IABV seguir capturando en segundo plano.')
        return str(execution_metadata.get('detail') or metadata.get('selector_reason') or '')

    def _coherence_flags(self, task: Any, result: Any | None) -> list[str]:
        flags: list[str] = []
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        goal_parameters = dict(task_metadata.get('goal_parameters') or {})
        requested_assistant = self._requested_assistant_kind(task, result)
        actual_assistant = str(execution_metadata.get('assistant_kind') or task_metadata.get('assistant_kind') or '').strip().lower()
        tool_family = self._assistant_family_for_tool_id(str(getattr(task, 'tool_id', '') or ''))
        if requested_assistant and actual_assistant and requested_assistant != actual_assistant and requested_assistant not in {'local', 'local_first'}:
            flags.append('la familia solicitada no coincide con la familia ejecutada')
        if requested_assistant and tool_family and requested_assistant not in {tool_family, 'local', 'local_first'}:
            flags.append('familia de asistente no coincide con la herramienta')
        lane = str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or self._lane_for(task, result))
        thread_key = str(execution_metadata.get('thread_key') or task_metadata.get('thread_key') or '').strip()
        thread_title = str(execution_metadata.get('thread_title') or task_metadata.get('thread_title') or '').strip()
        session_scope = str(execution_metadata.get('session_scope') or task_metadata.get('session_scope') or '').strip()
        session_profile_dir = str(execution_metadata.get('session_profile_dir') or execution_metadata.get('browser_profile_dir') or task_metadata.get('session_profile_dir') or '').strip()
        thread_family = self._assistant_family_from_text(' '.join(part for part in (thread_key, thread_title) if part))
        prompt_family = self._assistant_family_from_text(str(task_metadata.get('context_pack') or goal_parameters.get('context_pack') or ''))
        if thread_family and tool_family and thread_family != tool_family:
            flags.append('el hilo dedicado apunta a otra familia de asistente')
        if prompt_family and requested_assistant and prompt_family != requested_assistant:
            flags.append('el prompt externo fue redactado para otra familia')
        if lane in {'background', 'app'} and session_scope in {'program_chat', 'external_app'} and not thread_key:
            flags.append('seguimiento de hilo faltante')
        if session_scope == 'program_chat' and not session_profile_dir:
            flags.append('sesion aislada sin perfil persistente')
        capture_mode = str(execution_metadata.get('response_capture_mode') or task_metadata.get('response_capture_mode') or '').strip().lower()
        if execution_metadata.get('response_capture_pending') and capture_mode == 'manual_pasteback':
            flags.append('caida prematura a lane manual')
        autonomous = dict((dict(getattr(result, 'metadata', {}) or {})).get('autonomous_consultation') or {})
        if autonomous.get('response_ingested') and not bool(execution_metadata.get('response_captured')) and capture_mode not in {'tool_result', 'direct_text'}:
            flags.append('aprendizaje marcado sin captura valida')
        if execution_metadata.get('auto_capture_reason') == 'browser_input_missing' and str(execution_metadata.get('focused_title') or '').strip():
            flags.append('la sesion aislada no llego al chat util del asistente')
        return flags

    def _external_state_flags(self, task: Any, result: Any | None) -> list[str]:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        result_metadata = dict(getattr(result, 'metadata', {}) or {}) if result is not None else {}
        autonomous = dict(result_metadata.get('autonomous_consultation') or {})
        ia_trace = dict(
            result_metadata.get('ia_trace_entry')
            or execution_metadata.get('ia_trace_entry')
            or task_metadata.get('ia_trace_entry')
            or autonomous.get('ia_trace_entry')
            or {}
        )
        return canonical_external_state_flags(
            list(task_metadata.get('external_state_flags') or [])
            + list(execution_metadata.get('external_state_flags') or [])
            + list(result_metadata.get('external_state_flags') or [])
            + list(autonomous.get('external_state_flags') or [])
            + list(ia_trace.get('external_state_flags') or [])
        )

    def _phase_snapshot(self, task: Any, result: Any | None) -> dict[str, Any]:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_state = getattr(result, 'execution_state', None)
        execution_metadata = dict(getattr(execution_state, 'metadata', {}) or {})
        lane = str(execution_metadata.get('capture_lane') or task_metadata.get('capture_lane') or self._lane_for(task, result))
        steps = self._step_plan(lane)
        state = str(getattr(execution_state, 'state', '') or '').strip().lower()
        result_metadata = dict(getattr(result, 'metadata', {}) or {}) if result is not None else {}
        autonomous = dict(result_metadata.get('autonomous_consultation') or {})
        response_ingested = bool(autonomous.get('response_ingested'))
        response_captured = bool(execution_metadata.get('response_captured'))
        response_pending = bool(execution_metadata.get('response_capture_pending'))
        validation_status = str(getattr(getattr(result, 'validation_status', None), 'value', '') or '').strip().lower() if result is not None else ''
        auto_reason = str(execution_metadata.get('auto_capture_reason') or '').strip().lower()
        focused_title = str(execution_metadata.get('focused_title') or '').strip()
        detail = str(getattr(result, 'output_text', '') or getattr(execution_state, 'detail', '') or getattr(task, 'objective', '')).strip()
        blocker = ''
        stage = 'decidiendo ruta'
        phase_index = 0

        if result is None:
            progress = 0.08
        elif state in {'failed', 'blocked', 'adapter_missing'}:
            stage = 'bloqueado'
            phase_index = 1 if len(steps) > 1 else 0
            blocker = str(getattr(result, 'error_message', '') or getattr(execution_state, 'detail', '') or task_metadata.get('awaiting_reason') or 'La consulta no pudo avanzar.')
            progress = 0.32
        elif response_ingested or validation_status == 'approved':
            stage = 'aprendizaje consolidado'
            phase_index = len(steps) - 1
            progress = 1.0
        elif response_captured:
            stage = 'respuesta capturada'
            phase_index = max(len(steps) - 3, 0)
            progress = 0.78
        elif state in {'executed', 'approved'}:
            stage = 'validando aprendizaje'
            phase_index = max(len(steps) - 2, 0)
            progress = 0.9 if validation_status != 'approved' else 0.96
        elif state == 'awaiting_response' or response_pending:
            if execution_metadata.get('assistant_login_required'):
                stage = 'esperando login'
                phase_index = min(1, len(steps) - 1)
                blocker = 'La sesion aislada necesita autenticacion inicial.'
                progress = 0.24
            elif auto_reason == 'browser_input_missing' and focused_title:
                stage = 'abriendo sesion aislada'
                phase_index = min(1, len(steps) - 1)
                blocker = f'La sesion aislada quedo en "{focused_title}" y aun no aparece el input del chat.'
                progress = 0.26
            elif str(execution_metadata.get('launch_mode') or '').strip().lower() in {'web_assisted', 'desktop_app'} and not focused_title:
                stage = 'lanzando asistente'
                phase_index = min(1, len(steps) - 1)
                progress = 0.21
            elif lane == 'background':
                stage = 'esperando respuesta'
                phase_index = min(3, len(steps) - 1)
                progress = 0.58
            else:
                stage = 'esperando respuesta'
                phase_index = min(2, len(steps) - 1)
                progress = 0.5
        else:
            stage = state.replace('_', ' ') or 'decidiendo ruta'
            progress = 0.14

        current_step = steps[phase_index]
        pending_steps = steps[phase_index + 1:] if phase_index + 1 < len(steps) else []
        progress_pct = int(round(max(0.0, min(1.0, progress)) * 100.0))
        return {
            'stage': stage,
            'current_step': current_step,
            'detail': detail,
            'blocker': blocker,
            'progress': round(max(0.0, min(1.0, progress)), 4),
            'progress_pct': progress_pct,
            'remaining_pct': int(max(0, 100 - progress_pct)),
            'pending_steps': pending_steps,
            'pending_summary': ' | '.join(pending_steps[:3]),
        }

    def _step_plan(self, lane: str) -> list[str]:
        if lane == 'background':
            return ['decidir ruta', 'abrir sesion aislada', 'enviar prompt estrategico', 'esperar respuesta en segundo plano', 'capturar respuesta', 'validar coherencia', 'consolidar aprendizaje']
        if lane == 'app':
            return ['decidir ruta', 'abrir app externa', 'enfocar ventana y enviar prompt', 'esperar respuesta visible', 'capturar respuesta', 'validar coherencia', 'consolidar aprendizaje']
        return ['decidir ruta', 'preparar fallback manual', 'esperar respuesta del usuario', 'capturar respuesta', 'validar coherencia', 'consolidar aprendizaje']

    def _requested_assistant_kind(self, task: Any, result: Any | None = None) -> str:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        goal_parameters = dict(task_metadata.get('goal_parameters') or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        result_metadata = dict(getattr(result, 'metadata', {}) or {})
        autonomous = dict(result_metadata.get('autonomous_consultation') or {})
        for candidate in (
            execution_metadata.get('requested_assistant_kind'),
            autonomous.get('requested_assistant_kind'),
            task_metadata.get('requested_assistant_kind'),
            goal_parameters.get('assistant_preference'),
            goal_parameters.get('assistant_kind'),
            task_metadata.get('assistant_preference'),
            task_metadata.get('assistant_kind'),
        ):
            normalized = str(candidate or '').strip().lower()
            if normalized:
                return normalized
        return ''

    def _assistant_family_for_tool_id(self, tool_id: str) -> str:
        normalized = str(tool_id or '').strip().lower()
        for family in ('chatgpt', 'claude', 'codex', 'ollama'):
            if normalized.startswith(family):
                return family
        return normalized.split('_', 1)[0]

    def _assistant_family_from_text(self, text: str) -> str:
        normalized = str(text or '').strip().lower()
        for family in ('codex', 'chatgpt', 'claude', 'ollama'):
            if family in normalized:
                return family
        return ''

    def _sort_key(self, task: Any, result: Any | None) -> str:
        task_metadata = dict(getattr(task, 'metadata', {}) or {})
        execution_metadata = dict(getattr(getattr(result, 'execution_state', None), 'metadata', {}) or {})
        return str(execution_metadata.get('last_capture_attempt_utc') or getattr(result, 'created_at_utc', '') or task_metadata.get('updated_at_utc') or task_metadata.get('created_at_utc') or '')

    def _slug(self, value: str) -> str:
        normalized = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
        compact = '-'.join(part for part in normalized.split('-') if part)
        return compact[:60]

