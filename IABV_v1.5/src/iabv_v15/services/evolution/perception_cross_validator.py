"""Cross-validates perception data from multiple IABV sensors.

Compares processes vs tool availability, windows vs WorldModel, and
network status to detect inconsistencies that individual sensors miss.

When inconsistencies are found, the validator can auto-correct by
invalidating stale availability caches and triggering re-checks.
This embodies the principle: never trust a single source of truth.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PerceptionCrossValidator:
    """Cross-validator for meta-cognition consistency.

    Design principle: the ground truth is the *union* of all sensors,
    not any single one.  If filesystem says "missing" but process list
    says "running", the tool IS available — and the validator logs
    the disagreement so the system learns over time.
    """

    def __init__(
        self,
        *,
        world_model_service: Any = None,
        tool_registry: Any = None,
    ) -> None:
        self.world_model_service = world_model_service
        self.tool_registry = tool_registry
        self._created_at = time.time()
        self._check_statuses: dict[str, str] = {}
        self._check_reasons: dict[str, str] = {}
        self._check_reports: dict[str, dict[str, Any]] = {}

    def _set_check_status(self, check: str, status: str, reason: str = '') -> None:
        self._check_statuses[check] = status
        if reason:
            self._check_reasons[check] = reason[:200]
        else:
            self._check_reasons.pop(check, None)

    def _run_check(self, check: str, runner) -> list[dict[str, Any]]:
        try:
            return runner()
        except Exception as exc:
            self._set_check_status(check, 'READ_FAILED', type(exc).__name__)
            logger.warning('perception_check_failed: %s (%s)', check, type(exc).__name__)
            return []

    def run_cross_validation(self) -> dict[str, Any]:
        """Execute full cross-validation and return structured results.

        When inconsistencies are found, attempts auto-correction by
        invalidating the availability cache for affected tools and
        triggering a refresh.  Returns both inconsistencies and any
        corrections applied.
        """
        inconsistencies: list[dict[str, Any]] = []
        auto_corrections: list[dict[str, Any]] = []
        checked_at = datetime.now(timezone.utc).isoformat()
        check_names = (
            'tools_vs_processes', 'audit_vs_worldmodel',
            'windows_consistency', 'ui_self_awareness',
        )
        self._check_statuses = {}
        self._check_reasons = {}
        self._check_reports = {}

        proc_inconsistencies = self._run_check(
            'tools_vs_processes', self._cross_tools_vs_processes
        )
        inconsistencies.extend(proc_inconsistencies)
        corrections = self._auto_correct_availability(proc_inconsistencies)
        auto_corrections.extend(corrections)
        inconsistencies.extend(self._run_check(
            'audit_vs_worldmodel', self._cross_audit_vs_worldmodel
        ))
        inconsistencies.extend(self._run_check(
            'windows_consistency', self._cross_windows_consistency
        ))
        inconsistencies.extend(self._run_check(
            'ui_self_awareness', self._cross_ui_self_awareness
        ))

        for name in check_names:
            if name not in self._check_statuses:
                self._set_check_status(name, 'UNVERIFIED', 'check_did_not_report_execution_status')
        checks_passed = [
            name for name in check_names
            if self._check_statuses.get(name) == 'READ_OK'
            and not any(item.get('check') == name for item in inconsistencies)
        ]
        checks_unavailable = {
            name: {
                'status': self._check_statuses[name],
                'reason': self._check_reasons.get(name, ''),
            }
            for name in check_names
            if self._check_statuses[name] != 'READ_OK'
        }

        return {
            'checked_at': checked_at,
            'inconsistencies': inconsistencies,
            'auto_corrections': auto_corrections,
            'checks_passed': checks_passed,
            'checks_status': dict(self._check_statuses),
            'checks_unavailable': checks_unavailable,
            'checks_read_reports': dict(self._check_reports),
            'total_inconsistencies': len(inconsistencies),
            'total_auto_corrections': len(auto_corrections),
            'total_checks': 4,
            'learning': (
                'Cuando las fuentes discrepan (filesystem vs procesos vs ventanas), '
                'la fuente positiva prevalece. Un solo sensor negativo NO es '
                'suficiente para declarar missing. Esta validacion cruzada se '
                'ejecuta automaticamente para detectar y corregir percepciones '
                'erroneas antes de que afecten decisiones.'
            ),
        }

    def _auto_correct_availability(
        self, proc_inconsistencies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Invalidate cache and force refresh for tools with process evidence.

        Read-only with respect to tool state: only invalidates the
        in-process availability cache so the next refresh picks up
        the multi-source detection result.  Does not mutate the
        ToolCard directly.
        """
        corrections: list[dict[str, Any]] = []
        if self.tool_registry is None:
            return corrections

        for inc in proc_inconsistencies:
            tool_id = inc.get('tool_id', '')
            if not tool_id:
                continue
            try:
                self.tool_registry.invalidate_availability_cache(tool_id)
                card = self.tool_registry.get_card(tool_id)
                if card is not None:
                    refreshed = self.tool_registry.refresh_card(card, force=True)
                    corrections.append({
                        'tool_id': tool_id,
                        'action': 'cache_invalidated_and_refreshed',
                        'new_available': refreshed.available,
                        'reason': (
                            f'Proceso detectado pero registry decia unavailable. '
                            f'Cache invalidado y refresh forzado. Nuevo estado: '
                            f'available={refreshed.available}.'
                        ),
                    })
                    logger.info(
                        'auto_correction: %s — cache invalidated, '
                        'refreshed available=%s (was unavailable)',
                        tool_id,
                        refreshed.available,
                    )
            except Exception as exc:
                logger.warning(
                    'auto_correction_failed: %s — %s', tool_id, exc,
                )
        return corrections

    def _cross_tools_vs_processes(self) -> list[dict[str, Any]]:
        """Compare running processes against tool availability status.

        Also checks window titles as a third source — if a tool has
        a visible window, it is definitely running even if the process
        name doesn't match expected keywords.
        """
        inconsistencies: list[dict[str, Any]] = []
        if self.tool_registry is None:
            self._set_check_status('tools_vs_processes', 'NOT_CONFIGURED', 'tool_registry_not_connected')
            return inconsistencies
        if os.name != 'nt':
            self._set_check_status('tools_vs_processes', 'NOT_APPLICABLE', 'windows_process_sensor_not_applicable')
            return inconsistencies
        try:
            import psutil
        except ImportError:
            self._set_check_status('tools_vs_processes', 'UNAVAILABLE', 'psutil_not_installed')
            return inconsistencies

        proc_names: set[str] = set()
        proc_exes: set[str] = set()
        partial_process_reads = False
        try:
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    name = str(proc.info.get('name') or '').lower()
                    exe = str(proc.info.get('exe') or '').lower()
                    if name:
                        proc_names.add(name)
                    if exe:
                        proc_exes.add(exe)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    partial_process_reads = True
        except Exception as exc:
            self._set_check_status('tools_vs_processes', 'READ_FAILED', type(exc).__name__)
            return inconsistencies

        all_proc_text = ' '.join(proc_names) + ' ' + ' '.join(proc_exes)
        try:
            window_titles = self._enumerate_window_titles()
        except Exception as exc:
            partial_process_reads = True
            self._check_reasons['tools_vs_processes'] = 'window_enumeration_failed:' + type(exc).__name__
            window_titles = []
        all_window_text = ' '.join(window_titles)
        try:
            cards = self.tool_registry.list_cards()
        except Exception as exc:
            report = getattr(exc, 'report', None)
            if report is not None:
                payload = report.to_dict() if callable(getattr(report, 'to_dict', None)) else {
                    'status': getattr(getattr(report, 'status', None), 'value', str(getattr(report, 'status', 'UNKNOWN'))),
                    'records_seen': getattr(report, 'records_seen', None),
                    'records_loaded': getattr(report, 'records_loaded', None),
                    'failed_ids': list(getattr(report, 'failed_ids', []) or []),
                }
                self._check_reports['tools_vs_processes'] = payload
                report_status = getattr(getattr(report, 'status', None), 'value', '')
                status = 'READ_PARTIAL' if report_status == 'READ_PARTIAL' else 'READ_FAILED'
                reason = getattr(report, 'collection_error_type', '') or type(exc).__name__
                self._set_check_status('tools_vs_processes', status, reason)
            else:
                self._set_check_status('tools_vs_processes', 'READ_FAILED', type(exc).__name__)
            return inconsistencies

        for card in cards:
            if not hasattr(card, 'available') or card.available:
                continue
            launch_mode = str(card.metadata.get('launch_mode') or '').strip().lower()
            if launch_mode != 'desktop_app':
                continue

            keywords: list[str] = []
            for field in ('command_name', 'assistant_kind'):
                val = str(card.metadata.get(field) or '').strip().lower()
                if val:
                    keywords.append(val)
            for alias in card.metadata.get('command_aliases') or []:
                val = str(alias or '').strip().lower()
                if val:
                    keywords.append(val)
            title_lower = (card.title or '').lower()
            if title_lower and title_lower not in keywords:
                keywords.append(title_lower)

            found_in_process = [kw for kw in keywords if kw in all_proc_text]
            found_in_window = [kw for kw in keywords if kw in all_window_text]
            found = list(set(found_in_process + found_in_window))

            if found:
                sources = []
                if found_in_process:
                    sources.append(f'procesos({", ".join(found_in_process)})')
                if found_in_window:
                    sources.append(f'ventanas({", ".join(found_in_window)})')
                inconsistencies.append({
                    'check': 'tools_vs_processes',
                    'severity': 'high',
                    'tool_id': card.tool_id,
                    'expected': f'{card.tool_id} reported as unavailable',
                    'actual': f'Detected via: {", ".join(sources)}',
                    'sources_positive': sources,
                    'sources_negative': ['filesystem/registry'],
                    'detail': (
                        f'Tool registry says {card.tool_id} is unavailable but '
                        f'multiple sources confirm presence: {", ".join(sources)}. '
                        f'The detection logic may not cover this install method. '
                        f'Auto-correction will invalidate the cache and re-check.'
                    ),
                })

        self._set_check_status(
            'tools_vs_processes',
            'READ_PARTIAL' if partial_process_reads else 'READ_OK',
            self._check_reasons.get('tools_vs_processes', 'sensor_read_incomplete')
            if partial_process_reads else '',
        )
        return inconsistencies

    @staticmethod
    def _enumerate_window_titles() -> list[str]:
        """Enumerate visible window titles on Windows."""
        if os.name != 'nt':
            return []
        try:
            import ctypes
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            titles: list[str] = []

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)  # type: ignore[misc]
            def _enum_cb(hwnd: Any, _lparam: Any) -> bool:
                if user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd, buf, 512)
                    t = buf.value.strip()
                    if t:
                        titles.append(t.lower())
                return True

            user32.EnumWindows(_enum_cb, 0)
            return titles
        except Exception as exc:
            raise RuntimeError('window_enumeration_failed') from exc

    def _cross_audit_vs_worldmodel(self) -> list[dict[str, Any]]:
        """Compare self-audit tool status against WorldModel tool_live_status."""
        inconsistencies: list[dict[str, Any]] = []
        if self.world_model_service is None or self.tool_registry is None:
            self._set_check_status('audit_vs_worldmodel', 'NOT_CONFIGURED', 'world_model_or_tool_registry_not_connected')
            return inconsistencies
        try:
            snapshot = self.world_model_service.current_snapshot()
            if snapshot is None:
                raise RuntimeError('world_model_snapshot_missing')
            wm_tool_ids = {t.tool_id for t in snapshot.tool_live_status}
            cards = self.tool_registry.list_cards()
        except Exception as exc:
            report = getattr(exc, 'report', None)
            if report is not None:
                payload = report.to_dict() if callable(getattr(report, 'to_dict', None)) else {
                    'status': getattr(getattr(report, 'status', None), 'value', str(getattr(report, 'status', 'UNKNOWN'))),
                    'records_seen': getattr(report, 'records_seen', None),
                    'records_loaded': getattr(report, 'records_loaded', None),
                    'failed_ids': list(getattr(report, 'failed_ids', []) or []),
                }
                self._check_reports['audit_vs_worldmodel'] = payload
                report_status = getattr(getattr(report, 'status', None), 'value', '')
                status = 'READ_PARTIAL' if report_status == 'READ_PARTIAL' else 'READ_FAILED'
                reason = getattr(report, 'collection_error_type', '') or type(exc).__name__
                self._set_check_status('audit_vs_worldmodel', status, reason)
            else:
                self._set_check_status('audit_vs_worldmodel', 'READ_FAILED', type(exc).__name__)
            return inconsistencies

        for card in cards:
            if card.tool_id not in wm_tool_ids:
                inconsistencies.append({
                    'check': 'audit_vs_worldmodel',
                    'severity': 'medium',
                    'tool_id': card.tool_id,
                    'expected': f'{card.tool_id} tracked in WorldModel',
                    'actual': f'{card.tool_id} missing from WorldModel tool_live_status',
                    'detail': (
                        f'ToolRegistry has {card.tool_id} registered but WorldModel '
                        f'does not track it in tool_live_status. The tool is invisible '
                        f'to components that consult WorldModel for decisions.'
                    ),
                })

        wm_available = {
            t.tool_id for t in snapshot.tool_live_status if t.available
        }
        wm_unavailable = {
            t.tool_id for t in snapshot.tool_live_status if not t.available
        }
        registry_available = {c.tool_id for c in cards if c.available}
        registry_unavailable = {c.tool_id for c in cards if not c.available}

        for tool_id in wm_available & registry_unavailable:
            inconsistencies.append({
                'check': 'audit_vs_worldmodel',
                'severity': 'high',
                'tool_id': tool_id,
                'expected': f'{tool_id} status consistent across sources',
                'actual': f'WorldModel says available, ToolRegistry says unavailable',
                'detail': 'Availability status mismatch between WorldModel and ToolRegistry.',
            })

        for tool_id in wm_unavailable & registry_available:
            inconsistencies.append({
                'check': 'audit_vs_worldmodel',
                'severity': 'medium',
                'tool_id': tool_id,
                'expected': f'{tool_id} status consistent across sources',
                'actual': f'WorldModel says unavailable, ToolRegistry says available',
                'detail': 'Availability status mismatch between WorldModel and ToolRegistry.',
            })

        self._set_check_status('audit_vs_worldmodel', 'READ_OK')
        return inconsistencies

    def _cross_windows_consistency(self) -> list[dict[str, Any]]:
        """Compare WorldModel windows against live window enumeration."""
        inconsistencies: list[dict[str, Any]] = []
        if self.world_model_service is None:
            self._set_check_status('windows_consistency', 'NOT_CONFIGURED', 'world_model_service_not_connected')
            return inconsistencies
        try:
            snapshot = self.world_model_service.current_snapshot()
            if snapshot is None or not hasattr(snapshot, 'active_windows'):
                raise RuntimeError('world_model_windows_snapshot_unavailable')
        except Exception as exc:
            self._set_check_status('windows_consistency', 'READ_FAILED', type(exc).__name__)
            return inconsistencies

        wm_window_count = len(snapshot.active_windows)
        if wm_window_count == 0 and os.name == 'nt':
            inconsistencies.append({
                'check': 'windows_consistency',
                'severity': 'high',
                'tool_id': '',
                'expected': 'WorldModel should detect open windows on Windows',
                'actual': '0 windows detected',
                'detail': 'No windows in WorldModel — window enumeration may have failed.',
            })

        focused = snapshot.focused_window
        if focused is not None and wm_window_count > 0:
            wm_titles = {w.title for w in snapshot.active_windows}
            if focused.title and focused.title not in wm_titles:
                inconsistencies.append({
                    'check': 'windows_consistency',
                    'severity': 'medium',
                    'tool_id': '',
                    'expected': 'Focused window should be in active_windows list',
                    'actual': f'Focused window "{focused.title}" not in active_windows',
                    'detail': 'The focused window is not found in the active windows list.',
                })

        self._set_check_status('windows_consistency', 'READ_OK')
        return inconsistencies

    # ------------------------------------------------------------------
    # UI Self-Awareness: IABV checks its own window state
    # ------------------------------------------------------------------

    _IABV_TITLE_MARKERS = ('iabv', 'iabv v1.5', 'centro de control', 'centro vivo')
    _ZOMBIE_MARKERS = ('no responde', 'not responding')

    def _cross_ui_self_awareness(self) -> list[dict[str, Any]]:
        """Check IABV's own window presence and health in WorldModel.

        Detects:
        - IABV window missing from WorldModel entirely
        - Zombie window ("No responde") alongside a healthy instance
        - Multiple IABV instances (potential resource leak)
        """
        inconsistencies: list[dict[str, Any]] = []
        if self.world_model_service is None:
            self._set_check_status('ui_self_awareness', 'NOT_CONFIGURED', 'world_model_service_not_connected')
            return inconsistencies
        try:
            snapshot = self.world_model_service.current_snapshot()
            if snapshot is None or not hasattr(snapshot, 'active_windows'):
                raise RuntimeError('world_model_windows_snapshot_unavailable')
        except Exception as exc:
            self._set_check_status('ui_self_awareness', 'READ_FAILED', type(exc).__name__)
            return inconsistencies

        if not snapshot.active_windows:
            self._set_check_status('ui_self_awareness', 'UNVERIFIED', 'no_windows_observed')
            return inconsistencies

        iabv_windows: list[Any] = []
        zombie_windows: list[Any] = []

        for w in snapshot.active_windows:
            title_lower = (w.title or '').lower()
            is_iabv = any(m in title_lower for m in self._IABV_TITLE_MARKERS)
            if not is_iabv:
                continue
            is_zombie = any(z in title_lower for z in self._ZOMBIE_MARKERS)
            if is_zombie:
                zombie_windows.append(w)
            else:
                iabv_windows.append(w)

        if not iabv_windows and not zombie_windows:
            # El MCP server arranca ANTES de la UI — durante los primeros
            # ~60s es normal no encontrar la ventana IABV todavia.
            uptime_s = time.time() - self._created_at
            is_early = uptime_s < 60.0
            inconsistencies.append({
                'check': 'ui_self_awareness',
                'severity': 'medium' if is_early else 'high',
                'tool_id': 'iabv_ui',
                'expected': 'IABV window should be visible in WorldModel',
                'actual': 'No IABV window detected among active windows',
                'detail': (
                    'The program cannot see its own window in the WorldModel. '
                    'Either the UI did not start, or the window enumeration '
                    'does not match IABV title markers.'
                    + (' This may be a startup timing issue — the MCP starts '
                       'before the UI process. Should resolve on next scan.'
                       if is_early else '')
                ),
                'early_startup': is_early,
            })

        if zombie_windows:
            zombie_titles = [w.title for w in zombie_windows]
            inconsistencies.append({
                'check': 'ui_self_awareness',
                'severity': 'high',
                'tool_id': 'iabv_ui',
                'expected': 'No zombie IABV windows',
                'actual': f'{len(zombie_windows)} zombie window(s): {zombie_titles}',
                'detail': (
                    'Detected IABV window(s) in "No responde" state. This '
                    'indicates the UI event loop is blocked or the process '
                    'is hung. The zombie PID should be terminated.'
                ),
                'zombie_pids': [
                    getattr(w, 'pid', None) for w in zombie_windows
                    if getattr(w, 'pid', None) is not None
                ],
            })

        if len(iabv_windows) > 1:
            inconsistencies.append({
                'check': 'ui_self_awareness',
                'severity': 'medium',
                'tool_id': 'iabv_ui',
                'expected': 'Single IABV window instance',
                'actual': f'{len(iabv_windows)} active IABV windows detected',
                'detail': (
                    'Multiple IABV windows are running. This may indicate a '
                    'resource leak or duplicate launch. Only one instance '
                    'should be active at a time.'
                ),
            })

        self._set_check_status('ui_self_awareness', 'READ_OK')
        return inconsistencies
