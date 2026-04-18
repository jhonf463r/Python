from __future__ import annotations

from iabv_v15.domain.models import AdaptiveSession, DiagnosticCategory, ProbeDiagnosis, RuntimeAdjustment
from iabv_v15.infra.persistence.runtime_tuning_repository import RuntimeTuningRepository
from iabv_v15.services.adaptive.strategy_pack_registry import StrategyPackRegistry
from iabv_v15.services.evolution.hidden_incident_detector import HiddenIncidentDetector


class RuntimeTuner:
    def __init__(
        self,
        *,
        repository: RuntimeTuningRepository,
        hidden_incident_detector: HiddenIncidentDetector,
        strategy_pack_registry: StrategyPackRegistry,
    ) -> None:
        self.repository = repository
        self.hidden_incident_detector = hidden_incident_detector
        self.strategy_pack_registry = strategy_pack_registry
        self.apply_saved_profile()

    def apply_saved_profile(self) -> None:
        profile = self.repository.get('global')
        if profile is None:
            return
        thresholds = dict((profile.metadata or {}).get('incident_thresholds') or {})
        if thresholds:
            self.hidden_incident_detector.configure(thresholds)
        pack_overrides = dict((profile.metadata or {}).get('pack_parameter_overrides') or {})
        for pack_id, parameters in pack_overrides.items():
            for key, value in dict(parameters or {}).items():
                self.strategy_pack_registry.set_parameter_default(pack_id, key, value)

    def evaluate_and_apply(self, *, diagnosis: ProbeDiagnosis, session: AdaptiveSession) -> list[RuntimeAdjustment]:
        if diagnosis.category != DiagnosticCategory.NEED_RUNTIME_TUNING:
            return []
        incidents = [str(item.get('incident_kind') or '') for item in session.context.recent_incidents if item.get('incident_kind')]
        adjustments: list[RuntimeAdjustment] = []
        profile = self.repository.get('global')
        threshold_overrides = dict((profile.metadata or {}).get('incident_thresholds') or {}) if profile is not None else {}
        pack_overrides = dict((profile.metadata or {}).get('pack_parameter_overrides') or {}) if profile is not None else {}
        current_thresholds = self.hidden_incident_detector.describe_thresholds()

        if 'session_restore_weak' in incidents:
            current_value = self.strategy_pack_registry.get_parameter_default('wplay.login', 'login_mode')
            if current_value != 'guided_only':
                self.strategy_pack_registry.set_parameter_default('wplay.login', 'login_mode', 'guided_only')
                pack_overrides.setdefault('wplay.login', {})['login_mode'] = 'guided_only'
                adjustment = RuntimeAdjustment(
                    target_key='strategy_pack:wplay.login:login_mode',
                    previous_value=current_value,
                    new_value='guided_only',
                    reason='La restauracion de sesion viene fallando repetidamente; se fuerza login guiado para no insistir con restore_then_guided.',
                    evidence_refs=list(diagnosis.evidence_refs[:4]),
                    helped=False,
                )
                adjustments.append(adjustment)
                self.repository.append_adjustment(adjustment)

        if any(kind in incidents for kind in ('bridge_lag', 'navigation_stall', 'tab_attach_gap')):
            next_thresholds = dict(current_thresholds)
            next_thresholds['queue_depth_threshold'] = max(int(current_thresholds.get('queue_depth_threshold', 80) or 80), 100)
            next_thresholds['poll_without_progress_threshold'] = max(int(current_thresholds.get('poll_without_progress_threshold', 4) or 4), 5)
            next_thresholds['navigation_stall_seconds'] = max(float(current_thresholds.get('navigation_stall_seconds', 8.0) or 8.0), 10.0)
            next_thresholds['tab_attach_gap_seconds'] = max(float(current_thresholds.get('tab_attach_gap_seconds', 2.0) or 2.0), 3.0)
            if next_thresholds != current_thresholds:
                self.hidden_incident_detector.configure(next_thresholds)
                threshold_overrides.update(next_thresholds)
                adjustment = RuntimeAdjustment(
                    target_key='hidden_incident_thresholds',
                    previous_value=current_thresholds,
                    new_value=next_thresholds,
                    reason='Subo thresholds seguros para no sobrerreaccionar mientras seguimos observando multitab, bridge y attach de paginas.',
                    evidence_refs=list(diagnosis.evidence_refs[:4]),
                    helped=False,
                )
                adjustments.append(adjustment)
                self.repository.append_adjustment(adjustment)

        if adjustments:
            metadata = {
                'incident_thresholds': threshold_overrides,
                'pack_parameter_overrides': pack_overrides,
            }
            if profile is None:
                from iabv_v15.domain.models import RuntimeTuningProfile
                profile = RuntimeTuningProfile(scope_key='global', metadata=metadata)
            else:
                profile.metadata.update(metadata)
            from datetime import datetime, timezone
            profile.updated_at_utc = datetime.now(timezone.utc)
            self.repository.save(profile)
        return adjustments
