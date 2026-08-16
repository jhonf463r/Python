"""P0.69: Metacognitive Discernment Frame Service.

Builds, updates and queries discernment frames — the shared evidence
contract that existing services read/write before acting.

This is NOT another cerebro.  It is a lightweight coordinator that:
1. Reads state from existing services (WorldModel, EnvironmentSelfModel,
   RuntimeAuditTracer, OSES, ExperimentLab, AdaptiveWeightLayer).
2. Produces a ``MetacognitiveDiscernmentFrame`` with bias/grounding/
   attractor/contradiction analysis.
3. Exposes the frame for downstream consumption (TaskContextAssembler,
   PortableContext, ControlCenterViewModel).

The service is stateless per-request: each ``build_frame()`` call reads
live state and returns a new frame.  A small in-memory ring buffer keeps
the last N frames for OSES to review.
"""
from __future__ import annotations

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iabv_v15.domain.models import MetacognitiveDiscernmentFrame, EpistemicHypothesis

_logger = logging.getLogger(__name__)

_MAX_FRAME_HISTORY = 20


class DiscernmentFrameService:
    """Builds discernment frames from live system state."""

    def __init__(self, *, workspace_root: str = '') -> None:
        self._workspace_root = workspace_root
        self._frame_history: deque[MetacognitiveDiscernmentFrame] = deque(maxlen=_MAX_FRAME_HISTORY)

    def build_frame(
        self,
        *,
        phase: str = 'observe',
        trigger_source: str = '',
        raw_inputs: list[str] | None = None,
        world_model: dict[str, Any] | None = None,
        environment_self_model: dict[str, Any] | None = None,
        experiment_runs: list[Any] | None = None,
        recent_findings: list[Any] | None = None,
        startup_events: list[dict[str, Any]] | None = None,
        freeze_reports: list[dict[str, Any]] | None = None,
        concept_weight_evidence: dict[str, Any] | None = None,
        human_evidence: list[dict[str, Any]] | None = None,
        diagnostic_request: bool = False,  # P0.18G: diagnostic intent marker
    ) -> MetacognitiveDiscernmentFrame:
        """Build a new discernment frame from available state."""
        frame = MetacognitiveDiscernmentFrame(
            phase=phase,
            trigger_source=trigger_source,
            raw_inputs=list(raw_inputs or []),
        )

        # P0.18G: Set diagnostic_request flag in frame metadata during construction
        if diagnostic_request:
            frame.metadata['diagnostic_request'] = True

        # Sensor sources
        sensors = self._collect_sensor_sources(
            world_model=world_model,
            environment_self_model=environment_self_model,
            startup_events=startup_events,
        )
        frame.sensor_sources = sensors['available']
        frame.trusted_sources = sensors['trusted']
        frame.untrusted_sources = sensors['untrusted']
        frame.missing_sources = sensors['missing']

        # Attractor summary from experiment runs
        attractors = self._build_attractor_summary(experiment_runs or [])
        frame.active_attractors = attractors['active']
        frame.failed_attractors = attractors['failed']
        frame.candidate_attractor = attractors['candidate']
        frame.attractor_confidence = attractors['confidence']

        # ConceptWeightEvidence wiring
        self._apply_concept_weight_evidence(frame, concept_weight_evidence)

        # Bias filter
        biases = self._detect_bias_risks(
            world_model=world_model,
            raw_inputs=raw_inputs or [],
            recent_findings=recent_findings or [],
            freeze_reports=freeze_reports or [],
        )
        frame.bias_risks = biases['risks']
        frame.contradictions = biases['contradictions']
        # Merge contradictions from concept weight evidence
        if concept_weight_evidence:
            cwe_contradictions = concept_weight_evidence.get('contradictions', [])
            if cwe_contradictions:
                frame.contradictions.extend(cwe_contradictions)

        # Grounding status
        frame.grounding_status = self._assess_grounding(frame)
        frame.confidence = self._compute_confidence(frame)

        # Unresolved (extend, don't overwrite — earlier steps may have added markers)
        frame.unresolved_fields.extend(
            f for f in self._collect_unresolved(frame)
            if f not in frame.unresolved_fields
        )

        selected_test = self._propose_diagnostic_test(frame, world_model=world_model)
        if selected_test:
            # P0.20b: Generate epistemic hypothesis from contradiction
            epistemic_hypothesis = self._generate_epistemic_hypothesis(frame, selected_test)
            if epistemic_hypothesis:
                frame.metadata['epistemic_hypothesis'] = epistemic_hypothesis
                # Propagate hypothesis_id and expected_result to selected_test
                selected_test['hypothesis_id'] = epistemic_hypothesis.hypothesis_id
                selected_test['expected_result'] = epistemic_hypothesis.expected_result
            frame.metadata['selected_test'] = selected_test
        if human_evidence:
            frame.metadata['human_evidence'] = [dict(item) for item in human_evidence if isinstance(item, dict)]

        self._frame_history.append(frame)
        return frame

    @staticmethod
    def _propose_diagnostic_test(
        frame: MetacognitiveDiscernmentFrame,
        *,
        world_model: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Derive one read-only diagnostic proposal from structured evidence.

        This is two-tier:
        1. First, check for structured provider health contradictions (most specific)
        2. Second, check for diagnostic intent marker with available evidence (general case)
        It never executes a test.
        """
        # Tier 1: Structured provider health contradictions (most specific)
        for contradiction in frame.contradictions:
            if str(contradiction.get('type') or '') != 'provider_health_vs_inference_failure':
                continue
            evidence = contradiction.get('evidence')
            if not isinstance(evidence, dict):
                continue
            provider = str(evidence.get('provider') or '').strip()
            target = str(evidence.get('diagnostic_target') or '').strip()
            if not provider or not target:
                continue
            return {
                'test_id': f'{provider}_availability_probe',
                'test_type': 'provider_availability',
                'target': target,
                'reason': 'Structured provider health contradicts its inference result.',
                'cost_class': 'low',
                'status': 'proposed',
                'contradiction_type': 'provider_health_vs_inference_failure',
                'diagnostic': True,
                'read_only': True,
                'requires_approval': False,
                'timeout_seconds': 2.0,
                'observed_condition': 'provider_available',  # P0.20h: Mandatory explicit dimension
            }

        # Tier 2: General diagnostic intent with available evidence (P0.18G integration)
        # P0.20h: Do not create executable test without defined observed_condition
        # Check if this is a diagnostic request via frame metadata
        is_diagnostic = bool(frame.metadata.get('diagnostic_request', False))
        if not is_diagnostic:
            return {}

        # For general diagnostic requests, propose a minimal self-diagnostic test
        # Only if we have at least one trusted source to work with
        if not frame.trusted_sources:
            return {}

        # Determine minimal diagnostic target from available sources
        diagnostic_target = 'system_self_diagnostic'
        if 'world_model' in frame.trusted_sources:
            diagnostic_target = 'world_model_state'
        elif 'environment_self_model' in frame.trusted_sources:
            diagnostic_target = 'environment_state'

        # P0.20h: Do not create executable test without observed_condition
        # General diagnostic without defined dimension should not execute invented observation
        # Return empty dict to indicate no executable test available
        return {}

    @staticmethod
    def _generate_epistemic_hypothesis(
        frame: MetacognitiveDiscernmentFrame,
        selected_test: dict[str, Any],
    ) -> EpistemicHypothesis | None:
        """Generate minimal epistemic hypothesis from contradiction.

        P0.20b: Creates a traceable hypothesis that explains the contradiction
        and provides an expected_result for verification.

        Returns None if no sufficient evidence exists.
        """
        # Only generate hypothesis if we have contradictions and trusted sources
        if not frame.contradictions or not frame.trusted_sources:
            return None

        # Use the first contradiction as the source
        contradiction = frame.contradictions[0]
        contradiction_type = str(contradiction.get('type') or 'unknown')

        # Build evidence refs from frame sources
        evidence_refs = []
        if frame.frame_id:
            evidence_refs.append(f'frame:{frame.frame_id}')
        for source in frame.trusted_sources[:3]:
            evidence_refs.append(f'source:{source}')
        if frame.sensor_sources:
            evidence_refs.append(f'sensors:{len(frame.sensor_sources)}')

        # Build contradiction refs
        contradiction_refs = [f'contradiction:{contradiction_type}']

        # Generate hypothesis statement based on contradiction type
        statement = f"Contradiction {contradiction_type} suggests a diagnostic gap."

        # Generate expected_result based on selected_test.observed_condition
        # P0.20g: Use explicit observed_condition from selected_test instead of inferring from target text
        # P0.20h: No fallback - observed_condition must be present in selected_test
        observed_condition = selected_test.get('observed_condition')
        if not observed_condition:
            # P0.20h: Cannot generate hypothesis without observed_condition
            return None
        expected_result = {
            'condition': observed_condition,
            'expected': True,
        }

        return EpistemicHypothesis(
            statement=statement,
            expected_result=expected_result,
            evidence_refs=evidence_refs,
            contradiction_refs=contradiction_refs,
        )

    def build_birth_frame(
        self,
        *,
        startup_events: list[dict[str, Any]] | None = None,
        environment_self_model: dict[str, Any] | None = None,
        world_model: dict[str, Any] | None = None,
        freeze_reports: list[dict[str, Any]] | None = None,
    ) -> MetacognitiveDiscernmentFrame:
        """Build a genesis/birth frame from startup data."""
        raw_inputs: list[str] = []
        if startup_events:
            phases = [e.get('phase', '') for e in startup_events[:10]]
            raw_inputs = [f'startup_phase:{p}' for p in phases if p]

        frame = self.build_frame(
            phase='birth',
            trigger_source='startup',
            raw_inputs=raw_inputs,
            world_model=world_model,
            environment_self_model=environment_self_model,
            startup_events=startup_events,
            freeze_reports=freeze_reports,
        )

        # Birth-specific: don't allow deep cognition
        if freeze_reports:
            frame.bias_risks.append({
                'type': 'birth_with_freeze_history',
                'detail': f'{len(freeze_reports)} recent freeze reports — defer heavy cognition',
                'severity': 'high',
            })
            frame.next_observation = 'stabilize_ui_before_deep_cognition'

        env_risks = []
        if environment_self_model:
            for risk in environment_self_model.get('risk_signals', []):
                if isinstance(risk, dict):
                    env_risks.append(risk.get('category', ''))
                else:
                    env_risks.append(str(getattr(risk, 'category', '')))
        if env_risks:
            frame.metadata['birth_env_risks'] = env_risks

        return frame

    def recent_frames(self, limit: int = 5) -> list[MetacognitiveDiscernmentFrame]:
        """Return most recent frames for OSES review."""
        return list(self._frame_history)[-limit:]

    def latest_frame(self) -> MetacognitiveDiscernmentFrame | None:
        """Return the most recent frame, or None."""
        return self._frame_history[-1] if self._frame_history else None

    def human_summary(self, frame: MetacognitiveDiscernmentFrame | None = None) -> dict[str, str]:
        """Build human-readable summary from a frame.

        Returns dict with keys: what_i_know, what_i_see, what_i_cannot_confirm,
        possible_bias, what_i_need_to_observe, next_action.
        """
        if frame is None:
            frame = self.latest_frame()
        if frame is None:
            return {
                'what_i_know': 'No tengo un frame de discernimiento activo.',
                'what_i_see': '',
                'what_i_cannot_confirm': '',
                'possible_bias': '',
                'what_i_need_to_observe': '',
                'next_action': 'Esperando primer estímulo.',
            }

        what_i_know_parts = []
        if frame.trusted_sources:
            what_i_know_parts.append(f'Fuentes confiables: {", ".join(frame.trusted_sources)}')
        if frame.active_attractors:
            names = [a.get('key', '') for a in frame.active_attractors[:3]]
            what_i_know_parts.append(f'Atractores activos: {", ".join(names)}')

        what_i_see_parts = []
        if frame.sensor_sources:
            what_i_see_parts.append(f'Sensores: {", ".join(frame.sensor_sources)}')
        if frame.detected_concepts:
            what_i_see_parts.append(f'Conceptos: {", ".join(frame.detected_concepts[:5])}')

        cannot_confirm_parts = []
        if frame.untrusted_sources:
            cannot_confirm_parts.append(f'Fuentes no confiables: {", ".join(frame.untrusted_sources)}')
        if frame.missing_sources:
            cannot_confirm_parts.append(f'Fuentes faltantes: {", ".join(frame.missing_sources)}')

        bias_parts = []
        for b in frame.bias_risks[:3]:
            bias_parts.append(f'{b.get("type", "unknown")}: {b.get("detail", "")}')

        return {
            'what_i_know': '; '.join(what_i_know_parts) or 'Sin información confirmada.',
            'what_i_see': '; '.join(what_i_see_parts) or 'Sin sensores activos.',
            'what_i_cannot_confirm': '; '.join(cannot_confirm_parts) or 'Todo confirmado.',
            'possible_bias': '; '.join(bias_parts) or 'Sin sesgos detectados.',
            'what_i_need_to_observe': frame.next_observation or 'Nada pendiente.',
            'next_action': frame.selected_action or 'Sin acción seleccionada.',
        }

    def compact_export(self, frame: MetacognitiveDiscernmentFrame | None = None) -> dict[str, Any]:
        """Compact export for PortableContext (no PII)."""
        if frame is None:
            frame = self.latest_frame()
        if frame is None:
            return {'status': 'no_frame'}
        return {
            'frame_id': frame.frame_id,
            'phase': frame.phase,
            'trigger_source': frame.trigger_source,
            'grounding_status': frame.grounding_status,
            'confidence': round(frame.confidence, 3),
            'sensor_count': len(frame.sensor_sources),
            'trusted_count': len(frame.trusted_sources),
            'untrusted_count': len(frame.untrusted_sources),
            'missing_count': len(frame.missing_sources),
            'detected_concepts': frame.detected_concepts[:10],
            'concept_weight_count': len(frame.concept_weights),
            'contradiction_count': len(frame.contradictions),
            'bias_risk_count': len(frame.bias_risks),
            'active_attractor_count': len(frame.active_attractors),
            'failed_attractor_count': len(frame.failed_attractors),
            'candidate_attractor': frame.candidate_attractor,
            'attractor_confidence': round(frame.attractor_confidence, 3),
            'selected_action': frame.selected_action,
            'human_help_needed': frame.human_help_needed,
            'unresolved_fields': frame.unresolved_fields[:5],
        }

    def discernment_frame_summary(self, frame: MetacognitiveDiscernmentFrame | None = None) -> dict[str, Any]:
        """Compact summary for TaskContextAssembler metadata."""
        if frame is None:
            frame = self.latest_frame()
        if frame is None:
            return {'status': 'no_frame'}
        return {
            'phase': frame.phase,
            'grounding_status': frame.grounding_status,
            'confidence': round(frame.confidence, 3),
            'detected_concepts': frame.detected_concepts[:5],
            'active_attractors': [a.get('key', '') for a in frame.active_attractors[:3]],
            'contradictions_count': len(frame.contradictions),
            'bias_risks': [b.get('type', '') for b in frame.bias_risks[:3]],
            'selected_action': frame.selected_action,
            'unresolved_fields': frame.unresolved_fields[:5],
        }

    # ── ConceptWeightEvidence wiring ──────────────────────────

    @staticmethod
    def _apply_concept_weight_evidence(
        frame: MetacognitiveDiscernmentFrame,
        evidence: dict[str, Any] | None,
    ) -> None:
        """Wire concept_weight_evidence (dict from existing service) into the frame.

        Accepts the dict output produced by the existing
        ``concept_weight_evidence`` service (or any compatible dict with
        keys: concepts, weights, sources, missing_sources, contradictions).
        Does NOT create a parallel model — consumes whatever the upstream
        service provides.
        """
        if evidence is None:
            if 'concept_weight_evidence_missing' not in frame.unresolved_fields:
                frame.unresolved_fields.append('concept_weight_evidence_missing')
            return
        concepts = evidence.get('concepts', [])
        weights = evidence.get('weights', {})
        sources = evidence.get('sources', [])
        if concepts:
            frame.detected_concepts = list(concepts)
        if weights:
            frame.concept_weights = dict(weights)
        if sources:
            for src in sources:
                label = f'cwe:{src}'
                if label not in frame.sensor_sources:
                    frame.sensor_sources.append(label)
                if label not in frame.trusted_sources:
                    frame.trusted_sources.append(label)

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _collect_sensor_sources(
        *,
        world_model: dict[str, Any] | None,
        environment_self_model: dict[str, Any] | None,
        startup_events: list[dict[str, Any]] | None,
    ) -> dict[str, list[str]]:
        available: list[str] = []
        trusted: list[str] = []
        untrusted: list[str] = []
        missing: list[str] = []

        if world_model:
            available.append('world_model')
            trusted.append('world_model')
            if world_model.get('active_windows'):
                available.append('windows')
                trusted.append('windows')
            if world_model.get('network'):
                available.append('network')
                trusted.append('network')
        else:
            missing.append('world_model')

        if environment_self_model:
            available.append('environment_self_model')
            trusted.append('environment_self_model')
        else:
            missing.append('environment_self_model')

        if startup_events:
            available.append('startup_timeline')
            trusted.append('startup_timeline')

        # Runtime audit is always potentially available
        try:
            from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
            tracer = get_runtime_tracer()
            if tracer.events(limit=1):
                available.append('runtime_audit')
                trusted.append('runtime_audit')
        except Exception:
            pass

        return {
            'available': available,
            'trusted': trusted,
            'untrusted': untrusted,
            'missing': missing,
        }

    @staticmethod
    def _build_attractor_summary(experiment_runs: list[Any]) -> dict[str, Any]:
        active: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        candidate = ''
        confidence = 0.0

        if not experiment_runs:
            return {
                'active': active,
                'failed': failed,
                'candidate': candidate,
                'confidence': confidence,
            }

        from collections import defaultdict
        config_success: dict[str, list[float]] = defaultdict(list)
        config_total: dict[str, int] = defaultdict(int)
        config_failures: dict[str, int] = defaultdict(int)

        for run in experiment_runs:
            kind = str(getattr(run, 'assistant_kind', '') or '').strip().lower()
            route_val = getattr(run, 'route', None)
            route = str(route_val.value if route_val else '')
            if not kind:
                continue
            key = f'{kind}:{route}'
            config_total[key] += 1
            success = bool(getattr(run, 'success', False))
            if success:
                metrics = getattr(run, 'metrics', None)
                score = float(getattr(metrics, 'total_score', 0.0) if metrics else 0.0)
                config_success[key].append(score)
            else:
                config_failures[key] += 1

        for key, scores in config_success.items():
            total = config_total.get(key, len(scores))
            if total < 3:
                continue
            success_rate = len(scores) / max(total, 1)
            avg_score = sum(scores) / max(len(scores), 1)
            if success_rate >= 0.75 and avg_score >= 0.5:
                active.append({
                    'key': key,
                    'avg_score': round(avg_score, 4),
                    'total_runs': total,
                    'success_rate': round(success_rate, 3),
                })

        for key, fail_count in config_failures.items():
            total = config_total.get(key, fail_count)
            if total < 3:
                continue
            fail_rate = fail_count / max(total, 1)
            if fail_rate >= 0.6:
                failed.append({
                    'key': key,
                    'fail_rate': round(fail_rate, 3),
                    'total_runs': total,
                })

        active.sort(key=lambda a: (a.get('avg_score', 0), a.get('total_runs', 0)), reverse=True)
        if active:
            candidate = active[0]['key']
            confidence = active[0].get('avg_score', 0.0)

        return {
            'active': active[:5],
            'failed': failed[:5],
            'candidate': candidate,
            'confidence': confidence,
        }

    @staticmethod
    def _detect_bias_risks(
        *,
        world_model: dict[str, Any] | None,
        raw_inputs: list[str],
        recent_findings: list[Any],
        freeze_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        risks: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []

        # Rule 1: if action based on local chat without grounding
        if raw_inputs and not world_model:
            risks.append({
                'type': 'local_reasoning_without_grounding',
                'detail': 'Action based on input without live world model',
                'severity': 'medium',
            })

        # Rule 2: if freeze reports present, bias toward caution
        if freeze_reports:
            risks.append({
                'type': 'recent_freeze_bias',
                'detail': f'{len(freeze_reports)} recent freezes — system should be cautious',
                'severity': 'medium',
            })

        # Rule 3: stale history contradicting live state
        if world_model and raw_inputs:
            wm_status = world_model.get('scan_status', '')
            if wm_status == 'stale':
                contradictions.append({
                    'type': 'stale_world_model_vs_live_input',
                    'detail': 'World model is stale; live input may be more current',
                    'resolution': 'live_wins',
                })

        # Rule 4: low visual/DOM confidence
        if world_model:
            for tool in world_model.get('tool_live_status', []):
                if isinstance(tool, dict):
                    conf = tool.get('confidence', 1.0)
                    probe = tool.get('probe_status', '')
                    if conf < 0.5 or probe == 'no_verificado':
                        tool_id = tool.get('tool_id', 'unknown')
                        risks.append({
                            'type': 'low_confidence_observation',
                            'detail': f'Tool {tool_id} has low confidence ({conf})',
                            'severity': 'low',
                        })

        # Rule 5: repeated failures from OSES findings
        for finding in recent_findings:
            severity = str(getattr(finding, 'severity', ''))
            category = str(getattr(finding, 'category', ''))
            if 'HIGH' in severity.upper() and 'repeat' in category.lower():
                risks.append({
                    'type': 'repeated_failure_route',
                    'detail': str(getattr(finding, 'summary', category)),
                    'severity': 'high',
                })

        # Structured provider evidence can identify a health/inference mismatch.
        # A target must be supplied by the observed provider state; no endpoint is
        # invented here for a particular provider.
        provider_health = dict((world_model or {}).get('metadata', {}).get('provider_health') or {})
        for provider, health in provider_health.items():
            if not isinstance(health, dict):
                continue
            health_status = str(health.get('health_status') or '').lower()
            inference_status = str(health.get('inference_status') or '').lower()
            target = str(health.get('diagnostic_target') or '').strip()
            if health_status != 'healthy' or inference_status not in {'timeout', 'failed', 'error'} or not target:
                continue
            contradictions.append({
                'type': 'provider_health_vs_inference_failure',
                'detail': f'Provider {provider} is healthy but inference is {inference_status}.',
                'evidence': {
                    'provider': str(provider),
                    'health_status': health_status,
                    'inference_status': inference_status,
                    'diagnostic_target': target,
                },
            })

        return {'risks': risks, 'contradictions': contradictions}

    @staticmethod
    def _assess_grounding(frame: MetacognitiveDiscernmentFrame) -> str:
        if not frame.sensor_sources:
            return 'no_sensors'
        if frame.missing_sources and len(frame.missing_sources) > len(frame.trusted_sources):
            return 'insufficient'
        if frame.contradictions:
            return 'contradicted'
        if frame.untrusted_sources and not frame.trusted_sources:
            return 'untrusted_only'
        if frame.trusted_sources:
            return 'grounded'
        return 'partial'

    @staticmethod
    def _compute_confidence(frame: MetacognitiveDiscernmentFrame) -> float:
        base = 0.5
        if frame.trusted_sources:
            base += 0.1 * min(len(frame.trusted_sources), 3)
        if frame.missing_sources:
            base -= 0.1 * min(len(frame.missing_sources), 3)
        if frame.contradictions:
            base -= 0.15 * min(len(frame.contradictions), 2)
        if frame.bias_risks:
            base -= 0.05 * min(len(frame.bias_risks), 3)
        if frame.active_attractors:
            base += 0.05
        return max(0.0, min(1.0, round(base, 3)))

    @staticmethod
    def _collect_unresolved(frame: MetacognitiveDiscernmentFrame) -> list[str]:
        unresolved: list[str] = []
        if 'world_model' in frame.missing_sources:
            unresolved.append('world_model_missing')
        if 'environment_self_model' in frame.missing_sources:
            unresolved.append('environment_self_model_missing')
        if frame.grounding_status in ('no_sensors', 'insufficient', 'untrusted_only'):
            unresolved.append(f'grounding_{frame.grounding_status}')
        for c in frame.contradictions:
            unresolved.append(f'contradiction_{c.get("type", "unknown")}')
        return unresolved
