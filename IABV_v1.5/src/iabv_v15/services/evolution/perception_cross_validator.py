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

    def run_cross_validation(self) -> dict[str, Any]:
        """Execute full cross-validation and return structured results.

        When inconsistencies are found, attempts auto-correction by
        invalidating the availability cache for affected tools and
        triggering a refresh.  Returns both inconsistencies and any
        corrections applied.
        """
        inconsistencies: list[dict[str, Any]] = []
        auto_corrections: list[dict[str, Any]] = []
        checks_passed: list[str] = []
        checked_at = datetime.now(timezone.utc).isoformat()

        proc_inconsistencies = self._cross_tools_vs_processes()
        inconsistencies.extend(proc_inconsistencies)

        corrections = self._auto_correct_availability(proc_inconsistencies)
        auto_corrections.extend(corrections)

        inconsistencies.extend(self._cross_audit_vs_worldmodel())
        inconsistencies.extend(self._cross_windows_consistency())

        if not any(i['check'] == 'tools_vs_processes' for i in inconsistencies):
            checks_passed.append('tools_vs_processes')
        if not any(i['check'] == 'audit_vs_worldmodel' for i in inconsistencies):
            checks_passed.append('audit_vs_worldmodel')
        if not any(i['check'] == 'windows_consistency' for i in inconsistencies):
            checks_passed.append('windows_consistency')

        # Incluir boot-time disagreements capturados por tool_adapters
        boot_disagreements = self._collect_boot_disagreements()
        inconsistencies.extend(boot_disagreements)

        if not any(i['check'] == 'boot_disagreements' for i in inconsistencies):
            checks_passed.append('boot_disagreements')

        return {
            'checked_at': checked_at,
            'inconsistencies': inconsistencies,
            'auto_corrections': auto_corrections,
            'checks_passed': checks_passed,
            'total_inconsistencies': len(inconsistencies),
            'total_auto_corrections': len(auto_corrections),
            'total_checks': 4,
            'learning': (
                'Cuando las fuentes discrepan (filesystem vs procesos vs ventanas), '
                'la fuente positiva prevalece. Un solo sensor negativo NO es '
                'suficiente para declarar missing. Esta validacion cruzada se '
                'ejecuta automaticamente para detectar y corregir percepciones '
                'erroneas antes de que afecten decisiones. Los disagreements '
                'del boot se preservan como evidencia de que el cruce funciona.'
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

    def _collect_boot_disagreements(self) -> list[dict[str, Any]]:
        """Recoge los multi_source_disagreement capturados durante el boot.
        
        Los tool_adapters guardan evidencia cuando diferentes fuentes de
        deteccion (filesystem, process, window) no coinciden. Esta informacion
        es valiosa para la auditoria y para demostrar que el cruce de
        informacion funciona.
        """
        inconsistencies: list[dict[str, Any]] = []
        if self.tool_registry is None:
            return inconsistencies

        try:
            cards = list(self.tool_registry.all_cards())
        except Exception:
            return inconsistencies

        for card in cards:
            detection = None
            if hasattr(card, 'metadata') and isinstance(card.metadata, dict):
                detection = card.metadata.get('detection_evidence')
            if detection is None:
                detection = getattr(card, 'detection_evidence', None)
            if detection is None:
                continue
            
            positives = detection.get('positives', [])
            negatives = detection.get('negatives', [])
            
            if positives and negatives:
                inconsistencies.append({
                    'check': 'boot_disagreements',
                    'tool_id': card.tool_id if hasattr(card, 'tool_id') else str(card),
                    'expected': f'todas las fuentes coinciden',
                    'actual': f'positives={positives}, negatives={negatives}',
                    'severity': 'info',
                    'description': (
                        f'Boot-time disagreement: {card.tool_id if hasattr(card, "tool_id") else card} '
                        f'detectado por {positives} pero NO por {negatives}. '
                        f'Resolucion: available=True (optimistic).'
                    ),
                    'auto_resolution': 'optimistic_positive',
                })

        return inconsistencies

    def _cross_tools_vs_processes(self) -> list[dict[str, Any]]:
        """Compare running processes against tool availability status.

        Also checks window titles as a third source — if a tool has
        a visible window, it is definitely running even if the process
        name doesn't match expected keywords.
        """
        inconsistencies: list[dict[str, Any]] = []
        if self.tool_registry is None:
            return inconsistencies

        if os.name != 'nt':
            return inconsistencies

        try:
            import psutil
        except ImportError:
            return inconsistencies

        proc_names: set[str] = set()
        proc_exes: set[str] = set()
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
                    continue
        except Exception:
            return inconsistencies

        all_proc_text = ' '.join(proc_names) + ' ' + ' '.join(proc_exes)

        window_titles = self._enumerate_window_titles()
        all_window_text = ' '.join(window_titles)

        try:
            cards = self.tool_registry.list_cards()
        except Exception:
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
        except Exception:
            return []

    def _cross_audit_vs_worldmodel(self) -> list[dict[str, Any]]:
        """Compare self-audit tool status against WorldModel tool_live_status."""
        inconsistencies: list[dict[str, Any]] = []
        if self.world_model_service is None or self.tool_registry is None:
            return inconsistencies

        try:
            snapshot = self.world_model_service.current_snapshot()
        except Exception:
            return inconsistencies

        wm_tool_ids = {t.tool_id for t in snapshot.tool_live_status}

        try:
            cards = self.tool_registry.list_cards()
        except Exception:
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

        return inconsistencies

    def _cross_windows_consistency(self) -> list[dict[str, Any]]:
        """Compare WorldModel windows against live window enumeration."""
        inconsistencies: list[dict[str, Any]] = []
        if self.world_model_service is None:
            return inconsistencies

        try:
            snapshot = self.world_model_service.current_snapshot()
        except Exception:
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

        return inconsistencies
