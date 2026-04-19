from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Any

try:
    import ctypes
    from ctypes import wintypes
except Exception:  # pragma: no cover - non-Windows fallback
    ctypes = None
    wintypes = None

try:
    from PIL import ImageGrab
except Exception:  # pragma: no cover - optional runtime fallback
    ImageGrab = None

from iabv_v15.services.capture.browser_session_controller import BrowserSessionController, sync_playwright as browser_sync_playwright
from iabv_v15.domain.models import (
    AnnotationConfidence,
    CrossCheckResult,
    ObjectIdentityLink,
    OverlayKind,
    TeachingEvidence,
    ToolAction,
    ToolActionType,
    ToolCard,
    ToolTask,
    UserClickTrace,
    VisualObjectAnnotation,
    VisualTeachingFrame,
)


class UIExecutionRunner:
    """Executes low-level desktop actions on Windows and records auditable evidence.

    If the environment does not allow real execution, the runner returns a simulated
    result and makes that explicit in metadata instead of pretending success.
    """

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root)
        self._user32 = self._load_user32()

    def is_available(self) -> bool:
        return bool(os.name == 'nt' and self._user32 is not None)

    def run(self, card: ToolCard, task: ToolTask, *, sandbox: bool = False) -> dict[str, Any]:
        start = time.perf_counter()
        execution_dir = self.workspace_root / 'data' / 'tool_teaching' / 'ui_execution' / task.task_id
        execution_dir.mkdir(parents=True, exist_ok=True)
        real_execution = self.is_available() and not sandbox
        simulation_reason = '' if real_execution else ('sandbox_mode' if sandbox else 'execution_backend_unavailable')
        artifacts: list[str] = []
        frames: list[VisualTeachingFrame] = []
        evidence: list[TeachingEvidence] = []
        errors: list[str] = []
        step_summaries: list[str] = []
        screen_width, screen_height = self._screen_size()
        for index, action in enumerate(task.actions, start=1):
            before_path = execution_dir / f'{index:02d}_{action.action_type.value}_before.png'
            after_path = execution_dir / f'{index:02d}_{action.action_type.value}_after.png'
            before_ok = self._capture_screenshot(before_path)
            if before_ok:
                artifacts.append(str(before_path))
            frame, detail, error = self._execute_action(
                action=action,
                before_path=str(before_path) if before_ok else '',
                after_path=after_path,
                screen_width=screen_width,
                screen_height=screen_height,
                real_execution=real_execution,
                card=card,
            )
            if frame is not None:
                frames.append(frame)
                evidence.extend(self._frame_evidence(frame))
            if after_path.exists():
                artifacts.append(str(after_path))
            if detail:
                step_summaries.append(detail)
            if error:
                errors.append(error)
        cross_check_summary = self._cross_check_summary(frames)
        success = not errors
        state_hint = '' if real_execution else 'simulated'
        if not task.actions:
            step_summaries.append('No habia acciones declaradas; solo se confirmo disponibilidad del runner.')
            success = True
            state_hint = 'simulated' if not real_execution else 'ready'
        output = '\\n'.join(step_summaries) or ('UIExecutionRunner listo.' if real_execution else 'UIExecutionRunner disponible solo en modo simulado.')
        return {
            'success': success,
            'output_text': output,
            'extracted_data': {
                'frame_count': len(frames),
                'cross_check_summary': cross_check_summary,
                'screen_width': screen_width,
                'screen_height': screen_height,
            },
            'artifacts': artifacts,
            'error_message': '; '.join(errors),
            'execution_ms': int((time.perf_counter() - start) * 1000),
            'metadata': {
                'sandbox': sandbox,
                'state_hint': state_hint,
                'simulation_mode': 'real' if real_execution else 'simulated',
                'simulation_reason': simulation_reason,
                'real_execution_available': self.is_available(),
                'visual_teaching_frames': [frame.model_dump(mode='json') for frame in frames],
                'teaching_evidence': [item.model_dump(mode='json') for item in evidence],
                'cross_check_summary': cross_check_summary,
            },
        }

    def capture_response_from_app(
        self,
        *,
        launch_target: str,
        title_hints: list[str] | tuple[str, ...],
        prompt_text: str,
        launch_mode: str = 'desktop_app',
        submit_after_paste: bool = True,
        launch_wait_seconds: float = 1.2,
        window_wait_seconds: float = 8.0,
        response_wait_seconds: float = 4.0,
        clipboard_settle_seconds: float = 0.2,
        background_capture_mode: str = '',
        session_state_path: str = '',
        session_rollouts_root: str = '',
        fallback_session_state_path: str = '',
        fallback_session_rollouts_root: str = '',
        response_match_markers: list[str] | tuple[str, ...] | None = None,
        thread_key: str = '',
        thread_title: str = '',
        launch_env: dict[str, str] | None = None,
        browser_profile_dir: str = '',
        browser_headless: bool = True,
        input_selectors: list[str] | tuple[str, ...] | None = None,
        response_selectors: list[str] | tuple[str, ...] | None = None,
        submit_selectors: list[str] | tuple[str, ...] | None = None,
        reingest_only: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        started_unix = time.time()
        hints = [str(item or '').strip() for item in title_hints if str(item or '').strip()]
        match_markers = [str(item or '').strip() for item in (response_match_markers or []) if str(item or '').strip()]
        session_capture_mode = str(background_capture_mode or '').strip().lower()
        if session_capture_mode == 'browser_dom':
            return self._capture_browser_dom_response(
                launch_target=launch_target,
                prompt_text=prompt_text,
                response_wait_seconds=response_wait_seconds,
                browser_profile_dir=browser_profile_dir,
                browser_headless=browser_headless,
                input_selectors=list(input_selectors or []),
                response_selectors=list(response_selectors or []),
                submit_selectors=list(submit_selectors or []),
                reingest_only=reingest_only,
            )
        initial_clipboard = self.read_clipboard_text()
        launched = False
        focused_title = ''
        prompt_pasted = False
        response_captured = False
        captured_text = ''
        capture_source = ''
        thread_verified = False
        used_fallback_capture = False
        rollout_path = ''
        error_message = ''
        rollout_error = ''
        try:
            if not self.is_available():
                raise RuntimeError('ui_execution_unavailable')
            launched = self._launch_target(launch_target, launch_mode=launch_mode, launch_env=launch_env)
            time.sleep(max(0.1, launch_wait_seconds))
            focused_title = self._wait_and_focus_any_window(hints, window_wait_seconds)
            if focused_title:
                self._paste_text(prompt_text)
                prompt_pasted = True
                if submit_after_paste:
                    self._send_virtual_key(0x0D)
            deadline = time.monotonic() + max(0.1, response_wait_seconds)
            poll_seconds = max(0.35, min(1.5, response_wait_seconds / 4.0))
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(poll_seconds, max(0.1, remaining)))
                if session_capture_mode == 'codex_rollout':
                    rollout_capture = self._capture_codex_rollout_response(
                        session_state_path=session_state_path,
                        session_rollouts_root=session_rollouts_root,
                        fallback_session_state_path=fallback_session_state_path,
                        fallback_session_rollouts_root=fallback_session_rollouts_root,
                        correlation_markers=match_markers,
                        prompt_text=prompt_text,
                        started_after_unix=started_unix,
                    )
                    if rollout_capture.get('response_captured'):
                        captured_text = str(rollout_capture.get('captured_text') or '').strip()
                        response_captured = True
                        capture_source = 'session_rollout'
                        thread_verified = bool(rollout_capture.get('thread_verified'))
                        used_fallback_capture = bool(rollout_capture.get('used_fallback_capture'))
                        rollout_path = str(rollout_capture.get('rollout_path') or '')
                        if not focused_title:
                            focused_title = str(rollout_capture.get('focused_title') or '')
                        break
                    rollout_error = str(rollout_capture.get('error_message') or rollout_error or '').strip()
                captured_text = self.copy_active_window_text(
                    select_all=True,
                    settle_seconds=max(0.05, clipboard_settle_seconds),
                ).strip()
                response_captured = self._captured_text_looks_useful(
                    captured_text=captured_text,
                    prompt_text=prompt_text,
                    previous_clipboard=initial_clipboard,
                )
                if response_captured:
                    capture_source = 'clipboard_capture'
                    break
        except Exception as exc:
            error_message = str(exc)
        if not response_captured and not error_message and rollout_error:
            error_message = rollout_error
        return {
            'launched': launched,
            'focused': bool(focused_title),
            'focused_title': focused_title,
            'prompt_pasted': prompt_pasted,
            'response_captured': response_captured,
            'captured_text': captured_text if response_captured else '',
            'captured_excerpt': captured_text[:400] if captured_text else '',
            'capture_source': capture_source,
            'thread_verified': thread_verified,
            'used_fallback_capture': used_fallback_capture,
            'rollout_path': rollout_path,
            'error_message': error_message,
            'execution_ms': int((time.perf_counter() - started) * 1000),
            'metadata': {
                'launch_mode': launch_mode,
                'launch_target': launch_target,
                'title_hints': hints,
                'window_wait_seconds': window_wait_seconds,
                'response_wait_seconds': response_wait_seconds,
                'clipboard_settle_seconds': clipboard_settle_seconds,
                'background_capture_mode': session_capture_mode,
                'thread_key': thread_key,
                'thread_title': thread_title,
            },
        }

    def _execute_action(
        self,
        *,
        action: ToolAction,
        before_path: str,
        after_path: Path,
        screen_width: int,
        screen_height: int,
        real_execution: bool,
        card: ToolCard,
    ) -> tuple[VisualTeachingFrame | None, str, str]:
        detected = self._annotation_from_action(action, before_path, screen_width=screen_width, screen_height=screen_height)
        click_trace: UserClickTrace | None = None
        error = ''
        detail = ''
        if real_execution:
            try:
                detail = self._perform_real_action(action, card=card)
            except Exception as exc:  # pragma: no cover - real environment branch
                error = str(exc)
                detail = f'{action.action_type.value}: fallo {exc}'
        else:
            detail = f'{action.action_type.value}: simulado ({action.label or action.target or action.action_id})'
        after_ok = self._capture_screenshot(after_path)
        if action.action_type in {ToolActionType.CLICK, ToolActionType.CLICK_POINT, ToolActionType.TYPE_TEXT, ToolActionType.SCROLL}:
            click_trace = self._click_trace_from_action(
                action,
                screenshot_ref=str(after_path) if after_ok else before_path,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        cross_check = self._cross_check(detected, click_trace)
        frame = VisualTeachingFrame(
            episode_id=action.metadata.get('episode_id', ''),
            step_id=action.action_id,
            objective=action.label or action.target or action.action_type.value,
            screenshot_ref=str(after_path) if after_ok else before_path,
            detected_objects=[detected] if detected is not None else [],
            user_click=click_trace,
            object_links=self._object_links(detected, click_trace, cross_check),
            cross_check=cross_check,
            notes=[detail],
            metadata={
                'action_type': action.action_type.value,
                'tool_id': action.metadata.get('tool_id', ''),
                'execution_mode': 'real' if real_execution else 'simulated',
                'before_screenshot': before_path,
                'after_screenshot': str(after_path) if after_ok else '',
                'requires_approval': action.requires_approval,
                'card_title': card.title,
            },
        )
        return frame, detail, error

    def _perform_real_action(self, action: ToolAction, *, card: ToolCard) -> str:
        if action.action_type == ToolActionType.LAUNCH_APP:
            target = action.target or str(action.parameters.get('path') or action.parameters.get('url') or '')
            if not target:
                raise RuntimeError('No recibi destino para lanzar la aplicacion.')
            if target.lower().startswith('http://') or target.lower().startswith('https://'):
                opened = webbrowser.open(target)
                return f'launch_app: {target} ({"ok" if opened else "open_requested"})'
            self._launch_desktop_target(target, cwd=Path(card.metadata.get('workspace_root') or self.workspace_root))
            time.sleep(float(action.parameters.get('wait_seconds', 1.2) or 1.2))
            return f'launch_app: {target}'
        if action.action_type == ToolActionType.FOCUS_WINDOW:
            title = action.target or str(action.parameters.get('window_title') or '')
            if not title:
                raise RuntimeError('No recibi titulo de ventana para enfocar.')
            if not self._focus_window(title):
                raise RuntimeError(f'No encontre una ventana compatible con: {title}')
            time.sleep(0.2)
            return f'focus_window: {title}'
        if action.action_type in {ToolActionType.CLICK, ToolActionType.CLICK_POINT}:
            x, y = self._resolve_xy(action)
            self._user32.SetCursorPos(int(x), int(y))
            time.sleep(0.05)
            self._mouse_click()
            time.sleep(float(action.parameters.get('wait_seconds', 0.25) or 0.25))
            return f'click: ({int(x)}, {int(y)})'
        if action.action_type == ToolActionType.MOVE_MOUSE:
            x, y = self._resolve_xy(action)
            self._user32.SetCursorPos(int(x), int(y))
            time.sleep(0.05)
            return f'move_mouse: ({int(x)}, {int(y)})'
        if action.action_type == ToolActionType.SCROLL:
            amount = int(action.parameters.get('delta') or action.parameters.get('amount') or 0)
            self._user32.mouse_event(0x0800, 0, 0, amount, 0)
            time.sleep(float(action.parameters.get('wait_seconds', 0.2) or 0.2))
            return f'scroll: {amount}'
        if action.action_type == ToolActionType.TYPE_TEXT:
            value = action.value or str(action.parameters.get('text') or '')
            if not value:
                raise RuntimeError('No recibi texto para escribir.')
            self._paste_text(value)
            if bool(action.parameters.get('submit_after')):
                self._send_virtual_key(0x0D)
            time.sleep(float(action.parameters.get('wait_seconds', 0.2) or 0.2))
            return f'type_text: {len(value)} chars'
        if action.action_type == ToolActionType.WAIT_FOR_WINDOW:
            title = action.target or str(action.parameters.get('window_title') or '')
            if not title:
                raise RuntimeError('No recibi titulo de ventana para esperar.')
            timeout = float(action.parameters.get('timeout_seconds') or 8.0)
            if not self._wait_for_window(title, timeout):
                raise RuntimeError(f'No aparecio la ventana esperada: {title}')
            return f'wait_for_window: {title}'
        if action.action_type == ToolActionType.WAIT_FOR_CHANGE:
            delay = float(action.parameters.get('seconds') or action.parameters.get('wait_seconds') or 1.0)
            time.sleep(delay)
            return f'wait_for_change: {delay:.2f}s'
        if action.action_type in {ToolActionType.SCREENSHOT, ToolActionType.VERIFY_STATE}:
            time.sleep(float(action.parameters.get('wait_seconds', 0.1) or 0.1))
            return action.action_type.value
        raise RuntimeError(f'Accion no soportada por UIExecutionRunner: {action.action_type.value}')

    def _annotation_from_action(
        self,
        action: ToolAction,
        screenshot_ref: str,
        *,
        screen_width: int,
        screen_height: int,
    ) -> VisualObjectAnnotation | None:
        rect = dict(action.parameters.get('overlay_rect') or action.parameters.get('expected_rect') or {})
        point = dict(action.parameters.get('overlay_point') or action.parameters.get('expected_point') or {})
        if not rect and not point:
            coords = action.parameters.get('x'), action.parameters.get('y')
            if coords[0] is not None and coords[1] is not None:
                x = float(coords[0])
                y = float(coords[1])
                point = {
                    'valid': True,
                    'x': 0.0 if screen_width <= 0 else max(0.0, min(1.0, x / max(screen_width, 1))),
                    'y': 0.0 if screen_height <= 0 else max(0.0, min(1.0, y / max(screen_height, 1))),
                }
        if not rect and not point:
            return None
        confidence = AnnotationConfidence.CONFIRMED if rect or point else AnnotationConfidence.INSUFFICIENT
        return VisualObjectAnnotation(
            label=action.label or action.target or action.action_type.value,
            overlay_kind=OverlayKind.CLICK_POINT if point else OverlayKind.RECT,
            overlay_rect=rect,
            overlay_point=point,
            detected_by='action_hint',
            confidence_score=0.82 if confidence == AnnotationConfidence.CONFIRMED else 0.35,
            confidence=confidence,
            screenshot_ref=screenshot_ref,
            metadata={
                'target': action.target,
                'expected_signal': action.expected_signal,
            },
        )

    def _click_trace_from_action(
        self,
        action: ToolAction,
        *,
        screenshot_ref: str,
        screen_width: int,
        screen_height: int,
    ) -> UserClickTrace | None:
        try:
            x, y = self._resolve_xy(action)
        except Exception:
            return None
        return UserClickTrace(
            action_type=action.action_type.value,
            target=action.target,
            screenshot_ref=screenshot_ref,
            x=int(x),
            y=int(y),
            normalized_x=0.0 if screen_width <= 0 else max(0.0, min(1.0, float(x) / max(screen_width, 1))),
            normalized_y=0.0 if screen_height <= 0 else max(0.0, min(1.0, float(y) / max(screen_height, 1))),
            derived_from_rect=bool(action.parameters.get('derived_from_rect')),
            metadata={'label': action.label},
        )

    def _cross_check(
        self,
        detected: VisualObjectAnnotation | None,
        click_trace: UserClickTrace | None,
    ) -> CrossCheckResult | None:
        if detected is None and click_trace is None:
            return None
        if detected is None or click_trace is None:
            return CrossCheckResult(
                status=AnnotationConfidence.INSUFFICIENT,
                matched=False,
                annotation_id=detected.annotation_id if detected is not None else '',
                click_id=click_trace.click_id if click_trace is not None else '',
                discrepancy='missing_visual_pair',
                rationale='Solo tengo deteccion o solo tengo clic humano; no puedo validar coincidencia completa.',
                confidence=0.22,
            )
        matched = False
        distance_score = 0.0
        rect = detected.overlay_rect if isinstance(detected.overlay_rect, dict) else {}
        point = detected.overlay_point if isinstance(detected.overlay_point, dict) else {}
        if rect.get('valid'):
            matched = (
                rect.get('x', 0.0) <= click_trace.normalized_x <= rect.get('x', 0.0) + rect.get('width', 0.0)
                and rect.get('y', 0.0) <= click_trace.normalized_y <= rect.get('y', 0.0) + rect.get('height', 0.0)
            )
        elif point.get('valid'):
            dx = abs(float(point.get('x', 0.0) or 0.0) - click_trace.normalized_x)
            dy = abs(float(point.get('y', 0.0) or 0.0) - click_trace.normalized_y)
            distance_score = max(0.0, 1.0 - min(1.0, (dx + dy) * 3.0))
            matched = distance_score >= 0.65
        status = AnnotationConfidence.CONFIRMED if matched else AnnotationConfidence.DOUBTFUL
        return CrossCheckResult(
            status=status,
            matched=matched,
            annotation_id=detected.annotation_id,
            click_id=click_trace.click_id,
            discrepancy='' if matched else 'click_not_aligned_with_detected_object',
            rationale='El clic humano coincide con el objeto detectado.' if matched else 'El clic humano y el objeto detectado no quedaron suficientemente alineados.',
            confidence=0.84 if matched else 0.48,
            metadata={'distance_score': round(distance_score, 4)},
        )

    def _object_links(
        self,
        detected: VisualObjectAnnotation | None,
        click_trace: UserClickTrace | None,
        cross_check: CrossCheckResult | None,
    ) -> list[ObjectIdentityLink]:
        if detected is None or click_trace is None or cross_check is None:
            return []
        return [
            ObjectIdentityLink(
                annotation_id=detected.annotation_id,
                click_id=click_trace.click_id,
                matched=cross_check.matched,
                distance_score=float(cross_check.metadata.get('distance_score') or 1.0 if cross_check.matched else 0.0),
                rationale=cross_check.rationale,
            )
        ]

    def _frame_evidence(self, frame: VisualTeachingFrame) -> list[TeachingEvidence]:
        summary = frame.cross_check.rationale if frame.cross_check is not None else 'Sin cruce visual.'
        return [
            TeachingEvidence(
                episode_id=frame.episode_id,
                frame_id=frame.frame_id,
                summary=summary,
                screenshot_ref=frame.screenshot_ref,
                confidence=float(frame.cross_check.confidence if frame.cross_check is not None else 0.0),
                metadata={'step_id': frame.step_id},
            )
        ]

    def _cross_check_summary(self, frames: list[VisualTeachingFrame]) -> dict[str, Any]:
        confirmed = doubtful = insufficient = 0
        for frame in frames:
            if frame.cross_check is None:
                insufficient += 1
                continue
            if frame.cross_check.status == AnnotationConfidence.CONFIRMED:
                confirmed += 1
            elif frame.cross_check.status == AnnotationConfidence.DOUBTFUL:
                doubtful += 1
            else:
                insufficient += 1
        total = max(1, len(frames))
        return {
            'frame_count': len(frames),
            'confirmed_count': confirmed,
            'doubtful_count': doubtful,
            'insufficient_count': insufficient,
            'observer_agreement_score': round(confirmed / total, 4),
            'target_element_alignment': round((confirmed + (doubtful * 0.5)) / total, 4),
        }

    def _resolve_xy(self, action: ToolAction) -> tuple[float, float]:
        if action.parameters.get('x') is not None and action.parameters.get('y') is not None:
            return float(action.parameters['x']), float(action.parameters['y'])
        rect = dict(action.parameters.get('overlay_rect') or action.parameters.get('expected_rect') or {})
        if rect.get('valid') and self._user32 is not None:
            width, height = self._screen_size()
            return (
                (float(rect.get('x', 0.0) or 0.0) + (float(rect.get('width', 0.0) or 0.0) / 2.0)) * max(width, 1),
                (float(rect.get('y', 0.0) or 0.0) + (float(rect.get('height', 0.0) or 0.0) / 2.0)) * max(height, 1),
            )
        point = dict(action.parameters.get('overlay_point') or action.parameters.get('expected_point') or {})
        if point.get('valid') and self._user32 is not None:
            width, height = self._screen_size()
            return float(point.get('x', 0.0) or 0.0) * max(width, 1), float(point.get('y', 0.0) or 0.0) * max(height, 1)
        raise RuntimeError('No recibi coordenadas ni geometria suficiente para ejecutar la accion.')

    def _screen_size(self) -> tuple[int, int]:
        if self._user32 is not None:
            return int(self._user32.GetSystemMetrics(0)), int(self._user32.GetSystemMetrics(1))
        return 0, 0

    def read_clipboard_text(self) -> str:
        try:  # pragma: no cover - live app branch
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            clipboard = app.clipboard() if app is not None else None
            if clipboard is not None:
                return str(clipboard.text() or '')
        except Exception:
            pass
        try:
            completed = self._run_powershell_command('Get-Clipboard -Raw')
            return self._decode_subprocess_text(completed.stdout).strip()
        except Exception:
            return ''

    def copy_active_window_text(self, *, select_all: bool = True, settle_seconds: float = 0.15) -> str:
        if select_all:
            self._send_hotkey(0x11, 0x41)
            time.sleep(max(0.03, settle_seconds))
        self._send_hotkey(0x11, 0x43)
        time.sleep(max(0.03, settle_seconds))
        return self.read_clipboard_text()
    def _capture_screenshot(self, path: Path) -> bool:
        try:
            if ImageGrab is not None:
                image = ImageGrab.grab(all_screens=True)
                image.save(path)
                return True
        except Exception:
            pass
        try:  # pragma: no cover - Qt fallback in live app
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            screen = app.primaryScreen() if app is not None else None
            if screen is not None:
                pixmap = screen.grabWindow(0)
                if not pixmap.isNull():
                    pixmap.save(str(path))
                    return True
        except Exception:
            return False
        return False

    def _load_user32(self):
        if os.name != 'nt' or ctypes is None:
            return None
        try:
            return ctypes.windll.user32
        except Exception:
            return None

    def _mouse_click(self) -> None:
        if self._user32 is None:
            raise RuntimeError('user32 no disponible')
        self._user32.mouse_event(0x0002, 0, 0, 0, 0)
        self._user32.mouse_event(0x0004, 0, 0, 0, 0)

    def _launch_target(self, target: str, *, launch_mode: str = 'desktop_app', launch_env: dict[str, str] | None = None) -> bool:
        resolved_target = str(target or '').strip()
        if not resolved_target:
            raise RuntimeError('missing_launch_target')
        if launch_mode == 'web_assisted' or resolved_target.lower().startswith(('http://', 'https://')):
            return bool(webbrowser.open(resolved_target))
        self._launch_desktop_target(resolved_target, cwd=self.workspace_root, launch_env=launch_env)
        return True

    def _launch_desktop_target(self, target: str, *, cwd: Path, launch_env: dict[str, str] | None = None) -> None:
        resolved_target = str(target or '').strip()
        if not resolved_target:
            raise RuntimeError('missing_launch_target')
        resolved = Path(resolved_target)
        if os.name == 'nt' and self._should_launch_via_shell(resolved_target, resolved):
            subprocess.Popen(['cmd', '/c', 'start', '', resolved_target], cwd=str(cwd), env={**os.environ, **dict(launch_env or {})})
            return
        if os.name == 'nt' and resolved.exists():
            if launch_env:
                subprocess.Popen([str(resolved)], cwd=str(cwd), env={**os.environ, **dict(launch_env or {})})
            else:
                os.startfile(str(resolved))  # type: ignore[attr-defined]
            return
        subprocess.Popen([resolved_target], cwd=str(cwd), env={**os.environ, **dict(launch_env or {})})

    def _should_launch_via_shell(self, target: str, resolved: Path) -> bool:
        lowered = str(target or '').lower().replace('/', '\\')
        if '\\program files\\windowsapps\\' in lowered:
            return True
        return os.name == 'nt' and not resolved.exists() and not any(token in str(target) for token in ('\\', '/', ':'))

    def _wait_and_focus_any_window(self, titles: list[str], timeout_seconds: float) -> str:
        if not titles:
            return ''
        deadline = time.monotonic() + max(0.2, timeout_seconds)
        while time.monotonic() < deadline:
            for title in titles:
                if self._focus_window(title):
                    return title
            time.sleep(0.2)
        return ''

    def _send_hotkey(self, *vk_codes: int) -> None:
        if not vk_codes:
            return
        modifiers = [code for code in vk_codes[:-1]]
        key = vk_codes[-1]
        for code in modifiers:
            self._key_down(code)
        try:
            self._send_virtual_key(key)
        finally:
            for code in reversed(modifiers):
                self._key_up(code)

    def _captured_text_looks_useful(self, *, captured_text: str, prompt_text: str, previous_clipboard: str) -> bool:
        text = str(captured_text or '').strip()
        if len(text) < 24:
            return False
        normalized = ' '.join(text.split()).lower()
        prompt_normalized = ' '.join(str(prompt_text or '').split()).lower()
        previous_normalized = ' '.join(str(previous_clipboard or '').split()).lower()
        if normalized == prompt_normalized or normalized == previous_normalized:
            return False
        if prompt_normalized and normalized.startswith(prompt_normalized) and len(normalized) <= len(prompt_normalized) + 16:
            return False
        return True

    def _capture_browser_dom_response(
        self,
        *,
        launch_target: str,
        prompt_text: str,
        response_wait_seconds: float,
        browser_profile_dir: str,
        browser_headless: bool,
        input_selectors: list[str],
        response_selectors: list[str],
        submit_selectors: list[str],
        reingest_only: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        profile_dir = Path(browser_profile_dir) if browser_profile_dir else (self.workspace_root / 'data' / 'tool_teaching' / 'external_assistants' / 'web_program_session' / 'browser_profile')
        profile_dir.mkdir(parents=True, exist_ok=True)
        if browser_sync_playwright is None:
            return {
                'launched': False,
                'focused': False,
                'focused_title': '',
                'prompt_pasted': False,
                'response_captured': False,
                'captured_text': '',
                'captured_excerpt': '',
                'capture_source': 'browser_dom',
                'error_message': 'browser_dom_unavailable',
                'browser_profile_dir': str(profile_dir),
                'execution_ms': int((time.perf_counter() - started) * 1000),
                'metadata': {'background_capture_mode': 'browser_dom'},
            }
        controller = BrowserSessionController(user_data_dir=str(profile_dir), headless=browser_headless)
        launched = False
        prompt_pasted = False
        response_captured = False
        captured_text = ''
        focused_title = ''
        error_message = ''
        try:
            controller.start()
            launched = True
            page = controller.page or controller.new_page()
            page.goto(launch_target, wait_until='domcontentloaded')
            try:
                page.wait_for_load_state('networkidle', timeout=7000)
            except Exception:
                pass
            focused_title = str(page.title() or '').strip()

            # Intentar con reintentos para esperar verificación de seguridad (Cloudflare, etc.)
            security_verification_wait = 12.0
            max_security_retries = 3
            input_selector = ''
            for attempt in range(max_security_retries):
                input_selector = self._first_browser_selector(page, input_selectors)
                if input_selector:
                    break
                if self._browser_page_requires_security_verification(page):
                    time.sleep(security_verification_wait / max_security_retries)
                    try:
                        page.reload(wait_until='domcontentloaded')
                        page.wait_for_load_state('networkidle', timeout=7000)
                    except Exception:
                        pass
                    focused_title = str(page.title() or '').strip()
                    continue
                break

            if not input_selector and not reingest_only:
                if self._browser_page_requires_security_verification(page):
                    error_message = 'browser_security_verification'
                elif self._browser_page_requires_login(page):
                    error_message = 'assistant_login_required'
                else:
                    error_message = 'browser_input_missing'
                return {
                    'launched': launched,
                    'focused': True,
                    'focused_title': focused_title,
                    'prompt_pasted': False,
                    'response_captured': False,
                    'captured_text': '',
                    'captured_excerpt': '',
                    'capture_source': 'browser_dom',
                    'error_message': error_message,
                    'browser_profile_dir': str(profile_dir),
                    'execution_ms': int((time.perf_counter() - started) * 1000),
                    'metadata': {'background_capture_mode': 'browser_dom', 'security_retries': attempt + 1},
                }
            if reingest_only:
                # Modo reingesta: la sesion aislada ya tiene un hilo abierto con respuesta.
                # No re-pegar prompt ni re-submittear; solo leer los response_selectors actuales.
                pass
            else:
                self._fill_browser_prompt(page, input_selector, prompt_text)
                prompt_pasted = True
                self._submit_browser_prompt(page, submit_selectors)
            deadline = time.monotonic() + max(3.0, response_wait_seconds)
            stable_hits = 0
            last_text = ''
            while time.monotonic() < deadline:
                time.sleep(1.0)
                candidate = self._latest_browser_response_text(page, response_selectors)
                if not self._captured_text_looks_useful(captured_text=candidate, prompt_text=prompt_text, previous_clipboard=''):
                    continue
                if candidate == last_text:
                    stable_hits += 1
                else:
                    last_text = candidate
                    stable_hits = 1
                if stable_hits >= 2:
                    captured_text = candidate
                    response_captured = True
                    break
            if not response_captured and not error_message:
                error_message = 'browser_dom_capture_pending'
        except Exception as exc:
            error_message = str(exc)
        finally:
            try:
                controller.close()
            except Exception:
                pass
        return {
            'launched': launched,
            'focused': launched,
            'focused_title': focused_title,
            'prompt_pasted': prompt_pasted,
            'response_captured': response_captured,
            'captured_text': captured_text if response_captured else '',
            'captured_excerpt': captured_text[:400] if captured_text else '',
            'capture_source': 'browser_dom_reingest' if reingest_only else 'browser_dom',
            'error_message': error_message,
            'browser_profile_dir': str(profile_dir),
            'execution_ms': int((time.perf_counter() - started) * 1000),
            'metadata': {
                'background_capture_mode': 'browser_dom',
                'browser_headless': browser_headless,
                'reingest_only': reingest_only,
            },
        }

    def _first_browser_selector(self, page: Any, selectors: list[str]) -> str:
        for selector in selectors:
            probe = str(selector or '').strip()
            if not probe:
                continue
            try:
                locator = page.locator(probe)
                if locator.count() > 0:
                    return probe
            except Exception:
                continue
        return ''

    def _fill_browser_prompt(self, page: Any, selector: str, prompt_text: str) -> None:
        locator = page.locator(selector).first
        try:
            locator.click(timeout=3000)
        except Exception:
            pass
        try:
            locator.fill(prompt_text)
            return
        except Exception:
            pass
        try:
            page.keyboard.insert_text(prompt_text)
        except Exception:
            locator.evaluate("(node, value) => { if (node && 'textContent' in node) { node.textContent = value; } }", prompt_text)

    def _submit_browser_prompt(self, page: Any, submit_selectors: list[str]) -> None:
        selector = self._first_browser_selector(page, submit_selectors)
        if selector:
            try:
                page.locator(selector).first.click(timeout=3000)
                return
            except Exception:
                pass
        try:
            page.keyboard.press('Enter')
        except Exception:
            pass

    def _latest_browser_response_text(self, page: Any, selectors: list[str]) -> str:
        for selector in selectors:
            probe = str(selector or '').strip()
            if not probe:
                continue
            try:
                locator = page.locator(probe)
                if locator.count() <= 0:
                    continue
                texts = [str(item or '').strip() for item in locator.all_inner_texts()]
                texts = [item for item in texts if item]
                if texts:
                    return texts[-1]
            except Exception:
                continue
        try:
            body = str(page.locator('body').inner_text(timeout=1000) or '').strip()
            return body[-4000:]
        except Exception:
            return ''

    def _browser_page_requires_login(self, page: Any) -> bool:
        try:
            url = str(page.url or '').lower()
        except Exception:
            url = ''
        if any(token in url for token in ('login', 'signin', 'auth')):
            return True
        try:
            body = str(page.locator('body').inner_text(timeout=1500) or '').lower()
        except Exception:
            body = ''
        login_tokens = ('log in', 'login', 'sign in', 'continue with google', 'iniciar sesion', 'inicia sesion')
        return any(token in body for token in login_tokens)

    def _browser_page_requires_security_verification(self, page: Any) -> bool:
        try:
            title = str(page.title() or '').strip().lower()
        except Exception:
            title = ''
        try:
            url = str(page.url or '').strip().lower()
        except Exception:
            url = ''
        try:
            body = str(page.locator('body').inner_text(timeout=1500) or '').strip().lower()
        except Exception:
            body = ''
        verification_tokens = (
            'just a moment',
            'security verification',
            'performing security verification',
            'verify you are not a bot',
            'verifies you are not a bot',
            'cloudflare',
            'ray id:',
            'checking your browser',
            'verificando que no eres un bot',
        )
        if any(token in title for token in verification_tokens):
            return True
        if any(token in body for token in verification_tokens):
            return True
        return 'captcha' in url or 'challenge' in url

    def _capture_codex_rollout_response(
        self,
        *,
        session_state_path: str,
        session_rollouts_root: str,
        fallback_session_state_path: str,
        fallback_session_rollouts_root: str,
        correlation_markers: list[str],
        prompt_text: str,
        started_after_unix: float,
    ) -> dict[str, Any]:
        capture_candidates = [
            (
                Path(self._expand_external_path(session_state_path or r'{userprofile}\.codex\state_5.sqlite')),
                Path(self._expand_external_path(session_rollouts_root or r'{userprofile}\.codex\sessions')),
                True,
            )
        ]
        if fallback_session_state_path or fallback_session_rollouts_root:
            capture_candidates.append(
                (
                    Path(self._expand_external_path(fallback_session_state_path or r'{userprofile}\.codex\state_5.sqlite')),
                    Path(self._expand_external_path(fallback_session_rollouts_root or r'{userprofile}\.codex\sessions')),
                    False,
                )
            )
        markers = [item for item in correlation_markers if item]
        seen_roots: set[tuple[str, str, bool]] = set()
        any_state_found = False
        for state_path, rollouts_root, isolated_candidate in capture_candidates:
            cache_key = (str(state_path), str(rollouts_root), isolated_candidate)
            if cache_key in seen_roots:
                continue
            seen_roots.add(cache_key)
            if not state_path.exists():
                continue
            any_state_found = True
            recent_rollouts = self._recent_codex_rollout_candidates(
                state_path=state_path,
                rollouts_root=rollouts_root,
                started_after_unix=started_after_unix,
            )
            for rollout_path, title in recent_rollouts:
                captured_text = self._extract_codex_rollout_assistant_text(
                    rollout_path=rollout_path,
                    correlation_markers=markers,
                    prompt_text=prompt_text,
                )
                if captured_text:
                    return {
                        'response_captured': True,
                        'captured_text': captured_text,
                        'focused_title': title or 'Codex',
                        'error_message': '',
                        'rollout_path': str(rollout_path),
                        'thread_verified': bool(isolated_candidate and markers),
                        'used_fallback_capture': not isolated_candidate,
                    }
        if not any_state_found:
            return {'response_captured': False, 'captured_text': '', 'focused_title': '', 'error_message': 'codex_state_missing'}
        return {'response_captured': False, 'captured_text': '', 'focused_title': '', 'error_message': 'codex_rollout_pending'}

    def _recent_codex_rollout_candidates(
        self,
        *,
        state_path: Path,
        rollouts_root: Path,
        started_after_unix: float,
    ) -> list[tuple[Path, str]]:
        workspace = str(self.workspace_root).lower()
        candidates: list[tuple[int, Path, str]] = []
        try:
            conn = sqlite3.connect(str(state_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT rollout_path, updated_at, cwd, title FROM threads WHERE archived = 0 ORDER BY updated_at DESC LIMIT 12"
                ).fetchall()
            finally:
                conn.close()
        except Exception:
            rows = []
        for row in rows:
            rollout_path = self._resolve_rollout_path(str(row['rollout_path'] or ''), rollouts_root)
            if rollout_path is None or not rollout_path.exists():
                continue
            score = 0
            updated_at = self._normalize_codex_timestamp(row['updated_at'])
            if updated_at >= max(0.0, started_after_unix - 120.0):
                score += 4
            cwd = str(row['cwd'] or '').strip().lower()
            if cwd and workspace and cwd == workspace:
                score += 3
            elif cwd and workspace and workspace in cwd:
                score += 2
            candidates.append((score, rollout_path, str(row['title'] or 'Codex')))
        if not candidates and rollouts_root.exists():
            for rollout_path in sorted(rollouts_root.rglob('rollout-*.jsonl'), key=lambda item: item.stat().st_mtime, reverse=True)[:6]:
                candidates.append((1, rollout_path, 'Codex'))
        candidates.sort(key=lambda item: (item[0], item[1].stat().st_mtime if item[1].exists() else 0.0), reverse=True)
        return [(path, title) for _, path, title in candidates[:6]]

    def _extract_codex_rollout_assistant_text(
        self,
        *,
        rollout_path: Path,
        correlation_markers: list[str],
        prompt_text: str,
    ) -> str:
        matched_query = False
        latest_assistant = ''
        prompt_hint = ' '.join(str(prompt_text or '').split())[:180].lower()
        require_explicit_markers = bool(correlation_markers)
        try:
            with rollout_path.open('r', encoding='utf-8') as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get('type') != 'response_item':
                        continue
                    payload = record.get('payload') or {}
                    if str(payload.get('type') or '').strip().lower() != 'message':
                        continue
                    role = str(payload.get('role') or '').strip().lower()
                    text = self._extract_rollout_message_text(payload)
                    if not text:
                        continue
                    normalized = ' '.join(text.split()).lower()
                    if role == 'user':
                        marker_match = any(marker.lower() in normalized for marker in correlation_markers if marker)
                        prompt_match = (not require_explicit_markers) and bool(prompt_hint and prompt_hint in normalized)
                        if marker_match or prompt_match:
                            matched_query = True
                            latest_assistant = ''
                    elif role == 'assistant' and matched_query and self._captured_text_looks_useful(
                        captured_text=text,
                        prompt_text=prompt_text,
                        previous_clipboard='',
                    ):
                        latest_assistant = text
        except OSError:
            return ''
        return latest_assistant

    def _extract_rollout_message_text(self, payload: dict[str, Any]) -> str:
        content = payload.get('content')
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, list):
            return ''
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get('type') or '').strip().lower()
            if item_type in {'output_text', 'input_text'}:
                text = str(item.get('text') or '').strip()
                if text:
                    chunks.append(text)
        return '\n'.join(chunks).strip()

    def _resolve_rollout_path(self, rollout_path: str, rollouts_root: Path) -> Path | None:
        probe = str(rollout_path or '').strip()
        if not probe:
            return None
        path = Path(probe)
        if path.exists():
            return path
        if rollouts_root.exists():
            candidate = rollouts_root / path.name
            if candidate.exists():
                return candidate
        return path

    def _normalize_codex_timestamp(self, value: Any) -> float:
        try:
            numeric = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        return numeric / 1000.0 if numeric > 1_000_000_000_000 else numeric

    def _expand_external_path(self, candidate: str) -> str:
        expanded = str(candidate or '')
        replacements = {
            '{localappdata}': os.environ.get('LOCALAPPDATA', ''),
            '{programfiles}': os.environ.get('ProgramFiles', ''),
            '{programfilesx86}': os.environ.get('ProgramFiles(x86)', ''),
            '{userprofile}': os.environ.get('USERPROFILE', str(Path.home())),
        }
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        return expanded

    def _wait_for_window(self, title: str, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + max(0.2, timeout_seconds)
        while time.monotonic() < deadline:
            if self._find_window(title) is not None:
                return True
            time.sleep(0.2)
        return False

    def _focus_window(self, title: str) -> bool:
        hwnd = self._find_window(title)
        if hwnd is None or self._user32 is None:
            return False
        try:
            self._user32.ShowWindow(hwnd, 5)
            self._user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def _find_window(self, title: str):
        if self._user32 is None or wintypes is None:
            return None
        matched: list[int] = []
        title_lower = title.lower()
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def _callback(hwnd, _lparam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, length + 1)
            if title_lower in buffer.value.lower():
                matched.append(hwnd)
                return False
            return True

        self._user32.EnumWindows(enum_proc(_callback), 0)
        return matched[0] if matched else None

    def _paste_text(self, text: str) -> None:
        self._set_clipboard_text(text)
        self._key_down(0x11)
        self._send_virtual_key(0x56)
        self._key_up(0x11)

    def _set_clipboard_text(self, text: str) -> None:
        try:  # pragma: no cover - live app branch
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            clipboard = app.clipboard() if app is not None else None
            if clipboard is not None:
                clipboard.setText(text)
                return
        except Exception:
            pass
        self._run_powershell_command(
            'Set-Clipboard -Value ([Console]::In.ReadToEnd())',
            input_text=text,
        )

    def _run_powershell_command(self, script: str, *, input_text: str = '') -> subprocess.CompletedProcess[bytes]:
        kwargs: dict[str, Any] = {
            'check': False,
            'capture_output': True,
        }
        if input_text:
            kwargs['input'] = str(input_text).encode('utf-8')
        return subprocess.run(
            ['powershell', '-NoProfile', '-Command', script],
            **kwargs,
        )

    def _decode_subprocess_text(self, value: Any) -> str:
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        if not isinstance(value, (bytes, bytearray)):
            return str(value)
        raw = bytes(value)
        for encoding in ('utf-8-sig', 'utf-16-le', 'utf-16', 'cp1252', 'latin-1'):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode('utf-8', errors='replace')

    def _send_virtual_key(self, vk_code: int) -> None:
        self._key_down(vk_code)
        time.sleep(0.03)
        self._key_up(vk_code)

    def _key_down(self, vk_code: int) -> None:
        if self._user32 is None:
            raise RuntimeError('user32 no disponible')
        self._user32.keybd_event(vk_code, 0, 0, 0)

    def _key_up(self, vk_code: int) -> None:
        if self._user32 is None:
            raise RuntimeError('user32 no disponible')
        self._user32.keybd_event(vk_code, 0, 0x0002, 0)

