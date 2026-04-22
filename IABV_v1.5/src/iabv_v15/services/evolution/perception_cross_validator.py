"""Cross-validates perception data from multiple IABV sensors.

Compares processes vs tool availability, windows vs WorldModel, and
network status to detect inconsistencies that individual sensors miss.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PerceptionCrossValidator:
    """Lightweight cross-validator for meta-cognition consistency."""

    def __init__(
        self,
        *,
        world_model_service: Any = None,
        tool_registry: Any = None,
    ) -> None:
        self.world_model_service = world_model_service
        self.tool_registry = tool_registry

    def run_cross_validation(self) -> dict[str, Any]:
        """Execute full cross-validation and return structured results."""
        inconsistencies: list[dict[str, Any]] = []
        checks_passed: list[str] = []
        checked_at = datetime.now(timezone.utc).isoformat()

        inconsistencies.extend(self._cross_tools_vs_processes())
        inconsistencies.extend(self._cross_audit_vs_worldmodel())
        inconsistencies.extend(self._cross_windows_consistency())

        if not any(i['check'] == 'tools_vs_processes' for i in inconsistencies):
            checks_passed.append('tools_vs_processes')
        if not any(i['check'] == 'audit_vs_worldmodel' for i in inconsistencies):
            checks_passed.append('audit_vs_worldmodel')
        if not any(i['check'] == 'windows_consistency' for i in inconsistencies):
            checks_passed.append('windows_consistency')

        return {
            'checked_at': checked_at,
            'inconsistencies': inconsistencies,
            'checks_passed': checks_passed,
            'total_inconsistencies': len(inconsistencies),
            'total_checks': 3,
        }

    def _cross_tools_vs_processes(self) -> list[dict[str, Any]]:
        """Compare running processes against tool availability status."""
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

            found = [kw for kw in keywords if kw in all_proc_text]
            if found:
                inconsistencies.append({
                    'check': 'tools_vs_processes',
                    'severity': 'high',
                    'tool_id': card.tool_id,
                    'expected': f'{card.tool_id} reported as unavailable',
                    'actual': f'Process matching {found} is running',
                    'detail': (
                        f'Tool registry says {card.tool_id} is unavailable but a '
                        f'matching process ({", ".join(found)}) is currently running. '
                        f'The detection logic may not cover this install method.'
                    ),
                })

        return inconsistencies

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
