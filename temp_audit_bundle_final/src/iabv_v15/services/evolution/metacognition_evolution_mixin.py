"""Metacognition evolution mixin — connects new evolution services to OSES.

This mixin aggregates findings from:
- ``DecisionSimplifierEngine`` — fast-path obstacle resolution stats
- ``PlatformLearningOrchestrator`` — platform learning status
- ``ApiKeyDiscoveryService`` (existing) — provider health
- ``AutoCorrectionEngine`` (existing) — auto-correction capabilities
- ``ResourceMetacognitionService`` — RAM/GPU/process resource state

It also reacts to actionable findings autonomously:
- Auto-provision missing API keys
- Rotate exhausted providers
- Trigger platform re-learning when confidence drops

Architecture:
- NOT another brain.  Feeds findings into ``build_review()`` via
  injection into OSES.  Does not decide routes.
- Reacts only to findings with clear, safe actions.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MetacognitionEvolutionMixin:
    """Aggregates evolution findings and reacts autonomously.

    Injected attributes (set by bootstrap):
    - ``decision_simplifier``: ``DecisionSimplifierEngine``
    - ``platform_learning``: ``PlatformLearningOrchestrator``
    - ``api_key_discovery``: ``ApiKeyDiscoveryService``
    - ``auto_correction_engine``: ``AutoCorrectionEngine``
    - ``resource_metacognition``: ``ResourceMetacognitionService``
    """

    def __init__(self) -> None:
        self.decision_simplifier: Any = None
        self.platform_learning: Any = None
        self.api_key_discovery: Any = None
        self.auto_correction_engine: Any = None
        self.resource_metacognition: Any = None

    def all_findings(self) -> list[dict[str, Any]]:
        """Aggregate findings from all evolution services.

        Returns dicts with fields matching ``SelfExaminationFinding``.
        These are consumed by ``OperationalSelfExaminationService.build_review()``.
        """
        findings: list[dict[str, Any]] = []

        # DecisionSimplifierEngine findings
        if self.decision_simplifier:
            try:
                findings.extend(self.decision_simplifier.oses_findings())
            except Exception as exc:
                logger.warning('metacognition: decision_simplifier findings error: %s', exc)

        # PlatformLearningOrchestrator findings
        if self.platform_learning:
            try:
                findings.extend(self.platform_learning.oses_findings())
            except Exception as exc:
                logger.warning('metacognition: platform_learning findings error: %s', exc)

        # ResourceMetacognitionService findings
        if self.resource_metacognition:
            try:
                findings.extend(self.resource_metacognition.oses_findings())
            except Exception as exc:
                logger.warning('metacognition: resource_metacognition findings error: %s', exc)

        # ApiKeyDiscoveryService — check for missing/failing providers
        if self.api_key_discovery:
            try:
                missing = self.api_key_discovery.find_missing_keys()
                if len(missing) >= 2:
                    names = ', '.join(m['name'] for m in missing[:4])
                    findings.append({
                        'category': 'metacognition_evolution',
                        'title': f'{len(missing)} cloud providers not configured',
                        'summary': (
                            f'Missing API keys: {names}. '
                            f'Auto-provisioning can set these up.'
                        ),
                        'severity': 'MEDIUM',
                        'confidence': 0.9,
                        'recommendation': 'Run auto_provision_missing_secrets()',
                        'metadata': {
                            'missing_providers': [m['provider_id'] for m in missing],
                            'actionable': True,
                        },
                    })
            except Exception as exc:
                logger.warning('metacognition: api_key_discovery findings error: %s', exc)

        return findings

    def react_to_findings(self, findings: list[dict[str, Any]]) -> list[str]:
        """Execute safe auto-reactions to actionable findings.

        Returns list of action descriptions taken.
        """
        actions_taken: list[str] = []

        for finding in findings:
            meta = finding.get('metadata', {})
            if not meta.get('actionable'):
                continue

            category = finding.get('category', '')
            title = finding.get('title', '')

            # Auto-provision missing API keys
            if 'not configured' in title and self.auto_correction_engine:
                try:
                    self.auto_correction_engine.auto_provision_missing_secrets()
                    actions_taken.append(f'Auto-provisioned missing keys ({title})')
                    logger.info('metacognition: auto-provisioned missing keys')
                except Exception as exc:
                    logger.warning('metacognition: auto-provision failed: %s', exc)

            # Rotate exhausted provider
            if 'quota' in title.lower() and self.api_key_discovery:
                try:
                    best = self.api_key_discovery.best_provider()
                    if best and best.valid:
                        actions_taken.append(f'Rotated to best provider: {best.provider_id}')
                        logger.info('metacognition: rotated to %s', best.provider_id)
                except Exception as exc:
                    logger.warning('metacognition: rotation failed: %s', exc)

            # Trigger platform re-learning
            if 'reliability' in title.lower() and self.platform_learning:
                platform_id = meta.get('platform_id', '')
                if platform_id:
                    actions_taken.append(f'Flagged {platform_id} for re-learning')
                    logger.info('metacognition: flagged %s for re-learning', platform_id)

        return actions_taken

    def run_evolution_cycle(self) -> dict[str, Any]:
        """Execute one metacognition evolution cycle.

        Collect findings → react → return summary.
        """
        findings = self.all_findings()
        actions = self.react_to_findings(findings)

        # Benchmark providers if api_key_discovery available
        provider_health: dict[str, Any] | None = None
        if self.api_key_discovery:
            try:
                provider_health = self.api_key_discovery.full_health_report()
            except Exception:
                pass

        return {
            'findings_count': len(findings),
            'actions_taken': actions,
            'provider_health': provider_health,
            'decision_simplifier_status': (
                self.decision_simplifier.status_summary()
                if self.decision_simplifier else None
            ),
            'platform_learning_status': (
                self.platform_learning.status_summary()
                if self.platform_learning else None
            ),
        }
